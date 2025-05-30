"""
RISE (Rapid Intensive Successive Events) method for recharge estimation.
This tab implements the RISE method for calculating recharge using water level data.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QPushButton, QGroupBox, QTableWidget, 
    QTableWidgetItem, QMessageBox, QDateEdit, QSplitter,
    QCheckBox, QFrame, QTabWidget, QGridLayout, QSizePolicy,
    QHeaderView, QSpinBox, QRadioButton, QButtonGroup,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd
from scipy import signal

logger = logging.getLogger(__name__)

class RiseTab(QWidget):
    """
    Tab implementing the RISE method for recharge estimation.
    """
    
    def __init__(self, data_manager, parent=None):
        """
        Initialize the RISE tab.
        
        Args:
            data_manager: Data manager providing access to well data
            parent: Parent widget
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.selected_wells = []
        self.well_data = {}
        self.current_well = None
        self.water_years = []
        self.selected_water_year = None
        self.raw_data = None  # Store the raw data (15-min intervals)
        self.processed_data = None  # Store the processed/filtered data
        
        # Setup UI
        self.setup_ui()
    
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
        
        # Set splitter sizes (30% left, 70% right) - more space for the graph
        self.main_splitter.setSizes([300, 700])
        
        layout.addWidget(self.main_splitter)
    
    def create_left_panel(self):
        """Create the left panel with tabs for parameters, event selection, and results."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for parameters and results
        self.left_tabs = QTabWidget()
        
        # Parameters tab
        parameters_panel = self.create_parameters_panel()
        self.left_tabs.addTab(parameters_panel, "Parameters")
        
        # Filtering tab (new)
        filtering_panel = self.create_filtering_panel()
        self.left_tabs.addTab(filtering_panel, "Filtering")
        
        # Event Selection tab
        event_selection_panel = self.create_event_selection_panel()
        self.left_tabs.addTab(event_selection_panel, "Event Selection")
        
        # Results tab
        results_panel = self.create_results_panel()
        self.left_tabs.addTab(results_panel, "Results")
        
        left_layout.addWidget(self.left_tabs)
        
        # Set minimum width to allow resizing to be smaller
        left_widget.setMinimumWidth(250)
        
        return left_widget
    
    def create_parameters_panel(self):
        """Create the parameters panel for the RISE method."""
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
        
        # Water Year Settings
        water_year_group = QGroupBox("Water Year Settings")
        water_year_layout = QVBoxLayout(water_year_group)
        water_year_layout.setSpacing(8)
        
        # Water year start month and day
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("Start Month:"))
        self.water_year_month = QSpinBox()
        self.water_year_month.setRange(1, 12)
        self.water_year_month.setValue(10)  # Default to October
        start_date_layout.addWidget(self.water_year_month)
        
        start_date_layout.addWidget(QLabel("Start Day:"))
        self.water_year_day = QSpinBox()
        self.water_year_day.setRange(1, 31)
        self.water_year_day.setValue(1)  # Default to 1st
        start_date_layout.addWidget(self.water_year_day)
        
        water_year_layout.addLayout(start_date_layout)
        water_year_layout.addWidget(QLabel("Standard water year: October 1 - September 30"))
        
        layout.addWidget(water_year_group)
        
        # Method parameters
        params_group = QGroupBox("RISE Method Parameters")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(8)
        
        # Specific yield
        sy_layout = QHBoxLayout()
        sy_layout.addWidget(QLabel("Specific Yield:"))
        self.sy_spinner = QDoubleSpinBox()
        self.sy_spinner.setRange(0.001, 0.5)
        self.sy_spinner.setSingleStep(0.01)
        self.sy_spinner.setValue(0.2)
        self.sy_spinner.setDecimals(3)
        self.sy_spinner.setToolTip("Volume of water released per unit area per unit decline in water table")
        sy_layout.addWidget(self.sy_spinner)
        params_layout.addWidget(QLabel("Volume of water released per unit area per unit decline"))
        params_layout.addLayout(sy_layout)
        
        # Rise threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Rise Threshold (ft):"))
        self.threshold_spinner = QDoubleSpinBox()
        self.threshold_spinner.setRange(0.01, 10.0)
        self.threshold_spinner.setSingleStep(0.1)
        self.threshold_spinner.setValue(0.2)  # Lower threshold to 0.2 ft
        self.threshold_spinner.setDecimals(2)
        self.threshold_spinner.setToolTip("Minimum rise to be considered significant; should be above noise level")
        threshold_layout.addWidget(self.threshold_spinner)
        params_layout.addWidget(QLabel("Minimum rise to be considered significant (eliminates noise)"))
        params_layout.addLayout(threshold_layout)
        
        # Note about daily rises
        rise_note = QLabel("Note: According to the RISE method, each daily rise is treated independently.")
        rise_note.setWordWrap(True)
        rise_note.setStyleSheet("font-style: italic; color: #555;")
        params_layout.addWidget(rise_note)
        
        layout.addWidget(params_group)
        
        # Calculate button
        self.calculate_btn = QPushButton("Calculate Recharge")
        self.calculate_btn.setEnabled(False)
        self.calculate_btn.setMinimumHeight(40)  # Make button larger and more prominent
        self.calculate_btn.clicked.connect(self.calculate_recharge)
        layout.addWidget(self.calculate_btn)
        
        layout.addStretch()
        
        return panel
    
    def create_filtering_panel(self):
        """Create the filtering panel with data preprocessing options."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Data Preprocessing Group
        preprocess_group = QGroupBox("Data Preprocessing - RISE Best Practices")
        preprocess_layout = QVBoxLayout(preprocess_group)
        preprocess_layout.setSpacing(8)
        
        # Best practices instructions with improved spacing and wrapping
        best_practices_label = QLabel(
            "Standard RISE workflow for water level data:\n\n"
            "1. Convert to daily values (e.g., median of each day)\n\n"
            "2. Apply 3-day TRAILING smoothing window (avoiding 'peeking' into future)\n\n"
            "3. Calculate rises between consecutive days"
        )
        best_practices_label.setWordWrap(True)
        best_practices_label.setMinimumHeight(100)  # Ensure enough vertical space
        best_practices_label.setStyleSheet("font-weight: bold; margin: 10px 5px; line-height: 120%;")
        preprocess_layout.addWidget(best_practices_label)
        
        # Downsampling section
        downsample_label = QLabel("Step 1: Downsampling")
        downsample_label.setStyleSheet("font-weight: bold;")
        preprocess_layout.addWidget(downsample_label)
        
        # Downsampling options
        self.downsample_combo = QComboBox()
        self.downsample_combo.addItem("None (use 15-min data, not recommended)", "none")
        self.downsample_combo.addItem("Daily (recommended)", "1D")
        self.downsample_combo.addItem("Hourly (higher resolution, more noise)", "1h")
        self.downsample_combo.addItem("Weekly (loses event resolution)", "1W")
        self.downsample_combo.setCurrentIndex(1)  # Set default to Daily
        self.downsample_combo.setToolTip("RISE method works best with daily data")
        self.downsample_combo.currentIndexChanged.connect(self.on_preprocessing_changed)
        preprocess_layout.addWidget(self.downsample_combo)
        
        # Downsampling method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.downsample_method_combo = QComboBox()
        self.downsample_method_combo.addItem("Mean (general use)", "mean")
        self.downsample_method_combo.addItem("Median (for pumped wells, recommended)", "median")
        self.downsample_method_combo.addItem("End-of-day value (for USGS RORA compatibility)", "last")
        self.downsample_method_combo.setCurrentIndex(1)  # Set default to Median
        self.downsample_method_combo.setToolTip(
            "Median is more robust against pump cycles and outliers.\n"
            "Mean is traditional but susceptible to spikes.\n"
            "End-of-day matches USGS methods but is less robust."
        )
        self.downsample_method_combo.currentIndexChanged.connect(self.on_preprocessing_changed)
        method_layout.addWidget(self.downsample_method_combo)
        preprocess_layout.addLayout(method_layout)
        
        # Smoothing section
        filter_label = QLabel("Step 2: Smoothing")
        filter_label.setStyleSheet("font-weight: bold;")
        preprocess_layout.addWidget(filter_label)
        
        # Create radio buttons for smoothing types
        self.filter_group = QButtonGroup()
        
        # No smoothing
        self.no_filter_radio = QRadioButton("No Smoothing (prone to noise)")
        self.filter_group.addButton(self.no_filter_radio)
        preprocess_layout.addWidget(self.no_filter_radio)
        
        # Moving average (recommended)
        self.ma_radio = QRadioButton("Moving Average (recommended)")
        self.ma_radio.setChecked(True)  # Set as default
        self.filter_group.addButton(self.ma_radio)
        preprocess_layout.addWidget(self.ma_radio)
        
        # Moving average window size
        ma_window_layout = QHBoxLayout()
        ma_window_layout.addSpacing(20)  # Indent
        ma_window_layout.addWidget(QLabel("Window Size:"))
        self.ma_window_spinner = QSpinBox()
        self.ma_window_spinner.setRange(2, 7)
        self.ma_window_spinner.setValue(3)  # Set default to 3-day window
        self.ma_window_spinner.setSuffix(" days")
        self.ma_window_spinner.setToolTip(
            "3-day window is optimal for most sites:\n"
            "- Removes barometric/sensor noise\n"
            "- Preserves recharge events\n"
            "- Supported by multiple studies"
        )
        self.ma_window_spinner.valueChanged.connect(self.on_preprocessing_changed)
        ma_window_layout.addWidget(self.ma_window_spinner)
        preprocess_layout.addLayout(ma_window_layout)
        
        # Window type (centered vs trailing)
        ma_centered_layout = QHBoxLayout()
        ma_centered_layout.addSpacing(20)  # Indent
        ma_centered_layout.addWidget(QLabel("Window Type:"))
        self.ma_window_type = QComboBox()
        self.ma_window_type.addItem("Trailing ([t, t-1, t-2], recommended for RISE)", "trailing")
        self.ma_window_type.addItem("Centered ([t-1, t, t+1], not recommended for RISE)", "center")
        self.ma_window_type.setToolTip(
            "RISE method requires a trailing window to maintain causality.\n"
            "- Trailing: Only uses data from today and earlier (causal)\n"
            "- Centered: Uses future data, which artificially shifts recharge timing\n"
            "For proper RISE method implementation, use trailing window."
        )
        self.ma_window_type.currentIndexChanged.connect(self.on_preprocessing_changed)
        ma_centered_layout.addWidget(self.ma_window_type)
        preprocess_layout.addLayout(ma_centered_layout)
        
        # Explanation of why trailing is important
        trailing_explanation = QLabel(
            "Why trailing window is important:\n\n"
            "A trailing window only uses past information to smooth the current "
            "value, preserving causal order. This ensures rises are attributed to the correct day.\n\n"
            "Centered windows look into the future and can shift recharge timing incorrectly."
        )
        trailing_explanation.setWordWrap(True)
        trailing_explanation.setMinimumHeight(80)  # Ensure enough vertical space
        trailing_explanation.setStyleSheet("font-style: italic; color: #555; margin: 5px 20px; line-height: 120%;")
        preprocess_layout.addWidget(trailing_explanation)
        
        # Add the preprocessing group to the main layout
        layout.addWidget(preprocess_group)
        
        # Preview processed data button
        self.preview_btn = QPushButton("Preview Processed Data")
        self.preview_btn.clicked.connect(self.preview_processed_data)
        self.preview_btn.setEnabled(False)
        layout.addWidget(self.preview_btn)
        
        layout.addStretch()
        
        return panel
    
    def create_event_selection_panel(self):
        """Create the event selection panel with filtering and events table."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Water year filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Water Year:"))
        self.water_year_combo = QComboBox()
        self.water_year_combo.addItem("All Water Years", "all")
        self.water_year_combo.currentIndexChanged.connect(self.filter_events_by_water_year)
        self.water_year_combo.setMinimumWidth(200)  # Ensure dropdown is wide enough
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
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_events)
        button_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(button_layout)
        
        # Recalculate button
        recalculate_btn = QPushButton("Recalculate with Selected")
        recalculate_btn.clicked.connect(self.recalculate_with_selected)
        recalculate_btn.setMinimumHeight(40)  # Make button larger and more prominent
        layout.addWidget(recalculate_btn)
        
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
        export_layout.addWidget(export_csv_btn)
        
        export_excel_btn = QPushButton("Export to Excel")
        export_excel_btn.clicked.connect(self.export_to_excel)
        export_layout.addWidget(export_excel_btn)
        
        layout.addLayout(export_layout)
        
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
        layout = QVBoxLayout(group_box)
        
        # Plot panel
        self.figure = plt.figure(figsize=(10, 8), dpi=100)  # Larger figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Plot options panel
        options_group = QGroupBox("Plot Options")
        options_layout = QVBoxLayout(options_group)
        
        # Display options
        options_row = QHBoxLayout()
        
        self.show_raw_data = QCheckBox("Show Raw Data")
        self.show_raw_data.setChecked(True)
        self.show_raw_data.setToolTip("Display the original 15-minute data (low opacity)")
        self.show_raw_data.stateChanged.connect(self.update_plot)
        options_row.addWidget(self.show_raw_data)
        
        self.show_processed_data = QCheckBox("Show Processed Data")
        self.show_processed_data.setChecked(True)
        self.show_processed_data.setToolTip("Display the downsampled and filtered data")
        self.show_processed_data.stateChanged.connect(self.update_plot)
        options_row.addWidget(self.show_processed_data)
        
        self.show_rise_events = QCheckBox("Show Rise Events")
        self.show_rise_events.setChecked(True)
        self.show_rise_events.setToolTip("Highlight identified rise events in red")
        self.show_rise_events.stateChanged.connect(self.update_plot)
        options_row.addWidget(self.show_rise_events)
        
        self.show_selected_event = QCheckBox("Highlight Selected")
        self.show_selected_event.setChecked(True)
        self.show_selected_event.setToolTip("Highlight the currently selected event with a green fill")
        self.show_selected_event.stateChanged.connect(self.update_plot)
        options_row.addWidget(self.show_selected_event)
        
        options_layout.addLayout(options_row)
        
        # Add refresh button
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self.update_plot)
        options_layout.addWidget(refresh_btn)
        
        options_layout.addStretch()
        layout.addWidget(options_group)
        
        return group_box
    
    def update_well_selection(self, selected_wells):
        """Update the list of selected wells."""
        self.selected_wells = selected_wells
        
        # Update combo box
        self.well_combo.clear()
        
        if selected_wells:
            self.well_combo.setEnabled(True)
            self.calculate_btn.setEnabled(True)
            
            for well_id, well_name in selected_wells:
                self.well_combo.addItem(f"{well_name} ({well_id})", well_id)
        else:
            self.well_combo.setEnabled(False)
            self.calculate_btn.setEnabled(False)
    
    def on_well_selected(self, index):
        """Handle well selection from dropdown."""
        if index < 0:
            return
            
        well_id = self.well_combo.currentData()
        well_name = self.well_combo.currentText()
        self.current_well = well_id
        
        # Clear any existing results
        self.clear_results()
        
        # Reset selected water year
        self.selected_water_year = "all"
        
        # Switch to Parameters tab
        self.left_tabs.setCurrentIndex(0)  # Make sure we're on the Parameters tab when well changes
        
        # Load well data if not already loaded
        if well_id not in self.well_data:
            self.load_well_data(well_id)
        
        # Set date range based on available data for this well
        if well_id in self.well_data and self.well_data[well_id]:
            self.set_date_range_from_data(self.well_data[well_id])
            
        # Update the status in the UI
        self.calculate_btn.setText(f"Calculate Recharge for {well_name}")
        self.calculate_btn.setEnabled(True)
    
    def load_well_data(self, well_id):
        """Load water level data for the selected well."""
        try:
            logger.info(f"Loading data for well {well_id}")
            
            # Use the data_manager to fetch actual data from the database
            # Instead of generating synthetic data
            if hasattr(self.data_manager, 'get_well_data'):
                df = self.data_manager.get_well_data(well_id)
                
                if df is not None and not df.empty:
                    logger.info(f"Loaded {len(df)} data points for well {well_id}")
                    
                    # Check column names and rename if necessary to match expected format
                    if 'timestamp_utc' in df.columns and 'water_level' in df.columns:
                        # Rename columns to match expected format for the rise tab
                        df = df.rename(columns={
                            'timestamp_utc': 'timestamp',
                            'water_level': 'level'
                        })
                    
                    # Make sure the timestamp is in datetime format
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # Store the raw data
                    self.raw_data = df
                    
                    # Process the data with current preprocessing settings
                    self.process_data()
                    
                    # Update the plot to show the data
                    self.update_plot()
                    
                    return
            
            # If we're here, either we couldn't get data or we got an empty dataset
            # As a fallback, create synthetic data for demonstration
            logger.warning(f"Using synthetic data for well {well_id}")
            self._create_synthetic_data()
            
        except Exception as e:
            logger.error(f"Error loading well data: {e}", exc_info=True)
            QMessageBox.warning(
                self, "Data Loading Error", 
                f"Failed to load data for well {well_id}: {str(e)}"
            )
            
            # Use synthetic data as fallback
            logger.warning(f"Using synthetic data as fallback for well {well_id}")
            self._create_synthetic_data()
    
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
        
        # Create a pandas DataFrame
        self.raw_data = pd.DataFrame({
            'timestamp': pd.to_datetime(timestamps),  # Ensure proper datetime format
            'level': levels
        })
        
        logger.debug(f"Generated synthetic data with {len(self.raw_data)} points")
        
        # Process the data with current preprocessing settings
        self.process_data()
        
        if self.processed_data is None:
            logger.warning("Failed to process data after loading")
            # Just use raw data if processing failed
            self.processed_data = self.raw_data.copy()
        
        # Update the plot to show the data
        self.update_plot()
    
    def set_date_range_from_data(self, data):
        """Set date range based on available data."""
        # Placeholder - would set date range from actual data
        # For now, using default range
        start_date = QDate.currentDate().addYears(-1)
        end_date = QDate.currentDate()
        
        self.start_date.setDate(start_date)
        self.end_date.setDate(end_date)
    
    def set_full_date_range(self):
        """Set date range to cover all available data."""
        if self.current_well and self.current_well in self.well_data:
            self.set_date_range_from_data(self.well_data[self.current_well])
    
    def calculate_recharge(self):
        """Calculate recharge using the RISE method."""
        logger.info("=" * 50)
        logger.info("CALCULATING RECHARGE")
        
        # Clear previous results
        self.clear_results()
        
        # Get parameters
        rise_threshold = self.threshold_spinner.value()
        specific_yield = self.sy_spinner.value()
        
        # Log parameters
        logger.info(f"Parameters:")
        logger.info(f"- Rise threshold: {rise_threshold} ft")
        logger.info(f"- Specific yield: {specific_yield}")
        logger.info(f"- Water year starts: Month {self.water_year_month.value()}, Day {self.water_year_day.value()}")
        
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
            
            # Set up water year parameters
            water_year_month = self.water_year_month.value()
            water_year_day = self.water_year_day.value()
            
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
        
        Args:
            use_filtered: Whether to use filtered events
            preview_mode: Whether to show raw and processed data for preview
        """
        try:
            self.figure.clear()
            
            # If we have no data at all, just show an empty plot
            if not hasattr(self, 'raw_data') or self.raw_data is None or self.raw_data.empty:
                ax = self.figure.add_subplot(111)
                ax.set_title("No data available")
                ax.set_xlabel("Date")
                ax.set_ylabel("Water Level (ft)")
                ax.grid(True)
                self.canvas.draw()
                return
            
            # Create a single subplot for all data
            ax = self.figure.add_subplot(111)
            
            # Initialize variables for water year filtering
            selected_water_year = None
            
            # Determine if we should filter by water year from the Event Selection tab
            if hasattr(self, 'selected_water_year') and self.selected_water_year and self.selected_water_year != "all":
                selected_water_year = self.selected_water_year
                logger.info(f"Zooming plot to water year: {selected_water_year}")
            
            # Determine data date range for zoom
            x_min, x_max = None, None
            
            # If filtering by water year, zoom to that time period
            if selected_water_year and hasattr(self, 'processed_data') and self.processed_data is not None:
                # Get the water year start month/day
                water_year_month = self.water_year_month.value()
                water_year_day = self.water_year_day.value()
                
                # Extract year components from the water year string (format: "YYYY-YYYY")
                if "-" in selected_water_year:
                    year_parts = selected_water_year.split("-")
                    start_year = int(year_parts[0])
                    end_year = int(year_parts[1])
                else:
                    # Handle single year format if needed
                    start_year = int(selected_water_year) - 1
                    end_year = int(selected_water_year)
                
                # Calculate the date range for this water year
                x_min = pd.Timestamp(year=start_year, month=water_year_month, day=water_year_day)
                x_max = pd.Timestamp(year=end_year, month=water_year_month, day=water_year_day)
                
                logger.info(f"Water year zoom range: {x_min.date()} to {x_max.date()}")
            
            # Plot raw data if option is checked (always in preview mode)
            if (hasattr(self, 'show_raw_data') and self.show_raw_data.isChecked()) or preview_mode:
                raw_timestamps = pd.to_datetime(self.raw_data['timestamp'])
                ax.plot(
                    raw_timestamps, 
                    self.raw_data['level'], 
                    'b-', 
                    linewidth=0.8, 
                    alpha=0.3, 
                    label='Raw Data'
                )
            
            # Plot processed data if option is checked (always in preview mode)
            if ((hasattr(self, 'show_processed_data') and self.show_processed_data.isChecked()) or preview_mode) and hasattr(self, 'processed_data') and self.processed_data is not None:
                # Get timestamps and levels from processed data
                if 'timestamp' in self.processed_data.columns:
                    processed_timestamps = pd.to_datetime(self.processed_data['timestamp'])
                    level_column = 'level'
                else:
                    # If timestamp is the index
                    processed_timestamps = self.processed_data.index
                    level_column = self.processed_data.columns[0]
                
                # Plot processed data more prominently
                ax.plot(
                    processed_timestamps, 
                    self.processed_data[level_column], 
                    'g-', 
                    linewidth=1.5, 
                    label='Processed Data'
                )
            
            # In preview mode, just show raw vs processed data
            if preview_mode:
                title_text = f'Data Preprocessing Preview - {self.well_combo.currentText()}'
                ax.set_title(title_text)
                ax.legend()
                ax.grid(True)
                ax.set_xlabel('Date')
                ax.set_ylabel('Water Level (ft)')
                
                # Format x-axis dates
                self.figure.autofmt_xdate()
                self.canvas.draw()
                return
            
            # If we have rise events and the option is checked
            if hasattr(self, 'rise_events') and hasattr(self, 'show_rise_events') and self.show_rise_events.isChecked():
                events_to_plot = self.rise_events_filtered if use_filtered and hasattr(self, 'rise_events_filtered') else self.rise_events
                
                # Filter by water year if needed
                if selected_water_year and not use_filtered:  # Only if not already filtered
                    events_to_plot = [e for e in events_to_plot if e['water_year'] == selected_water_year]
                
                # Plot all rise points with markers
                dates = [event['date'] for event in events_to_plot]
                rises = [event['rise'] for event in events_to_plot]
                
                # Find the corresponding levels for these dates
                levels = []
                for event in events_to_plot:
                    date = event['date']
                    if 'level' in event:
                        levels.append(event['level'])
                    else:
                        # Find this date in the processed data
                        if 'timestamp' in self.processed_data.columns:
                            mask = (self.processed_data['timestamp'] == date)
                            if mask.any():
                                levels.append(self.processed_data.loc[mask, level_column].iloc[0])
                            else:
                                # If we can't find the exact date, use the level from the event itself
                                levels.append(None)
                        else:
                            try:
                                # If timestamp is the index
                                levels.append(self.processed_data.loc[date, level_column])
                            except:
                                levels.append(None)
                
                # Plot each rise point with a marker
                for i, (date, level, rise) in enumerate(zip(dates, levels, rises)):
                    if level is not None:
                        # Mark the rise point with a red dot (smaller size)
                        ax.plot(date, level, 'ro', markersize=4, zorder=10)
                        
                        # Optionally add a line to show the rise
                        if rise > 0:
                            # Draw a vertical line to show the magnitude of the rise
                            ax.plot([date, date], [level - rise, level], 'r-', linewidth=1.0, zorder=5)
                
                # Highlight selected event if option is checked
                if hasattr(self, 'selected_event') and self.selected_event is not None and hasattr(self, 'show_selected_event') and self.show_selected_event.isChecked():
                    # Find the event
                    if self.selected_event < len(events_to_plot):
                        event = events_to_plot[self.selected_event]
                        date = event['date']
                        
                        if 'level' in event and event['level'] is not None:
                            level = event['level']
                            rise = event['rise']
                            
                            # Highlight the point with a smaller marker
                            ax.plot(date, level, 'go', markersize=6, zorder=15)
                            
                            # Draw a green vertical line for the rise
                            if rise > 0:
                                ax.plot([date, date], [level - rise, level], 'g-', linewidth=2, zorder=14)
                                
                                # Shade the area of the rise
                                ax.fill_between([date - pd.Timedelta(hours=6), date + pd.Timedelta(hours=6)],
                                                [level - rise, level - rise], 
                                                [level, level], 
                                                color='g', alpha=0.3, zorder=13)
            
            # Build legend items
            legend_items = []
            if hasattr(self, 'show_raw_data') and self.show_raw_data.isChecked():
                legend_items.append('Raw Data')
            if hasattr(self, 'show_processed_data') and self.show_processed_data.isChecked() and hasattr(self, 'processed_data') and self.processed_data is not None:
                legend_items.append('Processed Data')
            if hasattr(self, 'show_rise_events') and self.show_rise_events.isChecked() and hasattr(self, 'rise_events'):
                legend_items.append('Rise Points')
            
            # Add legend if we have items
            if legend_items:
                ax.legend(legend_items)
                
            # Always add grid
            ax.grid(True)
            ax.set_xlabel('Date')
            ax.set_ylabel('Water Level (ft)')
            
            # Create title with appropriate information
            title_text = f'Water Level Data - {self.well_combo.currentText()}'
            
            # Add preprocessing info
            if hasattr(self, 'processed_data') and self.processed_data is not None:
                preprocess_text = ""
                if hasattr(self, 'downsample_combo') and self.downsample_combo.currentData() != "none":
                    preprocess_text += f" ({self.downsample_combo.currentText()})"
                
                if hasattr(self, 'ma_radio') and self.ma_radio.isChecked():
                    preprocess_text += f" (MA Filter)"
                
                title_text += preprocess_text
            
            # Add water year or selected events count
            if selected_water_year:
                title_text += f' (Water Year: {selected_water_year})'
            elif use_filtered and hasattr(self, 'rise_events_filtered'):
                title_text += f' ({len(events_to_plot)} selected rises)'
            
            ax.set_title(title_text)
            
            # Set the x-axis limits if we're filtering by water year
            if x_min is not None and x_max is not None:
                ax.set_xlim(x_min, x_max)
                logger.info(f"Zooming plot to water year range: {x_min.date()} to {x_max.date()}")
            
            # Format x-axis dates
            self.figure.autofmt_xdate()
            self.figure.tight_layout()
            
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}", exc_info=True)
            # Don't show message box for plot errors to avoid excessive dialogs
            # Just clear the figure to prevent display issues
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_title("Error plotting data")
            self.canvas.draw()
    
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
            
        # This is a placeholder function - implementation will be added later
        QMessageBox.information(self, "Export", "CSV export will be implemented in a future update.")
        
    def export_to_excel(self):
        """Export results to Excel file."""
        if not hasattr(self, 'rise_events') or not self.rise_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        # This is a placeholder function - implementation will be added later
        QMessageBox.information(self, "Export", "Excel export will be implemented in a future update.")
    
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
        month = self.water_year_month.value()
        day = self.water_year_day.value()
        
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
            
            # Step 1: Flag and handle outliers/pump cycles if enabled
            if hasattr(self, 'max_rate_check') and self.max_rate_check.isChecked():
                # Convert rate threshold from ft/hr to ft per data interval
                time_diff = pd.Series(data['timestamp']).diff().dt.total_seconds().median() / 3600  # hours
                rate_threshold = self.max_rate_spinner.value() * time_diff  # Convert to ft per interval
                
                logger.info(f"Filtering outliers with rate threshold of {self.max_rate_spinner.value()} ft/hr")
                logger.info(f"Median time interval: {time_diff*3600:.1f} seconds ({time_diff:.4f} hours)")
                
                # Calculate rate of change
                data['level_diff'] = data['level'].diff()
                
                # Flag points with excessive rate of change (potential pump cycles)
                data['outlier'] = abs(data['level_diff']) > rate_threshold
                
                # Log number of outliers
                outlier_count = data['outlier'].sum()
                logger.info(f"Flagged {outlier_count} points ({outlier_count/len(data)*100:.1f}%) as outliers")
                
                # Handle small gaps with interpolation if selected
                if self.gap_combo.currentData() == "linear":
                    logger.info("Using linear interpolation for small gaps (<2 hrs)")
                    # Find runs of outliers less than 2 hours
                    data['outlier_run'] = (data['outlier'] != data['outlier'].shift()).cumsum()
                    runs = data[data['outlier']].groupby('outlier_run')
                    
                    # Get timestamp column or index
                    timestamp_col = 'timestamp' if 'timestamp' in data.columns else data.index
                    
                    interpolated_gaps = 0
                    for _, run in runs:
                        if len(run) > 0:
                            # Calculate run duration
                            if isinstance(timestamp_col, str):
                                start_time = run[timestamp_col].iloc[0]
                                end_time = run[timestamp_col].iloc[-1]
                            else:
                                start_time = run.index[0]
                                end_time = run.index[-1]
                            
                            duration = (end_time - start_time).total_seconds() / 3600  # hours
                            
                            # Only interpolate gaps less than 2 hours
                            if duration < 2:
                                # Get indices to interpolate between
                                if isinstance(timestamp_col, str):
                                    run_indices = run.index
                                    start_idx = run_indices[0] - 1 if run_indices[0] > 0 else run_indices[0]
                                    end_idx = run_indices[-1] + 1 if run_indices[-1] < len(data) - 1 else run_indices[-1]
                                else:
                                    run_indices = [data.index.get_loc(idx) for idx in run.index]
                                    start_idx = run_indices[0] - 1 if run_indices[0] > 0 else run_indices[0]
                                    end_idx = run_indices[-1] + 1 if run_indices[-1] < len(data) - 1 else run_indices[-1]
                                
                                # Linear interpolation for this gap
                                if start_idx != end_idx:
                                    data.loc[run.index, 'level'] = np.nan  # Set outliers to NaN
                                    interpolated_gaps += 1
                            else:
                                # For longer gaps, set to NaN
                                data.loc[run.index, 'level'] = np.nan
                    
                    logger.info(f"Interpolated {interpolated_gaps} short gaps")
                    
                    # Interpolate the NaN values
                    original_nan_count = data['level'].isna().sum()
                    data['level'] = data['level'].interpolate(method='linear', limit=8)  # Limit to 2 hours at 15-min intervals
                    final_nan_count = data['level'].isna().sum()
                    logger.info(f"NaN values: {original_nan_count} before interpolation, {final_nan_count} after")
                else:
                    # Set outliers to NaN without interpolation
                    data.loc[data['outlier'], 'level'] = np.nan
                    logger.info(f"Set {outlier_count} outliers to NaN without interpolation")
                
                # Remove temporary columns
                if 'outlier' in data.columns:
                    data = data.drop(['outlier'], axis=1)
                if 'level_diff' in data.columns: 
                    data = data.drop(['level_diff'], axis=1)
                if 'outlier_run' in data.columns:
                    data = data.drop(['outlier_run'], axis=1)
            
            # Step 2: Apply downsampling (to daily by default)
            resample_rule = self.downsample_combo.currentData()
            if resample_rule != "none":
                # Set timestamp as index for resampling
                if 'timestamp' in data.columns:
                    logger.info(f"Downsampling to {resample_rule} intervals using {self.downsample_method_combo.currentText()}")
                    
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
                    method = self.downsample_method_combo.currentData()
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
            
            # Step 3: Apply smoothing if selected
            apply_smoothing = True
            if self.no_filter_radio.isChecked():
                apply_smoothing = False
                logger.info("No smoothing filter applied")
            
            if apply_smoothing:
                # Determine window type
                window_type = "center"
                if hasattr(self, 'ma_window_type'):
                    window_type = self.ma_window_type.currentData()
                
                center = window_type == "center"
                
                if self.ma_radio.isChecked():
                    # Moving average filter
                    window = self.ma_window_spinner.value()
                    min_periods = 1 if center else None  # At least 1 value for centered MA
                    
                    logger.info(f"Applying {window}-point moving average filter (centered={center})")
                    
                    # Apply smoothing
                    if 'level' in data.columns:  # If using timestamp column
                        data['level'] = data['level'].rolling(window=window, center=center, min_periods=min_periods).mean()
                    else:  # If data is a Series or has index as timestamp
                        data = data.rolling(window=window, center=center, min_periods=min_periods).mean()
                    
                    logger.debug(f"Applied {window}-point moving average filter (centered={center})")
                    
                elif self.median_radio.isChecked():
                    # Median filter
                    window = self.median_window_spinner.value()
                    min_periods = 1 if center else None
                    
                    logger.info(f"Applying {window}-point median filter (centered={center})")
                    
                    # Apply smoothing
                    if 'level' in data.columns:
                        data['level'] = data['level'].rolling(window=window, center=center, min_periods=min_periods).median()
                    else:
                        data = data.rolling(window=window, center=center, min_periods=min_periods).median()
                    
                    logger.debug(f"Applied {window}-point median filter (centered={center})")
            
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