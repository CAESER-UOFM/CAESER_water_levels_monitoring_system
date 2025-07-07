# -*- coding: utf-8 -*-
"""
Barologger Data Edit Dialog

Provides editing capabilities for barologger data with focus on spike correction filtering.
Similar to water level edit dialog but specialized for atmospheric pressure data.

@author: claude
"""

import sys
import sqlite3
import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, 
    QLabel, QCheckBox, QDateTimeEdit, QGroupBox, QMessageBox,
    QProgressDialog, QFrame, QSizePolicy, QSpacerItem, QScrollArea, QWidget,
    QTabWidget, QListWidget, QListWidgetItem, QApplication
)
from PyQt5.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

class SpikeDetectionWorker(QThread):
    """Worker thread for spike detection and correction processing."""
    
    progress_updated = pyqtSignal(int, str)
    spike_detection_completed = pyqtSignal(object, object)  # original_data, corrected_data
    
    def __init__(self, data: pd.DataFrame):
        super().__init__()
        self.data = data
        
    def run(self):
        """Run spike detection algorithm."""
        try:
            self.progress_updated.emit(10, "Analyzing pressure data...")
            
            # Apply spike correction algorithm
            corrected_data = self._detect_and_correct_spikes(self.data.copy())
            
            self.progress_updated.emit(100, "Spike detection completed")
            self.spike_detection_completed.emit(self.data, corrected_data)
            
        except Exception as e:
            logger.error(f"Error in spike detection: {e}")
            self.spike_detection_completed.emit(self.data, None)
    
    def _detect_and_correct_spikes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Implement spike detection and correction algorithm."""
        try:
            if 'pressure' not in df.columns or len(df) < 10:
                return df
                
            self.progress_updated.emit(30, "Detecting spikes...")
            
            # Parameters for spike detection
            window_hours = 4
            local_avg_hours = 1
            threshold_std = 3.0
            
            # Convert to numpy arrays for efficiency
            pressure = df['pressure'].values
            timestamps = pd.to_datetime(df['timestamp_utc'])
            
            # Calculate rolling statistics for spike detection
            # Use 4-hour window (16 points for 15-min data)
            window_size = max(5, int(window_hours * 4))  # 4 points per hour for 15-min data
            local_avg_size = max(3, int(local_avg_hours * 4))  # 1 hour window
            
            self.progress_updated.emit(50, "Calculating statistics...")
            
            spike_flags = np.zeros(len(pressure), dtype=bool)
            corrected_pressure = pressure.copy()
            
            # Rolling window spike detection
            for i in range(window_size, len(pressure) - window_size):
                # Get surrounding window (excluding current point)
                window_start = max(0, i - window_size)
                window_end = min(len(pressure), i + window_size + 1)
                
                # Exclude current point from window
                window_data = np.concatenate([
                    pressure[window_start:i],
                    pressure[i+1:window_end]
                ])
                
                if len(window_data) < 5:
                    continue
                    
                # Calculate statistics
                window_mean = np.mean(window_data)
                window_std = np.std(window_data)
                
                # Check if current point is a spike
                deviation = abs(pressure[i] - window_mean)
                if deviation > threshold_std * window_std and window_std > 0.01:
                    spike_flags[i] = True
                    
                    # Replace with local average
                    local_start = max(0, i - local_avg_size)
                    local_end = min(len(pressure), i + local_avg_size + 1)
                    
                    # Get local data excluding the spike
                    local_data = np.concatenate([
                        pressure[local_start:i],
                        pressure[i+1:local_end]
                    ])
                    
                    if len(local_data) > 0:
                        corrected_pressure[i] = np.mean(local_data)
                        
                # Update progress
                if i % 100 == 0:
                    progress = 50 + int((i / len(pressure)) * 40)
                    self.progress_updated.emit(progress, f"Processing point {i}/{len(pressure)}")
            
            self.progress_updated.emit(90, "Finalizing corrections...")
            
            # Add results to dataframe
            df['pressure_corrected'] = corrected_pressure
            df['spike_flag'] = spike_flags
            df['correction_magnitude'] = np.abs(pressure - corrected_pressure)
            
            num_spikes = np.sum(spike_flags)
            logger.info(f"Detected and corrected {num_spikes} spikes out of {len(df)} points")
            
            return df
            
        except Exception as e:
            logger.error(f"Error in spike correction algorithm: {e}")
            return df


class BarologgerEditDialog(QDialog):
    """Dialog for editing barologger data with spike correction capabilities."""
    
    def __init__(self, selected_barologgers: List[str], db_manager, parent=None):
        super().__init__(parent)
        self.selected_barologgers = selected_barologgers
        self.db_manager = db_manager
        self.parent_window = parent
        
        # Data storage
        self.original_data = None
        self.corrected_data = None
        self.current_data = None
        
        # UI components
        self.figure = None
        self.canvas = None
        self.ax = None
        self.span_selector = None
        
        # Control flags
        self.show_original = True
        self.show_corrected = False
        self.show_corrections = False
        
        # Manual spike removal variables (compatible with water level edit dialog)
        self.manual_spike_pairs = []  # List of (start_point, end_point) tuples
        self.manual_corrected_data = None
        self.manual_spike_changes = {}  # Track manual changes
        
        # Spike selection variables (same as water level edit dialog)
        self.spike_selection_mode = False
        self.spike_helper_dialog = None
        self.spike_selection_points = []  # Store selected points for visualization
        self.spike_preview_lines = []  # Store preview lines
        self.spike_click_event_id = None
        
        # Point selection and interaction variables (from water level edit dialog)
        self.scatter_plots = []  # Store plot objects for hover and pick events
        self.hover_annotation = None  # Current hover tooltip
        self.point_annotations = {}  # Persistent click annotations
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle(f"Edit Barologger Data - {', '.join(self.selected_barologgers)}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Controls section
        controls_frame = self._create_controls_section()
        layout.addWidget(controls_frame)
        
        # Plot section
        plot_frame = self._create_plot_section()
        layout.addWidget(plot_frame, stretch=1)
        
        # Bottom buttons
        button_layout = self._create_button_section()
        layout.addLayout(button_layout)
        
    def _create_controls_section(self) -> QFrame:
        """Create the controls section with tabs."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setMaximumHeight(180)  # Increased height for tabs
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(5)
        
        # Create tab widget
        self.controls_tabs = QTabWidget()
        
        # Tab 1: Automatic Detection
        auto_tab = self._create_auto_detection_tab()
        self.controls_tabs.addTab(auto_tab, "Automatic Detection")
        
        # Tab 2: Manual Removal  
        manual_tab = self._create_manual_removal_tab()
        self.controls_tabs.addTab(manual_tab, "Manual Removal")
        
        # Tab 3: Display Controls (moved here)
        display_tab = self._create_display_controls_tab()
        self.controls_tabs.addTab(display_tab, "Display & Time Range")
        
        layout.addWidget(self.controls_tabs)
        return frame
        
    def _create_auto_detection_tab(self) -> QWidget:
        """Create the automatic detection tab."""
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setSpacing(8)
        
        # Processing controls
        process_group = QGroupBox("Automatic Spike Detection")
        process_layout = QHBoxLayout(process_group)
        
        self.detect_spikes_btn = QPushButton("Detect & Correct Spikes")
        self.detect_spikes_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.detect_spikes_btn.clicked.connect(self.detect_spikes)
        process_layout.addWidget(self.detect_spikes_btn)
        
        self.reset_auto_btn = QPushButton("Reset Automatic")
        self.reset_auto_btn.clicked.connect(self.reset_to_original)
        process_layout.addWidget(self.reset_auto_btn)
        
        # Help button
        help_btn = QPushButton("Help")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        help_btn.clicked.connect(self.show_help_dialog)
        process_layout.addWidget(help_btn)
        
        process_layout.addStretch()
        layout.addWidget(process_group, 0, 0, 1, 2)
        
        return tab
        
    def _create_manual_removal_tab(self) -> QWidget:
        """Create the manual spike removal tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)  # Use horizontal layout like automatic detection
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Import the spike fix helper dialog
        from ..dialogs.edit_tool_helper_dialog import SpikeFixHelperDialog
        
        # Create spike fix helper button that opens the same dialog as water level edit
        spike_fix_btn = QPushButton("Fix Spikes Helper")
        spike_fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 140px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        spike_fix_btn.clicked.connect(self.open_spike_fix_helper)
        layout.addWidget(spike_fix_btn)
        
        self.apply_manual_btn = QPushButton("Apply Manual Fixes")
        self.apply_manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 160px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.apply_manual_btn.clicked.connect(self.apply_manual_fixes)
        layout.addWidget(self.apply_manual_btn)
        
        layout.addStretch()
        
        # Initialize spike selection variables - same as water level edit dialog
        self.spike_selection_mode = False
        self.spike_helper_dialog = None
        self.spike_selection_points = []  # Store selected points for visualization
        self.spike_preview_lines = []  # Store preview lines
        self.spike_click_event_id = None
        
        return tab
        
    def _create_display_controls_tab(self) -> QWidget:
        """Create the display controls and time range tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)  # Use horizontal layout like other tabs
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Data display checkboxes
        self.show_original_cb = QCheckBox("Show Original")
        self.show_original_cb.setChecked(True)
        self.show_original_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                padding: 8px 12px;
                spacing: 8px;
                min-height: 40px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.show_original_cb.stateChanged.connect(self.update_plot_display)
        layout.addWidget(self.show_original_cb)
        
        self.show_corrected_cb = QCheckBox("Show Corrected")
        self.show_corrected_cb.setChecked(False)
        self.show_corrected_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                padding: 8px 12px;
                spacing: 8px;
                min-height: 40px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.show_corrected_cb.stateChanged.connect(self.update_plot_display)
        layout.addWidget(self.show_corrected_cb)
        
        self.show_corrections_cb = QCheckBox("Show Corrections")
        self.show_corrections_cb.setChecked(False)
        self.show_corrections_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                padding: 8px 12px;
                spacing: 8px;
                min-height: 40px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.show_corrections_cb.stateChanged.connect(self.update_plot_display)
        layout.addWidget(self.show_corrections_cb)
        
        # Show Data Gaps checkbox
        self.show_data_gaps_cb = QCheckBox("Show Data Gaps")
        self.show_data_gaps_cb.setChecked(True)
        self.show_data_gaps_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                padding: 8px 12px;
                spacing: 8px;
                min-height: 40px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.show_data_gaps_cb.stateChanged.connect(self.update_plot_display)
        layout.addWidget(self.show_data_gaps_cb)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #ccc;")
        layout.addWidget(separator)
        
        # Time range controls
        start_label = QLabel("Start:")
        start_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        layout.addWidget(start_label)
        
        self.start_date = QDateTimeEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDateTime(QDateTime.currentDateTime().addDays(-30))
        self.start_date.setStyleSheet("""
            QDateTimeEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 13px;
                min-height: 40px;
                min-width: 150px;
            }
        """)
        self.start_date.dateTimeChanged.connect(self.update_plot_display)
        layout.addWidget(self.start_date)
        
        end_label = QLabel("End:")
        end_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        layout.addWidget(end_label)
        
        self.end_date = QDateTimeEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDateTime(QDateTime.currentDateTime())
        self.end_date.setStyleSheet("""
            QDateTimeEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 13px;
                min-height: 40px;
                min-width: 150px;
            }
        """)
        self.end_date.dateTimeChanged.connect(self.update_plot_display)
        layout.addWidget(self.end_date)
        
        zoom_btn = QPushButton("Zoom to Range")
        zoom_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 14px;
                min-height: 40px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        zoom_btn.clicked.connect(self.zoom_to_range)
        layout.addWidget(zoom_btn)
        
        full_range_btn = QPushButton("Full Range")
        full_range_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 14px;
                min-height: 40px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        full_range_btn.clicked.connect(self.zoom_to_full_range)
        layout.addWidget(full_range_btn)
        
        layout.addStretch()
        return tab
        
    def _create_plot_section(self) -> QFrame:
        """Create the plotting section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connect interactive event handlers for tooltips and point selection
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        return frame
        
    def _create_button_section(self) -> QHBoxLayout:
        """Create the bottom button section."""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # Save changes button
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        save_btn.clicked.connect(self.save_changes)
        layout.addWidget(save_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancel_dialog)
        layout.addWidget(cancel_btn)
        
        return layout
        
    def load_data(self):
        """Load barologger data from database."""
        try:
            if not self.db_manager.current_db:
                QMessageBox.warning(self, "Error", "No database selected")
                return
                
            # Create progress dialog
            progress = QProgressDialog("Loading barologger data...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            with sqlite3.connect(self.db_manager.current_db) as conn:
                # Build query for selected barologgers
                placeholders = ','.join(['?' for _ in self.selected_barologgers])
                query = f"""
                    SELECT serial_number, timestamp_utc, julian_timestamp, 
                           pressure, temperature
                    FROM barometric_readings 
                    WHERE serial_number IN ({placeholders})
                    ORDER BY serial_number, julian_timestamp
                """
                
                progress.setValue(50)
                
                df = pd.read_sql_query(query, conn, params=self.selected_barologgers)
                
                if df.empty:
                    QMessageBox.information(self, "No Data", "No data found for selected barologgers")
                    return
                    
                progress.setValue(80)
                
                # Convert timestamp
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                
                # Store original data
                self.original_data = df.copy()
                self.current_data = df.copy()
                
                # Update time range controls
                self.start_date.setDateTime(QDateTime.fromString(
                    df['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M:%S'), 
                    'yyyy-MM-dd hh:mm:ss'
                ))
                self.end_date.setDateTime(QDateTime.fromString(
                    df['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M:%S'), 
                    'yyyy-MM-dd hh:mm:ss'
                ))
                
                progress.setValue(100)
                progress.close()
                
                # Initial plot
                self.update_plot_display()
                
        except Exception as e:
            logger.error(f"Error loading barologger data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
            
    def detect_spikes(self):
        """Run spike detection and correction."""
        if self.original_data is None or self.original_data.empty:
            QMessageBox.warning(self, "Warning", "No data loaded for spike detection")
            return
            
        # Create progress dialog
        progress = QProgressDialog("Detecting spikes...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(False)
        progress.show()
        
        # Create and start worker thread
        self.spike_worker = SpikeDetectionWorker(self.original_data)
        self.spike_worker.progress_updated.connect(progress.setValue)
        self.spike_worker.progress_updated.connect(lambda v, msg: progress.setLabelText(msg))
        self.spike_worker.spike_detection_completed.connect(self._on_spike_detection_completed)
        self.spike_worker.finished.connect(progress.close)
        
        self.spike_worker.start()
        
    def _on_spike_detection_completed(self, original_data, corrected_data):
        """Handle spike detection completion."""
        if corrected_data is not None:
            self.corrected_data = corrected_data
            
            # Enable corrected data display
            self.show_corrected_cb.setChecked(True)
            self.show_corrections_cb.setChecked(True)
            
            # Update plot
            self.update_plot_display()
            
            # Show summary
            if 'spike_flag' in corrected_data.columns:
                num_spikes = corrected_data['spike_flag'].sum()
                total_points = len(corrected_data)
                percentage = (num_spikes / total_points) * 100 if total_points > 0 else 0
                
                QMessageBox.information(
                    self, 
                    "Spike Detection Complete",
                    f"Detected and corrected {num_spikes} spikes out of {total_points} points ({percentage:.2f}%)"
                )
        else:
            QMessageBox.critical(self, "Error", "Spike detection failed")
            
    def update_plot_display(self):
        """Update the plot display based on current settings."""
        if self.original_data is None:
            return
            
        try:
            self.figure.clear()
            
            # Get time range
            start_time = self.start_date.dateTime().toPyDateTime()
            end_time = self.end_date.dateTime().toPyDateTime()
            
            # Filter data by time range
            mask = (self.original_data['timestamp_utc'] >= start_time) & \
                   (self.original_data['timestamp_utc'] <= end_time)
            display_data = self.original_data[mask]
            
            if display_data.empty:
                self.canvas.draw()
                return
                
            # Calculate dynamic line width based on data density
            num_points = len(display_data)
            if num_points > 10000:
                base_linewidth = 0.5
                marker_size = 1
            elif num_points > 5000:
                base_linewidth = 0.8
                marker_size = 1.5
            elif num_points > 1000:
                base_linewidth = 1.0
                marker_size = 2
            else:
                base_linewidth = 1.5
                marker_size = 3
                
            # Create subplots with better spacing
            if self.show_corrections_cb.isChecked() and self.corrected_data is not None:
                self.ax = self.figure.add_subplot(211)
                ax_corrections = self.figure.add_subplot(212)
                # Adjust subplot spacing
                self.figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.15, hspace=0.3)
            else:
                self.ax = self.figure.add_subplot(111)
                # Single plot spacing
                self.figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.12)
                
            # Clear scatter_plots for new plot
            self.scatter_plots = []
            
            # Plot original data
            if self.show_original_cb.isChecked():
                for serial in display_data['serial_number'].unique():
                    serial_data = display_data[display_data['serial_number'] == serial]
                    line, = self.ax.plot(serial_data['timestamp_utc'], serial_data['pressure'], 
                                       'o-', alpha=0.7, markersize=marker_size, linewidth=base_linewidth, 
                                       label=f'{serial} (Original)', picker=5)  # Enable picking with 5-point tolerance
                    # Store the line and its data for hover and pick events
                    self.scatter_plots.append((line, serial_data))
                    
            # Plot corrected data (automatic and manual)
            if self.show_corrected_cb.isChecked():
                # Plot automatic corrections
                if self.corrected_data is not None:
                    corrected_mask = (self.corrected_data['timestamp_utc'] >= start_time) & \
                                   (self.corrected_data['timestamp_utc'] <= end_time)
                    corrected_display = self.corrected_data[corrected_mask]
                    
                    for serial in corrected_display['serial_number'].unique():
                        serial_data = corrected_display[corrected_display['serial_number'] == serial]
                        line, = self.ax.plot(serial_data['timestamp_utc'], serial_data['pressure_corrected'], 
                                           's-', alpha=0.8, markersize=marker_size, linewidth=base_linewidth * 1.2,
                                           label=f'{serial} (Auto Corrected)', picker=5)  # Enable picking
                        # Store the line and its data for hover and pick events
                        self.scatter_plots.append((line, serial_data))
                
                # Plot manual corrections
                if self.manual_corrected_data is not None and self.manual_spike_changes:
                    manual_mask = (self.manual_corrected_data['timestamp_utc'] >= start_time) & \
                                 (self.manual_corrected_data['timestamp_utc'] <= end_time)
                    manual_display = self.manual_corrected_data[manual_mask]
                    
                    for serial in manual_display['serial_number'].unique():
                        serial_data = manual_display[manual_display['serial_number'] == serial]
                        # Only plot manually corrected points
                        manual_indices = [idx for idx in self.manual_spike_changes.keys() if idx in serial_data.index]
                        if manual_indices:
                            manual_data = serial_data.loc[manual_indices]
                            line, = self.ax.plot(manual_data['timestamp_utc'], manual_data['pressure'], 
                                               '^-', alpha=0.8, markersize=marker_size * 1.2, linewidth=base_linewidth * 1.2,
                                               label=f'{serial} (Manual Corrected)', picker=5)  # Enable picking
                            # Store the line and its data for hover and pick events
                            self.scatter_plots.append((line, manual_data))
                    
            # Plot corrections and spike highlights
            if self.show_corrections_cb.isChecked() and self.corrected_data is not None:
                corrected_mask = (self.corrected_data['timestamp_utc'] >= start_time) & \
                               (self.corrected_data['timestamp_utc'] <= end_time)
                corrected_display = self.corrected_data[corrected_mask]
                
                for serial in corrected_display['serial_number'].unique():
                    serial_data = corrected_display[corrected_display['serial_number'] == serial]
                    
                    # Highlight automatic spikes on main plot
                    spikes = serial_data[serial_data['spike_flag'] == True]
                    if not spikes.empty:
                        self.ax.scatter(spikes['timestamp_utc'], spikes['pressure'], 
                                      color='red', s=20, alpha=0.8, marker='x',
                                      label=f'{serial} (Auto Spikes)', zorder=10)
                        
                    # Plot correction magnitude in corrections subplot if it exists
                    if 'ax_corrections' in locals():
                        ax_corrections.plot(serial_data['timestamp_utc'], 
                                          serial_data['correction_magnitude'],
                                          'purple', alpha=0.7, linewidth=base_linewidth,
                                          label=f'{serial} (Auto Correction)')
                                          
            # Highlight manual spike pairs on main plot
            if self.manual_spike_pairs:
                for i, ((t1, p1), (t2, p2)) in enumerate(self.manual_spike_pairs):
                    # Highlight the manual spike pair points
                    self.ax.scatter([t1, t2], [p1, p2], 
                                  color='orange', s=max(20, marker_size * 8), alpha=0.9, marker='o',
                                  label=f'Manual Spikes {i+1}' if i == 0 else '', zorder=15)
                    # Draw connection line
                    self.ax.plot([t1, t2], [p1, p2], 'orange', alpha=0.7, linewidth=base_linewidth * 2, linestyle='--')
                    
            # Show manual correction effects in corrections subplot
            if ('ax_corrections' in locals() and self.manual_corrected_data is not None 
                and self.manual_spike_changes):
                manual_mask = (self.manual_corrected_data['timestamp_utc'] >= start_time) & \
                             (self.manual_corrected_data['timestamp_utc'] <= end_time)
                manual_display = self.manual_corrected_data[manual_mask]
                
                # Calculate and plot manual correction magnitudes
                for idx in self.manual_spike_changes.keys():
                    if idx in manual_display.index:
                        row = manual_display.loc[idx]
                        change_info = self.manual_spike_changes[idx]
                        correction_magnitude = abs(change_info['manual_corrected_pressure'] - change_info['original_pressure'])
                        ax_corrections.scatter(row['timestamp_utc'], correction_magnitude,
                                             color='orange', s=15, alpha=0.8, marker='^',
                                             label='Manual Correction' if idx == list(self.manual_spike_changes.keys())[0] else '')
            
            # Add data gap visualization if enabled
            if self.show_data_gaps_cb.isChecked() and display_data is not None and not display_data.empty:
                self._plot_data_gaps(display_data)
                        
            # Format main plot
            self.ax.set_ylabel('Pressure (psi)', fontsize=10)
            self.ax.legend(loc='best', fontsize=8)
            self.ax.grid(True, alpha=0.3)
            
            # Format corrections plot if it exists
            if self.show_corrections_cb.isChecked() and self.corrected_data is not None:
                if 'ax_corrections' in locals():
                    ax_corrections.set_xlabel('Date/Time (UTC)', fontsize=10)
                    ax_corrections.set_ylabel('Correction (psi)', fontsize=10)
                    ax_corrections.legend(loc='best', fontsize=8)
                    ax_corrections.grid(True, alpha=0.3)
                    # Format corrections plot date axis
                    ax_corrections.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%y'))
                    ax_corrections.xaxis.set_major_locator(mdates.YearLocator())
                    ax_corrections.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
                    ax_corrections.tick_params(axis='x', rotation=45, labelsize=8)
                    ax_corrections.tick_params(axis='y', labelsize=8)
            else:
                self.ax.set_xlabel('Date/Time (UTC)', fontsize=10)
                
            # Determine appropriate date format based on time range
            time_range = end_time - start_time
            if time_range.days > 1825:  # > 5 years
                date_format = '%Y'
                major_locator = mdates.YearLocator()
                minor_locator = mdates.MonthLocator((1, 7))
            elif time_range.days > 365:  # > 1 year
                date_format = '%m/%y'
                major_locator = mdates.YearLocator()
                minor_locator = mdates.MonthLocator((1, 4, 7, 10))
            elif time_range.days > 90:  # > 3 months
                date_format = '%m/%d/%y'
                major_locator = mdates.MonthLocator()
                minor_locator = mdates.WeekdayLocator()
            elif time_range.days > 7:  # > 1 week
                date_format = '%m/%d'
                major_locator = mdates.WeekdayLocator()
                minor_locator = mdates.DayLocator()
            else:  # <= 1 week
                date_format = '%m/%d %H:%M'
                major_locator = mdates.DayLocator()
                minor_locator = mdates.HourLocator((0, 6, 12, 18))
                
            # Format main plot date axis with dynamic formatting
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            self.ax.xaxis.set_major_locator(major_locator)
            self.ax.xaxis.set_minor_locator(minor_locator)
            self.ax.tick_params(axis='x', rotation=45, labelsize=8)
            self.ax.tick_params(axis='y', labelsize=8)
            
            # Apply tight layout with padding to prevent label cutoff
            self.figure.tight_layout(pad=1.5)
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            
    def zoom_to_range(self):
        """Zoom plot to selected time range."""
        self.update_plot_display()
        
    def zoom_to_full_range(self):
        """Zoom to full data range."""
        if self.original_data is not None:
            self.start_date.setDateTime(QDateTime.fromString(
                self.original_data['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M:%S'), 
                'yyyy-MM-dd hh:mm:ss'
            ))
            self.end_date.setDateTime(QDateTime.fromString(
                self.original_data['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M:%S'), 
                'yyyy-MM-dd hh:mm:ss'
            ))
            self.update_plot_display()
    
    def _plot_data_gaps(self, data):
        """Add background highlighting for data gaps in barologger data"""
        try:
            # Gap configuration (adjusted for barologger 15-minute intervals)
            gap_color = "#FFEBEE"  # Light red background for gaps
            gap_threshold = timedelta(hours=2)  # Use 2-hour threshold for 15-minute data
            gap_alpha = 0.6  # Opacity
            
            if data is None or len(data) < 2:
                return
                
            # Sort by timestamp to ensure chronological order
            sorted_data = data.sort_values('timestamp_utc').reset_index(drop=True)
            
            # Calculate time differences between consecutive points
            time_diffs = sorted_data['timestamp_utc'].diff()
            
            # Find indices where the time difference exceeds the threshold
            gap_indices = time_diffs[time_diffs > gap_threshold].index.tolist()
            
            # Create gap rectangles
            for idx in gap_indices:
                gap_start = sorted_data.loc[idx-1, 'timestamp_utc']
                gap_end = sorted_data.loc[idx, 'timestamp_utc']
                
                # Get current plot y-limits
                y_min, y_max = self.ax.get_ylim()
                
                # Add a rectangle spanning the gap with a distinctive color
                rect = plt.Rectangle(
                    (mdates.date2num(gap_start), y_min),
                    mdates.date2num(gap_end) - mdates.date2num(gap_start),
                    y_max - y_min,
                    color=gap_color,
                    alpha=gap_alpha,
                    zorder=-100  # Place behind other plot elements
                )
                self.ax.add_patch(rect)
                
        except Exception as e:
            logger.error(f"Error plotting data gaps: {e}", exc_info=True)
            
    def reset_to_original(self):
        """Reset data to original values."""
        self.corrected_data = None
        self.manual_corrected_data = None
        self.manual_spike_pairs = []
        self.manual_spike_changes = {}
        self.clear_spike_lines()
        self.update_pairs_list()
        self.show_corrected_cb.setChecked(False)
        self.show_corrections_cb.setChecked(False)
        self.update_plot_display()
        
        
    def apply_manual_fixes(self):
        """Apply manual spike corrections using linear interpolation."""
        if not self.manual_spike_pairs:
            QMessageBox.warning(self, "No Selection", "Please select spike pairs first")
            return
            
        if self.original_data is None or self.original_data.empty:
            QMessageBox.warning(self, "No Data", "No data available for manual correction")
            return
            
        try:
            # Create a copy of original data for manual corrections
            if self.manual_corrected_data is None:
                self.manual_corrected_data = self.original_data.copy()
                
            changes_made = 0
            
            for pair_idx, ((t1, p1), (t2, p2)) in enumerate(self.manual_spike_pairs):
                # Find data points between t1 and t2
                mask = (self.manual_corrected_data['timestamp_utc'] >= t1) & \
                       (self.manual_corrected_data['timestamp_utc'] <= t2)
                       
                affected_indices = self.manual_corrected_data[mask].index
                
                if len(affected_indices) > 0:
                    # Linear interpolation between p1 and p2
                    timestamps = self.manual_corrected_data.loc[affected_indices, 'timestamp_utc']
                    
                    # Calculate interpolated values
                    time_range = (t2 - t1).total_seconds()
                    for idx in affected_indices:
                        timestamp = self.manual_corrected_data.loc[idx, 'timestamp_utc']
                        time_fraction = (timestamp - t1).total_seconds() / time_range if time_range > 0 else 0
                        interpolated_pressure = p1 + (p2 - p1) * time_fraction
                        
                        # Store original value if not already stored
                        if idx not in self.manual_spike_changes:
                            self.manual_spike_changes[idx] = {
                                'original_pressure': self.manual_corrected_data.loc[idx, 'pressure'],
                                'manual_corrected_pressure': interpolated_pressure,
                                'pair_index': pair_idx
                            }
                        
                        # Apply the correction
                        self.manual_corrected_data.loc[idx, 'pressure'] = interpolated_pressure
                        changes_made += 1
                        
            # Update display
            self.show_corrected_cb.setChecked(True)
            self.update_plot_display()
            
            QMessageBox.information(
                self, 
                "Manual Corrections Applied",
                f"Applied linear interpolation to {changes_made} data points across {len(self.manual_spike_pairs)} spike pairs."
            )
            
        except Exception as e:
            logger.error(f"Error applying manual fixes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply manual corrections: {str(e)}")
            
    def save_changes(self):
        """Save corrected data to database."""
        # Check if we have any corrections to save
        has_auto_corrections = self.corrected_data is not None
        has_manual_corrections = self.manual_corrected_data is not None and self.manual_spike_changes
        
        if not has_auto_corrections and not has_manual_corrections:
            QMessageBox.information(self, "No Changes", "No corrections to save")
            return
            
        try:
            # Collect all modifications (auto + manual)
            all_modifications = []
            
            # Add automatic corrections
            if has_auto_corrections:
                spike_corrected_mask = self.corrected_data['spike_flag'] == True
                auto_modified = self.corrected_data[spike_corrected_mask].copy()
                for _, row in auto_modified.iterrows():
                    all_modifications.append({
                        'serial_number': row['serial_number'],
                        'timestamp_utc': row['timestamp_utc'],
                        'new_pressure': row['pressure_corrected'],
                        'correction_type': 'automatic_spike_detection'
                    })
            
            # Add manual corrections
            if has_manual_corrections:
                for idx, change_info in self.manual_spike_changes.items():
                    row = self.manual_corrected_data.loc[idx]
                    all_modifications.append({
                        'serial_number': row['serial_number'],
                        'timestamp_utc': row['timestamp_utc'],
                        'new_pressure': change_info['manual_corrected_pressure'],
                        'correction_type': 'manual_spike_correction'
                    })
            
            if not all_modifications:
                QMessageBox.information(self, "No Changes", "No corrections to save")
                return
                
            # Show confirmation dialog
            num_records = len(all_modifications)
            auto_count = sum(1 for m in all_modifications if m['correction_type'] == 'automatic_spike_detection')
            manual_count = sum(1 for m in all_modifications if m['correction_type'] == 'manual_spike_correction')
            
            confirm_msg = f"Are you sure you want to update {num_records} records in the database?\n\n"
            if auto_count > 0:
                confirm_msg += f"• {auto_count} automatic spike corrections\n"
            if manual_count > 0:
                confirm_msg += f"• {manual_count} manual spike corrections\n"
            confirm_msg += "\nThis will update pressure values in the barometric_readings table."
            
            if QMessageBox.question(self, 'Confirm Changes', confirm_msg, 
                                  QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                return
                
            # Create progress dialog
            progress = QProgressDialog("Updating database...", "Cancel", 0, num_records, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Applying Spike Corrections")
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            
            # Apply changes to database
            try:
                # Check database path
                if not self.db_manager.current_db:
                    raise ValueError("No database connection available")
                    
                # Connect and start transaction
                conn = sqlite3.connect(self.db_manager.current_db)
                cursor = conn.cursor()
                
                logger.info(f"Starting database update for {num_records} spike-corrected records")
                
                # Process in batches
                batch_size = 100
                records_updated = 0
                
                # Update barometric_readings table with corrected pressure values
                for i, modification in enumerate(all_modifications):
                    if progress.wasCanceled():
                        break
                        
                    try:
                        # Determine quality flag and notes based on correction type
                        if modification['correction_type'] == 'automatic_spike_detection':
                            quality_flag = 'auto_spike_corrected'
                            note_text = 'Auto spike corrected on'
                        else:
                            quality_flag = 'manual_spike_corrected'
                            note_text = 'Manual spike corrected on'
                        
                        # Update pressure value in database
                        cursor.execute("""
                            UPDATE barometric_readings 
                            SET pressure = ?, 
                                quality_flag = ?,
                                notes = COALESCE(notes || ' | ', '') || ? || ' ' || datetime('now')
                            WHERE serial_number = ? 
                            AND timestamp_utc = ?
                        """, (
                            float(modification['new_pressure']),
                            quality_flag,
                            note_text,
                            modification['serial_number'],
                            modification['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S')
                        ))
                        
                        records_updated += 1
                        
                        # Update progress
                        if records_updated % 10 == 0:  # Update every 10 records
                            progress.setValue(records_updated)
                            progress.setLabelText(f"Updated {records_updated}/{num_records} records...")
                            
                    except Exception as e:
                        logger.error(f"Error updating record {index}: {e}")
                        continue
                        
                # Commit changes
                conn.commit()
                conn.close()
                
                progress.setValue(num_records)
                progress.close()
                
                # Track changes if this is a cloud database
                if (hasattr(self.db_manager, 'is_cloud_database') and 
                    self.db_manager.is_cloud_database and
                    hasattr(self.db_manager, 'change_tracker') and 
                    self.db_manager.change_tracker):
                    
                    # Track the bulk change
                    change_id = self.db_manager.change_tracker.track_bulk_baro_spike_correction(
                        self.selected_barologgers, records_updated
                    )
                    logger.info(f"Tracked bulk spike correction: {change_id}")
                    
                    # Mark cloud database as modified
                    self.db_manager.mark_cloud_modified()
                
                # Show success message
                success_msg = f"Successfully updated {records_updated} records with spike corrections.\n\n" \
                              f"Quality flags set to 'spike_corrected' for modified data points."
                QMessageBox.information(self, "Success", success_msg)
                
                # Emit signal to refresh parent data if needed
                if hasattr(self.parent_window, 'refresh_data'):
                    self.parent_window.refresh_data()
                
                # Close helper dialog when saving changes
                self.close_helper_dialog()
                    
                self.accept()
                
            except Exception as e:
                logger.error(f"Database error during save: {e}")
                progress.close()
                QMessageBox.critical(self, "Database Error", f"Failed to save changes to database: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error saving changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
            
    def open_spike_fix_helper(self):
        """Open the spike fix helper dialog - same as water level edit dialog"""
        from ..dialogs.edit_tool_helper_dialog import SpikeFixHelperDialog
        
        if self.spike_helper_dialog is None or not self.spike_helper_dialog.isVisible():
            self.spike_helper_dialog = SpikeFixHelperDialog(self)
            self.spike_helper_dialog.parametersChanged.connect(self.on_spike_parameters_changed)
            self.spike_helper_dialog.apply_btn.clicked.connect(self.apply_spike_fixes)
            self.spike_helper_dialog.reset_btn.clicked.connect(self.reset_spike_selection)
            
        self.spike_helper_dialog.show()
        self.spike_helper_dialog.raise_()
        self.spike_helper_dialog.activateWindow()
    
    def start_spike_point_selection(self, helper_dialog):
        """Start spike point selection mode - same as water level edit dialog"""
        try:
            logger.info("Starting spike point selection mode")
            
            self.spike_selection_mode = True
            self.spike_helper_dialog = helper_dialog
            
            # Clear any previous selection
            self.clear_spike_selection_visuals()
            
            # Change cursor to cross-hair
            self.canvas.setCursor(Qt.CrossCursor)
            
            # Connect mouse click event - use button_release_event like water level dialog
            if hasattr(self, 'spike_click_event_id') and self.spike_click_event_id:
                self.canvas.mpl_disconnect(self.spike_click_event_id)
            self.spike_click_event_id = self.canvas.mpl_connect('button_release_event', self.on_spike_point_click)
            
            # Add status message at the top of the dialog
            if not hasattr(self, 'spike_status_label') or not self.spike_status_label:
                self.spike_status_label = QLabel("Click on the first point (start of spike) | Press ESC to cancel selection")
                self.spike_status_label.setAlignment(Qt.AlignCenter)
                self.spike_status_label.setStyleSheet("background-color: #FFF3CD; color: #856404; padding: 8px; border-radius: 4px;")
                self.layout().insertWidget(0, self.spike_status_label)
            
            # Initialize storage for preview lines and points if not already created
            if not hasattr(self, 'spike_lines') or self.spike_lines is None:
                self.spike_lines = []
            if not hasattr(self, 'spike_points') or self.spike_points is None:
                self.spike_points = []
            
            logger.info("Spike point selection mode activated")
            
        except Exception as e:
            logger.error(f"Error starting spike point selection: {e}")
    
    def cancel_spike_point_selection(self):
        """Cancel spike point selection mode - same as water level edit dialog"""
        try:
            logger.info("Canceling spike point selection mode")
            
            self.spike_selection_mode = False
            
            # Restore normal cursor
            self.canvas.setCursor(Qt.ArrowCursor)
            
            # Disconnect mouse click event
            if hasattr(self, 'spike_click_event_id') and self.spike_click_event_id:
                self.canvas.mpl_disconnect(self.spike_click_event_id)
                self.spike_click_event_id = None
            
            # Remove status label
            if hasattr(self, 'spike_status_label') and self.spike_status_label:
                self.spike_status_label.deleteLater()
                self.spike_status_label = None
            
            # Clear visual elements
            self.clear_spike_selection_visuals()
            
            # Reset helper dialog if it exists
            if self.spike_helper_dialog:
                self.spike_helper_dialog.reset_selection()
            
            logger.info("Spike point selection mode canceled")
            
        except Exception as e:
            logger.error(f"Error canceling spike point selection: {e}")
    
    def on_spike_point_click(self, event):
        """Handle mouse clicks during spike selection - same as water level edit dialog"""
        try:
            # Only select on left-button release when in selection mode and inside axes
            if not self.spike_selection_mode or event.inaxes != self.ax:
                return
            # Skip if pan/zoom tool is active  
            if hasattr(self, 'toolbar') and getattr(self.toolbar, 'mode', None):
                return
            # Skip if any keyboard modifier is held (allow navigation)
            gui_event = getattr(event, 'guiEvent', None)
            if gui_event and gui_event.modifiers() != Qt.NoModifier:
                return
            # Only handle left mouse button release
            if getattr(event, 'button', None) != 1:
                return
            
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Convert click coordinates to data coordinates
            click_time = pd.to_datetime(mdates.num2date(event.xdata))
            click_pressure = event.ydata
            
            # Find closest data point
            closest_point = self.find_closest_data_point(click_time, click_pressure)
            if closest_point is None:
                return
            
            timestamp, pressure = closest_point
            
            # Add visual marker
            self.add_spike_selection_marker(timestamp, pressure)
            
            # Pass to helper dialog
            self.spike_helper_dialog.set_selected_point(timestamp, pressure)
            
            logger.debug(f"Spike point selected: {timestamp}, {pressure:.3f} psi")
            
        except Exception as e:
            logger.error(f"Error handling spike point click: {e}")
        finally:
            QApplication.restoreOverrideCursor()
    
    def find_closest_data_point(self, click_time, click_pressure):
        """Find the closest data point to the click location"""
        try:
            if self.original_data is None or self.original_data.empty:
                return None
            
            # Get current time range
            start_time = self.start_date.dateTime().toPyDateTime()
            end_time = self.end_date.dateTime().toPyDateTime()
            
            # Filter data to current view
            mask = (self.original_data['timestamp_utc'] >= start_time) & \
                   (self.original_data['timestamp_utc'] <= end_time)
            view_data = self.original_data[mask]
            
            if view_data.empty:
                return None
            
            # Calculate distances (normalize time and pressure scales)
            time_values = view_data['timestamp_utc'].values
            pressure_values = view_data['pressure'].values
            
            # Normalize to [0, 1] scale for distance calculation
            time_range = (end_time - start_time).total_seconds()
            pressure_range = pressure_values.max() - pressure_values.min()
            
            if time_range == 0 or pressure_range == 0:
                return None
            
            time_norm = [(t - start_time).total_seconds() / time_range for t in time_values]
            pressure_norm = (pressure_values - pressure_values.min()) / pressure_range
            
            click_time_norm = (click_time - start_time).total_seconds() / time_range
            click_pressure_norm = (click_pressure - pressure_values.min()) / pressure_range
            
            # Calculate Euclidean distances
            distances = [(t - click_time_norm)**2 + (p - click_pressure_norm)**2 
                        for t, p in zip(time_norm, pressure_norm)]
            
            # Find closest point
            min_idx = distances.index(min(distances))
            closest_time = time_values[min_idx]
            closest_pressure = pressure_values[min_idx]
            
            return pd.to_datetime(closest_time), float(closest_pressure)
            
        except Exception as e:
            logger.error(f"Error finding closest data point: {e}")
            return None
    
    def add_spike_selection_marker(self, timestamp, pressure):
        """Add visual marker for selected spike point"""
        try:
            # Determine marker color (red for first, blue for second point)
            num_points = len(self.spike_selection_points)
            if num_points % 2 == 0:
                color = 'red'
                marker = 'o'
                label = 'Spike Start'
            else:
                color = 'blue'
                marker = 's'
                label = 'Spike End'
            
            # Add scatter point
            scatter = self.ax.scatter([timestamp], [pressure], 
                                   color=color, s=60, marker=marker, 
                                   alpha=0.9, zorder=15, 
                                   label=label if num_points < 2 else "")
            
            # Store for cleanup
            self.spike_selection_points.append(scatter)
            
            # Add preview line if this is the second point of a pair
            if num_points % 2 == 1 and len(self.spike_selection_points) >= 2:
                # Get the previous point
                prev_scatter = self.spike_selection_points[-2]
                prev_timestamp = prev_scatter.get_offsets()[0][0]
                prev_pressure = prev_scatter.get_offsets()[0][1]
                
                # Convert matplotlib date number back to datetime
                prev_timestamp = mdates.num2date(prev_timestamp)
                
                # Draw preview line
                line, = self.ax.plot([prev_timestamp, timestamp], [prev_pressure, pressure],
                                   'r--', linewidth=2, alpha=0.7, zorder=14)
                self.spike_preview_lines.append(line)
            
            # Update legend and redraw
            self.ax.legend(loc='best', fontsize=8)
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error adding spike selection marker: {e}")
    
    def clear_spike_selection_visuals(self):
        """Clear all spike selection visual elements"""
        try:
            # Remove scatter points
            for scatter in self.spike_selection_points:
                scatter.remove()
            self.spike_selection_points.clear()
            
            # Remove preview lines
            for line in self.spike_preview_lines:
                line.remove()
            self.spike_preview_lines.clear()
            
            # Update legend and redraw
            if hasattr(self, 'ax') and self.ax:
                self.ax.legend(loc='best', fontsize=8)
                self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error clearing spike selection visuals: {e}")
    
    def on_spike_parameters_changed(self, parameters):
        """Handle parameter changes from spike helper dialog"""
        try:
            # Update preview lines based on current pairs
            pairs = parameters.get('pairs', [])
            
            # Clear existing preview lines
            for line in self.spike_preview_lines:
                line.remove()
            self.spike_preview_lines.clear()
            
            # Add new preview lines for all pairs
            for pair in pairs:
                (t1, p1), (t2, p2) = pair
                line, = self.ax.plot([t1, t2], [p1, p2], 
                                   'orange', linewidth=2, alpha=0.7, 
                                   linestyle='--', zorder=14)
                self.spike_preview_lines.append(line)
            
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating spike parameters: {e}")
    
    def apply_spike_fixes(self):
        """Apply spike fixes from helper dialog"""
        try:
            if not self.spike_helper_dialog:
                return
            
            parameters = self.spike_helper_dialog.get_current_parameters()
            pairs = parameters.get('pairs', [])
            
            if not pairs:
                QMessageBox.warning(self, "No Selection", "Please select spike pairs first")
                return
            
            # Apply the same logic as the existing apply_manual_fixes method
            self.manual_spike_pairs = pairs
            self.apply_manual_fixes()
            
        except Exception as e:
            logger.error(f"Error applying spike fixes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply spike fixes: {str(e)}")
    
    def reset_spike_selection(self):
        """Reset spike selection"""
        try:
            self.clear_spike_selection_visuals()
            if self.spike_helper_dialog:
                self.spike_helper_dialog.clear_all()
            
        except Exception as e:
            logger.error(f"Error resetting spike selection: {e}")

    def keyPressEvent(self, event):
        """Handle key press events for spike selection"""
        try:
            # Handle ESC key to cancel spike selection
            if event.key() == Qt.Key_Escape and hasattr(self, 'spike_selection_mode') and self.spike_selection_mode:
                logger.info("ESC pressed, canceling spike selection")
                self.cancel_spike_point_selection()
                return
            
            # Call parent implementation for other keys
            super().keyPressEvent(event)
            
        except Exception as e:
            logger.error(f"Error in keyPressEvent: {e}")
            super().keyPressEvent(event)

    def show_help_dialog(self):
        """Show help dialog explaining the spike detection algorithm"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Spike Detection Algorithm - Help")
        help_dialog.setMinimumSize(600, 500)
        help_dialog.resize(700, 600)
        
        layout = QVBoxLayout(help_dialog)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Barologger Spike Detection & Correction Algorithm")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2E7D32; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Main content with sections
        content = """
<h3 style="color: #1976D2;">🔍 Algorithm Overview</h3>
<p>This tool automatically detects and corrects atmospheric pressure spikes in barologger data that can affect water level compensations. The algorithm uses a <strong>statistical outlier detection method</strong> with a rolling window approach.</p>

<h3 style="color: #1976D2;">⚙️ Algorithm Parameters</h3>
<ul>
<li><strong>Detection Window:</strong> 4 hours (16 data points for 15-minute intervals)</li>
<li><strong>Threshold:</strong> 3-sigma (3 standard deviations from local mean)</li>
<li><strong>Correction Window:</strong> 1 hour local average for replacement values</li>
</ul>

<h3 style="color: #1976D2;">🎯 How It Works</h3>
<ol>
<li><strong>Rolling Window Analysis:</strong> For each data point, examines surrounding 4-hour window</li>
<li><strong>Statistical Assessment:</strong> Calculates mean and standard deviation of surrounding data (excluding current point)</li>
<li><strong>Spike Detection:</strong> Identifies points that deviate more than 3σ from the local mean</li>
<li><strong>Value Correction:</strong> Replaces spike values with 1-hour local average</li>
<li><strong>Quality Flagging:</strong> Marks corrected points with 'spike_corrected' quality flag</li>
</ol>

<h3 style="color: #1976D2;">📊 What Gets Corrected</h3>
<p><strong>Spikes are detected when:</strong></p>
<p style="margin-left: 20px; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px;">
|pressure_point - local_mean| > 3.0 × local_standard_deviation
</p>

<h3 style="color: #1976D2;">✅ Benefits</h3>
<ul>
<li><strong>Preserves Data Integrity:</strong> Only corrects obvious outliers</li>
<li><strong>Conservative Approach:</strong> 3-sigma threshold minimizes false positives</li>
<li><strong>Maintains Trends:</strong> Uses local averaging for natural replacement values</li>
<li><strong>Full Traceability:</strong> Original values preserved, corrections tracked</li>
</ul>

<h3 style="color: #1976D2;">⚠️ Important Notes</h3>
<ul>
<li>This algorithm is specifically designed for <strong>atmospheric pressure spikes</strong></li>
<li>It does <strong>not</strong> correct legitimate pressure variations or trends</li>
<li>Original data is always preserved - corrections can be undone</li>
<li>Quality flags help identify which data points were modified</li>
</ul>

<h3 style="color: #1976D2;">🔧 Usage Tips</h3>
<ul>
<li>Review the "Show Corrections" plot to verify spike identification</li>
<li>Check the correction magnitude plot for reasonableness</li>
<li>Red 'X' markers show detected spikes on the original data</li>
<li>Use "Reset to Original" to undo changes if needed</li>
</ul>
        """
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setAlignment(Qt.AlignTop)
        content_label.setStyleSheet("""
            QLabel {
                background-color: white;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 8px;
                line-height: 1.4;
            }
        """)
        content_layout.addWidget(content_label)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        close_btn.clicked.connect(help_dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Show the dialog
        help_dialog.exec_()
    
    def on_hover(self, event):
        """Handle mouse hover events for barologger data"""
        if (event.inaxes != self.ax) and (self.hover_annotation is not None):
            try:
                self.hover_annotation.remove()
            except (NotImplementedError, AttributeError):
                self.hover_annotation.set_visible(False)
            self.hover_annotation = None
            self.canvas.draw_idle()
            return
            
        # Clear previous hover annotation
        if self.hover_annotation:
            try:
                self.hover_annotation.remove()
            except (NotImplementedError, AttributeError):
                self.hover_annotation.set_visible(False)
            self.hover_annotation = None

        found_point = False
                
        # Loop over all data series (scatter plots and lines)
        for artist, df in self.scatter_plots:
            if hasattr(artist, 'contains') and event.xdata is not None and event.ydata is not None:
                # Handle line plots - find the closest point to the cursor
                import matplotlib.dates as mdates
                import numpy as np
                
                # Get x and y data from the line
                line_times = mdates.date2num(df['timestamp_utc'].values)
                
                # Use appropriate pressure column
                if 'pressure_corrected' in df.columns:
                    line_pressures = df['pressure_corrected'].values
                else:
                    line_pressures = df['pressure'].values
                
                # Find the closest point in x direction (time)
                x_diff = abs(line_times - event.xdata)
                closest_idx = np.argmin(x_diff)
                
                # Check if the point is close enough (5 pixels in data coordinates)
                if x_diff[closest_idx] < 5/72:  # approx 5 pixels in data coordinates
                    point_data = df.iloc[closest_idx]
                    time_str = point_data['timestamp_utc'].strftime('%Y-%m-%d %H:%M')
                    pressure_val = line_pressures[closest_idx]
                    
                    text = f'Serial: {point_data["serial_number"]}\n' \
                           f'Date: {time_str}\n' \
                           f'Pressure: {pressure_val:.4f}'
                    
                    # Add source information if available
                    if 'data_source' in point_data:
                        text += f'\nSource: {point_data["data_source"]}'
                    
                    # Create the annotation at the point
                    self.hover_annotation = self.ax.annotate(text,
                        xy=(point_data['timestamp_utc'], pressure_val),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
                    found_point = True
                    break
        
        # Only redraw if we created a new annotation
        if found_point:
            self.canvas.draw_idle()
    
    def on_pick(self, event):
        """Handle pick events for barologger data points"""
        try:
            artist = event.artist
            
            # Find which data series this artist belongs to
            for plot_artist, df in self.scatter_plots:
                if plot_artist == artist:
                    if hasattr(event, 'ind'):
                        # Multiple points picked, use the first one
                        ind = event.ind[0] if hasattr(event.ind, '__iter__') else event.ind
                    else:
                        # Find closest point manually
                        import matplotlib.dates as mdates
                        import numpy as np
                        
                        line_times = mdates.date2num(df['timestamp_utc'].values)
                        if hasattr(event, 'mouseevent') and event.mouseevent.xdata:
                            x_diff = abs(line_times - event.mouseevent.xdata)
                            ind = np.argmin(x_diff)
                        else:
                            ind = 0
                    
                    point_data = df.iloc[ind]
                    
                    # Use appropriate pressure column
                    if 'pressure_corrected' in df.columns:
                        pressure_val = point_data['pressure_corrected']
                        pressure_type = "Corrected Pressure"
                    else:
                        pressure_val = point_data['pressure']
                        pressure_type = "Pressure"
                    
                    # Check if we're in spike selection mode
                    if self.spike_selection_mode and self.spike_helper_dialog:
                        # Integrate with spike selection workflow
                        timestamp = point_data['timestamp_utc']
                        
                        # Add visual marker for spike selection
                        self.add_spike_selection_marker(timestamp, pressure_val)
                        
                        # Pass to helper dialog (same as on_spike_point_click)
                        self.spike_helper_dialog.set_selected_point(timestamp, pressure_val)
                        
                        logger.debug(f"Spike point selected via pick: {timestamp}, {pressure_val:.3f}")
                        self.canvas.draw_idle()
                        
                    else:
                        # Normal annotation mode when not in spike selection
                        time_str = point_data['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S')
                        text = f'Serial: {point_data["serial_number"]}\n' \
                               f'Date: {time_str}\n' \
                               f'{pressure_type}: {pressure_val:.4f}\n'
                        
                        # Add additional information if available
                        if 'data_source' in point_data:
                            text += f'Source: {point_data["data_source"]}\n'
                        if 'correction_magnitude' in point_data:
                            text += f'Correction: {point_data["correction_magnitude"]:.4f}\n'
                        
                        # Create unique key for this annotation
                        key = f"{point_data['serial_number']}_{time_str}"
                        
                        # Remove existing annotation if it exists
                        if key in self.point_annotations:
                            try:
                                self.point_annotations[key].remove()
                            except:
                                pass
                            del self.point_annotations[key]
                        else:
                            # Create new annotation
                            annotation = self.ax.annotate(text,
                                xy=(point_data['timestamp_utc'], pressure_val),
                                xytext=(20, 20), textcoords='offset points',
                                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                                fontsize=9)
                            self.point_annotations[key] = annotation
                        
                        self.canvas.draw_idle()
                    break
                    
        except Exception as e:
            logger.error(f"Error in pick event: {e}")
    
    def on_key_press(self, event):
        """Handle key press events"""
        try:
            if event.key == 'c':
                # Clear all annotations
                for annotation in self.point_annotations.values():
                    try:
                        annotation.remove()
                    except:
                        pass
                self.point_annotations.clear()
                self.canvas.draw_idle()
            elif event.key == 'h':
                # Show help
                self.show_interaction_help()
                
        except Exception as e:
            logger.error(f"Error in key press event: {e}")
    
    def show_interaction_help(self):
        """Show help for plot interaction"""
        QMessageBox.information(self, "Plot Interaction Help", 
                              "• Hover over data points to see tooltips\n"
                              "• Click on data points to:\n"
                              "  - Select spike pairs (when in spike selection mode)\n"
                              "  - Create persistent annotations (in normal mode)\n"
                              "• Press 'c' to clear all annotations\n"
                              "• Press 'h' to show this help\n"
                              "• Use 'Manual Spike Fix' button to enter spike selection mode")
    
    def close_helper_dialog(self):
        """Close the helper dialog if it exists"""
        try:
            if self.spike_helper_dialog and self.spike_helper_dialog.isVisible():
                self.spike_helper_dialog.close()
                self.spike_helper_dialog = None
                self.spike_selection_mode = False
                logger.debug("Helper dialog closed")
        except Exception as e:
            logger.error(f"Error closing helper dialog: {e}")
    
    def cancel_dialog(self):
        """Cancel the dialog and close helper"""
        try:
            # Close helper dialog when canceling
            self.close_helper_dialog()
            
            # Clear any visual elements
            self.clear_spike_selection_visuals()
            
            # Call the standard reject method
            self.reject()
            
        except Exception as e:
            logger.error(f"Error in cancel_dialog: {e}")
            self.reject()  # Still cancel even if there's an error
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        try:
            # Close helper dialog when main dialog closes
            self.close_helper_dialog()
            
            # Clear any visual elements
            self.clear_spike_selection_visuals()
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            logger.error(f"Error in closeEvent: {e}")
            event.accept()  # Still close even if there's an error