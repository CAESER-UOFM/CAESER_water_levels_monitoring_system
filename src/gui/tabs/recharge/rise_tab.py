"""
RISE (Rapid Intensive Successive Events) method for recharge estimation.
This tab implements the RISE method for calculating recharge using water level data.
"""

import logging
import numpy as np
import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QPushButton, QGroupBox, QTableWidget, 
    QTableWidgetItem, QMessageBox, QDateEdit, QSplitter,
    QCheckBox, QFrame, QTabWidget, QGridLayout, QSizePolicy,
    QHeaderView, QSpinBox, QRadioButton, QButtonGroup,
    QAbstractItemView, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QDate
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd
from scipy import signal

from .db.rise_database import RiseDatabase
from .base_recharge_tab import BaseRechargeTab

logger = logging.getLogger(__name__)

class RiseTab(BaseRechargeTab):
    """
    Tab implementing the RISE method for recharge estimation.
    """
    
    def __init__(self, db_manager, parent=None):
        """
        Initialize the RISE tab.
        
        Args:
            db_manager: Database manager providing access to well data
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        logger.info(f"[DEBUG] RISE tab initialized with db_manager type: {type(db_manager).__name__}")
        self.selected_wells = []
        self.well_data = {}
        self.current_well = None
        self.water_years = []
        self.selected_water_year = None
        
        # Data management - separate display and calculation data
        self.display_data = None  # Store downsampled data for fast plotting
        self.raw_data = None  # Store the full resolution data for calculations
        self.processed_data = None  # Store the processed/filtered data
        self.data_loaded = {'display': False, 'full': False}  # Track what's loaded
        self.data_loading = False  # Prevent concurrent loading
        
        # Initialize database for RISE calculations
        self.rise_db = None
        self.init_database()
        
        # Initialize default settings for data processing
        self.current_settings = {
            'remove_outliers': True,
            'outlier_threshold': 3.0,
            'enable_smoothing': True,
            'smoothing_window': 3,
            'smoothing_type': 'Moving Average'
        }
        
        # Setup UI
        self.setup_ui()
    
    def _comprehensive_process_data(self, raw_data):
        """Comprehensive data processing method that applies all global settings."""
        if raw_data is None or raw_data.empty:
            return None
            
        try:
            import pandas as pd
            import numpy as np
            import re
            
            # Get current settings
            settings = getattr(self, 'current_settings', {})
            logger.info(f"[PROCESS_DEBUG] Processing data with settings: {list(settings.keys())}")
            
            # Start with raw data
            data = raw_data.copy()
            
            # Make sure timestamp is datetime
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Apply downsampling from settings
            downsample_freq = settings.get('downsample_frequency', 'None')
            if downsample_freq != 'None' and 'None' not in downsample_freq:
                # Extract frequency code from strings like "Daily (1D) - Recommended"
                freq_match = re.search(r'\((\w+)\)', downsample_freq)
                if freq_match:
                    freq_code = freq_match.group(1)
                    
                    if 'timestamp' in data.columns:
                        data = data.set_index('timestamp')
                    
                    method = settings.get('downsample_method', 'Mean')
                    # Extract method name from strings like "Median (for pumped wells) - Recommended"
                    method_name = method.split(' ')[0] if ' ' in method else method
                    
                    if method_name == "Mean":
                        data = data.resample(freq_code).mean()
                    elif method_name == "Median":
                        data = data.resample(freq_code).median()
                    elif method_name == "Last":
                        data = data.resample(freq_code).last()
                        
                    data = data.reset_index()
                    logger.info(f"Applied {freq_code} downsampling using {method_name} method")
            
            # Apply smoothing if enabled in settings
            if settings.get('enable_smoothing', False):
                window = settings.get('smoothing_window', 3)
                if 'level' in data.columns:
                    data['level'] = data['level'].rolling(window=window, center=False).mean()
                    logger.info(f"[PROCESS_DEBUG] Applied smoothing with window {window}")
            
            # Drop NaN values
            data = data.dropna()
            
            # Final validation to ensure no NaN/Inf values remain
            if 'level' in data.columns:
                if data['level'].isna().any():
                    logger.warning(f"Removing {data['level'].isna().sum()} remaining NaN values")
                    data = data.dropna(subset=['level'])
                    
                if not np.isfinite(data['level']).all():
                    logger.warning("Found non-finite values in level data, removing them")
                    data = data[np.isfinite(data['level'])]
            
            logger.info(f"[PROCESS_DEBUG] Data processing complete: {len(raw_data)} -> {len(data)} points")
            return data
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return raw_data.copy()  # Return unprocessed data on error
    
    def _simple_process_data(self, raw_data):
        """Simple data processing method that applies smoothing based on settings (deprecated)."""
        # Keep for backward compatibility, but use comprehensive method
        return self._comprehensive_process_data(raw_data)
    
    def init_database(self):
        """Initialize the RISE database connection and tables."""
        try:
            # Get database path from data manager
            if hasattr(self.db_manager, 'current_db'):
                db_path = self.db_manager.current_db
            else:
                logger.warning("Could not get database path from db manager")
                return
            
            # Initialize RISE database manager
            self.rise_db = RiseDatabase(db_path)
            
            # Create tables if they don't exist
            success = self.rise_db.create_tables()
            if success:
                logger.info("RISE database initialized successfully")
            else:
                logger.error("Failed to initialize RISE database tables")
                self.rise_db = None
                
        except Exception as e:
            logger.error(f"Error initializing RISE database: {e}")
            self.rise_db = None
    
    def setup_ui(self):
        """Set up the UI for the RISE tab."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "The RISE method estimates recharge based on water level rises "
            "multiplied by specific yield. "
            "It identifies rapid water level rises and calculates recharge for each rise event."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Create main splitter (Parameters on left, Plot on right)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)  # Wider handle for easier dragging
        
        # Left panel - Parameters and results
        left_panel = self.create_left_panel()
        self.main_splitter.addWidget(left_panel)
        
        # Right panel - Plot visualization
        right_panel = self.create_plot_panel()
        self.main_splitter.addWidget(right_panel)
        
        # Set splitter sizes to match fixed widths (400px left, 800px right)
        self.main_splitter.setSizes([400, 800])
        
        layout.addWidget(self.main_splitter)
    
    def create_left_panel(self):
        """Create the left panel with tabs for parameters, event selection, and results."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for parameters and results
        self.left_tabs = QTabWidget()
        
        
        # Event Selection tab
        event_selection_panel = self.create_event_selection_panel()
        self.left_tabs.addTab(event_selection_panel, "Event Selection")
        
        # Results tab
        results_panel = self.create_results_panel()
        self.left_tabs.addTab(results_panel, "Results")
        
        left_layout.addWidget(self.left_tabs)
        
        # Set fixed width for visual consistency across all tabs
        left_widget.setFixedWidth(400)
        
        return left_widget
    
    
    def create_event_selection_panel(self):
        """Create the event selection panel with filtering and events table."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Well selection
        well_layout = QHBoxLayout()
        well_layout.addWidget(QLabel("Well:"))
        self.well_combo = QComboBox()
        self.well_combo.setEnabled(False)
        self.well_combo.currentIndexChanged.connect(self.on_well_selected)
        well_layout.addWidget(self.well_combo)
        layout.addLayout(well_layout)
        
        # Step 1: Identify Events button
        self.identify_events_btn = QPushButton("Identify Events")
        self.identify_events_btn.setEnabled(False)
        self.identify_events_btn.setMinimumHeight(40)
        self.identify_events_btn.clicked.connect(self.identify_rise_events_ui)
        self.identify_events_btn.setToolTip("Analyze water level data to identify potential rise events. All parameters are configured in Global Settings.")
        self.identify_events_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        layout.addWidget(self.identify_events_btn)
        
        # Water year filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Water Year:"))
        self.water_year_combo = QComboBox()
        self.water_year_combo.addItem("All Water Years", "all")
        self.water_year_combo.currentIndexChanged.connect(self.filter_events_by_water_year)
        self.water_year_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        filter_layout.addWidget(self.water_year_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Events table
        self.event_selection_table = QTableWidget()
        self.event_selection_table.setColumnCount(6)
        self.event_selection_table.setHorizontalHeaderLabels([
            "Include", "ID", "Water Year", "Date", "Rise (ft)", "Recharge (in)"
        ])
        self.event_selection_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.event_selection_table.selectionModel().selectionChanged.connect(self.on_event_selected)
        self.event_selection_table.verticalHeader().setVisible(False)  # Hide row numbers
        self.event_selection_table.setAlternatingRowColors(True)
        layout.addWidget(self.event_selection_table)
        
        # Select/deselect buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_events)
        select_all_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_events)
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        button_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(button_layout)
        
        # Step 2: Calculate Recharge button
        self.calculate_recharge_btn = QPushButton("Calculate Recharge for Selected")
        self.calculate_recharge_btn.clicked.connect(self.calculate_recharge_for_selected)
        self.calculate_recharge_btn.setEnabled(False)  # Disabled until events are identified
        self.calculate_recharge_btn.setMinimumHeight(40)  # Make button larger and more prominent
        self.calculate_recharge_btn.setToolTip("Calculate recharge values for the selected rise events from the table above.")
        self.calculate_recharge_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        layout.addWidget(self.calculate_recharge_btn)
        
        return panel
    
    def create_results_panel(self):
        """Create the results panel with yearly summary."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Create yearly statistics table
        self.yearly_stats_table = QTableWidget()
        self.yearly_stats_table.setColumnCount(4)
        self.yearly_stats_table.setHorizontalHeaderLabels([
            "Water Year", "Rises Count", "Recharge (in)", "Annual Rate (in/yr)"
        ])
        self.yearly_stats_table.setSortingEnabled(True)
        self.yearly_stats_table.setAlternatingRowColors(True)
        self.yearly_stats_table.verticalHeader().setVisible(False)
        layout.addWidget(self.yearly_stats_table)
        
        # Summary section
        summary_group = QGroupBox("Recharge Summary")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setSpacing(10)
        
        # Total recharge
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("Total Recharge:"))
        self.total_recharge_label = QLabel("0.0 inches")
        self.total_recharge_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        total_layout.addWidget(self.total_recharge_label)
        total_layout.addStretch()
        summary_layout.addLayout(total_layout)
        
        # Annual rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Annual Rate:"))
        self.annual_rate_label = QLabel("0.0 inches/year")
        self.annual_rate_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        rate_layout.addWidget(self.annual_rate_label)
        rate_layout.addStretch()
        summary_layout.addLayout(rate_layout)
        
        # Event count
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Total Rises:"))
        self.events_count_label = QLabel("0")
        self.events_count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        count_layout.addWidget(self.events_count_label)
        count_layout.addStretch()
        summary_layout.addLayout(count_layout)
        
        # Average annual recharge
        avg_layout = QHBoxLayout()
        avg_layout.addWidget(QLabel("Avg. Annual Recharge:"))
        self.avg_annual_label = QLabel("0.0 inches/year")
        self.avg_annual_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        avg_layout.addWidget(self.avg_annual_label)
        avg_layout.addStretch()
        summary_layout.addLayout(avg_layout)
        
        layout.addWidget(summary_group)
        
        # Export options
        export_layout = QHBoxLayout()
        
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_to_csv)
        export_csv_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        export_layout.addWidget(export_csv_btn)
        
        export_excel_btn = QPushButton("Export to Excel")
        export_excel_btn.clicked.connect(self.export_to_excel)
        export_excel_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        export_layout.addWidget(export_excel_btn)
        
        layout.addLayout(export_layout)
        
        # Database save/load section
        db_group = QGroupBox("Database Operations")
        db_layout = QVBoxLayout(db_group)
        
        # Save button
        self.save_to_db_btn = QPushButton("Save to Database")
        self.save_to_db_btn.clicked.connect(self.save_to_database)
        self.save_to_db_btn.setToolTip("Save the current RISE calculation to the database")
        self.save_to_db_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        db_layout.addWidget(self.save_to_db_btn)
        
        # Load button
        self.load_from_db_btn = QPushButton("Load from Database")
        self.load_from_db_btn.clicked.connect(self.load_from_database)
        self.load_from_db_btn.setToolTip("Load a previous RISE calculation from the database")
        self.load_from_db_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        db_layout.addWidget(self.load_from_db_btn)
        
        # Compare button
        self.compare_btn = QPushButton("Compare Calculations")
        self.compare_btn.clicked.connect(self.compare_calculations)
        self.compare_btn.setToolTip("Compare multiple RISE calculations")
        self.compare_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        db_layout.addWidget(self.compare_btn)
        
        layout.addWidget(db_group)
        
        # Create a reference to the results table for compatibility
        # with existing code, but it won't be displayed
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Water Year", "Date", "Rise (ft)", 
            "Recharge (in)", "Daily Rate (in/yr)"
        ])
        
        # Create reference to results_water_year_combo for compatibility
        # with existing code, but it won't be displayed or used
        self.results_water_year_combo = QComboBox()
        self.results_water_year_combo.addItem("All Years", "all")
        
        return panel
    
    def create_plot_panel(self):
        """Create the plot panel for visualization."""
        group_box = QGroupBox("Visualization")
        group_box.setFixedWidth(800)  # Fixed width for visual consistency
        layout = QVBoxLayout(group_box)
        
        # Plot panel - use BaseRechargeTab's canvas (already initialized)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Plot options panel - use base class display options and add RISE-specific ones
        options_group = self.create_plot_display_options()
        options_layout = options_group.layout()
        
        # Set processed data checkbox to checked by default for RISE tab
        if hasattr(self, 'show_processed_data'):
            self.show_processed_data.setChecked(True)
        
        # Add RISE-specific display options in the existing horizontal layout
        # Find the third column position (after left and right columns from base class)
        rise_column = QVBoxLayout()
        rise_column.setSpacing(4)  # Tight vertical spacing
        
        self.show_rise_events = QCheckBox("Show Rise Events")
        self.show_rise_events.setChecked(True)
        self.show_rise_events.setToolTip("Highlight identified rise events in red")
        self.show_rise_events.stateChanged.connect(self.update_plot)
        rise_column.addWidget(self.show_rise_events)
        
        self.show_selected_event = QCheckBox("Highlight Selected")
        self.show_selected_event.setChecked(True)
        self.show_selected_event.setToolTip("Highlight the currently selected event with a green fill")
        self.show_selected_event.stateChanged.connect(self.update_plot)
        rise_column.addWidget(self.show_selected_event)
        
        # Insert the RISE column before the stretch
        options_layout.insertLayout(2, rise_column)  # Insert at position 2 (after left and right columns)
        
        # Add refresh button as a fourth column at the same level
        button_column = QVBoxLayout()
        button_column.setSpacing(4)
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self.update_plot)
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """)
        refresh_btn.setMaximumWidth(100)  # Keep button compact
        button_column.addWidget(refresh_btn)
        button_column.addStretch()  # Center the button vertically
        
        # Insert the button column before the final stretch
        options_layout.insertLayout(3, button_column)  # Insert at position 3 (after RISE column)
        
        # Keep the compact height since everything is now in one row
        options_group.setMaximumHeight(70)  # Back to original compact height
        
        layout.addWidget(options_group)
        
        return group_box
    
    def update_well_selection(self, selected_wells):
        """Update the list of selected wells."""
        # Prevent redundant updates if selection hasn't changed
        if self.selected_wells == selected_wells:
            return
            
        self.selected_wells = selected_wells
        
        # Clear data cache when wells change
        self._clear_data_cache()
        
        # Update combo box
        self.well_combo.clear()
        
        if selected_wells:
            self.well_combo.setEnabled(True)
            self.identify_events_btn.setEnabled(True)
            
            for well_id, cae_number in selected_wells:
                # well_id is the Well Number, cae_number is the CAE Number
                # Display well number as primary, with CAE number in parentheses if different
                if cae_number and cae_number != well_id:
                    display_name = f"{well_id} ({cae_number})"
                else:
                    # If CAE number is same as well number or missing, just show the well number
                    display_name = well_id
                self.well_combo.addItem(display_name, well_id)
        else:
            self.well_combo.setEnabled(False)
            self.identify_events_btn.setEnabled(False)
            self.calculate_recharge_btn.setEnabled(False)
    
    def on_well_selected(self, index):
        """Handle well selection from dropdown."""
        logger.info(f"[PLOT_DEBUG] on_well_selected called with index: {index}")
        
        if index < 0:
            logger.info(f"[PLOT_DEBUG] Invalid index, returning")
            return
            
        well_id = self.well_combo.currentData()
        well_name = self.well_combo.currentText()
        logger.info(f"[PLOT_DEBUG] Well selected: {well_name} (ID: {well_id})")
        
        # If same well is selected, don't reload
        if self.current_well == well_id:
            logger.info(f"[PLOT_DEBUG] Same well already selected, returning")
            return
            
        logger.info(f"[PLOT_DEBUG] Switching from well {self.current_well} to {well_id}")
        self.current_well = well_id
        
        # Clear any existing results and data cache for new well
        logger.info(f"[PLOT_DEBUG] Clearing results and data cache")
        self.clear_results()
        self._clear_data_cache()
        
        # Reset selected water year
        self.selected_water_year = "all"
        
        # Switch to Parameters tab
        self.left_tabs.setCurrentIndex(0)  # Switch to Event Selection tab when well changes
        
        # Data loading disabled - using centralized preprocessing from parent tab
        logger.info(f"[PLOT_DEBUG] Skipping individual data loading - waiting for shared data from centralized preprocessing")
            
        # Update the status in the UI
        self.identify_events_btn.setText("Identify Events")
        self.identify_events_btn.setEnabled(True)
        # Reset step 2 button
        self.calculate_recharge_btn.setEnabled(False)
        logger.info(f"[PLOT_DEBUG] Well selection complete for {well_name}")
    
    def _clear_data_cache(self):
        """Clear all cached data when well changes."""
        self.display_data = None
        self.raw_data = None
        self.processed_data = None
        self.data_loaded = {'display': False, 'full': False}
    
    def load_display_data(self, well_id):
        """Load downsampled data for quick display/preview."""
        # DISABLED: Using centralized preprocessing from parent tab
        logger.info(f"[PLOT_DEBUG] load_display_data disabled - using centralized preprocessing")
        return
        
        logger.info(f"[PLOT_DEBUG] load_display_data called for well {well_id}")
        logger.info(f"[PLOT_DEBUG] Current state - data_loading: {self.data_loading}, data_loaded: {self.data_loaded}")
        
        if self.data_loading or self.data_loaded['display']:
            logger.info(f"[PLOT_DEBUG] Skipping load - already loading or loaded")
            return
            
        try:
            import time
            start_time = time.time()
            self.data_loading = True
            logger.info(f"[PLOT_DEBUG] Starting data load for well {well_id}")
            
            if hasattr(self.data_manager, 'get_well_data'):
                # Load ALL available data with downsampling for display
                logger.debug(f"Loading all available data for display (downsampled)")
                
                logger.info(f"[DEBUG] About to call {type(self.data_manager).__name__}.get_well_data()")
                query_start = time.time()
                df = self.data_manager.get_well_data(
                    well_id, 
                    downsample=None  # Load raw data without hardcoded downsampling
                )
                query_time = time.time() - query_start
                logger.debug(f"Database query took {query_time:.2f} seconds")
                logger.info(f"[DEBUG] Data manager call completed, returned {len(df) if df is not None else 0} rows")
                
                if df is not None and not df.empty:
                    logger.info(f"[PLOT_DEBUG] Successfully loaded {len(df)} display data points for well {well_id}")
                    
                    # Standardize column names and store as raw data
                    self.raw_data = self._standardize_dataframe(df)
                    
                    # Store display data for backward compatibility
                    self.display_data = self.raw_data
                    
                    # Process data according to global settings (like ERC tab)
                    logger.info(f"[PLOT_DEBUG] Processing data with global settings...")
                    try:
                        # Use comprehensive processing that applies all global settings
                        self.processed_data = self._comprehensive_process_data(self.raw_data.copy())
                        logger.info(f"[PLOT_DEBUG] Processed data created: {len(self.processed_data)} points")
                    except Exception as e:
                        logger.error(f"[PLOT_DEBUG] Processing failed: {e}", exc_info=True)
                        # Fallback: use raw data as processed data
                        self.processed_data = self.raw_data.copy()
                    
                    self.data_loaded['display'] = True
                    logger.info(f"[PLOT_DEBUG] Data stored (raw_data and processed_data), updating data_loaded to: {self.data_loaded}")
                    
                    # Set date range based on available data
                    self.set_date_range_from_data(df)
                    
                    # Update plot with display data
                    plot_start = time.time()
                    logger.info(f"[PLOT_DEBUG] About to call update_plot()...")
                    try:
                        # Ensure matplotlib figure exists before plotting
                        if not hasattr(self, 'figure') or self.figure is None:
                            logger.error(f"[PLOT_DEBUG] Figure not initialized!")
                            return
                        if not hasattr(self, 'canvas') or self.canvas is None:
                            logger.error(f"[PLOT_DEBUG] Canvas not initialized!")
                            return
                            
                        self.update_plot()
                        logger.info(f"[PLOT_DEBUG] Plot update succeeded")
                        
                        # Force canvas refresh
                        self.canvas.draw()
                        logger.info(f"[PLOT_DEBUG] Canvas.draw() called to force refresh")
                        
                    except AttributeError as e:
                        logger.error(f"[PLOT_DEBUG] update_plot method missing: {e}")
                        logger.error(f"[PLOT_DEBUG] Available methods: {[m for m in dir(self) if 'plot' in m.lower()]}")
                        # Try to show an empty plot at least
                        self._show_empty_plot(f"AttributeError: {e}")
                    except Exception as e:
                        logger.error(f"[PLOT_DEBUG] Plot update failed: {e}")
                        # Try to show an empty plot with error message
                        self._show_empty_plot(f"Plot update failed: {e}")
                    plot_time = time.time() - plot_start
                    
                    total_time = time.time() - start_time
                    logger.debug(f"Plot update took {plot_time:.2f} seconds")
                    logger.info(f"[PLOT_DEBUG] Total display data loading took {total_time:.2f} seconds")
                    return
                else:
                    logger.warning(f"[PLOT_DEBUG] No data returned for well {well_id}")
                    # Show proper no data message instead of synthetic data
                    self._show_empty_plot(f"No water level data available for well {well_id}")
                    return
            
        except Exception as e:
            logger.error(f"[PLOT_DEBUG] Error loading display data: {e}", exc_info=True)
            # Show error message instead of synthetic data
            self._show_empty_plot(f"Error loading data: {str(e)}")
            return
        finally:
            self.data_loading = False
            logger.info(f"[PLOT_DEBUG] Data loading finished, data_loading reset to False")
    
    def _show_empty_plot(self, message="No data available"):
        """Show an empty plot with a message when data loading fails."""
        try:
            if hasattr(self, 'figure') and self.figure is not None:
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                ax.set_title(message)
                ax.set_xlabel("Date")
                ax.set_ylabel("Water Level (ft)")
                ax.grid(True)
                if hasattr(self, 'canvas') and self.canvas is not None:
                    self.canvas.draw()
                logger.info(f"[PLOT_DEBUG] Showing empty plot with message: {message}")
        except Exception as e:
            logger.error(f"[PLOT_DEBUG] Failed to show empty plot: {e}")
    
    def load_full_data_for_calculations(self, well_id):
        """Load full resolution data for recharge calculations."""
        # DISABLED: Using centralized preprocessing from parent tab
        logger.info(f"[PLOT_DEBUG] load_full_data_for_calculations disabled - using shared data")
        return True  # Return True to indicate success
        
        if self.data_loading or self.data_loaded['full']:
            return True
            
        try:
            self.data_loading = True
            logger.info(f"Loading full resolution data for calculations - well {well_id}")
            
            if hasattr(self.data_manager, 'get_well_data'):
                # Load ALL available data with NO downsampling for calculations
                df = self.data_manager.get_well_data(
                    well_id,
                    downsample=None  # No downsampling - full resolution
                )
                
                if df is not None and not df.empty:
                    logger.info(f"Loaded {len(df)} full resolution data points for calculations")
                    
                    # Standardize column names
                    df = self._standardize_dataframe(df)
                    
                    # Store full resolution data for calculations
                    self.raw_data = df
                    self.data_loaded['full'] = True
                    return True
                else:
                    logger.error("Failed to load full resolution data")
                    return False
            else:
                logger.error("Data manager does not have get_well_data method")
                return False
                
        except Exception as e:
            logger.error(f"Error loading full resolution data: {e}", exc_info=True)
            QMessageBox.warning(
                self, "Data Loading Error", 
                f"Failed to load full resolution data for well {well_id}: {str(e)}"
            )
            return False
        finally:
            self.data_loading = False
    
    def _standardize_dataframe(self, df):
        """Standardize dataframe column names and formats."""
        # Check column names and rename if necessary
        if 'timestamp_utc' in df.columns and 'water_level' in df.columns:
            df = df.rename(columns={
                'timestamp_utc': 'timestamp',
                'water_level': 'level'
            })
        
        # Make sure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ensure level column is numeric to prevent string subtraction errors
        if 'level' in df.columns:
            df['level'] = pd.to_numeric(df['level'], errors='coerce')
            # Drop any rows where level conversion failed (resulted in NaN)
            df = df.dropna(subset=['level'])
        
        return df
    
    def load_well_data(self, well_id):
        """DEPRECATED - use load_display_data or load_full_data_for_calculations instead."""
        logger.warning("load_well_data is deprecated - using load_display_data")
        self.load_display_data(well_id)
    
    def _create_synthetic_data(self):
        """Create synthetic data for demonstration purposes."""
        # Create a 2-year date range with 15-minute intervals
        start_date = datetime.now() - timedelta(days=730)  # 2 years ago
        end_date = datetime.now()
        
        # Generate timestamps at 15-minute intervals
        timestamps = []
        current = start_date
        while current <= end_date:
            timestamps.append(current)
            current += timedelta(minutes=15)
        
        # Generate water levels with trends and noise
        levels = []
        base_level = 100.0
        annual_cycle = 2.0  # 2 foot annual cycle
        
        for ts in timestamps:
            # Annual cycle component (lowest in late summer, highest in early spring)
            day_of_year = ts.timetuple().tm_yday
            annual_component = annual_cycle * np.sin(2 * np.pi * (day_of_year - 60) / 365.0)
            
            # Random events component (occasional rises)
            event_component = 0
            if np.random.random() < 0.001:  # Occasional rise events
                event_component = np.random.uniform(0.5, 2.0)
            
            # Noise component
            noise = np.random.normal(0, 0.05)
            
            # Combine components
            level = base_level + annual_component + event_component + noise
            
            # Add slow decline over time (0.5 ft per year)
            days_since_start = (ts - start_date).days
            decline = 0.5 * days_since_start / 365.0
            
            levels.append(level - decline)
        
        # Create pandas DataFrames - both display and full data
        full_data = pd.DataFrame({
            'timestamp': pd.to_datetime(timestamps),  # Ensure proper datetime format
            'level': levels
        })
        
        # Create downsampled display data (daily)
        display_data = full_data.set_index('timestamp').resample('1D').mean().reset_index()
        
        # Store both datasets
        self.raw_data = full_data  # Full resolution synthetic data
        self.display_data = display_data  # Downsampled for display
        self.data_loaded = {'display': True, 'full': True}
        
        logger.debug(f"Generated synthetic data: {len(self.raw_data)} full points, {len(self.display_data)} display points")
        
        # Don't process data automatically - wait for user to click Calculate
        # Just update the plot to show display data
        try:
            self.update_plot()
            logger.info(f"[DEBUG] Synthetic data plot update succeeded")
        except AttributeError as e:
            logger.error(f"[DEBUG] update_plot method missing in synthetic data: {e}")
        except Exception as e:
            logger.error(f"[DEBUG] Synthetic data plot update failed: {e}")
    
    def set_date_range_from_data(self, data):
        """Set date range based on available data."""
        # RISE tab doesn't have date filtering UI currently
        # This is a placeholder method for future date range functionality
        if data is not None and not data.empty and 'timestamp' in data.columns:
            # Log the actual date range of the data for information
            start_date = data['timestamp'].min()
            end_date = data['timestamp'].max()
            logger.debug(f"Data date range: {start_date} to {end_date}")
        else:
            logger.debug("No valid data for date range detection")
    
    def set_full_date_range(self):
        """Set date range to cover all available data."""
        if self.current_well and self.current_well in self.well_data:
            self.set_date_range_from_data(self.well_data[self.current_well])
    
    def calculate_recharge(self):
        """Calculate recharge using the RISE method."""
        logger.info("=" * 50)
        logger.info("CALCULATING RECHARGE")
        
        # Ensure we have a current well selected
        if not self.current_well:
            QMessageBox.warning(self, "No Well Selected", "Please select a well before calculating recharge.")
            return
        
        # Clear previous results
        self.clear_results()
        
        # Load full resolution data for accurate calculations
        logger.info("Loading full resolution data for calculations...")
        if not self.load_full_data_for_calculations(self.current_well):
            QMessageBox.critical(
                self, "Data Loading Error", 
                "Failed to load full resolution data for calculations. Cannot proceed."
            )
            return
        
        # Get parameters from unified settings
        if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
            settings = self.parent.unified_settings.get_method_settings('RISE')
            rise_threshold = settings.get('rise_threshold', 0.2)
            specific_yield = settings.get('specific_yield', 0.2)
            water_year_month = settings.get('water_year_month', 10)
            water_year_day = settings.get('water_year_day', 1)
            logger.info("Using parameters from global unified settings")
        else:
            # Fallback to default values if unified settings not available
            rise_threshold = 0.2
            specific_yield = 0.2
            water_year_month = 10
            water_year_day = 1
            logger.warning("Unified settings not available - using default parameters")
        
        # Log parameters
        logger.info(f"Parameters (from Global Settings):")
        logger.info(f"- Rise threshold: {rise_threshold} ft")
        logger.info(f"- Specific yield: {specific_yield}")
        logger.info(f"- Water year starts: Month {water_year_month}, Day {water_year_day}")
        logger.info(f"- Full resolution data loaded: {len(self.raw_data)} points")
        
        try:
            # Process the data (downsampling, filtering, etc.)
            self.process_data()
            
            if not hasattr(self, 'processed_data') or self.processed_data is None or self.processed_data.empty:
                logger.error("No processed data available")
                QMessageBox.warning(
                    self, "Calculation Error", 
                    "No processed data available. Please check your data preprocessing settings."
                )
                return
                
            # Identify rise events using the RISE method
            self.identify_rise_events(
                self.processed_data,
                rise_threshold=rise_threshold,
                time_window=None,  # No longer used in RISE method
                specific_yield=specific_yield
            )
            
            # If we successfully calculated rises, update the plot
            if hasattr(self, 'rise_events') and self.rise_events:
                # Update the plot
                self.update_plot()
                
                # Switch to Results tab
                self.left_tabs.setCurrentIndex(2)  # Results tab is index 2
                
                # Show a success message
                QMessageBox.information(
                    self, 
                    "Calculation Complete", 
                    f"Recharge calculation completed successfully.\n"
                    f"Found {len(self.rise_events)} rises with total recharge of {self.total_recharge_label.text()}"
                )
        
        except Exception as e:
            logger.error(f"Error in calculate_recharge: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Calculation Error", 
                f"Failed to calculate recharge: {str(e)}"
            )
    
    def identify_rise_events_ui(self):
        """Step 1: Identify potential rise events and populate the table for user review."""
        logger.info("=" * 50)
        logger.info("IDENTIFYING RISE EVENTS")
        
        # Ensure we have a current well selected
        if not self.current_well:
            QMessageBox.warning(self, "No Well Selected", "Please select a well before identifying events.")
            return
        
        # Clear previous events
        self.event_selection_table.setRowCount(0)
        
        # Load full resolution data for accurate calculations
        logger.info("Loading full resolution data for event identification...")
        if not self.load_full_data_for_calculations(self.current_well):
            QMessageBox.critical(
                self, "Data Loading Error", 
                "Failed to load full resolution data for event identification. Cannot proceed."
            )
            return
        
        # Get parameters from unified settings
        if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
            settings = self.parent.unified_settings.get_method_settings('RISE')
            rise_threshold = settings.get('rise_threshold', 0.2)
            specific_yield = settings.get('specific_yield', 0.2)
            water_year_month = settings.get('water_year_month', 10)
            water_year_day = settings.get('water_year_day', 1)
            logger.info("Using parameters from global unified settings")
        else:
            # Fallback to default values if unified settings not available
            rise_threshold = 0.2
            specific_yield = 0.2
            water_year_month = 10
            water_year_day = 1
            logger.warning("Unified settings not available - using default parameters")
        
        # Log parameters
        logger.info(f"Parameters (from Global Settings):")
        logger.info(f"- Rise threshold: {rise_threshold} ft")
        logger.info(f"- Specific yield: {specific_yield}")
        logger.info(f"- Water year starts: Month {water_year_month}, Day {water_year_day}")
        logger.info(f"- Full resolution data loaded: {len(self.raw_data)} points")
        
        try:
            # Process the data (downsampling, filtering, etc.)
            self.process_data()
            
            if not hasattr(self, 'processed_data') or self.processed_data is None or self.processed_data.empty:
                logger.error("No processed data available")
                QMessageBox.warning(
                    self, "Event Identification Error", 
                    "No processed data available. Please check your data preprocessing settings."
                )
                return
                
            # Identify rise events without calculating recharge yet
            self.identify_rise_events_only(
                self.processed_data,
                rise_threshold=rise_threshold,
                specific_yield=specific_yield,
                water_year_month=water_year_month,
                water_year_day=water_year_day
            )
            
            # If we successfully identified events, populate the table
            if hasattr(self, 'potential_rise_events') and self.potential_rise_events:
                self.populate_events_table(self.potential_rise_events)
                
                # Enable the second step button
                self.calculate_recharge_btn.setEnabled(True)
                
                # Update the plot to show identified events
                self.update_plot()
                
                # Show a success message
                QMessageBox.information(
                    self, 
                    "Event Identification Complete", 
                    f"Identified {len(self.potential_rise_events)} potential rise events.\n"
                    f"Review the events in the table below and select which ones to include in recharge calculation."
                )
        
        except Exception as e:
            logger.error(f"Error in identify_rise_events_ui: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Event Identification Error", 
                f"Failed to identify rise events: {str(e)}"
            )
    
    def calculate_recharge_for_selected(self):
        """Step 2: Calculate recharge for the selected events from the table."""
        logger.info("=" * 50)
        logger.info("CALCULATING RECHARGE FOR SELECTED EVENTS")
        
        if not hasattr(self, 'potential_rise_events') or not self.potential_rise_events:
            QMessageBox.warning(
                self, "No Events", 
                "No rise events available. Please identify events first using the 'Identify Events' button."
            )
            return
        
        # Get selected events from the table
        selected_events = self.get_selected_events_from_table()
        
        if not selected_events:
            QMessageBox.warning(
                self, "No Selection", 
                "No events selected. Please select at least one event to calculate recharge."
            )
            return
        
        try:
            # Calculate recharge for selected events
            self.calculate_recharge_for_events(selected_events)
            
            # Update results and switch to Results tab
            if hasattr(self, 'rise_events') and self.rise_events:
                # Update the plot
                self.update_plot()
                
                # Switch to Results tab
                self.left_tabs.setCurrentIndex(2)  # Results tab is index 2
                
                # Show a success message
                QMessageBox.information(
                    self, 
                    "Recharge Calculation Complete", 
                    f"Recharge calculation completed successfully.\n"
                    f"Calculated recharge for {len(selected_events)} selected events.\n"
                    f"Total recharge: {self.total_recharge_label.text()}"
                )
        
        except Exception as e:
            logger.error(f"Error in calculate_recharge_for_selected: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Calculation Error", 
                f"Failed to calculate recharge for selected events: {str(e)}"
            )
    
    def identify_rise_events(self, data, rise_threshold, time_window, specific_yield):
        """
        Identify recharge using the RISE method based on daily rises.
        
        Args:
            data: Pandas DataFrame with timestamp and level columns
            rise_threshold: Minimum rise to be considered significant (ft)
            time_window: DEPRECATED - Not used in revised method
            specific_yield: Specific yield for recharge calculation
        """
        try:
            if data is None or len(data) < 2:
                logger.error("Not enough data to identify rises")
                QMessageBox.warning(
                    self, "Calculation Error", 
                    "Not enough data to identify rises. Need at least 2 data points."
                )
                return
            
            # DEBUG: Log the input parameters and data shape
            logger.info(f"DEBUG: Starting RISE method with:")
            logger.info(f"DEBUG: - rise_threshold: {rise_threshold} ft (minimum significant rise)")
            logger.info(f"DEBUG: - specific_yield: {specific_yield}")
            logger.info(f"DEBUG: - data shape: {data.shape}")
            
            # DEBUG: Check and log the first few rows to verify data structure
            logger.info(f"DEBUG: First few rows of data:\n{data.head().to_string()}")
            
            # Ensure data is sorted by timestamp
            if 'timestamp' in data.columns:
                data = data.sort_values('timestamp')
                level_col = 'level'
                timestamp_col = 'timestamp'
                logger.info(f"DEBUG: Using 'timestamp' column and 'level' column from DataFrame")
            else:
                # Data is likely a Series with DatetimeIndex
                data = data.sort_index()
                level_col = data.columns[0] if isinstance(data, pd.DataFrame) else data.name
                timestamp_col = data.index
                logger.info(f"DEBUG: Using DatetimeIndex and column '{level_col}'")
            
            # DEBUG: Check for NaN values in the level column
            nan_count = data[level_col].isna().sum()
            logger.info(f"DEBUG: NaN values in level column: {nan_count} ({nan_count/len(data)*100:.2f}%)")
            
            # Set up water year parameters - use temporary values if set by identify_rise_events_only
            if hasattr(self, '_temp_water_year_month') and hasattr(self, '_temp_water_year_day'):
                water_year_month = self._temp_water_year_month
                water_year_day = self._temp_water_year_day
                # Clean up temporary values
                delattr(self, '_temp_water_year_month')
                delattr(self, '_temp_water_year_day')
            elif hasattr(self, 'water_year_month') and hasattr(self, 'water_year_day'):
                # Use UI controls if available (for backward compatibility)
                water_year_month = self.water_year_month.value()
                water_year_day = self.water_year_day.value()
            else:
                # Fallback to defaults
                water_year_month = 10
                water_year_day = 1
            
            logger.info(f"Starting RISE method calculations with threshold={rise_threshold}ft, Sy={specific_yield}")
            
            # Step 1: Calculate daily rises from the processed data
            if 'timestamp' in data.columns:
                data['rise'] = data[level_col].diff()
            else:
                # If data is a Series or DataFrame with DatetimeIndex
                data = data.copy()  # Avoid SettingWithCopyWarning
                if isinstance(data, pd.DataFrame):
                    data['rise'] = data[level_col].diff()
                else:
                    # Convert Series to DataFrame for consistent handling
                    data = pd.DataFrame({level_col: data})
                    data['rise'] = data[level_col].diff()
                    data.index.name = 'timestamp'
                    data = data.reset_index()
                    timestamp_col = 'timestamp'
            
            # Step 2: Keep only positive rises (RISE method)
            data['rise_original'] = data['rise']  # Save original rise for reference
            data['rise'] = data['rise'].clip(lower=0)  # Set negative rises to zero
            
            # Calculate recharge for each rise (rise * specific yield, converted to inches)
            data['recharge'] = data['rise'] * specific_yield * 12  # Convert ft to inches
            
            # Calculate cumulative recharge
            data['cumulative_recharge'] = data['recharge'].cumsum()
            
            # Identify water years
            if isinstance(timestamp_col, str):
                data['water_year'] = data.apply(
                    lambda row: self.get_water_year(row[timestamp_col]), axis=1
                )
            else:
                # When timestamp is the index
                data['water_year'] = [self.get_water_year(ts) for ts in data.index]
            
            # Create daily rise records, which serve as individual "events"
            daily_rises = []
            
            # Only include days with positive rises
            positive_rises = data[data['rise'] > 0].copy()
            
            # Apply threshold filter if specified
            if rise_threshold > 0:
                significant_rises = positive_rises[positive_rises['rise'] >= rise_threshold].copy()
                logger.info(f"Found {len(significant_rises)} significant rises >= {rise_threshold} ft")
            else:
                significant_rises = positive_rises.copy()
                logger.info(f"Using all {len(significant_rises)} positive rises (no threshold)")
            
            # Create individual rise records for each day with a rise
            for i, row in significant_rises.iterrows():
                date = row[timestamp_col] if isinstance(timestamp_col, str) else row.name
                
                # Create a rise record
                rise_record = {
                    'event_num': i + 1,  # Simple sequential numbering
                    'water_year': row['water_year'],
                    'date': date,
                    'level': row[level_col],
                    'rise': row['rise'],
                    'recharge': row['recharge'],
                    'annual_rate': row['recharge'] * 365,  # Simple annualization for single-day rise
                }
                
                logger.debug(f"Added rise record for {date}: {row['rise']:.4f} ft, {row['recharge']:.2f} inches")
                daily_rises.append(rise_record)
            
            # Sort rises by date
            daily_rises.sort(key=lambda x: x['date'])
            
            # Calculate some overall statistics
            if daily_rises:
                total_recharge = sum(r['recharge'] for r in daily_rises)
                total_rise = sum(r['rise'] for r in daily_rises)
                logger.info(f"Total recharge: {total_recharge:.2f} inches from {len(daily_rises)} daily rises")
                logger.info(f"Total water level rise: {total_rise:.2f} ft")
                
                # Calculate overall annual rate
                if len(daily_rises) > 1:
                    first_date = daily_rises[0]['date']
                    last_date = daily_rises[-1]['date']
                    days_span = (last_date - first_date).total_seconds() / (24 * 3600)
                    if days_span > 0:
                        annual_rate = total_recharge * 365 / days_span
                        logger.info(f"Overall annual recharge rate: {annual_rate:.2f} inches/year over {days_span:.1f} days")
            else:
                logger.warning("No significant rises found that meet the threshold criteria.")
                QMessageBox.warning(
                    self, "No Rises Found", 
                    f"No rises were found that exceed the threshold of {rise_threshold} ft.\n\n"
                    f"Suggestions:\n"
                    f"1. Try lowering the rise threshold\n"
                    f"2. Check data preprocessing settings\n"
                    f"3. Verify the water level data shows actual rises"
                )
            
            # Store the daily rises as our "events"
            self.rise_events = daily_rises
            
            # Store the processed data for reference
            self.processed_rise_data = data
            
            # Update the results display
            self.update_results_with_events(daily_rises)
            
        except Exception as e:
            logger.error(f"Error in identify_rise_events: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Error", 
                f"An error occurred while processing rise events:\n{str(e)}"
            )
    
    def populate_event_selection_table(self, rises):
        """Populate the event selection table with the provided rises."""
        if not rises:
            return
            
        self.event_selection_table.setRowCount(len(rises))
        
        for row, rise in enumerate(rises):
            # Create checkbox for selection
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # All events selected by default
            checkbox_cell = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_cell)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.event_selection_table.setCellWidget(row, 0, checkbox_cell)
            
            # Event number
            self.event_selection_table.setItem(row, 1, QTableWidgetItem(str(rise['event_num'])))
            
            # Water year
            self.event_selection_table.setItem(row, 2, QTableWidgetItem(rise['water_year']))
            
            # Date
            date_str = rise['date'].strftime('%Y-%m-%d') if isinstance(rise['date'], datetime) else str(rise['date'])
            self.event_selection_table.setItem(row, 3, QTableWidgetItem(date_str))
            
            # Rise amount (ft)
            rise_item = QTableWidgetItem(f"{rise['rise']:.4f}")
            self.event_selection_table.setItem(row, 4, rise_item)
            
            # Recharge amount (inches)
            recharge_item = QTableWidgetItem(f"{rise['recharge']:.2f}")
            self.event_selection_table.setItem(row, 5, recharge_item)
        
        # Resize columns to fit content
        self.event_selection_table.resizeColumnsToContents()
    
    def on_event_selected(self):
        """Handle selection of an event in the event selection table."""
        selected_rows = self.event_selection_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_event = None
            return
        
        # Get the index of the selected row (use the first one if multiple are selected)
        row_index = selected_rows[0].row()
        
        # Find the corresponding event in our rise_events list
        event_num = int(self.event_selection_table.item(row_index, 1).text())
        
        # Find the index of this event in the rise_events list
        events_to_use = self.rise_events_filtered if hasattr(self, 'rise_events_filtered') else self.rise_events
        for i, event in enumerate(events_to_use):
            if event['event_num'] == event_num:
                self.selected_event = i
                break
        
        # Update the plot to highlight the selected event
        self.update_plot(use_filtered=hasattr(self, 'rise_events_filtered'))
    
    def update_plot(self, use_filtered=False, preview_mode=False):
        """Update the plot with water level data and rise events.
        
        Uses the standardized base plotting with RISE-specific additions.
        
        Args:
            use_filtered: Whether to use filtered events
            preview_mode: Whether to show raw and processed data for preview
        """
        logger.info(f"[PLOT_DEBUG] RISE update_plot called - use_filtered: {use_filtered}, preview_mode: {preview_mode}")
        
        try:
            # Check if we have any data to plot - if not, show completely empty plot
            has_data = (
                (hasattr(self, 'raw_data') and self.raw_data is not None and not self.raw_data.empty) or
                (hasattr(self, 'processed_data') and self.processed_data is not None and not self.processed_data.empty)
            )
            
            if not has_data:
                # Show completely empty plot (like ERC tab)
                self.figure.clear()
                self.canvas.draw()
                return
            
            # Use base class plotting for consistent appearance
            ax = self.update_plot_base()
            if ax is None:
                logger.warning("[PLOT_DEBUG] Base plot update returned None")
                return
                
            # Add RISE-specific elements
            self.add_method_specific_plots(ax)
            
            logger.info(f"[PLOT_DEBUG] RISE plot update completed successfully")
            
        except Exception as e:
            logger.error(f"[PLOT_DEBUG] Error updating plot: {e}", exc_info=True)
            # Don't show message box for plot errors to avoid excessive dialogs
            # Just clear the figure to prevent display issues
            try:
                if hasattr(self, 'figure') and self.figure is not None:
                    self.figure.clear()
                    ax = self.figure.add_subplot(111)
                    ax.set_title("Error plotting data")
                    if hasattr(self, 'canvas') and self.canvas is not None:
                        self.canvas.draw()
                logger.error(f"[PLOT_DEBUG] Showed error plot due to exception")
            except Exception as inner_e:
                logger.error(f"[PLOT_DEBUG] Failed to show error plot: {inner_e}")
    
    def add_method_specific_plots(self, ax):
        """Add RISE-specific plot elements to the base plot."""
        try:
            # Debug logging
            has_events = hasattr(self, 'rise_events') and self.rise_events
            has_checkbox = hasattr(self, 'show_rise_events')
            is_checked = has_checkbox and self.show_rise_events.isChecked()
            logger.info(f"[PLOT_DEBUG] Events plotting: has_events={has_events}, has_checkbox={has_checkbox}, is_checked={is_checked}")
            if has_events:
                logger.info(f"[PLOT_DEBUG] Number of rise events: {len(self.rise_events)}")
            
            # If we have rise events and the option is checked
            if has_events and has_checkbox and is_checked:
                events_to_plot = self.rise_events
                
                # Filter by selected water year if needed
                if hasattr(self, 'selected_water_year') and self.selected_water_year and self.selected_water_year != "all":
                    events_to_plot = [e for e in events_to_plot if e['water_year'] == self.selected_water_year]
                
                # Plot all rise points with markers
                for event in events_to_plot:
                    date = event['date']
                    rise = event['rise']
                    
                    if 'level' in event and event['level'] is not None:
                        level = event['level']
                        
                        # Mark the rise point with a red dot (made larger and more visible)
                        existing_labels = ax.get_legend_handles_labels()[1]
                        ax.plot(date, level, 'ro', markersize=6, zorder=10, alpha=0.8, 
                               markeredgewidth=1, markeredgecolor='darkred',
                               label='Rise Points' if 'Rise Points' not in existing_labels else "")
                        
                        # Draw a vertical line to show the magnitude of the rise
                        if rise > 0:
                            ax.plot([date, date], [level - rise, level], 'r-', linewidth=1.0, zorder=5)
                
                # Highlight selected event if option is checked
                if hasattr(self, 'selected_event') and self.selected_event is not None and hasattr(self, 'show_selected_event') and self.show_selected_event.isChecked():
                    if self.selected_event < len(events_to_plot):
                        event = events_to_plot[self.selected_event]
                        date = event['date']
                        
                        if 'level' in event and event['level'] is not None:
                            level = event['level']
                            rise = event['rise']
                            
                            # Highlight the point with a green marker
                            existing_labels = ax.get_legend_handles_labels()[1]
                            ax.plot(date, level, 'go', markersize=6, zorder=15, label='Selected Event' if 'Selected Event' not in existing_labels else "")
                            
                            # Draw a green vertical line for the rise
                            if rise > 0:
                                ax.plot([date, date], [level - rise, level], 'g-', linewidth=2, zorder=14)
                                
                                # Shade the area of the rise
                                ax.fill_between([date - pd.Timedelta(hours=6), date + pd.Timedelta(hours=6)],
                                                [level - rise, level - rise], 
                                                [level, level], 
                                                color='g', alpha=0.3, zorder=13)
            
            # Update title with RISE-specific information
            current_title = ax.get_title()
            if hasattr(self, 'rise_events') and self.rise_events:
                events_count = len(self.rise_events)
                if hasattr(self, 'selected_water_year') and self.selected_water_year and self.selected_water_year != "all":
                    filtered_events = [e for e in self.rise_events if e['water_year'] == self.selected_water_year]
                    events_count = len(filtered_events)
                current_title += f' ({events_count} rise events)'
                ax.set_title(current_title)
                
        except Exception as e:
            logger.error(f"Error adding RISE-specific plots: {e}", exc_info=True)

    def _highlight_selected_event(self, ax, event_data, timestamp_col, level_col):
        """Helper method to highlight a selected event on the plot.
        
        Args:
            ax: Matplotlib axis to plot on
            event_data: DataFrame containing event data
            timestamp_col: Column name for timestamps (or None if index)
            level_col: Column name for water levels
        """
        if event_data.empty:
            return
            
        # Get timestamps
        if timestamp_col is None:
            timestamps = event_data.index
        else:
            timestamps = event_data[timestamp_col]
        
        # Get levels
        levels = event_data[level_col]
        
        # Plot event with thicker line
        ax.plot(
            timestamps, 
            levels, 
            'g-', 
            linewidth=3.0,
            zorder=10
        )
        
        # Fill area below the event (recharge)
        min_level = levels.min()
        ax.fill_between(
            timestamps, 
            levels, 
            min_level, 
            alpha=0.3, 
            color='g',
            zorder=9
        )
    
    def clear_results(self):
        """Clear all results and plots."""
        self.results_table.setRowCount(0)
        self.yearly_stats_table.setRowCount(0)
        self.total_recharge_label.setText("0.0 inches")
        self.annual_rate_label.setText("0.0 inches/year")
        self.events_count_label.setText("0")
        self.avg_annual_label.setText("0.0 inches/year")
        
        # Clear event selection table too
        self.event_selection_table.setRowCount(0)
        
        # Reset water year selection
        self.selected_water_year = "all"
        
        # Clear water year dropdown for Event Selection tab
        while self.water_year_combo.count() > 1:
            self.water_year_combo.removeItem(1)
        
        if hasattr(self, 'rise_events'):
            del self.rise_events
        
        if hasattr(self, 'rise_events_filtered'):
            del self.rise_events_filtered
        
        self.figure.clear()
        self.canvas.draw()
    
    def export_to_csv(self):
        """Export results to CSV file."""
        if not hasattr(self, 'rise_events') or not self.rise_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export to CSV", 
                f"{self.well_combo.currentText()}_RISE_results.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # Get events to export (filtered or all)
            events_to_export = self.rise_events_filtered if hasattr(self, 'rise_events_filtered') else self.rise_events
            
            # Write CSV file
            with open(file_path, 'w', newline='') as csvfile:
                # Write header information
                csvfile.write(f"# RISE Calculation Results for {self.well_combo.currentText()}\n")
                csvfile.write(f"# Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                csvfile.write(f"# Parameters:\n")
                csvfile.write(f"#   Specific Yield: {self.sy_spinner.value()}\n")
                csvfile.write(f"#   Rise Threshold: {self.threshold_spinner.value()} ft\n")
                csvfile.write(f"#   Water Year Start: Month {self.water_year_month.value()}, Day {self.water_year_day.value()}\n")
                csvfile.write(f"# Total Recharge: {self.total_recharge_label.text()}\n")
                csvfile.write(f"# Annual Rate: {self.annual_rate_label.text()}\n")
                csvfile.write("#\n")
                
                # Write data headers and rows
                fieldnames = ['Event_ID', 'Water_Year', 'Date', 'Water_Level_ft', 'Rise_ft', 'Recharge_in', 'Daily_Rate_in_per_yr']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in events_to_export:
                    writer.writerow({
                        'Event_ID': event['event_num'],
                        'Water_Year': event['water_year'],
                        'Date': event['date'].strftime('%Y-%m-%d'),
                        'Water_Level_ft': f"{event['level']:.2f}",
                        'Rise_ft': f"{event['rise']:.4f}",
                        'Recharge_in': f"{event['recharge']:.3f}",
                        'Daily_Rate_in_per_yr': f"{event['annual_rate']:.2f}"
                    })
                    
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Results exported successfully to:\n{file_path}"
            )
            logger.info(f"Exported RISE results to CSV: {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Export Error", 
                f"Failed to export to CSV:\n{str(e)}"
            )
        
    def export_to_excel(self):
        """Export results to Excel file."""
        if not hasattr(self, 'rise_events') or not self.rise_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export to Excel", 
                f"{self.well_combo.currentText()}_RISE_results.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # Get events to export (filtered or all)
            events_to_export = self.rise_events_filtered if hasattr(self, 'rise_events_filtered') else self.rise_events
            
            # Create DataFrames for export
            # 1. Rise events data
            events_data = []
            for event in events_to_export:
                events_data.append({
                    'Event ID': event['event_num'],
                    'Water Year': event['water_year'],
                    'Date': event['date'],
                    'Water Level (ft)': event['level'],
                    'Rise (ft)': event['rise'],
                    'Recharge (in)': event['recharge'],
                    'Daily Rate (in/yr)': event['annual_rate']
                })
            events_df = pd.DataFrame(events_data)
            
            # 2. Yearly summary data
            water_years = sorted(set(event['water_year'] for event in events_to_export))
            yearly_data = []
            for water_year in water_years:
                year_events = [e for e in events_to_export if e['water_year'] == water_year]
                year_recharge = sum(e['recharge'] for e in year_events)
                
                # Calculate annual rate for this water year
                if len(year_events) > 1:
                    year_dates = [e['date'] for e in year_events]
                    year_first_date = min(year_dates)
                    year_last_date = max(year_dates)
                    year_days = (year_last_date - year_first_date).total_seconds() / (24 * 3600)
                    year_rate = year_recharge * 365 / year_days if year_days > 0 else year_recharge * 365
                else:
                    year_rate = year_recharge * 365
                    
                yearly_data.append({
                    'Water Year': water_year,
                    'Number of Rises': len(year_events),
                    'Total Recharge (in)': year_recharge,
                    'Annual Rate (in/yr)': year_rate
                })
            yearly_df = pd.DataFrame(yearly_data)
            
            # 3. Parameters summary
            params_data = {
                'Parameter': [
                    'Well', 'Specific Yield', 'Rise Threshold (ft)', 
                    'Water Year Start', 'Downsample Method', 'Filter Type',
                    'Total Recharge (in)', 'Annual Rate (in/yr)', 'Total Rises'
                ],
                'Value': [
                    self.well_combo.currentText(),
                    self.sy_spinner.value(),
                    self.threshold_spinner.value(),
                    f"Month {self.water_year_month.value()}, Day {self.water_year_day.value()}",
                    self.downsample_combo.currentText(),
                    'Moving Average' if self.ma_radio.isChecked() else 'None',
                    float(self.total_recharge_label.text().split()[0]),
                    float(self.annual_rate_label.text().split()[0]),
                    len(events_to_export)
                ]
            }
            params_df = pd.DataFrame(params_data)
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Write parameters
                params_df.to_excel(writer, sheet_name='Parameters', index=False)
                
                # Write yearly summary
                yearly_df.to_excel(writer, sheet_name='Yearly Summary', index=False)
                
                # Write individual events
                events_df.to_excel(writer, sheet_name='Rise Events', index=False)
                
                # Auto-adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                        
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Results exported successfully to:\n{file_path}\n\n"
                f"The Excel file contains:\n"
                f"- Parameters sheet\n"
                f"- Yearly Summary sheet\n"
                f"- Rise Events sheet"
            )
            logger.info(f"Exported RISE results to Excel: {file_path}")
            
        except ImportError:
            QMessageBox.warning(
                self, 
                "Missing Dependency", 
                "Excel export requires the 'openpyxl' package.\n"
                "Please install it using: pip install openpyxl"
            )
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Export Error", 
                f"Failed to export to Excel:\n{str(e)}"
            )
    
    def save_to_database(self):
        """Save the current RISE calculation to the database."""
        if not hasattr(self, 'rise_events') or not self.rise_events:
            QMessageBox.warning(self, "No Data", "No results to save. Calculate recharge first.")
            return
            
        if not self.rise_db:
            QMessageBox.warning(self, "Database Error", "Database connection not available.")
            return
            
        if not self.current_well:
            QMessageBox.warning(self, "No Well", "No well selected.")
            return
            
        try:
            # Get calculation parameters from global settings
            well_id = self.current_well
            well_name = self.well_combo.currentText()
            
            # Get global settings from parent's unified settings
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                settings = self.parent.unified_settings.get_method_settings('RISE')
            else:
                # Fallback to current settings if unified settings not available
                settings = getattr(self, 'current_settings', {})
            
            # Extract parameters from settings
            specific_yield = settings.get('specific_yield', 0.2)
            rise_threshold = settings.get('rise_threshold', 0.1)
            
            # Get preprocessing parameters
            downsample_rule = settings.get('downsample_frequency', 'None')
            downsample_method = settings.get('downsample_method', 'Mean')
            
            # Filter settings
            filter_type = "none"
            filter_window = None
            if settings.get('enable_smoothing', False):
                filter_type = "moving_average"
                filter_window = settings.get('smoothing_window', 3)
            
            # Water year settings
            water_year_start_month = settings.get('water_year_month', 10)
            water_year_start_day = settings.get('water_year_day', 1)
            
            # Get events to save (filtered or all)
            events_to_save = self.rise_events_filtered if hasattr(self, 'rise_events_filtered') else self.rise_events
            
            # Calculate total recharge and annual rate
            total_recharge = sum(event['recharge'] for event in events_to_save)
            
            # Calculate date span for annual rate
            if len(events_to_save) > 1:
                first_date = min(event['date'] for event in events_to_save)
                last_date = max(event['date'] for event in events_to_save)
                days_span = (last_date - first_date).total_seconds() / (24 * 3600)
                annual_rate = total_recharge * 365 / days_span if days_span > 0 else 0
            else:
                annual_rate = events_to_save[0]['annual_rate'] if events_to_save else 0
                
            # Convert events to the format expected by the database
            rise_events_data = []
            for event in events_to_save:
                rise_events_data.append({
                    'event_date': event['date'].isoformat() if hasattr(event['date'], 'isoformat') else str(event['date']),
                    'water_year': event['water_year'],
                    'water_level': event['level'],
                    'rise_magnitude': event['rise'],
                    'recharge_value': event['recharge']
                })
                
            # Calculate yearly summaries
            yearly_summaries = []
            water_years = sorted(set(event['water_year'] for event in events_to_save))
            for water_year in water_years:
                year_events = [e for e in events_to_save if e['water_year'] == water_year]
                year_recharge = sum(e['recharge'] for e in year_events)
                
                # Calculate annual rate for this water year
                if len(year_events) > 1:
                    year_dates = [e['date'] for e in year_events]
                    year_first_date = min(year_dates)
                    year_last_date = max(year_dates)
                    year_days = (year_last_date - year_first_date).total_seconds() / (24 * 3600)
                    year_rate = year_recharge * 365 / year_days if year_days > 0 else year_recharge * 365
                else:
                    year_rate = year_recharge * 365
                    
                yearly_summaries.append({
                    'water_year': water_year,
                    'total_recharge': year_recharge,
                    'num_events': len(year_events),
                    'annual_rate': year_rate
                })
            
            # Prepare parameters dictionary for database
            parameters = {
                'well_name': well_name,
                'specific_yield': specific_yield,
                'rise_threshold': rise_threshold,
                'downsample_rule': downsample_rule,
                'downsample_method': downsample_method,
                'filter_type': filter_type,
                'filter_window': filter_window,
                'water_year_start_month': water_year_start_month,
                'water_year_start_day': water_year_start_day
            }
            
            # Save to database
            success = self.rise_db.save_calculation(
                well_number=well_id,
                parameters=parameters,
                events=rise_events_data,
                yearly_summary=yearly_summaries,
                total_recharge=total_recharge,
                annual_rate=annual_rate
            )
            
            if success:
                QMessageBox.information(
                    self, 
                    "Save Successful", 
                    f"RISE calculation saved successfully for {well_name}.\n\n"
                    f"Total recharge: {total_recharge:.2f} inches\n"
                    f"Annual rate: {annual_rate:.2f} inches/year\n"
                    f"Number of rises: {len(events_to_save)}"
                )
                logger.info(f"Saved RISE calculation for well {well_id} to database")
            else:
                QMessageBox.warning(
                    self, 
                    "Save Failed", 
                    "Failed to save the calculation to the database. Check the logs for details."
                )
                
        except Exception as e:
            logger.error(f"Error saving to database: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Save Error", 
                f"An error occurred while saving:\n{str(e)}"
            )
    
    def load_from_database(self):
        """Load a previous RISE calculation from the database."""
        if not self.rise_db:
            QMessageBox.warning(self, "Database Error", "Database connection not available.")
            return
            
        if not self.current_well:
            QMessageBox.warning(self, "No Well", "Please select a well first.")
            return
            
        try:
            # Get previous calculations for this well
            calculations = self.rise_db.get_calculations_for_well(self.current_well)
            
            if not calculations:
                QMessageBox.information(
                    self, 
                    "No Previous Calculations", 
                    f"No saved RISE calculations found for {self.well_combo.currentText()}."
                )
                return
                
            # Create a dialog to select from previous calculations
            dialog = LoadCalculationDialog(calculations, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_calc_id = dialog.selected_calculation_id
                if selected_calc_id:
                    self.load_calculation(selected_calc_id)
                    
        except Exception as e:
            logger.error(f"Error loading from database: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Load Error", 
                f"An error occurred while loading:\n{str(e)}"
            )
    
    def load_calculation(self, calculation_id):
        """Load a specific calculation from the database."""
        try:
            # Get the full calculation data
            calc_data = self.rise_db.get_calculation_details(calculation_id)
            
            if not calc_data:
                QMessageBox.warning(self, "Load Error", "Could not load calculation details.")
                return
                
            # Load parameters into global settings
            # Note: Since we're using global settings now, we should update them
            # and inform the user that settings have been updated
            
            loaded_settings = {
                'specific_yield': calc_data.get('specific_yield', 0.2),
                'rise_threshold': calc_data.get('rise_threshold', 0.1),
                'water_year_month': calc_data.get('water_year_start_month', 10),
                'water_year_day': calc_data.get('water_year_start_day', 1),
                'downsample_frequency': calc_data.get('downsample_rule', 'None'),
                'downsample_method': calc_data.get('downsample_method', 'Mean'),
                'enable_smoothing': calc_data.get('filter_type') == 'moving_average',
                'smoothing_window': calc_data.get('filter_window', 3) if calc_data.get('filter_type') == 'moving_average' else 3
            }
            
            # Update current settings with loaded values
            if hasattr(self, 'current_settings'):
                self.current_settings.update(loaded_settings)
            else:
                self.current_settings = loaded_settings
            
            logger.info(f"Loaded calculation parameters: {loaded_settings}")
            
            # Convert rise events from database format back to internal format
            self.rise_events = []
            for idx, event in enumerate(calc_data['rise_events']):
                self.rise_events.append({
                    'event_num': idx + 1,
                    'water_year': event['water_year'],
                    'date': pd.to_datetime(event['event_date']),
                    'level': event['water_level'],
                    'rise': event['rise_magnitude'],
                    'recharge': event['recharge_value'],
                    'annual_rate': event['recharge_value'] * 365
                })
            
            # Update the results display
            self.update_results_with_events(self.rise_events)
            
            # Update the plot
            self.update_plot()
            
            # Switch to Results tab
            self.left_tabs.setCurrentIndex(3)  # Results tab
            
            QMessageBox.information(
                self, 
                "Load Successful", 
                f"Loaded RISE calculation from {calc_data['calculation_date']}\n\n"
                f"Total recharge: {calc_data['total_recharge']:.2f} inches\n"
                f"Annual rate: {calc_data['annual_rate']:.2f} inches/year\n"
                f"Number of rises: {len(self.rise_events)}"
            )
            
            logger.info(f"Loaded RISE calculation {calculation_id} for well {self.current_well}")
            
        except Exception as e:
            logger.error(f"Error loading calculation: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Load Error", 
                f"Failed to load calculation:\n{str(e)}"
            )
    
    def compare_calculations(self):
        """Open dialog to compare multiple RISE calculations."""
        if not self.rise_db:
            QMessageBox.warning(self, "Database Error", "Database connection not available.")
            return
            
        if not self.current_well:
            QMessageBox.warning(self, "No Well", "Please select a well first.")
            return
            
        try:
            # Get all calculations for this well
            calculations = self.rise_db.get_calculations_for_well(self.current_well)
            
            if not calculations or len(calculations) < 2:
                QMessageBox.information(
                    self, 
                    "Insufficient Data", 
                    f"Need at least 2 saved calculations to compare.\n"
                    f"Found {len(calculations) if calculations else 0} calculation(s) for {self.well_combo.currentText()}."
                )
                return
                
            # Create comparison dialog
            dialog = CompareCalculationsDialog(calculations, self.rise_db, self)
            dialog.exec_()
                    
        except Exception as e:
            logger.error(f"Error in compare_calculations: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Comparison Error", 
                f"An error occurred while comparing:\n{str(e)}"
            )
    
    def select_all_events(self):
        """Select all events in the table."""
        if not self.event_selection_table.rowCount():
            return
            
        for row in range(self.event_selection_table.rowCount()):
            if not self.event_selection_table.isRowHidden(row):
                checkbox = self.event_selection_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def deselect_all_events(self):
        """Deselect all events in the table."""
        if not self.event_selection_table.rowCount():
            return
            
        for row in range(self.event_selection_table.rowCount()):
            if not self.event_selection_table.isRowHidden(row):
                checkbox = self.event_selection_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)
    
    def recalculate_with_selected(self):
        """Recalculate recharge using only the selected rises."""
        if not hasattr(self, 'rise_events') or not self.rise_events:
            QMessageBox.warning(
                self, "No Data", 
                "No rise events available. Run the calculation first from the Parameters tab."
            )
            return
        
        logger.info("=" * 50)    
        logger.info("RECALCULATING WITH SELECTED RISES")
            
        # Get selected rises
        selected_rises = []
        
        logger.info(f"Original rises count: {len(self.rise_events)}")
        logger.info(f"Event selection table rows: {self.event_selection_table.rowCount()}")
        
        for row in range(self.event_selection_table.rowCount()):
            if not self.event_selection_table.isRowHidden(row):
                checkbox = self.event_selection_table.cellWidget(row, 0).findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    event_num = int(self.event_selection_table.item(row, 1).text())
                    logger.info(f"Including rise #{event_num}")
                    
                    # Find the rise with this number
                    matching_rises = [rise for rise in self.rise_events if rise['event_num'] == event_num]
                    if matching_rises:
                        selected_rises.append(matching_rises[0])
                        logger.info(f"  Rise #{event_num}: {matching_rises[0]['date']}, Rise={matching_rises[0]['rise']:.2f}ft, Recharge={matching_rises[0]['recharge']:.2f} in")
                    else:
                        logger.warning(f"  Could not find rise #{event_num} in rise_events!")
        
        if not selected_rises:
            logger.warning("NO RISES SELECTED!")
            QMessageBox.warning(
                self, "No Selection", 
                "No rises selected. Please select at least one rise to include in the calculation."
            )
            return
        
        # Save water year filter state
        self.selected_water_year = self.water_year_combo.currentData()
        logger.info(f"Selected water year filter: {self.selected_water_year}")
        
        # Update results with filtered rises
        logger.info(f"Updating results with {len(selected_rises)} selected rises")
        self.rise_events_filtered = selected_rises
        self.update_results_with_events(selected_rises)
        
        # Switch to Results tab
        self.left_tabs.setCurrentIndex(2)  # Results tab is index 2
        
        # Log total recharge from selected rises
        if selected_rises:
            total_recharge = sum(rise['recharge'] for rise in selected_rises)
            logger.info(f"Total recharge from selected rises: {total_recharge:.2f} inches")
            
            # Calculate annual rate if we have date information
            if len(selected_rises) > 1:
                first_date = min(rise['date'] for rise in selected_rises)
                last_date = max(rise['date'] for rise in selected_rises)
                days = (last_date - first_date).total_seconds() / (24 * 3600)
                if days > 0:
                    annual_rate = total_recharge * 365 / days
                    logger.info(f"Annual recharge rate: {annual_rate:.2f} inches/year over {days} days")
        
        logger.info("RECALCULATION COMPLETE")
        logger.info("=" * 50)
        
        # Show a success message
        QMessageBox.information(
            self, 
            "Recalculation Complete", 
            f"Recharge recalculated using {len(selected_rises)} selected rises.\n"
            f"Total estimated recharge: {self.total_recharge_label.text()}"
        )
    
    def update_results_with_events(self, rises):
        """Update the results using the provided rises list."""
        if not rises:
            logger.warning("update_results_with_events called with empty rises list")
            return
            
        logger.info(f"Updating results with {len(rises)} rises")
        
        # Update the results table
        self.results_table.setRowCount(len(rises))
        
        # Calculate totals
        total_recharge = sum(rise['recharge'] for rise in rises)
        total_rise_ft = sum(rise['rise'] for rise in rises)
        
        # Calculate annual rate based on the entire data period
        if len(rises) > 1:
            first_date = min(rise['date'] for rise in rises)
            last_date = max(rise['date'] for rise in rises)
            days_span = (last_date - first_date).total_seconds() / (24 * 3600)
            if days_span > 0:
                annual_rate = total_recharge * 365 / days_span
            else:
                annual_rate = 0
        else:
            annual_rate = rises[0]['annual_rate'] if rises else 0
        
        # Update the summary labels
        self.total_recharge_label.setText(f"{total_recharge:.2f} inches")
        self.annual_rate_label.setText(f"{annual_rate:.2f} inches/year")
        self.events_count_label.setText(str(len(rises)))
        
        # Calculate water year statistics
        water_years = sorted(set(rise['water_year'] for rise in rises))
        yearly_stats = []
        
        for water_year in water_years:
            year_rises = [rise for rise in rises if rise['water_year'] == water_year]
            year_recharge = sum(rise['recharge'] for rise in year_rises)
            
            # Calculate annual rate for this water year
            if len(year_rises) > 1:
                year_dates = [rise['date'] for rise in year_rises]
                year_first_date = min(year_dates)
                year_last_date = max(year_dates)
                year_days = (year_last_date - year_first_date).total_seconds() / (24 * 3600)
                if year_days > 0:
                    year_rate = year_recharge * 365 / year_days
                else:
                    year_rate = year_recharge * 365  # Single day rate
            else:
                year_rate = year_recharge * 365  # Single day rate
                
            yearly_stats.append({
                'water_year': water_year,
                'recharge': year_recharge,
                'rate': year_rate,
                'rises': len(year_rises)
            })
            
            logger.info(f"Water Year {water_year}: {year_recharge:.2f} inches from {len(year_rises)} rises, rate: {year_rate:.2f} in/yr")
        
        # Calculate multi-year average
        total_years = len(water_years)
        if total_years > 0:
            avg_yearly_recharge = total_recharge / total_years
            logger.info(f"Average yearly recharge: {avg_yearly_recharge:.2f} inches/year over {total_years} years")
            self.avg_annual_label.setText(f"{avg_yearly_recharge:.2f} inches/year")
        else:
            self.avg_annual_label.setText("0.0 inches/year")
            
        # Update the yearly statistics table
        self.yearly_stats_table.setRowCount(len(yearly_stats))
        
        for row, stats in enumerate(yearly_stats):
            # Water Year
            self.yearly_stats_table.setItem(row, 0, QTableWidgetItem(stats['water_year']))
            
            # Rises Count
            count_item = QTableWidgetItem(str(stats['rises']))
            count_item.setData(Qt.DisplayRole, stats['rises'])  # For sorting
            self.yearly_stats_table.setItem(row, 1, count_item)
            
            # Recharge amount
            recharge_item = QTableWidgetItem(f"{stats['recharge']:.2f}")
            recharge_item.setData(Qt.DisplayRole, stats['recharge'])  # For sorting
            self.yearly_stats_table.setItem(row, 2, recharge_item)
            
            # Annual Rate
            rate_item = QTableWidgetItem(f"{stats['rate']:.2f}")
            rate_item.setData(Qt.DisplayRole, stats['rate'])  # For sorting
            self.yearly_stats_table.setItem(row, 3, rate_item)
            
        # Resize columns to fit content
        self.yearly_stats_table.resizeColumnsToContents()
        
        # Check if we need to update column headers
        if self.results_table.columnCount() >= 6:
            self.results_table.setHorizontalHeaderItem(2, QTableWidgetItem("Date"))
            self.results_table.setHorizontalHeaderItem(3, QTableWidgetItem("Rise (ft)"))
            self.results_table.setHorizontalHeaderItem(4, QTableWidgetItem("Recharge (in)"))
            self.results_table.setHorizontalHeaderItem(5, QTableWidgetItem("Daily Rate (in/yr)"))
        
        # Update the table with rises data
        for row, rise in enumerate(rises):
            # Basic info (ID and water year)
            self.results_table.setItem(row, 0, QTableWidgetItem(str(rise['event_num'])))
            self.results_table.setItem(row, 1, QTableWidgetItem(rise['water_year']))
            
            # Date
            date_str = rise['date'].strftime('%Y-%m-%d')
            self.results_table.setItem(row, 2, QTableWidgetItem(date_str))
            
            # Rise amount (ft)
            rise_item = QTableWidgetItem(f"{rise['rise']:.4f}")
            rise_item.setData(Qt.DisplayRole, rise['rise'])  # For sorting
            self.results_table.setItem(row, 3, rise_item)
            
            # Recharge amount (inches)
            recharge_item = QTableWidgetItem(f"{rise['recharge']:.2f}")
            recharge_item.setData(Qt.DisplayRole, rise['recharge'])  # For sorting
            self.results_table.setItem(row, 4, recharge_item)
            
            # Annual rate based on this daily rise (inches/year)
            daily_rate = rise['recharge'] * 365  # Convert daily recharge to annual rate
            rate_item = QTableWidgetItem(f"{daily_rate:.2f}")
            rate_item.setData(Qt.DisplayRole, daily_rate)  # For sorting
            self.results_table.setItem(row, 5, rate_item)
        
        # Update water year list
        self.update_water_year_list(rises)
        
        # Populate the event selection table
        self.populate_event_selection_table(rises)
        
        logger.info(f"Total recharge: {total_recharge:.2f} inches")
        logger.info(f"Annual rate: {annual_rate:.2f} inches/year")
        logger.info(f"Total rises: {len(rises)}")
        
        # Sort results by date (column 2)
        self.results_table.sortItems(2)
    
    def update_water_year_list(self, rises):
        """Update the water year dropdown list based on the available rises."""
        if not rises:
            return
            
        # Extract all unique water years from the rises
        water_years = sorted(set(rise['water_year'] for rise in rises))
        
        # Store the current selection
        current_data = self.water_year_combo.currentData()
        
        # Clear existing items (except the 'All' option)
        while self.water_year_combo.count() > 1:
            self.water_year_combo.removeItem(1)
        
        # Configure the combo box to adjust its size to the contents
        self.water_year_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            
        # Add the water years from our rises
        for water_year in water_years:
            self.water_year_combo.addItem(f"Water Year {water_year}", water_year)
            
        # Try to restore the previous selection if it still exists
        if current_data != "all":
            for i in range(self.water_year_combo.count()):
                if self.water_year_combo.itemData(i) == current_data:
                    self.water_year_combo.setCurrentIndex(i)
                    break
    
    def get_water_year(self, date):
        """
        Determine the water year for a given date based on the configured water year start.
        
        Args:
            date: A datetime object
        
        Returns:
            A string representing the water year (e.g., "2021-2022")
        """
        # Get water year settings from unified settings
        if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
            settings = self.parent.unified_settings.get_method_settings('RISE')
            month = settings.get('water_year_month', 10)
            day = settings.get('water_year_day', 1)
        else:
            # Fallback to default values
            month = 10  # October
            day = 1     # 1st
        
        # Check if the date is before or after the water year start
        if (date.month > month) or (date.month == month and date.day >= day):
            # After start - use current year as start of water year
            start_year = date.year
        else:
            # Before start - use previous year as start of water year
            start_year = date.year - 1
            
        end_year = start_year + 1
        return f"{start_year}-{end_year}"
    
    def filter_events_by_water_year(self, index):
        """Filter the events table by water year and zoom plot to that water year if selected."""
        selected_water_year = self.water_year_combo.currentData()
        
        # If we don't have any events yet, just return
        if not hasattr(self, 'rise_events') or not self.rise_events:
            return
            
        logger.info(f"Filtering events by water year: {selected_water_year}")
        
        # Store the selected water year for use in other methods
        self.selected_water_year = selected_water_year
        
        # Show all rows if "all" is selected
        if selected_water_year == "all":
            for row in range(self.event_selection_table.rowCount()):
                self.event_selection_table.setRowHidden(row, False)
        else:
            # Otherwise, hide rows that don't match the selected water year
            for row in range(self.event_selection_table.rowCount()):
                water_year = self.event_selection_table.item(row, 2).text()
                self.event_selection_table.setRowHidden(row, water_year != selected_water_year)
        
        # Update the plot to show the selected water year (or all years)
        self.update_plot(use_filtered=True)
    
    def filter_results_by_water_year(self, index):
        """
        Filter the results by water year. 
        
        This method is kept for compatibility but does nothing now since
        the water year filter has been removed from the Results tab.
        """
        # No-op since we removed the filter from the Results tab
        pass
    
    def on_preprocessing_changed(self, *args):
        """Handle changes to preprocessing options."""
        # Only update if we have data
        if hasattr(self, 'raw_data') and self.raw_data is not None:
            self.process_data()
            self.update_plot(preview_mode=True)
            
    def process_data(self):
        """Process the raw data with current preprocessing settings following RISE best practices."""
        if self.raw_data is None:
            return
            
        try:
            # Log the start of data processing
            logger.info("=" * 50)
            logger.info("DATA PROCESSING - STARTING")
            logger.info(f"Processing data with {len(self.raw_data)} points")
            
            # Start with the raw data
            data = self.raw_data.copy()
            
            # Make sure timestamp is a datetime type
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                logger.info(f"Data date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
            
            # Log original data stats
            if 'level' in data.columns:
                logger.info(f"Raw water levels: min={data['level'].min():.2f}ft, max={data['level'].max():.2f}ft, range={data['level'].max()-data['level'].min():.2f}ft")
            
            # Step 1: Flag and handle outliers/pump cycles (simplified - using global settings)
            # Get outlier removal parameters from unified settings
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                outlier_settings = self.parent.unified_settings.get_method_settings('RISE')
                remove_outliers = outlier_settings.get('remove_outliers', False)
                outlier_threshold = outlier_settings.get('outlier_threshold', 3.0)
            else:
                # Fallback to defaults
                remove_outliers = False
                outlier_threshold = 3.0
            
            if remove_outliers:
                # Simple outlier detection using standard deviation
                logger.info(f"Applying outlier removal with threshold {outlier_threshold} standard deviations")
                
                # Calculate z-scores for water levels
                mean_level = data['level'].mean()
                std_level = data['level'].std()
                z_scores = abs((data['level'] - mean_level) / std_level)
                
                # Mark outliers
                outliers = z_scores > outlier_threshold
                outlier_count = outliers.sum()
                logger.info(f"Flagged {outlier_count} points ({outlier_count/len(data)*100:.1f}%) as outliers")
                
                # Remove outliers by setting to NaN
                data.loc[outliers, 'level'] = np.nan
                
                # Optional: interpolate small gaps
                data['level'] = data['level'].interpolate(method='linear', limit=12)  # Limit to 3 hours at 15-min intervals
                
                logger.info("Outlier removal and interpolation complete")
            else:
                logger.info("Outlier removal disabled")
            
            # Step 2: Apply downsampling (get settings from global settings)
            # Get preprocessing parameters from unified settings
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                preprocessing_settings = self.parent.unified_settings.get_method_settings('RISE')
                raw_resample_rule = preprocessing_settings.get('downsample_frequency', 'D')
                raw_downsample_method = preprocessing_settings.get('downsample_method', 'median')
                
                # Map descriptive strings to pandas frequency codes
                frequency_mapping = {
                    'Daily (1D) - Recommended': 'D',
                    'Hourly (1H)': 'H', 
                    'Weekly (1W)': 'W',
                    'Monthly (1M)': 'M',
                    'No Downsampling': 'none',
                    'none': 'none',
                    'D': 'D',  # Already correct
                    'H': 'H',  # Already correct
                    'W': 'W',  # Already correct
                    'M': 'M'   # Already correct
                }
                
                method_mapping = {
                    'Median (for pumped wells) - Recommended': 'median',
                    'Mean (for natural wells)': 'mean', 
                    'Last Value': 'last',
                    'median': 'median',  # Already correct
                    'mean': 'mean',      # Already correct
                    'last': 'last'       # Already correct
                }
                
                resample_rule = frequency_mapping.get(raw_resample_rule, 'D')  # Default to daily
                downsample_method = method_mapping.get(raw_downsample_method, 'median')  # Default to median
            else:
                # Fallback to defaults
                resample_rule = 'D'  # Daily downsampling
                downsample_method = 'median'
            
            if resample_rule != "none":
                # Set timestamp as index for resampling
                if 'timestamp' in data.columns:
                    logger.info(f"Downsampling to {resample_rule} intervals using {downsample_method}")
                    
                    data = data.set_index('timestamp')
                else:
                    logger.error("Cannot resample: no timestamp column found")
                    logger.error("ERROR: Cannot resample - no timestamp column found")
                    QMessageBox.warning(
                        self, "Preprocessing Error", 
                        "Cannot perform downsampling: no timestamp column found in data."
                    )
                    return
                    
                # Make sure index is datetime
                if not isinstance(data.index, pd.DatetimeIndex):
                    logger.error(f"Cannot resample: index is not DatetimeIndex but {type(data.index)}")
                    logger.error(f"ERROR: Cannot resample - index is not DatetimeIndex but {type(data.index)}")
                    QMessageBox.warning(
                        self, "Preprocessing Error", 
                        "Cannot perform downsampling: timestamps are not in correct format."
                    )
                    return
                
                try:
                    method = downsample_method
                    # Group by the resampling period and aggregate
                    original_length = len(data)
                    if method == "mean":
                        data = data.resample(resample_rule).mean()
                    elif method == "median":
                        data = data.resample(resample_rule).median()
                    elif method == "last":
                        data = data.resample(resample_rule).last()
                    else:
                        # Default to median if method not found
                        data = data.resample(resample_rule).median()
                        
                    logger.info(f"Downsampled from {original_length} to {len(data)} points ({len(data)/original_length*100:.1f}%)")
                    logger.debug(f"Downsampled data using {method} to {resample_rule} intervals, resulting in {len(data)} points")
                except Exception as e:
                    logger.error(f"Error during resampling: {e}")
                    logger.error(f"ERROR during resampling: {e}")
                    QMessageBox.warning(
                        self, "Resampling Error", 
                        f"Failed to downsample data: {str(e)}"
                    )
                    return
            
            # Step 3: Apply smoothing if selected (get settings from global settings)
            # Get smoothing parameters from unified settings
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                smoothing_settings = self.parent.unified_settings.get_method_settings('RISE')
                apply_smoothing = smoothing_settings.get('enable_smoothing', True)
                smoothing_window = smoothing_settings.get('smoothing_window', 3)
                smoothing_type = smoothing_settings.get('smoothing_type', 'Moving Average')
            else:
                # Fallback to defaults
                apply_smoothing = True
                smoothing_window = 3
                smoothing_type = 'Moving Average'
            
            if apply_smoothing and smoothing_type == 'Moving Average':
                # Moving average filter
                window = smoothing_window
                center = True  # Use centered moving average
                min_periods = 1  # At least 1 value for centered MA
                
                logger.info(f"Applying {window}-point moving average filter (centered={center})")
                
                # Apply smoothing
                if 'level' in data.columns:  # If using timestamp column
                    data['level'] = data['level'].rolling(window=window, center=center, min_periods=min_periods).mean()
                else:  # If data is a Series or has index as timestamp
                    data = data.rolling(window=window, center=center, min_periods=min_periods).mean()
                
                logger.debug(f"Applied {window}-point moving average filter (centered={center})")
            else:
                if not apply_smoothing:
                    logger.info("No smoothing filter applied")
                else:
                    logger.info(f"Smoothing type '{smoothing_type}' not supported, skipping smoothing")
            
            # Step 4: Reset index if we resampled
            if resample_rule != "none":
                data = data.reset_index()
                logger.info("Reset index after resampling")
            
            # Calculate rises to check if we have anything to work with
            if 'level' in data.columns:
                rises = data['level'].diff()
                positive_rises = rises[rises > 0]
                max_rise = positive_rises.max() if len(positive_rises) > 0 else 0
                logger.info(f"After processing: {len(positive_rises)} positive rises, max rise={max_rise:.4f}ft")
            
            # Drop any remaining NaN values
            original_len = len(data)
            data = data.dropna()
            dropped_count = original_len - len(data)
            logger.info(f"Dropped {dropped_count} NaN values ({dropped_count/original_len*100:.1f}% of data)")
            logger.debug(f"Final processed data has {len(data)} points")
            
            # Check if we have enough data left
            if len(data) < 2:
                error_msg = f"Too few data points after processing: {len(data)} points"
                logger.error(error_msg)
                logger.error(error_msg)
                QMessageBox.warning(
                    self, "Processing Error", 
                    f"{error_msg}\nTry different preprocessing settings."
                )
                return
            
            # Store the processed data
            self.processed_data = data
            
            # Log completion
            logger.info("DATA PROCESSING - COMPLETE")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            QMessageBox.warning(
                self, "Processing Error", 
                f"Failed to process data: {str(e)}"
            )
    
    def preview_processed_data(self):
        """Preview the processed data in the plot."""
        if not hasattr(self, 'raw_data') or self.raw_data is None:
            QMessageBox.warning(self, "No Data", "Please select a well first.")
            return
            
        try:
            # Process the data with current settings
            self.process_data()
            
            if self.processed_data is None:
                QMessageBox.warning(self, "Processing Error", "Failed to process data. Check the settings.")
                return
                
            # Update the plot
            self.update_plot(preview_mode=True)
            
            # Show a message about the preprocessing
            downsample_text = self.downsample_combo.currentText()
            
            filter_text = "No Filter"
            if self.ma_radio.isChecked():
                filter_text = f"Moving Average (window={self.ma_window_spinner.value()})"
            elif self.median_radio.isChecked():
                filter_text = f"Median Filter (window={self.median_window_spinner.value()})"
                
            QMessageBox.information(
                self, 
                "Data Preview", 
                f"Showing preview with:\n"
                f"- Downsampling: {downsample_text}\n"
                f"- Filter: {filter_text}\n\n"
                f"Original data points: {len(self.raw_data)}\n"
                f"Processed data points: {len(self.processed_data)}"
            )
            
        except Exception as e:
            logger.error(f"Error in data preview: {e}")
            QMessageBox.warning(
                self, "Preview Error", 
                f"Failed to preview processed data: {str(e)}"
            )
    
    def identify_rise_events_only(self, data, rise_threshold, specific_yield, water_year_month=10, water_year_day=1):
        """Identify rise events without calculating recharge - just for table population."""
        try:
            if data is None or len(data) < 2:
                logger.error("Not enough data to identify rises")
                return
            
            # Store the water year parameters temporarily for use in identify_rise_events
            self._temp_water_year_month = water_year_month
            self._temp_water_year_day = water_year_day
            
            # Use the existing identify_rise_events method but store results separately
            # This will populate self.rise_events with potential events
            self.identify_rise_events(data, rise_threshold, None, specific_yield)
            
            # Store the identified events as potential events for table population
            if hasattr(self, 'rise_events') and self.rise_events:
                self.potential_rise_events = self.rise_events.copy()
                logger.info(f"Identified {len(self.potential_rise_events)} potential rise events")
            else:
                self.potential_rise_events = []
                logger.warning("No rise events identified")
                
        except Exception as e:
            logger.error(f"Error in identify_rise_events_only: {e}", exc_info=True)
            self.potential_rise_events = []

    def populate_events_table(self, events):
        """Populate the events table with identified rise events."""
        try:
            self.event_selection_table.setRowCount(len(events))
            
            for row, event in enumerate(events):
                # Checkbox for inclusion (all selected by default)
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                self.event_selection_table.setCellWidget(row, 0, checkbox)
                
                # Event details
                self.event_selection_table.setItem(row, 1, QTableWidgetItem(str(event['event_num'])))
                self.event_selection_table.setItem(row, 2, QTableWidgetItem(str(event['water_year'])))
                self.event_selection_table.setItem(row, 3, QTableWidgetItem(event['date'].strftime('%Y-%m-%d')))
                self.event_selection_table.setItem(row, 4, QTableWidgetItem(f"{event['rise']:.3f}"))
                self.event_selection_table.setItem(row, 5, QTableWidgetItem(f"{event['recharge']:.2f}"))
            
            # Update water year filter with available years
            self.update_water_year_filter(events)
            
            logger.info(f"Populated events table with {len(events)} events")
            
        except Exception as e:
            logger.error(f"Error populating events table: {e}", exc_info=True)

    def get_selected_events_from_table(self):
        """Get the events that are selected (checked) in the table."""
        selected_events = []
        
        try:
            for row in range(self.event_selection_table.rowCount()):
                if not self.event_selection_table.isRowHidden(row):
                    checkbox = self.event_selection_table.cellWidget(row, 0)
                    if checkbox and checkbox.isChecked():
                        event_num = int(self.event_selection_table.item(row, 1).text())
                        
                        # Find the corresponding event from potential_rise_events
                        matching_events = [e for e in self.potential_rise_events if e['event_num'] == event_num]
                        if matching_events:
                            selected_events.append(matching_events[0])
            
            logger.info(f"Found {len(selected_events)} selected events from table")
            
        except Exception as e:
            logger.error(f"Error getting selected events from table: {e}", exc_info=True)
        
        return selected_events

    def calculate_recharge_for_events(self, selected_events):
        """Calculate recharge values for the provided events."""
        try:
            # Store the selected events as the final rise_events for results
            self.rise_events = selected_events
            self.rise_events_filtered = selected_events
            
            # Update results with the selected events
            self.update_results_with_events(selected_events)
            
            logger.info(f"Calculated recharge for {len(selected_events)} selected events")
            
        except Exception as e:
            logger.error(f"Error calculating recharge for events: {e}", exc_info=True)
            raise

    def update_water_year_filter(self, events):
        """Update the water year filter dropdown with years from the events."""
        try:
            # Clear existing items (except "All Water Years")
            while self.water_year_combo.count() > 1:
                self.water_year_combo.removeItem(1)
            
            # Get unique water years from events
            water_years = sorted(set(event['water_year'] for event in events))
            
            # Add water years to combo box
            for year in water_years:
                self.water_year_combo.addItem(f"Water Year {year}", year)
            
            logger.info(f"Updated water year filter with {len(water_years)} years")
            
        except Exception as e:
            logger.error(f"Error updating water year filter: {e}", exc_info=True)

    def set_shared_data(self, raw_data, processed_data):
        """Set data that has been preprocessed centrally.
        
        Args:
            raw_data: The raw data DataFrame
            processed_data: The preprocessed data DataFrame
        """
        logger.info(f"[PREPROCESS_DEBUG] RISE receiving shared data: {len(raw_data) if raw_data is not None else 0} raw, {len(processed_data) if processed_data is not None else 0} processed")
        
        self.raw_data = raw_data
        self.processed_data = processed_data
        self.display_data = raw_data  # For backward compatibility
        
        # Mark data as loaded
        self.data_loaded = {'display': True, 'full': True}
        
        # Update plot with new data
        self.update_plot()
        
        logger.info("[PREPROCESS_DEBUG] RISE tab updated with shared data")


class LoadCalculationDialog(QDialog):
    """Dialog for selecting a previous RISE calculation to load."""
    
    def __init__(self, calculations, parent=None):
        super().__init__(parent)
        self.calculations = calculations
        self.selected_calculation_id = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Load Previous Calculation")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Select a previous RISE calculation to load:")
        layout.addWidget(instructions)
        
        # Table of calculations
        self.calc_table = QTableWidget()
        self.calc_table.setColumnCount(5)
        self.calc_table.setHorizontalHeaderLabels([
            "Date", "Total Recharge (in)", "Annual Rate (in/yr)", 
            "Rises Count", "Parameters"
        ])
        self.calc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.calc_table.setAlternatingRowColors(True)
        self.calc_table.verticalHeader().setVisible(False)
        
        # Populate table
        self.calc_table.setRowCount(len(self.calculations))
        for row, calc in enumerate(self.calculations):
            # Date
            date_item = QTableWidgetItem(calc['calculation_date'])
            self.calc_table.setItem(row, 0, date_item)
            
            # Total recharge
            recharge_item = QTableWidgetItem(f"{calc['total_recharge']:.2f}")
            self.calc_table.setItem(row, 1, recharge_item)
            
            # Annual rate
            rate_item = QTableWidgetItem(f"{calc['annual_rate']:.2f}")
            self.calc_table.setItem(row, 2, rate_item)
            
            # Rises count from total_events field
            rises_count = calc.get('total_events', 0)
            count_item = QTableWidgetItem(str(rises_count))
            self.calc_table.setItem(row, 3, count_item)
            
            # Parameters summary - extract from parameters dict
            params_dict = calc.get('parameters', {})
            sy = params_dict.get('specific_yield', 0.2)
            threshold = params_dict.get('rise_threshold', 0.1)
            params = f"Sy={sy:.3f}, Threshold={threshold:.2f}ft"
            params_item = QTableWidgetItem(params)
            self.calc_table.setItem(row, 4, params_item)
            
            # Store calculation ID in the first column's data
            date_item.setData(Qt.UserRole, calc['id'])
        
        # Resize columns to fit content
        self.calc_table.resizeColumnsToContents()
        layout.addWidget(self.calc_table)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect double-click to load
        self.calc_table.doubleClicked.connect(self.accept)
        
    def accept(self):
        """Handle OK button click."""
        selected_rows = self.calc_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            # Get calculation ID from the first column's data
            self.selected_calculation_id = self.calc_table.item(row, 0).data(Qt.UserRole)
        super().accept()


