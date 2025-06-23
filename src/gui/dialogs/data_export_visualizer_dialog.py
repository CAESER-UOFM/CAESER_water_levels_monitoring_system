# src/gui/dialogs/data_export_visualizer_dialog.py

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np
from scipy import stats

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QDateEdit, QSplitter, QFileDialog, QMessageBox, 
    QWidget, QColorDialog, QButtonGroup, QRadioButton, QAbstractItemView, QLineEdit, QHeaderView,
    QShortcut, QStatusBar, QFrame
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QKeySequence

from ..handlers.water_level_plot_handler import WaterLevelPlotHandler
import logging

logger = logging.getLogger(__name__)

class DataExportVisualizerDialog(QDialog):
    """Dialog for visualizing and exporting water level data."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.db_path = str(self.db_manager.current_db)
        self.selected_wells = []
        self.well_colors = {}  # Dictionary to store custom colors for wells
        self.well_line_widths = {}  # Dictionary to store custom line widths
        self.well_line_styles = {}  # Dictionary to store custom line styles for wells
        self.date_range = {'start': None, 'end': None}
        self.theme = "light"  # Default theme
        self.color_theme = "blue"  # Default color theme
        
        self.setup_ui()
        self.load_wells()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Initialize plot axes before applying theme
        self.plot_handler.add_axes()
        
        # Apply initial theme
        self.apply_theme()
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts for common operations."""
        # Refresh data
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.load_wells)
        
        # Toggle theme
        theme_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        theme_shortcut.activated.connect(self.cycle_themes)
        
        # Auto date range
        auto_date_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        auto_date_shortcut.activated.connect(self.set_auto_date_range)
        
        # Fullscreen
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
    
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Water Level Visualizer & Data Export")
        self.resize(1400, 900)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Create a header with logo and title
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title_label = QLabel("Water Level Data Visualizer")
        title_label.setObjectName("headerTitle")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Theme selection in header
        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(5)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light Theme", "Dark Theme", "Blue Theme", "Earth Theme"])
        self.theme_combo.setCurrentIndex(0)
        self.theme_combo.setToolTip("Select visual theme")
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        self.theme_combo.setMaximumWidth(120)
        theme_layout.addWidget(self.theme_combo)
        
        header_layout.addLayout(theme_layout)
        main_layout.addWidget(header_widget)
        
        # Add a line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("headerLine")
        main_layout.addWidget(line)
        
        # Create a vertical splitter for the main components
        main_splitter = QSplitter(Qt.Vertical)
        
        # Upper section with well selection and plot
        upper_widget = QWidget()
        upper_layout = QVBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a horizontal splitter for the well table and plot
        upper_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - ONLY Well selection table
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Well selection table
        well_group = QGroupBox("Available Wells")
        well_layout = QVBoxLayout(well_group)
        
        self.well_table = QTableWidget()
        self.well_table.setColumnCount(5)  # We'll adjust the actual columns in load_wells
        self.well_table.setHorizontalHeaderLabels(["Well Number", "CAESER Number", "Wellfield", "Aquifer", "TOC"])
        self.well_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.well_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.well_table.selectionModel().selectionChanged.connect(self.on_well_selection_changed)
        well_layout.addWidget(self.well_table)
        
        # Add search/filter options
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_input = QComboBox()
        self.filter_input.setEditable(True)
        self.filter_input.editTextChanged.connect(self.filter_wells)
        filter_layout.addWidget(self.filter_input)
        well_layout.addLayout(filter_layout)
        
        left_layout.addWidget(well_group)
        
        # Add left panel to splitter - ONLY contains well selection now
        upper_splitter.addWidget(left_panel)
        
        # Right panel - Plot area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Matplotlib figure and canvas
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.plot_handler = WaterLevelPlotHandler(self.figure, self.canvas)
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)
        
        # Add right panel to splitter
        upper_splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (30% left, 70% right)
        upper_splitter.setSizes([300, 700])
        
        upper_layout.addWidget(upper_splitter)
        main_splitter.addWidget(upper_widget)
        
        # Lower section with ALL control panels now in a single row
        lower_widget = QWidget()
        lower_layout = QHBoxLayout(lower_widget)
        lower_layout.setContentsMargins(5, 5, 5, 5)
        lower_layout.setSpacing(8)  # Slightly increased spacing between panels for better separation
        
        # Explicitly set widths for panels to prevent overlapping
        # Define a consistent width for all panels
        panel_width = 200  # Base width for control panels
        
        # 1. Data Controls panel
        viz_group = QGroupBox("Data Controls")
        viz_group.setMinimumWidth(panel_width)
        viz_layout = QVBoxLayout(viz_group)
        viz_layout.setContentsMargins(5, 15, 5, 5)  # Increased top margin to account for title
        viz_layout.setSpacing(4)  # Slightly increased spacing
        
        # Data type selection
        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(QLabel("Data:"))  # Shorter label
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["Water Level", "Temperature"])
        self.data_type_combo.currentIndexChanged.connect(self.update_plot)
        data_type_layout.addWidget(self.data_type_combo)
        viz_layout.addLayout(data_type_layout)
        
        # Add downsampling in same panel but more compact
        downsample_layout = QHBoxLayout()
        downsample_layout.addWidget(QLabel("Sample:"))
        self.downsample_combo = QComboBox()
        self.downsample_combo.addItems([
            "No Downsampling", "30 Minutes", "1 Hour", "2 Hours", 
            "6 Hours", "12 Hours", "1 Day", "1 Week", "1 Month"
        ])
        self.downsample_combo.currentIndexChanged.connect(self.update_plot)
        downsample_layout.addWidget(self.downsample_combo)
        viz_layout.addLayout(downsample_layout)
        
        # Add aggregation method option under downsampling
        agg_layout = QHBoxLayout()
        agg_layout.addWidget(QLabel("Method:"))
        self.aggregate_combo = QComboBox()
        self.aggregate_combo.addItems(["Mean", "Median", "Min", "Max"])
        self.aggregate_combo.currentIndexChanged.connect(self.update_plot)
        agg_layout.addWidget(self.aggregate_combo)
        viz_layout.addLayout(agg_layout)
        
        lower_layout.addWidget(viz_group)
        
        # 2. Date Range panel
        date_range_group = QGroupBox("Date Range")
        date_range_group.setMinimumWidth(panel_width)
        date_range_layout = QVBoxLayout(date_range_group)
        date_range_layout.setContentsMargins(5, 15, 5, 5)
        date_range_layout.setSpacing(4)
        
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("Start:"))  # Shorter label
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_edit.dateChanged.connect(lambda date: self.update_date_range('start', date))
        start_date_layout.addWidget(self.start_date_edit)
        date_range_layout.addLayout(start_date_layout)
        
        end_date_layout = QHBoxLayout()
        end_date_layout.addWidget(QLabel("End:"))  # Shorter label
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(lambda date: self.update_date_range('end', date))
        end_date_layout.addWidget(self.end_date_edit)
        date_range_layout.addLayout(end_date_layout)
        
        # Auto range button on its own row
        auto_range_btn = QPushButton("Auto Range")  # Shorter text
        auto_range_btn.setToolTip("Set date range based on available data in selected wells")
        auto_range_btn.clicked.connect(self.set_auto_date_range)
        date_range_layout.addWidget(auto_range_btn)
        
        lower_layout.addWidget(date_range_group)
        
        # 3. Plot Style panel
        style_group = QGroupBox("Plot Style")
        style_group.setMinimumWidth(panel_width - 10)  # Slightly smaller for balance
        style_layout = QVBoxLayout(style_group)
        style_layout.setContentsMargins(5, 15, 5, 5)
        style_layout.setSpacing(4)
        
        # Checkboxes in a more compact layout
        checkbox_layout = QHBoxLayout()
        self.show_manual_cb = QCheckBox("Manual")  # Shorter text
        self.show_manual_cb.setToolTip("Show Manual Readings")
        self.show_manual_cb.setChecked(True)
        self.show_manual_cb.stateChanged.connect(self.update_plot)
        checkbox_layout.addWidget(self.show_manual_cb)
        
        self.show_grid_cb = QCheckBox("Grid")  # Shorter text
        self.show_grid_cb.setToolTip("Show Grid Lines")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.stateChanged.connect(self.update_plot)
        checkbox_layout.addWidget(self.show_grid_cb)
        
        # Add theme toggle
        self.theme_cb = QCheckBox("Dark Theme")
        self.theme_cb.setToolTip("Toggle Dark/Light Theme")
        self.theme_cb.stateChanged.connect(self.toggle_theme)
        checkbox_layout.addWidget(self.theme_cb)
        
        style_layout.addLayout(checkbox_layout)
        
        # Line width in a compact layout
        line_width_layout = QHBoxLayout()
        line_width_layout.addWidget(QLabel("Width:"))
        self.line_width_spinner = QDoubleSpinBox()
        self.line_width_spinner.setRange(0.5, 5.0)
        self.line_width_spinner.setSingleStep(0.5)
        self.line_width_spinner.setValue(1.5)
        self.line_width_spinner.valueChanged.connect(self.update_plot)
        line_width_layout.addWidget(self.line_width_spinner)
        style_layout.addLayout(line_width_layout)
        
        lower_layout.addWidget(style_group)
        
        # 4. Labels and Legend panel
        label_group = QGroupBox("Labels & Legend")
        label_group.setMinimumWidth(panel_width + 20)  # Slightly wider for font control
        label_layout = QVBoxLayout(label_group)
        label_layout.setContentsMargins(5, 15, 5, 5)
        label_layout.setSpacing(4)
        
        # More compact label options
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Plot title")
        self.title_edit.textChanged.connect(self.update_plot)
        title_layout.addWidget(self.title_edit)
        label_layout.addLayout(title_layout)
        
        # Y and X labels on same row to save space
        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel("Y:"))
        self.y_label_edit = QLineEdit()
        self.y_label_edit.setPlaceholderText("Y-axis")
        self.y_label_edit.setMaximumWidth(80)
        self.y_label_edit.textChanged.connect(self.update_plot)
        axis_layout.addWidget(self.y_label_edit)
        
        axis_layout.addWidget(QLabel("X:"))
        self.x_label_edit = QLineEdit()
        self.x_label_edit.setPlaceholderText("X-axis")
        self.x_label_edit.setMaximumWidth(80)
        self.x_label_edit.textChanged.connect(self.update_plot)
        axis_layout.addWidget(self.x_label_edit)
        label_layout.addLayout(axis_layout)
        
        # Font size controls - NEW ADDITION
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font:"))
        self.font_size_spinner = QSpinBox()
        self.font_size_spinner.setRange(6, 24)
        self.font_size_spinner.setValue(10)
        self.font_size_spinner.setSingleStep(1)
        self.font_size_spinner.valueChanged.connect(self.update_plot)
        self.font_size_spinner.setToolTip("Change font size for plot labels")
        font_size_layout.addWidget(self.font_size_spinner)
        label_layout.addLayout(font_size_layout)
        
        # Legend position
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend:"))
        self.legend_pos_combo = QComboBox()
        self.legend_pos_combo.addItems([
            "Best", "Upper Right", "Upper Left", "Lower Left", "Lower Right", 
            "Right", "Outside"  # Reduced options to save space
        ])
        self.legend_pos_combo.currentIndexChanged.connect(self.update_plot)
        legend_layout.addWidget(self.legend_pos_combo)
        label_layout.addLayout(legend_layout)
        
        lower_layout.addWidget(label_group)
        
        # 5. Well Style Customization panel
        custom_style_group = QGroupBox("Well Styling")
        custom_style_group.setMinimumWidth(panel_width + 10)
        custom_style_layout = QVBoxLayout(custom_style_group)
        custom_style_layout.setContentsMargins(5, 15, 5, 5)
        custom_style_layout.setSpacing(4)
        
        self.custom_well_combo = QComboBox()
        self.custom_well_combo.setEnabled(False)
        self.custom_well_combo.currentTextChanged.connect(self.on_custom_well_changed)
        custom_style_layout.addWidget(self.custom_well_combo)
        
        # Put color and line style on one row
        style_controls_layout = QHBoxLayout()
        
        self.color_button = QPushButton("Color")
        self.color_button.setEnabled(False)
        self.color_button.clicked.connect(self.select_well_color)
        self.color_button.setMaximumWidth(60)
        style_controls_layout.addWidget(self.color_button)
        
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["Solid", "Dashed", "Dotted", "Dash-Dot", "None"])
        self.line_style_combo.setEnabled(False)
        self.line_style_combo.currentIndexChanged.connect(self.update_well_style)
        style_controls_layout.addWidget(self.line_style_combo)
        
        custom_style_layout.addLayout(style_controls_layout)
        
        # Width control
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.custom_width_spinner = QDoubleSpinBox()
        self.custom_width_spinner.setRange(0.5, 5.0)
        self.custom_width_spinner.setSingleStep(0.5)
        self.custom_width_spinner.setValue(1.5)
        self.custom_width_spinner.setEnabled(False)
        self.custom_width_spinner.valueChanged.connect(self.update_well_style)
        width_layout.addWidget(self.custom_width_spinner)
        custom_style_layout.addLayout(width_layout)
        
        lower_layout.addWidget(custom_style_group)
        
        # 6. Trend Analysis panel
        trend_group = QGroupBox("Trend Analysis")
        trend_group.setMinimumWidth(panel_width + 15)
        trend_layout = QVBoxLayout(trend_group)
        trend_layout.setContentsMargins(5, 15, 5, 5)
        trend_layout.setSpacing(4)
        
        # Trend line options
        trend_line_layout = QHBoxLayout()
        self.show_trend_cb = QCheckBox("Show Trend")
        self.show_trend_cb.setToolTip("Show trend line for water level data")
        self.show_trend_cb.stateChanged.connect(self.update_plot)
        trend_line_layout.addWidget(self.show_trend_cb)
        
        self.trend_type_combo = QComboBox()
        self.trend_type_combo.addItems(["Linear", "Polynomial"])
        self.trend_type_combo.setToolTip("Select trend line type")
        self.trend_type_combo.setEnabled(False)
        self.trend_type_combo.currentIndexChanged.connect(self.update_plot)
        trend_line_layout.addWidget(self.trend_type_combo)
        
        # Connect trend checkbox to enable/disable trend type
        self.show_trend_cb.toggled.connect(self.trend_type_combo.setEnabled)
        
        trend_layout.addLayout(trend_line_layout)
        
        # Moving average option
        ma_layout = QHBoxLayout()
        self.show_ma_cb = QCheckBox("Moving Avg")
        self.show_ma_cb.setToolTip("Show moving average")
        self.show_ma_cb.stateChanged.connect(self.update_plot)
        ma_layout.addWidget(self.show_ma_cb)
        
        self.ma_window_spin = QSpinBox()
        self.ma_window_spin.setRange(2, 30)
        self.ma_window_spin.setValue(7)
        self.ma_window_spin.setEnabled(False)
        self.ma_window_spin.setToolTip("Window size (days)")
        self.ma_window_spin.valueChanged.connect(self.update_plot)
        ma_layout.addWidget(self.ma_window_spin)
        
        # Connect moving average checkbox to enable/disable window size
        self.show_ma_cb.toggled.connect(self.ma_window_spin.setEnabled)
        
        trend_layout.addLayout(ma_layout)
        
        lower_layout.addWidget(trend_group)
        
        # 7. Export Options panel
        export_group = QGroupBox("Export")
        export_group.setMinimumWidth(panel_width - 50)  # Export panel can be narrower
        export_layout = QVBoxLayout(export_group)
        export_layout.setContentsMargins(5, 15, 5, 5)
        export_layout.setSpacing(5)
        
        export_data_btn = QPushButton("To CSV")
        export_data_btn.setToolTip("Export Data to CSV")
        export_data_btn.clicked.connect(self.export_to_csv)
        export_layout.addWidget(export_data_btn)
        
        export_image_btn = QPushButton("To Image")
        export_image_btn.setToolTip("Export Plot as Image")
        export_image_btn.clicked.connect(self.export_plot_image)
        export_layout.addWidget(export_image_btn)
        
        lower_layout.addWidget(export_group)
        
        main_splitter.addWidget(lower_widget)
        
        # Set main splitter sizes (85% upper, 15% lower) - reduced height for controls
        main_splitter.setSizes([765, 135])
        
        # Add main splitter to main layout
        main_layout.addWidget(main_splitter)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        main_layout.addWidget(self.status_bar)
        
        # Add buttons at the bottom
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton(" Refresh Data")
        refresh_btn.setObjectName("actionButton")
        refresh_btn.setToolTip("Reload all data (F5)")
        refresh_btn.clicked.connect(self.load_wells)
        button_layout.addWidget(refresh_btn)
        
        # Add a button to toggle fullscreen
        fullscreen_btn = QPushButton(" Toggle Fullscreen")
        fullscreen_btn.setObjectName("secondaryButton")
        fullscreen_btn.setToolTip("Toggle fullscreen mode (F11)")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        button_layout.addWidget(fullscreen_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton(" Close")
        close_btn.setObjectName("closeButton")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
        # Initialize plot handler
        self.update_date_range('start', self.start_date_edit.date())
        self.update_date_range('end', self.end_date_edit.date())
        
        # Add tooltips to all controls for better usability
        self.add_tooltips()
        
        # Show status message with key shortcuts
        self.status_bar.showMessage("Ready - F5: Refresh | Ctrl+T: Toggle Theme | F11: Fullscreen | Ctrl+D: Auto Date Range")
    
    def add_tooltips(self):
        """Add helpful tooltips to UI controls."""
        self.well_table.setToolTip("Select wells to display (hold Ctrl/Shift for multiple)")
        self.filter_input.setToolTip("Filter wells by name")
        self.data_type_combo.setToolTip("Select data type to display")
        self.downsample_combo.setToolTip("Reduce data points for faster rendering")
        self.aggregate_combo.setToolTip("Method to aggregate downsampled data")
        self.start_date_edit.setToolTip("Start date for data display")
        self.end_date_edit.setToolTip("End date for data display")
        self.show_trend_cb.setToolTip("Show statistical trend line")
        self.show_ma_cb.setToolTip("Show moving average")
        self.title_edit.setToolTip("Set custom plot title")
        self.y_label_edit.setToolTip("Set custom Y-axis label")
        self.x_label_edit.setToolTip("Set custom X-axis label")
        
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.status_bar.showMessage("Exited fullscreen mode")
        else:
            self.showFullScreen()
            self.status_bar.showMessage("Entered fullscreen mode - Press F11 to exit")
    
    def cycle_themes(self):
        """Cycle through available themes."""
        themes = ["Light Theme", "Dark Theme", "Blue Theme", "Earth Theme"]
        current_index = self.theme_combo.currentIndex()
        next_index = (current_index + 1) % len(themes)
        self.theme_combo.setCurrentIndex(next_index)
    
    def on_theme_changed(self, index):
        """Handle theme combo box changes."""
        theme_map = {
            0: ("light", "blue"),    # Light Theme
            1: ("dark", "blue"),     # Dark Theme
            2: ("light", "blue"),    # Blue Theme
            3: ("light", "earth")    # Earth Theme
        }
        
        self.theme, self.color_theme = theme_map.get(index, ("light", "blue"))
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the selected theme to the UI."""
        # Base styling for controls
        button_style = """
            QPushButton {
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(dark);
            }
        """
        
        # Theme-specific styling
        if self.theme == "dark":
            # Dark theme
            self.setStyleSheet(f"""
                QWidget {{ background-color: #222233; color: #E1E1E1; }}
                QDialog {{ background-color: #222233; color: #E1E1E1; }}
                QTableWidget {{ 
                    background-color: #2D2D44; 
                    color: #E1E1E1; 
                    gridline-color: #444466;
                    border-radius: 4px;
                    border: 1px solid #444466;
                }}
                QTableWidget::item:selected {{ 
                    background-color: #3F3F66; 
                    color: white;
                }}
                QHeaderView::section {{ 
                    background-color: #3F3F66; 
                    color: #E1E1E1; 
                    padding: 5px;
                    border: none;
                }}
                QGroupBox {{ 
                    border: 1px solid #444466; 
                    border-radius: 4px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #E1E1E1; 
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                }}
                QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{ 
                    background-color: #333355; 
                    color: #E1E1E1; 
                    border: 1px solid #444466;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
                    border: 1px solid #5555AA;
                }}
                QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                    border: 1px solid #7777FF;
                }}
                QPushButton#actionButton {{ 
                    background-color: #4455BB; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#secondaryButton {{ 
                    background-color: #445588; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#closeButton {{ 
                    background-color: #774455; 
                    color: white; 
                    {button_style}
                }}
                QCheckBox {{ color: #E1E1E1; }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #555577;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #5555AA;
                }}
                QStatusBar {{ 
                    background-color: #2F2F44; 
                    color: #AAAACC;
                    border-top: 1px solid #444466;
                }}
                QLabel#headerTitle {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #AAAAFF;
                }}
                QFrame#headerLine {{
                    color: #444466;
                }}
                QSplitter::handle {{
                    background-color: #444466;
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:vertical {{
                    height: 2px;
                }}
                QScrollBar:vertical {{
                    background-color: #2D2D44;
                    width: 12px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #444466;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #5555AA;
                }}
            """)
            
            # Make sure ax exists before accessing it
            if hasattr(self.plot_handler, 'ax'):
                # Apply dark background to matplotlib figure
                self.figure.patch.set_facecolor('#222233')
                self.plot_handler.ax.set_facecolor('#2D2D44')
                self.plot_handler.ax.tick_params(colors='#E1E1E1')
                self.plot_handler.ax.xaxis.label.set_color('#E1E1E1')
                self.plot_handler.ax.yaxis.label.set_color('#E1E1E1')
                self.plot_handler.ax.title.set_color('#AAAAFF')
                for spine in self.plot_handler.ax.spines.values():
                    spine.set_color('#444466')
                
                # Set grid style for dark theme
                self.plot_handler.ax.grid(True, linestyle='--', alpha=0.5, color='#444466')
            
        elif self.color_theme == "blue" and self.theme == "light":
            # Blue theme (light)
            self.setStyleSheet(f"""
                QWidget {{ background-color: #F0F4F8; color: #333344; }}
                QDialog {{ background-color: #F0F4F8; color: #333344; }}
                QTableWidget {{ 
                    background-color: white; 
                    color: #333344;
                    gridline-color: #DDDDEE;
                    border-radius: 4px;
                    border: 1px solid #CCDDEE;
                }}
                QTableWidget::item:selected {{ 
                    background-color: #3070B0; 
                    color: white;
                }}
                QHeaderView::section {{ 
                    background-color: #CCDDEE; 
                    color: #333366; 
                    padding: 5px;
                    border: none;
                }}
                QGroupBox {{ 
                    border: 1px solid #CCDDEE; 
                    border-radius: 4px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #3070B0; 
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                }}
                QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{ 
                    background-color: white; 
                    color: #333344; 
                    border: 1px solid #CCDDEE;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
                    border: 1px solid #99BBDD;
                }}
                QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                    border: 1px solid #3070B0;
                }}
                QPushButton#actionButton {{ 
                    background-color: #3070B0; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#secondaryButton {{ 
                    background-color: #5090D0; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#closeButton {{ 
                    background-color: #B03050; 
                    color: white; 
                    {button_style}
                }}
                QCheckBox {{ color: #333344; }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #AABBCC;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #3070B0;
                }}
                QStatusBar {{ 
                    background-color: #E0E8F0; 
                    color: #335588;
                    border-top: 1px solid #CCDDEE;
                }}
                QLabel#headerTitle {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #3070B0;
                }}
                QFrame#headerLine {{
                    color: #CCDDEE;
                }}
                QSplitter::handle {{
                    background-color: #CCDDEE;
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:vertical {{
                    height: 2px;
                }}
                QScrollBar:vertical {{
                    background-color: #F0F4F8;
                    width: 12px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #CCDDEE;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #3070B0;
                }}
            """)
            
            # Make sure ax exists before accessing it
            if hasattr(self.plot_handler, 'ax'):
                # Apply light blue-themed background to matplotlib figure
                self.figure.patch.set_facecolor('#F0F4F8')
                self.plot_handler.ax.set_facecolor('#FFFFFF')
                self.plot_handler.ax.tick_params(colors='#333344')
                self.plot_handler.ax.xaxis.label.set_color('#3070B0')
                self.plot_handler.ax.yaxis.label.set_color('#3070B0')
                self.plot_handler.ax.title.set_color('#3070B0')
                for spine in self.plot_handler.ax.spines.values():
                    spine.set_color('#CCDDEE')
                
                # Set grid style
                self.plot_handler.ax.grid(True, linestyle='--', alpha=0.5, color='#CCDDEE')
            
        elif self.color_theme == "earth":
            # Earth tones theme
            self.setStyleSheet(f"""
                QWidget {{ background-color: #F5F5F0; color: #333322; }}
                QDialog {{ background-color: #F5F5F0; color: #333322; }}
                QTableWidget {{ 
                    background-color: white; 
                    color: #333322;
                    gridline-color: #DDDDCC;
                    border-radius: 4px;
                    border: 1px solid #CCBB99;
                }}
                QTableWidget::item:selected {{ 
                    background-color: #8B7355; 
                    color: white;
                }}
                QHeaderView::section {{ 
                    background-color: #E8E0D0; 
                    color: #554433; 
                    padding: 5px;
                    border: none;
                }}
                QGroupBox {{ 
                    border: 1px solid #CCBB99; 
                    border-radius: 4px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #8B7355; 
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                }}
                QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{ 
                    background-color: white; 
                    color: #333322; 
                    border: 1px solid #CCBB99;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
                    border: 1px solid #AA9966;
                }}
                QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                    border: 1px solid #8B7355;
                }}
                QPushButton#actionButton {{ 
                    background-color: #8B7355; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#secondaryButton {{ 
                    background-color: #AA9977; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#closeButton {{ 
                    background-color: #AA5544; 
                    color: white; 
                    {button_style}
                }}
                QCheckBox {{ color: #333322; }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #BBAA88;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #8B7355;
                }}
                QStatusBar {{ 
                    background-color: #E8E0D0; 
                    color: #554433;
                    border-top: 1px solid #CCBB99;
                }}
                QLabel#headerTitle {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #8B7355;
                }}
                QFrame#headerLine {{
                    color: #CCBB99;
                }}
                QSplitter::handle {{
                    background-color: #CCBB99;
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:vertical {{
                    height: 2px;
                }}
                QScrollBar:vertical {{
                    background-color: #F5F5F0;
                    width: 12px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #CCBB99;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #8B7355;
                }}
            """)
            
            # Make sure ax exists before accessing it
            if hasattr(self.plot_handler, 'ax'):
                # Apply earth-toned background to matplotlib figure
                self.figure.patch.set_facecolor('#F5F5F0')
                self.plot_handler.ax.set_facecolor('#FFFFFF')
                self.plot_handler.ax.tick_params(colors='#333322')
                self.plot_handler.ax.xaxis.label.set_color('#8B7355')
                self.plot_handler.ax.yaxis.label.set_color('#8B7355')
                self.plot_handler.ax.title.set_color('#8B7355')
                for spine in self.plot_handler.ax.spines.values():
                    spine.set_color('#CCBB99')
                
                # Set grid style
                self.plot_handler.ax.grid(True, linestyle='--', alpha=0.5, color='#DDDDCC')
            
        else:
            # Default light theme
            self.setStyleSheet("")
            
            # Make sure ax exists before accessing it
            if hasattr(self.plot_handler, 'ax'):
                # Reset matplotlib figure to light theme
                self.figure.patch.set_facecolor('#FFFFFF')
                self.plot_handler.ax.set_facecolor('#FFFFFF')
                self.plot_handler.ax.tick_params(colors='black')
                self.plot_handler.ax.xaxis.label.set_color('black')
                self.plot_handler.ax.yaxis.label.set_color('black')
                self.plot_handler.ax.title.set_color('black')
                for spine in self.plot_handler.ax.spines.values():
                    spine.set_color('black')
                
                # Set standard grid
                self.plot_handler.ax.grid(self.show_grid_cb.isChecked(), linestyle='--', alpha=0.7)
        
        # Update the theme checkbox state to match the current theme
        self.theme_cb.setChecked(self.theme == "dark")
        
        # Update plot to apply theme only if there are selected wells
        if self.selected_wells:
            self.update_plot()
        
        # Update status bar message
        self.status_bar.showMessage(f"Theme changed to {self.theme.capitalize()} {self.color_theme.capitalize()}")
        
    def toggle_theme(self, state=None):
        """Toggle between light and dark theme."""
        # This method is kept for backward compatibility
        if state is not None:
            self.theme = "dark" if state == Qt.Checked else "light"
        else:
            # Toggle when called directly
            self.theme = "dark" if self.theme == "light" else "light"
            self.theme_cb.setChecked(self.theme == "dark")
        
        # Update theme combo box to match
        theme_index = 1 if self.theme == "dark" else 0
        self.theme_combo.setCurrentIndex(theme_index)
        
        # Apply the theme
        self.apply_theme()
    
    def load_wells(self):
        """Load available wells from the database with proper column checking."""
        try:
            self.well_table.setRowCount(0)  # Clear table
            self.well_table.setSortingEnabled(False)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, check what columns actually exist in the wells table
                cursor.execute("PRAGMA table_info(wells)")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]
                
                # Set table columns based on available database columns
                available_columns = ["well_number"]  # Always include well_number
                display_names = ["Well Number"]
                
                # Check for optional columns
                column_mappings = {
                    "caesar_number": "CAESER Number",
                    "wellfield": "Wellfield", 
                    "aquifer": "Aquifer", 
                    "toc": "TOC",
                    # Add more potential columns here if needed
                }
                
                for db_col, display_name in column_mappings.items():
                    if db_col in column_names:
                        available_columns.append(db_col)
                        display_names.append(display_name)
                
                # Set up table with available columns
                self.well_table.setColumnCount(len(available_columns))
                self.well_table.setHorizontalHeaderLabels(display_names)
                
                # Build query dynamically based on available columns
                query = f"SELECT {', '.join(available_columns)} FROM wells ORDER BY well_number"
                cursor.execute(query)
                wells = cursor.fetchall()
                
                for i, row_data in enumerate(wells):
                    self.well_table.insertRow(i)
                    
                    # Add columns from results
                    for j, value in enumerate(row_data):
                        item = QTableWidgetItem(str(value) if value is not None else "")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.well_table.setItem(i, j, item)
                    
                    # Add to filter dropdown as well (only well number)
                    if i == 0:  # Only clear the first time
                        self.filter_input.clear()
                    self.filter_input.addItem(row_data[0])  # well_number is always the first column
            
            # Adjust column widths
            header = self.well_table.horizontalHeader()
            for i in range(self.well_table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            
            self.well_table.setSortingEnabled(True)
            logger.info(f"Loaded {len(wells)} wells from database")
            
            # Resize columns to content
            self.well_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error loading wells: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load wells: {str(e)}")
    
    def filter_wells(self, filter_text):
        """Filter the wells table based on the search text."""
        filter_text = filter_text.lower()
        for row in range(self.well_table.rowCount()):
            item = self.well_table.item(row, 0)
            if item:
                well_number = item.text().lower()
                self.well_table.setRowHidden(row, filter_text not in well_number)
    
    def on_well_selection_changed(self):
        """Handle well selection changes in the table."""
        self.selected_wells = []
        for item in self.well_table.selectedItems():
            well_number = item.text()
            if well_number not in self.selected_wells:
                self.selected_wells.append(well_number)
        
        # Update the custom well combo box
        self.custom_well_combo.clear()
        if self.selected_wells:
            self.custom_well_combo.addItems(self.selected_wells)
            self.custom_well_combo.setEnabled(True)
            self.color_button.setEnabled(True)
            self.custom_width_spinner.setEnabled(True)
            self.line_style_combo.setEnabled(True)  # Enable line style selection
        else:
            self.custom_well_combo.setEnabled(False)
            self.color_button.setEnabled(False)
            self.custom_width_spinner.setEnabled(False)
            self.line_style_combo.setEnabled(False)  # Disable line style selection
        
        # Update the plot
        self.update_plot()
    
    def on_custom_well_changed(self, well_name):
        """Update the style controls when a different well is selected in the customization dropdown."""
        if not well_name:
            return
            
        # Update width spinner to show current value for this well
        if well_name in self.well_line_widths:
            self.custom_width_spinner.setValue(self.well_line_widths[well_name])
        else:
            self.custom_width_spinner.setValue(self.line_width_spinner.value())
            
        # Update line style combo to show current value for this well
        if well_name in self.well_line_styles:
            style_index = {
                '-': 0,      # Solid
                '--': 1,     # Dashed
                ':': 2,      # Dotted
                '-.': 3,     # Dash-Dot
                'None': 4    # None
            }.get(self.well_line_styles[well_name], 0)
            self.line_style_combo.setCurrentIndex(style_index)
        else:
            self.line_style_combo.setCurrentIndex(0)  # Default to solid
    
    def update_date_range(self, which, qdate):
        """Update the date range for plotting."""
        py_date = qdate.toPyDate()
        self.date_range[which] = py_date
        
        # Update the plot if both dates are set
        if self.date_range['start'] and self.date_range['end']:
            self.update_plot()
    
    def select_well_color(self):
        """Open color dialog to select a color for the selected well."""
        well = self.custom_well_combo.currentText()
        if not well:
            return
        
        # Get current color if already set, otherwise use default
        current_color = self.well_colors.get(well, QColor(31, 119, 180))  # Default matplotlib blue
        
        color = QColorDialog.getColor(current_color, self, "Select Color for " + well)
        if color.isValid():
            self.well_colors[well] = color
            
            # Update the color button background to show selected color
            self.color_button.setStyleSheet(f"background-color: {color.name()};")
            
            self.update_plot()
    
    def update_well_style(self):
        """Update the style for the selected well."""
        well = self.custom_well_combo.currentText()
        if not well:
            return
        
        # Store the custom line width
        self.well_line_widths[well] = self.custom_width_spinner.value()
        
        # Store the custom line style
        style_index = self.line_style_combo.currentIndex()
        line_style = ['-', '--', ':', '-.', 'None'][style_index]
        self.well_line_styles[well] = line_style
        
        self.update_plot()
    
    def downsample_dataframe(self, df, interval):
        """Downsample a dataframe to the specified interval."""
        if df.empty or interval == "No Downsampling":
            return df
            
        # Map interval names to pandas resample rule strings
        interval_map = {
            "30 Minutes": "30T",
            "1 Hour": "1H",
            "2 Hours": "2H",
            "6 Hours": "6H",
            "12 Hours": "12H",
            "1 Day": "1D",
            "1 Week": "1W",
            "1 Month": "1M"
        }
        
        # Map aggregation method names to pandas functions
        method_map = {
            "Mean": "mean",
            "Median": "median",
            "Min": "min",
            "Max": "max"
        }
        
        rule = interval_map.get(interval)
        method = method_map.get(self.aggregate_combo.currentText(), "mean")
        
        if rule:
            # Set timestamp as index for resampling
            df = df.set_index('timestamp_utc')
            # Resample and aggregate using the selected method
            df = df.resample(rule).agg(method)
            # Reset index to get timestamp back as a column
            df = df.reset_index()
            
        return df
    
    def update_plot(self):
        """Update the plot with the selected wells and settings."""
        print(f"\n--- Update Plot Called ---")
        print(f"Selected wells: {self.selected_wells}")
        print(f"Date range: {self.date_range}")
        print(f"Show temperature: {self.data_type_combo.currentText() == 'Temperature'}")
        
        if not self.selected_wells:
            self.plot_handler.clear_plot()
            self.canvas.draw()
            print("No wells selected, cleared plot and returned")
            return
        
        # Toggle temperature mode based on selection
        show_temperature = self.data_type_combo.currentText() == "Temperature"
        self.plot_handler.toggle_temperature(show_temperature)
        
        # Clear and update the plot
        self.plot_handler.clear_plot()
        self.plot_handler.add_axes()
        
        # Set font sizes first - NEW ADDITION
        font_size = self.font_size_spinner.value()
        plt.rcParams.update({
            'font.size': font_size,
            'axes.titlesize': font_size + 2,
            'axes.labelsize': font_size,
            'xtick.labelsize': font_size - 1,
            'ytick.labelsize': font_size - 1,
            'legend.fontsize': font_size - 1
        })
        
        try:
            # Get colors from a cycle
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                      '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            # Track if any plots were actually added
            plots_created = False
            
            # Get downsampling interval
            downsample_interval = self.downsample_combo.currentText()
            
            # Apply custom styling for each well
            for i, well_number in enumerate(self.selected_wells):
                print(f"\nProcessing well: {well_number}")
                # Get data for the selected date range
                df = self.get_well_data(well_number)
                
                if df.empty:
                    print(f"No data for well {well_number}, skipping")
                    continue
                
                # Apply downsampling if selected
                if downsample_interval != "No Downsampling":
                    df = self.downsample_dataframe(df, downsample_interval)
                    print(f"Downsampled to {downsample_interval}, resulting in {len(df)} rows")
                
                # FIXED: Improved date filtering logic 
                # Check if data is within the date range first
                earliest_date = df['timestamp_utc'].min().date()
                latest_date = df['timestamp_utc'].max().date()
                
                # Auto-adjust date range if needed and show notification
                date_adjusted = False
                if self.date_range['start'] and self.date_range['end']:
                    if earliest_date > self.date_range['end'] or latest_date < self.date_range['start']:
                        print(f"Warning: Data for {well_number} ({earliest_date} to {latest_date}) is outside selected date range")
                        self.status_bar.showMessage(f"Warning: Data for well {well_number} is outside the selected date range")
                    else:
                        # Apply date filtering
                        start_date = datetime.combine(self.date_range['start'], datetime.min.time())
                        end_date = datetime.combine(self.date_range['end'], datetime.max.time())
                        
                        # Adjust the date filter if necessary
                        if start_date.date() < earliest_date:
                            start_date = datetime.combine(earliest_date, datetime.min.time())
                            date_adjusted = True
                        
                        if end_date.date() > latest_date:
                            end_date = datetime.combine(latest_date, datetime.max.time())
                            date_adjusted = True
                        
                        print(f"Filtering data between {start_date} and {end_date}")
                        filtered_df = df[(df['timestamp_utc'] >= start_date) & (df['timestamp_utc'] <= end_date)]
                        print(f"Filtered from {len(df)} to {len(filtered_df)} rows")
                        df = filtered_df
                
                if date_adjusted:
                    print(f"Date range was adjusted to match available data for {well_number}")
                    self.status_bar.showMessage(f"Date range adjusted to match available data for {well_number}")
                
                if df.empty:
                    print(f"No data after filtering for well {well_number}, skipping")
                    continue
                
                # Get custom color for this well or use default from cycle
                if well_number in self.well_colors:
                    color = self.well_colors[well_number].name()
                else:
                    color = colors[i % len(colors)]
                
                # Get custom line width for this well or use default
                line_width = self.well_line_widths.get(well_number, self.line_width_spinner.value())
                
                # Get custom line style for this well or use default
                if well_number in self.well_line_styles:
                    line_style = self.well_line_styles[well_number]
                else:
                    line_style = '-'  # Default solid line
                
                print(f"Plotting {well_number} with color {color}, line width {line_width}, line style {line_style}")
                
                # Plot data based on selected type
                if show_temperature:
                    line = self.plot_handler.ax.plot(df['timestamp_utc'], df['temperature'], 
                                          color=color, label=f"{well_number}", 
                                          linewidth=line_width, linestyle=line_style)
                    print(f"Plotted temperature data, line object: {line}")
                else:
                    line = self.plot_handler.ax.plot(df['timestamp_utc'], df['water_level'], 
                                          color=color, label=f"{well_number}", 
                                          linewidth=line_width, linestyle=line_style)
                    print(f"Plotted water level data, line object: {line}")
                
                plots_created = True
                
                # Show trend line if enabled (only for water level data)
                if self.show_trend_cb.isChecked() and not show_temperature:
                    # Prepare time values as numeric for regression
                    x = np.array([(t - df['timestamp_utc'].iloc[0]).total_seconds() for t in df['timestamp_utc']])
                    y = df['water_level'].values
                    
                    if self.trend_type_combo.currentText() == "Linear":
                        # Linear regression
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                        trend_y = intercept + slope * x
                        
                        self.plot_handler.ax.plot(df['timestamp_utc'], trend_y, '--', 
                                          color=color, alpha=0.7, linewidth=1.0,
                                          label=f"{well_number} Trend (r²={r_value**2:.2f})")
                        
                        print(f"Added linear trend line with slope={slope:.6f}, r²={r_value**2:.4f}")
                    else:
                        # Polynomial regression (degree 2)
                        coeffs = np.polyfit(x, y, 2)
                        trend_y = np.polyval(coeffs, x)
                        
                        self.plot_handler.ax.plot(df['timestamp_utc'], trend_y, '--', 
                                          color=color, alpha=0.7, linewidth=1.0,
                                          label=f"{well_number} Poly Trend")
                        
                        print(f"Added polynomial trend line with coefficients: {coeffs}")
                
                # Show moving average if enabled (only for water level data)
                if self.show_ma_cb.isChecked() and not show_temperature:
                    window = self.ma_window_spin.value()
                    if len(df) > window:
                        # Calculate moving average
                        ma = df['water_level'].rolling(window=window, center=True).mean()
                        self.plot_handler.ax.plot(df['timestamp_utc'], ma, '-', 
                                          color=color, alpha=0.7, linewidth=1.5,
                                          label=f"{well_number} MA({window})")
                        
                        print(f"Added moving average with window={window}")
                
                # Get and plot manual readings if checkbox is checked
                if self.show_manual_cb.isChecked() and not show_temperature:
                    manual_readings = self.plot_handler.get_manual_readings(well_number, self.db_path)
                    print(f"Found {len(manual_readings)} manual readings for well {well_number}")
                    
                    if not manual_readings.empty:
                        # Apply date filtering to manual readings too
                        if self.date_range['start'] and self.date_range['end']:
                            start_date = datetime.combine(self.date_range['start'], datetime.min.time())
                            end_date = datetime.combine(self.date_range['end'], datetime.max.time())
                            filtered_manual = manual_readings[
                                (manual_readings['measurement_date_utc'] >= start_date) & 
                                (manual_readings['measurement_date_utc'] <= end_date)
                            ]
                            print(f"Filtered manual readings from {len(manual_readings)} to {len(filtered_manual)}")
                            manual_readings = filtered_manual
                        
                        if not manual_readings.empty:
                            # Use the same color for manual readings as the main line
                            scatter = self.plot_handler.ax.scatter(manual_readings['measurement_date_utc'],
                                                     manual_readings['water_level'],
                                                     color=color, marker='o', s=25, alpha=0.8,
                                                     edgecolor='black', linewidth=0.5,
                                                     label=f"{well_number} (Manual)")
                            print(f"Plotted manual readings, scatter object: {scatter}")
            
            # Apply custom labels if provided
            custom_title = self.title_edit.text().strip()
            custom_y_label = self.y_label_edit.text().strip()
            custom_x_label = self.x_label_edit.text().strip()
            
            # Set axis labels and title
            if show_temperature:
                self.plot_handler.ax.set_ylabel(custom_y_label if custom_y_label else 'Temperature (°C)')
                self.plot_handler.ax.set_title(custom_title if custom_title else 'Well Temperature Data')
            else:
                self.plot_handler.ax.set_ylabel(custom_y_label if custom_y_label else 'Water Level (ft)')
                self.plot_handler.ax.set_title(custom_title if custom_title else 'Well Water Level Data')
            
            self.plot_handler.ax.set_xlabel(custom_x_label if custom_x_label else 'Date/Time (UTC)')
            
            # Add grid if checked
            self.plot_handler.ax.grid(self.show_grid_cb.isChecked(), linestyle='--', alpha=0.7)
            
            # Format dates on x-axis
            self.plot_handler.format_date_axis()
            
            # Check for handles and labels before adding legend
            handles, labels = self.plot_handler.ax.get_legend_handles_labels()
            print(f"\nLegend handles: {handles}")
            print(f"Legend labels: {labels}")
            
            # Map legend position strings to matplotlib location codes
            legend_positions = {
                "Best": "best",
                "Upper Right": "upper right",
                "Upper Left": "upper left",
                "Lower Left": "lower left",
                "Lower Right": "lower right",
                "Right": "right",
                "Center Left": "center left",
                "Center Right": "center right", 
                "Lower Center": "lower center",
                "Upper Center": "upper center",
                "Center": "center",
                "Outside": "outside"
            }
            
            legend_pos = legend_positions.get(self.legend_pos_combo.currentText(), "best")
            
            # Add legend only if we have handles
            if handles:
                print(f"Adding legend with handles at position: {legend_pos}")
                if legend_pos == "outside":
                    self.plot_handler.ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
                else:
                    self.plot_handler.ax.legend(loc=legend_pos)
            else:
                print("WARNING: No handles found for legend!")
                if plots_created:
                    print("Plots were created but no handles were found - this is unexpected")
                    # Try manually getting lines from axis
                    lines = self.plot_handler.ax.get_lines()
                    print(f"Lines in the axes: {lines}")
                    if lines:
                        print("Forcing legend creation with existing lines")
                        self.plot_handler.ax.legend(lines, [line.get_label() for line in lines], loc='best')
            
            # Adjust layout
            self.figure.tight_layout()
            
            # Update canvas
            self.canvas.draw()
            print("Canvas updated")
            
            # Update status bar with plot info
            if plots_created:
                self.status_bar.showMessage(f"Displaying data for {len(self.selected_wells)} wells")
            else:
                # Enhanced error message
                if self.selected_wells:
                    range_text = f" in the date range {self.date_range['start']} - {self.date_range['end']}"
                    self.status_bar.showMessage(f"No data available for the selected wells{range_text}. Try adjusting the date range.")
                    
                    # Add a message on the plot too
                    self.plot_handler.ax.text(0.5, 0.5, 
                                            f"No data found in the selected date range.\n"
                                            f"The selected wells have data outside this period.\n"
                                            f"Try using the 'Auto Range' button.",
                                            ha='center', va='center', transform=self.plot_handler.ax.transAxes,
                                            bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.8))
                else:
                    self.status_bar.showMessage("No wells selected")
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            print(f"Exception in update_plot: {e}")
            import traceback
            traceback.print_exc()
            self.plot_handler.clear_plot()
            self.plot_handler.add_axes()
            self.plot_handler.ax.text(0.5, 0.5, f"Error: {str(e)}",
                                  ha='center', va='center', transform=self.plot_handler.ax.transAxes)
            self.canvas.draw()
            self.status_bar.showMessage(f"Error: {str(e)}")
    
    def get_well_data(self, well_number):
        """Get the water level data for a specific well."""
        try:
            print(f"Getting data for well: {well_number}")
            with sqlite3.connect(self.db_path) as conn:
                # Check if the well is a telemetry well
                cursor = conn.cursor()
                cursor.execute("SELECT data_source FROM wells WHERE well_number = ?", (well_number,))
                result = cursor.fetchone()
                data_source = result[0] if result else 'transducer'
                print(f"Well {well_number} data source: {data_source}")
                
                # Query based on data source
                if data_source == 'telemetry':
                    query = """
                        SELECT timestamp_utc, water_level, temperature
                        FROM telemetry_level_readings
                        WHERE well_number = ?
                        ORDER BY timestamp_utc
                    """
                else:
                    query = """
                        SELECT timestamp_utc, water_level, temperature
                        FROM water_level_readings
                        WHERE well_number = ?
                        ORDER BY timestamp_utc
                    """
                
                df = pd.read_sql_query(query, conn, params=(well_number,))
                print(f"Query returned {len(df)} rows for well {well_number}")
                
                if not df.empty:
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    print(f"Date range: {df['timestamp_utc'].min()} to {df['timestamp_utc'].max()}")
                    print(f"Water level range: {df['water_level'].min()} to {df['water_level'].max()}")
                    print(f"Temperature range: {df['temperature'].min()} to {df['temperature'].max()}")
                else:
                    print(f"No data returned for well {well_number}")
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting well data: {e}")
            print(f"Exception in get_well_data: {e}")
            return pd.DataFrame()
    
    def export_to_csv(self):
        """Export selected wells data to CSV."""
        if not self.selected_wells:
            QMessageBox.warning(self, "No Wells Selected", "Please select at least one well to export.")
            return
        
        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        
        try:
            # Progress counter
            total_exports = len(self.selected_wells)
            success_count = 0
            exported_files = []
            
            for well_number in self.selected_wells:
                # Get data for the selected well
                df = self.get_well_data(well_number)
                
                # Apply date filtering
                if not df.empty and self.date_range['start'] and self.date_range['end']:
                    start_date = datetime.combine(self.date_range['start'], datetime.min.time())
                    end_date = datetime.combine(self.date_range['end'], datetime.max.time())
                    df = df[(df['timestamp_utc'] >= start_date) & (df['timestamp_utc'] <= end_date)]
                
                if df.empty:
                    logger.warning(f"No data to export for well {well_number}")
                    continue
                
                # Create file name with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(output_dir, f"{well_number}_data_{timestamp}.csv")
                
                # Export to CSV
                df.to_csv(file_path, index=False)
                exported_files.append(os.path.basename(file_path))
                success_count += 1
                
                # Get manual readings too if showing them
                if self.show_manual_cb.isChecked():
                    manual_readings = self.plot_handler.get_manual_readings(well_number, self.db_path)
                    
                    # Apply date filtering to manual readings
                    if not manual_readings.empty and self.date_range['start'] and self.date_range['end']:
                        start_date = datetime.combine(self.date_range['start'], datetime.min.time())
                        end_date = datetime.combine(self.date_range['end'], datetime.max.time())
                        manual_readings = manual_readings[
                            (manual_readings['measurement_date_utc'] >= start_date) & 
                            (manual_readings['measurement_date_utc'] <= end_date)
                        ]
                    
                    # Export manual readings if available
                    if not manual_readings.empty:
                        manual_file_path = os.path.join(output_dir, f"{well_number}_manual_readings_{timestamp}.csv")
                        manual_readings.to_csv(manual_file_path, index=False)
                        exported_files.append(os.path.basename(manual_file_path))
            
            # Show success message with list of exported files
            if success_count > 0:
                files_text = "\n".join(exported_files[:5])
                if len(exported_files) > 5:
                    files_text += f"\n... and {len(exported_files) - 5} more files"
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Successfully exported data for {success_count} out of {total_exports} wells to {output_dir}.\n\n"
                                      f"Exported files:\n{files_text}")
            else:
                QMessageBox.warning(self, "Export Warning", 
                                  f"No data found to export for the selected wells in the specified date range.")
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export data: {str(e)}")
    
    def export_plot_image(self):
        """Export the current plot as an image."""
        if not self.selected_wells:
            QMessageBox.warning(self, "No Wells Selected", "Please select at least one well to export the plot.")
            return
        
        # Ask for output file
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Plot Image", "", 
                                                "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)")
        if not file_path:
            return
        
        try:
            # Get file extension
            _, ext = os.path.splitext(file_path)
            if not ext:
                file_path += ".png"
                ext = ".png"
            
            # Create a dialog to select resolution
            resolution_dialog = QDialog(self)
            resolution_dialog.setWindowTitle("Select Image Resolution")
            resolution_layout = QVBoxLayout(resolution_dialog)
            
            resolution_layout.addWidget(QLabel("Select Image Resolution (DPI):"))
            
            resolution_options = [("Low (100 DPI)", 100), 
                               ("Medium (300 DPI)", 300), 
                               ("High (600 DPI)", 600), 
                               ("Very High (1200 DPI)", 1200)]
            
            resolution_group = QButtonGroup(resolution_dialog)
            selected_dpi = 300  # Default to medium
            
            for i, (label, dpi) in enumerate(resolution_options):
                radio = QRadioButton(label)
                if i == 1:  # Medium is default
                    radio.setChecked(True)
                resolution_group.addButton(radio, dpi)
                resolution_layout.addWidget(radio)
            
            # Connect button group
            resolution_group.buttonClicked.connect(lambda button: setattr(resolution_dialog, 'selected_dpi', resolution_group.id(button)))
            resolution_dialog.selected_dpi = selected_dpi
            
            # Add OK button
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(resolution_dialog.accept)
            resolution_layout.addWidget(ok_btn)
            
            # Show dialog
            if resolution_dialog.exec_() == QDialog.Accepted:
                dpi = resolution_dialog.selected_dpi
                
                # Save current figure with selected resolution
                self.figure.savefig(file_path, dpi=dpi, bbox_inches='tight')
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Plot saved successfully as {file_path} at {dpi} DPI.")
            
        except Exception as e:
            logger.error(f"Error exporting plot: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export plot: {str(e)}")
    
    def set_auto_date_range(self):
        """Set the date range automatically based on available data for selected wells."""
        if not self.selected_wells:
            QMessageBox.warning(self, "No Wells Selected", "Please select at least one well first.")
            return
            
        try:
            # Find min and max dates across all selected wells
            min_date = None
            max_date = None
            data_found = False
            
            print("Setting auto date range for selected wells...")
            for well_number in self.selected_wells:
                df = self.get_well_data(well_number)
                
                if not df.empty:
                    data_found = True
                    well_min = df['timestamp_utc'].min().date()
                    well_max = df['timestamp_utc'].max().date()
                    
                    print(f"Well {well_number} date range: {well_min} to {well_max}")
                    
                    if min_date is None or well_min < min_date:
                        min_date = well_min
                    if max_date is None or well_max > max_date:
                        max_date = well_max
            
            if not data_found:
                QMessageBox.warning(self, "No Data", "No data found for the selected wells.")
                return
                
            print(f"Overall date range found: {min_date} to {max_date}")
            
            # Set date range with a small buffer (1 day on each side if possible)
            self.start_date_edit.setDate(QDate(min_date.year, min_date.month, min_date.day))
            self.end_date_edit.setDate(QDate(max_date.year, max_date.month, max_date.day))
            
            # Update the plot and provide feedback
            self.status_bar.showMessage(f"Date range set to {min_date} - {max_date} based on available data")
            QMessageBox.information(self, "Date Range Updated", 
                                   f"Date range set to {min_date} - {max_date} based on available data.")
            
        except Exception as e:
            logger.error(f"Error setting auto date range: {e}")
            print(f"Error setting auto date range: {e}")
            QMessageBox.critical(self, "Error", f"Failed to set auto date range: {str(e)}")