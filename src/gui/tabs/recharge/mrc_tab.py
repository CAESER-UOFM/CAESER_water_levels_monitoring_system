"""
MRC (Master Recession Curve) method for recharge estimation.
This tab implements the MRC method for calculating recharge using water level data.
Based on USGS EMR (Episodic Master Recession) methodology.
"""

import logging
import numpy as np
import os
import sys
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QPushButton, QGroupBox, QTableWidget, 
    QTableWidgetItem, QMessageBox, QDateEdit, QSplitter,
    QCheckBox, QFrame, QTabWidget, QGridLayout, QSizePolicy,
    QHeaderView, QSpinBox, QRadioButton, QButtonGroup,
    QAbstractItemView, QDialog, QDialogButtonBox, QTextEdit
)
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd
from scipy import signal, optimize
from scipy.stats import linregress

from .db.mrc_database import MrcDatabase
try:
    from .base_recharge_tab import BaseRechargeTab
    from .settings_persistence import SettingsPersistence
except ImportError:
    from base_recharge_tab import BaseRechargeTab
    try:
        from settings_persistence import SettingsPersistence
    except ImportError:
        # Gracefully handle case where settings persistence isn't available
        SettingsPersistence = None

logger = logging.getLogger(__name__)


class CollapsibleGroupBox(QFrame):
    """
    A collapsible group box that can expand and collapse its content.
    """
    toggled = pyqtSignal(bool)  # Signal emitted when expanded/collapsed
    
    def __init__(self, title="", persistence_key=None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        self.title = title
        self.persistence_key = persistence_key  # Unique key for saving state
        self.is_expanded = False  # Start collapsed by default
        self.animation_duration = 200
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header frame with toggle button and title
        self.header_frame = QFrame()
        self.header_frame.setFrameShape(QFrame.StyledPanel)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(8, 8, 8, 8)
        
        # Toggle button
        self.toggle_button = QPushButton("▶")  # Right arrow for collapsed
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 3px;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 13px;
                color: #2c3e50;
                padding-left: 5px;
            }
        """)
        
        self.header_layout.addWidget(self.toggle_button)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        # Content frame
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        self.content_layout.setSpacing(4)  # Reduced spacing
        
        # Add header and content to main layout
        self.main_layout.addWidget(self.header_frame)
        self.main_layout.addWidget(self.content_frame)
        
        # Animation for smooth expand/collapse
        self.animation = QPropertyAnimation(self.content_frame, b"maximumHeight")
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.finished.connect(self.on_animation_finished)
        
        # Apply styling similar to QGroupBox  
        self.setStyleSheet("""
            CollapsibleGroupBox {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 2px 0px;
                background-color: transparent;
                min-height: 44px;
            }
        """)
        
        # Store the original height for animation
        self.content_height = 0
        
        # Set initial collapsed state
        self.content_frame.setMaximumHeight(0)
        
        # Ensure consistent header height when collapsed
        self.header_frame.setFixedHeight(36)  # Fixed header height for consistency
        
    def set_content_layout(self, layout):
        """Set the layout for the content area."""
        # Clear existing layout
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
            elif child.layout():
                self.clear_layout(child.layout())
        
        # Add new layout/widget
        if hasattr(layout, 'count'):  # It's a layout
            # Transfer all widgets from the given layout to our content layout
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    self.content_layout.addWidget(item.widget())
                elif item.layout():
                    self.content_layout.addLayout(item.layout())
        else:  # It's a widget
            self.content_layout.addWidget(layout)
            
    def clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
            elif child.layout():
                self.clear_layout(child.layout())
    
    def add_widget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)
        
    def add_layout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)
        
    def toggle(self):
        """Toggle the expanded/collapsed state."""
        self.is_expanded = not self.is_expanded
        self.set_expanded(self.is_expanded)
        
    def set_expanded(self, expanded, save_state=True):
        """Set the expanded state."""
        self.is_expanded = expanded
        
        if expanded:
            self.toggle_button.setText("▼")  # Down arrow
            self.expand()
        else:
            self.toggle_button.setText("▶")  # Right arrow
            self.collapse()
            
        self.toggled.emit(expanded)
        
        # Save state if requested
        if save_state:
            self.save_state()
        
    def expand(self):
        """Expand the content area."""
        if self.content_height == 0:
            # Calculate the content height
            self.content_frame.adjustSize()
            self.content_height = max(self.content_frame.sizeHint().height(), 100)
        
        # Reset max height and show content
        self.content_frame.setMaximumHeight(16777215)  # Remove height constraint
        self.animation.setStartValue(0 if self.content_frame.maximumHeight() == 0 else self.content_frame.height())
        self.animation.setEndValue(self.content_height)
        self.animation.start()
        
    def collapse(self):
        """Collapse the content area."""
        if self.content_height == 0:
            self.content_height = max(self.content_frame.height(), self.content_frame.sizeHint().height(), 100)
            
        self.animation.setStartValue(self.content_height)
        self.animation.setEndValue(0)
        self.animation.start()
        
    def set_content_height(self, height):
        """Manually set the content height for animation."""
        self.content_height = height
        
    def on_animation_finished(self):
        """Handle animation completion."""
        if not self.is_expanded:
            # When collapsed, hide content completely
            self.content_frame.setMaximumHeight(0)
        else:
            # When expanded, remove height constraint
            self.content_frame.setMaximumHeight(16777215)
            
    def save_state(self):
        """Save the expanded/collapsed state to persistent storage."""
        if self.persistence_key and SettingsPersistence:
            try:
                settings = SettingsPersistence()
                preference_key = f"collapsible_panel_{self.persistence_key}_expanded"
                settings.save_user_preference(preference_key, self.is_expanded)
            except Exception as e:
                logger.warning(f"Failed to save panel state for {self.persistence_key}: {e}")
                
    def load_state(self):
        """Load the expanded/collapsed state from persistent storage."""
        if self.persistence_key and SettingsPersistence:
            try:
                settings = SettingsPersistence()
                preference_key = f"collapsible_panel_{self.persistence_key}_expanded"
                saved_state = settings.get_user_preference(preference_key)
                if saved_state is not None:
                    # Convert to boolean if it's a string
                    if isinstance(saved_state, str):
                        saved_state = saved_state.lower() in ('true', '1', 'yes')
                    self.set_expanded(bool(saved_state), save_state=False)
                    return True
            except Exception as e:
                logger.warning(f"Failed to load panel state for {self.persistence_key}: {e}")
        
        # If no saved state exists, ensure we're in the default collapsed state
        if not self.is_expanded:
            self.set_expanded(False, save_state=False)
        return False


class MrcTab(BaseRechargeTab):
    """
    Tab implementing the MRC method for recharge estimation.
    """
    
    def __init__(self, db_manager, parent=None):
        """
        Initialize the MRC tab.
        
        Args:
            db_manager: Database manager providing access to well data
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.data_manager = db_manager  # Fix: set data_manager for get_db_path() method
        self.selected_wells = []
        self.well_data = {}
        self.current_well = None
        self.water_years = []
        self.selected_water_year = None
        self.raw_data = None  # Store the raw data (15-min intervals)
        self.processed_data = None  # Store the processed/filtered data
        self.display_data = None  # Store downsampled data for fast plotting
        self.current_curve = None  # Current MRC curve parameters
        self.recession_segments = []  # Identified recession segments
        self.recharge_events = []  # Calculated recharge events
        
        # Data management - separate display and calculation data (like RISE tab)
        self.display_data = None  # Store downsampled data for fast plotting
        self.calculation_data = None  # Store the full resolution data for calculations
        self.data_loaded = {'display': False, 'full': False}  # Track what's loaded
        self.data_loading = False  # Prevent concurrent loading
        
        # Initialize default settings for data processing
        self.current_settings = {
            'specific_yield': 0.2,
            'mrc_deviation_threshold': 0.1,
            'water_year_month': 10,
            'water_year_day': 1,
            'downsample_frequency': 'None',
            'downsample_method': 'Mean',
            'enable_smoothing': False,
            'smoothing_window': 3,
            'min_recession_length': 7,
            'fluctuation_tolerance': 0.02,
            'use_precipitation': False,
            'precip_threshold': 0.1,
            'precip_lag': 2
        }
        logger.info(f"[INIT_DEBUG] MRC tab initialized with default settings: min_recession_length={self.current_settings['min_recession_length']}")
        
        # Initialize database for MRC calculations
        self.mrc_db = None
        self.db_path = None  # Store path, create connection when needed
        self.get_db_path()
        
        # Session state management for preserving work across well switches
        self.well_sessions = {}  # Store per-well state data
        self.session_saving_enabled = True  # Can be disabled during restoration
        
        # Setup UI
        self.setup_ui()
    
    def get_db_path(self):
        """Get database path from data manager."""
        try:
            logger.info(f"[DB_PATH_DEBUG] data_manager type: {type(self.data_manager)}")
            logger.info(f"[DB_PATH_DEBUG] data_manager attributes: {[attr for attr in dir(self.data_manager) if not attr.startswith('_')]}")
            
            # Get database path from data manager
            if hasattr(self.data_manager, 'db_path'):
                logger.info(f"[DB_PATH_DEBUG] Found db_path: {self.data_manager.db_path}")
                self.db_path = self.data_manager.db_path
            elif hasattr(self.data_manager, '_db_manager') and hasattr(self.data_manager._db_manager, 'current_db'):
                logger.info(f"[DB_PATH_DEBUG] Found _db_manager.current_db: {self.data_manager._db_manager.current_db}")
                self.db_path = self.data_manager._db_manager.current_db
            elif hasattr(self.data_manager, 'current_db'):
                logger.info(f"[DB_PATH_DEBUG] Found current_db: {self.data_manager.current_db}")
                self.db_path = self.data_manager.current_db
            else:
                logger.warning(f"[DB_PATH_DEBUG] Could not find database path in data manager")
                logger.warning(f"[DB_PATH_DEBUG] Available attributes: {[attr for attr in dir(self.data_manager) if 'db' in attr.lower()]}")
                self.db_path = None
        except Exception as e:
            logger.error(f"Error getting database path: {e}")
            self.db_path = None
    
    def get_mrc_database(self):
        """Get or create MRC database connection for current thread."""
        logger.info(f"[DB_DEBUG] get_mrc_database called, self.db_path = {self.db_path}")
        
        if not self.db_path:
            logger.warning("[DB_DEBUG] db_path is None, trying to get it")
            self.get_db_path()
            logger.info(f"[DB_DEBUG] After get_db_path, self.db_path = {self.db_path}")
            
        if not self.db_path:
            logger.error("[DB_DEBUG] Still no db_path after get_db_path")
            return None
            
        try:
            # Create a new database connection for this thread
            mrc_db = MrcDatabase(self.db_path)
            
            # Create tables if they don't exist
            success = mrc_db.create_tables()
            if success:
                return mrc_db
            else:
                logger.error("Failed to initialize MRC database tables")
                return None
                
        except Exception as e:
            logger.error(f"Error creating MRC database connection: {e}")
            return None
    
    def setup_ui(self):
        """Set up the UI for the MRC tab."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "The MRC method estimates recharge by identifying deviations from a master recession curve. "
            "First create or select a recession curve, then calculate recharge based on positive deviations."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Create main splitter (Parameters on left, Plot on right)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)
        
        # Left panel - Parameters and results
        left_panel = self.create_left_panel()
        self.main_splitter.addWidget(left_panel)
        
        # Right panel - Plot visualization
        right_panel = self.create_plot_panel()
        self.main_splitter.addWidget(right_panel)
        
        # Set splitter sizes to match fixed widths (400px left, 800px right)
        self.main_splitter.setSizes([400, 800])
        
        layout.addWidget(self.main_splitter)
        
        # Load saved panel states, but start collapsed
        self.load_panel_states()
        # Override to start collapsed regardless of saved state
        self.segments_group.set_expanded(False, save_state=False)
        self.curve_group.set_expanded(False, save_state=False)
    
    def load_panel_states(self):
        """Load the saved states of collapsible panels."""
        try:
            # Load states for both collapsible panels
            self.segments_group.load_state()
            self.curve_group.load_state()
            logger.debug("Loaded collapsible panel states")
        except Exception as e:
            logger.warning(f"Failed to load panel states: {e}")
    
    def create_left_panel(self):
        """Create the left panel with tabs for parameters, curve management, and results."""
        from PyQt5.QtWidgets import QScrollArea
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for parameters and results
        self.left_tabs = QTabWidget()
        
        # Curve Management tab with scroll area
        curve_panel = self.create_curve_management_panel()
        curve_scroll = QScrollArea()
        curve_scroll.setWidget(curve_panel)
        curve_scroll.setWidgetResizable(True)
        curve_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Prevent horizontal scrolling
        curve_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        curve_scroll.setContentsMargins(0, 0, 0, 0)  # Remove scroll area margins
        self.left_tabs.addTab(curve_scroll, "Curve Management")
        
        # Results tab
        results_panel = self.create_results_panel()
        self.left_tabs.addTab(results_panel, "Results")
        
        left_layout.addWidget(self.left_tabs)
        
        # Set fixed width for visual consistency across all tabs
        left_widget.setFixedWidth(400)
        left_widget.setContentsMargins(0, 0, 0, 0)  # Remove any extra margins
        
        return left_widget
    
    
    def create_curve_management_panel(self):
        """Create the curve management panel unique to MRC."""
        panel = QWidget()
        panel.setMaximumWidth(395)  # Ensure panel never exceeds width
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(2, 2, 2, 2)  # Minimal panel margins
        layout.setSpacing(6)  # Further reduced spacing
        
        # Well selection
        well_layout = QHBoxLayout()
        well_label = QLabel("Well:")
        well_label.setFixedWidth(35)  # Fixed narrow width for label
        well_layout.addWidget(well_label)
        self.well_combo = QComboBox()
        self.well_combo.setEnabled(False)
        self.well_combo.currentIndexChanged.connect(self.on_well_selected)
        self.well_combo.setMaximumWidth(350)  # Strict maximum width limit
        well_layout.addWidget(self.well_combo)
        layout.addLayout(well_layout)
        
        # Move curve selection and fitting into Step 2 below
        
        # Curve management buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)  # Increased spacing between sections
        
        # Consistent button styling for all buttons - more compact
        button_style = """
            QPushButton {
                padding: 6px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 10px;
                font-weight: 500;
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
        """
        
        # Enhanced GroupBox styling
        groupbox_style = """
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #495057;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """
        
        # Step 1: Recession Segment Analysis (Collapsible)
        self.segments_group = CollapsibleGroupBox("Step 1: Recession Segment Analysis", "mrc_step1_segments")
        self.segments_group.setMaximumWidth(390)  # Ensure group fits
        self.segments_group.setMinimumHeight(44)  # Consistent collapsed height
        self.segments_group.set_expanded(False, save_state=False)  # Start collapsed
        
        # Create mixed layout: button + dropdown for better workflow
        segments_action_layout = QHBoxLayout()
        segments_action_layout.setSpacing(8)
        
        # Analyze button (left side)
        self.identify_recessions_btn = QPushButton("Analyze Patterns")
        self.identify_recessions_btn.clicked.connect(self.identify_recession_segments)
        self.identify_recessions_btn.setEnabled(False)
        self.identify_recessions_btn.setStyleSheet(button_style)
        self.identify_recessions_btn.setToolTip("Identify recession periods from water level data")
        segments_action_layout.addWidget(self.identify_recessions_btn)
        
        self.segments_group.add_layout(segments_action_layout)
        
        # Load segments section
        load_segments_layout = QVBoxLayout()
        load_segments_layout.setSpacing(3)  # Reduced spacing
        
        load_segments_label = QLabel("Load Segments:")
        load_segments_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin-top: 8px;")
        load_segments_layout.addWidget(load_segments_label)
        
        # Segments dropdown
        self.segments_combo = QComboBox()
        self.segments_combo.addItem("No segments selected", None)
        self.segments_combo.currentIndexChanged.connect(self.on_segments_selected)
        self.segments_combo.setMinimumHeight(26)
        self.segments_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 10px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }
        """)
        load_segments_layout.addWidget(self.segments_combo)
        
        self.segments_group.add_layout(load_segments_layout)
        
        # Status indicator
        self.segments_status_label = QLabel("No recession segments identified")
        self.segments_status_label.setStyleSheet("color: #666; font-style: italic; margin: 5px;")
        self.segments_group.add_widget(self.segments_status_label)
        
        # Interactive recession segments table (like RISE tab)
        self.recession_table = QTableWidget()
        self.recession_table.setColumnCount(6)
        self.recession_table.setHorizontalHeaderLabels([
            "Use", "Start", "End", "Days", "Rate", "Quality"
        ])
        self.recession_table.setAlternatingRowColors(True)
        self.recession_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recession_table.verticalHeader().setVisible(False)
        
        # Set specific column widths to fit in 390px (400px - margins)
        self.recession_table.setColumnWidth(0, 30)   # Use checkbox
        self.recession_table.setColumnWidth(1, 60)   # Start date
        self.recession_table.setColumnWidth(2, 60)   # End date
        self.recession_table.setColumnWidth(3, 40)   # Duration
        self.recession_table.setColumnWidth(4, 50)   # Rate
        self.recession_table.setColumnWidth(5, 55)   # Quality
        
        # Disable horizontal scrolling and stretch to fit
        self.recession_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.recession_table.horizontalHeader().setStretchLastSection(True)
        self.recession_table.setMaximumHeight(140)  # Slightly bigger for quality column
        self.recession_table.setMaximumWidth(385)  # Ensure table fits in panel
        self.recession_table.itemChanged.connect(self.on_segment_selection_changed)
        self.segments_group.add_widget(self.recession_table)
        
        # Selection summary
        self.selection_summary_label = QLabel("No segments available")
        self.selection_summary_label.setStyleSheet("color: #666; font-style: italic; margin: 5px;")
        self.segments_group.add_widget(self.selection_summary_label)
        
        button_layout.addWidget(self.segments_group)
        
        # Step 2: Interactive Curve Fitting (Collapsible)
        self.curve_group = CollapsibleGroupBox("Step 2: Interactive Curve Fitting", "mrc_step2_curves")
        self.curve_group.setMaximumWidth(390)  # Ensure group fits
        self.curve_group.setMinimumHeight(44)  # Consistent collapsed height
        self.curve_group.set_expanded(False, save_state=False)  # Start collapsed
        
        # Vertical layout for curve selection and results to save horizontal space
        curve_info_vertical = QVBoxLayout()
        curve_info_vertical.setSpacing(3)  # Reduced spacing
        
        # Load existing curves section
        existing_label = QLabel("Load Existing Curve:")
        existing_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px; margin-bottom: 2px;")
        curve_info_vertical.addWidget(existing_label)
        
        # Curve selection dropdown
        self.curve_combo = QComboBox()
        self.curve_combo.addItem("No curve selected", None)
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        self.curve_combo.setMinimumHeight(22)  # Further reduced height
        self.curve_combo.setMaximumWidth(360)  # Strict width limit
        self.curve_combo.setStyleSheet("""
            QComboBox {
                padding: 3px 6px;
                border: 1px solid #ced4da;
                border-radius: 3px;
                background-color: white;
                font-size: 9px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox::down-arrow {
                width: 8px;
                height: 8px;
            }
        """)
        curve_info_vertical.addWidget(self.curve_combo)
        
        # Current curve info - compact display
        self.curve_info_label = QLabel("No curve loaded")
        self.curve_info_label.setWordWrap(True)
        self.curve_info_label.setStyleSheet("font-style: italic; color: #6c757d; margin: 2px 0px; font-size: 9px;")
        curve_info_vertical.addWidget(self.curve_info_label)
        
        # Current Curve Results section - now below the dropdown
        results_label = QLabel("Current Results:")
        results_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin-top: 8px; margin-bottom: 2px;")
        curve_info_vertical.addWidget(results_label)
        
        # Create a styled container for curve equation and R² - very compact
        results_container = QFrame()
        results_container.setMaximumWidth(360)  # Strict width limit
        results_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 2px;
                padding: 2px;
            }
        """)
        results_container_layout = QVBoxLayout(results_container)
        results_container_layout.setContentsMargins(2, 2, 2, 2)
        results_container_layout.setSpacing(1)
        
        # Curve equation
        self.curve_equation_label = QLabel("No curve fitted")
        self.curve_equation_label.setWordWrap(True)
        self.curve_equation_label.setStyleSheet("font-family: 'Courier New', monospace; color: #495057; font-size: 9px; font-weight: 500;")
        results_container_layout.addWidget(self.curve_equation_label)
        
        # R² value
        self.r_squared_label = QLabel("R² = N/A")
        self.r_squared_label.setStyleSheet("font-weight: bold; color: #28a745; font-size: 10px;")
        results_container_layout.addWidget(self.r_squared_label)
        
        curve_info_vertical.addWidget(results_container)
        
        self.curve_group.add_layout(curve_info_vertical)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #dee2e6; margin: 8px 0px;")
        self.curve_group.add_widget(separator)
        
        # Interactive fitting section
        fitting_section = QFrame()
        fitting_layout = QVBoxLayout(fitting_section)
        fitting_layout.setContentsMargins(2, 3, 2, 3)  # Further reduced margins
        fitting_layout.setSpacing(3)  # Reduced spacing
        
        fitting_label = QLabel("Fit/Edit Actions:")
        fitting_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px; margin-bottom: 2px;")
        fitting_layout.addWidget(fitting_label)
        
        # Instructions and status
        self.fitting_preview_label = QLabel("Select segments above, then use buttons below to fit or manage curves")
        self.fitting_preview_label.setWordWrap(True)
        self.fitting_preview_label.setStyleSheet("color: #6c757d; font-style: italic; margin: 2px 0px; font-size: 10px;")
        fitting_layout.addWidget(self.fitting_preview_label)
        
        # Vertical button layout to save horizontal space
        curve_button_layout = QVBoxLayout()
        curve_button_layout.setSpacing(3)  # Reduced spacing
        
        # Primary action button
        self.fit_curve_btn = QPushButton("Interactive Fitting")
        self.fit_curve_btn.clicked.connect(self.open_interactive_curve_fitting)
        self.fit_curve_btn.setEnabled(False)
        self.fit_curve_btn.setStyleSheet(button_style)
        self.fit_curve_btn.setMaximumWidth(360)  # Ensure button fits
        self.fit_curve_btn.setToolTip(
            "Opens an interactive dialog where you can:\n"
            "• Choose between Exponential, Power Law, or Linear curve types\n"
            "• Manually adjust parameters and see real-time curve updates\n"
            "• Use Auto Optimize to find the best-fit parameters\n"
            "• View R² and RMSE statistics to assess fit quality\n"
            "• Compare how different curve types fit your recession data\n"
            "• Save curves directly from the dialog"
        )
        curve_button_layout.addWidget(self.fit_curve_btn)
        
        # Manage data button
        self.manage_data_btn = QPushButton("Manage Data")
        self.manage_data_btn.clicked.connect(self.manage_data)
        self.manage_data_btn.setEnabled(False)
        self.manage_data_btn.setStyleSheet(button_style)
        self.manage_data_btn.setMaximumWidth(360)  # Ensure button fits
        self.manage_data_btn.setToolTip(
            "Manage saved curves and segments.\n"
            "This allows you to:\n"
            "• Delete curves and their associated segments\n"
            "• View all saved data for the current well\n"
            "• Clean up outdated or unwanted data"
        )
        curve_button_layout.addWidget(self.manage_data_btn)
        
        fitting_layout.addLayout(curve_button_layout)
        self.curve_group.add_widget(fitting_section)
        
        button_layout.addWidget(self.curve_group)
        
        # Step 3: Recharge Calculation
        recharge_group = QGroupBox("Step 3: Recharge Calculation")
        recharge_group.setStyleSheet(groupbox_style)
        recharge_layout = QVBoxLayout(recharge_group)
        recharge_layout.setContentsMargins(12, 16, 12, 12)
        recharge_layout.setSpacing(8)
        
        # Enhanced calculate button with better styling
        self.calculate_btn = QPushButton("🧮 Calculate Recharge")
        self.calculate_btn.setEnabled(False)
        self.calculate_btn.setMinimumHeight(42)
        self.calculate_btn.clicked.connect(self.calculate_recharge)
        enhanced_button_style = button_style + """
            QPushButton {
                font-size: 12px;
                font-weight: 600;
                background-color: #007bff;
                color: white;
                border: 1px solid #0056b3;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
        self.calculate_btn.setStyleSheet(enhanced_button_style)
        self.calculate_btn.setToolTip("Calculate recharge based on deviations from master curve")
        recharge_layout.addWidget(self.calculate_btn)
        
        # Calculation status with better styling
        self.calc_status_label = QLabel("Ready to calculate recharge")
        self.calc_status_label.setStyleSheet("color: #6c757d; font-style: italic; margin: 4px 0px; font-size: 10px; text-align: center;")
        self.calc_status_label.setAlignment(Qt.AlignCenter)
        recharge_layout.addWidget(self.calc_status_label)
        
        button_layout.addWidget(recharge_group)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        return panel
    
    def create_results_panel(self):
        """Create the results panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Create yearly statistics table
        self.yearly_stats_table = QTableWidget()
        self.yearly_stats_table.setColumnCount(5)
        self.yearly_stats_table.setHorizontalHeaderLabels([
            "Water Year", "Events", "Recharge (in)", "Rate (in/yr)", "Max Deviation (ft)"
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
        count_layout.addWidget(QLabel("Total Events:"))
        self.events_count_label = QLabel("0")
        self.events_count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        count_layout.addWidget(self.events_count_label)
        count_layout.addStretch()
        summary_layout.addLayout(count_layout)
        
        layout.addWidget(summary_group)
        
        # Export options
        export_layout = QHBoxLayout()
        
        # Define button styling
        button_style = """
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
        """
        
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_to_csv)
        export_csv_btn.setStyleSheet(button_style)
        export_layout.addWidget(export_csv_btn)
        
        export_excel_btn = QPushButton("Export to Excel")
        export_excel_btn.clicked.connect(self.export_to_excel)
        export_excel_btn.setStyleSheet(button_style)
        export_layout.addWidget(export_excel_btn)
        
        layout.addLayout(export_layout)
        
        # Database operations
        db_group = QGroupBox("Database Operations")
        db_layout = QVBoxLayout(db_group)
        
        # Save button
        self.save_to_db_btn = QPushButton("Save to Database")
        self.save_to_db_btn.clicked.connect(self.save_to_database)
        self.save_to_db_btn.setToolTip("Save the current MRC calculation to the database")
        self.save_to_db_btn.setStyleSheet(button_style)
        db_layout.addWidget(self.save_to_db_btn)
        
        # Load button
        self.load_from_db_btn = QPushButton("Load from Database")
        self.load_from_db_btn.clicked.connect(self.load_from_database)
        self.load_from_db_btn.setToolTip("Load a previous MRC calculation from the database")
        self.load_from_db_btn.setStyleSheet(button_style)
        db_layout.addWidget(self.load_from_db_btn)
        
        # Compare button
        self.compare_btn = QPushButton("Compare Calculations")
        self.compare_btn.clicked.connect(self.compare_calculations)
        self.compare_btn.setToolTip("Compare multiple MRC calculations")
        self.compare_btn.setStyleSheet(button_style)
        db_layout.addWidget(self.compare_btn)
        
        layout.addWidget(db_group)
        
        return panel
    
    def create_plot_panel(self):
        """Create the plot panel for visualization."""
        group_box = QGroupBox("Visualization")
        group_box.setFixedWidth(800)  # Fixed width for visual consistency
        layout = QVBoxLayout(group_box)
        
        # Plot panel
        # Use base class figure and canvas (already initialized with correct size)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Use standardized display options from base class
        display_options = self.create_plot_display_options()
        
        # Set processed data checkbox to checked by default for MRC tab
        if hasattr(self, 'show_processed_data'):
            self.show_processed_data.setChecked(True)
        
        # Add MRC-specific plot options
        mrc_options_layout = QHBoxLayout()
        
        self.show_recession_curve = QCheckBox("Show Recession Curve")
        self.show_recession_curve.setChecked(True)
        self.show_recession_curve.stateChanged.connect(self.update_plot)
        mrc_options_layout.addWidget(self.show_recession_curve)
        
        self.show_deviations = QCheckBox("Show Deviations")
        self.show_deviations.setChecked(True)
        self.show_deviations.stateChanged.connect(self.update_plot)
        mrc_options_layout.addWidget(self.show_deviations)
        
        # Add refresh button at the same level as display options
        button_style = """
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
        """
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.update_plot)
        refresh_btn.setStyleSheet(button_style)
        refresh_btn.setMaximumWidth(100)
        mrc_options_layout.addWidget(refresh_btn)
        mrc_options_layout.addStretch()
        
        # Create a combined layout for display options
        combined_options_layout = QHBoxLayout()
        combined_options_layout.addWidget(display_options)
        combined_options_layout.addLayout(mrc_options_layout)
        
        layout.addLayout(combined_options_layout)
        
        return group_box
    
    def update_well_selection(self, selected_wells):
        """Update the list of selected wells."""
        self.selected_wells = selected_wells
        
        # Update combo box
        self.well_combo.clear()
        
        if selected_wells:
            self.well_combo.setEnabled(True)
            self.identify_recessions_btn.setEnabled(True)
            
            for well_id, cae_number in selected_wells:
                # well_id is the Well Number, cae_number is the CAE Number
                # Display well number as primary, with CAE number in parentheses if different
                if cae_number and cae_number != well_id:
                    display_name = f"{well_id} ({cae_number})"
                else:
                    # If CAE number is same as well number or missing, just show the well number
                    display_name = well_id
                self.well_combo.addItem(display_name, well_id)
                
            # Load curves and segments for the first well
            if len(selected_wells) > 0:
                first_well_id = selected_wells[0][0]
                self.load_curves_for_well(first_well_id)
                self.load_segments_for_well(first_well_id)
                self.manage_data_btn.setEnabled(True)
        else:
            self.well_combo.setEnabled(False)
            self.identify_recessions_btn.setEnabled(False)
    
    def on_well_selected(self, index):
        """Handle well selection from dropdown."""
        if index < 0:
            return
            
        well_id = self.well_combo.currentData()
        well_name = self.well_combo.currentText()
        
        # Save current well state before switching (if we have a current well)
        if self.current_well and self.session_saving_enabled:
            self.save_current_well_state()
        
        self.current_well = well_id
        
        # Check if we have session state for this well
        if well_id in self.well_sessions:
            # Restore previous session state
            self.restore_well_state(well_id)
        else:
            # Clear results and start fresh
            self.clear_results()
            
            # Data loading disabled - using centralized preprocessing from parent tab
            logger.info(f"[PLOT_DEBUG] Skipping individual data loading for MRC - waiting for shared data")
                
            # Load curves for this well
            self.load_curves_for_well(well_id)
            
            # Load segments for this well
            self.load_segments_for_well(well_id)
        
        # Enable identify recessions button and manage data button
        self.identify_recessions_btn.setEnabled(True)
        self.manage_data_btn.setEnabled(True)
    
    def get_method_name(self):
        """Get the method name for this tab (required by base class)."""
        return "MRC"
    
    def load_curves_for_well(self, well_id):
        """Load available curves for the selected well."""
        try:
            logger.info(f"[MRC_CURVES_DEBUG] load_curves_for_well called with well_id: {well_id}")
            logger.info(f"[MRC_CURVES_DEBUG] mrc_db state: {self.mrc_db is not None}")
            
            # Ensure database is initialized
            if not self.mrc_db:
                logger.info(f"MRC database not initialized, initializing now...")
                self.mrc_db = self.get_mrc_database()
                if not self.mrc_db:
                    logger.error("Failed to initialize MRC database")
                    return
            
            # Clear curve combo
            self.curve_combo.clear()
            self.curve_combo.addItem("No curve selected", None)
            
            # Get curves from database
            # Note: well_id here is actually the well_number (string identifier)
            curves = self.mrc_db.get_curves_for_well(well_id)
            logger.info(f"Found {len(curves)} curves for well {well_id}")
            
            if curves:
                logger.info(f"[CURVE_DROPDOWN_DEBUG] Processing {len(curves)} curves")
                logger.info(f"[CURVE_DROPDOWN_DEBUG] First curve: {curves[0]}")
            else:
                logger.warning(f"[CURVE_DROPDOWN_DEBUG] No curves returned for well {well_id}")
            
            for i, curve in enumerate(curves):
                label = f"{curve['creation_date'][:10]} - {curve['curve_type']} (R²={curve['r_squared']:.3f})"
                if curve['description']:
                    label += f" - {curve['description']}"
                logger.info(f"[CURVE_DROPDOWN_DEBUG] Adding curve {i}: {label} (ID: {curve['id']})")
                self.curve_combo.addItem(label, curve['id'])
                
            logger.info(f"[CURVE_DROPDOWN_DEBUG] Dropdown now has {self.curve_combo.count()} items")
                
        except Exception as e:
            logger.error(f"Error loading curves: {e}")
    
    def load_curve_segments(self, curve_id):
        """Load recession segments associated with a specific curve."""
        try:
            logger.info(f"Loading segments for curve {curve_id}")
            
            # Get segments from database
            segments_data = self.mrc_db.get_segments_for_curve(curve_id)
            if not segments_data:
                logger.warning(f"No segments found for curve {curve_id}")
                self.recession_segments = []
                return
            
            # Load segments using existing load_segments_from_data method
            self.load_segments_from_data(segments_data)
            
            # Update UI
            self.update_recession_table()
            self.update_segments_status()
            
            # Enable fit curve button for modification
            if hasattr(self, 'recession_segments') and self.recession_segments:
                self.fit_curve_btn.setEnabled(True)
            
            # Check if no segments were loaded and inform user
            if not self.recession_segments:
                # Get diagnostic information
                diagnostic_info = self.mrc_db.diagnose_segment_data_issues(self.current_well)
                curves_with_issues = diagnostic_info.get('summary', {}).get('curves_with_issues', 0)
                total_curves = diagnostic_info.get('summary', {}).get('total_curves', 0)
                
                QMessageBox.warning(self, "No Segments Available", 
                    f"The selected curve has no usable segment data.\n\n"
                    f"Diagnostic info for this well:\n"
                    f"• {curves_with_issues} out of {total_curves} curves have data issues\n\n"
                    f"This may happen if:\n"
                    f"• The segments were saved with an older version\n"
                    f"• There was a data corruption issue\n\n"
                    f"You can identify new recession segments to replace the missing data.")
            
            # Save session state after loading segments
            if self.session_saving_enabled and self.current_well:
                self.save_current_well_state()
                
            logger.info(f"Successfully loaded {len(self.recession_segments)} segments for curve {curve_id}")
            
        except Exception as e:
            logger.error(f"Error loading segments for curve {curve_id}: {e}")
            self.recession_segments = []
    
    def load_segments_for_well(self, well_id):
        """Load all segment sets for the current well into the segments dropdown."""
        try:
            if not well_id:
                self.segments_combo.clear()
                self.segments_combo.addItem("No segments available", None)
                return
                
            logger.info(f"Loading segment sets for well {well_id}")
            
            # Ensure database is initialized
            if not self.mrc_db:
                self.mrc_db = self.get_mrc_database()
                if not self.mrc_db:
                    logger.error("Failed to initialize MRC database")
                    return
            
            # Clear and populate segments dropdown
            self.segments_combo.clear()
            self.segments_combo.addItem("No segments selected", None)
            
            # Add current segments if they exist (unsaved)
            if hasattr(self, 'recession_segments') and self.recession_segments:
                segment_count = len(self.recession_segments)
                self.segments_combo.addItem(f"Current - Unsaved ({segment_count} segments)", "current")
            
            # Get saved segment sets from database
            segment_sets = self.mrc_db.get_all_segments_for_well(well_id)
            
            for segment_set in segment_sets:
                date_str = segment_set['creation_date'][:10]  # Get just the date part
                curve_type = segment_set['curve_type']
                count = segment_set['segment_count']
                r_squared = segment_set.get('r_squared', 0)
                
                label = f"{date_str} - {curve_type} (R²={r_squared:.3f}) - {count} segments"
                if segment_set.get('description'):
                    label += f" - {segment_set['description'][:20]}..."
                    
                self.segments_combo.addItem(label, segment_set['curve_id'])
                
            logger.info(f"Loaded {len(segment_sets)} segment sets for dropdown")
            
        except Exception as e:
            logger.error(f"Error loading segment sets: {e}")
    
    def on_segments_selected(self, index):
        """Handle segment selection from dropdown."""
        if index <= 0:  # "No segments selected"
            return
            
        segments_id = self.segments_combo.currentData()
        
        # Handle current segments (unsaved)
        if segments_id == "current":
            logger.info("Current segments already loaded")
            return
            
        # Handle saved segments from database
        if segments_id and self.mrc_db:
            try:
                logger.info(f"Loading segments for curve {segments_id}")
                self.load_curve_segments(segments_id)
            except Exception as e:
                logger.error(f"Error loading segments for curve {segments_id}: {e}")
    
    def manage_data(self):
        """Open dialog to manage curves and segments."""
        if not self.current_well:
            QMessageBox.warning(self, "No Well Selected", "Please select a well first.")
            return
            
        try:
            from .manage_data_dialog import ManageDataDialog
            
            dialog = ManageDataDialog(self.current_well, self.mrc_db, self)
            if dialog.exec_() == QDialog.Accepted:
                # Refresh curves and segments dropdowns
                self.load_curves_for_well(self.current_well)
                self.load_segments_for_well(self.current_well)
                
        except ImportError:
            # For now, show a simple message until we create the dialog
            QMessageBox.information(self, "Manage Data", 
                "Data management dialog will be implemented.\n"
                "This will allow you to delete curves and segments.")
        except Exception as e:
            logger.error(f"Error opening manage data dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open manage data dialog: {str(e)}")
    
    def on_curve_selected(self, index):
        """Handle curve selection from dropdown."""
        if index <= 0:  # "No curve selected"
            self.current_curve = None
            self.curve_info_label.setText("No curve loaded")
            self.curve_equation_label.setText("No curve fitted")
            self.r_squared_label.setText("R² = N/A")
            self.calculate_btn.setEnabled(False)
            return
            
        curve_id = self.curve_combo.currentData()
        
        # Handle current fitted curve (not yet saved)
        if curve_id == "current":
            # Current curve is already set, just enable buttons
            if self.current_curve:
                self.calculate_btn.setEnabled(True)
            return
            
        # Handle saved curves from database
        if curve_id and self.mrc_db:
            # Load curve details
            curve_data = self.mrc_db.get_curve_details(curve_id)
            if curve_data:
                self.current_curve = curve_data
                self.display_curve_info(curve_data)
                self.calculate_btn.setEnabled(True)
                
                # Load associated segments for this curve
                self.load_curve_segments(curve_id)
                
                self.update_plot()
                
                # Save session state after successful curve loading
                if self.session_saving_enabled and self.current_well:
                    self.save_current_well_state()
    
    def display_curve_info(self, curve_data):
        """Display information about the loaded curve."""
        curve_type = curve_data['curve_type']
        # Handle both old and new parameter formats
        # Priority: 'parameters' > 'curve_coefficients' > 'curve_parameters'
        if 'parameters' in curve_data and curve_data['parameters']:
            params = curve_data['parameters']
        elif 'curve_coefficients' in curve_data and curve_data['curve_coefficients']:
            params = curve_data['curve_coefficients']
        elif 'curve_parameters' in curve_data and curve_data['curve_parameters']:
            params = curve_data['curve_parameters']
        else:
            params = {}
            logger.warning(f"[MRC_TAB] No parameters found in curve_data for equation display")
        
        # Update curve info label
        info_text = f"Type: {curve_type}\n"
        info_text += f"Created: {curve_data['creation_date'][:10]}\n"
        info_text += f"Segments used: {curve_data['recession_segments']}"
        self.curve_info_label.setText(info_text)
        
        # Update equation label with proper formatting
        self.curve_equation_label.setTextFormat(Qt.RichText)
        
        if curve_type == 'exponential':
            # Check if it's the new format or old format
            if 'a' in params and 'b' in params:
                # New format: Q = a × (1 - e^(-bt))
                equation = f"Q = {params['a']:.3f} × (1 - e<sup>-{params['b']:.4f}t</sup>)"
            elif 'Q0' in params and 'a' in params:
                # Old format: Q = Q0 × e^(-at) -> keep as is for display consistency
                Q0 = params['Q0']
                a = params['a']
                equation = f"Q = {Q0:.3f} × e<sup>-{a:.4f}t</sup>"
            else:
                # Fallback for other old formats
                alpha = params.get('alpha', params.get('a', 0))
                equation = f"Q = Q<sub>0</sub> × e<sup>-{alpha:.4f}t</sup>"
        elif curve_type == 'power':
            if 'a' in params and 'b' in params:
                # New format: Q = a × t^b
                equation = f"Q = {params['a']:.3f} × t<sup>{params['b']:.3f}</sup>"
            elif 'Q0' in params and 'b' in params:
                # Old format: Q = Q0 × t^(-b) -> keep as is for display consistency
                Q0 = params['Q0']
                b = params['b']
                equation = f"Q = {Q0:.3f} × t<sup>-{b:.4f}</sup>"
            else:
                # Fallback for other old formats
                beta = params.get('beta', params.get('b', 0))
                equation = f"Q = Q<sub>0</sub> × t<sup>-{beta:.4f}</sup>"
        else:  # linear
            if 'a' in params and 'b' in params:
                # New format: Q = a - b × t
                equation = f"Q = {params['a']:.3f} - {params['b']:.4f} × t"
            elif 'intercept' in params and 'slope' in params:
                # Old format: ln(Q) = intercept + slope×t
                intercept = params['intercept']
                slope = params['slope']
                equation = f"ln(Q) = {intercept:.4f} + {slope:.4f}×t"
            else:
                # Fallback
                intercept = params.get('intercept', 0)
                slope = params.get('slope', 0)
                equation = f"ln(Q) = {intercept:.4f} - {slope:.4f}×t"
        
        self.curve_equation_label.setText(equation)
        
        # Update R-squared
        self.r_squared_label.setText(f"R² = {curve_data['r_squared']:.4f}")
    
    def load_display_data(self, well_id):
        """Load downsampled data for fast plotting."""
        # DISABLED: Using centralized preprocessing from parent tab
        logger.info(f"[PLOT_DEBUG] load_display_data disabled - using centralized preprocessing")
        return
        
        if self.data_loading:
            return
            
        try:
            self.data_loading = True
            logger.info(f"[PLOT_DEBUG] Loading display data for well {well_id}")
            
            # Load raw data without hardcoded downsampling
            data = self.data_manager.get_well_data(well_id, downsample=None)
            
            if data is not None and len(data) > 0:
                logger.info(f"[PLOT_DEBUG] Loaded {len(data)} display data points for well {well_id}")
                
                # Standardize column names and store as raw data
                self.raw_data = self._standardize_dataframe(data.copy())
                self.current_well_id = well_id
                self.data_loaded['display'] = True
                
                # Process the data using global settings (like ERC tab)
                self.processed_data = self._comprehensive_process_data(self.raw_data.copy())
                
                # Keep display_data for backward compatibility
                self.display_data = self.raw_data
                
                # Update plot
                self.update_plot()
                
                return True
            else:
                logger.warning(f"No data found for well {well_id}")
                self._show_empty_plot(f"No data available for well {well_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading display data for well {well_id}: {e}")
            self._show_empty_plot(f"Error loading data: {str(e)}")
            return False
        finally:
            self.data_loading = False
    
    def load_full_data_for_calculations(self, well_id):
        """Load full resolution data for calculations."""
        if self.data_loaded['full'] and self.current_well_id == well_id:
            return True
            
        try:
            logger.info(f"[CALC_DEBUG] Loading full data for calculations: {well_id}")
            
            # Get full resolution data for calculations
            data = self.data_manager.get_well_data(well_id, downsample=None)
            
            if data is not None and len(data) > 0:
                logger.info(f"[CALC_DEBUG] Loaded {len(data)} full data points for calculations")
                
                # Standardize and store for calculations
                self.calculation_data = self._standardize_dataframe(data.copy())
                self.data_loaded['full'] = True
                
                return True
            else:
                logger.warning(f"No full data found for well {well_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading full data for well {well_id}: {e}")
            return False
    
    def _standardize_dataframe(self, df):
        """Standardize dataframe column names and formats."""
        # Check column names and rename if necessary
        if 'timestamp_utc' in df.columns:
            df = df.rename(columns={
                'timestamp_utc': 'timestamp'
                # Keep 'water_level' as is - don't rename to 'level'
            })
        
        # Make sure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Always ensure water_level column is numeric, regardless of current dtype
        if 'water_level' in df.columns:
            # Force conversion to numeric to handle any string-like types
            df['water_level'] = pd.to_numeric(df['water_level'], errors='coerce')
            # Drop any rows where water_level conversion failed (resulted in NaN)
            df = df.dropna(subset=['water_level'])
            logger.debug(f"Water_level column dtype after conversion: {df['water_level'].dtype}")
        
        return df

    def load_well_data(self, well_id):
        """Load water level data for the selected well - using new pattern like RISE tab."""
        # DISABLED: Using centralized preprocessing from parent tab
        logger.info(f"[PLOT_DEBUG] load_well_data disabled - using centralized preprocessing")
        return
        
        logger.info(f"load_well_data called for well {well_id}")
        
        # Store current well ID for later reference
        self.current_well_id = well_id
        
        # Reset data loading state
        self.data_loaded = {'display': False, 'full': False}
        
        # Use the display data loading method
        self.load_display_data(well_id)
        
    def reset_data_state(self):
        """Reset data loading state - called when switching wells."""
        self.data_loaded = {'display': False, 'full': False}
        self.data_loading = False
        self.raw_data = None
        self.processed_data = None
        self.display_data = None
        logger.info("Data state reset")
    
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
                if 'water_level' in data.columns:
                    data['water_level'] = data['water_level'].rolling(window=window, center=False).mean()
                    logger.info(f"[PROCESS_DEBUG] Applied smoothing with window {window}")
            
            # Drop NaN values
            data = data.dropna()
            
            # Final validation to ensure no NaN/Inf values remain
            if 'water_level' in data.columns:
                if data['water_level'].isna().any():
                    logger.warning(f"Removing {data['water_level'].isna().sum()} remaining NaN values")
                    data = data.dropna(subset=['water_level'])
                    
                if not np.isfinite(data['water_level']).all():
                    logger.warning("Found non-finite values in level data, removing them")
                    data = data[np.isfinite(data['water_level'])]
            
            logger.info(f"[PROCESS_DEBUG] Data processing complete: {len(raw_data)} -> {len(data)} points")
            return data
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return raw_data.copy()  # Return unprocessed data on error
    
    def _simple_process_data(self, raw_data):
        """Simple data processing method that applies smoothing based on settings (deprecated)."""
        # Keep for backward compatibility, but use comprehensive method
        return self._comprehensive_process_data(raw_data)
    
    def load_display_data(self, well_id):
        """Load downsampled data for quick display/preview."""
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
                # Load ALL available data without downsampling (raw data)
                logger.debug(f"Loading all available raw data for display")
                
                logger.info(f"[DEBUG] About to call {type(self.data_manager).__name__}.get_well_data()")
                query_start = time.time()
                df = self.data_manager.get_well_data(
                    well_id, 
                    downsample=None  # Load raw data without downsampling
                )
                query_time = time.time() - query_start
                logger.debug(f"Database query took {query_time:.2f} seconds")
                logger.info(f"[DEBUG] Data manager call completed, returned {len(df) if df is not None else 0} rows")
                
                if df is not None and not df.empty:
                    logger.info(f"[PLOT_DEBUG] Successfully loaded {len(df)} display data points for well {well_id}")
                    
                    # Standardize column names
                    df = self._standardize_dataframe(df)
                    
                    # Store display data
                    self.display_data = df
                    # Also set raw_data so base class plotting works
                    self.raw_data = df
                    
                    # Process data according to global settings for the "Show Processed Data" option
                    logger.info(f"[PLOT_DEBUG] Processing data with global settings...")
                    try:
                        # Try to process data with a simple inline method for now
                        processed_df = self._simple_process_data(df)
                        if processed_df is not None:
                            self.processed_data = processed_df
                            logger.info(f"[PLOT_DEBUG] Processed data created: {len(processed_df)} points")
                        else:
                            logger.warning(f"[PLOT_DEBUG] Data processing returned None, using raw data")
                            self.processed_data = df.copy()
                    except Exception as e:
                        logger.error(f"[PLOT_DEBUG] Processing failed: {e}", exc_info=True)
                        # Fallback: use raw data as processed data
                        self.processed_data = df.copy()
                    
                    self.data_loaded['display'] = True
                    logger.info(f"[PLOT_DEBUG] Data stored (raw_data and processed_data), updating data_loaded to: {self.data_loaded}")
                    
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
                    logger.debug(f"Total load_display_data took {total_time:.2f} seconds")
                    
                else:
                    logger.warning(f"[PLOT_DEBUG] No data returned from data manager for well {well_id}")
                    self._show_empty_plot("No data available for this well")
            else:
                logger.error(f"[PLOT_DEBUG] Data manager does not have get_well_data method")
                self._show_empty_plot("Data manager error")
                
        except Exception as e:
            logger.error(f"[PLOT_DEBUG] Error in load_display_data: {e}", exc_info=True)
            self._show_empty_plot(f"Error loading data: {e}")
        finally:
            self.data_loading = False
    
    def load_full_data_for_calculations(self, well_id):
        """Load full resolution data for MRC calculations."""
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
    
    def _show_empty_plot(self, message="No data available"):
        """Show an empty plot with a message."""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, message, 
                   horizontalalignment='center', 
                   verticalalignment='center',
                   transform=ax.transAxes,
                   fontsize=12,
                   color='gray')
            ax.set_title('MRC Analysis', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Water Level (ft)')
            self.canvas.draw()
        except Exception as e:
            logger.error(f"[PLOT_DEBUG] Failed to show empty plot: {e}")
    
    def _create_synthetic_data(self):
        """Create synthetic data for demonstration."""
        # Create 2 years of data
        start_date = datetime.now() - timedelta(days=730)
        end_date = datetime.now()
        
        # Generate timestamps at 15-minute intervals
        timestamps = pd.date_range(start=start_date, end=end_date, freq='15min')
        
        # Generate water levels with recession behavior
        levels = []
        base_level = 100.0
        current_level = base_level
        
        for i, ts in enumerate(timestamps):
            # Add seasonal variation
            day_of_year = ts.timetuple().tm_yday
            seasonal = 2.0 * np.sin(2 * np.pi * (day_of_year - 60) / 365.0)
            
            # Add recession behavior
            if np.random.random() < 0.95:  # 95% of time, recession
                current_level *= 0.99995  # Slow recession
            else:  # 5% of time, recharge event
                current_level += np.random.uniform(0.5, 2.0)
                
            # Add noise
            noise = np.random.normal(0, 0.02)
            
            # Combine components
            level = current_level + seasonal + noise
            levels.append(level)
            
            # Prevent level from going too low
            if current_level < 95:
                current_level = base_level
        
        # Create DataFrame
        self.raw_data = pd.DataFrame({
            'timestamp': timestamps,
            'water_level': levels
        })
        
        logger.debug(f"Generated synthetic data with {len(self.raw_data)} points")
        
        # Don't process data automatically - wait for user action
        # Just update the plot to show raw data
        self.update_plot()
    
    def process_data(self):
        """Process the raw data with current preprocessing settings."""
        if self.raw_data is None:
            return
        
        # For MRC calculations, we need full resolution data
        # If we only have display data, we need to load full data
        if hasattr(self, 'current_well_id') and self.current_well_id:
            if not self.data_loaded.get('full', False):
                logger.info("Loading full resolution data for MRC processing")
                success = self.load_full_data_for_calculations(self.current_well_id)
                if not success:
                    logger.error("Failed to load full resolution data for processing")
                    return
            
        try:
            logger.info("Processing data for MRC method")
            
            # Start with raw data
            data = self.raw_data.copy()
            
            # Make sure timestamp is datetime
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Skip data quality checks for now - method doesn't exist
            # self._perform_data_quality_checks(data)
            
            # Get global settings for data processing
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                settings = self.parent.unified_settings.get_method_settings('MRC')
            else:
                # Fallback to defaults if unified settings not available
                settings = {
                    'downsample_frequency': 'None',
                    'downsample_method': 'Mean',
                    'enable_smoothing': False,
                    'smoothing_window': 3
                }
            
            # Apply downsampling
            resample_rule = settings.get('downsample_frequency', 'None')
            if resample_rule != "None" and resample_rule != "none":
                if 'timestamp' in data.columns:
                    data = data.set_index('timestamp')
                
                method = settings.get('downsample_method', 'Mean').lower()
                # Only resample numeric columns to avoid string aggregation errors
                numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
                if method == "mean":
                    data = data[numeric_columns].resample(resample_rule).mean()
                elif method == "median":
                    data = data[numeric_columns].resample(resample_rule).median()
                elif method == "last":
                    data = data[numeric_columns].resample(resample_rule).last()
                    
                data = data.reset_index()
            
            # Apply smoothing if enabled
            if settings.get('enable_smoothing', False):
                window = settings.get('smoothing_window', 3)
                if 'water_level' in data.columns:
                    data['water_level'] = data['water_level'].rolling(window=window, center=False).mean()
            
            # Drop NaN values
            data = data.dropna()
            
            # Store processed data
            self.processed_data = data
            logger.info(f"Processed data has {len(data)} points")
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            QMessageBox.warning(self, "Processing Error", f"Failed to process data: {str(e)}")
    
    def identify_recession_segments(self):
        """Identify recession segments in the data with USGS-compliant fluctuation tolerance."""
        if self.processed_data is None:
            QMessageBox.warning(self, "No Data", "Please load and process data first.")
            return
            
        try:
            logger.info("Identifying recession segments")
            
            # Get parameters from current settings (updated via update_settings method)
            current_settings = self.get_current_settings()
            
            # Try to get fresh settings from unified settings if available
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                try:
                    # Force fresh settings retrieval to get latest user changes
                    self.parent.unified_settings.load_settings()
                    fresh_settings = self.parent.unified_settings.get_method_settings('MRC')
                    
                    # Log what we got from fresh settings
                    fresh_min_length = fresh_settings.get('min_recession_length', 'NOT_FOUND')
                    current_min_length = current_settings.get('min_recession_length', 'NOT_FOUND')
                    logger.info(f"[SETTINGS_REFRESH_DEBUG] Fresh settings min_recession_length: {fresh_min_length}")
                    logger.info(f"[SETTINGS_REFRESH_DEBUG] Current settings min_recession_length: {current_min_length}")
                    
                    # Update our current settings with any fresh changes
                    current_settings.update(fresh_settings)
                    final_min_length = current_settings.get('min_recession_length', 'NOT_FOUND')
                    logger.info(f"[SETTINGS_REFRESH_DEBUG] Final merged min_recession_length: {final_min_length}")
                    logger.info(f"Retrieved and merged fresh MRC settings from global settings")
                except Exception as e:
                    logger.warning(f"Could not load fresh unified settings: {e}, using current settings")
            
            min_length = current_settings.get('min_recession_length', 10)
            precip_tolerance = current_settings.get('precip_threshold', 0.1) if current_settings.get('use_precipitation', False) else 0.1
            lag_days = current_settings.get('precip_lag', 2)
            fluctuation_tolerance = current_settings.get('fluctuation_tolerance', 0.01)
            logger.info(f"Using MRC settings - current/updated settings used")
            
            logger.info(f"Recession Parameters (from Global Settings): Min Length={min_length} days, Fluctuation Tolerance={fluctuation_tolerance} ft")
            
            # Calculate daily changes
            data = self.processed_data.copy()
            data['change'] = data['water_level'].diff()
            
            # Find recession periods with fluctuation tolerance
            # Allow small upticks during recession
            data['is_recession'] = data['change'] <= fluctuation_tolerance
            
            # Group consecutive recession days
            data['recession_group'] = (data['is_recession'] != data['is_recession'].shift()).cumsum()
            
            # Find recession segments
            self.recession_segments = []
            
            for group_id, group in data[data['is_recession']].groupby('recession_group'):
                if len(group) >= min_length:
                    # Check if this is a valid recession (net decline)
                    net_change = group['water_level'].iloc[-1] - group['water_level'].iloc[0]
                    if net_change < 0:  # Overall declining trend
                        segment = {
                            'start_date': group['timestamp'].iloc[0],
                            'end_date': group['timestamp'].iloc[-1],
                            'duration_days': len(group),
                            'start_level': group['water_level'].iloc[0],
                            'end_level': group['water_level'].iloc[-1],
                            'recession_rate': net_change / len(group),
                            'data': group
                        }
                        self.recession_segments.append(segment)
            
            # Update recession table
            self.update_recession_table()
            
            # Enable fit curve button
            if len(self.recession_segments) > 0:
                # Mark all segments as selected by default
                for segment in self.recession_segments:
                    segment['selected'] = True
                    
                # Enable buttons
                self.fit_curve_btn.setEnabled(True)
                
                # Update status
                self.update_segments_status()
                
                # Update segments dropdown to include current segments
                self.load_segments_for_well(self.current_well)
                
                QMessageBox.information(self, "Segments Found", 
                    f"Found {len(self.recession_segments)} recession segments meeting criteria.\n"
                    f"Segments are ready for curve fitting. They will be saved when you save a curve.")
            else:
                # Update status for no segments
                self.update_segments_status()
                QMessageBox.warning(self, "No Segments", 
                    "No recession segments found meeting the minimum length criteria.")
                
            # Update plot
            self.update_plot()
            
            # Save session state after successful recession identification
            if self.session_saving_enabled and self.current_well:
                self.save_current_well_state()
            
        except Exception as e:
            logger.error(f"Error identifying recession segments: {e}")
            QMessageBox.critical(self, "Error", f"Failed to identify recession segments: {str(e)}")
    
    def calculate_segment_quality(self, segment):
        """Calculate quality score for a recession segment (0-1)."""
        try:
            # Base score from duration (longer = better)
            duration_score = min(segment['duration_days'] / 30.0, 1.0)  # Max at 30 days
            
            # Score from recession rate consistency
            if 'data' in segment and len(segment['data']) > 2:
                levels = segment['data']['water_level'].values
                daily_changes = abs(levels[1:] - levels[:-1])
                if len(daily_changes) > 0:
                    consistency_score = 1.0 - min(daily_changes.std() / daily_changes.mean(), 1.0)
                else:
                    consistency_score = 0.5
            else:
                consistency_score = 0.5
            
            # Score from recession rate magnitude (not too fast, not too slow)
            rate = abs(segment['recession_rate'])
            if 0.001 <= rate <= 0.1:  # Good range for recession rates
                rate_score = 1.0
            elif rate < 0.001:
                rate_score = rate / 0.001  # Too slow
            else:
                rate_score = max(0.1, 0.1 / rate)  # Too fast
            
            # Weighted average
            quality = (duration_score * 0.4 + consistency_score * 0.4 + rate_score * 0.2)
            return max(0.0, min(1.0, quality))
            
        except Exception as e:
            logger.warning(f"Error calculating segment quality: {e}")
            return 0.5
    
    def create_color(self, hex_color):
        """Create QColor from hex string."""
        from PyQt5.QtGui import QColor
        return QColor(hex_color)
    
    def update_selection_summary(self):
        """Update the selection summary below the table."""
        total_segments = self.recession_table.rowCount()
        if total_segments == 0:
            self.selection_summary_label.setText("No segments available")
            return
        
        selected_count = 0
        high_quality = 0
        medium_quality = 0
        low_quality = 0
        
        for row in range(total_segments):
            checkbox = self.recession_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
                quality_item = self.recession_table.item(row, 5)
                if quality_item:
                    quality = float(quality_item.text())
                    if quality >= 0.8:
                        high_quality += 1
                    elif quality >= 0.6:
                        medium_quality += 1
                    else:
                        low_quality += 1
        
        summary = f"{selected_count} of {total_segments} segments selected"
        if selected_count > 0:
            quality_summary = []
            if high_quality > 0:
                quality_summary.append(f"{high_quality} high")
            if medium_quality > 0:
                quality_summary.append(f"{medium_quality} medium")
            if low_quality > 0:
                quality_summary.append(f"{low_quality} low")
            
            if quality_summary:
                summary += f" ({', '.join(quality_summary)} quality)"
        
        self.selection_summary_label.setText(summary)
        
        # Enable/disable curve fitting based on selection
        self.fit_curve_btn.setEnabled(selected_count > 0)
        
        # Update curve type preview based on current selection
        self.on_curve_type_changed()
    
    def on_segment_selection_changed(self):
        """Handle changes in segment selection."""
        self.update_selection_summary()
    
    def update_recession_table(self):
        """Update the recession segments table with checkboxes and quality scores."""
        self.recession_table.setRowCount(len(self.recession_segments))
        
        for row, segment in enumerate(self.recession_segments):
            # Use checkbox (column 0)
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_selection_summary)
            self.recession_table.setCellWidget(row, 0, checkbox)
            
            # Start date (column 1)
            self.recession_table.setItem(row, 1, 
                QTableWidgetItem(segment['start_date'].strftime('%Y-%m-%d')))
            
            # End date (column 2)
            self.recession_table.setItem(row, 2, 
                QTableWidgetItem(segment['end_date'].strftime('%Y-%m-%d')))
            
            # Duration (column 3)
            self.recession_table.setItem(row, 3, 
                QTableWidgetItem(str(segment['duration_days'])))
            
            # Recession rate (column 4)
            rate_item = QTableWidgetItem(f"{segment['recession_rate']:.4f}")
            self.recession_table.setItem(row, 4, rate_item)
            
            # Quality score (column 5)
            quality_score = self.calculate_segment_quality(segment)
            quality_item = QTableWidgetItem(f"{quality_score:.2f}")
            
            # Color code based on quality
            if quality_score >= 0.8:
                quality_item.setBackground(self.create_color('#d4edda'))  # Green
                self.recession_table.item(row, 1).setBackground(self.create_color('#d4edda'))
                self.recession_table.item(row, 2).setBackground(self.create_color('#d4edda'))
            elif quality_score >= 0.6:
                quality_item.setBackground(self.create_color('#fff3cd'))  # Yellow
                self.recession_table.item(row, 1).setBackground(self.create_color('#fff3cd'))
                self.recession_table.item(row, 2).setBackground(self.create_color('#fff3cd'))
            else:
                quality_item.setBackground(self.create_color('#f8d7da'))  # Red
                self.recession_table.item(row, 1).setBackground(self.create_color('#f8d7da'))
                self.recession_table.item(row, 2).setBackground(self.create_color('#f8d7da'))
            
            self.recession_table.setItem(row, 5, quality_item)
        
        # Update selection summary
        self.update_selection_summary()
    
    def fit_recession_curve(self):
        """Fit a master recession curve to the identified segments."""
        if not self.recession_segments:
            QMessageBox.warning(self, "No Segments", "Please identify recession segments first.")
            return
            
        try:
            logger.info("Fitting master recession curve")
            
            # Collect data from selected segments
            all_data = []
            for i, segment in enumerate(self.recession_segments):
                checkbox = self.recession_table.cellWidget(i, 4)
                if checkbox and checkbox.isChecked():
                    # Normalize time to start at 0 for each segment
                    seg_data = segment['data'].copy()
                    seg_data['time_days'] = (seg_data['timestamp'] - seg_data['timestamp'].iloc[0]).dt.total_seconds() / 86400
                    # Normalize to start at the initial level (more intuitive for recession)
                    seg_data['normalized_level'] = seg_data['water_level'] - seg_data['water_level'].iloc[0]
                    all_data.append(seg_data)
            
            if not all_data:
                QMessageBox.warning(self, "No Selection", "Please select at least one recession segment.")
                return
                
            # Combine all selected segments
            combined_data = pd.concat(all_data, ignore_index=True)
            
            # Fit curve based on selected type
            curve_type = self.curve_type_combo.currentData()
            
            if curve_type == 'exponential':
                # Fit exponential: Q = a * (1 - exp(-b*t)) - NEW FORMAT
                # Use log transformation: ln(Q) = ln(Q0) - a*t for intermediate calculation
                valid_data = combined_data[combined_data['normalized_level'] > 0]
                x = valid_data['time_days'].values
                y = np.log(valid_data['normalized_level'].values)
                
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                
                # Convert to new format: Q = a * (1 - exp(-b*t))
                old_a = -slope  # decay rate
                old_Q0 = np.exp(intercept)  # initial value
                
                # For consistency with new format, use a=Q_max, b=alpha
                a = old_Q0  # maximum drawdown
                b = old_a   # decay rate
                r_squared = r_value ** 2
                
                coefficients = {'a': a, 'b': b}
                self.curve_equation_label.setTextFormat(Qt.RichText)
                equation = f"Q = {a:.3f} × (1 - e<sup>-{b:.4f}t</sup>)"
                
            elif curve_type == 'power':
                # Fit power law: Q = a * t^b - NEW FORMAT
                # Use log-log transformation: log(Q) = log(a) + b*log(t)
                valid_data = combined_data[(combined_data['normalized_level'] > 0) & (combined_data['time_days'] > 0)]
                x = np.log(valid_data['time_days'].values)
                y = np.log(valid_data['normalized_level'].values)
                
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                
                # For consistency with new format: Q = a * t^b
                a = np.exp(intercept)  # coefficient
                b = slope              # exponent
                r_squared = r_value ** 2
                
                coefficients = {'a': a, 'b': b}
                self.curve_equation_label.setTextFormat(Qt.RichText)
                equation = f"Q = {a:.3f} × t<sup>{b:.3f}</sup>"
                
            else:  # linear
                # Simple linear regression: Q = a - b*t - NEW FORMAT
                valid_data = combined_data[combined_data['normalized_level'] > 0]
                x = valid_data['time_days'].values
                y = valid_data['normalized_level'].values  # Use raw values, not log
                
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                r_squared = r_value ** 2
                
                # For consistency with new format: Q = a - b*t
                a = intercept  # y-intercept
                b = -slope     # negative slope (since we want Q = a - b*t form)
                
                coefficients = {'a': a, 'b': b}
                equation = f"Q = {a:.3f} - {b:.4f} × t"
            
            # Store curve parameters
            self.current_curve = {
                'curve_type': curve_type,
                'curve_coefficients': coefficients,
                'r_squared': r_squared,
                'recession_segments': len(all_data),
                'fitting_data': combined_data
            }
            
            # Update UI
            self.curve_equation_label.setText(equation)
            self.r_squared_label.setText(f"R² = {r_squared:.4f}")
            
            # Curve fitted successfully
            self.calculate_btn.setEnabled(True)
            
            # Update plot
            self.update_plot()
            
            QMessageBox.information(self, "Curve Fitted", 
                f"Successfully fitted {curve_type} curve with R² = {r_squared:.4f}")
            
            # Save session state after successful curve fitting
            if self.session_saving_enabled and self.current_well:
                self.save_current_well_state()
            
        except Exception as e:
            logger.error(f"Error fitting curve: {e}")
            QMessageBox.critical(self, "Error", f"Failed to fit curve: {str(e)}")
    
    def calculate_recharge(self):
        """Calculate recharge using the MRC method."""
        if not self.current_curve:
            QMessageBox.warning(self, "No Curve", "Please select or fit a recession curve first.")
            return
            
        try:
            logger.info("=== STARTING CALCULATE_RECHARGE ===")
            logger.info(f"Current curve type: {self.current_curve.get('curve_type', 'UNKNOWN')}")
            logger.info(f"Current curve keys: {list(self.current_curve.keys())}")
            
            # Get parameters from unified settings
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                settings = self.parent.unified_settings.get_method_settings('MRC')
                specific_yield = settings.get('specific_yield', 0.2)
                deviation_threshold = settings.get('mrc_deviation_threshold', 0.1)
            else:
                # Fallback to default values if unified settings not available
                specific_yield = 0.2
                deviation_threshold = 0.1
                logger.warning("Using default parameters - unified settings not available")
            
            logger.info(f"Parameters (from Global Settings): Specific Yield={specific_yield}, Deviation Threshold={deviation_threshold} ft")
            
            # Get processed data
            logger.info(f"Getting processed_data, type: {type(self.processed_data)}")
            if self.processed_data is None:
                logger.error("ERROR: processed_data is None!")
                QMessageBox.critical(self, "Error", "No processed data available. Please load well data first.")
                return
                
            data = self.processed_data.copy()
            logger.info(f"Data shape: {data.shape}, columns: {list(data.columns)}")
            logger.info(f"Data dtypes: {data.dtypes.to_dict()}")
            
            # Log sample of data before conversion
            if not data.empty and 'water_level' in data.columns:
                logger.info(f"BEFORE conversion - First 3 level values: {data['water_level'].head(3).tolist()}")
                logger.info(f"BEFORE conversion - Level dtype: {data['water_level'].dtype}")
            
            # Ensure water_level column is numeric before calculations
            if 'water_level' in data.columns:
                data['water_level'] = pd.to_numeric(data['water_level'], errors='coerce')
                data = data.dropna(subset=['water_level'])
                logger.info(f"AFTER conversion - Level dtype: {data['water_level'].dtype}")
                logger.info(f"AFTER conversion - First 3 level values: {data['water_level'].head(3).tolist()}")
            
            # Calculate predicted levels based on curve
            curve_type = self.current_curve['curve_type']
            # Handle both old and new curve data formats
            if 'parameters' in self.current_curve:
                params = self.current_curve['parameters']
            else:
                params = self.current_curve.get('curve_coefficients', {})
            
            logger.info(f"=== CURVE INFORMATION ===")
            logger.info(f"Curve type: {curve_type}")
            logger.info(f"Curve parameters: {params}")
            logger.info(f"Curve R²: {self.current_curve.get('r_squared', 'N/A')}")
            
            # Initialize with actual values - ensure numeric types
            logger.info("=== INITIALIZING PREDICTED LEVEL ===")
            data['predicted_level'] = pd.to_numeric(data['water_level'].values, errors='coerce')
            logger.info(f"Predicted level dtype after initialization: {data['predicted_level'].dtype}")
            data['deviation'] = 0.0
            
            # For each recession period, calculate predicted values
            logger.info("=== CALCULATING RECESSION PERIODS ===")
            data['change'] = data['water_level'].diff()
            data['is_recession'] = data['change'] < 0
            data['recession_group'] = (data['is_recession'] != data['is_recession'].shift()).cumsum()
            
            recession_count = 0
            total_recession_groups = len(data[data['is_recession']].groupby('recession_group'))
            logger.info(f"Total recession groups found: {total_recession_groups}")
            
            for group_id, group in data[data['is_recession']].groupby('recession_group'):
                if len(group) > 1:
                    recession_count += 1
                    logger.info(f"Processing recession group {recession_count}/{total_recession_groups}, size: {len(group)}")
                    
                    # Time since start of recession
                    start_time = group['timestamp'].iloc[0]
                    logger.info(f"Group water_level dtype: {group['water_level'].dtype}")
                    logger.info(f"First water_level value: {group['water_level'].iloc[0]}, type: {type(group['water_level'].iloc[0])}")
                    start_level = float(group['water_level'].iloc[0])  # Force to numeric!
                    
                    time_days = (group['timestamp'] - start_time).dt.total_seconds() / 86400
                    
                    if curve_type == 'exponential':
                        # New model: drawdown = Q_max * (1 - exp(-α*t))
                        # So water level = start_level - drawdown
                        a = params.get('a', params.get('Q_max', 1.0))
                        b = params.get('b', params.get('alpha', 0.1))
                        drawdown = a * (1 - np.exp(-b * time_days))
                        predicted = start_level - drawdown
                    elif curve_type == 'power':
                        # New model: drawdown = a * t^β
                        # So water level = start_level - drawdown
                        a = params.get('a', 1.0)
                        b = params.get('b', params.get('beta', 1.0))
                        drawdown = a * np.power(np.maximum(time_days, 0.001), b)
                        predicted = start_level - drawdown
                    else:  # linear
                        # drawdown = a - b*t (but for recession, drawdown increases, so a + b*t)
                        a = params.get('a', 0.0)
                        b = params.get('b', params.get('slope', 0.1))
                        drawdown = b * time_days
                        predicted = start_level - drawdown
                    
                    logger.info(f"Predicted values type: {type(predicted)}, dtype: {predicted.dtype if hasattr(predicted, 'dtype') else 'N/A'}")
                    logger.info(f"Before assignment - predicted_level dtype: {data['predicted_level'].dtype}")
                    data.loc[group.index, 'predicted_level'] = predicted
                    logger.info(f"After assignment - predicted_level dtype: {data['predicted_level'].dtype}")
                    
                    # Show sample of predicted vs actual values for this group
                    if len(group) > 0:
                        logger.info(f"Sample comparison for group {recession_count}:")
                        logger.info(f"  Actual:    {group['water_level'].iloc[:3].tolist()}")
                        logger.info(f"  Predicted: {predicted[:3].tolist() if hasattr(predicted, '__len__') else [predicted]}")
                        logger.info(f"  Difference: {(group['water_level'].iloc[:3] - predicted[:3]).tolist() if hasattr(predicted, '__len__') else [(group['water_level'].iloc[0] - predicted)]}")
            
            # Calculate deviations (positive = recharge)
            # Debug data types to understand the issue
            logger.info(f"Level column dtype: {data['water_level'].dtype}, sample values: {data['water_level'].head().tolist()}")
            logger.info(f"Predicted level column dtype: {data['predicted_level'].dtype}, sample values: {data['predicted_level'].head().tolist()}")
            
            # Force conversion to numeric - this should fix the string subtraction error
            try:
                logger.info("=== ATTEMPTING DEVIATION CALCULATION ===")
                logger.info(f"BEFORE final conversion - Level dtype: {data['water_level'].dtype}")
                logger.info(f"BEFORE final conversion - Predicted dtype: {data['predicted_level'].dtype}")
                
                data['water_level'] = pd.to_numeric(data['water_level'], errors='coerce')
                data['predicted_level'] = pd.to_numeric(data['predicted_level'], errors='coerce')
                
                logger.info(f"AFTER final conversion - Level dtype: {data['water_level'].dtype}")
                logger.info(f"AFTER final conversion - Predicted dtype: {data['predicted_level'].dtype}")
                logger.info(f"Level sample after conversion: {data['water_level'].head(3).tolist()}")
                logger.info(f"Predicted sample after conversion: {data['predicted_level'].head(3).tolist()}")
                
                logger.info("About to calculate deviation...")
                data['deviation'] = data['water_level'] - data['predicted_level']
                logger.info("Successfully calculated deviations!")
            except Exception as e:
                logger.error(f"Error in deviation calculation: {e}")
                logger.error(f"Level sample: {data['water_level'].iloc[0] if not data.empty else 'EMPTY'} (type: {type(data['water_level'].iloc[0]) if not data.empty else 'N/A'})")
                logger.error(f"Predicted sample: {data['predicted_level'].iloc[0] if not data.empty else 'EMPTY'} (type: {type(data['predicted_level'].iloc[0]) if not data.empty else 'N/A'})")
                raise
            
            # Add detailed debugging for deviation analysis
            logger.info("=== DEVIATION ANALYSIS ===")
            logger.info(f"Deviation threshold: {deviation_threshold} ft")
            logger.info(f"Deviation statistics:")
            logger.info(f"  Min: {data['deviation'].min():.4f} ft")
            logger.info(f"  Max: {data['deviation'].max():.4f} ft")
            logger.info(f"  Mean: {data['deviation'].mean():.4f} ft")
            logger.info(f"  Std: {data['deviation'].std():.4f} ft")
            logger.info(f"  Total data points: {len(data)}")
            
            # Show distribution around threshold
            positive_devs = data[data['deviation'] > 0]
            logger.info(f"  Positive deviations: {len(positive_devs)} points")
            if len(positive_devs) > 0:
                logger.info(f"    Min positive: {positive_devs['deviation'].min():.4f} ft")
                logger.info(f"    Max positive: {positive_devs['deviation'].max():.4f} ft")
            
            # Identify recharge events (deviations above threshold)
            data['is_recharge'] = data['deviation'] > deviation_threshold
            
            # Debug threshold comparison
            above_threshold = (data['deviation'] > deviation_threshold).sum()
            logger.info(f"  Points above threshold ({deviation_threshold} ft): {above_threshold}")
            
            if above_threshold > 0:
                recharge_candidates = data[data['deviation'] > deviation_threshold]
                logger.info(f"  Recharge event deviations: {recharge_candidates['deviation'].tolist()[:10]}...")  # Show first 10
            else:
                logger.warning(f"  NO POINTS EXCEED THRESHOLD! All deviations are <= {deviation_threshold} ft")
                logger.warning(f"  Suggested threshold: Try {max(0.001, data['deviation'].max() * 0.5):.4f} ft")
                
                # Show some examples near the threshold
                if len(positive_devs) > 0:
                    near_threshold = positive_devs.nlargest(5, 'deviation')['deviation']
                    logger.warning(f"  Largest positive deviations: {near_threshold.tolist()}")
            
            # Calculate recharge
            data['recharge'] = 0.0
            data.loc[data['is_recharge'], 'recharge'] = data.loc[data['is_recharge'], 'deviation'] * specific_yield * 12  # Convert to inches
            
            # Identify water years
            data['water_year'] = data['timestamp'].apply(self.get_water_year)
            
            # Create recharge events
            self.recharge_events = []
            recharge_data = data[data['is_recharge']]
            
            for idx, row in recharge_data.iterrows():
                event = {
                    'event_date': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                    'water_year': str(row['water_year']),
                    'water_level': float(row['water_level']),
                    'predicted_level': float(row['predicted_level']),
                    'deviation': float(row['deviation']),
                    'recharge_value': float(row['recharge'])
                }
                self.recharge_events.append(event)
            
            # Calculate summaries
            total_recharge = sum(e['recharge_value'] for e in self.recharge_events)
            
            if len(self.recharge_events) > 0:
                try:
                    # Parse string dates back to datetime objects for calculation
                    from datetime import datetime
                    first_date_str = min(e['event_date'] for e in self.recharge_events)
                    last_date_str = max(e['event_date'] for e in self.recharge_events)
                    
                    # Parse ISO format dates - handle both with and without timezone
                    try:
                        first_date = datetime.fromisoformat(first_date_str.replace('Z', '+00:00'))
                        last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
                    except:
                        # Fallback for simpler date formats
                        first_date = pd.to_datetime(first_date_str)
                        last_date = pd.to_datetime(last_date_str)
                    
                    days_span = (last_date - first_date).total_seconds() / (24 * 3600)
                    annual_rate = total_recharge * 365 / days_span if days_span > 0 else 0
                except Exception as e:
                    logger.error(f"Error calculating annual rate: {e}")
                    annual_rate = 0
            else:
                annual_rate = 0
            
            # Update results
            self.total_recharge_label.setText(f"{total_recharge:.2f} inches")
            self.annual_rate_label.setText(f"{annual_rate:.2f} inches/year")
            self.events_count_label.setText(str(len(self.recharge_events)))
            
            # Final summary logging
            logger.info("=== FINAL CALCULATION SUMMARY ===")
            logger.info(f"Total recharge events found: {len(self.recharge_events)}")
            logger.info(f"Total recharge amount: {total_recharge:.4f} inches")
            logger.info(f"Annual rate: {annual_rate:.4f} inches/year")
            logger.info(f"Recession groups processed: {recession_count}")
            logger.info(f"Deviation threshold used: {deviation_threshold} ft")
            logger.info(f"Specific yield used: {specific_yield}")
            
            if len(self.recharge_events) == 0:
                logger.error("🚨 ZERO RECHARGE EVENTS DETECTED!")
                logger.error("This indicates one of these issues:")
                logger.error("1. Deviation threshold too high - no deviations exceed threshold")
                logger.error("2. Curve fitting too tight - predicted levels match actual too closely")
                logger.error("3. All deviations are negative - recession curve is above actual data")
                logger.error("Check the deviation analysis above to diagnose the specific cause.")
            
            logger.info("=== END CALCULATION SUMMARY ===")
            
            # Update yearly stats
            self.update_yearly_stats()
            
            # Store calculation data
            self.calculation_data = data
            
            # Switch to results tab
            self.left_tabs.setCurrentIndex(3)
            
            # Update plot
            self.update_plot()
            
            QMessageBox.information(self, "Calculation Complete", 
                f"Found {len(self.recharge_events)} recharge events\n"
                f"Total recharge: {total_recharge:.2f} inches")
            
            # Save session state after successful recharge calculation
            if self.session_saving_enabled and self.current_well:
                self.save_current_well_state()
            
        except Exception as e:
            import traceback
            logger.error(f"Error calculating recharge: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to calculate recharge: {str(e)}")
    
    def update_yearly_stats(self):
        """Update the yearly statistics table."""
        if not self.recharge_events:
            return
            
        from datetime import datetime
            
        # Group by water year
        yearly_stats = {}
        for event in self.recharge_events:
            wy = event['water_year']
            if wy not in yearly_stats:
                yearly_stats[wy] = {
                    'events': 0,
                    'recharge': 0.0,
                    'max_deviation': 0.0,
                    'dates': []
                }
            yearly_stats[wy]['events'] += 1
            yearly_stats[wy]['recharge'] += event['recharge_value']
            yearly_stats[wy]['max_deviation'] = max(yearly_stats[wy]['max_deviation'], event['deviation'])
            yearly_stats[wy]['dates'].append(event['event_date'])
        
        # Update table
        self.yearly_stats_table.setRowCount(len(yearly_stats))
        
        row = 0
        for wy, stats in sorted(yearly_stats.items()):
            # Water year
            self.yearly_stats_table.setItem(row, 0, QTableWidgetItem(wy))
            
            # Events
            self.yearly_stats_table.setItem(row, 1, QTableWidgetItem(str(stats['events'])))
            
            # Recharge
            self.yearly_stats_table.setItem(row, 2, QTableWidgetItem(f"{stats['recharge']:.2f}"))
            
            # Annual rate
            # Convert string dates to datetime for calculation
            date_strings = stats['dates']
            if date_strings:
                try:
                    # Parse dates - they're stored as ISO format strings
                    dates = []
                    for date_str in date_strings:
                        try:
                            # Try ISO format with timezone
                            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            # Fallback to pandas parser
                            date = pd.to_datetime(date_str)
                        dates.append(date)
                    
                    first_date = min(dates)
                    last_date = max(dates)
                    days = (last_date - first_date).total_seconds() / (24 * 3600)
                    rate = stats['recharge'] * 365 / days if days > 0 else stats['recharge'] * 365
                except Exception as e:
                    logger.error(f"Error calculating rate for water year: {e}")
                    rate = stats['recharge'] * 365  # Default to annual total
            else:
                rate = stats['recharge'] * 365
            self.yearly_stats_table.setItem(row, 3, QTableWidgetItem(f"{rate:.2f}"))
            
            # Max deviation
            self.yearly_stats_table.setItem(row, 4, QTableWidgetItem(f"{stats['max_deviation']:.3f}"))
            
            row += 1
    
    def update_plot(self):
        """Update the plot with current data and MRC-specific elements."""
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
            
            # Use base class for standardized plotting
            ax = self.update_plot_base()
            if ax is None:
                return
                
            # Add MRC-specific plot elements
            self.add_method_specific_plots(ax)
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}", exc_info=True)
    
    def add_method_specific_plots(self, ax):
        """Add MRC-specific plot elements to the base plot."""
        try:
            # Plot recession segments
            if hasattr(self, 'recession_segments') and len(self.recession_segments) > 0:
                for i, segment in enumerate(self.recession_segments):
                    if 'data' in segment and segment['data'] is not None and len(segment['data']) > 0:
                        seg_data = segment['data']
                        label = 'Recession Segments' if i == 0 else ""
                        ax.plot(seg_data['timestamp'], seg_data['water_level'], 
                               'r-', linewidth=2, alpha=0.7, label=label)
            
            # Plot recession curve and deviations (only if data exists and is properly calculated)
            if (hasattr(self, 'show_recession_curve') and self.show_recession_curve.isChecked() and 
                hasattr(self, 'calculation_data') and self.calculation_data is not None):
                
                data = self.calculation_data
                # Only plot if the required columns exist
                if 'timestamp' in data.columns and 'predicted_level' in data.columns:
                    ax.plot(data['timestamp'], data['predicted_level'], 
                           'k--', linewidth=1, label='Recession Curve')
                
                if (hasattr(self, 'show_deviations') and self.show_deviations.isChecked() and 
                    'is_recharge' in data.columns):
                    # Highlight recharge events
                    recharge_data = data[data['is_recharge']]
                    if len(recharge_data) > 0:
                        ax.scatter(recharge_data['timestamp'], recharge_data['water_level'], 
                                 c='blue', s=30, marker='o', edgecolors='darkblue', linewidth=1,
                                 zorder=10, label='Recharge Events', alpha=0.7)
            
            # Update title with MRC-specific information
            current_title = ax.get_title()
            if hasattr(self, 'recharge_events') and self.recharge_events:
                events_count = len(self.recharge_events)
                total_recharge = sum(event['recharge_value'] for event in self.recharge_events)
                current_title += f' ({events_count} events, {total_recharge:.2f}" total)'
                ax.set_title(current_title)
                
        except Exception as e:
            logger.error(f"Error adding MRC-specific plots: {e}", exc_info=True)

    def clear_results(self):
        """Clear all results and reset UI."""
        self.recession_segments = []
        self.recharge_events = []
        self.current_curve = None
        
        self.recession_table.setRowCount(0)
        self.yearly_stats_table.setRowCount(0)
        
        self.total_recharge_label.setText("0.0 inches")
        self.annual_rate_label.setText("0.0 inches/year")
        self.events_count_label.setText("0")
        
        self.curve_equation_label.setText("No curve fitted")
        self.r_squared_label.setText("R² = N/A")
        
        self.fit_curve_btn.setEnabled(False)
        self.calculate_btn.setEnabled(False)
    
    def on_preprocessing_changed(self):
        """Handle changes to preprocessing options."""
        if hasattr(self, 'raw_data') and self.raw_data is not None:
            self.process_data()
            self.update_plot()
    
    def preview_processed_data(self):
        """Preview the processed data."""
        if not hasattr(self, 'raw_data') or self.raw_data is None:
            QMessageBox.warning(self, "No Data", "Please select a well first.")
            return
            
        self.process_data()
        self.update_plot()
        
        QMessageBox.information(self, "Data Preview", 
            f"Original data points: {len(self.raw_data)}\n"
            f"Processed data points: {len(self.processed_data)}")
    
    def export_to_csv(self):
        """Export results to CSV."""
        if not hasattr(self, 'recharge_events') or not self.recharge_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export to CSV", 
                f"{self.well_combo.currentText()}_MRC_results.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # Write CSV file
            with open(file_path, 'w', newline='') as csvfile:
                # Write header information
                csvfile.write(f"# MRC Calculation Results for {self.well_combo.currentText()}\n")
                csvfile.write(f"# Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                csvfile.write(f"# Curve Type: {self.current_curve['curve_type'] if self.current_curve else 'N/A'}\n")
                csvfile.write(f"# Curve R²: {self.current_curve['r_squared']:.4f if self.current_curve else 0}\n")
                csvfile.write(f"# Parameters:\n")
                # Get parameters from global settings
                if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                    settings = self.parent.unified_settings.get_method_settings('MRC')
                    sy = settings.get('specific_yield', 0.2)
                    deviation_threshold = settings.get('mrc_deviation_threshold', 0.1)
                else:
                    sy = 0.2
                    deviation_threshold = 0.1
                    
                csvfile.write(f"#   Specific Yield: {sy}\n")
                csvfile.write(f"#   Deviation Threshold: {deviation_threshold} ft\n")
                csvfile.write(f"# Total Recharge: {self.total_recharge_label.text()}\n")
                csvfile.write(f"# Annual Rate: {self.annual_rate_label.text()}\n")
                csvfile.write("#\n")
                
                # Write data headers and rows
                fieldnames = ['Event_Date', 'Water_Year', 'Water_Level_ft', 'Predicted_Level_ft', 
                             'Deviation_ft', 'Recharge_in']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in self.recharge_events:
                    writer.writerow({
                        'Event_Date': event['event_date'].strftime('%Y-%m-%d'),
                        'Water_Year': event['water_year'],
                        'Water_Level_ft': f"{event['water_level']:.2f}",
                        'Predicted_Level_ft': f"{event['predicted_level']:.2f}",
                        'Deviation_ft': f"{event['deviation']:.3f}",
                        'Recharge_in': f"{event['recharge_value']:.3f}"
                    })
                    
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Results exported successfully to:\n{file_path}"
            )
            logger.info(f"Exported MRC results to CSV: {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Export Error", 
                f"Failed to export to CSV:\n{str(e)}"
            )
    
    def export_to_excel(self):
        """Export results to Excel."""
        if not hasattr(self, 'recharge_events') or not self.recharge_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export to Excel", 
                f"{self.well_combo.currentText()}_MRC_results.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # Create DataFrames for export
            # 1. Recharge events data
            events_data = []
            for event in self.recharge_events:
                events_data.append({
                    'Event Date': event['event_date'],
                    'Water Year': event['water_year'],
                    'Water Level (ft)': event['water_level'],
                    'Predicted Level (ft)': event['predicted_level'],
                    'Deviation (ft)': event['deviation'],
                    'Recharge (in)': event['recharge_value']
                })
            events_df = pd.DataFrame(events_data)
            
            # 2. Yearly summary (from table)
            yearly_data = []
            for row in range(self.yearly_stats_table.rowCount()):
                yearly_data.append({
                    'Water Year': self.yearly_stats_table.item(row, 0).text(),
                    'Number of Events': int(self.yearly_stats_table.item(row, 1).text()),
                    'Total Recharge (in)': float(self.yearly_stats_table.item(row, 2).text()),
                    'Annual Rate (in/yr)': float(self.yearly_stats_table.item(row, 3).text()),
                    'Max Deviation (ft)': float(self.yearly_stats_table.item(row, 4).text())
                })
            yearly_df = pd.DataFrame(yearly_data)
            
            # 3. Parameters and curve info
            params_data = {
                'Parameter': [
                    'Well', 'Curve Type', 'Curve R²', 'Specific Yield', 
                    'Deviation Threshold (ft)', 'Min Recession Length (days)',
                    'Total Recharge (in)', 'Annual Rate (in/yr)', 'Total Events'
                ],
                'Value': [
                    self.well_combo.currentText(),
                    self.current_curve['curve_type'] if self.current_curve else 'N/A',
                    f"{self.current_curve['r_squared']:.4f}" if self.current_curve else 'N/A',
                    self.current_settings.get('specific_yield', 0.2),
                    self.current_settings.get('mrc_deviation_threshold', 0.1),
                    self.current_settings.get('min_recession_length', 7),
                    float(self.total_recharge_label.text().split()[0]),
                    float(self.annual_rate_label.text().split()[0]),
                    len(self.recharge_events)
                ]
            }
            params_df = pd.DataFrame(params_data)
            
            # 4. Recession segments (if available)
            if hasattr(self, 'recession_segments') and self.recession_segments:
                segments_data = []
                for segment in self.recession_segments:
                    segments_data.append({
                        'Start Date': segment['start_date'],
                        'End Date': segment['end_date'],
                        'Duration (days)': segment['duration_days'],
                        'Start Level (ft)': segment['start_level'],
                        'End Level (ft)': segment['end_level'],
                        'Recession Rate (ft/day)': segment['recession_rate']
                    })
                segments_df = pd.DataFrame(segments_data)
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Write parameters
                params_df.to_excel(writer, sheet_name='Parameters', index=False)
                
                # Write yearly summary
                yearly_df.to_excel(writer, sheet_name='Yearly Summary', index=False)
                
                # Write individual events
                events_df.to_excel(writer, sheet_name='Recharge Events', index=False)
                
                # Write recession segments if available
                if hasattr(self, 'recession_segments') and self.recession_segments:
                    segments_df.to_excel(writer, sheet_name='Recession Segments', index=False)
                
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
                f"- Recharge Events sheet\n"
                f"- Recession Segments sheet"
            )
            logger.info(f"Exported MRC results to Excel: {file_path}")
            
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
        """Save calculation to database."""
        if not hasattr(self, 'recharge_events') or not self.recharge_events:
            QMessageBox.warning(self, "No Data", "No results to save. Calculate recharge first.")
            return
            
        # Get database connection for this thread
        mrc_db = self.get_mrc_database()
        if not mrc_db:
            QMessageBox.warning(self, "Database Error", "Database connection not available.")
            return
            
        if not self.current_curve:
            QMessageBox.warning(self, "No Curve", "No curve selected or fitted.")
            return
            
        try:
            # Get curve ID - either from loaded curve or need to save current curve first
            curve_id = None
            if 'id' in self.current_curve:
                curve_id = self.current_curve['id']
            else:
                # Ask user if they want to save the curve first
                reply = QMessageBox.question(
                    self, 
                    "Save Curve", 
                    "The current curve has not been saved. Would you like to save it first?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.save_curve()
                    # Curve should now be saved, get the ID from current_curve
                    curve_id = self.current_curve.get('id') if hasattr(self, 'current_curve') and self.current_curve else None
                    if not curve_id:
                        # Fallback to combo box
                        curve_id = self.curve_combo.currentData()
                else:
                    return
            
            if not curve_id:
                QMessageBox.warning(self, "No Curve ID", "Failed to get curve ID.")
                return
            
            # Prepare yearly summaries
            yearly_summaries = []
            for row in range(self.yearly_stats_table.rowCount()):
                yearly_summaries.append({
                    'water_year': self.yearly_stats_table.item(row, 0).text(),
                    'num_events': int(self.yearly_stats_table.item(row, 1).text()),
                    'total_recharge': float(self.yearly_stats_table.item(row, 2).text()),
                    'annual_rate': float(self.yearly_stats_table.item(row, 3).text()),
                    'max_deviation': float(self.yearly_stats_table.item(row, 4).text())
                })
            
            # Get total recharge and annual rate
            total_recharge = float(self.total_recharge_label.text().split()[0])
            annual_rate = float(self.annual_rate_label.text().split()[0])
            
            # Get parameters from global settings
            if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
                settings = self.parent.unified_settings.get_method_settings('MRC')
            else:
                # Fallback to defaults if unified settings not available
                settings = {
                    'specific_yield': 0.2,
                    'mrc_deviation_threshold': 0.1,
                    'water_year_month': 10,
                    'water_year_day': 1,
                    'downsample_frequency': 'None',
                    'downsample_method': 'Mean',
                    'enable_smoothing': False,
                    'smoothing_window': 3
                }
            
            # Save calculation
            calc_id = mrc_db.save_calculation(
                curve_id=curve_id,
                well_number=self.current_well,
                well_name=self.well_combo.currentText(),
                specific_yield=settings.get('specific_yield', 0.2),
                deviation_threshold=settings.get('mrc_deviation_threshold', 0.1),
                water_year_start_month=settings.get('water_year_month', 10),
                water_year_start_day=settings.get('water_year_day', 1),
                downsample_rule=settings.get('downsample_frequency', 'None'),
                downsample_method=settings.get('downsample_method', 'Mean') if settings.get('downsample_frequency') != "None" else None,
                filter_type='moving_average' if settings.get('enable_smoothing', False) else 'none',
                filter_window=settings.get('smoothing_window', 3) if settings.get('enable_smoothing', False) else None,
                total_recharge=total_recharge,
                annual_rate=annual_rate,
                recharge_events=self.recharge_events,
                yearly_summaries=yearly_summaries
            )
            
            if calc_id:
                QMessageBox.information(
                    self, 
                    "Save Successful", 
                    f"MRC calculation saved successfully for {self.well_combo.currentText()}.\n\n"
                    f"Total recharge: {total_recharge:.2f} inches\n"
                    f"Annual rate: {annual_rate:.2f} inches/year\n"
                    f"Number of events: {len(self.recharge_events)}"
                )
                logger.info(f"Saved MRC calculation {calc_id} for well {self.current_well}")
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
        """Load calculation from database."""
        # Get database connection for this thread
        mrc_db = self.get_mrc_database()
        if not mrc_db:
            QMessageBox.warning(self, "Database Error", "Database connection not available.")
            return
            
        if not self.current_well:
            QMessageBox.warning(self, "No Well", "Please select a well first.")
            return
            
        try:
            # Get all curves for this well first
            curves = self.mrc_db.get_curves_for_well(self.current_well)
            
            if not curves:
                QMessageBox.information(
                    self, 
                    "No Curves", 
                    f"No saved curves found for {self.well_combo.currentText()}.\n"
                    f"Please create and save a curve first."
                )
                return
            
            # Create dialog to select calculation
            dialog = LoadMrcCalculationDialog(curves, self.mrc_db, self)
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
            calc_data = self.mrc_db.get_calculation_details(calculation_id)
            
            if not calc_data:
                QMessageBox.warning(self, "Load Error", "Could not load calculation details.")
                return
                
            # Load parameters - update internal settings since we're using global settings now
            # Note: Since we're using global settings now, we should update them
            # and inform the user that settings have been updated
            
            loaded_settings = {
                'specific_yield': calc_data.get('specific_yield', 0.2),
                'mrc_deviation_threshold': calc_data.get('deviation_threshold', 0.1),
                'water_year_month': calc_data.get('water_year_start_month', 10),
                'water_year_day': calc_data.get('water_year_start_day', 1),
                'downsample_frequency': calc_data.get('downsample_rule', 'None'),
                'downsample_method': calc_data.get('downsample_method', 'Mean'),
                'enable_smoothing': calc_data.get('filter_type') == 'moving_average',
                'smoothing_window': calc_data.get('filter_window', 3) if calc_data.get('filter_type') == 'moving_average' else 3
            }
            
            # Update current settings with loaded values (for internal use)
            if hasattr(self, 'current_settings'):
                self.current_settings.update(loaded_settings)
            else:
                self.current_settings = loaded_settings
            
            logger.info(f"Loaded MRC calculation parameters: {loaded_settings}")
            
            # Load the curve
            curve_id = calc_data['curve_id']
            for i in range(self.curve_combo.count()):
                if self.curve_combo.itemData(i) == curve_id:
                    self.curve_combo.setCurrentIndex(i)
                    break
            
            # Convert recharge events from database format
            self.recharge_events = []
            for event in calc_data['recharge_events']:
                self.recharge_events.append({
                    'event_date': pd.to_datetime(event['event_date']),
                    'water_year': event['water_year'],
                    'water_level': event['water_level'],
                    'predicted_level': event['predicted_level'],
                    'deviation': event['deviation'],
                    'recharge_value': event['recharge_value']
                })
            
            # Update results
            self.total_recharge_label.setText(f"{calc_data['total_recharge']:.2f} inches")
            self.annual_rate_label.setText(f"{calc_data['annual_rate']:.2f} inches/year")
            self.events_count_label.setText(str(len(self.recharge_events)))
            
            # Update yearly stats table
            self.update_yearly_stats()
            
            # Update the plot
            self.update_plot()
            
            # Switch to Results tab
            self.left_tabs.setCurrentIndex(3)
            
            QMessageBox.information(
                self, 
                "Load Successful", 
                f"Loaded MRC calculation from {calc_data['calculation_date']}\n\n"
                f"Total recharge: {calc_data['total_recharge']:.2f} inches\n"
                f"Annual rate: {calc_data['annual_rate']:.2f} inches/year\n"
                f"Number of events: {len(self.recharge_events)}"
            )
            
            logger.info(f"Loaded MRC calculation {calculation_id} for well {self.current_well}")
            
        except Exception as e:
            logger.error(f"Error loading calculation: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Load Error", 
                f"Failed to load calculation:\n{str(e)}"
            )
    
    def compare_calculations(self):
        """Compare multiple calculations."""
        # Get database connection for this thread
        mrc_db = self.get_mrc_database()
        if not mrc_db:
            QMessageBox.warning(self, "Database Error", "Database connection not available.")
            return
            
        if not self.current_well:
            QMessageBox.warning(self, "No Well", "Please select a well first.")
            return
            
        try:
            # Get all curves for this well
            curves = self.mrc_db.get_curves_for_well(self.current_well)
            
            if not curves or len(curves) < 2:
                QMessageBox.information(
                    self, 
                    "Insufficient Data", 
                    f"Need at least 2 saved curves to compare calculations.\n"
                    f"Found {len(curves) if curves else 0} curve(s) for {self.well_combo.currentText()}."
                )
                return
                
            # Create comparison dialog
            dialog = CompareMrcCalculationsDialog(curves, self.mrc_db, self)
            dialog.exec_()
                    
        except Exception as e:
            logger.error(f"Error in compare_calculations: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Comparison Error", 
                f"An error occurred while comparing:\n{str(e)}"
            )
    
    def _perform_data_quality_checks(self, data):
        """Perform USGS-recommended data quality checks."""
        warnings = []
        
        # Check for data gaps
        if 'timestamp' in data.columns and len(data) > 1:
            time_diffs = data['timestamp'].diff().dropna()
            median_interval = time_diffs.median()
            
            # Find gaps > 1 day
            gaps = time_diffs[time_diffs > pd.Timedelta(days=1)]
            if len(gaps) > 0:
                warnings.append(f"Found {len(gaps)} data gaps > 1 day")
            
            # Check if data frequency is at least daily
            if median_interval > pd.Timedelta(days=1):
                warnings.append(f"Data frequency ({median_interval}) is less than daily")
        
        # Check for negative or zero water levels
        if 'water_level' in data.columns:
            negative_levels = data[data['water_level'] <= 0]
            if len(negative_levels) > 0:
                warnings.append(f"Found {len(negative_levels)} non-positive water levels")
        
        # Show warnings if any
        if warnings:
            warning_msg = "Data Quality Issues:\n\n" + "\n".join(f"• {w}" for w in warnings)
            warning_msg += "\n\nContinue with analysis?"
            
            reply = QMessageBox.question(
                self, "Data Quality Warning", warning_msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.No:
                raise ValueError("Data quality check failed")
    
    
    def manage_recession_segments(self):
        """Open dialog to manage recession segment selection."""
        if not hasattr(self, 'recession_segments') or not self.recession_segments:
            QMessageBox.warning(self, "No Segments", 
                              "No recession segments available. Please identify segments first.")
            return
            
        try:
            # Create segment management dialog
            dialog = ManageSegmentsDialog(self.recession_segments, self)
            if dialog.exec_() == QDialog.Accepted:
                # Get selected segments
                selected_segments = dialog.get_selected_segment_indices()
                
                # Update internal storage with selection
                for i, segment in enumerate(self.recession_segments):
                    segment['selected'] = i in selected_segments
                
                # Enable curve fitting if any segments are selected
                selected_count = len(selected_segments)
                self.fit_curve_btn.setEnabled(selected_count > 0)
                
                # Update status
                self.update_segments_status()
                
                # Save segment selections to database if requested
                if dialog.save_selections:
                    self.save_segment_selections()
                
                logger.info(f"Updated segment selection: {selected_count} segments selected")
                
        except Exception as e:
            logger.error(f"Error managing segments: {e}")
            QMessageBox.critical(self, "Management Error", f"Failed to manage segments: {str(e)}")
    
    def update_segments_status(self):
        """Update the segments status label."""
        if not hasattr(self, 'recession_segments') or not self.recession_segments:
            self.segments_status_label.setText("No recession segments identified")
            self.segments_status_label.setStyleSheet("color: #666; font-style: italic; margin: 5px;")
            return
            
        total_segments = len(self.recession_segments)
        selected_segments = len([s for s in self.recession_segments if s.get('selected', True)])
        
        if selected_segments == total_segments:
            status_text = f"✅ {total_segments} segments identified (all selected)"
            color = "#28a745"  # green
        elif selected_segments > 0:
            status_text = f"⚠️ {selected_segments} of {total_segments} segments selected"
            color = "#ffc107"  # yellow
        else:
            status_text = f"❌ {total_segments} segments identified (none selected)"
            color = "#dc3545"  # red
            
        self.segments_status_label.setText(status_text)
        self.segments_status_label.setStyleSheet(f"color: {color}; font-weight: bold; margin: 5px;")
    
    def check_for_saved_segments(self, well_id):
        """Check if there are saved segments for the current well and enable load button."""
        try:
            if not well_id:
                self.load_segments_btn.setEnabled(False)
                return
                
            mrc_db = self.get_mrc_database()
            if not mrc_db:
                self.load_segments_btn.setEnabled(False)
                return
                
            with mrc_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count FROM mrc_recession_segments 
                    WHERE well_number = ?
                ''', (well_id,))
                
                result = cursor.fetchone()
                has_saved_segments = result['count'] > 0
                
            self.load_segments_btn.setEnabled(has_saved_segments)
            self.clear_segments_btn.setEnabled(has_saved_segments)
            
            if has_saved_segments:
                self.load_segments_btn.setToolTip(f"Load {result['count']} saved recession segments")
                self.clear_segments_btn.setToolTip(f"Clear {result['count']} saved recession segments")
            else:
                self.load_segments_btn.setToolTip("No saved segments available for this well")
                self.clear_segments_btn.setToolTip("No saved segments to clear")
                
        except Exception as e:
            logger.error(f"Error checking for saved segments: {e}")
            self.load_segments_btn.setEnabled(False)
            self.clear_segments_btn.setEnabled(False)
    
    def save_segment_selections(self):
        """Save current segment selections to database."""
        if not hasattr(self, 'recession_segments') or not self.recession_segments:
            return
            
        try:
            mrc_db = self.get_mrc_database()
            if not mrc_db:
                return
                
            with mrc_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear existing segments for this well
                cursor.execute('DELETE FROM mrc_recession_segments WHERE well_number = ?', 
                             (self.current_well,))
                
                # Save current segments with selections
                for segment in self.recession_segments:
                    # Handle DataFrame data properly (same as in database save method)
                    data = segment.get('data')
                    if data is not None and hasattr(data, 'to_dict'):
                        # Convert DataFrame to dictionary format that can be reconstructed
                        # Handle datetime columns properly
                        data_copy = data.copy()
                        for col in data_copy.columns:
                            if data_copy[col].dtype.name.startswith('datetime'):
                                data_copy[col] = data_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                        segment_data_json = json.dumps(data_copy.to_dict('records'))
                    else:
                        segment_data_json = json.dumps(data) if data else None
                    
                    cursor.execute('''
                        INSERT INTO mrc_recession_segments 
                        (well_number, start_date, end_date, duration_days, recession_rate, 
                         segment_data, selected, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        self.current_well,
                        segment['start_date'].isoformat(),
                        segment['end_date'].isoformat(), 
                        segment['duration_days'],
                        segment.get('recession_rate', segment.get('avg_decline_rate', 0.0)),
                        segment_data_json,
                        segment.get('selected', True),
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                logger.info(f"Saved {len(self.recession_segments)} recession segments to database")
                
        except Exception as e:
            logger.error(f"Error saving segment selections: {e}")
    
    def load_segments_from_data(self, segments_data):
        """Load recession segments from database data."""
        try:
            self.recession_segments = []
            skipped_segments = 0
            
            for segment_row in segments_data:
                # Get segment data (already parsed by database method)
                segment_data = segment_row['segment_data']
                if segment_data is None:
                    logger.warning(f"Segment data is None for segment starting {segment_row.get('start_date', 'unknown date')}")
                    skipped_segments += 1
                    continue
                
                # Create DataFrame from the stored data
                # Data should be a list of records (dictionaries)
                try:
                    if isinstance(segment_data, list):
                        segment_df = pd.DataFrame(segment_data)
                    elif isinstance(segment_data, dict):
                        segment_df = pd.DataFrame([segment_data])
                    elif isinstance(segment_data, str):
                        # Try to parse as JSON (fallback for old format)
                        try:
                            parsed_data = json.loads(segment_data)
                            if isinstance(parsed_data, list):
                                segment_df = pd.DataFrame(parsed_data)
                            else:
                                segment_df = pd.DataFrame([parsed_data])
                        except json.JSONDecodeError:
                            logger.warning(f"Cannot parse string segment_data as JSON, skipping segment")
                            continue
                    else:
                        logger.warning(f"Unexpected segment_data format: {type(segment_data)}")
                        continue
                    
                    # Ensure timestamp column is properly formatted
                    if 'timestamp' in segment_df.columns:
                        try:
                            segment_df['timestamp'] = pd.to_datetime(segment_df['timestamp'])
                        except Exception as e:
                            logger.warning(f"Could not convert timestamp data: {e}")
                            # Skip this segment if timestamp conversion fails
                            continue
                    
                except Exception as e:
                    logger.error(f"Failed to create DataFrame from segment data: {e}")
                    continue
                
                # Recreate segment object
                # Handle both old and new column names
                decline_rate = segment_row.get('avg_decline_rate', segment_row.get('recession_rate', 0.0))
                
                # Calculate start_level and end_level from the segment data
                start_level = segment_df['water_level'].iloc[0] if len(segment_df) > 0 and 'water_level' in segment_df.columns else 0.0
                end_level = segment_df['water_level'].iloc[-1] if len(segment_df) > 0 and 'water_level' in segment_df.columns else 0.0
                
                segment = {
                    'start_date': pd.to_datetime(segment_row['start_date']),
                    'end_date': pd.to_datetime(segment_row['end_date']),
                    'duration_days': segment_row['duration_days'],
                    'start_level': start_level,
                    'end_level': end_level,
                    'avg_decline_rate': decline_rate,
                    'recession_rate': decline_rate,  # Include both for compatibility
                    'data': segment_df,
                    'selected': bool(segment_row.get('selected', True))
                }
                
                self.recession_segments.append(segment)
                
            total_segments = len(self.recession_segments) + skipped_segments
            if skipped_segments > 0:
                logger.warning(f"Loaded {len(self.recession_segments)} recession segments from database, skipped {skipped_segments} segments with missing data")
            else:
                logger.info(f"Loaded {len(self.recession_segments)} recession segments from database")
            
        except Exception as e:
            logger.error(f"Error loading segments from data: {e}")
            raise
    
    def get_water_year(self, date):
        """Get water year for a given date."""
        # Get water year settings from unified settings
        if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'unified_settings') and self.parent.unified_settings:
            settings = self.parent.unified_settings.get_method_settings('MRC')
            month = settings.get('water_year_month', 10)
            day = settings.get('water_year_day', 1)
        else:
            # Fallback to default values
            month = 10
            day = 1
        
        if (date.month > month) or (date.month == month and date.day >= day):
            start_year = date.year
        else:
            start_year = date.year - 1
            
        end_year = start_year + 1
        return f"{start_year}-{end_year}"
    
    def get_selected_segments(self):
        """Get the selected segments data from the recession table."""
        selected = []
        if hasattr(self, 'recession_table') and hasattr(self, 'recession_segments'):
            for row in range(self.recession_table.rowCount()):
                checkbox = self.recession_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    if row < len(self.recession_segments):
                        selected.append(self.recession_segments[row])
        return selected
    
    def on_curve_type_changed(self):
        """Update preview information when segments change."""
        try:
            selected_segments = self.get_selected_segments()
            
            if len(selected_segments) == 0:
                self.fitting_preview_label.setText("💡 Select segments above, then click 'Fit Interactive Curve' to start fitting process")
                return
                
            # Show segment count and readiness
            self.fitting_preview_label.setText(
                f"✅ {len(selected_segments)} segments selected. Ready for interactive curve fitting. "
                f"Click 'Fit Interactive Curve' to choose curve type and see fitting results."
            )
            
        except Exception as e:
            logger.error(f"Error updating curve preview: {e}")
    
    def open_interactive_curve_fitting(self):
        """Open the enhanced interactive curve fitting dialog."""
        selected_segments = self.get_selected_segments()
        
        if len(selected_segments) == 0:
            QMessageBox.warning(self, "No Segments Selected", 
                              "Please select at least one recession segment to fit a curve.")
            return
            
        try:
            # Check if we're modifying an existing curve
            existing_curve = None
            if self.current_curve and hasattr(self, 'curve_combo') and self.curve_combo.currentData() != "current":
                # We're modifying a loaded curve
                existing_curve = self.current_curve
            
            # Get database connection
            mrc_db = self.get_mrc_database() if hasattr(self, 'mrc_db') else None
            
            # Create enhanced interactive curve fitting dialog
            fitting_dialog = InteractiveCurveFittingDialog(
                segments=selected_segments, 
                curve_type="exponential" if not existing_curve else None,  # Use existing curve type if available
                parent=self,
                existing_curve=existing_curve,
                mrc_db=mrc_db,
                well_id=self.current_well
            )
            
            # Show the dialog
            if fitting_dialog.exec_() == QDialog.Accepted:
                # Get the fitted curve data
                self.current_curve = fitting_dialog.get_curve_data()
                
                if self.current_curve:
                    # Update curve info display
                    curve_info = f"✅ {self.current_curve['curve_type'].title()} curve fitted"
                    self.curve_info_label.setText(curve_info)
                    self.curve_info_label.setStyleSheet("color: #28a745; font-weight: bold; margin: 5px; font-size: 11px;")
                    
                    # Update curve equation and R² labels
                    curve_type = self.current_curve['curve_type']
                    params = self.current_curve['parameters']
                    
                    # Format equation based on curve type
                    self.curve_equation_label.setTextFormat(Qt.RichText)
                    if curve_type == 'exponential':
                        equation = f"Q = {params['a']:.3f} × (1 - e<sup>-{params['b']:.4f}t</sup>)"
                    elif curve_type == 'power':
                        equation = f"Q = {params['a']:.3f} × t<sup>{params['b']:.3f}</sup>"
                    else:  # linear
                        equation = f"Q = {params['a']:.3f} - {params['b']:.4f} × t"
                    self.curve_equation_label.setText(equation)
                    
                    # Update R² label
                    self.r_squared_label.setText(f"R² = {self.current_curve.get('r_squared', 0):.4f}")
                    
                    # Update dropdown to show current fitted curve
                    self.curve_combo.blockSignals(True)  # Prevent triggering on_curve_selected
                    if self.curve_combo.count() == 1:  # Only "No curve selected"
                        self.curve_combo.addItem("Current fitted curve (unsaved)", "current")
                    else:
                        # Update the text if it exists
                        for i in range(self.curve_combo.count()):
                            if self.curve_combo.itemData(i) == "current":
                                self.curve_combo.setItemText(i, "Current fitted curve (unsaved)")
                                break
                        else:
                            self.curve_combo.addItem("Current fitted curve (unsaved)", "current")
                    
                    # Select the current fitted curve
                    current_index = self.curve_combo.findData("current")
                    if current_index >= 0:
                        self.curve_combo.setCurrentIndex(current_index)
                    self.curve_combo.blockSignals(False)
                    
                    # Enable calculate button
                    self.calculate_btn.setEnabled(True)
                    
                    # Update plot to show fitted curve
                    self.update_plot()
                    
                    logger.info(f"Interactive curve fitting completed: {self.current_curve['curve_type']} curve with R² = {self.current_curve.get('r_squared', 0):.3f}")
                else:
                    QMessageBox.warning(self, "Fitting Failed", "Curve fitting was not successful.")
                    
        except Exception as e:
            logger.error(f"Error in interactive curve fitting: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open curve fitting dialog: {str(e)}")
    
    def set_shared_data(self, raw_data, processed_data):
        """Set data that has been preprocessed centrally.
        
        Args:
            raw_data: The raw data DataFrame
            processed_data: The preprocessed data DataFrame
        """
        logger.info(f"MRC receiving shared data: {len(raw_data) if raw_data is not None else 0} raw, {len(processed_data) if processed_data is not None else 0} processed")
        
        self.raw_data = raw_data
        self.processed_data = processed_data
        self.display_data = raw_data  # For backward compatibility
        
        # Mark data as loaded
        self.data_loaded = {'display': True, 'full': True}
        
        # Update plot with new data
        self.update_plot()
        
        logger.info("MRC tab updated with shared data")
    
    def update_settings(self, settings):
        """Update MRC tab with unified settings."""
        try:
            logger.info("Updating MRC tab with unified settings")
            logger.info(f"[SETTINGS_DEBUG] Received settings: {settings}")
            
            # Store settings internally since we don't have UI controls
            if hasattr(self, 'current_settings'):
                old_min_length = self.current_settings.get('min_recession_length', 10)
                self.current_settings.update(settings)
                new_min_length = self.current_settings.get('min_recession_length', 10)
                logger.info(f"[SETTINGS_DEBUG] Min recession length changed from {old_min_length} to {new_min_length}")
            else:
                self.current_settings = settings.copy()
                logger.info(f"[SETTINGS_DEBUG] Initial settings stored")
            
            # Log the key values that affect recession identification
            min_recession = self.current_settings.get('min_recession_length', 10)
            fluctuation_tol = self.current_settings.get('fluctuation_tolerance', 0.01)
            logger.info(f"Updated MRC tab settings: {list(settings.keys())}")
            logger.info(f"Key recession parameters - Min Length: {min_recession} days, Fluctuation Tolerance: {fluctuation_tol} ft")
            
            # Note: Data preprocessing is now handled centrally in RechargeTab
            # The parent will call set_shared_data() with updated processed data
            
            logger.info("MRC tab settings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating MRC tab settings: {e}")
    
    def get_current_settings(self):
        """Get current MRC tab settings."""
        try:
            # Default settings
            default_settings = {
                'specific_yield': 0.2,
                'mrc_deviation_threshold': 0.1,
                'water_year_month': 10,
                'water_year_day': 1,
                'downsample_frequency': 'None',
                'downsample_method': 'Mean',
                'enable_smoothing': False,
                'smoothing_window': 3,
                'min_recession_length': 7,
                'fluctuation_tolerance': 0.02,
                'use_precipitation': False,
                'precip_threshold': 0.1,
                'precip_lag': 2
            }
            
            # Return current settings from internal storage, fall back to defaults
            if hasattr(self, 'current_settings') and self.current_settings:
                # Merge with defaults to ensure all keys are present
                result = default_settings.copy()
                result.update(self.current_settings)
                return result
            else:
                return default_settings
            
        except Exception as e:
            logger.error(f"Error getting MRC tab settings: {e}")
            # Return defaults on error
            return {
                'specific_yield': 0.2,
                'mrc_deviation_threshold': 0.1,
                'water_year_month': 10,
                'water_year_day': 1,
                'downsample_frequency': 'None',
                'downsample_method': 'Mean',
                'enable_smoothing': False,
                'smoothing_window': 3,
                'min_recession_length': 7,
                'fluctuation_tolerance': 0.02,
                'use_precipitation': False,
                'precip_threshold': 0.1,
                'precip_lag': 2
            }
    
    def save_current_well_state(self):
        """Save the current well's session state for later restoration."""
        if not self.current_well:
            return
            
        try:
            # Capture current UI state
            state = {
                # Current selections and data
                'selected_curve_id': self.curve_combo.currentData(),
                'selected_segment_curve_id': self.segments_combo.currentData(),
                'recession_segments': self.recession_segments.copy() if self.recession_segments else [],
                'current_curve': self.current_curve.copy() if self.current_curve else None,
                'recharge_events': self.recharge_events.copy() if self.recharge_events else [],
                
                # Data state
                'raw_data': self.raw_data.copy() if self.raw_data is not None else None,
                'processed_data': self.processed_data.copy() if self.processed_data is not None else None,
                'display_data': self.display_data.copy() if self.display_data is not None else None,
                'calculation_data': self.calculation_data.copy() if self.calculation_data is not None else None,
                'data_loaded': self.data_loaded.copy(),
                
                # Settings
                'current_settings': self.current_settings.copy(),
                'selected_water_year': self.selected_water_year,
                'water_years': self.water_years.copy() if self.water_years else [],
                
                # UI state
                'curve_info_visible': hasattr(self, 'curve_info_frame') and self.curve_info_frame.isVisible(),
                'results_visible': hasattr(self, 'results_frame') and self.results_frame.isVisible()
            }
            
            # Store the state
            self.well_sessions[self.current_well] = state
            logger.info(f"Saved session state for well {self.current_well}")
            
        except Exception as e:
            logger.error(f"Error saving well state for {self.current_well}: {e}")
    
    def restore_well_state(self, well_id):
        """Restore a well's session state."""
        if well_id not in self.well_sessions:
            return
            
        try:
            # Temporarily disable session saving during restoration
            self.session_saving_enabled = False
            
            state = self.well_sessions[well_id]
            
            # Restore data
            self.raw_data = state.get('raw_data')
            self.processed_data = state.get('processed_data')
            self.display_data = state.get('display_data')
            self.calculation_data = state.get('calculation_data')
            self.data_loaded = state.get('data_loaded', {'display': False, 'full': False})
            
            # Restore session variables
            self.recession_segments = state.get('recession_segments', [])
            self.current_curve = state.get('current_curve')
            self.recharge_events = state.get('recharge_events', [])
            self.current_settings = state.get('current_settings', self.current_settings)
            self.selected_water_year = state.get('selected_water_year')
            self.water_years = state.get('water_years', [])
            
            # Load well data if not already loaded
            if well_id not in self.well_data:
                self.load_well_data(well_id)
            
            # Restore UI selections
            # Load curves and segments first
            self.load_curves_for_well(well_id)
            self.load_segments_for_well(well_id)
            
            # Restore curve selection
            selected_curve_id = state.get('selected_curve_id')
            if selected_curve_id:
                for i in range(self.curve_combo.count()):
                    if self.curve_combo.itemData(i) == selected_curve_id:
                        self.curve_combo.setCurrentIndex(i)
                        self.on_curve_selected(i)  # Trigger curve loading
                        break
            
            # Restore segment selection
            selected_segment_curve_id = state.get('selected_segment_curve_id')
            if selected_segment_curve_id:
                for i in range(self.segments_combo.count()):
                    if self.segments_combo.itemData(i) == selected_segment_curve_id:
                        self.segments_combo.setCurrentIndex(i)
                        break
            
            # Update displays
            if self.raw_data is not None or self.display_data is not None:
                self.update_plot()
            
            if self.recession_segments:
                self.update_segments_table()
            
            if self.recharge_events:
                self.update_recharge_table()
            
            # Restore UI visibility states
            if hasattr(self, 'curve_info_frame') and state.get('curve_info_visible', False):
                self.curve_info_frame.setVisible(True)
            
            if hasattr(self, 'results_frame') and state.get('results_visible', False):
                self.results_frame.setVisible(True)
            
            logger.info(f"Restored session state for well {well_id}")
            
        except Exception as e:
            logger.error(f"Error restoring well state for {well_id}: {e}")
            # Fall back to normal loading
            self.clear_results()
            if well_id not in self.well_data:
                self.load_well_data(well_id)
            self.load_curves_for_well(well_id)
            self.load_segments_for_well(well_id)
        finally:
            # Re-enable session saving
            self.session_saving_enabled = True
    
    def save_curve(self):
        """Save the current curve by opening the curve fitting dialog."""
        try:
            if not self.recession_segments:
                QMessageBox.warning(self, "No Data", 
                    "No recession segments available. Please identify segments first.")
                return False
                
            # Open the curve fitting dialog which handles saving
            dialog = InteractiveCurveFittingDialog(
                self.recession_segments,
                parent=self,
                mrc_db=self.mrc_db,
                well_id=self.current_well
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Get the saved curve ID from the dialog
                if hasattr(dialog, 'current_curve') and dialog.current_curve and 'id' in dialog.current_curve:
                    saved_curve_id = dialog.current_curve['id']
                    # Update main tab's current_curve with the saved ID
                    if self.current_curve:
                        self.current_curve['id'] = saved_curve_id
                    else:
                        self.current_curve = {'id': saved_curve_id}
                    logger.info(f"Updated main tab current_curve with saved ID: {saved_curve_id}")
                
                # Reload segments and curves after successful save
                self.load_segments_for_well(self.current_well)
                self.load_curves_for_well(self.current_well)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error opening curve fitting dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save curve: {str(e)}")
            return False


class LoadSegmentsDialog(QDialog):
    """Dialog for selecting saved recession segments to load."""
    
    def __init__(self, segments_data, parent=None):
        super().__init__(parent)
        self.segments_data = segments_data
        self.selected_segments = []
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Load Saved Recession Segments")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Select the recession segments you want to load:")
        layout.addWidget(instructions)
        
        # Segments table
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(6)
        self.segments_table.setHorizontalHeaderLabels([
            "Select", "Start Date", "End Date", "Duration (days)", 
            "Decline Rate (ft/day)", "Created"
        ])
        self.segments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.segments_table.setAlternatingRowColors(True)
        
        # Populate table
        self.segments_table.setRowCount(len(self.segments_data))
        for row, segment in enumerate(self.segments_data):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(segment.get('selected', True))
            self.segments_table.setCellWidget(row, 0, checkbox)
            
            # Start date
            self.segments_table.setItem(row, 1, 
                QTableWidgetItem(segment['start_date'][:10]))  # Just date part
            
            # End date
            self.segments_table.setItem(row, 2, 
                QTableWidgetItem(segment['end_date'][:10]))
            
            # Duration
            self.segments_table.setItem(row, 3, 
                QTableWidgetItem(str(segment['duration_days'])))
            
            # Decline rate - handle both column names
            decline_rate = segment.get('avg_decline_rate', segment.get('recession_rate', 0.0))
            self.segments_table.setItem(row, 4, 
                QTableWidgetItem(f"{decline_rate:.4f}"))
            
            # Created date
            created_date = segment.get('created_at', 'Unknown')
            if 'T' in created_date:
                created_date = created_date.split('T')[0]  # Just date part
            self.segments_table.setItem(row, 5, QTableWidgetItem(created_date))
        
        # Resize columns
        self.segments_table.resizeColumnsToContents()
        layout.addWidget(self.segments_table)
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        selection_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_none)
        selection_layout.addWidget(select_none_btn)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def select_all(self):
        """Select all segments."""
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            checkbox.setChecked(True)
    
    def select_none(self):
        """Deselect all segments."""
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            checkbox.setChecked(False)
    
    def get_selected_segments(self):
        """Get the selected segments data."""
        selected = []
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            if checkbox.isChecked():
                selected.append(self.segments_data[row])
        return selected


class ManageSegmentsDialog(QDialog):
    """Dialog for managing recession segment selection for curve fitting."""
    
    def __init__(self, segments, parent=None):
        super().__init__(parent)
        self.segments = segments
        self.selected_indices = set(range(len(segments)))  # All selected by default
        self.save_selections = False
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Manage Recession Segment Selection")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Select which recession segments to use for master curve fitting.\n"
            "Unselected segments will be ignored during curve creation."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Segments table
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(6)
        self.segments_table.setHorizontalHeaderLabels([
            "Use for Curve", "Start Date", "End Date", "Duration (days)", 
            "Decline Rate (ft/day)", "Quality Score"
        ])
        self.segments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.segments_table.setAlternatingRowColors(True)
        
        # Populate table
        self.segments_table.setRowCount(len(self.segments))
        for row, segment in enumerate(self.segments):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(segment.get('selected', True))
            checkbox.stateChanged.connect(self.on_selection_changed)
            self.segments_table.setCellWidget(row, 0, checkbox)
            
            # Start date
            self.segments_table.setItem(row, 1, 
                QTableWidgetItem(segment['start_date'].strftime('%Y-%m-%d')))
            
            # End date
            self.segments_table.setItem(row, 2, 
                QTableWidgetItem(segment['end_date'].strftime('%Y-%m-%d')))
            
            # Duration
            self.segments_table.setItem(row, 3, 
                QTableWidgetItem(str(segment['duration_days'])))
            
            # Decline rate
            self.segments_table.setItem(row, 4, 
                QTableWidgetItem(f"{segment.get('avg_decline_rate', segment.get('recession_rate', 0)):.4f}"))
            
            # Quality score (based on duration and consistency)
            quality = self.calculate_quality_score(segment)
            quality_item = QTableWidgetItem(f"{quality:.2f}")
            if quality >= 0.8:
                quality_item.setBackground(Qt.green)
            elif quality >= 0.6:
                quality_item.setBackground(Qt.yellow)
            else:
                quality_item.setBackground(Qt.red)
            self.segments_table.setItem(row, 5, quality_item)
        
        # Resize columns
        self.segments_table.resizeColumnsToContents()
        layout.addWidget(self.segments_table)
        
        # Selection summary
        self.summary_label = QLabel()
        self.update_summary()
        layout.addWidget(self.summary_label)
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        selection_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_none)
        selection_layout.addWidget(select_none_btn)
        
        select_best_btn = QPushButton("Select Best Quality")
        select_best_btn.clicked.connect(self.select_best_quality)
        selection_layout.addWidget(select_best_btn)
        
        selection_layout.addStretch()
        
        # Save checkbox
        self.save_checkbox = QCheckBox("Save selections to database")
        self.save_checkbox.setChecked(True)
        selection_layout.addWidget(self.save_checkbox)
        
        layout.addLayout(selection_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def calculate_quality_score(self, segment):
        """Calculate a quality score for the segment (0-1)."""
        duration_score = min(segment['duration_days'] / 30.0, 1.0)  # Longer is better, cap at 30 days
        
        # Rate consistency (lower variance is better)
        if 'data' in segment and not segment['data'].empty:
            daily_changes = segment['data']['water_level'].diff().dropna()
            if len(daily_changes) > 1:
                consistency_score = max(0, 1 - (daily_changes.std() / 0.1))  # Normalize by 0.1 ft
            else:
                consistency_score = 0.5
        else:
            consistency_score = 0.5
        
        return (duration_score + consistency_score) / 2
    
    def on_selection_changed(self):
        """Handle selection changes."""
        self.update_summary()
    
    def update_summary(self):
        """Update the selection summary."""
        selected_count = 0
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            if checkbox.isChecked():
                selected_count += 1
        
        total_count = len(self.segments)
        self.summary_label.setText(f"Selected: {selected_count} of {total_count} segments")
        
        if selected_count == 0:
            self.summary_label.setStyleSheet("color: red; font-weight: bold;")
        elif selected_count < total_count / 2:
            self.summary_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.summary_label.setStyleSheet("color: green; font-weight: bold;")
    
    def select_all(self):
        """Select all segments."""
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            checkbox.setChecked(True)
    
    def select_none(self):
        """Deselect all segments."""
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            checkbox.setChecked(False)
    
    def select_best_quality(self):
        """Select only the highest quality segments (score >= 0.7)."""
        for row in range(self.segments_table.rowCount()):
            quality_item = self.segments_table.item(row, 5)
            quality_score = float(quality_item.text())
            checkbox = self.segments_table.cellWidget(row, 0)
            checkbox.setChecked(quality_score >= 0.7)
    
    def get_selected_segment_indices(self):
        """Get indices of selected segments."""
        selected = []
        for row in range(self.segments_table.rowCount()):
            checkbox = self.segments_table.cellWidget(row, 0)
            if checkbox.isChecked():
                selected.append(row)
        return selected
    
    def accept(self):
        """Handle dialog acceptance."""
        self.save_selections = self.save_checkbox.isChecked()
        super().accept()


class LoadMrcCalculationDialog(QDialog):
    """Dialog for selecting a previous MRC calculation to load."""
    
    def __init__(self, curves, mrc_db, parent=None):
        super().__init__(parent)
        self.curves = curves
        self.mrc_db = mrc_db
        self.selected_calculation_id = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Load MRC Calculation")
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Select a curve and then a calculation to load:")
        layout.addWidget(instructions)
        
        # Curve selection
        curve_layout = QHBoxLayout()
        curve_layout.addWidget(QLabel("Curve:"))
        self.curve_combo = QComboBox()
        for curve in self.curves:
            label = f"{curve['creation_date'][:10]} - {curve['curve_type']} (R²={curve['r_squared']:.3f})"
            self.curve_combo.addItem(label, curve['id'])
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        curve_layout.addWidget(self.curve_combo)
        layout.addLayout(curve_layout)
        
        # Calculations table
        self.calc_table = QTableWidget()
        self.calc_table.setColumnCount(5)
        self.calc_table.setHorizontalHeaderLabels([
            "Date", "Total Recharge (in)", "Annual Rate (in/yr)", 
            "Events", "Parameters"
        ])
        self.calc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.calc_table.setAlternatingRowColors(True)
        self.calc_table.verticalHeader().setVisible(False)
        layout.addWidget(self.calc_table)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Load calculations for first curve
        if self.curves:
            self.on_curve_selected()
        
        # Connect double-click to load
        self.calc_table.doubleClicked.connect(self.accept)
        
    def on_curve_selected(self):
        """Load calculations for the selected curve."""
        curve_id = self.curve_combo.currentData()
        if not curve_id:
            return
            
        # Get calculations for this curve
        calculations = self.mrc_db.get_calculations_for_curve(curve_id)
        
        # Update table
        self.calc_table.setRowCount(len(calculations))
        for row, calc in enumerate(calculations):
            # Date
            date_item = QTableWidgetItem(calc['calculation_date'])
            date_item.setData(Qt.UserRole, calc['id'])
            self.calc_table.setItem(row, 0, date_item)
            
            # Total recharge
            recharge_item = QTableWidgetItem(f"{calc['total_recharge']:.2f}")
            self.calc_table.setItem(row, 1, recharge_item)
            
            # Annual rate
            rate_item = QTableWidgetItem(f"{calc['annual_rate']:.2f}")
            self.calc_table.setItem(row, 2, rate_item)
            
            # Events count
            count_item = QTableWidgetItem(str(calc.get('event_count', 'N/A')))
            self.calc_table.setItem(row, 3, count_item)
            
            # Parameters summary
            params = f"Sy={calc['specific_yield']:.3f}, Threshold={calc['deviation_threshold']:.2f}ft"
            params_item = QTableWidgetItem(params)
            self.calc_table.setItem(row, 4, params_item)
        
        # Resize columns
        self.calc_table.resizeColumnsToContents()
        
    def accept(self):
        """Handle OK button click."""
        selected_rows = self.calc_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            self.selected_calculation_id = self.calc_table.item(row, 0).data(Qt.UserRole)
        super().accept()


class CompareMrcCalculationsDialog(QDialog):
    """Dialog for comparing multiple MRC calculations."""
    
    def __init__(self, curves, mrc_db, parent=None):
        super().__init__(parent)
        self.curves = curves
        self.mrc_db = mrc_db
        self.selected_curves = []
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Compare MRC Calculations")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Select curves to compare (calculations will be compared for each curve):"
        )
        layout.addWidget(instructions)
        
        # Curves table with checkboxes
        self.curves_table = QTableWidget()
        self.curves_table.setColumnCount(6)
        self.curves_table.setHorizontalHeaderLabels([
            "Include", "Date", "Type", "R²", "Segments", "Calculations"
        ])
        self.curves_table.setAlternatingRowColors(True)
        self.curves_table.verticalHeader().setVisible(False)
        
        # Populate curves table
        self.curves_table.setRowCount(len(self.curves))
        for row, curve in enumerate(self.curves):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(row < 2)  # Check first two by default
            checkbox_cell = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_cell)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.curves_table.setCellWidget(row, 0, checkbox_cell)
            
            # Date
            date_item = QTableWidgetItem(curve['creation_date'][:10])
            date_item.setData(Qt.UserRole, curve['id'])
            self.curves_table.setItem(row, 1, date_item)
            
            # Type
            self.curves_table.setItem(row, 2, QTableWidgetItem(curve['curve_type']))
            
            # R²
            self.curves_table.setItem(row, 3, QTableWidgetItem(f"{curve['r_squared']:.4f}"))
            
            # Segments
            self.curves_table.setItem(row, 4, QTableWidgetItem(str(curve['recession_segments'])))
            
            # Get calculation count
            calcs = self.mrc_db.get_calculations_for_curve(curve['id'])
            self.curves_table.setItem(row, 5, QTableWidgetItem(str(len(calcs))))
        
        self.curves_table.resizeColumnsToContents()
        layout.addWidget(self.curves_table)
        
        # Comparison plot
        self.figure = plt.figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        plot_btn = QPushButton("Update Comparison")
        plot_btn.clicked.connect(self.update_comparison)
        button_layout.addWidget(plot_btn)
        
        export_btn = QPushButton("Export Comparison")
        export_btn.clicked.connect(self.export_comparison)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Initial comparison
        self.update_comparison()
        
    def update_comparison(self):
        """Update the comparison plot."""
        self.figure.clear()
        
        # Get selected curves
        selected_curves = []
        for row in range(self.curves_table.rowCount()):
            checkbox = self.curves_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                curve_id = self.curves_table.item(row, 1).data(Qt.UserRole)
                curve_date = self.curves_table.item(row, 1).text()
                curve_type = self.curves_table.item(row, 2).text()
                selected_curves.append((curve_id, curve_date, curve_type))
        
        if len(selected_curves) < 2:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Select at least 2 curves to compare', 
                    ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            return
            
        # Create subplots
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        # Colors for different curves
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        
        # Collect data for comparison
        curve_labels = []
        avg_recharges = []
        avg_rates = []
        calculation_counts = []
        
        for idx, (curve_id, curve_date, curve_type) in enumerate(selected_curves):
            color = colors[idx % len(colors)]
            
            # Get calculations for this curve
            calcs = self.mrc_db.get_calculations_for_curve(curve_id)
            
            if calcs:
                # Extract data
                recharges = [calc['total_recharge'] for calc in calcs]
                rates = [calc['annual_rate'] for calc in calcs]
                
                # Store averages
                curve_labels.append(f"{curve_date}\n{curve_type}")
                avg_recharges.append(np.mean(recharges))
                avg_rates.append(np.mean(rates))
                calculation_counts.append(len(calcs))
                
                # Box plot of recharges
                positions = [idx]
                ax1.boxplot(recharges, positions=positions, widths=0.6, 
                           patch_artist=True, boxprops=dict(facecolor=color, alpha=0.5))
        
        # Format recharge comparison
        ax1.set_xticks(range(len(curve_labels)))
        ax1.set_xticklabels(curve_labels, rotation=45, ha='right')
        ax1.set_ylabel('Total Recharge (inches)')
        ax1.set_title('Recharge Distribution by Curve')
        ax1.grid(True, alpha=0.3)
        
        # Bar chart comparison
        x = np.arange(len(curve_labels))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, avg_recharges, width, label='Avg Total Recharge', alpha=0.7)
        bars2 = ax2.bar(x + width/2, avg_rates, width, label='Avg Annual Rate', alpha=0.7)
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax2.annotate(f'{height:.1f}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=8)
        
        ax2.set_xlabel('Curve')
        ax2.set_ylabel('Inches / Inches per Year')
        ax2.set_title('Average Recharge Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(curve_labels, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Add calculation counts as text
        for i, (label, count) in enumerate(zip(curve_labels, calculation_counts)):
            ax2.text(i, -0.1, f'n={count}', ha='center', transform=ax2.get_xaxis_transform())
        
        self.figure.tight_layout()
        self.canvas.draw()
        
    def export_comparison(self):
        """Export comparison results."""
        selected_count = sum(1 for row in range(self.curves_table.rowCount()) 
                           if self.curves_table.cellWidget(row, 0).findChild(QCheckBox).isChecked())
        
        if selected_count < 2:
            QMessageBox.warning(self, "Selection Required", 
                              "Please select at least 2 curves to export comparison.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Comparison", 
                "MRC_curve_comparison.png",
                "PNG Files (*.png);;PDF Files (*.pdf)"
            )
            
            if file_path:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Export Successful", 
                                      f"Comparison exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", 
                               f"Failed to export comparison:\n{str(e)}")





class InteractiveCurveFittingDialog(QDialog):
    """Interactive dialog for curve fitting with real-time preview and parameter adjustment."""
    
    def __init__(self, segments, curve_type=None, parent=None, existing_curve=None, mrc_db=None, well_id=None):
        super().__init__(parent)
        self.segments = segments
        self.existing_curve = existing_curve
        self.mrc_db = mrc_db
        self.well_id = well_id
        self.parent_tab = parent
        
        # If editing existing curve, use its type and parameters
        if existing_curve:
            self.curve_type = existing_curve.get('curve_type', 'exponential')
            self.curve_data = existing_curve
            # Extract parameters for initial values
            self.initial_params = existing_curve.get('curve_coefficients', {})
        else:
            self.curve_type = curve_type or "exponential"
            self.curve_data = None
            self.initial_params = None
            
        self.fitted_params = None
        self.manual_params = {}  # Track manual parameter adjustments
        self.is_manual_mode = False  # Track if using manual parameters
        
        # Prepare segment data for fitting
        self.prepare_segment_data()
        
        self.setup_ui()
        self.update_curve_description()
        
        # Load initial parameters if editing
        if self.existing_curve and self.initial_params:
            self.load_existing_parameters()
        else:
            self.fit_initial_curve()
    
    def setup_ui(self):
        """Setup the comprehensive interactive UI."""
        if self.existing_curve:
            self.setWindowTitle(f"Interactive Curve Fitting - Editing {self.curve_type.title()} Curve")
        else:
            self.setWindowTitle(f"Interactive Curve Fitting - {self.curve_type.title()}")
        self.setModal(True)
        self.resize(1000, 700)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        
        # Left panel: Controls
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # Curve selection section
        selection_group = QGroupBox("Curve Type Selection")
        selection_layout = QVBoxLayout(selection_group)
        
        # Curve type dropdown
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.curve_type_combo = QComboBox()
        self.curve_type_combo.addItem("Exponential (Recommended)", "exponential")
        self.curve_type_combo.addItem("Power Law", "power")
        self.curve_type_combo.addItem("Linear", "linear")
        self.curve_type_combo.setCurrentIndex(0)
        self.curve_type_combo.currentIndexChanged.connect(self.on_curve_type_changed_dialog)
        type_layout.addWidget(self.curve_type_combo)
        selection_layout.addLayout(type_layout)
        
        # Description of selected curve type
        self.curve_description_label = QLabel()
        self.curve_description_label.setWordWrap(True)
        self.curve_description_label.setStyleSheet("color: #6c757d; font-style: italic; font-size: 10px; margin: 5px;")
        selection_layout.addWidget(self.curve_description_label)
        
        left_layout.addWidget(selection_group)
        
        # Data info section
        info_group = QGroupBox("Data Information")
        info_layout = QVBoxLayout(info_group)
        
        # Segment selection dropdown (only if we have database access)
        if self.mrc_db and self.well_id:
            segment_layout = QHBoxLayout()
            segment_layout.addWidget(QLabel("Segments:"))
            
            self.segment_source_combo = QComboBox()
            self.segment_source_combo.setToolTip(
                "Select different segment sets to see how the curve changes.\n"
                "You can compare curves fitted with different recession segments."
            )
            # Add current segments as first option
            self.segment_source_combo.addItem(f"Current ({len(self.segments)} segments)", "current")
            
            # Load available segment sets from database
            self.load_available_segments()
            
            self.segment_source_combo.currentIndexChanged.connect(self.on_segment_source_changed)
            segment_layout.addWidget(self.segment_source_combo)
            info_layout.addLayout(segment_layout)
        else:
            self.segments_label = QLabel(f"Segments: {len(self.segments)}")
            info_layout.addWidget(self.segments_label)
        
        self.data_points_label = QLabel(f"Data Points: {self.total_points}")
        info_layout.addWidget(self.data_points_label)
        
        left_layout.addWidget(info_group)
        
        # Fitting parameters section
        self.params_group = QGroupBox("Fitting Parameters")
        params_layout = QVBoxLayout(self.params_group)
        
        # Add curve-specific parameter controls
        self.create_parameter_controls(params_layout)
        
        left_layout.addWidget(self.params_group)
        
        # Fitting results section
        results_group = QGroupBox("Fitting Results")
        results_layout = QVBoxLayout(results_group)
        
        self.equation_label = QLabel("Equation: Not fitted")
        self.equation_label.setWordWrap(True)
        self.equation_label.setStyleSheet("font-family: monospace; font-size: 11px;")
        results_layout.addWidget(self.equation_label)
        
        self.r_squared_label = QLabel("R²: Not calculated")
        self.r_squared_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        results_layout.addWidget(self.r_squared_label)
        
        self.rmse_label = QLabel("RMSE: Not calculated") 
        results_layout.addWidget(self.rmse_label)
        
        self.quality_label = QLabel("Quality: Not assessed")
        self.quality_label.setWordWrap(True)
        results_layout.addWidget(self.quality_label)
        
        left_layout.addWidget(results_group)
        
        # Action buttons
        button_layout = QVBoxLayout()
        
        self.refit_btn = QPushButton("🔄 Refit Curve")
        self.refit_btn.clicked.connect(self.refit_curve)
        self.refit_btn.setToolTip(
            "Recalculate the curve using the parameter values shown above.\n"
            "Use this after manually adjusting Q_max or α values to see how\n"
            "the changes affect the curve fit. The R² value will be updated\n"
            "to show the goodness of fit with your manual parameters."
        )
        button_layout.addWidget(self.refit_btn)
        
        self.auto_optimize_btn = QPushButton("⚡ Auto Optimize")
        self.auto_optimize_btn.clicked.connect(self.auto_optimize)
        self.auto_optimize_btn.setToolTip(
            "Automatically find the best parameters for the selected curve type.\n"
            "This uses optimization algorithms to minimize the error between\n"
            "the fitted curve and your recession data. Multiple initial guesses\n"
            "are tested to find the global best fit. The parameters will be\n"
            "updated automatically and the R² value shows the quality of fit."
        )
        button_layout.addWidget(self.auto_optimize_btn)
        
        left_layout.addLayout(button_layout)
        left_layout.addStretch()
        
        # Dialog buttons with Save option
        dialog_button_layout = QHBoxLayout()
        
        self.save_curve_btn = QPushButton("💾 Save Curve")
        self.save_curve_btn.clicked.connect(self.save_curve_from_dialog)
        self.save_curve_btn.setToolTip(
            "Save the current curve to the database.\n"
            "The curve will be associated with the selected segments."
        )
        dialog_button_layout.addWidget(self.save_curve_btn)
        
        dialog_button_layout.addStretch()
        
        self.accept_btn = QPushButton("✓ Use Curve")
        self.accept_btn.clicked.connect(self.accept_fitting)
        self.accept_btn.setToolTip("Use this curve for calculations without saving")
        dialog_button_layout.addWidget(self.accept_btn)
        
        self.cancel_btn = QPushButton("✗ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        dialog_button_layout.addWidget(self.cancel_btn)
        
        left_layout.addLayout(dialog_button_layout)
        
        main_layout.addWidget(left_panel)
        
        # Right panel: Plot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Plot title
        plot_title = QLabel("Curve Fitting Visualization")
        plot_title.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px;")
        plot_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(plot_title)
        
        # Matplotlib plot
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        main_layout.addWidget(right_panel)
    
    def create_parameter_controls(self, layout):
        """Create parameter controls specific to curve type."""
        if self.curve_type == 'exponential':
            # Exponential recession: Q = Q_max * (1 - e^(-αt))
            equation_label = QLabel("")
            equation_label.setTextFormat(Qt.RichText)
            equation_label.setText("Q = Q<sub>max</sub> × (1 - e<sup>-αt</sup>)")
            layout.addWidget(equation_label)
            
            # Maximum drawdown Q_max
            a_layout = QHBoxLayout()
            a_layout.addWidget(QLabel("Maximum Drawdown (Q_max):"))
            self.param_a = QDoubleSpinBox()
            self.param_a.setRange(0.01, 100.0)
            self.param_a.setValue(10.0)  # Better initial guess
            self.param_a.setDecimals(3)
            self.param_a.valueChanged.connect(self.on_parameter_changed)
            a_layout.addWidget(self.param_a)
            layout.addLayout(a_layout)
            
            # Recession coefficient α
            b_layout = QHBoxLayout()
            b_layout.addWidget(QLabel("Recession Coefficient (α):"))
            self.param_b = QDoubleSpinBox()
            self.param_b.setRange(0.001, 1.0)
            self.param_b.setValue(0.05)  # Better initial guess for recession
            self.param_b.setDecimals(4)
            self.param_b.valueChanged.connect(self.on_parameter_changed)
            b_layout.addWidget(self.param_b)
            layout.addLayout(b_layout)
            
        elif self.curve_type == 'power':
            # Power law: Q = a * t^β
            equation_label = QLabel("")
            equation_label.setTextFormat(Qt.RichText)
            equation_label.setText("Q = a × t<sup>β</sup>")
            layout.addWidget(equation_label)
            
            # Initial drawdown Q₀
            a_layout = QHBoxLayout()
            a_layout.addWidget(QLabel("Initial Drawdown (Q₀):"))
            self.param_a = QDoubleSpinBox()
            self.param_a.setRange(0.01, 100.0)
            self.param_a.setValue(10.0)  # Better initial guess
            self.param_a.setDecimals(3)
            self.param_a.valueChanged.connect(self.on_parameter_changed)
            a_layout.addWidget(self.param_a)
            layout.addLayout(a_layout)
            
            # Recession exponent β
            b_layout = QHBoxLayout()
            b_layout.addWidget(QLabel("Recession Exponent (β):"))
            self.param_b = QDoubleSpinBox()
            self.param_b.setRange(0.1, 3.0)
            self.param_b.setValue(1.0)
            self.param_b.setDecimals(3)
            self.param_b.valueChanged.connect(self.on_parameter_changed)
            b_layout.addWidget(self.param_b)
            layout.addLayout(b_layout)
            
        else:  # linear
            # Linear: y = a - b * t
            layout.addWidget(QLabel("y = a - b × t"))
            
            # Intercept (a)
            a_layout = QHBoxLayout()
            a_layout.addWidget(QLabel("Intercept (a):"))
            self.param_a = QDoubleSpinBox()
            self.param_a.setRange(-1000.0, 1000.0)
            self.param_a.setValue(0.0)
            self.param_a.setDecimals(3)
            self.param_a.valueChanged.connect(self.on_parameter_changed)
            a_layout.addWidget(self.param_a)
            layout.addLayout(a_layout)
            
            # Slope (b)
            b_layout = QHBoxLayout()
            b_layout.addWidget(QLabel("Slope (b):"))
            self.param_b = QDoubleSpinBox()
            self.param_b.setRange(0.001, 10.0)
            self.param_b.setValue(0.1)
            self.param_b.setDecimals(4)
            self.param_b.valueChanged.connect(self.on_parameter_changed)
            b_layout.addWidget(self.param_b)
            layout.addLayout(b_layout)
    
    def prepare_segment_data(self):
        """Prepare segment data for curve fitting."""
        self.all_times = []
        self.all_levels = []
        self.normalized_levels = []  # Add normalized levels
        self.segment_colors = []
        
        for i, segment in enumerate(self.segments):
            if 'data' in segment and segment['data'] is not None:
                segment_data = segment['data'].copy()
                
                # Process based on data structure
                if hasattr(segment_data, 'columns'):
                    # It's a DataFrame
                    if 'timestamp' in segment_data.columns:
                        # Convert timestamp to days from start
                        start_time = segment_data['timestamp'].iloc[0]
                        times = (segment_data['timestamp'] - start_time).dt.total_seconds() / 86400
                        times = times.tolist()
                    elif 'time_days' in segment_data.columns:
                        # Already has time in days
                        times = segment_data['time_days'].tolist()
                    elif hasattr(segment_data, 'index'):
                        # Use index as time
                        times = list(range(len(segment_data)))
                    else:
                        times = list(range(len(segment_data)))
                    
                    # Get levels
                    if 'water_level' in segment_data.columns:
                        levels = segment_data['water_level'].tolist()
                    elif 'normalized_level' in segment_data.columns:
                        levels = segment_data['normalized_level'].tolist()
                    else:
                        levels = segment_data.iloc[:, 0].tolist()
                else:
                    # Fallback for other data formats
                    times = list(range(len(segment_data)))
                    levels = list(segment_data) if hasattr(segment_data, '__iter__') else [segment_data]
                
                # Normalize levels for recession curves (drawdown from initial level)
                if levels:
                    start_level = levels[0]
                    # For recession, water level decreases, so drawdown is positive
                    normalized = [start_level - level for level in levels]
                    self.normalized_levels.extend(normalized)
                
                self.all_times.extend(times)
                self.all_levels.extend(levels)
                self.segment_colors.extend([i] * len(times))
        
        self.total_points = len(self.all_times)
        
        # Convert to numpy arrays
        import numpy as np
        self.times_array = np.array(self.all_times)
        self.levels_array = np.array(self.all_levels)
        self.normalized_array = np.array(self.normalized_levels)  # For normalized fitting
    
    def on_curve_type_changed_dialog(self):
        """Handle curve type changes within the dialog."""
        try:
            # Update curve type
            self.curve_type = self.curve_type_combo.currentData()
            
            # Update window title
            self.setWindowTitle(f"Interactive Curve Fitting - {self.curve_type.title()}")
            
            # Update description
            self.update_curve_description()
            
            # Recreate parameter controls for new curve type
            self.recreate_parameter_controls()
            
            # Refit with new curve type
            self.fit_curve_with_params()
            self.update_plot()
            
        except Exception as e:
            logger.error(f"Error changing curve type in dialog: {e}")
    
    def update_curve_description(self):
        """Update the curve type description."""
        descriptions = {
            'exponential': "📈 Best for natural aquifer recession. Exponential approach: Q = Q_max × (1 - e^(-αt))",
            'power': "📊 Good for complex drainage patterns. Power law: Q = a × t^β",
            'linear': "📉 Simplest model for constant decline rate. Linear: y = a - b × t"
        }
        
        description = descriptions.get(self.curve_type, "Unknown curve type")
        self.curve_description_label.setText(description)
    
    def recreate_parameter_controls(self):
        """Recreate parameter controls when curve type changes."""
        try:
            # Clear existing parameter controls
            params_layout = self.params_group.layout()
            
            # Remove all widgets (including equation labels)
            for i in reversed(range(params_layout.count())):
                child = params_layout.itemAt(i)
                if child:
                    if child.widget():
                        child.widget().deleteLater()
                    elif child.layout():
                        self.clear_layout(child.layout())
                    params_layout.removeItem(child)
            
            # Recreate controls for new curve type
            self.create_parameter_controls(params_layout)
            
        except Exception as e:
            logger.error(f"Error recreating parameter controls: {e}")
    
    def clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
    
    def fit_initial_curve(self):
        """Fit initial curve with default parameters."""
        self.fit_curve_with_params()
        self.update_plot()
    
    def fit_curve_with_params(self):
        """Fit curve using current parameter values."""
        try:
            import numpy as np
            from scipy.optimize import curve_fit
            
            if len(self.times_array) == 0:
                return
            
            # Define curve functions
            if self.curve_type == 'exponential':
                # For recession curves: drawdown approaches maximum value
                # Q(t) = Q_max * (1 - exp(-α*t))
                def curve_func(t, a, b):
                    return a * (1 - np.exp(-b * t))
                initial_guess = [self.param_a.value(), self.param_b.value()]
            elif self.curve_type == 'power':
                def curve_func(t, a, b):
                    # For recession: Q = a * t^b (b positive for increasing drawdown)
                    return a * np.power(np.maximum(t, 0.001), b)
                initial_guess = [self.param_a.value(), self.param_b.value()]
            else:  # linear
                def curve_func(t, a, b):
                    return a - b * t
                initial_guess = [self.param_a.value(), self.param_b.value()]
            
            # Perform curve fitting on normalized data for better recession curve results
            try:
                # Use normalized drawdown values (already positive)
                fitting_levels = self.normalized_array
                popt, pcov = curve_fit(curve_func, self.times_array, fitting_levels, p0=initial_guess)
                self.fitted_params = popt
                
                # Calculate R-squared on normalized data
                fitted_values = curve_func(self.times_array, *popt)
                ss_res = np.sum((fitting_levels - fitted_values) ** 2)
                ss_tot = np.sum((fitting_levels - np.mean(fitting_levels)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                
                # Calculate RMSE on normalized data
                rmse = np.sqrt(np.mean((fitting_levels - fitted_values) ** 2))
                
                # Update parameter controls with fitted values
                self.param_a.setValue(popt[0])
                self.param_b.setValue(popt[1])
                
                # Store results
                self.curve_data = {
                    'curve_type': self.curve_type,
                    'parameters': {'a': popt[0], 'b': popt[1]},
                    'r_squared': r_squared,
                    'rmse': rmse,
                    'fitted_params': popt
                }
                
                # Update display
                self.update_results_display()
                
            except Exception as e:
                logger.error(f"Curve fitting failed: {e}")
                self.equation_label.setText("Fitting failed - try adjusting parameters")
                
        except Exception as e:
            logger.error(f"Error in curve fitting: {e}")
    
    def update_results_display(self):
        """Update the results display with current fitting results."""
        if not self.curve_data:
            return
            
        params = self.curve_data['parameters']
        r_squared = self.curve_data['r_squared']
        rmse = self.curve_data['rmse']
        
        # Update equation with proper formatting
        self.equation_label.setTextFormat(Qt.RichText)
        if self.curve_type == 'exponential':
            equation = f"Q = {params['a']:.3f} × (1 - e<sup>-{params['b']:.4f}t</sup>)"
        elif self.curve_type == 'power':
            equation = f"Q = {params['a']:.3f} × t<sup>{params['b']:.3f}</sup>"
        else:  # linear
            equation = f"Q = {params['a']:.3f} - {params['b']:.4f} × t"
        
        self.equation_label.setText(equation)
        
        # Update R-squared with color coding
        self.r_squared_label.setText(f"R² = {r_squared:.4f}")
        if r_squared >= 0.9:
            self.r_squared_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px;")
        elif r_squared >= 0.7:
            self.r_squared_label.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px;")
        else:
            self.r_squared_label.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px;")
        
        # Update RMSE
        self.rmse_label.setText(f"RMSE: {rmse:.4f}")
        
        # Update quality assessment
        if r_squared >= 0.95:
            quality_text = "🟢 Excellent fit (R² ≥ 0.95)"
            quality_color = "#d4edda"
        elif r_squared >= 0.90:
            quality_text = "🟡 Good fit (R² ≥ 0.90)"
            quality_color = "#fff3cd"
        elif r_squared >= 0.80:
            quality_text = "🟠 Fair fit (R² ≥ 0.80)"
            quality_color = "#ffeaa7"
        else:
            quality_text = "🔴 Poor fit (R² < 0.80)"
            quality_color = "#f8d7da"
        
        self.quality_label.setText(quality_text)
        self.quality_label.setStyleSheet(f"margin: 10px; padding: 5px; background-color: {quality_color}; border-radius: 4px;")
    
    def update_plot(self):
        """Update the fitting visualization plot."""
        try:
            logger.debug("Updating plot in interactive dialog")
            
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            if not hasattr(self, 'all_times') or len(self.all_times) == 0:
                ax.text(0.5, 0.5, "No data to plot", ha='center', va='center', transform=ax.transAxes)
                self.canvas.draw()
                logger.warning("No data available for plotting")
                return
            
            # Plot segment data with different colors
            import matplotlib.pyplot as plt
            import numpy as np
            colors = plt.cm.Set3(np.linspace(0, 1, len(self.segments)))
            
            # Plot normalized drawdown data
            for i in range(len(self.segments)):
                mask = np.array(self.segment_colors) == i
                if np.any(mask):
                    ax.scatter(np.array(self.all_times)[mask], self.normalized_array[mask], 
                              c=[colors[i]], alpha=0.7, s=30, label=f'Segment {i+1}')
            
            # Plot fitted curve if available
            if self.fitted_params is not None:
                t_fit = np.linspace(min(self.all_times), max(self.all_times), 100)
                
                if self.curve_type == 'exponential':
                    # Q(t) = Q_max * (1 - exp(-α*t))
                    y_fit = self.fitted_params[0] * (1 - np.exp(-self.fitted_params[1] * t_fit))
                elif self.curve_type == 'power':
                    y_fit = self.fitted_params[0] * np.power(np.maximum(t_fit, 0.001), self.fitted_params[1])
                else:  # linear
                    y_fit = self.fitted_params[0] - self.fitted_params[1] * t_fit
                
                ax.plot(t_fit, y_fit, 'r-', linewidth=2, label=f'Fitted {self.curve_type.title()} Curve')
            
            ax.set_xlabel('Time since recession start (days)')
            ax.set_ylabel('Drawdown (ft)')  # Changed to drawdown for normalized data
            ax.set_title(f'{self.curve_type.title()} Recession Curve Fitting')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            self.figure.tight_layout()
            self.canvas.draw()
            logger.debug("Plot updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            # Try to show error on plot
            try:
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, f"Plot error: {str(e)}", ha='center', va='center', transform=ax.transAxes)
                self.canvas.draw()
            except:
                pass
    
    def on_parameter_changed(self):
        """Handle parameter changes for real-time preview."""
        # For now, just update the manual parameters (user can click Refit for updated curve)
        pass
    
    def update_fitting_results(self):
        """Update the fitting results display with current curve data."""
        try:
            if not self.curve_data:
                return
                
            params = self.curve_data.get('parameters', {})
            r_squared = self.curve_data.get('r_squared', 0)
            rmse = self.curve_data.get('rmse', 0)
            
            # Update equation with proper formatting
            self.equation_label.setTextFormat(Qt.RichText)
            if self.curve_type == 'exponential':
                equation = f"Q = {params.get('a', 0):.3f} × (1 - e<sup>-{params.get('b', 0):.4f}t</sup>)"
            elif self.curve_type == 'power':
                equation = f"Q = {params.get('a', 0):.3f} × t<sup>{params.get('b', 0):.3f}</sup>"
            else:  # linear
                equation = f"Q = {params.get('intercept', 0):.3f} - {params.get('slope', 0):.4f} × t"
            
            self.equation_label.setText(equation)
            
            # Update R-squared with color coding
            self.r_squared_label.setText(f"R² = {r_squared:.4f}")
            if r_squared >= 0.9:
                self.r_squared_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px;")
            elif r_squared >= 0.7:
                self.r_squared_label.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px;")
            else:
                self.r_squared_label.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px;")
            
            # Update RMSE
            self.rmse_label.setText(f"RMSE: {rmse:.4f}")
            
        except Exception as e:
            logger.error(f"Error updating fitting results: {e}")
    
    def refit_curve(self):
        """Refit curve with current manual parameter values without optimization."""
        try:
            # Mark as manual mode
            self.is_manual_mode = True
            
            # Get current parameters from spinboxes
            if self.curve_type == 'exponential':
                self.manual_params = {
                    'a': self.param_a.value(),
                    'b': self.param_b.value(),
                    'Q0': self.param_a.value()  # For compatibility
                }
                self.fitted_params = [self.param_a.value(), self.param_b.value()]
            elif self.curve_type == 'power':
                self.manual_params = {
                    'a': self.param_a.value(),
                    'b': self.param_b.value()
                }
                self.fitted_params = [self.param_a.value(), self.param_b.value()]
            else:  # linear
                self.manual_params = {
                    'slope': self.param_b.value(),
                    'intercept': self.param_a.value()
                }
                self.fitted_params = [self.param_a.value(), self.param_b.value()]
            
            # Calculate R² for manual parameters
            self.calculate_manual_r_squared()
            
            # Update display
            self.update_results_display()
            self.update_plot()
            
            # Update quality label to indicate manual fit
            self.quality_label.setText("Quality: Manual fit - parameters set by user")
            self.quality_label.setStyleSheet("color: #ff6b35; font-weight: bold;")
            
        except Exception as e:
            logger.error(f"Error in manual refit: {e}")
            QMessageBox.warning(self, "Refit Error", f"Failed to refit curve: {str(e)}")
    
    def auto_optimize(self):
        """Automatically optimize parameters for best fit."""
        try:
            # Try multiple initial guesses to find global optimum
            import numpy as np
            from scipy.optimize import curve_fit
            
            best_r_squared = -1
            best_params = None
            
            # Try different initial guesses
            initial_guesses = [
                [1.0, 0.1], [10.0, 0.01], [0.1, 1.0], [5.0, 0.05]
            ]
            
            for guess in initial_guesses:
                try:
                    if self.curve_type == 'exponential':
                        def curve_func(t, a, b):
                            return a * (1 - np.exp(-b * t))
                    elif self.curve_type == 'power':
                        def curve_func(t, a, b):
                            return a * np.power(np.maximum(t, 0.001), b)
                    else:  # linear
                        def curve_func(t, a, b):
                            return a - b * t
                    
                    # Use normalized drawdown data for fitting
                    fitting_levels = self.normalized_array
                    popt, _ = curve_fit(curve_func, self.times_array, fitting_levels, p0=guess)
                    
                    # Calculate R-squared on normalized data
                    fitted_values = curve_func(self.times_array, *popt)
                    ss_res = np.sum((fitting_levels - fitted_values) ** 2)
                    ss_tot = np.sum((fitting_levels - np.mean(fitting_levels)) ** 2)
                    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                    
                    if r_squared > best_r_squared:
                        best_r_squared = r_squared
                        best_params = popt
                        
                except:
                    continue
            
            if best_params is not None:
                # Mark as automatic mode
                self.is_manual_mode = False
                
                # Update spinboxes with optimized values
                self.param_a.setValue(best_params[0])
                self.param_b.setValue(best_params[1])
                
                # Store optimized parameters
                self.fitted_params = best_params
                
                # Perform the fit with optimized parameters
                self.fit_curve_with_params()
                self.update_plot()
                
                # Update quality label
                self.quality_label.setText("Quality: Auto-optimized fit")
                self.quality_label.setStyleSheet("color: #28a745; font-weight: bold;")
                
                QMessageBox.information(self, "Optimization Complete", 
                                      f"Auto-optimization completed!\nBest R² = {best_r_squared:.4f}")
            else:
                QMessageBox.warning(self, "Optimization Failed", "Could not find better parameters.")
                
        except Exception as e:
            logger.error(f"Auto-optimization failed: {e}")
            QMessageBox.warning(self, "Optimization Error", f"Auto-optimization failed: {str(e)}")
    
    def accept_fitting(self):
        """Accept the current fitting results."""
        if self.curve_data and self.curve_data.get('r_squared', 0) > 0:
            self.accept()
        else:
            reply = QMessageBox.question(self, "Poor Fit Quality", 
                                       "The current fit quality is poor. Accept anyway?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.accept()
    
    def get_curve_data(self):
        """Get the fitted curve data."""
        return self.curve_data
    
    def load_available_segments(self):
        """Load available segment sets from database."""
        try:
            if not self.mrc_db or not self.well_id:
                return
                
            # Get all segment sets for this well
            segment_sets = self.mrc_db.get_all_segments_for_well(self.well_id)
            
            for segment_set in segment_sets:
                date_str = segment_set['creation_date'][:10]
                curve_type = segment_set['curve_type']
                count = segment_set['segment_count']
                r_squared = segment_set.get('r_squared', 0)
                
                label = f"{date_str} - {curve_type} (R²={r_squared:.3f}, {count} segments)"
                self.segment_source_combo.addItem(label, segment_set['curve_id'])
                
        except Exception as e:
            logger.error(f"Error loading available segments: {e}")
    
    def on_segment_source_changed(self, index):
        """Handle segment source selection change."""
        try:
            if index < 0:
                return
                
            segment_id = self.segment_source_combo.currentData()
            
            if segment_id == "current":
                # Already using current segments
                return
                
            # Load segments from the selected curve
            if segment_id and self.mrc_db:
                segments_data = self.mrc_db.get_segments_for_curve(segment_id)
                
                if segments_data:
                    # Convert database segments to the format expected by the dialog
                    new_segments = []
                    skipped_count = 0
                    
                    for seg in segments_data:
                        if seg.get('segment_data'):
                            try:
                                # Reconstruct segment structure with all required fields
                                segment_df = pd.DataFrame(seg['segment_data'])
                                
                                # Ensure timestamp column is datetime
                                if 'timestamp' in segment_df.columns:
                                    segment_df['timestamp'] = pd.to_datetime(segment_df['timestamp'])
                                
                                # Validate data has required columns
                                if 'water_level' not in segment_df.columns:
                                    logger.warning(f"Segment missing 'water_level' column, skipping")
                                    skipped_count += 1
                                    continue
                                
                                segment = {
                                    'start_date': pd.to_datetime(seg['start_date']),
                                    'end_date': pd.to_datetime(seg['end_date']),
                                    'duration_days': seg['duration_days'],
                                    'start_level': seg.get('start_level', 0),
                                    'end_level': seg.get('end_level', 0),
                                    'recession_rate': seg.get('recession_rate', 0),
                                    'data': segment_df,
                                    'selected': True
                                }
                                new_segments.append(segment)
                                
                            except Exception as e:
                                logger.error(f"Error processing segment: {e}")
                                skipped_count += 1
                                continue
                        else:
                            skipped_count += 1
                    
                    if skipped_count > 0:
                        logger.warning(f"Skipped {skipped_count} segments with missing or invalid data")
                    
                    if new_segments:
                        # Update segments and refit
                        self.segments = new_segments
                        self.prepare_segment_data()
                        
                        # Update labels
                        self.data_points_label.setText(f"Data Points: {self.total_points}")
                        
                        # Update segment count display
                        if hasattr(self, 'segments_label'):
                            self.segments_label.setText(f"Segments: {len(self.segments)}")
                        
                        # Refit with new segments
                        self.fit_initial_curve()
                        self.update_plot()
                    else:
                        if skipped_count > 0:
                            QMessageBox.warning(self, "No Data", 
                                              f"The selected curve has {skipped_count} segments with missing data.\n"
                                              f"No usable segments found. This usually happens with curves saved "
                                              f"in an older format.")
                        else:
                            QMessageBox.warning(self, "No Data", 
                                              "The selected curve has no usable segment data.")
                        # Reset to current
                        self.segment_source_combo.setCurrentIndex(0)
                        
        except Exception as e:
            logger.error(f"Error changing segment source: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load segments: {str(e)}")
    
    def save_curve_from_dialog(self):
        """Save the current curve directly from the dialog."""
        try:
            if not self.curve_data:
                QMessageBox.warning(self, "No Curve", "No curve to save. Please fit a curve first.")
                return
                
            if not self.mrc_db:
                QMessageBox.warning(self, "Database Error", "No database connection available.")
                return
                
            # Get description from user
            from PyQt5.QtWidgets import QInputDialog
            
            # Create informative default description
            fit_type = "Manual" if self.is_manual_mode else "Auto-optimized"
            default_desc = f"{self.curve_type.title()} curve ({fit_type}), {len(self.segments)} segments"
            
            description, ok = QInputDialog.getText(self, "Save Master Recession Curve", 
                f"Enter a description for this curve:\n\n"
                f"Type: {self.curve_type}\n"
                f"Fit: {fit_type}\n"
                f"R²: {self.curve_data.get('r_squared', 0):.3f}\n"
                f"Segments: {len(self.segments)}",
                text=default_desc)
            
            if not ok or not description.strip():
                return
                
            # Prepare recession segments data
            segments_data = []
            for segment in self.segments:
                segments_data.append({
                    'start_date': segment['start_date'].isoformat(),
                    'end_date': segment['end_date'].isoformat(),
                    'duration_days': segment['duration_days'],
                    'start_level': segment.get('start_level', 0),
                    'end_level': segment.get('end_level', 0),
                    'recession_rate': segment.get('recession_rate', 0),
                    'data': segment.get('data'),
                    'selected': segment.get('selected', True)
                })
            
            # Get current settings from parent tab
            current_settings = {}
            if self.parent_tab and hasattr(self.parent_tab, 'current_settings'):
                current_settings = self.parent_tab.current_settings
            
            # Save curve
            curve_id = self.mrc_db.save_curve(
                well_number=self.well_id,
                well_name=self.parent_tab.well_combo.currentText() if self.parent_tab else "Unknown",
                curve_type=self.curve_type,
                curve_parameters={
                    'min_recession_length': current_settings.get('min_recession_length', 7),
                    'precip_tolerance': current_settings.get('precip_threshold', 0.1),
                    'precip_lag': current_settings.get('precip_lag', 2),
                    'fit_type': 'manual' if self.is_manual_mode else 'auto'
                },
                curve_coefficients=self.curve_data.get('parameters', {}),
                r_squared=self.curve_data.get('r_squared', 0),
                recession_segments=len(self.segments),
                min_recession_length=current_settings.get('min_recession_length', 7),
                description=description,
                recession_segments_data=segments_data
            )
            
            if curve_id:
                QMessageBox.information(self, "Save Successful", 
                    "Master recession curve saved successfully.")
                
                # Update current_curve with the new ID so it won't ask to save again
                if hasattr(self, 'current_curve') and self.current_curve:
                    self.current_curve['id'] = curve_id
                elif not hasattr(self, 'current_curve'):
                    self.current_curve = {'id': curve_id}
                
                # Update parent tab's current_curve as well
                if self.parent_tab and hasattr(self.parent_tab, 'current_curve'):
                    if self.parent_tab.current_curve:
                        self.parent_tab.current_curve['id'] = curve_id
                    else:
                        self.parent_tab.current_curve = {'id': curve_id}
                
                # Update segment dropdown to include the new curve
                self.load_available_segments()
                
                # Update parent tab if available
                if self.parent_tab:
                    self.parent_tab.load_curves_for_well(self.well_id)
                    self.parent_tab.load_segments_for_well(self.well_id)
            else:
                QMessageBox.warning(self, "Save Failed", 
                    "Failed to save the curve to database.")
                    
        except Exception as e:
            logger.error(f"Error saving curve from dialog: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save curve: {str(e)}")
    
    def save_curve(self):
        """Save the current curve - wrapper for save_curve_from_dialog."""
        return self.save_curve_from_dialog()
    
    def calculate_manual_r_squared(self):
        """Calculate R² for manually set parameters."""
        try:
            import numpy as np
            
            if len(self.times_array) == 0 or not self.fitted_params:
                return
                
            # Calculate predicted values using manual parameters
            if self.curve_type == 'exponential':
                y_pred = self.fitted_params[0] * (1 - np.exp(-self.fitted_params[1] * self.times_array))
            elif self.curve_type == 'power':
                y_pred = self.fitted_params[0] * np.power(np.maximum(self.times_array, 0.001), self.fitted_params[1])
            else:  # linear
                y_pred = self.fitted_params[0] - self.fitted_params[1] * self.times_array
            
            # Calculate R²
            ss_res = np.sum((self.normalized_array - y_pred) ** 2)
            ss_tot = np.sum((self.normalized_array - np.mean(self.normalized_array)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Update curve data
            if not self.curve_data:
                self.curve_data = {}
            
            self.curve_data['r_squared'] = max(0, r_squared)  # Ensure non-negative
            self.curve_data['parameters'] = self.manual_params
            self.curve_data['curve_type'] = self.curve_type
            
        except Exception as e:
            logger.error(f"Error calculating manual R²: {e}")
    
    def load_existing_parameters(self):
        """Load parameters from existing curve."""
        try:
            if not self.initial_params:
                return
                
            # Set parameter values based on curve type
            if self.curve_type == 'exponential':
                self.param_a.setValue(self.initial_params.get('a', 1.0))
                self.param_b.setValue(self.initial_params.get('b', 0.1))
            elif self.curve_type == 'power':
                self.param_a.setValue(self.initial_params.get('a', 1.0))
                self.param_b.setValue(self.initial_params.get('b', 0.5))
            else:  # linear
                self.param_a.setValue(self.initial_params.get('intercept', 0.0))
                self.param_b.setValue(self.initial_params.get('slope', 0.1))
            
            # Perform initial fit with loaded parameters
            self.fit_curve_with_params()
            self.update_plot()
            
        except Exception as e:
            logger.error(f"Error loading existing parameters: {e}")

