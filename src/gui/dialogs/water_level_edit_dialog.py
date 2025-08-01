import logging
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor, SpanSelector
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QGroupBox, QCheckBox, QDateTimeEdit,
    QLabel, QPushButton, QMessageBox, QProgressBar, QSpinBox, QWidget, QApplication,
    QProgressDialog, QSplitter, QRadioButton  # Add QRadioButton here
)
from PyQt5.QtCore import Qt, QTimer  # Add QTimer here
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QAbstractSpinBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib import cm
import matplotlib.dates as mdates
import sqlite3
from typing import List
from .edit_tool_helper_dialog import SpikeFixHelperDialog, CompensationHelperDialog, BaselineHelperDialog
import numpy as np
import matplotlib.patches
import uuid
import copy

logger = logging.getLogger(__name__)

class WaterLevelEditDialog(QDialog):
    def __init__(self, transducer_data=None, manual_data=None, master_baro_data=None, parent=None, db_path=None):
        super().__init__(parent)
        
        # Store each data type separately
        self.transducer_data = transducer_data.copy() if transducer_data is not None else pd.DataFrame()
        self.manual_data = manual_data.copy() if manual_data is not None else pd.DataFrame()
        self.master_baro_data = master_baro_data.copy() if master_baro_data is not None else pd.DataFrame()
        
        # Add a source marker to transducer data to correctly identify it later
        if not self.transducer_data.empty:
            self.transducer_data['data_source_type'] = 'Transducer'
        
        # Rename for backwards compatibility
        self.baro_data = self.master_baro_data
        
        # For backwards compatibility, create a combined plot_data for visualization
        self.plot_data = pd.concat([self.transducer_data, self.manual_data])
        
        # Store the database path
        self.db_path = db_path
        
        # Initialize data type selection early (before UI setup)
        self.data_type = 'water_level'  # or 'temperature'
        
        # Add additional computed columns if needed
        if not self.transducer_data.empty:
            columns_to_check = [
                'water_level_master_corrected',
                'water_level_level_corrected',
                'water_level_spike_corrected'
            ]
            
            for col in columns_to_check:
                if col not in self.transducer_data.columns:
                    self.transducer_data[col] = self.transducer_data['water_level']
            
            if 'spike_flag' not in self.transducer_data.columns:
                self.transducer_data['spike_flag'] = 'none'
                
            # Initialize modification flag columns
            if 'baro_flag_mod' not in self.transducer_data.columns:
                self.transducer_data['baro_flag_mod'] = self.transducer_data['baro_flag']
                
            if 'level_flag_mod' not in self.transducer_data.columns:
                self.transducer_data['level_flag_mod'] = self.transducer_data['level_flag']
                
            if 'level_flag_baro_mod' not in self.transducer_data.columns:
                self.transducer_data['level_flag_baro_mod'] = self.transducer_data['level_flag']
                
            # Also initialize in plot_data for consistency
            if 'baro_flag_mod' not in self.plot_data.columns:
                self.plot_data['baro_flag_mod'] = self.plot_data['baro_flag'] if 'baro_flag' in self.plot_data.columns else 'standard'
                
            if 'level_flag_mod' not in self.plot_data.columns:
                self.plot_data['level_flag_mod'] = self.plot_data['level_flag'] if 'level_flag' in self.plot_data.columns else 'standard'
                
            if 'level_flag_baro_mod' not in self.plot_data.columns:
                self.plot_data['level_flag_baro_mod'] = self.plot_data['level_flag'] if 'level_flag' in self.plot_data.columns else 'standard'
            
            # Add temperature tracking columns
            if 'temperature' in self.plot_data.columns:
                if 'temperature_spike_corrected' not in self.plot_data.columns:
                    self.plot_data['temperature_spike_corrected'] = self.plot_data['temperature'].copy()
                if 'temperature_spike_flag' not in self.plot_data.columns:
                    self.plot_data['temperature_spike_flag'] = 'none'
        
        self.selected_data = None  # Store selected data points
        
        # Cache for grouped data - will be computed from baro data
        self._baro_groups = None   # For non-master baro ranges (standard compensation)
        self._master_baro_groups = None  # For ranges where master baro is present
        
        # Add storage for annotations and selected points
        self.hover_annotation = None
        self.selected_points = []  # Will hold keys (tuple of scatter id and point index)
        self.point_annotations = {}  # Map from key to annotation
        self.scatter_plots = []      # List of tuples: (scatter_object, corresponding_data_dataframe)
        self.compensation_line_handles = []  # For storing the compensation corrected line(s)
        self.baseline_preview_line = None  # For storing baseline preview line
        
        # Pre-calculate data groups if needed (for performance)
        self._calculate_groups()
        
        # Initialize edit tracking system
        self.session_id = str(uuid.uuid4())
        self.edit_history = {
            'session_id': self.session_id,
            'edits': []
        }
        
        # Store original session data for reset functionality
        self.original_session_data = {
            'transducer_data': self.transducer_data.copy() if not self.transducer_data.empty else pd.DataFrame(),
            'manual_data': self.manual_data.copy() if not self.manual_data.empty else pd.DataFrame(),
            'plot_data': self.plot_data.copy() if not self.plot_data.empty else pd.DataFrame()
        }
        
        # Track active instances
        self.active_instances = {}
        
        # Add version debug info
        logger.info("="*50)
        logger.info("WATER LEVEL EDIT DIALOG - INITIALIZATION DEBUG")
        logger.info("="*50)
        logger.info(f"Dialog initialization started - VERSION: 2025-07-03-DEBUG-v1.1")
        logger.info(f"File path: {__file__}")
        
        # Check if we have the new methods
        has_protocol_method = hasattr(self.__class__, 'open_protocol_feedback_dialog')
        has_help_method = hasattr(self.__class__, 'open_help_dialog')
        logger.info(f"Has protocol feedback method: {has_protocol_method}")
        logger.info(f"Has help dialog method: {has_help_method}")
        
        self.setup_ui()
        self.setup_initial_dates()
        self.update_plot()  # Initial plot
        
        # Initialize Google Drive service and feedback button visibility
        self.drive_service = None
        self.user_name = None
        logger.info("About to initialize feedback system...")
        self._initialize_feedback_system()
        logger.info("Feedback system initialization completed")
        
        # Add selection mode attributes
        self.selection_mode = False
        self.selecting_for = None
        self.click_cid = None
        
        # Add gap detection attributes (from water_level_plot_handler)
        self.gap_highlight_enabled = True
        self.gap_color = "#ffcccb"  # Light red background for gaps - more visible
        self.gap_alpha = 0.7
        self.gap_threshold = timedelta(minutes=20)  # Gap threshold (> 15 min sample interval)

    def _calculate_groups(self):
        """Pre-calculate groups for both baro flags from separate baro data"""
        try:
            # Initialize empty groups
            self._baro_groups = []
            self._master_baro_groups = []
            
            # Check if we're using the standard baro_data or the new master_baro_data
            df_to_use = self.transducer_data
            
            if df_to_use.empty:
                logger.debug("No data available for grouping")
                return
                
            # Check if baro_flag column exists
            if 'baro_flag' not in df_to_use.columns:
                logger.debug("No baro_flag column found in data")
                return
                
            # Ensure data is sorted by timestamp
            df_sorted = df_to_use.sort_values('timestamp_utc')
            
            # Find groups where baro_flag is not 'master' (for non-master highlighting)
            non_master_mask = df_sorted['baro_flag'] != 'master'
            if non_master_mask.any():
                # Get indices where status changes
                status_changes = non_master_mask.diff().fillna(False).astype(bool)
                change_indices = status_changes[status_changes].index.tolist()
                
                # Add the last index if it's not already included
                if len(change_indices) % 2 != 0:
                    change_indices.append(df_sorted.index[-1])
                
                # Create groups of consecutive non-master ranges
                for i in range(0, len(change_indices), 2):
                    if i+1 < len(change_indices):
                        start_idx = change_indices[i]
                        end_idx = change_indices[i+1]
                        group_data = df_sorted.loc[start_idx:end_idx]
                        if not group_data.empty:
                            self._baro_groups.append(group_data)
                
            # Find groups where baro_flag is 'master' (for master highlighting)
            master_mask = df_sorted['baro_flag'] == 'master'
            if master_mask.any():
                # Similar logic for master groups
                status_changes = master_mask.diff().fillna(False).astype(bool)
                change_indices = status_changes[status_changes].index.tolist()
                
                if len(change_indices) % 2 != 0:
                    change_indices.append(df_sorted.index[-1])
                
                for i in range(0, len(change_indices), 2):
                    if i+1 < len(change_indices):
                        start_idx = change_indices[i]
                        end_idx = change_indices[i+1]
                        group_data = df_sorted.loc[start_idx:end_idx]
                        if not group_data.empty:
                            self._master_baro_groups.append(group_data)
                            
            logger.debug(f"Found {len(self._baro_groups)} non-master baro groups and {len(self._master_baro_groups)} master baro groups")
                
        except Exception as e:
            logger.error(f"Error pre-calculating groups: {e}")

    def identify_data_gaps(self, df: pd.DataFrame) -> List:
        """
        Identify gaps in time series data where the interval between samples exceeds the threshold.
        
        Args:
            df: DataFrame with a 'timestamp_utc' column
            
        Returns:
            List of (start_time, end_time) tuples representing gaps
        """
        if df is None or df.empty or 'timestamp_utc' not in df.columns:
            return []
            
        # Sort by timestamp to ensure chronological order
        sorted_df = df.sort_values('timestamp_utc').reset_index(drop=True)
        
        # Calculate time differences between consecutive points
        time_diffs = sorted_df['timestamp_utc'].diff()
        
        # Find indices where the time difference exceeds the threshold
        gap_indices = time_diffs[time_diffs > self.gap_threshold].index.tolist()
        
        gaps = []
        for idx in gap_indices:
            gap_start = sorted_df.loc[idx-1, 'timestamp_utc']
            gap_end = sorted_df.loc[idx, 'timestamp_utc']
            gaps.append((gap_start, gap_end))
            
        return gaps
    
    def highlight_data_gaps(self, gaps: List, y_min: float, y_max: float):
        """
        Add background highlighting for data gaps.
        
        Args:
            gaps: List of (start_time, end_time) tuples representing gaps
            y_min: Minimum y value for the plot
            y_max: Maximum y value for the plot
        """
        if not gaps or not self.gap_highlight_enabled:
            return
            
        for gap_start, gap_end in gaps:
            # Add a rectangle spanning the gap with a distinctive color
            rect = plt.Rectangle(
                (mdates.date2num(gap_start), y_min),
                mdates.date2num(gap_end) - mdates.date2num(gap_start),
                y_max - y_min,
                color=self.gap_color,
                alpha=self.gap_alpha,
                zorder=-100  # Place behind other plot elements
            )
            self.ax.add_patch(rect)
    
    def toggle_gap_highlighting(self, enabled: bool):
        """Enable or disable the gap highlighting feature"""
        self.gap_highlight_enabled = enabled
        self.update_plot()  # Refresh the plot
    
    def toggle_gap_highlighting_from_checkbox(self, state):
        """Toggle gap highlighting from checkbox state"""
        show_gaps = (state == 2)  # 2 = checked, 0 = unchecked
        self.toggle_gap_highlighting(show_gaps)
    
    def on_data_type_changed(self):
        """Handle data type selection change"""
        try:
            if self.temperature_radio.isChecked():
                self.data_type = 'temperature'
                # Disable non-applicable tools for temperature
                self.compensation_btn.setEnabled(False)
                self.adjust_baseline_btn.setEnabled(False)
                self.show_master_baro.setEnabled(False)
                self.show_baro_flag.setEnabled(False)
                self.show_level_flag.setEnabled(False)
                
                # Change button colors to indicate disabled state
                self.compensation_btn.setStyleSheet("QPushButton { background-color: #d3d3d3; color: #888888; }")
                self.adjust_baseline_btn.setStyleSheet("QPushButton { background-color: #d3d3d3; color: #888888; }")
                
                # Keep spike fix enabled
                self.fix_spikes_btn.setEnabled(True)
            else:
                self.data_type = 'water_level'
                # Enable all tools for water level
                self.compensation_btn.setEnabled(True)
                self.adjust_baseline_btn.setEnabled(True)
                self.show_master_baro.setEnabled(True)
                self.show_baro_flag.setEnabled(True)
                self.show_level_flag.setEnabled(True)
                
                # Reset button colors to default state
                self.compensation_btn.setStyleSheet("")
                self.adjust_baseline_btn.setStyleSheet("")
                self.fix_spikes_btn.setEnabled(True)
            
            # Close any active helper dialogs
            if hasattr(self, 'spike_helper') and self.spike_helper:
                self.spike_helper.close()
                self.spike_helper = None
            if hasattr(self, 'compensation_helper') and self.compensation_helper:
                self.compensation_helper.close()
                self.compensation_helper = None
            if hasattr(self, 'baseline_helper') and self.baseline_helper:
                self.baseline_helper.close()
                self.baseline_helper = None
            
            # Update window title
            if self.data_type == 'temperature':
                self.setWindowTitle("Edit Temperature Data")
            else:
                self.setWindowTitle("Edit Water Level Data")
            
            # Update the plot
            self.update_plot()
            
        except Exception as e:
            logger.error(f"Error changing data type: {e}")

    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Edit Water Level Data")
        self.resize(1400, 900)  # Larger size for better visualization
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Create compact control panel
        controls_panel = self.create_compact_controls_panel()
        main_layout.addWidget(controls_panel)
        
        # Create plot section
        plot_widget = self.create_plot_section()
        main_layout.addWidget(plot_widget)
        
        # Create bottom buttons
        button_layout = self.create_bottom_buttons()
        main_layout.addLayout(button_layout)
        
        
        # Setup span selector
        self.span_selector = SpanSelector(
            self.ax, self.on_span_select, 'horizontal',
            useblit=True, props=dict(alpha=0.2, facecolor='red'),
            interactive=True
        )
        
        # Connect to axis events to update formatting when zooming/panning
        self.ax.callbacks.connect('xlim_changed', self._on_xlim_changed)
    
    def create_compact_controls_panel(self):
        """Create a compact horizontal control panel"""
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(12)
        
        # Data Type Selection section
        data_type_group = QGroupBox("Data Type")
        data_type_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        data_type_layout = QHBoxLayout(data_type_group)
        data_type_layout.setContentsMargins(12, 16, 12, 12)
        data_type_layout.setSpacing(8)
        
        # Add radio buttons for data type selection
        self.water_level_radio = QRadioButton("Water Level")
        self.temperature_radio = QRadioButton("Temperature")
        self.water_level_radio.setChecked(True)  # Default to water level
        
        # Connect signals
        self.water_level_radio.toggled.connect(self.on_data_type_changed)
        
        data_type_layout.addWidget(self.water_level_radio)
        data_type_layout.addWidget(self.temperature_radio)
        
        controls_layout.addWidget(data_type_group)
        
        # Data Filters section (compact)
        filters_group = QGroupBox("Data Filters")
        filters_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        filters_layout = QHBoxLayout(filters_group)
        filters_layout.setContentsMargins(12, 16, 12, 12)
        filters_layout.setSpacing(8)
        
        # Add filter checkboxes horizontally
        self.show_master_baro = QCheckBox("Master Baro")
        self.show_baro_flag = QCheckBox("Baro Flags")
        self.show_level_flag = QCheckBox("Level Flags")
        self.show_gaps_cb = QCheckBox("Show Data Gaps")
        
        # Set checked by default
        self.show_master_baro.setChecked(False)
        self.show_baro_flag.setChecked(True)
        self.show_level_flag.setChecked(True)
        self.show_gaps_cb.setChecked(True)  # Enabled by default
        
        # Add tooltips
        self.show_gaps_cb.setToolTip("Show colored background for data gaps")
        
        # Connect checkbox signals
        self.show_master_baro.stateChanged.connect(self.update_plot)
        self.show_baro_flag.stateChanged.connect(self.update_plot)
        self.show_level_flag.stateChanged.connect(self.update_plot)
        self.show_gaps_cb.stateChanged.connect(self.toggle_gap_highlighting_from_checkbox)
        
        filters_layout.addWidget(self.show_master_baro)
        filters_layout.addWidget(self.show_baro_flag)
        filters_layout.addWidget(self.show_level_flag)
        filters_layout.addWidget(self.show_gaps_cb)
        
        # Edit Tools section (compact)
        edit_group = QGroupBox("Edit Tools")
        edit_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        edit_layout = QHBoxLayout(edit_group)
        edit_layout.setContentsMargins(12, 16, 12, 12)
        edit_layout.setSpacing(8)
        
        # Add edit tool buttons with modern styling
        self.fix_spikes_btn = QPushButton("Fix Spikes")
        self.compensation_btn = QPushButton("Compensation")
        self.adjust_baseline_btn = QPushButton("Adjust Baseline")
        self.calculator_btn = QPushButton("Calculator")
        
        # Connect edit tool buttons
        self.fix_spikes_btn.clicked.connect(self.fix_spikes)
        self.compensation_btn.clicked.connect(self.apply_compensation)
        self.adjust_baseline_btn.clicked.connect(self.adjust_baseline)
        self.calculator_btn.clicked.connect(self.open_calculator)
        
        # Apply modern button styling
        for btn in [self.fix_spikes_btn, self.compensation_btn, self.adjust_baseline_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    border: 1px solid #0056b3;
                    border-radius: 6px;
                    background-color: #007bff;
                    color: white;
                    font-weight: 500;
                    min-height: 28px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                    border-color: #004085;
                }
                QPushButton:pressed {
                    background-color: #004085;
                    border-color: #002752;
                }
            """)
        
        # Set calculator button to secondary style
        self.calculator_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 500;
                min-height: 28px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
                border-color: #6c757d;
            }
        """)
        
        self.calculator_btn.setIcon(QIcon.fromTheme("accessories-calculator"))
        self.calculator_btn.setToolTip("Open system calculator")
        
        edit_layout.addWidget(self.fix_spikes_btn)
        edit_layout.addWidget(self.compensation_btn)
        edit_layout.addWidget(self.adjust_baseline_btn)
        edit_layout.addWidget(self.calculator_btn)
        
        # Time Range section (compact)
        time_group = QGroupBox("Time Range")
        time_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        time_layout = QHBoxLayout(time_group)
        time_layout.setContentsMargins(12, 16, 12, 12)
        time_layout.setSpacing(8)
        
        # Start date/time (more compact)
        start_label = QLabel("Start:")
        start_label.setMinimumWidth(35)
        self.start_date = QDateTimeEdit()
        self.start_date.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_date.setCalendarPopup(True)
        self.start_date.dateTimeChanged.connect(self.on_manual_date_changed)
        self.start_date.setMaximumWidth(140)
        
        # Add small button for setting to first point
        self.start_min_btn = QPushButton("⏮")
        self.start_min_btn.setToolTip("Set to earliest data point")
        self.start_min_btn.setFixedSize(22, 22)
        self.start_min_btn.clicked.connect(self.set_start_to_first_point)
        self.start_min_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #6c757d;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        # End date/time (more compact)
        end_label = QLabel("End:")
        end_label.setMinimumWidth(30)
        self.end_date = QDateTimeEdit()
        self.end_date.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_date.setCalendarPopup(True)
        self.end_date.dateTimeChanged.connect(self.on_manual_date_changed)
        self.end_date.setMaximumWidth(140)
        
        # Add small button for setting to last point
        self.end_max_btn = QPushButton("⏭")
        self.end_max_btn.setToolTip("Set to latest data point")
        self.end_max_btn.setFixedSize(22, 22)
        self.end_max_btn.clicked.connect(self.set_end_to_last_point)
        self.end_max_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #6c757d;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        # Action buttons (compact)
        self.zoom_to_selection_btn = QPushButton("Zoom")
        self.zoom_to_selection_btn.clicked.connect(self.zoom_to_selected_data)
        self.zoom_to_selection_btn.setToolTip("Zoom to selected data range")
        
        self.full_range_btn = QPushButton("Full Range")
        self.full_range_btn.setToolTip("Set date range to show all available data")
        self.full_range_btn.clicked.connect(self.set_full_date_range)
        
        # Style the time range action buttons
        for btn in [self.zoom_to_selection_btn, self.full_range_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    border: 1px solid #6c757d;
                    border-radius: 4px;
                    background-color: #f8f9fa;
                    color: #495057;
                    font-weight: 500;
                    min-height: 24px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                    border-color: #495057;
                }
                QPushButton:pressed {
                    background-color: #dee2e6;
                }
            """)
        
        time_layout.addWidget(start_label)
        time_layout.addWidget(self.start_date)
        time_layout.addWidget(self.start_min_btn)
        time_layout.addWidget(end_label)
        time_layout.addWidget(self.end_date)
        time_layout.addWidget(self.end_max_btn)
        time_layout.addWidget(self.zoom_to_selection_btn)
        time_layout.addWidget(self.full_range_btn)
        
        # DEBUG: Button creation
        logger.info("Creating Protocol Feedback button...")
        
        # Protocol Feedback button (positioned in upper right)
        self.protocol_feedback_btn = QPushButton("📋 Protocol Feedback")
        self.protocol_feedback_btn.setToolTip("Submit feedback on water levels processing protocols")
        self.protocol_feedback_btn.setVisible(False)  # Initially hidden, shown when Drive service available
        self.protocol_feedback_btn.clicked.connect(self.open_protocol_feedback_dialog)
        self.protocol_feedback_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a2d91;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        logger.info(f"Protocol Feedback button created: {self.protocol_feedback_btn}")
        
        # DEBUG: Help button creation
        logger.info("Creating Help button...")
        
        # Help button for comprehensive user guidance
        self.help_btn = QPushButton("❓ Help")
        self.help_btn.setToolTip("Open comprehensive help and user guide for this dialog")
        self.help_btn.clicked.connect(self.open_help_dialog)
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        logger.info(f"Help button created: {self.help_btn}")
        
        # DEBUG: User Notes button creation
        logger.info("Creating User Notes button...")
        
        # User Notes button for data analysis notes
        self.user_notes_btn = QPushButton("📝 Notes")
        self.user_notes_btn.setToolTip("Add notes about water level data analysis\n\n💡 Tip: Select a time range by dragging on the plot first - the selection will be automatically used in the notes dialog!")
        self.user_notes_btn.clicked.connect(self.open_user_notes_dialog)
        self.user_notes_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        logger.info(f"User Notes button created: {self.user_notes_btn}")
        
        # Create vertical layout for feedback and help buttons (stacked)
        buttons_group = QGroupBox()
        buttons_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        buttons_layout = QVBoxLayout(buttons_group)
        buttons_layout.setContentsMargins(4, 4, 4, 4)
        buttons_layout.setSpacing(4)
        
        logger.info("Adding Protocol Feedback button to vertical stack...")
        buttons_layout.addWidget(self.protocol_feedback_btn)
        
        logger.info("Adding User Notes button to vertical stack...")
        buttons_layout.addWidget(self.user_notes_btn)
        
        logger.info("Adding Help button to vertical stack...")
        buttons_layout.addWidget(self.help_btn)
        
        # DEBUG: Adding buttons to layout
        logger.info("Adding button group to controls layout...")
        
        # Add all groups to main layout
        controls_layout.addWidget(filters_group)
        controls_layout.addWidget(edit_group)
        controls_layout.addWidget(time_group)
        controls_layout.addWidget(buttons_group)
        controls_layout.addStretch()
        
        logger.info(f"Controls layout widget count: {controls_layout.count()}")
        logger.info(f"Protocol Feedback button visible: {self.protocol_feedback_btn.isVisible()}")
        logger.info(f"Help button visible: {self.help_btn.isVisible()}")
        
        return controls_widget
    
    def create_plot_section(self):
        """Create the plot section"""
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(4)
        
        plot_group = QGroupBox("Data Editor")
        plot_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        plot_content_layout = QVBoxLayout(plot_group)
        plot_content_layout.setContentsMargins(8, 16, 8, 8)
        plot_content_layout.setSpacing(4)
        
        self.figure = Figure(figsize=(14, 10))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Connect event handlers
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        # Disconnect the default home button and connect our custom handler
        home_btn = self.toolbar.actions()[0]  # Home button is the first action
        home_btn.triggered.disconnect()  # Disconnect default behavior
        home_btn.triggered.connect(self.on_home_button_clicked)
        
        # Add a separator and the Reset All Edits button
        self.toolbar.addSeparator()
        self.reset_all_edits_action = self.toolbar.addAction("Reset All Edits")
        self.reset_all_edits_action.setToolTip("Reset all edits made in this session")
        self.reset_all_edits_action.triggered.connect(self.reset_all_edits)
        
        plot_content_layout.addWidget(self.toolbar)
        plot_content_layout.addWidget(self.canvas)
        
        plot_layout.addWidget(plot_group)
        
        return plot_widget
    
    def create_bottom_buttons(self):
        """Create the bottom action buttons"""
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(8, 4, 8, 8)
        
        self.apply_changes_btn = QPushButton("Apply Changes")
        self.apply_changes_btn.clicked.connect(self.apply_changes)
        self.apply_changes_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #1e7e34;
                border-radius: 6px;
                background-color: #28a745;
                color: white;
                font-weight: 500;
                min-height: 32px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #218838;
                border-color: #1c7430;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
                border-color: #1a6e29;
            }
        """)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #6c757d;
                border-radius: 6px;
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 500;
                min-height: 32px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #495057;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
                border-color: #343a40;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_changes_btn)
        button_layout.addWidget(self.cancel_btn)
        
        return button_layout

    def setup_initial_dates(self):
        """Set initial date range from data without initializing the span selector"""
        if not self.plot_data.empty:
            min_date = self.plot_data['timestamp_utc'].min()
            max_date = self.plot_data['timestamp_utc'].max()
            self.start_date.setDateTime(min_date)
            self.end_date.setDateTime(max_date)
            # Don't initialize span selector - leave it hidden until user action

    def on_manual_date_changed(self):
        """Only respond to manual date changes if they weren't triggered by span selection"""
        if not self.start_date.signalsBlocked() and not self.end_date.signalsBlocked():
            try:
                start_dt = self.start_date.dateTime().toPyDateTime()
                end_dt = self.end_date.dateTime().toPyDateTime()
                
                if start_dt >= end_dt:
                    return
                
                # Store selected data (add this block)
                mask = (self.plot_data['timestamp_utc'] >= start_dt) & \
                       (self.plot_data['timestamp_utc'] <= end_dt)
                self.selected_data = self.plot_data[mask].copy()
                
                # Add debug logging
                logger.debug(f"Manual date selection: {start_dt} to {end_dt}")
                logger.debug(f"Selected data points: {len(self.selected_data)}")
                if not self.selected_data.empty:
                    logger.debug(f"Data sources in selection: {self.selected_data['data_source'].unique()}")
                
                self.ax.set_xlim(start_dt, end_dt)
                self.canvas.draw()
            except Exception as e:
                logger.error(f"Error handling date change: {e}")

    def on_home_clicked(self):
        """Handle our custom 'home' function - reset date selectors and plot"""
        try:
            if not self.plot_data.empty:
                min_date = self.plot_data['timestamp_utc'].min()
                max_date = self.plot_data['timestamp_utc'].max()
                self.start_date.setDateTime(min_date)
                self.end_date.setDateTime(max_date)
                self.ax.set_xlim(min_date, max_date)
                
                # Update master baro data if it's visible
                if self.show_master_baro.isChecked() and hasattr(self, 'ax2') and self.ax2 is not None:
                    self.ax2.remove()
                    self.ax2 = None
                    self._plot_master_baro_data()
                    
                self.canvas.draw()
        except Exception as e:
            logger.error(f"Error handling home click: {e}")

    def on_home_button_clicked(self):
        """Handle the toolbar's home button click - reset plot view to show FULL DATA RANGE without changing date selectors"""
        try:
            if not self.plot_data.empty:
                # Get the full data range
                min_date = None
                max_date = None
                
                # Get min/max from all data sources
                if not self.transducer_data.empty:
                    min_date = self.transducer_data['timestamp_utc'].min()
                    max_date = self.transducer_data['timestamp_utc'].max()
                
                if not self.manual_data.empty:
                    manual_min = self.manual_data['timestamp_utc'].min()
                    manual_max = self.manual_data['timestamp_utc'].max()
                    
                    if min_date is None or manual_min < min_date:
                        min_date = manual_min
                        
                    if max_date is None or manual_max > max_date:
                        max_date = manual_max
                
                if min_date is None or max_date is None:
                    logger.warning("No data available to set full range")
                    return
                
                # Set the plot to show full data range without changing the selected dates
                self.ax.set_xlim(min_date, max_date)
                self.ax.relim()  # Recalculate limits
                self.ax.autoscale(axis='y')  # Auto-scale only y axis
                
                # Update master baro data if it's visible
                if self.show_master_baro.isChecked() and hasattr(self, 'ax2') and self.ax2 is not None:
                    self.ax2.remove()
                    self.ax2 = None
                    self._plot_master_baro_data()
                    
                self.canvas.draw()
                logger.debug(f"Reset plot view to show full data range from {min_date} to {max_date}, keeping date selectors unchanged")
        except Exception as e:
            logger.error(f"Error handling home button click: {e}")

    def on_span_select(self, xmin, xmax):
        """Handle span selection without changing the plot zoom"""
        try:
            # Convert matplotlib dates to datetime and make them timezone-naive
            start = matplotlib.dates.num2date(xmin).replace(tzinfo=None)
            end = matplotlib.dates.num2date(xmax).replace(tzinfo=None)
            
            # Store selected data
            mask = (self.plot_data['timestamp_utc'] >= start) & \
                   (self.plot_data['timestamp_utc'] <= end)
            self.selected_data = self.plot_data[mask].copy()
            
            # Update date widgets without triggering the zoom
            self.start_date.blockSignals(True)
            self.end_date.blockSignals(True)
            self.start_date.setDateTime(start)
            self.end_date.setDateTime(end)
            self.start_date.blockSignals(False)
            self.end_date.blockSignals(False)
            
            # Don't change the zoom level - the user can use "Zoom to Selected Data" if they want to change view
            
        except Exception as e:
            logger.error(f"Error in span selection: {e}")
    
    def _setup_date_axis_formatting(self):
        """Setup intelligent date axis formatting based on data timespan"""
        try:
            # Get current time span
            xlim = self.ax.get_xlim()
            if len(xlim) < 2:
                return
                
            start_date = matplotlib.dates.num2date(xlim[0])
            end_date = matplotlib.dates.num2date(xlim[1])
            total_days = (end_date - start_date).days
            
            # Choose format based on timespan - intelligent formatting
            if total_days <= 7:
                # Less than a week - show month/day
                date_format = '%m/%d'
                locator = mdates.DayLocator(interval=1)
            elif total_days <= 31:
                # Less than a month - show month/day
                date_format = '%m/%d'
                locator = mdates.DayLocator(interval=max(1, total_days // 8))
            elif total_days <= 365:
                # Less than a year - show month/year
                date_format = '%m/%y'
                locator = mdates.MonthLocator()
            else:
                # More than a year - show year only
                date_format = '%Y'
                locator = mdates.MonthLocator(interval=max(1, total_days // 365))
            
            # Apply formatting
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            self.ax.xaxis.set_major_locator(locator)
            
            # Improve label spacing and rotation
            self.ax.tick_params(axis='x', rotation=45, labelsize=9)
            
            # Add minor ticks for better granularity
            if total_days <= 31:
                minor_locator = mdates.DayLocator()
                self.ax.xaxis.set_minor_locator(minor_locator)
            
            # Ensure labels don't overlap
            plt.setp(self.ax.xaxis.get_majorticklabels(), ha='right')
            
            # Adjust layout to prevent label cutoff
            self.figure.tight_layout()
            
            # Set up coordinate navigation to show full date/time
            self.setup_coordinate_navigation()
            
        except Exception as e:
            logger.warning(f"Error setting up date axis formatting: {e}")
            # Fallback to simple format
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            self.ax.tick_params(axis='x', rotation=45)
    
    def _on_xlim_changed(self, ax):
        """Callback when x-axis limits change (zoom/pan) to update date formatting"""
        try:
            # Small delay to avoid excessive updates during interactive operations
            if hasattr(self, '_format_timer'):
                self._format_timer.stop()
            
            self._format_timer = QTimer()
            self._format_timer.setSingleShot(True)
            self._format_timer.timeout.connect(lambda: self._setup_date_axis_formatting())
            self._format_timer.start(200)  # 200ms delay
        except Exception as e:
            logger.debug(f"Error in xlim changed callback: {e}")
    
    def setup_coordinate_navigation(self):
        """Set up coordinate navigation to show full date/time in toolbar coordinates"""
        try:
            # Create a custom format function for coordinates
            def format_coord(x, y):
                # Convert matplotlib date number to datetime
                try:
                    dt = matplotlib.dates.num2date(x)
                    date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    return f'Date: {date_str}, Level: {y:.3f}'
                except:
                    return f'x={x:.3f}, y={y:.3f}'
            
            # Apply the custom format to the axis
            self.ax.format_coord = format_coord
            
        except Exception as e:
            logger.warning(f"Error setting up coordinate navigation: {e}")

    def zoom_to_selected_data(self):
        """Zoom the plot to the selected date range without affecting other settings"""
        try:
            # Get the date range from the date controls
            start = self.start_date.dateTime().toPyDateTime()
            end = self.end_date.dateTime().toPyDateTime()
            
            if start >= end:
                QMessageBox.warning(self, "Warning", "Invalid date range selected")
                return
                
            # Update the view limits for the X axis only
            current_ylim = self.ax.get_ylim()  # Preserve current y limits
            self.ax.set_xlim(start, end)
            self.ax.set_ylim(current_ylim)  # Restore y limits
            
            # Update master baro data if it's visible, maintain the x limits
            if self.show_master_baro.isChecked() and hasattr(self, 'ax2') and self.ax2 is not None:
                current_y2lim = self.ax2.get_ylim()  # Preserve secondary y limits if they exist
                self.ax2.remove()
                self.ax2 = None
                self._plot_master_baro_data()
                if hasattr(self, 'ax2') and self.ax2 is not None:
                    self.ax2.set_ylim(current_y2lim)  # Restore secondary y limits
            
            # Update date formatting for new zoom level
            self._setup_date_axis_formatting()
                
            self.canvas.draw()
            logger.debug(f"Zoomed to selected data range: {start} to {end}")
            
        except Exception as e:
            logger.error(f"Error zooming to selected data: {e}")
            QMessageBox.warning(self, "Error", f"Failed to zoom: {str(e)}")

    def update_plot(self):
        """Update the plot based on current filters and selection"""
        try:
            self.ax.clear()
            self.scatter_plots = []  # Reset list at each update
            
            # Clear any secondary axis if it exists
            if hasattr(self, 'ax2') and self.ax2 is not None:
                self.ax2.remove()
                self.ax2 = None
            
            # Plot transducer data first (if exists)
            if not self.transducer_data.empty:
                # Plot the flag areas if enabled (only for water level mode)
                if self.data_type == 'water_level':
                    if self.show_baro_flag.isChecked():
                        self._plot_baro_flags()
                    
                    if self.show_level_flag.isChecked():
                        self._plot_level_flags()
                
                # Plot transducer data as lines (not pickable)
                for well in self.transducer_data['well_number'].unique():
                    well_mask = self.transducer_data['well_number'] == well
                    well_data = self.transducer_data[well_mask]
                    
                    # Determine which column to display based on data type
                    if self.data_type == 'temperature':
                        y_label = 'Temperature (°C)'
                        data_type_label = 'Temperature'
                        
                        # Always plot the original temperature line first
                        if 'temperature' in well_data.columns:
                            original_line, = self.ax.plot(well_data['timestamp_utc'], 
                                           well_data['temperature'], 
                                           '-', color='lightcoral', label=f'Well {well} (Original Temperature)',
                                           alpha=0.6,
                                           zorder=2,
                                           picker=5)
                            self.scatter_plots.append((original_line, well_data))
                        
                        # Plot the corrected temperature line if it exists and differs from original
                        if 'temperature_spike_corrected' in well_data.columns:
                            # Check if there are any actual corrections (different from original)
                            has_corrections = False
                            if 'temperature_spike_flag' in well_data.columns:
                                has_corrections = (well_data['temperature_spike_flag'] != 'none').any()
                            
                            if has_corrections:
                                corrected_line, = self.ax.plot(well_data['timestamp_utc'], 
                                               well_data['temperature_spike_corrected'], 
                                               '-', color='red', label=f'Well {well} (Spike Corrected)',
                                               alpha=0.8,
                                               zorder=3,
                                               linewidth=2,
                                               picker=5)
                                self.scatter_plots.append((corrected_line, well_data))
                            else:
                                # If no corrections, just use the original line with standard styling
                                if 'temperature' not in well_data.columns:
                                    line, = self.ax.plot(well_data['timestamp_utc'], 
                                                   well_data['temperature_spike_corrected'], 
                                                   '-', color='red', label=f'Well {well} (Temperature)',
                                                   alpha=0.7,
                                                   zorder=3,
                                                   picker=5)
                                    self.scatter_plots.append((line, well_data))
                    else:
                        # Use water_level_master_corrected for display if it exists, otherwise fall back to corrected level
                        display_column = 'water_level_master_corrected' if 'water_level_master_corrected' in well_data.columns else 'water_level_level_corrected'
                        y_label = 'Water Level (ft)'
                        line_color = 'blue'
                        data_type_label = 'Water Level'
                        
                        # Make the line pickable with a picker tolerance of 5 points
                        line, = self.ax.plot(well_data['timestamp_utc'], 
                                   well_data[display_column], 
                                   '-', color=line_color, label=f'Well {well} ({data_type_label})',
                                   alpha=0.7,
                                   zorder=3,
                                   picker=5)  # Enable picking for lines with 5-point tolerance
                        
                        # Store the line and its data for hover and pick events
                        self.scatter_plots.append((line, well_data))
            
            # Plot manual readings as scatter points (pickable) - only in water level mode
            if not self.manual_data.empty and self.data_type == 'water_level':
                # First filter out any rows with NaN well numbers
                manual_data = self.manual_data.dropna(subset=['well_number'])
                
                # Plot all manual data with a single style - no data_source distinction
                for well in manual_data['well_number'].unique():
                    if pd.isna(well):
                        continue
                        
                    well_mask = manual_data['well_number'] == well
                    well_data = manual_data[well_mask]
                    scatter_obj = self.ax.scatter(well_data['timestamp_utc'],
                                                 well_data['water_level'],
                                                 c='g', marker='s', s=50,
                                                 label=f'Well {well} (Manual)',
                                                 alpha=1.0, edgecolors='black',
                                                 zorder=5,
                                                 picker=True,
                                                 pickradius=5)
                    self.scatter_plots.append((scatter_obj, well_data))
            
            # Add master barometric data if checkbox is enabled (only for water level mode)
            if self.data_type == 'water_level' and self.show_master_baro.isChecked():
                self._plot_master_baro_data()
                
            # Set plot labels and appearance based on data type
            if self.data_type == 'temperature':
                self.ax.set_ylabel('Temperature (°C)', fontweight='bold')
            else:
                self.ax.set_ylabel('Water Level (ft)', fontweight='bold')
            
            self.ax.grid(True, linestyle='--', alpha=0.6)
            self.ax.legend(loc='upper right')
            
            # Format date axis with intelligent formatting
            self._setup_date_axis_formatting()
            
            # Set initial view limits based on BOTH transducer AND manual data timespan
            min_time = None
            max_time = None
            
            # Get min/max from transducer data
            if not self.transducer_data.empty:
                min_time = self.transducer_data['timestamp_utc'].min()
                max_time = self.transducer_data['timestamp_utc'].max()
            
            # Compare with min/max from manual data
            if not self.manual_data.empty:
                manual_min = self.manual_data['timestamp_utc'].min()
                manual_max = self.manual_data['timestamp_utc'].max()
                
                if min_time is None or manual_min < min_time:
                    min_time = manual_min
                    
                if max_time is None or manual_max > max_time:
                    max_time = manual_max
            
            # Set the plot limits if we have valid times
            if min_time is not None and max_time is not None:
                self.ax.set_xlim(min_time, max_time)
                
            # Add gap highlighting if enabled
            if hasattr(self, 'gap_highlight_enabled') and self.gap_highlight_enabled and not self.transducer_data.empty:
                # Identify gaps in the data
                gaps = self.identify_data_gaps(self.transducer_data)
                
                # Get y-axis limits for highlighting
                y_min, y_max = self.ax.get_ylim()
                
                # Add gap highlighting
                self.highlight_data_gaps(gaps, y_min, y_max)
                
            # Set the title using well_number and cae information
            if 'well_number' in self.transducer_data.columns:
                wells = self.transducer_data['well_number'].unique()
                wells_str = ', '.join(str(w) for w in wells)
                
                if 'cae' in self.transducer_data.columns:
                    cae_values = self.transducer_data['cae'].unique()
                    cae_str = ', '.join(str(c) for c in cae_values if pd.notna(c))
                    self.ax.set_title(f"Well Number: {wells_str}   CAE Number: {cae_str}", fontsize=12, fontweight='bold')
                else:
                    self.ax.set_title(f"Well Number: {wells_str}", fontsize=12, fontweight='bold')

            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}", exc_info=True)
            QMessageBox.warning(self, "Warning", f"Error updating plot: {str(e)}")

    def _group_consecutive_timestamps(self, data: pd.DataFrame) -> List[pd.DataFrame]:
        """
        Group data into consecutive ranges where baro_flag is 'standard'.
        Returns a list of DataFrames, each containing a consecutive group.
        """
        if data.empty:
            return []
            
        groups = []
        current_group = []
        
        # Ensure data is sorted by timestamp
        data = data.sort_values('timestamp_utc')
        
        # Iterate through the data row by row
        for idx, row in data.iterrows():
            if row['baro_flag'] == 'standard':
                current_group.append(idx)
            else:
                # If we have a current group and found non-standard, close it
                if current_group:
                    groups.append(data.loc[current_group])
                    current_group = []
        
        # Don't forget to add the last group if it exists
        if current_group:
            groups.append(data.loc[current_group])
            
        return groups

    def _plot_baro_flags(self):
        """Plot colored areas for baro flags"""
        try:
            # For each range where baro_flag is not 'master' or 'master_corrected', plot an orange shaded area
            data = self.transducer_data
            
            if data.empty or 'baro_flag' not in data.columns:
                return
                
            # Sort data by timestamp
            data = data.sort_values('timestamp_utc')
            
            # Find ranges where baro_flag is neither 'master' nor 'master_corrected'
            non_master_mask = ~data['baro_flag'].isin(['master', 'master_corrected'])
            
            if non_master_mask.any():
                # Group consecutive timestamps
                # This is a simplified approach - for production code, you might need a more robust method
                groups = []
                current_group = []
                
                timestamps = data[non_master_mask]['timestamp_utc'].sort_values().tolist()
                if not timestamps:
                    return
                    
                current_group = [timestamps[0]]
                
                for i in range(1, len(timestamps)):
                    if (timestamps[i] - timestamps[i-1]).total_seconds() > 3600:  # 1 hour gap
                        if current_group:
                            groups.append(current_group)
                        current_group = [timestamps[i]]
                    else:
                        current_group.append(timestamps[i])
                        
                if current_group:
                    groups.append(current_group)
                
                # Plot each group as a shaded area
                for i, group in enumerate(groups):
                    if len(group) > 0:
                        self.ax.axvspan(min(group), max(group),
                                       color='orange', alpha=0.3,
                                       label='Non-Master Baro' if i == 0 else None,
                                       zorder=1)
                        
        except Exception as e:
            logger.error(f"Error plotting baro flags: {e}")

    def _plot_level_flags(self):
        """Plot colored areas for level flags with default_level"""
        try:
            # For each range where level_flag is default_level, plot a violet shaded area
            data = self.transducer_data
            
            if data.empty or 'level_flag' not in data.columns:
                return
                
            # Sort data by timestamp
            data = data.sort_values('timestamp_utc')
            
            # Find ranges where level_flag is default_level
            default_level_mask = data['level_flag'] == 'default_level'
            
            if default_level_mask.any():
                # Group consecutive timestamps
                # This is a simplified approach - for production code, you might need a more robust method
                groups = []
                current_group = []
                
                timestamps = data[default_level_mask]['timestamp_utc'].sort_values().tolist()
                if not timestamps:
                    return
                    
                current_group = [timestamps[0]]
                
                for i in range(1, len(timestamps)):
                    if (timestamps[i] - timestamps[i-1]).total_seconds() > 3600:  # 1 hour gap
                        if current_group:
                            groups.append(current_group)
                        current_group = [timestamps[i]]
                    else:
                        current_group.append(timestamps[i])
                        
                if current_group:
                    groups.append(current_group)
                
                # Plot each group as a shaded area
                for i, group in enumerate(groups):
                    if len(group) > 0:
                        self.ax.axvspan(min(group), max(group),
                                       color='violet', alpha=0.3,
                                       label='Default Level' if i == 0 else None,
                                       zorder=1)
                        
        except Exception as e:
            logger.error(f"Error plotting level flags: {e}")

    def _plot_master_baro_flags(self):
        """Plot colored areas for master baro presence using cached groups"""
        try:
            if self._master_baro_groups is None:
                return
                
            # Plot each group as a colored area; label only the first instance
            for i, group in enumerate(self._master_baro_groups):
                if len(group) > 0:
                    self.ax.axvspan(group['timestamp_utc'].iloc[0],
                                      group['timestamp_utc'].iloc[-1],
                                      color='blue', alpha=0.2,
                                      label='Master Baro' if i == 0 else None,
                                      zorder=1)
        except Exception as e:
            logger.error(f"Error plotting master baro flags: {e}")

    def _plot_master_baro_data(self):
        """Plot master baro data on a secondary y-axis using dedicated master_baro_data DataFrame"""
        try:
            # Use the dedicated master_baro_data DataFrame directly
            if self.master_baro_data.empty:
                logger.debug("No master baro data available to plot")
                return
            
            # Get current x-axis limits
            xlim = self.ax.get_xlim()
            x_min = matplotlib.dates.num2date(xlim[0]).replace(tzinfo=None)
            x_max = matplotlib.dates.num2date(xlim[1]).replace(tzinfo=None)
            
            # Filter master baro data for visible range
            time_range_mask = (self.master_baro_data['timestamp_utc'] >= x_min) & \
                             (self.master_baro_data['timestamp_utc'] <= x_max)
            visible_master_baro = self.master_baro_data[time_range_mask]
            
            if visible_master_baro.empty:
                logger.debug("No master baro data in current view range")
                return
            
            # Create secondary y-axis for baro pressure
            self.ax2 = self.ax.twinx()
            self.ax2.set_ylabel('Barometric Pressure (psi)', color='blue')
            self.ax2.tick_params(axis='y', labelcolor='blue')
            
            # Plot the baro data (using 'pressure' column from master_baro_readings table)
            pressure_column = 'pressure'  # Column from master_baro_readings table
            
            self.ax2.plot(visible_master_baro['timestamp_utc'], 
                         visible_master_baro[pressure_column],
                         'b-', label='Master Baro', 
                         linewidth=2, 
                         alpha=0.7)
            
            # Add legend for the secondary axis
            lines2, labels2 = self.ax2.get_legend_handles_labels()
            if lines2:
                self.ax2.legend(loc='lower right')
            
            logger.debug(f"Plotted {len(visible_master_baro)} master baro points")
            
        except Exception as e:
            logger.error(f"Error plotting master baro data: {e}", exc_info=True)

    def apply_changes(self):
        """Apply changes to the database based on modification flags"""
        try:
            # Don't close helper dialogs at the start - let them stay open for further edits
            # They will be closed only after successful completion or when dialog is closed
            
            # Handle temperature changes separately
            if self.data_type == 'temperature':
                return self._apply_temperature_changes()
            else:
                return self._apply_water_level_changes()
                
        except Exception as e:
            logger.error(f"Error in apply_changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply changes: {str(e)}")
    
    def _apply_temperature_changes(self):
        """Apply temperature spike corrections to the database"""
        try:
            # Run database migration to ensure temperature_spike_corrected column exists
            if self.db_path:
                from ...database.migration_utils import DatabaseMigration
                migration = DatabaseMigration(self.db_path)
                migration.check_and_migrate()
            # Find records that have been spike corrected
            if 'temperature_spike_flag' not in self.plot_data.columns:
                QMessageBox.information(self, "No Changes", "No temperature corrections found to apply.")
                return
            
            spike_mod_mask = self.plot_data['temperature_spike_flag'] == 'spike_corrected'
            modified_data = self.plot_data[spike_mod_mask].copy()
            
            if modified_data.empty:
                QMessageBox.information(self, "No Changes", "No temperature modifications found to apply.")
                return
            
            num_records = len(modified_data)
            logger.info(f"Found {num_records} temperature records to update")
            
            # Create progress dialog
            progress = QProgressDialog("Updating temperature data...", "Cancel", 0, num_records, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Applying Temperature Changes")
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            
            try:
                # Check database path
                if not self.db_path:
                    raise ValueError("No database path provided")
                    
                # Connect and start transaction
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                logger.info(f"Starting temperature database update for {num_records} records")
                
                # Prepare update data
                update_data = []
                for index, row in modified_data.iterrows():
                    temperature_corrected = row['temperature_spike_corrected']
                    spike_flag = row['temperature_spike_flag']
                    timestamp_utc = row['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row['timestamp_utc'], pd.Timestamp) else str(row['timestamp_utc'])
                    well_number = str(row['well_number']).strip()
                    
                    update_data.append((temperature_corrected, spike_flag, well_number, timestamp_utc))
                    
                    # Update progress
                    progress.setValue(len(update_data))
                    QApplication.processEvents()
                    
                    if progress.wasCanceled():
                        conn.rollback()
                        conn.close()
                        progress.close()
                        QMessageBox.information(self, "Operation Canceled", "Temperature update was canceled.")
                        return
                
                # Execute batch update
                cursor.executemany("""
                    UPDATE water_level_readings 
                    SET temperature_spike_corrected = ?, temperature_spike_flag = ?
                    WHERE well_number = ? AND timestamp_utc = ?
                """, update_data)
                
                total_updated = cursor.rowcount if cursor.rowcount >= 0 else len(update_data)
                
                progress.setValue(num_records)
                QApplication.processEvents()
                
                # Commit transaction
                conn.commit()
                conn.close()
                progress.close()
                
                logger.info(f"Temperature database updated successfully. {total_updated} records affected.")
                
                # Mark database as modified
                parent_window = self.parent()
                if (hasattr(self, 'parent') and parent_window and 
                    hasattr(parent_window, 'db_manager') and parent_window.db_manager):
                    
                    if parent_window.db_manager.is_cloud_database:
                        parent_window.db_manager.mark_cloud_modified()
                        logger.info("Marked cloud database as modified after temperature edits")
                    
                    if hasattr(parent_window.db_manager, 'database_modified'):
                        parent_window.db_manager.database_modified.emit()
                        logger.info("Emitted database_modified signal after temperature edits")
                
                # Show success message
                QMessageBox.information(self, "Success", 
                    f"Temperature changes applied successfully!\n{total_updated} records updated.")
                
                # Close all helper dialogs
                self.close_all_helper_dialogs()
                    
            except Exception as e:
                progress.close()
                conn.rollback()
                conn.close()
                logger.error(f"Database error during temperature update: {e}")
                QMessageBox.critical(self, "Database Error", f"Failed to update database: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error applying temperature changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply temperature changes: {str(e)}")
    
    def _apply_water_level_changes(self):
        """Apply water level changes to the database (original method)"""
        try:
            # Find records that have been modified by any of the three methods
            baro_mod_mask = self.transducer_data['baro_flag_mod'] == 'master_mod'  # Compensation
            level_mod_mask = self.transducer_data['level_flag_mod'] == 'level_mod'  # Baseline adjustment
            spike_mod_mask = self.transducer_data['spike_flag'] == 'spike_corrected'  # Spike fix
            
            # Combine all modification masks to get all modified records
            modified_mask = baro_mod_mask | level_mod_mask | spike_mod_mask
            valid_well_mask = ~self.transducer_data['well_number'].isna()
            update_mask = modified_mask & valid_well_mask
            modified_data = self.transducer_data[update_mask].copy()
            
            if modified_data.empty:
                QMessageBox.information(self, "No Changes", "No data with changes to apply.")
                return
                
            # Show confirmation dialog
            num_records = len(modified_data)
            confirm_msg = f"Are you sure you want to update {num_records} records in the database?\\n\\n" \
                          f"This will update water levels and their corresponding flags."
            
            if QMessageBox.question(self, 'Confirm Changes', confirm_msg, 
                                  QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                return
                
            # Rest of the water level update logic continues as before...
            # (The rest of the original apply_changes method would go here)
            # For now, show a message that this part needs completion
            QMessageBox.information(self, "Water Level Changes", 
                f"Water level changes would be applied here for {num_records} records.")
            
        except Exception as e:
            logger.error(f"Error applying water level changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply water level changes: {str(e)}")
                
            # Show confirmation dialog
            num_records = len(modified_data)
            confirm_msg = f"Are you sure you want to update {num_records} records in the database?\n\n" \
                          f"This will update water levels and their corresponding flags."
            
            if QMessageBox.question(self, 'Confirm Changes', confirm_msg, 
                                  QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                return
                
            # Create progress dialog
            progress = QProgressDialog("Updating database...", "Cancel", 0, num_records, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Applying Changes")
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(0)  # Start at 0
            progress.show()
            
            try:
                # Check database path
                if not self.db_path:
                    raise ValueError("No database path provided")
                    
                # Connect and start transaction
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Log the start of the process
                logger.info(f"Starting database update for {num_records} records")
                
                # Process in smaller batches to update progress more frequently
                batch_size = 100  # Process 100 records at a time
                records_updated = 0
                total_updated = 0
                
                # Prepare all update data first
                update_data = []
                for index, row in modified_data.iterrows():
                    # Determine which water level and flags to use based on priority
                    if row['baro_flag_mod'] == 'master_mod':
                        water_level = row['water_level_master_corrected']
                        baro_flag = 'master_corrected'
                        level_flag = 'master_level_corrected' if row['level_flag_baro_mod'] == 'master_mod' else row['level_flag']
                    elif row['level_flag_mod'] == 'level_mod':
                        water_level = row['water_level_level_corrected']
                        level_flag = 'level_corrected'
                        baro_flag = row['baro_flag']
                    else:  # spike correction
                        water_level = row['water_level_spike_corrected']
                        level_flag = 'spike_corrected'
                        baro_flag = row['baro_flag']
                        
                    # Format timestamp
                    timestamp_utc = row['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row['timestamp_utc'], pd.Timestamp) else str(row['timestamp_utc'])
                    
                    # Add to batch update data
                    update_data.append((water_level, level_flag, baro_flag, str(row['well_number']).strip(), timestamp_utc))
                    
                    # Update progress more frequently
                    records_updated += 1
                    if records_updated % 10 == 0:  # Update UI every 10 records during preparation
                        progress.setValue(records_updated)
                        QApplication.processEvents()
                        
                    # Check for cancellation
                    if progress.wasCanceled():
                        conn.rollback()
                        conn.close()
                        progress.close()
                        logger.info("Update operation canceled by user")
                        QMessageBox.information(self, "Operation Canceled", "Database update was canceled.")
                        return
                
                # Now execute the updates in batches
                logger.info(f"Processing updates in batches of {batch_size}")
                for i in range(0, len(update_data), batch_size):
                    batch = update_data[i:i+batch_size]
                    
                    # Execute batch update
                    cursor.executemany("""
                        UPDATE water_level_readings 
                        SET water_level = ?, level_flag = ?, baro_flag = ?
                        WHERE well_number = ? AND timestamp_utc = ?
                    """, batch)
                    
                    # Count records affected in this batch
                    batch_affected = cursor.rowcount if cursor.rowcount >= 0 else len(batch)
                    total_updated += batch_affected
                    
                    # Update progress
                    current_progress = min(i + batch_size, num_records)
                    progress.setValue(current_progress)
                    logger.debug(f"Progress: {current_progress}/{num_records} records processed")
                    QApplication.processEvents()
                    
                    # Check for cancellation
                    if progress.wasCanceled():
                        conn.rollback()
                        conn.close()
                        progress.close()
                        logger.info("Update operation canceled by user")
                        QMessageBox.information(self, "Operation Canceled", "Database update was canceled.")
                        return
                
                # Ensure progress bar reaches 100% before commit
                progress.setValue(num_records)
                QApplication.processEvents()
                logger.info("All records processed, committing transaction")
                
                # Commit transaction
                conn.commit()
                
                # Update per-well flag summary in wells table after edits
                try:
                    from ...database.models.water_level import WaterLevelModel
                    model = WaterLevelModel(self.db_path)
                    for wn in modified_data['well_number'].unique():
                        model.update_well_flags(wn)
                except Exception as e:
                    logger.error(f"Error updating well flags after edit: {e}")
                
                # Use total_updated for the success message
                logger.info(f"Database updated successfully. {total_updated} records affected.")
                
                # Mark database as modified and emit signals
                parent_window = self.parent()
                if (hasattr(self, 'parent') and parent_window and 
                    hasattr(parent_window, 'db_manager') and parent_window.db_manager):
                    
                    # Mark cloud database as modified if applicable
                    if parent_window.db_manager.is_cloud_database:
                        parent_window.db_manager.mark_cloud_modified()
                        logger.info("Marked cloud database as modified after water level edits")
                    
                    # Emit database modification signal to enable Save to Cloud button
                    if hasattr(parent_window.db_manager, 'database_modified'):
                        parent_window.db_manager.database_modified.emit()
                        logger.info("Emitted database_modified signal after water level edits")
                    
                    # Track changes in the automatic change tracking system
                    if (hasattr(parent_window.db_manager, 'change_tracker') and 
                        parent_window.db_manager.change_tracker):
                        try:
                            from ...gui.handlers.change_tracker import ChangeType, ChangeAction
                            
                            # Group changes by well and summarize them
                            wells_modified = modified_data['well_number'].unique()
                            for well_number in wells_modified:
                                well_changes = modified_data[modified_data['well_number'] == well_number]
                                change_types = []
                                if (well_changes['baro_flag_mod'] == 'master_mod').any():
                                    change_types.append("barometric compensation")
                                if (well_changes['level_flag_mod'] == 'level_mod').any():
                                    change_types.append("baseline adjustment")
                                if (well_changes['spike_flag'] == 'spike_corrected').any():
                                    change_types.append("spike correction")
                                
                                change_description = f"Applied {', '.join(change_types)} to {len(well_changes)} readings"
                                
                                change_id = parent_window.db_manager.change_tracker.track_water_level_edit(
                                    well_number=str(well_number),
                                    records_modified=len(well_changes),
                                    change_description=change_description,
                                    change_type=ChangeType.MANUAL
                                )
                                logger.info(f"Tracked water level edit for well {well_number}: {change_description} (ID: {change_id})")
                        except Exception as e:
                            logger.error(f"Error tracking water level edit changes: {e}")
                            # Continue even if change tracking fails
                
                QMessageBox.information(self, "Changes Applied", 
                                      f"Successfully updated {total_updated} records in the database.")
                
                # Close everything
                conn.close()
                progress.close()
                self.close_helper_dialogs()  # Ensure helper dialogs are closed
                self.accept()
                
            except Exception as e:
                if 'conn' in locals():
                    conn.rollback()
                    conn.close()
                progress.close()
                logger.error(f"Database update error: {e}", exc_info=True)
                raise e
                
        except Exception as e:
            logger.error(f"Error applying changes to database: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to apply changes: {str(e)}")

    def fix_spikes(self):
        """Open the spike fixing dialog for point selection"""
        if self.transducer_data.empty:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("No Data")
            msg_box.setText("No transducer data available for spike fixing.")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            return
        # Create and show the helper dialog
        self.spike_helper = SpikeFixHelperDialog(self)
        self.spike_helper.apply_btn.clicked.connect(self.apply_spike_fix)
        # Use the Reset button to clear selection markers and helper state
        self.spike_helper.reset_btn.setText("Clear Selection")
        try:
            self.spike_helper.reset_btn.clicked.disconnect()
        except TypeError:
            pass
        self.spike_helper.reset_btn.clicked.connect(self.clear_spike_selection)
        self.spike_helper.show()

    def start_spike_point_selection(self, helper_dialog):
        """Start the point selection mode for spike fixing (multi-pair, no pause, pan/zoom always enabled)"""
        self.spike_selection_mode = True
        self.spike_helper_dialog = helper_dialog
        self.canvas.setCursor(Qt.CrossCursor)
        # Disconnect any previous selection handler and connect to release event for selection
        if hasattr(self, 'spike_click_cid') and self.spike_click_cid:
            self.canvas.mpl_disconnect(self.spike_click_cid)
        self.spike_click_cid = self.canvas.mpl_connect('button_release_event', self.on_spike_point_click)
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
        # Clear any previous selection state in helper
        if hasattr(self.spike_helper_dialog, 'reset_selection'):
            self.spike_helper_dialog.reset_selection()
        # Remove any existing plotted markers before new selection
        if hasattr(self, 'spike_points') and self.spike_points:
            for pt, _, _ in self.spike_points:
                try: pt.remove()
                except: pass
            self.spike_points = []
            self.canvas.draw_idle()

    def cancel_spike_point_selection(self):
        """Cancel the spike point selection mode (does not close dialog)"""
        self.spike_selection_mode = False
        self.canvas.setCursor(Qt.ArrowCursor)
        if hasattr(self, 'spike_click_cid') and self.spike_click_cid:
            self.canvas.mpl_disconnect(self.spike_click_cid)
            self.spike_click_cid = None
        if hasattr(self, 'spike_status_label') and self.spike_status_label:
            self.spike_status_label.deleteLater()
            self.spike_status_label = None
        if hasattr(self.spike_helper_dialog, 'reset_selection'):
            self.spike_helper_dialog.reset_selection()
        # Remove plotted selection markers and preview lines
        if hasattr(self, 'spike_points'):
            for pt, _, _ in self.spike_points:
                try: pt.remove()
                except: pass
            self.spike_points = []
        if hasattr(self, 'spike_lines'):
            for ln in self.spike_lines:
                try: ln.remove()
                except: pass
            self.spike_lines = []
        self.canvas.draw_idle()

    def on_spike_point_click(self, event):
        """Handle clicks when in spike point selection mode (multi-pair, no pause)"""
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
        try:
            x_coord = event.xdata
            y_coord = event.ydata
            
            # Check if coordinates are valid
            if x_coord is None or y_coord is None:
                QApplication.restoreOverrideCursor()
                return
                
            clicked_time = matplotlib.dates.num2date(x_coord).replace(tzinfo=None)
            # Find the closest transducer data point using efficient vectorized operations
            closest_point = self.find_closest_data_point(clicked_time, y_coord)
            if closest_point is None:
                QApplication.restoreOverrideCursor()
                return
            timestamp, value = closest_point
            # Pass point to helper dialog (handles first/second logic and pair logging)
            if hasattr(self, 'spike_helper_dialog') and self.spike_helper_dialog:
                self.spike_helper_dialog.set_selected_point(timestamp, value, self.data_type)
            # Highlight the selected point on the plot
            point_color = 'red' if not self.spike_helper_dialog.current_point else 'blue'
            point_label = None
            point = self.ax.scatter([timestamp], [value], color=point_color, s=100, zorder=10, label=point_label)
            self.spike_points.append((point, timestamp, value))
            self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Error processing point click: {e}", exc_info=True)
        finally:
            QApplication.restoreOverrideCursor()

    def find_closest_data_point(self, click_time, click_level):
        """Find the closest data point to the click location using efficient vectorized operations"""
        try:
            if self.transducer_data is None or self.transducer_data.empty:
                return None
            
            # Get current time range from the visible data
            xlim = self.ax.get_xlim()
            start_time = matplotlib.dates.num2date(xlim[0]).replace(tzinfo=None)
            end_time = matplotlib.dates.num2date(xlim[1]).replace(tzinfo=None)
            
            # Filter data to current view
            mask = (self.transducer_data['timestamp_utc'] >= start_time) & \
                   (self.transducer_data['timestamp_utc'] <= end_time)
            view_data = self.transducer_data[mask]
            
            if view_data.empty:
                return None
            
            # Convert to numpy arrays for efficient calculation
            time_values = view_data['timestamp_utc'].values
            
            # Get values based on current data type
            if self.data_type == 'temperature':
                if 'temperature_spike_corrected' in view_data.columns:
                    level_values = view_data['temperature_spike_corrected'].values
                else:
                    level_values = view_data['temperature'].values
            else:
                level_values = view_data['water_level'].values
            
            # Calculate time differences in seconds
            time_diffs = np.array([(pd.to_datetime(t) - pd.to_datetime(click_time)).total_seconds() 
                                 for t in time_values])
            
            # Normalize time and level scales for distance calculation
            time_range = (end_time - start_time).total_seconds()
            level_range = level_values.max() - level_values.min()
            
            if time_range == 0 or level_range == 0:
                # If no range, just use time difference
                min_idx = np.argmin(np.abs(time_diffs))
            else:
                # Normalize to [0, 1] scale for distance calculation
                time_norm = time_diffs / time_range
                level_norm = (level_values - level_values.min()) / level_range
                click_level_norm = (click_level - level_values.min()) / level_range
                
                # Calculate Euclidean distances
                distances = time_norm**2 + (level_norm - click_level_norm)**2
                min_idx = np.argmin(distances)
            
            # Get the closest point
            closest_timestamp = time_values[min_idx]
            closest_value = level_values[min_idx]
            
            return pd.to_datetime(closest_timestamp), closest_value
            
        except Exception as e:
            logger.error(f"Error finding closest data point: {e}")
            return None

    def apply_spike_fix(self):
        """Apply linear interpolation for all selected pairs at once"""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            params = self.spike_helper.get_current_parameters()
            pairs = params.get("pairs", [])
            interval_minutes = params.get("interval_minutes", 15)
            if not pairs:
                QApplication.restoreOverrideCursor()
                # Create warning message box with proper parent and modal settings
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("Please select at least one pair of points.")
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                return
            
            # Track changes for this instance
            changes = {}
            all_affected_indices = []
            
            # Remove previous preview lines
            if hasattr(self, 'spike_lines') and self.spike_lines:
                for line in self.spike_lines:
                    if line:
                        line.remove()
                self.spike_lines = []
            
            # Determine which columns to work with based on data type
            if self.data_type == 'temperature':
                corrected_column = 'temperature_spike_corrected'
                flag_column = 'temperature_spike_flag'
                data_type_label = 'temperature'
            else:
                corrected_column = 'water_level_spike_corrected'
                flag_column = 'spike_flag'
                data_type_label = 'water level'
            
            # For each pair, interpolate and update data
            for i, ((start_time, start_value), (end_time, end_value)) in enumerate(pairs):
                # Log the values for debugging
                logger.info(f"Processing pair {i+1}: {data_type_label} interpolation from {start_value:.2f} to {end_value:.2f}")
                
                if start_time > end_time:
                    start_time, end_time = end_time, start_time
                    start_value, end_value = end_value, start_value
                between_mask = (self.transducer_data['timestamp_utc'] > start_time) & \
                               (self.transducer_data['timestamp_utc'] < end_time)
                start_point_mask = self.transducer_data['timestamp_utc'] == start_time
                end_point_mask = self.transducer_data['timestamp_utc'] == end_time
                range_mask = between_mask | start_point_mask | end_point_mask
                range_indices = self.transducer_data[range_mask].index
                if len(range_indices) < 2:
                    continue
                time_diff = (end_time - start_time).total_seconds()
                num_intervals = max(1, int(time_diff / (interval_minutes * 60)))
                time_values = []
                level_values = []
                for j in range(num_intervals + 1):
                    t = j / num_intervals
                    interp_time = start_time + pd.Timedelta(seconds=t * time_diff)
                    interp_value = start_value + t * (end_value - start_value)
                    time_values.append(interp_time)
                    level_values.append(interp_value)
                interp_df = pd.DataFrame({
                    'timestamp_utc': time_values,
                    corrected_column: level_values
                })
                
                # Track changes for each affected index
                for idx in range_indices:
                    point_time = self.transducer_data.loc[idx, 'timestamp_utc']
                    time_diffs = [abs((t - point_time).total_seconds()) for t in time_values]
                    closest_idx = time_diffs.index(min(time_diffs))
                    
                    # Record the change
                    changes[idx] = {
                        corrected_column: level_values[closest_idx],
                        flag_column: 'spike_corrected'
                    }
                    # Debug logging
                    logger.debug(f"Setting {corrected_column} at index {idx} to {level_values[closest_idx]:.3f}")
                    all_affected_indices.append(idx)
                
                # Draw a preview line for this pair
                preview_line, = self.ax.plot(
                    interp_df['timestamp_utc'], 
                    interp_df[corrected_column],
                    'g-', linewidth=2, alpha=0.8,
                    label=f"Interpolation {i+1}" if i == 0 else None
                )
                self.spike_lines.append(preview_line)
            
            # Apply changes using the new tracking system
            if changes:
                logger.info(f"SPIKE FIX DEBUG: Applying {len(changes)} changes to data")
                for idx, change_data in list(changes.items())[:3]:  # Log first 3 changes
                    logger.info(f"  Change at index {idx}: {change_data}")
                self.apply_instance_edits(self.spike_helper.instance_id, 'spike_fix', changes)
                logger.info("SPIKE FIX DEBUG: Changes applied to transducer_data and plot_data")
                
            self.ax.legend(loc='upper right')
            # Update the entire plot to show changes with updated data
            logger.info(f"SPIKE FIX DEBUG: About to call update_plot(), data_type = {self.data_type}")
            if hasattr(self, 'transducer_data') and not self.transducer_data.empty:
                temp_cols = [col for col in self.transducer_data.columns if 'temp' in col.lower()]
                logger.info(f"SPIKE FIX DEBUG: Temperature columns in transducer_data: {temp_cols}")
                if 'temperature_spike_corrected' in self.transducer_data.columns:
                    temp_range = self.transducer_data['temperature_spike_corrected'].describe()
                    logger.info(f"SPIKE FIX DEBUG: temperature_spike_corrected range: {temp_range.to_dict()}")
            self.update_plot()
            logger.info("SPIKE FIX DEBUG: update_plot() completed")
            # Re-add preview lines
            for i, preview_line in enumerate(self.spike_lines):
                if preview_line:
                    x_data = preview_line.get_xdata()
                    y_data = preview_line.get_ydata()
                    new_line, = self.ax.plot(x_data, y_data, "g-", linewidth=2, alpha=0.8)
                    self.spike_lines[i] = new_line
            self.canvas.draw()
            QApplication.restoreOverrideCursor()
            # Create message box with proper parent and modal settings
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Interpolation Added")
            msg_box.setText(f"Added linear interpolation for {len(pairs)} {data_type_label} pairs.\nClick 'Apply Changes' on the main dialog to save to database.")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            # Reset helper dialog state for next use
            if hasattr(self.spike_helper, 'clear_all'):
                self.spike_helper.clear_all()
        except Exception as e:
            logger.error(f"Error applying spike fix: {e}", exc_info=True)
            QApplication.restoreOverrideCursor()
            # Create error message box with proper parent and modal settings
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to apply spike fix: {str(e)}")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()

    def reset_spike_fix(self):
        """Reset all spike corrected data back to original values and clear pairs"""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            spike_mask = self.transducer_data['spike_flag'] == 'spike_corrected'
            indices_to_reset = self.transducer_data[spike_mask].index
            if len(indices_to_reset) == 0:
                QApplication.restoreOverrideCursor()
                # Create info message box with proper parent and modal settings
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("No Changes")
                msg_box.setText("No spike-corrected data to reset.")
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                return
            for idx in indices_to_reset:
                original_level = self.transducer_data.loc[idx, 'water_level']
                self.transducer_data.loc[idx, 'water_level_spike_corrected'] = original_level
                self.transducer_data.loc[idx, 'spike_flag'] = 'none'
                if idx in self.plot_data.index:
                    self.plot_data.loc[idx, 'water_level_spike_corrected'] = original_level
                    self.plot_data.loc[idx, 'spike_flag'] = 'none'
            if hasattr(self, 'spike_lines') and self.spike_lines:
                for line in self.spike_lines:
                    if line:
                        line.remove()
                self.spike_lines = []
            if hasattr(self, 'spike_points') and self.spike_points:
                for point, _, _ in self.spike_points:
                    if point:
                        point.remove()
                self.spike_points = []
            if hasattr(self.spike_helper, 'clear_all'):
                self.spike_helper.clear_all()
            self.canvas.draw()
            QApplication.restoreOverrideCursor()
            # Create success message box with proper parent and modal settings
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Reset Complete")
            msg_box.setText(f"Successfully reset {len(indices_to_reset)} spike-corrected data points.")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            logger.debug(f"Reset spike correction for {len(indices_to_reset)} points")
        except Exception as e:
            logger.error(f"Error resetting spike fix: {e}", exc_info=True)
            QApplication.restoreOverrideCursor()
            # Create error message box with proper parent and modal settings
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to reset spike corrections: {str(e)}")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()

    def clear_spike_selection(self):
        """Clear the current spike selection markers and reset edits for this instance"""
        # Remove selection markers
        if hasattr(self, 'spike_points') and self.spike_points:
            for pt, _, _ in self.spike_points:
                try: pt.remove()
                except: pass
            self.spike_points = []
        # Remove preview lines
        if hasattr(self, 'spike_lines') and self.spike_lines:
            for ln in self.spike_lines:
                try: ln.remove()
                except: pass
            self.spike_lines = []
        # Reset edits for this instance
        if hasattr(self, 'spike_helper') and self.spike_helper:
            self.reset_instance_edits(self.spike_helper.instance_id)
        # Clear helper dialog list
        if hasattr(self, 'spike_helper') and hasattr(self.spike_helper, 'clear_all'):
            self.spike_helper.clear_all()
        self.canvas.draw_idle()

    def apply_compensation(self):
        """Handle compensation in the selected data"""
        # Create and show the helper dialog
        self.compensation_helper = CompensationHelperDialog(self)
        self.compensation_helper.parametersChanged.connect(self.preview_compensation)
        self.compensation_helper.apply_btn.clicked.connect(self.apply_compensation_changes)
        self.compensation_helper.reset_btn.clicked.connect(self.reset_compensation)
        self.compensation_helper.show()

    def adjust_baseline(self):
        """Handle baseline adjustment in the selected data"""
        # Create and show the helper dialog
        self.baseline_helper = BaselineHelperDialog(self)
        self.baseline_helper.parametersChanged.connect(self.preview_baseline)
        self.baseline_helper.apply_btn.clicked.connect(self.apply_baseline_changes)
        self.baseline_helper.reset_btn.clicked.connect(self.reset_baseline)
        logger.debug("Baseline helper buttons connected")
        self.baseline_helper.show()

    def preview_compensation(self, params):
        """Preview compensation with given parameters"""
        try:
            # Clear any existing compensation preview lines
            self.reset_compensation()
            logger.debug(f"Previewing compensation with params: {params}")
            
            # Get mode from the compensation helper dialog parameters
            mode = params.get("mode", "missing")
            show_preview = params.get("preview", True)
            logger.debug(f"Compensation mode: {mode}, Show preview: {show_preview}")

            if not show_preview:
                logger.debug("Preview disabled, skipping")
                return

            # Get the working dataset based on mode
            if mode == "selection":
                if self.selected_data is None or self.selected_data.empty:
                    logger.debug("No data selected for compensation preview.")
                    return
                df = self.selected_data.copy()
            elif mode == "missing":
                # For missing ranges, only get data where baro_flag is not master
                df = self.plot_data[self.plot_data['baro_flag'] != 'master'].copy()
            
            if df.empty:
                logger.debug("No data found to preview compensation.")
                return

            # Filter to only include transducer data (not manual readings)
            # First check for our custom marker column
            if 'data_source_type' in df.columns:
                transducer_mask = df['data_source_type'] == 'Transducer'
            # Then try the regular data_source column
            elif 'data_source' in df.columns:
                transducer_mask = df['data_source'].str.contains('Transducer', case=False, na=False)
            else:
                # If data_source column doesn't exist, use the transducer_data DataFrame indices
                transducer_mask = df.index.isin(self.transducer_data.index)
                
            df = df[transducer_mask]
            
            logger.debug(f"Working dataset size for preview: {len(df)}")
            
            # Get the master baro data for the time range
            master_data = self.plot_data[
                (self.plot_data['baro_flag'] == 'master') &
                (self.plot_data['timestamp_utc'] >= df['timestamp_utc'].min()) &
                (self.plot_data['timestamp_utc'] <= df['timestamp_utc'].max())
            ].copy()

            logger.debug(f"Master baro data size: {len(master_data)}")
            
            # Check if master data is empty and handle gracefully
            if master_data.empty:
                logger.debug("No master baro data available for compensation preview.")
                return
            
            # Check if pressure column exists in master data
            if 'pressure' not in master_data.columns:
                logger.warning("Master baro data doesn't contain 'pressure' column")
                return

            # Sort both datasets by timestamp
            df = df.sort_values('timestamp_utc')
            master_data = master_data.sort_values('timestamp_utc')
            
            # Interpolate master baro data to match our timestamps
            master_baro_interp = np.interp(
                mdates.date2num(df['timestamp_utc']),
                mdates.date2num(master_data['timestamp_utc']),
                master_data['pressure']
            )
            
            # Constants
            PSI_TO_FEET_OF_WATER = 2.31  # 1 PSI = 2.31 feet of water
            STANDARD_PRESSURE = 14.7  # Standard atmospheric pressure in PSI

            # Calculate the barometric correction in feet of water
            baro_correction_feet = (master_baro_interp - STANDARD_PRESSURE) * PSI_TO_FEET_OF_WATER
            
            # Calculate corrected water level
            corrected_levels = df['water_level'] - baro_correction_feet

            # Update the data in the water_level_master_corrected column but DON'T update flags yet
            df['water_level_master_corrected'] = corrected_levels
            
            # Save indices for later use
            indices_to_update = df.index
            
            # Update the main transducer_data DataFrame with corrected levels
            self.transducer_data.loc[indices_to_update, 'water_level_master_corrected'] = corrected_levels
            
            # Also update the combined plot_data (for backwards compatibility)
            self.plot_data.loc[indices_to_update, 'water_level_master_corrected'] = corrected_levels
            
            # STEP 2: SEGMENTATION AND LEVELING
            # Identify segments now, before flagging any data as master_corrected
            segments = self._identify_segments(self.transducer_data)
            logger.debug(f"Found {len(segments)} segments for leveling")
            
            # For each segment, apply the appropriate level adjustment
            for i, segment in enumerate(segments):
                # Skip segments that already have master/master_corrected flags
                if segment['baro_flag'].isin(['master', 'master_corrected']).all():
                    logger.debug(f"Segment {i+1} already has master/master_corrected flags, skipping")
                    continue
                    
                logger.debug(f"Processing segment {i+1}: {len(segment)} points from "
                            f"{segment['timestamp_utc'].min()} to {segment['timestamp_utc'].max()}")
                
                # Apply the leveling using the 3-tier priority system
                segment_indices = segment.index
                adjustment = 0.0
                level_method = "none"
                
                # Priority 1: Check for master/master_corrected data within 1 hour of segment start
                adjustment, level_method = self._find_reference_level_start(segment)
                
                # Priority 2: If no reference found, check for master/master_corrected data within 1 hour of segment end
                if adjustment == 0.0 and level_method == "none":
                    adjustment, level_method = self._find_reference_level_end(segment)
                
                # Priority 3: If still no reference found, use manual readings
                if adjustment == 0.0 and level_method == "none":
                    adjustment, level_method = self._find_manual_level_references(segment)
                
                # Apply adjustment if we found a reference
                if level_method != "none":
                    # Update the water level values
                    self.transducer_data.loc[segment_indices, 'water_level_master_corrected'] += adjustment
                    self.plot_data.loc[segment_indices, 'water_level_master_corrected'] += adjustment
                    
                    # Keep track that this segment was leveled (for flagging in step 3)
                    self.transducer_data.loc[segment_indices, '_needs_level_flag'] = True
                    self.plot_data.loc[segment_indices, '_needs_level_flag'] = True
                    
                    logger.debug(f"Applied level adjustment of {adjustment:.3f} ft to segment {i+1} "
                                f"using method: {level_method}")
                else:
                    logger.debug(f"No reference level found for segment {i+1}, left unleveled")
            
            # STEP 3: FLAGS - Update only the modification flags
            # Set 'baro_flag_mod' to 'master_mod' for all compensated data
            self.transducer_data.loc[indices_to_update, 'baro_flag_mod'] = 'master_mod'
            self.plot_data.loc[indices_to_update, 'baro_flag_mod'] = 'master_mod'
            
            # Set 'level_flag_baro_mod' to 'master_mod' for leveled data
            # First make sure the temporary flag column exists
            if '_needs_level_flag' not in self.transducer_data.columns:
                self.transducer_data['_needs_level_flag'] = False
            if '_needs_level_flag' not in self.plot_data.columns:
                self.plot_data['_needs_level_flag'] = False
            
            # Then update level flags where needed
            level_mask = self.transducer_data['_needs_level_flag'] == True
            self.transducer_data.loc[level_mask, 'level_flag_baro_mod'] = 'master_mod'
            self.plot_data.loc[level_mask, 'level_flag_baro_mod'] = 'master_mod'
            
            # Clear the temporary column
            self.transducer_data.drop('_needs_level_flag', axis=1, inplace=True, errors='ignore')
            self.plot_data.drop('_needs_level_flag', axis=1, inplace=True, errors='ignore')

            # Clear existing compensation lines
            if self.compensation_line_handles:
                for line in self.compensation_line_handles:
                    if line:
                        try:
                            line.remove()
                        except Exception as e:
                            logger.error(f"Error removing compensation line: {e}")
                self.compensation_line_handles = []
            
            # Draw the applied line directly with green color
            # Use the updated water_level_master_corrected that includes leveling adjustments
            line_handle, = self.ax.plot(
                self.transducer_data.loc[indices_to_update, 'timestamp_utc'],
                self.transducer_data.loc[indices_to_update, 'water_level_master_corrected'],
                color='green',
                linestyle='--',
                linewidth=2,
                label="Applied: Master Baro Corrected",
                zorder=6
            )
            
            self.compensation_line_handles = [line_handle]
            
            # Update the legend and redraw
            self.ax.legend(loc='upper right')
            self.canvas.draw()

            logger.debug(f"Applied compensation to {len(df)} points")

        except Exception as e:
            logger.error(f"Error applying compensation: {e}", exc_info=True)
            # Use always-on-top message box
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to apply compensation: {str(e)}")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()

    def _identify_segments(self, data: pd.DataFrame) -> List[pd.DataFrame]:
        """
        Identify segments where baro_flag is different from master or master_corrected.
        Returns a list of DataFrames, each containing a consecutive segment.
        """
        try:
            # Check if data is valid
            if data.empty:
                return []
            
            # Ensure data is sorted by timestamp
            data = data.sort_values('timestamp_utc')
            
            # Create mask for non-master/non-master_corrected points
            non_master_mask = ~data['baro_flag'].isin(['master', 'master_corrected'])
            
            # Check if we have any qualifying data
            if not non_master_mask.any():
                return []
                
            # Find transitions (where flag status changes)
            transitions = non_master_mask.astype(int).diff().fillna(0).astype(int)
            
            # Get segment start indices (where transitions == 1)
            starts = data.index[transitions == 1].tolist()
            
            # Get segment end indices (where transitions == -1)
            ends = data.index[transitions == -1].tolist()
            
            # Handle case where data starts with non-master data
            if non_master_mask.iloc[0]:
                starts.insert(0, data.index[0])
                
            # Handle case where data ends with non-master data
            if non_master_mask.iloc[-1]:
                ends.append(data.index[-1])
            
            # Create segments
            segments = []
            for i in range(min(len(starts), len(ends))):
                segment = data.loc[starts[i]:ends[i]]
                if not segment.empty:
                    segments.append(segment)
            
            return segments
        except Exception as e:
            logger.error(f"Error identifying segments: {e}")
            return []
            
    def _find_reference_level_start(self, segment: pd.DataFrame) -> (float, str):
        """
        Find reference level using data near the segment start.
        Returns a tuple of (adjustment value, method).
        """
        try:
            # Get the timestamp of the first point in the segment
            start_time = segment['timestamp_utc'].min()
            
            # Define the time window (1 hour before the start)
            window_start = start_time - pd.Timedelta(hours=1)
            window_end = start_time
            
            # Find master/master_corrected data in the window
            reference_mask = (
                (self.transducer_data['timestamp_utc'] >= window_start) &
                (self.transducer_data['timestamp_utc'] <= window_end) &
                (self.transducer_data['baro_flag'].isin(['master', 'master_corrected']))
            )
            
            reference_data = self.transducer_data[reference_mask]
            
            if not reference_data.empty:
                # Get the closest reference point to segment start
                time_diffs = abs(reference_data['timestamp_utc'] - start_time)
                closest_idx = time_diffs.idxmin()
                reference_point = reference_data.loc[closest_idx]
                
                # Get the closest segment point to the reference
                first_segment_point = segment.iloc[0]
                
                # Calculate the level difference
                level_diff = reference_point['water_level_master_corrected'] - first_segment_point['water_level_master_corrected']
                
                logger.debug(f"Found reference at start: {reference_point['timestamp_utc']} "
                          f"(diff: {(reference_point['timestamp_utc'] - start_time).total_seconds()/60:.1f} min), "
                          f"adjustment: {level_diff:.3f} ft")
                
                return level_diff, "start_reference"
            
            return 0.0, "none"
        except Exception as e:
            logger.error(f"Error finding reference level at start: {e}")
            return 0.0, "none"
            
    def _find_reference_level_end(self, segment: pd.DataFrame) -> (float, str):
        """
        Find reference level using data near the segment end.
        Returns a tuple of (adjustment value, method).
        """
        try:
            # Get the timestamp of the last point in the segment
            end_time = segment['timestamp_utc'].max()
            
            # Define the time window (1 hour after the end)
            window_start = end_time
            window_end = end_time + pd.Timedelta(hours=1)
            
            # Find master/master_corrected data in the window
            reference_mask = (
                (self.transducer_data['timestamp_utc'] >= window_start) &
                (self.transducer_data['timestamp_utc'] <= window_end) &
                (self.transducer_data['baro_flag'].isin(['master', 'master_corrected']))
            )
            
            reference_data = self.transducer_data[reference_mask]
            
            if not reference_data.empty:
                # Get the closest reference point to segment end
                time_diffs = abs(reference_data['timestamp_utc'] - end_time)
                closest_idx = time_diffs.idxmin()
                reference_point = reference_data.loc[closest_idx]
                
                # Get the last segment point
                last_segment_point = segment.iloc[-1]
                
                # Calculate the level difference
                level_diff = reference_point['water_level_master_corrected'] - last_segment_point['water_level_master_corrected']
                
                logger.debug(f"Found reference at end: {reference_point['timestamp_utc']} "
                          f"(diff: {(reference_point['timestamp_utc'] - end_time).total_seconds()/60:.1f} min), "
                          f"adjustment: {level_diff:.3f} ft")
                
                return level_diff, "end_reference"
            
            return 0.0, "none"
        except Exception as e:
            logger.error(f"Error finding reference level at end: {e}")
            return 0.0, "none"
    
    def _find_manual_level_references(self, segment: pd.DataFrame) -> (float, str):
        """
        Find reference level using manual readings near the segment.
        Returns a tuple of (adjustment value, method).
        """
        try:
            # Get segment time range
            start_time = segment['timestamp_utc'].min()
            end_time = segment['timestamp_utc'].max()
            
            # Define expanded time window (±1 hour around segment)
            window_start = start_time - pd.Timedelta(hours=1)
            window_end = end_time + pd.Timedelta(hours=1)
            
            # Find manual readings in the window
            if not self.manual_data.empty:
                manual_mask = (
                    (self.manual_data['timestamp_utc'] >= window_start) &
                    (self.manual_data['timestamp_utc'] <= window_end)
                )
                manual_readings = self.manual_data[manual_mask]
                
                if not manual_readings.empty:
                    # For each manual reading, find the closest segment point and calculate difference
                    dh_values = []
                    
                    for _, manual_row in manual_readings.iterrows():
                        # Find closest segment point in time
                        time_diffs = abs(segment['timestamp_utc'] - manual_row['timestamp_utc'])
                        closest_idx = time_diffs.idxmin()
                        closest_point = segment.loc[closest_idx]
                        
                        # Calculate level difference
                        dh = manual_row['water_level'] - closest_point['water_level_master_corrected']
                        dh_values.append(dh)
                        
                        logger.debug(f"Manual reading at {manual_row['timestamp_utc']} matched with segment point at "
                                  f"{closest_point['timestamp_utc']} (diff: {time_diffs.min().total_seconds()/60:.1f} min, "
                                  f"level diff: {dh:.3f} ft)")
                    
                    # Calculate average difference
                    if dh_values:
                        avg_dh = sum(dh_values) / len(dh_values)
                        logger.debug(f"Using average of {len(dh_values)} manual readings: {avg_dh:.3f} ft")
                        return avg_dh, "manual_readings"
            
            return 0.0, "none"
        except Exception as e:
            logger.error(f"Error finding manual level references: {e}")
            return 0.0, "none"

    def reset_compensation(self):
        """Reset compensation for the current instance"""
        try:
            # Remove preview lines
            if self.compensation_line_handles:
                for line in self.compensation_line_handles:
                    try:
                        line.remove()
                    except Exception as e:
                        logger.error(f"Error removing compensation line: {e}")
                self.compensation_line_handles = []
            
            # Reset edits for this instance
            if hasattr(self, 'compensation_helper') and self.compensation_helper:
                self.reset_instance_edits(self.compensation_helper.instance_id)
                
        except Exception as e:
            logger.error(f"Error resetting compensation: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to reset compensation: {str(e)}")

    def reset_baseline(self):
        """Remove the last baseline adjustment line"""
        try:
            logger.info("=== RESET BASELINE CALLED ===")
            
            # Remove the last baseline adjustment line if it exists
            if hasattr(self, 'baseline_lines') and self.baseline_lines:
                last_line = self.baseline_lines.pop()  # Remove from our list
                try:
                    last_line.remove()  # Remove from plot
                except:
                    last_line.set_visible(False)
                
                # Update legend and refresh
                self.ax.legend()
                self.canvas.draw()
                
                logger.info(f"Removed last baseline adjustment line. {len(self.baseline_lines)} adjustments remaining.")
            else:
                logger.info("No baseline adjustment lines to remove")
            
        except Exception as e:
            logger.error(f"Error resetting baseline: {e}", exc_info=True)

    def on_hover(self, event):
        """Handle mouse hover events"""
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
            if isinstance(artist, matplotlib.collections.PathCollection):
                # Handle scatter plots
                contains, info = artist.contains(event)
                if contains:
                    idx = info["ind"][0]
                    point_data = df.iloc[idx]
                    text = f'Well: {point_data["well_number"]}\n' \
                           f'Date: {point_data["timestamp_utc"].strftime("%Y-%m-%d %H:%M")}\n' \
                           f'Level: {point_data["water_level"]:.2f} ft\n' \
                           f'Source: {point_data["data_source"]}'
                    # Only create annotation if mouse coordinates are valid
                    if event.xdata is not None and event.ydata is not None:
                        self.hover_annotation = self.ax.annotate(text,
                            xy=(event.xdata, event.ydata),
                            xytext=(10, 10), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
                    found_point = True
                    break
            elif isinstance(artist, matplotlib.lines.Line2D):
                # Handle line plots - find the closest point to the cursor
                if event.xdata is not None and event.ydata is not None:
                    # Get x and y data from the line
                    line_times = mdates.date2num(df['timestamp_utc'].values)
                    if 'water_level_master_corrected' in df.columns:
                        line_levels = df['water_level_master_corrected'].values
                    elif 'water_level_level_corrected' in df.columns:
                        line_levels = df['water_level_level_corrected'].values
                    else:
                        line_levels = df['water_level'].values
                    
                    # Find the closest point in x direction (time)
                    x_diff = abs(line_times - event.xdata)
                    closest_idx = np.argmin(x_diff)
                    
                    # Check if the point is close enough (5 pixels in data coordinates)
                    if x_diff[closest_idx] < 5/72:  # approx 5 pixels in data coordinates
                        point_data = df.iloc[closest_idx]
                        time_str = point_data['timestamp_utc'].strftime('%Y-%m-%d %H:%M')
                        level_val = line_levels[closest_idx]
                        
                        text = f'Well: {point_data["well_number"]}\n' \
                               f'Date: {time_str}\n' \
                               f'Level: {level_val:.2f} ft'
                        
                        # Add flag information if available
                        if 'level_flag' in point_data:
                            text += f'\nLevel Flag: {point_data["level_flag"]}'
                        if 'baro_flag' in point_data:
                            text += f'\nBaro Flag: {point_data["baro_flag"]}'
                            
                        # Create the annotation at the point
                        self.hover_annotation = self.ax.annotate(text,
                            xy=(point_data['timestamp_utc'], level_val),
                            xytext=(10, 10), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.5),
                            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
                        found_point = True
                        break
        
        # Only redraw if we created a new annotation or removed an old one
        if found_point or self.hover_annotation is None:
            self.canvas.draw_idle()

    def on_pick(self, event):
        """Handle pick events on the scatter points and line plots"""
        try:
            artist = event.artist
            
            # Handle scatter plot picks
            if isinstance(artist, matplotlib.collections.PathCollection):
                ind = event.ind[0]  # Use the first point if multiple were picked
                
                # Find which scatter plot this belongs to
                for scatter_obj, data_df in self.scatter_plots:
                    if scatter_obj == artist and ind < len(data_df):
                        # Get the actual data record
                        point_data = data_df.iloc[ind]
                        
                        # Create annotation with a box
                        point_time = point_data['timestamp_utc']
                        point_level = point_data['water_level']
                        
                        # Format timestamp and display data fields
                        time_str = point_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Create comprehensive annotation text
                        text = f"Time: {time_str}\nLevel: {point_level:.3f} ft"
                        
                        # Add data source information if available
                        if 'data_source' in point_data:
                            text += f"\nSource: {point_data['data_source']}"
                        elif 'data_source_type' in point_data:
                            text += f"\nType: {point_data['data_source_type']}"
                            
                        # Add flag information if available
                        if 'level_flag' in point_data:
                            text += f"\nLevel Flag: {point_data['level_flag']}"
                            
                        if 'baro_flag' in point_data:
                            text += f"\nBaro Flag: {point_data['baro_flag']}"
                        
                        # Create a key for this point
                        key = (id(scatter_obj), ind)
                        
                        # Remove existing annotation for this point if it exists
                        if key in self.point_annotations:
                            self.point_annotations[key].remove()
                            del self.point_annotations[key]
                        else:
                            # Otherwise add a new annotation
                            annotation = self.ax.annotate(
                                text,
                                xy=(point_time, point_level),
                                xytext=(15, 15),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0")
                            )
                            
                            self.point_annotations[key] = annotation
                        
                        # Redraw the canvas
                        self.canvas.draw_idle()
                        return
                        
            # Handle line plot picks
            elif isinstance(artist, matplotlib.lines.Line2D):
                # Find the data associated with this line
                for line_obj, data_df in self.scatter_plots:
                    if line_obj == artist:
                        # Get mouse position in data coordinates
                        mouse_x = event.mouseevent.xdata
                        mouse_y = event.mouseevent.ydata
                        
                        if mouse_x is None or mouse_y is None:
                            return
                            
                        # Convert timestamps to matplotlib date numbers
                        line_times = mdates.date2num(data_df['timestamp_utc'].values)
                        
                        # Get values based on current data type
                        if self.data_type == 'temperature':
                            if 'temperature_spike_corrected' in data_df.columns:
                                line_values = data_df['temperature_spike_corrected'].values
                            else:
                                line_values = data_df['temperature'].values
                            value_label = "Temperature"
                            unit = "°C"
                        else:
                            # Water level mode
                            if 'water_level_master_corrected' in data_df.columns:
                                line_values = data_df['water_level_master_corrected'].values
                            elif 'water_level_level_corrected' in data_df.columns:
                                line_values = data_df['water_level_level_corrected'].values
                            else:
                                line_values = data_df['water_level'].values
                            value_label = "Level"
                            unit = "ft"
                        
                        # Find the closest point
                        distances = np.sqrt(((line_times - mouse_x) ** 2) + 
                                           ((line_values - mouse_y) ** 2))
                        closest_idx = np.argmin(distances)
                        
                        # Get the point data
                        point_data = data_df.iloc[closest_idx]
                        point_time = point_data['timestamp_utc']
                        point_value = line_values[closest_idx]
                        
                        # Format timestamp and create annotation
                        time_str = point_time.strftime('%Y-%m-%d %H:%M:%S')
                        text = f"Time: {time_str}\n{value_label}: {point_value:.3f} {unit}"
                        
                        # Add flag information if available
                        if self.data_type == 'temperature':
                            if 'temperature_spike_flag' in point_data:
                                text += f"\nTemp Flag: {point_data['temperature_spike_flag']}"
                        else:
                            if 'level_flag' in point_data:
                                text += f"\nLevel Flag: {point_data['level_flag']}"
                                
                            if 'baro_flag' in point_data:
                                text += f"\nBaro Flag: {point_data['baro_flag']}"
                        
                        # Create a unique key for this line point
                        key = (id(line_obj), closest_idx)
                        
                        # Remove existing annotation for this point if it exists
                        if key in self.point_annotations:
                            self.point_annotations[key].remove()
                            del self.point_annotations[key]
                        else:
                            # Otherwise add a new annotation
                            annotation = self.ax.annotate(
                                text,
                                xy=(point_time, point_value),
                                xytext=(15, 15),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.5", fc="lightgreen", alpha=0.8),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0")
                            )
                            
                            self.point_annotations[key] = annotation
                        
                        # Redraw the canvas
                        self.canvas.draw_idle()
                        return
                        
        except Exception as e:
            logger.error(f"Error in pick event: {e}", exc_info=True)

    def on_plot_click(self, event):
        """Handle plot clicks during selection mode or for point identification"""
        # First, handle selection mode if active
        if self.selection_mode and event.inaxes == self.ax:
            # Check if coordinates are valid
            if event.xdata is None:
                return
                
            # Get the exact datetime at click position
            selected_datetime = matplotlib.dates.num2date(event.xdata).replace(tzinfo=None)
            
            # Set the selected datetime to the appropriate date widget
            if self.selecting_for == "start":
                self.start_date.setDateTime(selected_datetime)
            else:
                self.end_date.setDateTime(selected_datetime)
            
            # Exit selection mode
            self.cancel_selection_mode()
            return
            
        # If not in selection mode, try to identify the nearest point
        elif event.inaxes == self.ax and not self.selection_mode:
            # Try to find the closest data point to the click
            if not self.transducer_data.empty:
                # Check if coordinates are valid
                if event.xdata is None or event.ydata is None:
                    return
                    
                # Convert click x-coordinate to datetime
                click_datetime = matplotlib.dates.num2date(event.xdata).replace(tzinfo=None)
                click_level = event.ydata
                
                # Find the closest point in transducer data by time
                time_diffs = abs(self.transducer_data['timestamp_utc'] - click_datetime)
                closest_idx = time_diffs.idxmin()
                closest_point = self.transducer_data.loc[closest_idx]
                
                # Calculate distance in both time and level dimensions
                time_diff_seconds = time_diffs.loc[closest_idx].total_seconds()
                level_diff = abs(closest_point['water_level'] - click_level)
                
                # Only show if within reasonable distance (adjust thresholds as needed)
                if time_diff_seconds < 86400 and level_diff < 2.0:  # Within 1 day and 2 feet
                    # Format point information
                    time_str = closest_point['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S')
                    level_val = closest_point['water_level']
                    
                    # Create annotation text
                    text = f"Time: {time_str}\nLevel: {level_val:.3f} ft"
                    
                    # Add data source information if available
                    if 'data_source' in closest_point:
                        text += f"\nSource: {closest_point['data_source']}"
                    elif 'data_source_type' in closest_point:
                        text += f"\nType: {closest_point['data_source_type']}"
                    
                    # Add flag information if available
                    if 'level_flag' in closest_point:
                        text += f"\nLevel Flag: {closest_point['level_flag']}"
                        
                    if 'baro_flag' in closest_point:
                        text += f"\nBaro Flag: {closest_point['baro_flag']}"
                    
                    # Store a unique key for this annotation
                    key = ('click_annotation', str(closest_idx))
                    
                    # Remove previous click annotation if exists
                    for k in list(self.point_annotations.keys()):
                        if k[0] == 'click_annotation':
                            self.point_annotations[k].remove()
                            del self.point_annotations[k]
                    
                    # Create a new annotation
                    annotation = self.ax.annotate(
                        text,
                        xy=(closest_point['timestamp_utc'], closest_point['water_level']),
                        xytext=(15, 15),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.5", fc="lightblue", alpha=0.8),
                        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0")
                    )
                    
                    self.point_annotations[key] = annotation
                    
                    # Log the identified point
                    logger.debug(f"Identified nearest point: {time_str}, Level: {level_val:.3f}, "
                               f"Time diff: {time_diff_seconds:.1f} sec, Level diff: {level_diff:.3f} ft")
                    
                    # Redraw the canvas
                    self.canvas.draw_idle()
                    
                    # If very close to a point, also highlight it
                    if time_diff_seconds < 3600 and level_diff < 0.5:  # Within 1 hour and 0.5 feet
                        # Find which scatter plot this belongs to
                        for scatter_obj, data_df in self.scatter_plots:
                            if closest_idx in data_df.index:
                                # Highlight this point temporarily
                                original_colors = scatter_obj.get_facecolors()
                                highlight_colors = original_colors.copy()
                                
                                # Find index in the scatter plot
                                scatter_idx = data_df.index.get_loc(closest_idx)
                                
                                # Make this point bright yellow
                                highlight_colors[scatter_idx] = (1, 1, 0, 1)  # Yellow
                                scatter_obj.set_facecolors(highlight_colors)
                                
                                # Reset after a brief delay
                                def reset_color():
                                    scatter_obj.set_facecolors(original_colors)
                                    self.canvas.draw_idle()
                                
                                # Use QTimer for delayed reset
                                QTimer.singleShot(1500, reset_color)
                                break

    def on_key_press(self, event):
        """Handle key press events for this dialog"""
        # If ESC is pressed while in spike selection mode, cancel the selection
        if event.key() == Qt.Key_Escape:
            if hasattr(self, 'spike_selection_mode') and self.spike_selection_mode:
                self.cancel_spike_point_selection()
                if hasattr(self, 'spike_helper') and self.spike_helper:
                    if hasattr(self.spike_helper, 'reset_selection'):
                        self.spike_helper.reset_selection()
                event.accept()
                return
        super().keyPressEvent(event)

    def show_message_box(self, icon, title, text, buttons=QMessageBox.Ok):
        """
        Create a message box that stays on top of the edit dialog and helper dialogs.
        
        Args:
            icon: QMessageBox icon (Information, Warning, Critical, Question)
            title: Window title
            text: Message text
            buttons: Buttons to show (default: Ok)
        
        Returns:
            Button clicked result
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        return msg_box.exec_()

    def close_helper_dialogs(self):
        """Close any open helper dialogs"""
        # Check and close each helper dialog if it exists
        if hasattr(self, 'spike_helper') and self.spike_helper:
            self.spike_helper.close()
            self.spike_helper = None
            
        if hasattr(self, 'compensation_helper') and self.compensation_helper:
            self.compensation_helper.close()
            self.compensation_helper = None
            
        if hasattr(self, 'baseline_helper') and self.baseline_helper:
            self.baseline_helper.close()
            self.baseline_helper = None
    
    def closeEvent(self, event):
        """Handle dialog closing to ensure helper dialogs are closed"""
        try:
            # Close helper dialogs when main dialog is closed
            self.close_helper_dialogs()
            # Accept the close event
            event.accept()
        except Exception as e:
            logger.error(f"Error in closeEvent: {e}")
            event.accept()  # Still close even if there's an error
    
    def register_edit(self, instance_id, method, affected_indices, original_values, modified_values):
        """Register an edit from a helper dialog instance"""
        edit_record = {
            'instance_id': instance_id,
            'method': method,
            'timestamp': datetime.now(),
            'affected_indices': affected_indices.tolist() if hasattr(affected_indices, 'tolist') else list(affected_indices),
            'original_values': original_values,
            'modified_values': modified_values,
            'is_applied': True
        }
        
        # Remove any existing edit with the same instance_id
        self.edit_history['edits'] = [e for e in self.edit_history['edits'] if e['instance_id'] != instance_id]
        
        # Add the new edit
        self.edit_history['edits'].append(edit_record)
        logger.debug(f"Registered edit for instance {instance_id}, method: {method}, affecting {len(affected_indices)} rows")
    
    def apply_instance_edits(self, instance_id, method, changes):
        """Apply edits from a specific helper instance"""
        try:
            # Store original values before applying changes
            affected_indices = list(changes.keys())
            original_values = {}
            
            for idx in affected_indices:
                original_values[idx] = {
                    'water_level': self.transducer_data.loc[idx, 'water_level'] if idx in self.transducer_data.index else None,
                    'water_level_spike_corrected': self.transducer_data.loc[idx, 'water_level_spike_corrected'] if idx in self.transducer_data.index else None,
                    'water_level_master_corrected': self.transducer_data.loc[idx, 'water_level_master_corrected'] if idx in self.transducer_data.index else None,
                    'water_level_level_corrected': self.transducer_data.loc[idx, 'water_level_level_corrected'] if idx in self.transducer_data.index else None,
                    'baro_flag_mod': self.transducer_data.loc[idx, 'baro_flag_mod'] if idx in self.transducer_data.index else None,
                    'level_flag_mod': self.transducer_data.loc[idx, 'level_flag_mod'] if idx in self.transducer_data.index else None,
                    'spike_flag': self.transducer_data.loc[idx, 'spike_flag'] if idx in self.transducer_data.index else None,
                    'temperature': self.transducer_data.loc[idx, 'temperature'] if idx in self.transducer_data.index and 'temperature' in self.transducer_data.columns else None,
                    'temperature_spike_corrected': self.transducer_data.loc[idx, 'temperature_spike_corrected'] if idx in self.transducer_data.index and 'temperature_spike_corrected' in self.transducer_data.columns else None,
                    'temperature_spike_flag': self.transducer_data.loc[idx, 'temperature_spike_flag'] if idx in self.transducer_data.index and 'temperature_spike_flag' in self.transducer_data.columns else None,
                }
            
            # Apply the changes
            for idx, change_data in changes.items():
                for col, value in change_data.items():
                    if idx in self.transducer_data.index:
                        self.transducer_data.loc[idx, col] = value
                    if idx in self.plot_data.index:
                        self.plot_data.loc[idx, col] = value
            
            # Register the edit
            self.register_edit(instance_id, method, affected_indices, original_values, changes)
            
            # Update the plot
            self.update_plot()
            
        except Exception as e:
            logger.error(f"Error applying instance edits: {e}", exc_info=True)
            raise
    
    def reset_instance_edits(self, instance_id):
        """Reset only edits from a specific instance"""
        try:
            # Find the edit record
            edit_record = None
            for edit in self.edit_history['edits']:
                if edit['instance_id'] == instance_id:
                    edit_record = edit
                    break
            
            if not edit_record:
                logger.warning(f"No edit record found for instance {instance_id}")
                return
            
            # Restore original values
            for idx, original_data in edit_record['original_values'].items():
                idx = int(idx) if isinstance(idx, str) else idx
                
                for col, value in original_data.items():
                    if value is not None:
                        if idx in self.transducer_data.index:
                            self.transducer_data.loc[idx, col] = value
                        if idx in self.plot_data.index:
                            self.plot_data.loc[idx, col] = value
            
            # Remove the edit from history
            self.edit_history['edits'] = [e for e in self.edit_history['edits'] if e['instance_id'] != instance_id]
            
            logger.debug(f"Reset edits for instance {instance_id}")
            
            # Update the plot
            self.update_plot()
            
        except Exception as e:
            logger.error(f"Error resetting instance edits: {e}", exc_info=True)
    
    def reset_all_edits(self):
        """Reset all edits to original session data"""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, 
                'Reset All Edits', 
                'Are you sure you want to reset all edits made in this session?\nThis action cannot be undone.',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Restore original data
                self.transducer_data = self.original_session_data['transducer_data'].copy()
                self.manual_data = self.original_session_data['manual_data'].copy()
                self.plot_data = self.original_session_data['plot_data'].copy()
                
                # Clear edit history
                self.edit_history['edits'] = []
                
                # Clear any preview lines or annotations
                if hasattr(self, 'spike_lines') and self.spike_lines:
                    for line in self.spike_lines:
                        if line:
                            try:
                                line.remove()
                            except:
                                pass
                    self.spike_lines = []
                
                if hasattr(self, 'spike_points') and self.spike_points:
                    for pt, _, _ in self.spike_points:
                        try:
                            pt.remove()
                        except:
                            pass
                    self.spike_points = []
                
                if self.compensation_line_handles:
                    for line in self.compensation_line_handles:
                        if line:
                            try:
                                line.remove()
                            except:
                                pass
                    self.compensation_line_handles = []
                
                if self.baseline_preview_line:
                    try:
                        self.baseline_preview_line.remove()
                    except:
                        pass
                    self.baseline_preview_line = None
                
                # Close any open helper dialogs
                self.close_helper_dialogs()
                
                # Update the plot
                self.update_plot()
                
                logger.info("All edits have been reset to original session data")
                QMessageBox.information(self, "Reset Complete", "All edits have been reset.")
                
        except Exception as e:
            logger.error(f"Error resetting all edits: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to reset edits: {str(e)}")

    def start_plot_selection(self, target="start"):
        """Start plot point selection mode (DISABLED/REMOVED)"""
        pass

    def cancel_selection_mode(self):
        """Cancel the date selection mode"""
        if hasattr(self, 'selection_status_label') and self.selection_status_label:
            self.selection_status_label.deleteLater()
            self.selection_status_label = None
        
        # Reset button styles
        self.select_start_btn.setStyleSheet("")
        self.select_end_btn.setStyleSheet("")
        
        # Remove guide line
        if hasattr(self, 'date_selection_line') and self.date_selection_line:
            self.date_selection_line.remove()
            self.date_selection_line = None
        
        # Disconnect events
        if hasattr(self, 'click_cid') and self.click_cid:
            self.canvas.mpl_disconnect(self.click_cid)
        
        if hasattr(self, 'motion_cid') and self.motion_cid:
            self.canvas.mpl_disconnect(self.motion_cid)
        
        # Reset cursor and selection mode
        self.canvas.setCursor(Qt.ArrowCursor)
        self.selection_mode = False
        
        # Redraw canvas
        self.canvas.draw_idle()

    def on_plot_motion(self, event):
        """Update position of selection line during motion"""
        if not self.selection_mode or event.inaxes != self.ax:
            return
        
        # Update vertical line position
        if hasattr(self, 'date_selection_line') and self.date_selection_line and event.xdata is not None:
            self.date_selection_line.set_xdata(event.xdata)
            self.canvas.draw_idle()

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape and hasattr(self, 'selection_mode') and self.selection_mode:
            # Cancel selection mode
            self.cancel_selection_mode()
        else:
            super().keyPressEvent(event)

    def set_full_date_range(self):
        """Set the date range to show all available data and update the span selector"""
        try:
            if not self.plot_data.empty:
                # Get the min and max timestamps from all data sources
                all_timestamps = []
                if not self.transducer_data.empty:
                    all_timestamps.append(self.transducer_data['timestamp_utc'].min())
                    all_timestamps.append(self.transducer_data['timestamp_utc'].max())
                if not self.manual_data.empty:
                    all_timestamps.append(self.manual_data['timestamp_utc'].min())
                    all_timestamps.append(self.manual_data['timestamp_utc'].max())
                if not self.master_baro_data.empty:
                    all_timestamps.append(self.master_baro_data['timestamp_utc'].min())
                    all_timestamps.append(self.master_baro_data['timestamp_utc'].max())
                min_date = min(all_timestamps)
                max_date = max(all_timestamps)
                self.start_date.blockSignals(True)
                self.end_date.blockSignals(True)
                self.start_date.setDateTime(min_date)
                self.end_date.setDateTime(max_date)
                self.start_date.blockSignals(False)
                self.end_date.blockSignals(False)
                self.ax.set_xlim(min_date, max_date)
                if self.show_master_baro.isChecked() and hasattr(self, 'ax2') and self.ax2 is not None:
                    self.ax2.remove()
                    self.ax2 = None
                    self._plot_master_baro_data()
                self.canvas.draw()
                # Update the span selector to match the new range
                self._update_span_selector_to_dates()
                logger.debug(f"Set full date range from {min_date} to {max_date}")
            else:
                logger.debug("No data available to set full range")
        except Exception as e:
            logger.error(f"Error setting full date range: {e}")
            QMessageBox.warning(self, "Error", f"Failed to set full date range: {str(e)}")

    def _update_span_selector_to_dates(self):
        """Update the red manual span selector extent to match the current start and end date widgets"""
        try:
            start_dt = self.start_date.dateTime().toPyDateTime()
            end_dt = self.end_date.dateTime().toPyDateTime()
            
            # Convert python datetimes to matplotlib numeric dates
            start_num = mdates.date2num(start_dt)
            end_num = mdates.date2num(end_dt)
            
            # Update the extents of the existing SpanSelector
            if hasattr(self, 'span_selector') and self.span_selector is not None:
                # Disable selector briefly to prevent triggering its callback
                self.span_selector.active = False 
                self.span_selector.extents = (start_num, end_num)
                self.span_selector.active = True
                
                # Ensure the internal rectangle is updated (may be needed depending on matplotlib version)
                if hasattr(self.span_selector, 'rect') and self.span_selector.rect:
                    self.span_selector.rect.set_x(start_num)
                    self.span_selector.rect.set_width(end_num - start_num)

                self.canvas.draw_idle()
            else:
                logger.warning("Span selector not found or not initialized yet.")
                
        except Exception as e:
            logger.error(f"Error updating span selector: {e}")

    def apply_compensation_changes(self):
        """Apply compensation changes by correcting water level based on master baro data"""
        try:
            # Track changes for this instance
            changes = {}
            # Get mode from the compensation helper dialog parameters
            params = self.compensation_helper.get_current_parameters()
            
            # Add a delay to ensure the UI is responsive
            QApplication.processEvents()
            
            # Get the working dataset based on mode
            mode = params.get("mode", "missing")
            logger.debug(f"Compensation mode: {mode}")
            
            if mode == "selection":
                if self.selected_data is None or self.selected_data.empty:
                    # Use always-on-top message box
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText("No data selected for compensation.")
                    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                    msg_box.exec_()
                    return
                    
                # Keep only transducer data from selection
                # First check for our custom marker column
                if 'data_source_type' in self.selected_data.columns:
                    transducer_mask = self.selected_data['data_source_type'] == 'Transducer'
                # Then try the regular data_source column
                elif 'data_source' in self.selected_data.columns:
                    transducer_mask = self.selected_data['data_source'].str.contains('Transducer', case=False, na=False)
                else:
                    # If data_source column doesn't exist, use the transducer_data DataFrame indices
                    transducer_mask = self.selected_data.index.isin(self.transducer_data.index)
                
                df = self.selected_data[transducer_mask].copy()
            elif mode == "missing":
                # For missing ranges, only get data where baro_flag is not master or master_corrected
                df = self.transducer_data[~self.transducer_data['baro_flag'].isin(['master', 'master_corrected'])].copy()
            
            if df.empty:
                # Use always-on-top message box
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Error")
                msg_box.setText("No data found to compensate.")
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                return
                
            logger.debug(f"Working dataset size: {len(df)}")

            # Get the master baro data in the proper time range
            if not self.baro_data.empty:
                # Filter master baro data by timestamp range only (without using baro_flag)
                master_baro_mask = (self.baro_data['timestamp_utc'] >= df['timestamp_utc'].min()) & \
                                  (self.baro_data['timestamp_utc'] <= df['timestamp_utc'].max())
                master_data = self.baro_data[master_baro_mask].copy()
            else:
                master_data = pd.DataFrame()

            logger.debug(f"Master baro data size: {len(master_data)}")
            
            # Check if master data exists before continuing
            if master_data.empty:
                QMessageBox.warning(self, "Error", 
                                "No master barometric data available in the selected range. "
                                "Cannot perform compensation without master barometric data.")
                return
                
            # Check if pressure column exists
            if 'pressure' not in master_data.columns:
                QMessageBox.warning(self, "Error", 
                                "Master barometric data doesn't contain pressure readings. "
                                "Cannot perform compensation without pressure data.")
                return

            # STEP 1: COMPENSATION - Calculate and apply barometric compensation
            # Sort both datasets by timestamp
            df = df.sort_values('timestamp_utc')
            master_data = master_data.sort_values('timestamp_utc')
            
            # Interpolate master baro data to match our timestamps
            master_baro_interp = np.interp(
                mdates.date2num(df['timestamp_utc']),
                mdates.date2num(master_data['timestamp_utc']),
                master_data['pressure']
            )
            
            # Constants
            PSI_TO_FEET_OF_WATER = 2.31  # 1 PSI = 2.31 feet of water
            STANDARD_PRESSURE = 14.7  # Standard atmospheric pressure in PSI

            # Calculate the barometric correction in feet of water
            baro_correction_feet = (master_baro_interp - STANDARD_PRESSURE) * PSI_TO_FEET_OF_WATER
            
            # Calculate corrected water level
            corrected_levels = df['water_level'] - baro_correction_feet

            # Update the data in the water_level_master_corrected column but DON'T update flags yet
            df['water_level_master_corrected'] = corrected_levels
            
            # Save indices for later use
            indices_to_update = df.index
            
            # Update the main transducer_data DataFrame with corrected levels
            self.transducer_data.loc[indices_to_update, 'water_level_master_corrected'] = corrected_levels
            
            # Also update the combined plot_data (for backwards compatibility)
            self.plot_data.loc[indices_to_update, 'water_level_master_corrected'] = corrected_levels
            
            # STEP 2: SEGMENTATION AND LEVELING
            # Identify segments now, before flagging any data as master_corrected
            segments = self._identify_segments(self.transducer_data)
            logger.debug(f"Found {len(segments)} segments for leveling")
            
            # For each segment, apply the appropriate level adjustment
            for i, segment in enumerate(segments):
                # Skip segments that already have master/master_corrected flags
                if segment['baro_flag'].isin(['master', 'master_corrected']).all():
                    logger.debug(f"Segment {i+1} already has master/master_corrected flags, skipping")
                    continue
                    
                logger.debug(f"Processing segment {i+1}: {len(segment)} points from "
                            f"{segment['timestamp_utc'].min()} to {segment['timestamp_utc'].max()}")
                
                # Apply the leveling using the 3-tier priority system
                segment_indices = segment.index
                adjustment = 0.0
                level_method = "none"
                
                # Priority 1: Check for master/master_corrected data within 1 hour of segment start
                adjustment, level_method = self._find_reference_level_start(segment)
                
                # Priority 2: If no reference found, check for master/master_corrected data within 1 hour of segment end
                if adjustment == 0.0 and level_method == "none":
                    adjustment, level_method = self._find_reference_level_end(segment)
                
                # Priority 3: If still no reference found, use manual readings
                if adjustment == 0.0 and level_method == "none":
                    adjustment, level_method = self._find_manual_level_references(segment)
                
                # Apply adjustment if we found a reference
                if level_method != "none":
                    # Update the water level values
                    self.transducer_data.loc[segment_indices, 'water_level_master_corrected'] += adjustment
                    self.plot_data.loc[segment_indices, 'water_level_master_corrected'] += adjustment
                    
                    # Keep track that this segment was leveled (for flagging in step 3)
                    self.transducer_data.loc[segment_indices, '_needs_level_flag'] = True
                    self.plot_data.loc[segment_indices, '_needs_level_flag'] = True
                    
                    logger.debug(f"Applied level adjustment of {adjustment:.3f} ft to segment {i+1} "
                                f"using method: {level_method}")
                else:
                    logger.debug(f"No reference level found for segment {i+1}, left unleveled")
            
            # STEP 3: FLAGS - Update only the modification flags
            # Set 'baro_flag_mod' to 'master_mod' for all compensated data
            self.transducer_data.loc[indices_to_update, 'baro_flag_mod'] = 'master_mod'
            self.plot_data.loc[indices_to_update, 'baro_flag_mod'] = 'master_mod'
            
            # Set 'level_flag_baro_mod' to 'master_mod' for leveled data
            # First make sure the temporary flag column exists
            if '_needs_level_flag' not in self.transducer_data.columns:
                self.transducer_data['_needs_level_flag'] = False
            if '_needs_level_flag' not in self.plot_data.columns:
                self.plot_data['_needs_level_flag'] = False
            
            # Then update level flags where needed
            level_mask = self.transducer_data['_needs_level_flag'] == True
            self.transducer_data.loc[level_mask, 'level_flag_baro_mod'] = 'master_mod'
            self.plot_data.loc[level_mask, 'level_flag_baro_mod'] = 'master_mod'
            
            # Clear the temporary column
            self.transducer_data.drop('_needs_level_flag', axis=1, inplace=True, errors='ignore')
            self.plot_data.drop('_needs_level_flag', axis=1, inplace=True, errors='ignore')

            # Clear existing compensation lines
            if self.compensation_line_handles:
                for line in self.compensation_line_handles:
                    if line:
                        try:
                            line.remove()
                        except Exception as e:
                            logger.error(f"Error removing compensation line: {e}")
                self.compensation_line_handles = []
            
            # Draw the applied line directly with green color
            # Use the updated water_level_master_corrected that includes leveling adjustments
            line_handle, = self.ax.plot(
                self.transducer_data.loc[indices_to_update, 'timestamp_utc'],
                self.transducer_data.loc[indices_to_update, 'water_level_master_corrected'],
                color='green',
                linestyle='--',
                linewidth=2,
                label="Applied: Master Baro Corrected",
                zorder=6
            )
            
            self.compensation_line_handles = [line_handle]
            
            # Update the legend and redraw
            self.ax.legend(loc='upper right')
            self.canvas.draw()

            logger.debug(f"Applied compensation to {len(df)} points")
            
            # Track all changes for this instance  
            for idx in indices_to_update:
                changes[idx] = {
                    'water_level_master_corrected': self.transducer_data.loc[idx, 'water_level_master_corrected'],
                    'baro_flag_mod': 'master_mod'
                }
            
            # Also track level flag changes
            if level_mask.any():
                for idx in self.transducer_data[level_mask].index:
                    if idx not in changes:
                        changes[idx] = {}
                    changes[idx]['level_flag_baro_mod'] = 'master_mod'
            
            # Apply changes using the new tracking system
            if changes:
                self.apply_instance_edits(self.compensation_helper.instance_id, 'compensation', changes)

        except Exception as e:
            logger.error(f"Error applying compensation: {e}", exc_info=True)
            # Use always-on-top message box
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to apply compensation: {str(e)}")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()

    def preview_baseline(self, params):
        """Preview baseline adjustment with given parameters - no action on parameter changes"""
        # No action needed here - preview only happens on apply now
        logger.debug("Preview baseline called but no action taken (as requested)")
        pass

    def apply_baseline_changes(self):
        """Apply baseline changes - SIMPLIFIED VERSION"""
        try:
            # Get parameters
            params = self.baseline_helper.get_current_parameters()
            adjustment = params.get("adjustment_value", 0.0)
            
            if adjustment == 0:
                QMessageBox.information(self, "Info", "No adjustment to apply (0.0 ft)")
                return
            
            # Check if there's a selection first
            if self.selected_data is not None and not self.selected_data.empty:
                # Use selected data
                if 'data_source_type' in self.selected_data.columns:
                    transducer_mask = self.selected_data['data_source_type'] == 'Transducer'
                else:
                    transducer_mask = self.selected_data.index.isin(self.transducer_data.index)
                visible_data = self.selected_data[transducer_mask]
            else:
                # No selection - use visible range
                xlim = self.ax.get_xlim()
                x_min = matplotlib.dates.num2date(xlim[0]).replace(tzinfo=None)
                x_max = matplotlib.dates.num2date(xlim[1]).replace(tzinfo=None)
                
                # Find transducer data in visible range
                mask = (self.transducer_data['timestamp_utc'] >= x_min) & \
                       (self.transducer_data['timestamp_utc'] <= x_max)
                visible_data = self.transducer_data[mask]
            
            if visible_data.empty:
                QMessageBox.warning(self, "Error", "No transducer data in visible range")
                return
            
            # Simple adjustment - add to water_level_level_corrected
            indices = visible_data.index
            self.transducer_data.loc[indices, 'water_level_level_corrected'] = \
                self.transducer_data.loc[indices, 'water_level'] + adjustment
            
            # CRITICAL: Set the flag to indicate this data has been modified
            self.transducer_data.loc[indices, 'level_flag_mod'] = 'level_mod'
            
            # Also update plot_data if indices exist there
            common_indices = indices.intersection(self.plot_data.index)
            if len(common_indices) > 0:
                self.plot_data.loc[common_indices, 'water_level_level_corrected'] = \
                    self.plot_data.loc[common_indices, 'water_level'] + adjustment
                # Set flag in plot_data too
                self.plot_data.loc[common_indices, 'level_flag_mod'] = 'level_mod'
            
            # Simple plot update - just add a new line for adjusted data
            adjusted_data = visible_data.copy()
            adjusted_data['water_level'] = adjusted_data['water_level'] + adjustment
            
            # Plot the adjusted line in green
            self.ax.plot(adjusted_data['timestamp_utc'], 
                        adjusted_data['water_level'], 
                        'g-', 
                        label=f'Baseline Adjusted (+{adjustment} ft)',
                        linewidth=2,
                        alpha=0.8)
            
            # Store reference to this line so we can remove it later
            if not hasattr(self, 'baseline_lines'):
                self.baseline_lines = []
            self.baseline_lines.append(self.ax.lines[-1])  # Last added line
            
            # Update legend and refresh
            self.ax.legend()
            self.canvas.draw()
            
            # Log success instead of showing dialog
            if self.selected_data is not None and not self.selected_data.empty:
                logger.info(f"Applied {adjustment} ft adjustment to {len(visible_data)} selected points")
            else:
                logger.info(f"Applied {adjustment} ft adjustment to {len(visible_data)} points in visible range")
            
        except Exception as e:
            logger.error(f"Error in baseline adjustment: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Baseline adjustment failed: {str(e)}")
    
    def calculate_baseline_adjustment(self):
        """Calculate baseline adjustment by comparing transducer and manual readings"""
        try:
            # Check if we have both transducer and manual data
            if self.transducer_data.empty or self.manual_data.empty:
                logger.warning("Cannot calculate baseline: missing transducer or manual data")
                return None
            
            # Get the data range to work with
            if self.selected_data is not None and not self.selected_data.empty:
                # Use selected time range
                selected_times = self.selected_data['timestamp_utc']
                time_min = selected_times.min()
                time_max = selected_times.max()
            else:
                # Use visible range
                xlim = self.ax.get_xlim()
                time_min = matplotlib.dates.num2date(xlim[0]).replace(tzinfo=None)
                time_max = matplotlib.dates.num2date(xlim[1]).replace(tzinfo=None)
            
            # Filter manual readings within the time range
            manual_mask = (self.manual_data['timestamp_utc'] >= time_min) & \
                         (self.manual_data['timestamp_utc'] <= time_max)
            relevant_manual = self.manual_data[manual_mask]
            
            if relevant_manual.empty:
                logger.warning("No manual readings found in selected time range")
                return None
            
            # For each manual reading, find the closest transducer reading in time
            adjustments = []
            
            for _, manual_reading in relevant_manual.iterrows():
                manual_time = manual_reading['timestamp_utc']
                manual_level = manual_reading['water_level']
                
                # Find closest transducer reading (within reasonable time window, e.g., 1 hour)
                time_diff = abs(self.transducer_data['timestamp_utc'] - manual_time)
                closest_idx = time_diff.idxmin()
                
                # Check if closest reading is within 1 hour
                if time_diff[closest_idx].total_seconds() <= 3600:  # 1 hour = 3600 seconds
                    transducer_level = self.transducer_data.loc[closest_idx, 'water_level']
                    adjustment = manual_level - transducer_level
                    adjustments.append(adjustment)
                    
                    logger.debug(f"Manual: {manual_level:.3f} ft, Transducer: {transducer_level:.3f} ft, "
                               f"Adjustment: {adjustment:.3f} ft at {manual_time}")
            
            if not adjustments:
                logger.warning("No matching transducer readings found for manual measurements")
                return None
            
            # Calculate average adjustment
            avg_adjustment = np.mean(adjustments)
            std_adjustment = np.std(adjustments) if len(adjustments) > 1 else 0
            
            logger.info(f"Calculated baseline adjustment: {avg_adjustment:.3f} ± {std_adjustment:.3f} ft "
                       f"(from {len(adjustments)} manual readings)")
            
            return avg_adjustment
            
        except Exception as e:
            logger.error(f"Error calculating baseline adjustment: {e}", exc_info=True)
            return None

    def set_start_to_first_point(self):
        """Set the start date to the first point in the plot data and update the span selector"""
        if not self.plot_data.empty:
            min_date = self.plot_data['timestamp_utc'].min()
            self.start_date.setDateTime(min_date)
            # Update the span selector to match the new range
            self._update_span_selector_to_dates()

    def set_end_to_last_point(self):
        """Set the end date to the last point in the plot data and update the span selector"""
        if not self.plot_data.empty:
            max_date = self.plot_data['timestamp_utc'].max()
            self.end_date.setDateTime(max_date)
            # Update the span selector to match the new range
            self._update_span_selector_to_dates()

    def open_calculator(self):
        """Open the system calculator application"""
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Windows":
                subprocess.Popen("calc.exe")
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", "Calculator"])
            elif system == "Linux":
                # Try common Linux calculator apps
                for calc in ["gnome-calculator", "kcalc", "xcalc"]:
                    try:
                        subprocess.Popen([calc])
                        break
                    except FileNotFoundError:
                        continue
            else:
                logger.error(f"Unsupported platform for calculator: {system}")
        except Exception as e:
            logger.error(f"Error opening calculator: {e}")
            QMessageBox.warning(self, "Error", f"Could not open calculator: {str(e)}")

    def toggle_pause_spike_selection(self):
        """Temporarily pause or resume spike selection mode to allow navigation"""
        if not hasattr(self, 'spike_selection_mode') or not self.spike_selection_mode:
            return
            
        if not hasattr(self, 'spike_selection_paused'):
            self.spike_selection_paused = False
            
        self.spike_selection_paused = not self.spike_selection_paused
        
        if self.spike_selection_paused:
            # Pause mode - allow pan/zoom but keep selection state
            self.ax.set_navigate(True)
            self.canvas.setCursor(Qt.ArrowCursor)
            # Visual indication that selection is paused
            if hasattr(self, 'spike_helper') and self.spike_helper:
                self.spike_helper.status_label.setText("Selection PAUSED - Use Pan/Zoom. Click 'Resume' to continue selection.")
                if hasattr(self.spike_helper, 'pause_btn'):
                    self.spike_helper.pause_btn.setText("Resume Selection")
                    self.spike_helper.pause_btn.setStyleSheet("background-color: #f0d0d0;")
        else:
            # Resume selection mode
            self.ax.set_navigate(False)
            self.canvas.setCursor(Qt.CrossCursor)
            if hasattr(self, 'spike_helper') and self.spike_helper:
                self.spike_helper.status_label.setText("Continue selecting second point...")
                if hasattr(self.spike_helper, 'pause_btn'):
                    self.spike_helper.pause_btn.setText("Pause Selection")
                    self.spike_helper.pause_btn.setStyleSheet("background-color: #d0d0f0;")
        
        self.canvas.draw_idle()
    
    def _initialize_feedback_system(self):
        """Initialize the protocol feedback system"""
        try:
            logger.info("DEBUG: _initialize_feedback_system called")
            
            # Check if buttons exist
            logger.info(f"DEBUG: protocol_feedback_btn exists: {hasattr(self, 'protocol_feedback_btn')}")
            logger.info(f"DEBUG: help_btn exists: {hasattr(self, 'help_btn')}")
            
            # Try to get Google Drive service from main window (traverse parent hierarchy)
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'drive_service'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'drive_service'):
                self.drive_service = main_window.drive_service
                logger.info(f"DEBUG: Got drive_service from main window: {self.drive_service}")
            else:
                logger.info("DEBUG: No drive_service found in main window")
            
            # Try to get user name from parent if available
            if hasattr(self.parent(), 'user_name'):
                self.user_name = self.parent().user_name
                logger.info(f"DEBUG: Got user_name from parent: {self.user_name}")
            elif hasattr(self.parent(), 'user_auth_service'):
                try:
                    current_user_info = self.parent().user_auth_service.get_current_user_info()
                    if current_user_info:
                        self.user_name = current_user_info.get('username', 'CAESER Team Member')
                    else:
                        self.user_name = "CAESER Team Member"
                    logger.info(f"DEBUG: Got user_name from auth service: {self.user_name}")
                except:
                    self.user_name = "CAESER Team Member"
                    logger.info("DEBUG: Failed to get user from auth service, using default")
            else:
                self.user_name = "CAESER Team Member"
                logger.info("DEBUG: No user auth found, using default name")
            
            # Update feedback button visibility
            logger.info("DEBUG: About to update button visibility")
            self._update_protocol_feedback_button_visibility()
            
        except Exception as e:
            logger.error(f"Error initializing feedback system: {e}")
            self.user_name = "CAESER Team Member"
    
    def _update_protocol_feedback_button_visibility(self):
        """Update visibility of protocol feedback button based on Drive service availability"""
        try:
            logger.info("DEBUG: _update_protocol_feedback_button_visibility called")
            
            if hasattr(self, 'protocol_feedback_btn'):
                logger.info("DEBUG: protocol_feedback_btn exists, checking Drive service...")
                
                # Check if Google Drive service is available (same simple logic as main feedback button)
                is_available = bool(hasattr(self, 'drive_service') and self.drive_service)
                
                logger.info(f"DEBUG: Drive service available: {is_available}")
                logger.info(f"DEBUG: drive_service: {self.drive_service}")
                
                # Only show button if Google Drive is available
                self.protocol_feedback_btn.setVisible(is_available)
                
                if is_available:
                    logger.info("DEBUG: Protocol feedback button shown - Google Drive service available")
                else:
                    logger.info("DEBUG: Protocol feedback button hidden - No Google Drive service available")
                    
                logger.info(f"DEBUG: Protocol feedback button visibility set: {self.protocol_feedback_btn.isVisible()}")
            else:
                logger.error("DEBUG: protocol_feedback_btn does NOT exist!")
                
        except Exception as e:
            logger.error(f"Error updating protocol feedback button visibility: {e}")
            import traceback
            logger.error(f"DEBUG: Full traceback: {traceback.format_exc()}")
            # Hide button on error to be safe
            if hasattr(self, 'protocol_feedback_btn'):
                self.protocol_feedback_btn.setVisible(False)
    
    def open_protocol_feedback_dialog(self):
        """Open the water levels protocol feedback dialog"""
        try:
            # Since the button is only visible when service is available,
            # we can assume the service is available when this method is called
            if not hasattr(self, 'drive_service') or not self.drive_service:
                # This shouldn't happen since button visibility is controlled,
                # but added as a safety check
                QMessageBox.warning(self, "Service Unavailable", 
                                  "Google Drive service is not available. Please check your connection and authentication.")
                return
            
            # Get current well information
            well_number = "Unknown"
            if hasattr(self, 'transducer_data') and not self.transducer_data.empty:
                if 'well_number' in self.transducer_data.columns:
                    well_number = str(self.transducer_data['well_number'].iloc[0])
                elif 'TN113_number' in self.transducer_data.columns:
                    well_number = str(self.transducer_data['TN113_number'].iloc[0])
            
            # Get current data info
            data_info = {}
            if hasattr(self, 'transducer_data') and not self.transducer_data.empty:
                if 'timestamp_utc' in self.transducer_data.columns:
                    timestamps = pd.to_datetime(self.transducer_data['timestamp_utc'])
                    data_info = {
                        'start_date': timestamps.min().strftime('%Y-%m-%d'),
                        'end_date': timestamps.max().strftime('%Y-%m-%d'),
                        'total_points': len(self.transducer_data)
                    }
            
            # Import and open the dialog
            from .water_levels_protocol_feedback_dialog import WaterLevelsProtocolFeedbackDialog
            
            dialog = WaterLevelsProtocolFeedbackDialog(
                parent=self,
                drive_service=self.drive_service,
                user_name=self.user_name,
                well_number=well_number,
                current_data_info=data_info
            )
            
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error opening protocol feedback dialog: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to open protocol feedback dialog:\n{str(e)}")
    
    def open_help_dialog(self):
        """Open the comprehensive help dialog for this dialog"""
        try:
            from .water_level_edit_help_dialog import WaterLevelEditHelpDialog
            
            help_dialog = WaterLevelEditHelpDialog(parent=self)
            help_dialog.show()
            
        except Exception as e:
            logger.error(f"Error opening help dialog: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to open help dialog:\n{str(e)}")
    
    def open_user_notes_dialog(self):
        """Open the user notes dialog for data analysis notes"""
        try:
            # Get well number from the data
            well_number = "Unknown"
            if not self.transducer_data.empty and 'well_number' in self.transducer_data.columns:
                well_number = str(self.transducer_data['well_number'].iloc[0])
            elif not self.manual_data.empty and 'well_number' in self.manual_data.columns:
                well_number = str(self.manual_data['well_number'].iloc[0])
            
            # Ensure user_name is available
            if not hasattr(self, 'user_name') or not self.user_name:
                self.user_name = "CAESER Team Member"
            
            # Get database manager from parent if available
            db_manager = None
            if hasattr(self.parent(), 'db_manager'):
                db_manager = self.parent().db_manager
            elif hasattr(self, 'db_path') and self.db_path:
                # Create a simple object with current_db property
                class SimpleDBManager:
                    def __init__(self, db_path):
                        self.current_db = db_path
                db_manager = SimpleDBManager(self.db_path)
            else:
                QMessageBox.warning(self, "Database Unavailable", 
                                  "Database connection is not available for saving notes.")
                return
            
            from .user_notes_dialog import UserNotesDialog
            
            # Get selected time range if available
            selected_time_range = None
            if hasattr(self, 'start_date') and hasattr(self, 'end_date'):
                try:
                    start_time = self.start_date.dateTime().toPyDateTime()
                    end_time = self.end_date.dateTime().toPyDateTime()
                    
                    # Check if there's a meaningful selection by looking at the data
                    if hasattr(self, 'selected_data') and self.selected_data is not None and not self.selected_data.empty:
                        # Validate that the time range is reasonable (not the full dataset)
                        if not self.plot_data.empty:
                            full_start = self.plot_data['timestamp_utc'].min()
                            full_end = self.plot_data['timestamp_utc'].max()
                            
                            # If the selected range is significantly smaller than the full range, it's a real selection
                            selected_duration = (end_time - start_time).total_seconds()
                            full_duration = (full_end - full_start).total_seconds()
                            
                            if selected_duration < full_duration * 0.95:  # Selection is less than 95% of full range
                                selected_time_range = (start_time, end_time)
                                logger.info(f"Passing selected time range to notes dialog: {start_time} to {end_time}")
                            else:
                                logger.debug("Selected range covers most of the data, not passing to notes dialog")
                        else:
                            # If no plot data, just use the selection
                            selected_time_range = (start_time, end_time)
                            logger.info(f"Passing time range to notes dialog: {start_time} to {end_time}")
                except Exception as e:
                    logger.warning(f"Could not determine selected time range: {e}")
            
            dialog = UserNotesDialog(
                db_manager=db_manager,
                well_number=well_number,
                user_name=self.user_name,
                parent=self,
                selected_time_range=selected_time_range
            )
            
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error opening user notes dialog: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to open user notes dialog:\n{str(e)}")