class CompareCalculationsDialog(QDialog):
    """Dialog for comparing multiple RISE calculations."""
    
    def __init__(self, calculations, rise_db, parent=None):
        super().__init__(parent)
        self.calculations = calculations
        self.rise_db = rise_db
        self.selected_calculations = []
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Compare RISE Calculations")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Select calculations to compare (check the boxes to include in comparison):"
        )
        layout.addWidget(instructions)
        
        # Table of calculations with checkboxes
        self.calc_table = QTableWidget()
        self.calc_table.setColumnCount(6)
        self.calc_table.setHorizontalHeaderLabels([
            "Include", "Date", "Total Recharge (in)", "Annual Rate (in/yr)", 
            "Rises Count", "Parameters"
        ])
        self.calc_table.setAlternatingRowColors(True)
        self.calc_table.verticalHeader().setVisible(False)
        
        # Populate table
        self.calc_table.setRowCount(len(self.calculations))
        for row, calc in enumerate(self.calculations):
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.setChecked(row < 2)  # Check first two by default
            checkbox_cell = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_cell)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.calc_table.setCellWidget(row, 0, checkbox_cell)
            
            # Date
            date_item = QTableWidgetItem(calc['calculation_date'])
            date_item.setData(Qt.UserRole, calc['id'])
            self.calc_table.setItem(row, 1, date_item)
            
            # Total recharge
            recharge_item = QTableWidgetItem(f"{calc['total_recharge']:.2f}")
            self.calc_table.setItem(row, 2, recharge_item)
            
            # Annual rate
            rate_item = QTableWidgetItem(f"{calc['annual_rate']:.2f}")
            self.calc_table.setItem(row, 3, rate_item)
            
            # Rises count
            rises_count = calc.get('rises_count', 'N/A')
            count_item = QTableWidgetItem(str(rises_count))
            self.calc_table.setItem(row, 4, count_item)
            
            # Parameters summary - extract from parameters dict
            params_dict = calc.get('parameters', {})
            sy = params_dict.get('specific_yield', 0.2)
            threshold = params_dict.get('rise_threshold', 0.1)
            params = f"Sy={sy:.3f}, Threshold={threshold:.2f}ft"
            params_item = QTableWidgetItem(params)
            self.calc_table.setItem(row, 5, params_item)
        
        # Resize columns to fit content
        self.calc_table.resizeColumnsToContents()
        layout.addWidget(self.calc_table)
        
        # Comparison plot
        self.figure = plt.figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        plot_btn = QPushButton("Update Comparison Plot")
        plot_btn.clicked.connect(self.update_comparison_plot)
        button_layout.addWidget(plot_btn)
        
        export_btn = QPushButton("Export Comparison")
        export_btn.clicked.connect(self.export_comparison)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Initial plot
        self.update_comparison_plot()
        
    def update_comparison_plot(self):
        """Update the comparison plot with selected calculations."""
        self.figure.clear()
        
        # Get selected calculations
        selected_calcs = []
        for row in range(self.calc_table.rowCount()):
            checkbox = self.calc_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                calc_id = self.calc_table.item(row, 1).data(Qt.UserRole)
                calc_date = self.calc_table.item(row, 1).text()
                selected_calcs.append((calc_id, calc_date))
        
        if len(selected_calcs) < 2:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Select at least 2 calculations to compare', 
                    ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            return
            
        # Create subplots
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        # Colors for different calculations
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        
        # Load and plot each calculation
        for idx, (calc_id, calc_date) in enumerate(selected_calcs):
            color = colors[idx % len(colors)]
            
            # Get calculation details
            calc_data = self.rise_db.get_calculation_details(calc_id)
            if not calc_data:
                continue
                
            # Extract yearly summaries for bar chart
            yearly_data = calc_data.get('yearly_summaries', [])
            if yearly_data:
                water_years = [y['water_year'] for y in yearly_data]
                recharges = [y['total_recharge'] for y in yearly_data]
                
                # Bar chart of yearly recharge
                x_pos = np.arange(len(water_years)) + idx * 0.2
                ax1.bar(x_pos, recharges, width=0.2, label=calc_date, color=color, alpha=0.7)
        
        # Format yearly comparison plot
        if selected_calcs:
            ax1.set_xlabel('Water Year')
            ax1.set_ylabel('Annual Recharge (inches)')
            ax1.set_title('Annual Recharge Comparison')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
        # Summary comparison
        labels = []
        total_recharges = []
        annual_rates = []
        
        for idx, (calc_id, calc_date) in enumerate(selected_calcs):
            calc = next((c for c in self.calculations if c['id'] == calc_id), None)
            if calc:
                params_dict = calc.get('parameters', {})
                sy = params_dict.get('specific_yield', 0.2)
                labels.append(f"{calc_date}\n(Sy={sy:.3f})")
                total_recharges.append(calc['total_recharge'])
                annual_rates.append(calc['annual_rate'])
        
        # Bar chart of totals
        x = np.arange(len(labels))
        width = 0.35
        
        ax2.bar(x - width/2, total_recharges, width, label='Total Recharge', alpha=0.7)
        ax2.bar(x + width/2, annual_rates, width, label='Annual Rate', alpha=0.7)
        
        ax2.set_xlabel('Calculation')
        ax2.set_ylabel('Inches')
        ax2.set_title('Total Recharge and Annual Rate')
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
        self.canvas.draw()
        
    def export_comparison(self):
        """Export comparison results."""
        selected_count = sum(1 for row in range(self.calc_table.rowCount()) 
                           if self.calc_table.cellWidget(row, 0).findChild(QCheckBox).isChecked())
        
        if selected_count < 2:
            QMessageBox.warning(self, "Selection Required", 
                              "Please select at least 2 calculations to export comparison.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Comparison", 
                "RISE_comparison.png",
                "PNG Files (*.png);;PDF Files (*.pdf)"
            )
            
            if file_path:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Export Successful", 
                                      f"Comparison exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", 
                               f"Failed to export comparison:\n{str(e)}")
    
    def update_settings(self, settings):
        """Update RISE tab with unified settings."""
        try:
            logger.info("Updating RISE tab with unified settings")
            
            # Update shared parameters
            if 'specific_yield' in settings and hasattr(self, 'sy_spinner'):
                self.sy_spinner.setValue(settings['specific_yield'])
                
            if 'water_year_month' in settings and hasattr(self, 'water_year_month'):
                self.water_year_month.setValue(settings['water_year_month'])
                
            if 'water_year_day' in settings and hasattr(self, 'water_year_day'):
                self.water_year_day.setValue(settings['water_year_day'])
            
            # Update RISE-specific parameters
            if 'rise_threshold' in settings and hasattr(self, 'threshold_spinner'):
                self.threshold_spinner.setValue(settings['rise_threshold'])
            
            # Update preprocessing parameters
            if 'downsample_frequency' in settings and hasattr(self, 'downsample_combo'):
                self.downsample_combo.setCurrentText(settings['downsample_frequency'])
                
            if 'downsample_method' in settings and hasattr(self, 'downsample_method_combo'):
                self.downsample_method_combo.setCurrentText(settings['downsample_method'])
                
            if 'enable_smoothing' in settings and hasattr(self, 'smoothing_type'):
                if settings['enable_smoothing']:
                    self.smoothing_type.setCurrentText("Moving Average")
                else:
                    self.smoothing_type.setCurrentText("No Smoothing")
                    
            if 'smoothing_window' in settings and hasattr(self, 'smoothing_window_spinner'):
                self.smoothing_window_spinner.setValue(settings['smoothing_window'])
                
            if 'window_type' in settings and hasattr(self, 'window_type_combo'):
                self.window_type_combo.setCurrentText(settings['window_type'])
            
            # Update filtering parameters  
            if 'min_time_between_events' in settings:
                # This would be implemented if the parameter exists in UI
                pass
                
            if 'max_rise_rate' in settings:
                # This would be implemented if the parameter exists in UI
                pass
            
            # Update current settings for data processing
            if settings:
                self.current_settings.update(settings)
                logger.info(f"Updated RISE settings: {settings}")
                
                # Note: Data preprocessing is now handled centrally in RechargeTab
                # The parent will call set_shared_data() with updated processed data
            
            logger.info("RISE tab settings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating RISE tab settings: {e}")
    
    def get_current_settings(self):
        """Get current RISE tab settings."""
        try:
            settings = {}
            
            # Get shared parameters
            if hasattr(self, 'sy_spinner'):
                settings['specific_yield'] = self.sy_spinner.value()
                
            if hasattr(self, 'water_year_month'):
                settings['water_year_month'] = self.water_year_month.value()
                
            if hasattr(self, 'water_year_day'):
                settings['water_year_day'] = self.water_year_day.value()
            
            # Get RISE-specific parameters
            if hasattr(self, 'threshold_spinner'):
                settings['rise_threshold'] = self.threshold_spinner.value()
            
            # Get preprocessing parameters
            if hasattr(self, 'downsample_combo'):
                settings['downsample_frequency'] = self.downsample_combo.currentText()
                
            if hasattr(self, 'downsample_method_combo'):
                settings['downsample_method'] = self.downsample_method_combo.currentText()
                
            if hasattr(self, 'smoothing_window_spinner'):
                settings['smoothing_window'] = self.smoothing_window_spinner.value()
                
            return settings
            
        except Exception as e:
            logger.error(f"Error getting RISE tab settings: {e}")
            return {}
    
    def get_method_name(self):
        """Return the method name for this tab."""
        return "RISE"
    
    def add_method_specific_plots(self, ax):
        """Add RISE-specific elements to the plot."""
        try:
            # Plot rise events if checkbox is checked
            if (hasattr(self, 'show_rise_events') and self.show_rise_events.isChecked() and 
                hasattr(self, 'rise_events') and self.rise_events):
                
                # Plot rise points
                dates = [e['date'] for e in self.rise_events]
                levels = [e.get('level', 0) for e in self.rise_events]
                rises = [e['rise'] for e in self.rise_events]
                
                # Plot markers at rise points
                ax.scatter(dates, levels, c='red', s=50, zorder=10, 
                          label='Rise Events', alpha=0.8)
                
                # Draw vertical lines showing rise magnitude
                for date, level, rise in zip(dates, levels, rises):
                    if level > 0:  # Only plot if we have valid level data
                        ax.plot([date, date], [level - rise, level], 
                               'r-', linewidth=1.5, alpha=0.6)
                               
                # Update legend
                ax.legend(loc='best', frameon=True, fancybox=True, shadow=True)
                
        except Exception as e:
            logger.error(f"Error adding RISE-specific plots: {e}")
    
    def process_data_with_settings(self, raw_data):
        """Process raw data according to global settings parameters."""
        if raw_data is None or raw_data.empty:
            return None
            
        try:
            import pandas as pd
            import numpy as np
            
            # Get current settings (use stored settings or defaults)
            settings = getattr(self, 'current_settings', {})
            logger.info(f"[PROCESS_DEBUG] Processing data with settings: {list(settings.keys())}")
            
            # Make a copy to avoid modifying original data
            processed_data = raw_data.copy()
            
            # 1. Remove outliers if enabled
            if settings.get('remove_outliers', True):
                threshold = settings.get('outlier_threshold', 3.0)
                logger.info(f"[PROCESS_DEBUG] Removing outliers with threshold: {threshold} std dev")
                
                mean_level = processed_data['level'].mean()
                std_level = processed_data['level'].std()
                lower_bound = mean_level - threshold * std_level
                upper_bound = mean_level + threshold * std_level
                
                before_count = len(processed_data)
                processed_data = processed_data[
                    (processed_data['level'] >= lower_bound) & 
                    (processed_data['level'] <= upper_bound)
                ]
                after_count = len(processed_data)
                logger.info(f"[PROCESS_DEBUG] Outlier removal: {before_count} -> {after_count} points")
            
            # 2. Apply smoothing if enabled
            if settings.get('enable_smoothing', True):
                window_size = settings.get('smoothing_window', 3)
                smoothing_type = settings.get('smoothing_type', 'Moving Average')
                
                logger.info(f"[PROCESS_DEBUG] Applying {smoothing_type} smoothing with window {window_size}")
                
                if smoothing_type == 'Moving Average':
                    # Simple moving average
                    processed_data['level'] = processed_data['level'].rolling(
                        window=window_size, center=True, min_periods=1
                    ).mean()
                
                logger.info(f"[PROCESS_DEBUG] Smoothing applied successfully")
            
            logger.info(f"[PROCESS_DEBUG] Data processing complete: {len(processed_data)} points")
            return processed_data
            
        except Exception as e:
            logger.error(f"[PROCESS_DEBUG] Error processing data: {e}", exc_info=True)
            # Return original data if processing fails
            return raw_data.copy()
    
    def populate_events_table(self, events):
        """Populate the events table with identified rise events."""
        try:
            self.event_selection_table.setRowCount(len(events))
            
            for row, event in enumerate(events):
                # Checkbox for inclusion (all selected by default)
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                self.event_selection_table.setCellWidget(row, 0, checkbox)
                
                # Event details
                self.event_selection_table.setItem(row, 1, QTableWidgetItem(str(event['event_num'])))
                self.event_selection_table.setItem(row, 2, QTableWidgetItem(str(event['water_year'])))
                self.event_selection_table.setItem(row, 3, QTableWidgetItem(event['date'].strftime('%Y-%m-%d')))
                self.event_selection_table.setItem(row, 4, QTableWidgetItem(f"{event['rise']:.3f}"))
                self.event_selection_table.setItem(row, 5, QTableWidgetItem(f"{event['recharge']:.2f}"))
            
            # Update water year filter with available years
            self.update_water_year_filter(events)
            
            logger.info(f"Populated events table with {len(events)} events")
            
        except Exception as e:
            logger.error(f"Error populating events table: {e}", exc_info=True)

    def get_selected_events_from_table(self):
        """Get the events that are selected (checked) in the table."""
        selected_events = []
        
        try:
            for row in range(self.event_selection_table.rowCount()):
                if not self.event_selection_table.isRowHidden(row):
                    checkbox = self.event_selection_table.cellWidget(row, 0)
                    if checkbox and checkbox.isChecked():
                        event_num = int(self.event_selection_table.item(row, 1).text())
                        
                        # Find the corresponding event from potential_rise_events
                        matching_events = [e for e in self.potential_rise_events if e['event_num'] == event_num]
                        if matching_events:
                            selected_events.append(matching_events[0])
            
            logger.info(f"Found {len(selected_events)} selected events from table")
            
        except Exception as e:
            logger.error(f"Error getting selected events from table: {e}", exc_info=True)
        
        return selected_events

    def calculate_recharge_for_events(self, selected_events):
        """Calculate recharge values for the provided events."""
        try:
            # Store the selected events as the final rise_events for results
            self.rise_events = selected_events
            self.rise_events_filtered = selected_events
            
            # Update results with the selected events
            self.update_results_with_events(selected_events)
            
            logger.info(f"Calculated recharge for {len(selected_events)} selected events")
            
        except Exception as e:
            logger.error(f"Error calculating recharge for events: {e}", exc_info=True)
            raise

    def update_water_year_filter(self, events):
        """Update the water year filter dropdown with years from the events."""
        try:
            # Clear existing items (except "All Water Years")
            while self.water_year_combo.count() > 1:
                self.water_year_combo.removeItem(1)
            
            # Get unique water years from events
            water_years = sorted(set(event['water_year'] for event in events))
            
            # Add water years to combo box
            for year in water_years:
                self.water_year_combo.addItem(f"Water Year {year}", year)
            
            logger.info(f"Updated water year filter with {len(water_years)} years")
            
        except Exception as e:
            logger.error(f"Error updating water year filter: {e}", exc_info=True)
