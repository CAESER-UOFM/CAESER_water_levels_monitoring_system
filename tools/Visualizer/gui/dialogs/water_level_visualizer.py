import os
import logging
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QDateEdit, QSplitter, QWidget, QColorDialog, QButtonGroup, 
    QRadioButton, QAbstractItemView, QLineEdit, QHeaderView, QShortcut, 
    QStatusBar, QFrame, QTabWidget, QProgressDialog, QSizePolicy, QApplication,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QKeySequence, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView
import numpy as np
import time

from ..managers.plot_handler import PlotHandler
from ..managers.data_manager import DataManager
from ..managers.export_manager import ExportManager
from ..managers.map_handler import MapHandler
from ..managers.central_data_store import CentralDataStore
from ..utils.theme_manager import ThemeManager
# Recharge tab moved to main app
# Import the new plot controls dialog
from .plot_controls_dialog import PlotControlsDialog

logger = logging.getLogger(__name__)

class WaterLevelVisualizer(QDialog):
    """Streamlined dialog for visualizing water level data using modular components."""
    
    # Signal for thread-safe UI updates
    reading_count_update = pyqtSignal(int, int)  # row, count
    
    def __init__(self, db_manager=None, parent=None):
        logger.info("Initializing WaterLevelVisualizer...")
        super().__init__(parent)
        
        # Handle different initialization scenarios
        if db_manager is None:
            # Opened directly - try to load last used database or start without one
            self.db_manager, self.db_path = self._initialize_standalone_mode()
        else:
            # Opened from main app - use provided database
            self.db_manager = db_manager
            self.db_path = str(self.db_manager.current_db)
            self._save_last_database_path(self.db_path)
            
        logger.info(f"Database path: {self.db_path}")
        
        # Log absolute path for debugging
        import os
        abs_path = os.path.abspath(self.db_path)
        logger.info(f"Absolute database path: {abs_path}")
        if os.path.exists(abs_path):
            logger.info(f"Database file exists at: {abs_path}")
        else:
            logger.warning(f"Database file NOT found at: {abs_path}")
        
        # Property to store pre-selected well
        self.pre_selected_well = None
        
        # Connect signal for thread-safe reading count updates
        self.reading_count_update.connect(self.update_reading_count)
        
        # Initialize managers - use fast data manager for better performance
        logger.info("Creating data manager...")
        if self.db_path:
            try:
                from ..managers.data_manager_fast import FastDataManager
                self.data_manager = FastDataManager(self.db_path)
                logger.info("Using FastDataManager for improved performance")
            except Exception as e:
                logger.warning(f"Failed to use FastDataManager, falling back to standard: {e}")
                self.data_manager = DataManager(self.db_path)
        else:
            # No database available - create a placeholder data manager
            self.data_manager = None
            logger.info("No database available - data manager not initialized")
        logger.info("Creating plot handler...")
        self.plot_handler = PlotHandler(self)
        logger.info("Creating map handler...")
        self.map_handler = MapHandler(self)
        logger.info("Creating export manager...")
        self.export_manager = ExportManager(self.data_manager, self.plot_handler) if self.data_manager else None
        logger.info("Creating theme manager...")
        self.theme_manager = ThemeManager()
        
        # Create central data store
        logger.info("Creating central data store...")
        if self.data_manager:
            self.central_data_store = CentralDataStore(self.data_manager)
            
            # Connect data store signals
            self.central_data_store.loading_started.connect(self.on_loading_started)
            self.central_data_store.loading_finished.connect(self.on_loading_finished)
            self.central_data_store.error_occurred.connect(self.on_data_error)
        else:
            self.central_data_store = None
        
        # Try to load saved properties
        logger.info("Loading saved plot properties...")
        self.plot_handler.load_properties()
        
        # Initialize state
        logger.info("Initializing state variables...")
        self.selected_wells = []
        self.well_colors = {}
        self.well_line_widths = {}
        self.well_line_styles = {}
        self.date_range = {'start': None, 'end': None}
        self.theme = "light"
        self.color_theme = "blue"
        self.show_temperature = False  # Default to showing water levels
        
        # Prevent dialog from closing when ESC is pressed
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        # Create the plot controls dialog but don't show it yet
        self.plot_controls_dialog = None
        
        # Setup UI
        logger.info("Setting up UI...")
        self.setup_ui()
        logger.info("Setting up keyboard shortcuts...")
        self.setup_shortcuts()
        
        # Defer well loading to after the UI is shown
        logger.info("Scheduling wells data loading...")
        logger.info("[MAIN_PLOT_DEBUG] About to schedule load_wells with QTimer")
        QTimer.singleShot(100, self.load_wells)
        
        # Schedule database info update after UI is ready
        QTimer.singleShot(50, self.update_database_info)
        
        # Connect signals
        self.plot_handler.plot_updated.connect(self.on_plot_updated)
        self.plot_handler.error_occurred.connect(self.on_error)
        self.plot_handler.point_clicked.connect(self.on_point_clicked)
        self.map_handler.map_updated.connect(lambda: self.status_bar.showMessage("Map updated successfully."))
        self.map_handler.error_occurred.connect(self.on_error)
        self.map_handler.well_selected.connect(self.on_map_well_selected)
        
        # Apply initial theme
        logger.info("Applying initial theme...")
        self.apply_theme()
        
        # Select pre-selected well if provided
        logger.info("Scheduling pre-selected well selection...")
        QTimer.singleShot(500, self.select_pre_selected_well)
        
        logger.info("WaterLevelVisualizer initialization completed!")
    
    def keyPressEvent(self, event):
        """Handle key press events, specifically preventing ESC from closing the dialog."""
        if event.key() == Qt.Key_Escape:
            # Prevent ESC from closing the dialog to avoid losing user work
            logger.info("ESC key pressed - ignoring to prevent accidental closure")
            event.ignore()  # Don't process the ESC key
            return
        
        # For all other keys, use the default behavior
        super().keyPressEvent(event)
    
    def setup_ui(self):
        """Set up the dialog UI with a clean, modular layout."""
        self.setWindowTitle("Water Level Data Visualizer")
        
        # Get screen geometry for smart sizing
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        
        # Use 90% of screen width and 85% of screen height
        width = int(screen.width() * 0.90)
        height = int(screen.height() * 0.85)
        
        # Set minimum and maximum sizes
        self.setMinimumSize(1400, 600)  # Increased minimum width
        self.setMaximumSize(screen.width(), screen.height())
        
        # Resize to calculated dimensions
        self.resize(width, height)
        
        # Center the window on screen
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins for more content space
        main_layout.setSpacing(6)  # Tighter spacing
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Main content - now just the upper section
        upper_section = self.create_upper_section()
        main_layout.addWidget(upper_section, 1)  # Give it a stretch factor to take all space
        
        # Status bar at the bottom
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        
        # Add database info and switch button to status bar
        self.setup_database_controls()
        
        main_layout.addWidget(self.status_bar)
        
        # Create the plot controls dialog but don't show it yet
        # This ensures it is available for all methods
        try:
            from gui.dialogs.plot_controls_dialog import PlotControlsDialog
            self.plot_controls_dialog = PlotControlsDialog(self)
            
            # Connect signals
            self.plot_controls_dialog.plot_updated.connect(self.on_plot_updated)
            self.plot_controls_dialog.export_triggered.connect(self.handle_export)
            
            # Create property aliases to access dialog controls
            self.setup_control_aliases()
        except Exception as e:
            logger.error(f"Error creating plot controls dialog: {e}")
            self.plot_controls_dialog = None
        
        # Set up keyboard shortcuts
        self.setup_shortcuts()
    
    def setup_control_aliases(self):
        """Create aliases for accessing plot control dialog widgets."""
        if self.plot_controls_dialog:
            # Font size control aliases
            self.axis_font_size = self.plot_controls_dialog.font_size_spinner
            self.legend_font_size = self.plot_controls_dialog.legend_font_spinner
            
            # For title font size, we can use the same as axis for now
            # or create a separate control later
            self.title_font_size = self.plot_controls_dialog.font_size_spinner
            
            # Trend control aliases
            self.trend_type_combo = self.plot_controls_dialog.trend_type_combo
            self.trend_degree_spinner = self.plot_controls_dialog.trend_degree_spinner
            self.trend_style_combo = self.plot_controls_dialog.trend_style_combo
            self.trend_width_spinner = self.plot_controls_dialog.trend_width_spinner
            self.trend_color_button = self.plot_controls_dialog.trend_color_button
            self.show_trend_cb = self.plot_controls_dialog.show_trend_cb
    
    def create_header(self):
        """Create the header section with title and theme selection."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("Water Level Data Visualizer")
        title.setObjectName("headerTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Plot controls button moved to toolbar area
        
        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(5)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light Theme", "Dark Theme", "Blue Theme", "Earth Theme"])
        self.theme_combo.setCurrentIndex(0)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        self.theme_combo.setMaximumWidth(120)
        theme_layout.addWidget(self.theme_combo)
        
        layout.addLayout(theme_layout)
        
        return header
    
    def create_upper_section(self):
        """Create the upper section with well selection and plot."""
        upper = QWidget()
        layout = QVBoxLayout(upper)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Well selection
        left_panel = self.create_well_selection_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Plot
        right_panel = self.create_plot_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter sizes - with wider window, we can use better proportions
        # 25% for well selection, 75% for plot area
        splitter.setSizes([350, 1050])  # Adjusted for wider window
        splitter.setStretchFactor(0, 0)  # Well panel doesn't stretch
        splitter.setStretchFactor(1, 1)  # Plot panel stretches
        
        layout.addWidget(splitter)
        return upper
    
    def create_well_selection_panel(self):
        """Create the well selection panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Well selection group
        well_group = QGroupBox("Available Wells")
        well_layout = QVBoxLayout(well_group)
        
        # Well table
        self.well_table = QTableWidget()
        self.well_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.well_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Connect selection signal with debug
        def debug_selection_changed(selected, deselected):
            print(f"[MAIN_PLOT_DEBUG] Selection changed! Selected: {len(selected.indexes())}")
            self.on_well_selection_changed()
            
        def debug_item_clicked(item):
            print(f"[MAIN_PLOT_DEBUG] Item clicked: {item.text()}")
            self.on_well_selection_changed()
            
        self.well_table.selectionModel().selectionChanged.connect(debug_selection_changed)
        self.well_table.itemClicked.connect(debug_item_clicked)
        well_layout.addWidget(self.well_table)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Aquifer:"))
        self.filter_input = QComboBox()
        # Remove editable property to make it a standard dropdown
        self.filter_input.currentIndexChanged.connect(lambda index: self.filter_wells(self.filter_input.currentText()))
        self.filter_input.setToolTip("Select a specific aquifer or water body to filter the wells list")
        filter_layout.addWidget(self.filter_input)
        well_layout.addLayout(filter_layout)
        
        layout.addWidget(well_group)
        return panel
    
    def create_plot_panel(self):
        """Create the plot panel with tabs for plot and map."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Plot tab
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        
        # Create a toolbar area with navigation and control buttons
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.plot_handler.get_toolbar())
        toolbar_layout.addStretch()  # Push buttons to the right
        
        # Add plot controls button
        controls_btn = QPushButton("Plot Controls")
        controls_btn.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        controls_btn.setToolTip("Open plot controls dialog")
        controls_btn.clicked.connect(self.show_plot_controls)
        controls_btn.setStyleSheet("""
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
        """)
        toolbar_layout.addWidget(controls_btn)
        
        # Add separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator.setMaximumWidth(2)
        toolbar_layout.addWidget(separator)
        
        # Add export buttons to toolbar area
        export_plot_btn = QPushButton("Export Plot")
        export_plot_btn.setIcon(self.style().standardIcon(self.style().SP_DialogSaveButton))
        export_plot_btn.setToolTip("Export plot as PNG image")
        export_plot_btn.clicked.connect(self.export_plot)
        export_plot_btn.setStyleSheet("""
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
        """)
        toolbar_layout.addWidget(export_plot_btn)
        
        export_data_btn = QPushButton("Export Data")
        export_data_btn.setIcon(self.style().standardIcon(self.style().SP_FileDialogDetailedView))
        export_data_btn.setToolTip("Export data as CSV file")
        export_data_btn.clicked.connect(self.export_data)
        export_data_btn.setStyleSheet("""
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
        """)
        toolbar_layout.addWidget(export_data_btn)
        
        # Add toolbar layout and plot widget
        plot_layout.addLayout(toolbar_layout)
        plot_layout.addWidget(self.plot_handler.get_widget())
        
        # Map tab
        map_tab = QWidget()
        map_tab.setObjectName("map_tab")
        map_layout = QVBoxLayout(map_tab)
        
        # Use map_handler instead of directly creating web view
        self.map_view = self.map_handler.get_widget()
        self.map_view.setMinimumSize(1000, 400)  # Wider but shorter for better fit
        map_layout.addWidget(self.map_view)
        
        # Add tabs
        self.tab_widget.addTab(plot_tab, "Plot View")
        self.tab_widget.addTab(map_tab, "Map View")
        
        # Recharge Estimates tab moved to main app
        
        # Connect tab change signal to update map when switching to map tab
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Initial map update
        QTimer.singleShot(100, self.update_map_display)
        
        layout.addWidget(self.tab_widget)
        return panel
    
    def setup_database_controls(self):
        """Setup database info label and switch button in the status bar."""
        # Create database info label
        self.db_info_label = QLabel()
        self.db_info_label.setMinimumWidth(200)
        self.status_bar.addWidget(self.db_info_label)
        
        # Add database switch button
        self.db_switch_btn = QPushButton("📂 Switch DB")
        self.db_switch_btn.setMaximumWidth(100)
        self.db_switch_btn.setToolTip("Switch to a different database file")
        self.db_switch_btn.clicked.connect(self.switch_database)
        self.db_switch_btn.setStyleSheet("""
            QPushButton {
                padding: 3px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        self.status_bar.addPermanentWidget(self.db_switch_btn)
        
        # Update the database info
        self.update_database_info()
    
    def _initialize_standalone_mode(self):
        """Initialize the visualizer in standalone mode (no db_manager provided)."""
        # Try to load the last used database path
        last_db_path = self._get_last_database_path()
        
        if last_db_path and os.path.exists(last_db_path):
            try:
                # Try to use the last database
                from simple_db_manager import SimpleDatabaseManager
                db_manager = SimpleDatabaseManager(last_db_path)
                logger.info(f"Loaded last used database: {last_db_path}")
                return db_manager, last_db_path
            except Exception as e:
                logger.warning(f"Failed to load last database {last_db_path}: {e}")
        
        # No valid database available - return None values
        logger.info("Starting in standalone mode without database")
        return None, ""
    
    def _get_settings_file_path(self):
        """Get the path to the visualizer settings file."""
        # Store settings in the same directory as the visualizer
        current_dir = os.path.dirname(os.path.abspath(__file__))
        settings_dir = os.path.join(current_dir, "..", "..", "..")
        settings_file = os.path.join(settings_dir, "visualizer_settings.json")
        return os.path.abspath(settings_file)
    
    def _get_last_database_path(self):
        """Get the last used database path from settings."""
        settings_file = self._get_settings_file_path()
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('last_database_path')
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}")
        return None
    
    def _save_last_database_path(self, db_path):
        """Save the database path to settings."""
        settings_file = self._get_settings_file_path()
        try:
            # Load existing settings or create new
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            
            # Update database path
            settings['last_database_path'] = db_path
            
            # Save settings
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
            logger.debug(f"Saved last database path: {db_path}")
        except Exception as e:
            logger.warning(f"Failed to save settings: {e}")
    
    def switch_database(self):
        """Switch to a different database file."""
        self.open_database()
    
    def create_lower_section(self):
        """
        This method is kept for compatibility with PlotControlsDialog.
        The lower section has been replaced with a button to open a dialog.
        """
        lower = QWidget()
        layout = QHBoxLayout(lower)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Downsampling panel
        data_controls = self.create_data_controls_panel()
        layout.addWidget(data_controls)
        
        # Date Range panel
        date_range = self.create_date_range_panel()
        layout.addWidget(date_range)
        
        # Combined Plot & Well Style panel
        plot_style = self.create_combined_style_panel()
        layout.addWidget(plot_style)
        
        # Labels and Legend panel
        labels = self.create_labels_panel()
        layout.addWidget(labels)
        
        # Trend Analysis panel
        trend = self.create_trend_panel()
        layout.addWidget(trend)
        
        # Export panel
        export = self.create_export_panel()
        layout.addWidget(export)
        
        return lower
    
    def create_data_controls_panel(self):
        """Create the downsampling panel."""
        panel = QGroupBox("Downsampling")  # Changed from "Data Processing"
        panel.setMinimumWidth(200)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Data type selection
        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(QLabel("Data:"))
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["Water Level", "Temperature"])
        self.data_type_combo.currentIndexChanged.connect(self.update_plot)
        data_type_layout.addWidget(self.data_type_combo)
        layout.addLayout(data_type_layout)
        
        # Downsampling
        downsample_layout = QHBoxLayout()
        downsample_layout.addWidget(QLabel("Sample:"))
        self.downsample_combo = QComboBox()
        self.downsample_combo.addItems([
            "No Downsampling", "30 Minutes", "1 Hour", "2 Hours", 
            "6 Hours", "12 Hours", "1 Day", "1 Week", "1 Month"
        ])
        # Set default to No Downsampling instead of 1 Week
        self.downsample_combo.setCurrentText("No Downsampling")
        self.downsample_combo.currentIndexChanged.connect(self.update_plot)
        downsample_layout.addWidget(self.downsample_combo)
        layout.addLayout(downsample_layout)
        
        # Aggregation method
        agg_layout = QHBoxLayout()
        agg_layout.addWidget(QLabel("Method:"))
        self.aggregate_combo = QComboBox()
        self.aggregate_combo.addItems(["Mean", "Median", "Min", "Max"])
        self.aggregate_combo.currentIndexChanged.connect(self.update_plot)
        agg_layout.addWidget(self.aggregate_combo)
        layout.addLayout(agg_layout)
        
        return panel
    
    def create_date_range_panel(self):
        """Create the date range panel."""
        panel = QGroupBox("Date Range")
        panel.setMinimumWidth(200)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Start date
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("Start:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_edit.dateChanged.connect(lambda date: self.update_date_range('start', date))
        start_date_layout.addWidget(self.start_date_edit)
        layout.addLayout(start_date_layout)
        
        # End date
        end_date_layout = QHBoxLayout()
        end_date_layout.addWidget(QLabel("End:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(lambda date: self.update_date_range('end', date))
        end_date_layout.addWidget(self.end_date_edit)
        layout.addLayout(end_date_layout)
        
        # Full range button (previously called Auto Range)
        full_range_btn = QPushButton("Full Range")
        full_range_btn.clicked.connect(self.set_auto_date_range)
        layout.addWidget(full_range_btn)
        
        return panel
    
    def create_combined_style_panel(self):
        """Create the enhanced plot and well style panel with separate manual and transducer controls."""
        panel = QGroupBox("Plot & Well Styling")
        panel.setMinimumWidth(400)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Well selection at the top
        well_selection_layout = QHBoxLayout()
        well_selection_layout.addWidget(QLabel("Well:"))
        self.custom_well_combo = QComboBox()
        self.custom_well_combo.setEnabled(False)
        self.custom_well_combo.currentTextChanged.connect(self.on_custom_well_changed)
        well_selection_layout.addWidget(self.custom_well_combo)
        layout.addLayout(well_selection_layout)
        
        # Create a tab widget for Transducer and Manual styles
        style_tabs = QTabWidget()
        style_tabs.setTabPosition(QTabWidget.North)
        style_tabs.setDocumentMode(True)
        
        # Transducer Data Tab
        transducer_tab = QWidget()
        transducer_layout = QVBoxLayout(transducer_tab)
        
        transducer_line_layout = QHBoxLayout()
        transducer_line_layout.addWidget(QLabel("Line:"))
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["Solid", "Dashed", "Dotted", "Dash-Dot", "None"])
        self.line_style_combo.setEnabled(False)
        self.line_style_combo.currentIndexChanged.connect(self.update_well_style)
        transducer_line_layout.addWidget(self.line_style_combo)
        transducer_layout.addLayout(transducer_line_layout)
        
        transducer_width_layout = QHBoxLayout()
        transducer_width_layout.addWidget(QLabel("Width:"))
        self.custom_width_spinner = QDoubleSpinBox()
        self.custom_width_spinner.setRange(0.5, 5.0)
        self.custom_width_spinner.setSingleStep(0.5)
        self.custom_width_spinner.setValue(1.5)
        self.custom_width_spinner.setEnabled(False)
        self.custom_width_spinner.valueChanged.connect(self.update_well_style)
        transducer_width_layout.addWidget(self.custom_width_spinner)
        transducer_layout.addLayout(transducer_width_layout)
        
        transducer_color_layout = QHBoxLayout()
        transducer_color_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton()
        self.color_button.setEnabled(False)
        self.color_button.clicked.connect(self.select_well_color)
        self.color_button.setMaximumWidth(80)
        self.color_button.setStyleSheet("background-color: #1f77b4;")  # Default matplotlib blue
        transducer_color_layout.addWidget(self.color_button)
        transducer_layout.addLayout(transducer_color_layout)
        
        style_tabs.addTab(transducer_tab, "Transducer")
        
        # Manual Data Tab
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        
        manual_marker_layout = QHBoxLayout()
        manual_marker_layout.addWidget(QLabel("Marker:"))
        self.manual_marker_combo = QComboBox()
        self.manual_marker_combo.addItems(["Circle", "Square", "Triangle", "Diamond", "X", "Plus"])
        self.manual_marker_combo.setEnabled(False)
        self.manual_marker_combo.currentIndexChanged.connect(self.update_manual_style)
        manual_marker_layout.addWidget(self.manual_marker_combo)
        manual_layout.addLayout(manual_marker_layout)
        
        manual_size_layout = QHBoxLayout()
        manual_size_layout.addWidget(QLabel("Size:"))
        self.manual_size_spinner = QSpinBox()
        self.manual_size_spinner.setRange(20, 200)
        self.manual_size_spinner.setSingleStep(10)
        self.manual_size_spinner.setValue(80)
        self.manual_size_spinner.setEnabled(False)
        self.manual_size_spinner.valueChanged.connect(self.update_manual_style)
        manual_size_layout.addWidget(self.manual_size_spinner)
        manual_layout.addLayout(manual_size_layout)
        
        manual_color_layout = QHBoxLayout()
        manual_color_layout.addWidget(QLabel("Color:"))
        self.manual_color_button = QPushButton()
        self.manual_color_button.setEnabled(False)
        self.manual_color_button.clicked.connect(self.select_manual_color)
        self.manual_color_button.setMaximumWidth(80)
        self.manual_color_button.setStyleSheet("background-color: #1f77b4;")  # Default matplotlib blue
        manual_color_layout.addWidget(self.manual_color_button)
        manual_layout.addLayout(manual_color_layout)
        
        style_tabs.addTab(manual_tab, "Manual")
        
        layout.addWidget(style_tabs)
        
        # Add common controls
        common_controls = QGroupBox("Common")
        common_layout = QVBoxLayout(common_controls)
        
        show_controls_layout = QHBoxLayout()
        self.show_manual_cb = QCheckBox("Show Manual")
        self.show_manual_cb.setChecked(True)
        # Fix checkbox styling to completely remove blue background
        self.show_manual_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.show_manual_cb.stateChanged.connect(self.update_plot)
        show_controls_layout.addWidget(self.show_manual_cb)
        
        self.show_grid_cb = QCheckBox("Show Grid")
        self.show_grid_cb.setChecked(True)
        # Fix checkbox styling
        self.show_grid_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.show_grid_cb.stateChanged.connect(self.toggle_grid)
        show_controls_layout.addWidget(self.show_grid_cb)
        
        # Add water year highlighting checkbox
        self.highlight_water_year_cb = QCheckBox("Highlight Water Years")
        self.highlight_water_year_cb.setChecked(False)
        # Same styling as other checkboxes
        self.highlight_water_year_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.highlight_water_year_cb.setToolTip("Show water years with alternating background colors. Water years start on October 1st.")
        self.highlight_water_year_cb.stateChanged.connect(self.toggle_water_year_highlight)
        show_controls_layout.addWidget(self.highlight_water_year_cb)
        
        # Add data gaps highlighting checkbox
        self.highlight_gaps_cb = QCheckBox("Highlight Gaps")
        self.highlight_gaps_cb.setChecked(False)
        # Same styling as other checkboxes
        self.highlight_gaps_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.highlight_gaps_cb.setToolTip("Highlight gaps in data sampling larger than 15 minutes with a semi-transparent color matching the well line.")
        self.highlight_gaps_cb.stateChanged.connect(self.toggle_gaps_highlight)
        show_controls_layout.addWidget(self.highlight_gaps_cb)
        
        common_layout.addLayout(show_controls_layout)
        
        layout.addWidget(common_controls)
        
        return panel
    
    def create_labels_panel(self):
        """Create the labels and legend panel with tab interface."""
        panel = QGroupBox("Labels & Legend")
        panel.setMinimumWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Create tab widget for title and axes labels
        labels_tabs = QTabWidget()
        labels_tabs.setTabPosition(QTabWidget.North)
        labels_tabs.setDocumentMode(True)
        
        # Title Tab
        title_tab = QWidget()
        title_layout = QVBoxLayout(title_tab)
        title_layout.setContentsMargins(5, 5, 5, 5)
        title_layout.setSpacing(4)
        
        # Plot title
        title_layout.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter plot title")
        self.title_input.textChanged.connect(self.update_plot_title)
        title_layout.addWidget(self.title_input)
        
        # Title font size
        title_font_layout = QHBoxLayout()
        title_font_layout.addWidget(QLabel("Size:"))
        self.title_font_size = QSpinBox()
        self.title_font_size.setRange(8, 24)
        self.title_font_size.setValue(14)
        self.title_font_size.valueChanged.connect(self.update_plot_title)
        title_font_layout.addWidget(self.title_font_size)
        title_layout.addLayout(title_font_layout)
        
        # Title bold checkbox
        self.title_bold_cb = QCheckBox("Bold")
        self.title_bold_cb.setChecked(True)
        # Fix checkbox styling to completely remove blue background
        self.title_bold_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.title_bold_cb.stateChanged.connect(self.update_plot_title)
        title_layout.addWidget(self.title_bold_cb)
        
        # Add stretch to push everything to the top
        title_layout.addStretch()
        
        # Axes Tab
        axes_tab = QWidget()
        axes_layout = QVBoxLayout(axes_tab)
        axes_layout.setContentsMargins(5, 5, 5, 5)
        axes_layout.setSpacing(4)
        
        # X-axis label
        axes_layout.addWidget(QLabel("X-axis:"))
        self.x_axis_input = QLineEdit()
        self.x_axis_input.setPlaceholderText("X-axis label (default: Date)")
        self.x_axis_input.textChanged.connect(self.update_axis_labels)
        axes_layout.addWidget(self.x_axis_input)
        
        # Y-axis label
        axes_layout.addWidget(QLabel("Y-axis:"))
        self.y_axis_input = QLineEdit()
        self.y_axis_input.setPlaceholderText("Y-axis label (default: Water Level)")
        self.y_axis_input.textChanged.connect(self.update_axis_labels)
        axes_layout.addWidget(self.y_axis_input)
        
        # Axis font size
        axis_font_layout = QHBoxLayout()
        axis_font_layout.addWidget(QLabel("Size:"))
        self.axis_font_size = QSpinBox()
        self.axis_font_size.setRange(8, 18)
        self.axis_font_size.setValue(10)
        self.axis_font_size.valueChanged.connect(self.update_axis_font)
        axis_font_layout.addWidget(self.axis_font_size)
        axes_layout.addLayout(axis_font_layout)
        
        # Axis bold checkboxes
        self.x_axis_bold_cb = QCheckBox("Bold X-axis")
        # Fix checkbox styling to completely remove blue background
        self.x_axis_bold_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.x_axis_bold_cb.stateChanged.connect(self.update_axis_labels)
        axes_layout.addWidget(self.x_axis_bold_cb)
        
        self.y_axis_bold_cb = QCheckBox("Bold Y-axis")
        # Fix checkbox styling to completely remove blue background
        self.y_axis_bold_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.y_axis_bold_cb.stateChanged.connect(self.update_axis_labels)
        axes_layout.addWidget(self.y_axis_bold_cb)
        
        # Add stretch to push everything to the top
        axes_layout.addStretch()
        
        # Legend Tab
        legend_tab = QWidget()
        legend_layout = QVBoxLayout(legend_tab)
        legend_layout.setContentsMargins(5, 5, 5, 5)
        legend_layout.setSpacing(4)
        
        # Legend position
        legend_layout.addWidget(QLabel("Position:"))
        self.legend_position = QComboBox()
        self.legend_position.addItems(["Best", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Center Left", "Center Right", "Lower Center", "Upper Center", "Center"])
        self.legend_position.setCurrentText("Best")
        self.legend_position.currentIndexChanged.connect(self.update_legend_position)
        legend_layout.addWidget(self.legend_position)
        
        # Legend options
        self.draggable_legend = QCheckBox("Draggable Legend")
        self.draggable_legend.setChecked(True)
        # Fix checkbox styling to completely remove blue background
        self.draggable_legend.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.draggable_legend.stateChanged.connect(self.update_legend_draggable)
        legend_layout.addWidget(self.draggable_legend)
        
        # Legend font size control
        legend_font_layout = QHBoxLayout()
        legend_font_layout.addWidget(QLabel("Size:"))
        self.legend_font_size = QSpinBox()
        self.legend_font_size.setRange(8, 16)
        self.legend_font_size.setValue(10)
        self.legend_font_size.valueChanged.connect(self.update_legend_font)
        legend_font_layout.addWidget(self.legend_font_size)
        legend_layout.addLayout(legend_font_layout)
        
        # Add stretch to push everything to the top
        legend_layout.addStretch()
        
        # Add tabs to the tab widget
        labels_tabs.addTab(title_tab, "Title")
        labels_tabs.addTab(axes_tab, "Axes")
        labels_tabs.addTab(legend_tab, "Legend")
        
        # Add the tab widget to the main layout
        layout.addWidget(labels_tabs)
        
        return panel

    def create_trend_panel(self):
        """Create the trend analysis panel."""
        panel = QGroupBox("Analysis")
        panel.setMinimumWidth(200)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Show trend line
        self.show_trend_cb = QCheckBox("Show Trend Line")
        self.show_trend_cb.setChecked(False)
        # Fix checkbox styling to completely remove blue background (match styling of other checkboxes)
        self.show_trend_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        self.show_trend_cb.stateChanged.connect(self.on_trend_checkbox_changed)
        layout.addWidget(self.show_trend_cb)
        
        # Trend type
        trend_type_layout = QHBoxLayout()
        trend_type_layout.addWidget(QLabel("Type:"))
        self.trend_type_combo = QComboBox()
        self.trend_type_combo.addItems(["Linear", "Polynomial", "Moving Avg"])
        self.trend_type_combo.setEnabled(False)
        self.trend_type_combo.currentIndexChanged.connect(self.on_trend_setting_changed)
        trend_type_layout.addWidget(self.trend_type_combo)
        layout.addLayout(trend_type_layout)
        
        # Trend period / degree
        trend_degree_layout = QHBoxLayout()
        trend_degree_layout.addWidget(QLabel("Degree:"))
        self.trend_degree_spinner = QSpinBox()
        self.trend_degree_spinner.setRange(1, 5)
        self.trend_degree_spinner.setValue(1)
        self.trend_degree_spinner.setEnabled(False)
        self.trend_degree_spinner.valueChanged.connect(self.on_trend_setting_changed)
        trend_degree_layout.addWidget(self.trend_degree_spinner)
        layout.addLayout(trend_degree_layout)
        
        # Trend line style
        trend_style_layout = QHBoxLayout()
        trend_style_layout.addWidget(QLabel("Style:"))
        self.trend_style_combo = QComboBox()
        self.trend_style_combo.addItems(["Solid", "Dashed", "Dotted", "Dash-Dot"])
        self.trend_style_combo.setCurrentText("Dashed")
        self.trend_style_combo.setEnabled(False)
        self.trend_style_combo.currentIndexChanged.connect(self.on_trend_setting_changed)
        trend_style_layout.addWidget(self.trend_style_combo)
        layout.addLayout(trend_style_layout)
        
        # Trend line width
        trend_width_layout = QHBoxLayout()
        trend_width_layout.addWidget(QLabel("Width:"))
        self.trend_width_spinner = QDoubleSpinBox()
        self.trend_width_spinner.setRange(0.5, 5.0)
        self.trend_width_spinner.setSingleStep(0.5)
        self.trend_width_spinner.setValue(1.5)
        self.trend_width_spinner.setEnabled(False)
        self.trend_width_spinner.valueChanged.connect(self.on_trend_setting_changed)
        trend_width_layout.addWidget(self.trend_width_spinner)
        layout.addLayout(trend_width_layout)
        
        # Trend line color
        trend_color_layout = QHBoxLayout()
        trend_color_layout.addWidget(QLabel("Color:"))
        self.trend_color_button = QPushButton()
        self.trend_color_button.setEnabled(False)
        self.trend_color_button.setMaximumWidth(80)
        self.trend_color_button.setStyleSheet("background-color: #ff7f0e;")  # Default orange
        self.trend_color_button.clicked.connect(self.select_trend_color)
        trend_color_layout.addWidget(self.trend_color_button)
        layout.addLayout(trend_color_layout)
        
        # Connect trend checkbox to enable/disable other controls
        self.show_trend_cb.stateChanged.connect(self.toggle_trend_controls)
        
        return panel

    def create_export_panel(self):
        """Create the export panel."""
        panel = QGroupBox("Export")
        panel.setMinimumWidth(180)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Export plot
        export_plot_btn = QPushButton("Export Plot (PNG)")
        export_plot_btn.clicked.connect(self.export_plot)
        layout.addWidget(export_plot_btn)
        
        # Export data
        export_data_btn = QPushButton("Export Data (CSV)")
        export_data_btn.clicked.connect(self.export_data)
        layout.addWidget(export_data_btn)
        
        # Add checkbox for applying downsampling to exports
        self.export_downsample_cb = QCheckBox("Apply Downsampling")
        self.export_downsample_cb.setChecked(False)
        self.export_downsample_cb.setToolTip("If checked, exported data will use the same downsampling settings as the plot")
        self.export_downsample_cb.setStyleSheet("""
            QCheckBox { color: palette(text); }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid gray; background: white; }
            QCheckBox::indicator:checked { image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); background: white; }
        """)
        layout.addWidget(self.export_downsample_cb)
        
        return panel

    # Methods for handling well selection
    
    def load_wells(self):
        """Load wells from the database and populate the table with optimized performance."""
        print("[MAIN_PLOT_DEBUG] load_wells() called!")  # Use print to ensure it shows
        
        # Check if we have a data manager
        if not self.data_manager:
            logger.info("No data manager available - cannot load wells")
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("No database loaded. Use 'Switch DB' to load a database file.")
            
            # Clear the table
            self.well_table.setRowCount(0)
            return
        
        print("[MAIN_PLOT_DEBUG] About to import time")
        import time
        print("[MAIN_PLOT_DEBUG] About to get start time")
        start_time = time.time()
        print("[MAIN_PLOT_DEBUG] About to enter try block")
        
        try:
            logger.info("[MAIN_PLOT_DEBUG] Starting well loading...")
            logger.info(f"[MAIN_PLOT_DEBUG] Data manager type: {type(self.data_manager)}")
            logger.info(f"Loading wells from database: {self.db_path}")
            # Show loading message in status bar
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("Loading wells from database...")
            
            # Clear the table but maintain selection if possible
            currently_selected = []
            for item in self.well_table.selectedItems():
                if item.column() == 0:  # Well number column
                    currently_selected.append(item.text())
            
            self.well_table.clear()
            self.well_table.setColumnCount(4)  # Changed from 3 to 4 columns to include readings
            self.well_table.setHorizontalHeaderLabels(["Well Number", "CAE Number", "Aquifer", "Readings"])
            
            # Get wells with data available - use optimized data loading
            wells_data = self.data_manager.get_wells_with_data()
            logger.info(f"[MAIN_PLOT_DEBUG] Got {len(wells_data)} wells from data manager")
            
            processing_time = time.time() - start_time
            logger.info(f"Retrieved well data in {processing_time*1000:.1f}ms")
            
            if not wells_data:
                self.status_bar.showMessage("No wells found with water level data.")
                return
                
            # Set table rows
            self.well_table.setRowCount(len(wells_data))
            
            # Get unique aquifers for filter
            aquifers = set()
            
            # Fill table using batch operation for better performance
            aquifer_items = []
            self.well_table.setSortingEnabled(False)  # Disable sorting while filling
            
            for row, (well_number, cae_number, water_body) in enumerate(wells_data):
                logger.debug(f"Adding well to table: {well_number}, {cae_number}, {water_body}")
                
                # Well number
                item = QTableWidgetItem(well_number)
                self.well_table.setItem(row, 0, item)
                
                # CAE number
                cae_item = QTableWidgetItem(cae_number if cae_number else "")
                self.well_table.setItem(row, 1, cae_item)
                
                # Aquifer (renamed from water_body)
                aquifer_item = QTableWidgetItem(water_body if water_body else "")
                self.well_table.setItem(row, 2, aquifer_item)
                
                # Initialize reading count as "Loading..." - will be updated asynchronously
                readings_item = QTableWidgetItem("...")
                readings_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.well_table.setItem(row, 3, readings_item)
                
                # Track aquifers for filter
                if water_body:
                    aquifers.add(water_body)
                    if water_body not in aquifer_items:
                        aquifer_items.append(water_body)
            
            # Restore selection if applicable
            if currently_selected:
                for row in range(self.well_table.rowCount()):
                    well_item = self.well_table.item(row, 0)
                    if well_item and well_item.text() in currently_selected:
                        self.well_table.selectRow(row)
            
            # Update the aquifer filter combo box
            self.filter_input.clear()
            self.filter_input.addItem("All Aquifers")
            
            # Sort aquifer items alphabetically
            aquifer_items.sort()
            self.filter_input.addItems(aquifer_items)
            
            # Resize columns after all data is loaded
            self.well_table.setSortingEnabled(True)  # Re-enable sorting
            self.well_table.resizeColumnsToContents()
            
            # Log completion time
            total_time = time.time() - start_time
            logger.info(f"Well table populated with {len(wells_data)} wells in {total_time*1000:.1f}ms")
            
            # Reconnect selection signal to make sure it works
            logger.info("[MAIN_PLOT_DEBUG] Reconnecting well table selection signal")
            if self.well_table.selectionModel():
                try:
                    self.well_table.selectionModel().selectionChanged.disconnect()
                except:
                    pass
                self.well_table.selectionModel().selectionChanged.connect(self.on_well_selection_changed)
                logger.info("[MAIN_PLOT_DEBUG] Selection signal reconnected successfully")
            else:
                logger.error("[MAIN_PLOT_DEBUG] No selection model found!")
            
            # Update status bar with completion message
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Loaded {len(wells_data)} wells successfully")
            
            # Start loading reading counts in background
            self.load_reading_counts_async(wells_data)
            
        except Exception as e:
            print(f"[MAIN_PLOT_DEBUG] Exception in load_wells: {e}")
            logger.error(f"Error loading wells: {e}", exc_info=True)
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Error loading wells: {str(e)}")
            
            # Show error in table
            self.well_table.setRowCount(1)
            self.well_table.setItem(0, 0, QTableWidgetItem("Error loading wells"))
            self.well_table.setItem(0, 1, QTableWidgetItem(str(e)))
    
    def load_reading_counts_async(self, wells_data):
        """Load reading counts for wells in background to avoid blocking UI."""
        import threading
        
        def load_counts():
            """Background thread function to load reading counts."""
            try:
                logger.info("Loading reading counts in background...")
                logger.info(f"Data manager type: {type(self.data_manager).__name__}")
                logger.info(f"Database path in thread: {self.db_path}")
                logger.info(f"Number of wells to load counts for: {len(wells_data)}")
                
                for row, (well_number, _, _) in enumerate(wells_data):
                    try:
                        count = self.data_manager.get_reading_count(well_number)
                        logger.info(f"Well {well_number} (row {row}) has {count} readings")
                        # Use signal to update UI from background thread (thread-safe)
                        self.reading_count_update.emit(row, count)
                    except Exception as e:
                        logger.error(f"Error getting count for {well_number}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        self.reading_count_update.emit(row, 0)
                
                logger.info(f"Finished loading reading counts for {len(wells_data)} wells")
            except Exception as e:
                logger.error(f"Error in background reading count loading: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Start background thread
        thread = threading.Thread(target=load_counts, daemon=True)
        thread.start()
    
    def update_reading_count(self, row, count):
        """Update reading count for a specific row (called from main thread)."""
        try:
            if row < self.well_table.rowCount():
                item = self.well_table.item(row, 3)
                if item:
                    item.setText(str(count))
                    logger.debug(f"Updated row {row} with count {count}")
                else:
                    logger.warning(f"No item found at row {row}, column 3")
            else:
                logger.warning(f"Row {row} is out of range (table has {self.well_table.rowCount()} rows)")
        except Exception as e:
            logger.error(f"Error updating reading count for row {row}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def filter_wells(self, text):
        """Filter wells in the table based on the selected aquifer."""
        if not text or text == "All Aquifers":
            # Show all wells
            for row in range(self.well_table.rowCount()):
                self.well_table.setRowHidden(row, False)
            self.status_bar.showMessage(f"Showing all wells ({self.well_table.rowCount()})")
            return
        
        filter_text = text.lower()
        matching_rows = 0
        
        for row in range(self.well_table.rowCount()):
            aquifer = self.well_table.item(row, 2).text().lower()
            
            # Show row if aquifer matches filter
            should_show = (filter_text in aquifer)
            self.well_table.setRowHidden(row, not should_show)
            
            if should_show:
                matching_rows += 1
        
        self.status_bar.showMessage(f"Filtered: showing {matching_rows} wells matching '{text}'")
        logger.debug(f"Applied filter '{text}', showing {matching_rows} wells")
    
    def on_well_selection_changed(self):
        """Handle well selection changes."""
        print("[MAIN_PLOT_DEBUG] on_well_selection_changed called")
        try:
            selected_rows = self.well_table.selectionModel().selectedRows()
            print(f"[MAIN_PLOT_DEBUG] Selected rows: {len(selected_rows)}")
            self.selected_wells = []
        
            for idx in selected_rows:
                well_number = self.well_table.item(idx.row(), 0).text()
                self.selected_wells.append(well_number)
                print(f"[MAIN_PLOT_DEBUG] Added well: {well_number}")
        except Exception as e:
            print(f"[MAIN_PLOT_DEBUG] Exception in on_well_selection_changed: {e}")
            return
        
        # Show immediate feedback that we're loading
        if self.selected_wells:
            print(f"[MAIN_PLOT_DEBUG] Selected wells: {self.selected_wells}")
            self.status_bar.showMessage(f"Loading data for {len(self.selected_wells)} selected wells...")
            
            # Don't clear plot here - let update_plot() handle it
            
            # Update plot controls dialog if it exists
            if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                # Update the custom well combo box with selected wells
                self.plot_controls_dialog.custom_well_combo.blockSignals(True)
                self.plot_controls_dialog.custom_well_combo.clear()
                self.plot_controls_dialog.custom_well_combo.addItems(self.selected_wells)
                self.plot_controls_dialog.custom_well_combo.setEnabled(True)
                
                # Enable styling controls
                self.plot_controls_dialog.color_button.setEnabled(True)
                self.plot_controls_dialog.line_style_combo.setEnabled(True)
                
                # Update date range for single well selection
                if len(self.selected_wells) == 1:
                    self.plot_controls_dialog.update_date_range_for_well(self.selected_wells[0])
                self.plot_controls_dialog.custom_width_spinner.setEnabled(True)
                self.plot_controls_dialog.manual_marker_combo.setEnabled(True)
                self.plot_controls_dialog.manual_size_spinner.setEnabled(True)
                self.plot_controls_dialog.manual_color_button.setEnabled(True)
                
                # Select the first well in the dropdown
                self.plot_controls_dialog.custom_well_combo.setCurrentIndex(0)
                self.plot_controls_dialog.custom_well_combo.blockSignals(False)
            
            # Make sure we have property entries for all wells
            # This ensures that when on_custom_well_changed is triggered, the properties exist
            for well in self.selected_wells:
                if not hasattr(self.plot_handler, 'well_properties') or well not in self.plot_handler.well_properties:
                    # Initialize the properties with default values
                    self.plot_handler.initialize_well_properties(well)
                    
                    # If we have legacy properties for this well, migrate them
                    if well in self.well_colors:
                        self.plot_handler.well_properties[well]['line']['color'] = self.well_colors[well]
                        self.plot_handler.well_properties[well]['manual']['color'] = self.well_colors[well]
                    
                    if well in self.well_line_widths:
                        self.plot_handler.well_properties[well]['line']['line_width'] = self.well_line_widths[well]
                    
                    if well in self.well_line_styles:
                        self.plot_handler.well_properties[well]['line']['line_style'] = self.well_line_styles[well]
            
            # Trigger well changed handler in plot controls dialog if it exists
            if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                current_well = self.plot_controls_dialog.custom_well_combo.currentText()
                if current_well:
                    self.plot_controls_dialog.on_custom_well_changed(current_well)
            
            # Load data for each selected well - call update_plot directly
            print("[MAIN_PLOT_DEBUG] Calling update_plot() directly")
            self.update_plot()
            
            # Recharge tab moved to main app
        else:
            # No wells selected, update the plot controls dialog if it exists
            if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                self.plot_controls_dialog.custom_well_combo.blockSignals(True)
                self.plot_controls_dialog.custom_well_combo.clear()
                self.plot_controls_dialog.custom_well_combo.setEnabled(False)
                
                # Disable styling controls
                self.plot_controls_dialog.color_button.setEnabled(False)
                self.plot_controls_dialog.line_style_combo.setEnabled(False)
                self.plot_controls_dialog.custom_width_spinner.setEnabled(False)
                self.plot_controls_dialog.manual_marker_combo.setEnabled(False)
                self.plot_controls_dialog.manual_size_spinner.setEnabled(False)
                self.plot_controls_dialog.manual_color_button.setEnabled(False)
                self.plot_controls_dialog.custom_well_combo.blockSignals(False)
            
            # Clear the plot
            self.plot_handler.clear_plot()
            self.plot_handler.canvas.draw()
            
            # Also clear recharge tab selection
            if hasattr(self, 'recharge_tab'):
                self.recharge_tab.update_well_selection([])
            
            self.status_bar.showMessage("No wells selected")
        
        # Update map to reflect current selection (if on map tab)
        if self.tab_widget.currentIndex() == 1:  # Map View tab
            QTimer.singleShot(100, self.update_map_display)
    
    def on_tab_changed(self, index):
        """Handle tab change events"""
        # Update map when switching to map tab
        if index == 1:  # Map View tab
            self.update_map_display()
        # Recharge tab moved to main app
    
    def update_map_display(self):
        """Update the map with well locations and selected wells using improved map handler."""
        try:
            # Use the improved map handler to update the map
            self.map_handler.update_map(self.selected_wells)
            self.status_bar.showMessage(f"Map updated with {len(self.selected_wells)} selected wells.")
            
        except Exception as e:
            logger.error(f"Error updating map display: {e}")
            self.status_bar.showMessage(f"Error updating map: {str(e)}")
    
    def update_map(self):
        """Legacy method - redirects to new implementation."""
        self.update_map_display()
    
    def on_map_well_selected(self, well_number):
        """Handle well selection from the map."""
        try:
            logger.debug(f"Well selected from map: {well_number}")
            
            # Find and select the well in the well table
            for row in range(self.well_table.rowCount()):
                item = self.well_table.item(row, 0)
                if item and item.text() == well_number:
                    # Clear current selection
                    self.well_table.clearSelection()
                    # Select the row
                    self.well_table.selectRow(row)
                    # Ensure it's visible
                    self.well_table.scrollToItem(item)
                    # Switch to the Plot View tab to show the selected data
                    self.tab_widget.setCurrentIndex(0)
                    self.status_bar.showMessage(f"Selected well {well_number} from map")
                    break
            else:
                logger.warning(f"Well {well_number} not found in well table")
                self.status_bar.showMessage(f"Well {well_number} not found in table")
                
        except Exception as e:
            logger.error(f"Error handling map well selection: {e}")
            self.status_bar.showMessage(f"Error selecting well: {str(e)}")
    
    def update_date_range(self, which, qdate):
        """Update the date range based on user selection."""
        date_str = qdate.toString("yyyy-MM-dd")
        
        if which == 'start':
            self.date_range['start'] = date_str
            # Ensure end date is not before start date
            end_date = self.end_date_edit.date()
            if end_date < qdate:
                self.end_date_edit.setDate(qdate)
        else:  # end
            self.date_range['end'] = date_str
            # Ensure start date is not after end date
            start_date = self.start_date_edit.date()
            if start_date > qdate:
                self.start_date_edit.setDate(qdate)
        
        # Update plot with new date range
        logger.info("[MAIN_PLOT_DEBUG] About to call update_plot() from well selection")
        self.update_plot()
    
    def set_auto_date_range(self):
        """Set the date range to cover all available data."""
        self.status_bar.showMessage("Setting date range to cover all available data...")
        
        # Reset date range to None which will use full data range
        self.date_range = {'start': None, 'end': None}
        
        # If wells are selected, use their data to determine date range
        if self.selected_wells:
            min_date = None
            max_date = None
            
            for well in self.selected_wells:
                try:
                    # Get data for this well
                    df = self.plot_handler.get_well_data(well, self.db_path)
                    
                    if not df.empty:
                        # For consistency with the plot handler, use timestamp_utc column or index
                        date_column = df.index if df.index.name == 'timestamp_utc' else df['timestamp_utc']
                        
                        well_min = date_column.min()
                        well_max = date_column.max()
                        
                        if min_date is None or well_min < min_date:
                            min_date = well_min
                        
                        if max_date is None or well_max > max_date:
                            max_date = well_max
                except Exception as e:
                    logger.error(f"Error getting date range for well {well}: {e}")
            
            # Update date controls if we found valid dates
            if min_date is not None and max_date is not None:
                min_qdate = QDate.fromString(min_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
                max_qdate = QDate.fromString(max_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
                
                self.start_date_edit.setDate(min_qdate)
                self.end_date_edit.setDate(max_qdate)
                
                self.date_range['start'] = min_date.strftime("%Y-%m-%d")
                self.date_range['end'] = max_date.strftime("%Y-%m-%d")
                
                self.status_bar.showMessage(f"Date range set from {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
            else:
                # If no valid data found, use default range
                default_range()
        else:
            # No wells selected, use default range
            default_range()
        
        # Update plot
        self.update_plot()
        
        def default_range():
            """Set default date range of last 3 months to today"""
            today = QDate.currentDate()
            three_months_ago = today.addMonths(-3)
            
            self.start_date_edit.setDate(three_months_ago)
            self.end_date_edit.setDate(today)
            
            self.date_range['start'] = three_months_ago.toString("yyyy-MM-dd")
            self.date_range['end'] = today.toString("yyyy-MM-dd")
            
            self.status_bar.showMessage("Set default date range (last 3 months)")
    
    def update_plot(self):
        """Update the plot with selected wells and settings."""
        logger.info("[MAIN_PLOT_DEBUG] update_plot() called")
        try:
            if not self.selected_wells:
                logger.info("[MAIN_PLOT_DEBUG] No wells selected, clearing plot")
                self.status_bar.showMessage("No wells selected for plotting.")
                self.plot_handler.clear_plot()
                return
            
            # Get settings from plot_controls_dialog if available, otherwise use defaults
            if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                data_type = self.plot_controls_dialog.data_type_combo.currentText().lower().replace(" ", "_")
                downsample = self.plot_controls_dialog.downsample_combo.currentText()
                # Check plot controls dialog first, fallback to main dialog
                if hasattr(self.plot_controls_dialog, 'show_manual_cb'):
                    show_manual = self.plot_controls_dialog.show_manual_cb.isChecked()
                else:
                    show_manual = hasattr(self, 'show_manual_cb') and self.show_manual_cb.isChecked()
            else:
                # Default values if dialog not available
                data_type = "water_level"
                downsample = "No Downsampling"
                show_manual = False
            
            # Track if we need to load data for any wells
            need_data_load = False
            
            # Show progress dialog for plot update if many wells are selected
            if len(self.selected_wells) > 3:
                progress = QProgressDialog("Updating plot...", "Cancel", 0, len(self.selected_wells), self)
                progress.setWindowModality(Qt.WindowModal)
                progress.setValue(0)
                progress.show()
            else:
                progress = None
            
            # Loop through selected wells to get their data
            for i, well in enumerate(self.selected_wells):
                # Update progress
                if progress:
                    progress.setValue(i)
                    if progress.wasCanceled():
                        break
                
                # Check if we already have data for this well
                if well not in self.plot_handler.well_data or not hasattr(self.plot_handler, 'well_data_full') or well not in self.plot_handler.well_data_full:
                    need_data_load = True
                    
                    # Get data for this well using the same FastDataManager that works in RISE tab
                    df = self.data_manager.get_well_data(well, 
                        start_date=self.date_range.get('start') if self.date_range else None,
                        end_date=self.date_range.get('end') if self.date_range else None,
                        downsample='1D')
                    
                    # Set data in plot handler
                    if not df.empty:
                        self.plot_handler.set_well_data(well, df)
                
                # Apply well styling if available but don't fully update the plot
                if well in self.well_colors and well not in self.plot_handler.well_properties.get(well, {}):
                    style = {
                        'color': self.well_colors[well],
                        'line_width': self.well_line_widths.get(well, 1.5),
                        'line_style': self.well_line_styles.get(well, '-')
                    }
                    # Just store the style but don't update the plot yet
                    self.plot_handler.well_styles[well] = style
                    
                    # Also store in well_properties
                    if well not in self.plot_handler.well_properties:
                        self.plot_handler.well_properties[well] = {
                            'line': style,
                            'manual': {'color': style['color'], 'marker': 'o', 'marker_size': 80},
                            'trend': {'color': '#ff7f0e', 'line_width': 1.5, 'line_style': '--'}
                        }
                    else:
                        self.plot_handler.well_properties[well]['line'].update(style)
            
            # Close progress dialog
            if progress:
                progress.setValue(len(self.selected_wells))
            
            # If this is a single well, check if we can get its CAE number for the title
            if len(self.selected_wells) == 1:
                well_info = self.plot_handler.get_well_info(self.selected_wells[0], self.db_path)
                if well_info:
                    cae_number = well_info.get('cae_number') or well_info.get('caesar_number', '')
                    if cae_number:
                        auto_title = f"{self.selected_wells[0]} ({cae_number})"
                    else:
                        auto_title = self.selected_wells[0]
                    
                    # Get title input from the appropriate place
                    title_input = None
                    if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                        if hasattr(self.plot_controls_dialog, 'title_input'):
                            title_input = self.plot_controls_dialog.title_input
                    elif hasattr(self, 'title_input'):
                        title_input = self.title_input
                    
                    # Only update title input if it exists and is empty or matches a previous auto-generated title
                    if title_input and (not title_input.currentText() or title_input.currentText().startswith(self.selected_wells[0])):
                        title_input.blockSignals(True)
                        title_input.setCurrentText(auto_title)
                        title_input.blockSignals(False)
                        
                        # Get font size from appropriate place
                        title_font_size = 12  # Default
                        if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                            if hasattr(self.plot_controls_dialog, 'font_size_spinner'):
                                title_font_size = self.plot_controls_dialog.font_size_spinner.value()
                        elif hasattr(self, 'title_font_size'):
                            title_font_size = self.title_font_size.value()
                            
                        self.plot_handler.set_title(auto_title, title_font_size)
            
            # Only do a full plot update if we needed to load data or if date range/settings changed
            # Always update when this method is first called
            plot_settings_key = f"{self.selected_wells}|{self.date_range}|{show_manual}|{data_type}|{downsample}"
            logger.info(f"[MAIN_PLOT_DEBUG] Plot settings key: {plot_settings_key}")
            # Clear cache when well changes to fix the reloading issue
            if not hasattr(self, '_last_plot_settings') or self.selected_wells != getattr(self, '_last_selected_wells', []):
                self._last_plot_settings = None  # Clear cache when wells change
                self._last_selected_wells = self.selected_wells.copy()
            
            if need_data_load or not hasattr(self, '_last_plot_settings') or self._last_plot_settings != plot_settings_key:
                logger.info("[MAIN_PLOT_DEBUG] Calling plot_handler.update_plot()")
                # Update the plot
                self.plot_handler.update_plot(
                    self.selected_wells, 
                    self.date_range, 
                    show_manual=show_manual,
                    data_type=data_type,
                    db_path=self.db_path,
                    downsample_method=downsample
                )
                
                # Store settings to avoid redundant updates
                self._last_plot_settings = plot_settings_key
                
                self.status_bar.showMessage(f"Plot updated with {len(self.selected_wells)} wells.")
                
                # Apply trend analysis if trend checkbox is checked
                trend_checked = False
                if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                    if hasattr(self.plot_controls_dialog, 'show_trend_cb'):
                        trend_checked = self.plot_controls_dialog.show_trend_cb.isChecked()
                elif hasattr(self, 'show_trend_cb'):
                    trend_checked = self.show_trend_cb.isChecked()
                    
                if trend_checked:
                    self.apply_trend_analysis()
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            self.status_bar.showMessage(f"Error updating plot: {str(e)}")
    
    def on_point_clicked(self, point_data):
        """Handle click events on plot points."""
        if point_data:
            message = (f"Well: {point_data['well']}, "
                      f"Date: {point_data['date'].strftime('%Y-%m-%d %H:%M')}, "
                      f"Value: {point_data['value']:.2f}")
            
            if point_data['temperature'] is not None:
                message += f", Temp: {point_data['temperature']:.2f}°C"
                
            self.status_bar.showMessage(message)
    
    def on_plot_updated(self):
        """Handle plot updated event."""
        self.status_bar.showMessage("Plot updated successfully.")
    
    def on_error(self, error_msg):
        """Handle error event."""
        self.status_bar.showMessage(f"Error: {error_msg}")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Refresh data
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.load_wells)
        
        # Toggle fullscreen
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        
        # Close dialog
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.accept)
    
    def on_custom_well_changed(self, well_name):
        """Handle custom well selection in the main visualizer.
        This is called by UI elements directly in this class, not as a callback from plot_controls_dialog."""
        if not well_name:
            return
            
        logger.debug(f"Main visualizer: on_custom_well_changed called with {well_name}")
        
        # Update plot handler with well data
        # (This is needed for when this method is called directly from UI elements in this class)
        if hasattr(self, 'plot_handler') and self.plot_handler:
            # This will initialize properties if not already set
            self.plot_handler.initialize_well_properties(well_name)
            
        # If the plot controls dialog exists, update its UI directly
        # We no longer call its on_custom_well_changed method to avoid recursion
        if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
            # Instead of calling its method (which would call back to us), we just need to 
            # ensure the combo box has the right value selected
            if self.plot_controls_dialog.custom_well_combo.currentText() != well_name:
                # Find the index of the well name in the combo box
                index = self.plot_controls_dialog.custom_well_combo.findText(well_name)
                if index >= 0:
                    # Set the selection without triggering the change event
                    self.plot_controls_dialog.custom_well_combo.blockSignals(True)
                    self.plot_controls_dialog.custom_well_combo.setCurrentIndex(index)
                    self.plot_controls_dialog.custom_well_combo.blockSignals(False)
                    
                    # Now manually update the controls
                    self.plot_controls_dialog.on_custom_well_changed(well_name)
    
    def update_well_style(self):
        """Proxy method to update well style in the plot_controls_dialog if it exists."""
        # If the plot controls dialog exists, delegate to it
        if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
            self.plot_controls_dialog.update_well_style()
        else:
            logger.warning("Cannot update well style - plot controls dialog not created yet")
    
    def update_manual_style(self):
        """Proxy method to update manual style in the plot_controls_dialog if it exists."""
        # If the plot controls dialog exists, delegate to it
        if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
            self.plot_controls_dialog.update_manual_style()
        else:
            logger.warning("Cannot update manual style - plot controls dialog not created yet")
    
    def select_well_color(self):
        """Proxy method to select well color in the plot_controls_dialog if it exists."""
        # If the plot controls dialog exists, delegate to it
        if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
            self.plot_controls_dialog.select_well_color()
        else:
            logger.warning("Cannot select well color - plot controls dialog not created yet")
    
    def select_manual_color(self):
        """Proxy method to select manual color in the plot_controls_dialog if it exists."""
        # If the plot controls dialog exists, delegate to it
        if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
            self.plot_controls_dialog.select_manual_color()
        else:
            logger.warning("Cannot select manual color - plot controls dialog not created yet")
    
    # Methods for handling plot title, axis fonts and legend position    
    def update_plot_title(self):
        """Update the plot title and font size."""
        title_text = self.title_input.text()
        font_size = self.title_font_size.value()
        
        # Set the title on the plot
        self.plot_handler.set_title(title_text, font_size)
        
        # Apply bold if checkbox is checked
        self.plot_handler.set_title_weight(self.title_bold_cb.isChecked())
    
    def update_axis_font(self):
        """Update the axis font size."""
        font_size = self.axis_font_size.value()
        
        # Set the axis font size on the plot
        self.plot_handler.set_axis_font_size(font_size)
    
    def update_axis_labels(self):
        """Update the axis labels and their styling."""
        x_label = self.x_axis_input.text()
        y_label = self.y_axis_input.text()
        
        # Set the axis labels on the plot
        self.plot_handler.set_axis_labels(x_label, y_label)
        
        # Apply bold formatting if checkboxes are checked
        x_bold = self.x_axis_bold_cb.isChecked()
        y_bold = self.y_axis_bold_cb.isChecked()
        
        # Update X-axis weight if checkbox is checked
        if x_bold:
            self.plot_handler.set_label_weight('x', bold=True)
        else:
            self.plot_handler.set_label_weight('x', bold=False)
        
        # Update Y-axis weight if checkbox is checked
        if y_bold:
            self.plot_handler.set_label_weight('y', bold=True)
        else:
            self.plot_handler.set_label_weight('y', bold=False)
    
    def update_legend_position(self):
        """Update the legend position."""
        position_text = self.legend_position.currentText().lower().replace(" ", "_")
        
        # Set the legend position
        self.plot_handler.set_legend_position(position_text)
    
    def update_legend_draggable(self):
        """Update whether the legend is draggable."""
        draggable = self.draggable_legend.isChecked()
        
        # Set the legend draggable property
        self.plot_handler.set_draggable_legend(draggable)
    
    def update_legend_font(self):
        """Update the legend font size."""
        font_size = self.legend_font_size.value()
        
        # Set the legend font size on the plot
        self.plot_handler.set_legend_font_size(font_size)
    
    def toggle_trend_controls(self, state):
        """Toggle the visibility of trend analysis controls based on checkbox state."""
        is_visible = state == Qt.Checked
        
        # Enable or disable the trend controls based on the checkbox state
        if hasattr(self, 'trend_type_combo'):
            self.trend_type_combo.setEnabled(is_visible)
            self.trend_degree_spinner.setEnabled(is_visible)
            self.trend_style_combo.setEnabled(is_visible)
            self.trend_width_spinner.setEnabled(is_visible)
            self.trend_color_button.setEnabled(is_visible)
        
        # If trend is being disabled, remove trend lines from plot
        if not is_visible and hasattr(self.plot_handler, 'remove_trend_lines'):
            self.plot_handler.remove_trend_lines()
            self.update_plot()
    
    def export_plot(self):
        """Export current plot as an image."""
        if not self.selected_wells:
            self.status_bar.showMessage("No data to export.")
            return
            
        # Let the export manager handle this
        self.export_manager.export_plot_image(self.plot_handler.figure, self.selected_wells)
    
    def export_data(self):
        """Export current plot data to CSV."""
        if not self.selected_wells:
            self.status_bar.showMessage("No data to export.")
            return
            
        # Get settings - check main dialog first, then plot controls dialog
        if hasattr(self, 'show_manual_cb'):
            show_manual = self.show_manual_cb.isChecked()
        elif hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
            show_manual = self.plot_controls_dialog.show_manual_cb.isChecked()
        else:
            show_manual = False
            
        if hasattr(self, 'export_downsample_cb'):
            apply_downsample = self.export_downsample_cb.isChecked()
        else:
            apply_downsample = False
        
        # Get downsampling settings if needed
        downsample_method = None
        agg_method = "mean"
        if apply_downsample:
            if hasattr(self, 'downsample_combo'):
                downsample_method = self.downsample_combo.currentText()
            elif hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                downsample_method = self.plot_controls_dialog.downsample_combo.currentText()
            
            if hasattr(self, 'aggregate_combo'):
                agg_method = self.aggregate_combo.currentText().lower()
            elif hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                agg_method = self.plot_controls_dialog.aggregate_combo.currentText().lower()
            
        # Let the export manager handle this
        self.export_manager.export_to_csv(
            self.selected_wells, 
            self.date_range, 
            show_manual,
            apply_downsample=apply_downsample, 
            downsample_method=downsample_method,
            agg_method=agg_method if apply_downsample else None
        )
        
        # Update status
        if apply_downsample:
            self.status_bar.showMessage(f"Data exported with {downsample_method} downsampling using {agg_method} method")
        else:
            self.status_bar.showMessage("Data exported without downsampling")
    
    def on_theme_changed(self, index):
        """Handle theme changes from the combo box."""
        theme_map = {
            0: {"theme": "light", "color_theme": "light"},  # Light Theme
            1: {"theme": "dark", "color_theme": "dark"},    # Dark Theme
            2: {"theme": "light", "color_theme": "blue"},   # Blue Theme
            3: {"theme": "light", "color_theme": "earth"}   # Earth Theme
        }
        
        if index in theme_map:
            self.theme = theme_map[index]["theme"]
            self.color_theme = theme_map[index]["color_theme"]
            self.apply_theme()
            logger.info(f"Theme changed to {self.theme_combo.currentText()}")
        
    def apply_theme(self):
        """Apply the current theme to the application."""
        # Get theme colors from theme manager
        theme_colors = self.theme_manager.get_theme_colors(self.theme)
        
        # Apply stylesheet to dialog
        stylesheet = self.theme_manager.get_theme_stylesheet(self.theme, self.color_theme)
        self.setStyleSheet(stylesheet)
        
        # Apply theme to plot
        plot_colors = self.theme_manager.get_plot_theme_colors(self.theme, self.color_theme)
        self.plot_handler.apply_theme(plot_colors)
        
        # Update status bar with theme info
        self.status_bar.showMessage(f"Theme: {self.theme_combo.currentText()}", 3000)
    
    def toggle_grid(self, state):
        """Toggle grid visibility based on checkbox state."""
        show_grid = state == Qt.Checked
        self.plot_handler.set_grid(show_grid)
        self.update_plot()
        
    def select_trend_color(self):
        """Open a color dialog to select a color for trend lines."""
        current_color = QColor(self.trend_color_button.styleSheet().split(":")[-1].strip("; "))
        
        color = QColorDialog.getColor(current_color, self, "Select Trend Line Color")
        if color.isValid():
            self.trend_color_button.setStyleSheet(f"background-color: {color.name()};")
            # If Show Trend is checked, update the plot
            if self.show_trend_cb.isChecked():
                self.apply_trend_analysis()
    
    def apply_trend_analysis(self):
        """Apply trend analysis to selected wells."""
        if not self.selected_wells:
            return
            
        try:
            # Get trend settings from dialog if available, otherwise use defaults
            trend_type = "Linear"
            trend_degree = 1
            trend_style = "--"
            trend_width = 1.5
            trend_color = "#ff7f0e"  # Default orange
            
            if hasattr(self, 'plot_controls_dialog') and self.plot_controls_dialog:
                dialog = self.plot_controls_dialog
                
                # Get trend type
                if hasattr(dialog, 'trend_type_combo'):
                    trend_type = dialog.trend_type_combo.currentText()
                
                # Get trend degree/window
                if hasattr(dialog, 'trend_degree_spinner'):
                    trend_degree = dialog.trend_degree_spinner.value()
                
                # Get line style
                if hasattr(dialog, 'trend_style_combo'):
                    style_name = dialog.trend_style_combo.currentText()
                    style_map = {
                        "Solid": "-",
                        "Dashed": "--",
                        "Dotted": ":",
                        "Dash-Dot": "-."
                    }
                    trend_style = style_map.get(style_name, "--")
                
                # Get line width
                if hasattr(dialog, 'trend_width_spinner'):
                    trend_width = dialog.trend_width_spinner.value()
                
                # Get color
                if hasattr(dialog, 'trend_color_button'):
                    color_style = dialog.trend_color_button.styleSheet()
                    if "background-color:" in color_style:
                        trend_color = color_style.split("background-color:")[-1].strip("; ")
            elif hasattr(self, 'trend_type_combo'):
                # Get trend type
                trend_type = self.trend_type_combo.currentText()
                
                # Get trend degree/window
                trend_degree = self.trend_degree_spinner.value()
                
                # Get line style
                style_name = self.trend_style_combo.currentText()
                style_map = {
                    "Solid": "-",
                    "Dashed": "--",
                    "Dotted": ":",
                    "Dash-Dot": "-."
                }
                trend_style = style_map.get(style_name, "--")
                
                # Get line width
                trend_width = self.trend_width_spinner.value()
                
                # Get color
                color_style = self.trend_color_button.styleSheet()
                if "background-color:" in color_style:
                    trend_color = color_style.split("background-color:")[-1].strip("; ")
                    
            # Create style dictionary
            style = {
                'line_style': trend_style,
                'line_width': trend_width,
                'color': trend_color
            }
            
            # Apply trend analysis based on type
            trend_type_map = {
                "Linear": "linear",
                "Polynomial": "polynomial", 
                "Moving Avg": "moving_average"
            }
            
            # Call the unified apply_trend_analysis method
            self.plot_handler.apply_trend_analysis(
                self.selected_wells, 
                trend_type=trend_type_map.get(trend_type, "linear"),
                degree=trend_degree,
                style=style
            )
            
            # Update status message
            if trend_type == "Linear":
                self.status_bar.showMessage(f"Applied linear trend analysis to {len(self.selected_wells)} wells")
            elif trend_type == "Polynomial":
                self.status_bar.showMessage(f"Applied polynomial trend (degree {trend_degree}) to {len(self.selected_wells)} wells")
            elif trend_type == "Moving Avg":
                self.status_bar.showMessage(f"Applied {trend_degree}-month moving average to {len(self.selected_wells)} wells")
                
        except Exception as e:
            logger.error(f"Error applying trend analysis: {e}")
            self.status_bar.showMessage(f"Error applying trend analysis: {str(e)}")

    def on_trend_checkbox_changed(self, state):
        """Handle trend checkbox state change."""
        is_checked = state == Qt.Checked
        
        if is_checked:
            # Apply trend analysis when checkbox is checked
            self.apply_trend_analysis()
        else:
            # Remove trend lines when checkbox is unchecked
            if hasattr(self.plot_handler, 'remove_trend_lines'):
                self.plot_handler.remove_trend_lines()
    
    def on_trend_setting_changed(self, *args):
        """Handle changes to trend settings."""
        # Only apply changes if trend is visible
        if self.show_trend_cb.isChecked():
            self.apply_trend_analysis()

    def accept(self):
        """Save properties and close the dialog."""
        # Save properties before closing
        self.plot_handler.save_properties()
        
        # Call the parent method to close the dialog
        super().accept()
        
    def reject(self):
        """Save properties and close the dialog."""
        # Save properties before closing
        self.plot_handler.save_properties()
        
        # Call the parent method to close the dialog
        super().reject()

    def load_well_data(self):
        """Load data for selected wells and update the plot."""
        print("[MAIN_PLOT_DEBUG] load_well_data() called")
        if not self.selected_wells:
            print("[MAIN_PLOT_DEBUG] No selected wells, returning")
            return
            
        # Show progress dialog for data loading if many wells are selected
        if len(self.selected_wells) > 3:
            progress = QProgressDialog("Loading well data...", "Cancel", 0, len(self.selected_wells), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setValue(0)
            progress.show()
        else:
            progress = None
            
        # Loop through selected wells to load their data
        for i, well in enumerate(self.selected_wells):
            # Update progress
            if progress:
                progress.setValue(i)
                if progress.wasCanceled():
                    break
                    
            # Check if we already have data for this well
            if well not in self.plot_handler.well_data or not hasattr(self.plot_handler, 'well_data_full') or well not in self.plot_handler.well_data_full:
                # Get data for this well using the same FastDataManager that works in RISE tab
                df = self.data_manager.get_well_data(well, 
                    start_date=self.date_range.get('start') if self.date_range else None,
                    end_date=self.date_range.get('end') if self.date_range else None,
                    downsample='1D')
                
                # Set data in plot handler
                if not df.empty:
                    self.plot_handler.set_well_data(well, df)
        
        # Close progress dialog
        if progress:
            progress.setValue(len(self.selected_wells))
            
        # Update the plot
        self.update_plot()

    def update_database_info(self):
        """Update the database info label in the status bar."""
        if hasattr(self, 'db_info_label'):
            if self.db_path:
                db_name = os.path.basename(self.db_path)
                self.db_info_label.setText(f"Database: {db_name}")
                self.db_info_label.setToolTip(f"Full path: {self.db_path}")
                logger.info(f"Current database: {self.db_path}")
            else:
                self.db_info_label.setText("No database loaded")
                self.db_info_label.setToolTip("Click 'Switch DB' to load a database file")
                logger.info("No database currently loaded")
    
    def open_database(self):
        """Open a new database file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Database File", "", 
            "SQLite Database Files (*.db *.sqlite);;All Files (*)", 
            options=options
        )
        
        if file_path:
            # Confirm with user (but not if no database is currently loaded)
            if self.db_path:
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Change Database")
                msg_box.setText("Changing database will reset all current selections and visualizations.")
                msg_box.setInformativeText("Do you want to continue?")
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.No)
                
                if msg_box.exec_() != QMessageBox.Yes:
                    return
            
            # Proceed with database loading
            # Check if the database exists and is valid
            if not os.path.exists(file_path):
                QMessageBox.critical(self, "Error", f"Database file not found: {file_path}")
                return
                
            try:
                # Import the database manager with optimized connection settings
                import sqlite3
                from simple_db_manager import SimpleDatabaseManager
                
                # Create a temporary DB manager to verify the database
                temp_manager = SimpleDatabaseManager(file_path)
                # The optimized connection settings are already applied in the SimpleDatabaseManager
                # Get and close the connection
                temp_conn = temp_manager.get_connection()
                
                # Reset the application with the new database
                logger.info(f"Switching database to: {file_path}")
                self.restart_with_new_database(file_path)
                
            except Exception as e:
                logger.error(f"Error opening database: {e}")
                QMessageBox.critical(self, "Error", f"Failed to open database: {str(e)}")
    
    def restart_with_new_database(self, new_db_path):
        """Restart the application with a new database."""
        try:
            # Create a new DB manager
            from simple_db_manager import SimpleDatabaseManager
            new_db_manager = SimpleDatabaseManager(new_db_path)
            
            # Clear current state
            self.selected_wells = []
            self.well_colors = {}
            self.well_line_widths = {}
            self.well_line_styles = {}
            self.date_range = {'start': None, 'end': None}
            
            # Update database references
            self.db_manager = new_db_manager
            self.db_path = str(new_db_manager.current_db)
            self.data_manager = DataManager(self.db_path)
            
            # Save the new database path for future standalone use
            self._save_last_database_path(self.db_path)
            
            # Update export manager to use new data manager
            if self.export_manager:
                self.export_manager.data_manager = self.data_manager
            else:
                self.export_manager = ExportManager(self.data_manager, self.plot_handler)
            
            # Update central data store
            if self.central_data_store:
                # Disconnect old signals
                self.central_data_store.loading_started.disconnect()
                self.central_data_store.loading_finished.disconnect()
                self.central_data_store.error_occurred.disconnect()
            
            # Create new central data store
            self.central_data_store = CentralDataStore(self.data_manager)
            self.central_data_store.loading_started.connect(self.on_loading_started)
            self.central_data_store.loading_finished.connect(self.on_loading_finished)
            self.central_data_store.error_occurred.connect(self.on_data_error)
            
            # Update UI
            self.update_database_info()
            self.load_wells()
            self.status_bar.showMessage(f"Database changed to: {os.path.basename(new_db_path)}", 5000)
            
            # Reset the plot
            self.plot_handler.clear_plot()
            self.plot_handler.initialize_plot()
            
        except Exception as e:
            logger.error(f"Error restarting with new database: {e}")
            QMessageBox.critical(self, "Error", f"Failed to switch database: {str(e)}")

    def toggle_water_year_highlight(self, state):
        """Toggle water year highlighting based on checkbox state."""
        is_checked = state == Qt.Checked
        self.plot_handler.set_water_year_highlight(is_checked)
        
        # Force a redraw of the plot
        if hasattr(self, 'plot_handler') and hasattr(self.plot_handler, 'highlight_water_years'):
            self.plot_handler.canvas.draw()
        
        # Show status message
        if is_checked:
            self.status_bar.showMessage("Water year highlighting enabled")
        else:
            self.status_bar.showMessage("Water year highlighting disabled")
            
    def toggle_gaps_highlight(self, state):
        """Toggle gaps highlighting based on checkbox state."""
        is_checked = state == Qt.Checked
        self.plot_handler.set_gaps_highlight(is_checked)
        
        # Force a redraw of the plot
        if hasattr(self, 'plot_handler') and hasattr(self.plot_handler, 'highlight_gaps'):
            self.plot_handler.canvas.draw()
        
        # Show status message
        if is_checked:
            self.status_bar.showMessage("Data gaps highlighting enabled")
        else:
            self.status_bar.showMessage("Data gaps highlighting disabled")

    def select_pre_selected_well(self):
        """Select the pre-selected well if one was provided in the settings."""
        if not hasattr(self, 'pre_selected_well') or not self.pre_selected_well:
            return
        
        logger.info(f"Attempting to select pre-selected well: {self.pre_selected_well}")
        
        # Check if well table is populated
        if self.well_table.rowCount() == 0:
            logger.warning("Well table is empty, scheduling another attempt to select well")
            QTimer.singleShot(500, self.select_pre_selected_well)
            return
        
        # Find the well in the table
        found = False
        for row in range(self.well_table.rowCount()):
            item = self.well_table.item(row, 0)  # Assuming well number is in column 0
            if item and item.text() == self.pre_selected_well:
                logger.info(f"Found pre-selected well {self.pre_selected_well} at row {row}")
                
                # Make sure the row is visible (not filtered out)
                self.well_table.setRowHidden(row, False)
                
                # Reset any filters
                self.filter_input.blockSignals(True)
                self.filter_input.setCurrentText("All Aquifers")
                self.filter_input.blockSignals(False)
                
                # Select this row
                self.well_table.selectRow(row)
                
                # Scroll to make it visible
                self.well_table.scrollToItem(item)
                found = True
                
                # Set the auto date range
                self.set_auto_date_range()
                
                # Update status bar
                self.status_bar.showMessage(f"Selected well {self.pre_selected_well} automatically")
                
                # Log success
                logger.info(f"Pre-selected well {self.pre_selected_well} successfully selected")
                break
        
        if not found:
            logger.warning(f"Pre-selected well {self.pre_selected_well} not found in well table")
            
            # If this is the first attempt, try again after a delay
            if hasattr(self, '_select_well_attempts'):
                self._select_well_attempts += 1
            else:
                self._select_well_attempts = 1
                
            if self._select_well_attempts < 3:
                logger.info(f"Will try again to select well (attempt {self._select_well_attempts} of 3)")
                QTimer.singleShot(1000, self.select_pre_selected_well)
                return
        
        # Clear pre-selected well to avoid reselecting on refresh
        self.pre_selected_well = None
        if hasattr(self, '_select_well_attempts'):
            delattr(self, '_select_well_attempts')

    def show_plot_controls(self):
        """Show the plot controls dialog."""
        # If dialog doesn't exist, create it
        if not hasattr(self, 'plot_controls_dialog') or not self.plot_controls_dialog:
            from gui.dialogs.plot_controls_dialog import PlotControlsDialog
            self.plot_controls_dialog = PlotControlsDialog(self)
            
            # Connect signals
            self.plot_controls_dialog.plot_updated.connect(self.on_plot_updated)
            self.plot_controls_dialog.export_triggered.connect(self.handle_export)
            
        # Make sure dialog has latest well data
        self.plot_controls_dialog.sync_from_parent()
        
        # Show the dialog
        self.plot_controls_dialog.show()
        
        # Position the dialog at the bottom of the main window
        main_geo = self.geometry()
        dialog_geo = self.plot_controls_dialog.geometry()
        
        # Center horizontally relative to main window
        x = main_geo.x() + (main_geo.width() - dialog_geo.width()) // 2
        # Position at bottom of main window with small gap
        y = main_geo.y() + main_geo.height() + 10
        
        self.plot_controls_dialog.move(x, y)
        self.plot_controls_dialog.raise_()
        self.plot_controls_dialog.activateWindow()

    def handle_export(self, export_type):
        """Handle export requests from the plot controls dialog."""
        if export_type == 'plot':
            self.export_plot()
        elif export_type == 'data':
            self.export_data()
    
    def on_loading_started(self, message):
        """Handle loading started signal from central data store."""
        self.status_bar.showMessage(message)
        
    def on_loading_finished(self):
        """Handle loading finished signal from central data store."""
        self.status_bar.showMessage("Data loading complete", 2000)
        
    def on_data_error(self, error_message):
        """Handle data error signal from central data store."""
        logger.error(f"Data store error: {error_message}")
        self.status_bar.showMessage(f"Error: {error_message}", 5000)
        
    def load_well_data(self):
        """Load data for selected wells using central data store."""
        if not self.selected_wells:
            return
            
        # The plotting is handled by the existing plot infrastructure
        # Just emit the plot_updated signal to trigger any necessary updates
        if hasattr(self, 'plot_handler'):
            self.plot_handler.plot_updated.emit()
