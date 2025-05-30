import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, 
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTabWidget,
    QRadioButton, QButtonGroup, QColorDialog, QFrame, QSizePolicy, QWidget,
    QScrollArea
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)

class PlotControlsDialog(QDialog):
    """
    A dialog containing plot controls that was previously in the lower panel of the main window.
    This allows more space for the graph in the main window.
    """
    
    # Define signals
    plot_updated = pyqtSignal()
    export_triggered = pyqtSignal(str)  # 'plot' or 'data'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Controls")
        self.setWindowFlag(Qt.Tool, True)  # Make it a tool window
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)  # Stay on top
        
        # References to managers from parent
        self.parent = parent
        self.plot_handler = parent.plot_handler
        self.data_manager = parent.data_manager
        self.export_manager = parent.export_manager
        
        # Setup UI
        self.setup_ui()
        
        # Set initial size and adjust for content
        self.resize(800, 180)  # Reduced width from 1100 to 800
        self.setMinimumSize(600, 150)  # Set a reasonable minimum size
        
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins
        layout.setSpacing(5)  # Reduced spacing
        
        # Create a scrollable area for the controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for controls
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(5)
        
        # Main controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(5)
        
        # Add the panels (copied from the main window lower section)
        controls_layout.addWidget(self.create_data_controls_panel())
        controls_layout.addWidget(self.create_date_range_panel())
        controls_layout.addWidget(self.create_combined_style_panel())
        controls_layout.addWidget(self.create_labels_panel())
        controls_layout.addWidget(self.create_trend_panel())
        controls_layout.addWidget(self.create_export_panel())
        
        container_layout.addLayout(controls_layout)
        
        # Set the container as the scroll area widget
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        
        # Add button at the bottom to close the dialog
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_data_controls_panel(self):
        """Create the downsampling panel."""
        panel = QGroupBox("Downsampling") 
        panel.setMinimumWidth(120)  # Reduced from 200
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 10, 3, 3)  # Reduced margins
        layout.setSpacing(3)  # Reduced spacing
        
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
        panel.setMinimumWidth(120)  # Reduced from 200
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 10, 3, 3)  # Reduced margins
        layout.setSpacing(3)  # Reduced spacing
        
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
        
        # Full range button
        full_range_btn = QPushButton("Full Range")
        full_range_btn.clicked.connect(self.set_auto_date_range)
        layout.addWidget(full_range_btn)
        
        return panel
    
    def create_combined_style_panel(self):
        """Create the enhanced plot and well style panel with separate manual and transducer controls."""
        panel = QGroupBox("Plot & Well Styling")
        panel.setMinimumWidth(180)  # Reduced from 400
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 10, 3, 3)  # Reduced margins
        layout.setSpacing(3)  # Reduced spacing
        
        # Well selection at the top
        well_selection_layout = QHBoxLayout()
        well_selection_layout.addWidget(QLabel("Well:"))
        self.custom_well_combo = QComboBox()
        self.custom_well_combo.setEnabled(False)
        self.custom_well_combo.currentTextChanged.connect(self._internal_custom_well_changed)
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
        
        return panel
    
    def create_labels_panel(self):
        """Create the labels and legend panel."""
        panel = QGroupBox("Labels & Legend")
        panel.setMinimumWidth(150)  # Reduced from original
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 10, 3, 3)  # Reduced margins
        layout.setSpacing(3)  # Reduced spacing
        
        # Create a tab widget for different categories of controls
        labels_tabs = QTabWidget()
        labels_tabs.setTabPosition(QTabWidget.North)
        labels_tabs.setDocumentMode(True)
        
        # Titles tab
        titles_tab = QWidget()
        titles_layout = QVBoxLayout(titles_tab)
        
        # Plot title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_input = QComboBox()
        self.title_input.setEditable(True)
        self.title_input.addItems(["Water Level Data", "Well Water Levels", "Groundwater Levels"])
        self.title_input.currentTextChanged.connect(self.update_plot_title)
        title_layout.addWidget(self.title_input)
        titles_layout.addLayout(title_layout)
        
        # Axis labels
        x_axis_layout = QHBoxLayout()
        x_axis_layout.addWidget(QLabel("X-Axis:"))
        self.x_axis_input = QComboBox()
        self.x_axis_input.setEditable(True)
        self.x_axis_input.addItems(["Date", ""])
        self.x_axis_input.currentTextChanged.connect(self.update_axis_labels)
        x_axis_layout.addWidget(self.x_axis_input)
        titles_layout.addLayout(x_axis_layout)
        
        y_axis_layout = QHBoxLayout()
        y_axis_layout.addWidget(QLabel("Y-Axis:"))
        self.y_axis_input = QComboBox()
        self.y_axis_input.setEditable(True)
        self.y_axis_input.addItems(["Depth to Water (ft)", "Water Level (ft)", ""])
        self.y_axis_input.currentTextChanged.connect(self.update_axis_labels)
        y_axis_layout.addWidget(self.y_axis_input)
        titles_layout.addLayout(y_axis_layout)
        
        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_size_spinner = QSpinBox()
        self.font_size_spinner.setRange(8, 24)
        self.font_size_spinner.setValue(12)
        self.font_size_spinner.valueChanged.connect(self.update_axis_font)
        font_layout.addWidget(self.font_size_spinner)
        titles_layout.addLayout(font_layout)
        
        # Show grid
        self.show_grid_cb = QCheckBox("Show Grid")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.stateChanged.connect(self.toggle_grid)
        titles_layout.addWidget(self.show_grid_cb)
        
        labels_tabs.addTab(titles_tab, "Titles")
        
        # Legend tab
        legend_tab = QWidget()
        legend_layout = QVBoxLayout(legend_tab)
        
        # Legend position
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position:"))
        self.legend_position_combo = QComboBox()
        self.legend_position_combo.addItems(["Best", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Center Left", "Center Right", "Lower Center", "Upper Center", "Center"])
        self.legend_position_combo.currentIndexChanged.connect(self.update_legend_position)
        position_layout.addWidget(self.legend_position_combo)
        legend_layout.addLayout(position_layout)
        
        # Legend font size
        legend_font_layout = QHBoxLayout()
        legend_font_layout.addWidget(QLabel("Font Size:"))
        self.legend_font_spinner = QSpinBox()
        self.legend_font_spinner.setRange(6, 16)
        self.legend_font_spinner.setValue(10)
        self.legend_font_spinner.valueChanged.connect(self.update_legend_font)
        legend_font_layout.addWidget(self.legend_font_spinner)
        legend_layout.addLayout(legend_font_layout)
        
        # Legend draggable checkbox
        self.legend_draggable_cb = QCheckBox("Draggable Legend")
        self.legend_draggable_cb.setChecked(True)
        self.legend_draggable_cb.stateChanged.connect(self.update_legend_draggable)
        legend_layout.addWidget(self.legend_draggable_cb)
        
        # Highlight special features
        self.highlight_water_year_cb = QCheckBox("Highlight Water Year")
        self.highlight_water_year_cb.setChecked(False)
        self.highlight_water_year_cb.stateChanged.connect(self.toggle_water_year_highlight)
        legend_layout.addWidget(self.highlight_water_year_cb)
        
        # Add highlight gaps option
        self.highlight_gaps_cb = QCheckBox("Highlight Data Gaps")
        self.highlight_gaps_cb.setChecked(False) 
        self.highlight_gaps_cb.stateChanged.connect(self.toggle_gaps_highlight)
        legend_layout.addWidget(self.highlight_gaps_cb)
        
        labels_tabs.addTab(legend_tab, "Legend")
        
        # Add the tab widget to the main layout
        layout.addWidget(labels_tabs)
        
        return panel
    
    def create_trend_panel(self):
        """Create the trend analysis panel."""
        panel = QGroupBox("Analysis")
        panel.setMinimumWidth(120)  # Reduced from 200
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 10, 3, 3)  # Reduced margins
        layout.setSpacing(3)  # Reduced spacing
        
        # Show trend line
        self.show_trend_cb = QCheckBox("Show Trend Line")
        self.show_trend_cb.setChecked(False)
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
        panel.setMinimumWidth(120)  # Reduced from 180
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 10, 3, 3)  # Reduced margins
        layout.setSpacing(3)  # Reduced spacing
        
        # Export plot
        export_plot_btn = QPushButton("Export Plot (PNG)")
        export_plot_btn.clicked.connect(lambda: self.export_triggered.emit('plot'))
        layout.addWidget(export_plot_btn)
        
        # Export data
        export_data_btn = QPushButton("Export Data (CSV)")
        export_data_btn.clicked.connect(lambda: self.export_triggered.emit('data'))
        layout.addWidget(export_data_btn)
        
        # Add checkbox for applying downsampling to exports
        self.export_downsample_cb = QCheckBox("Apply Downsampling")
        self.export_downsample_cb.setChecked(False)
        self.export_downsample_cb.setToolTip("If checked, exported data will use the same downsampling settings as the plot")
        layout.addWidget(self.export_downsample_cb)
        
        return panel
    
    # Forward methods to parent window
    def update_plot(self):
        """Update the plot directly with values from this dialog's controls."""
        try:
            # Get data type
            data_type = self.data_type_combo.currentText()
            
            # Get downsampling settings
            downsample_text = self.downsample_combo.currentText()
            agg_method = self.aggregate_combo.currentText().lower()
            
            # Get date range from date widgets
            start_date = self.start_date_edit.date().toPyDate()
            end_date = self.end_date_edit.date().toPyDate()
            date_range = (start_date, end_date)
            
            # Update the plot handler with these settings
            if hasattr(self.parent, 'plot_handler') and self.parent.plot_handler:
                handler = self.parent.plot_handler
                
                # Set data type
                if data_type == "Water Level":
                    handler.set_data_type('water_level')
                elif data_type == "Temperature":
                    handler.set_data_type('temperature')
                
                # Set downsampling
                if downsample_text == "No Downsampling":
                    handler.set_downsample(None)
                else:
                    handler.set_downsample(downsample_text, agg_method)
                
                # Set date range
                handler.set_date_range(date_range)
                
                # Update the plot
                if hasattr(self.parent, 'selected_wells') and self.parent.selected_wells:
                    handler.update_plot(self.parent.selected_wells, 
                                         show_manual=hasattr(self.parent, 'show_manual_cb') and 
                                                  self.parent.show_manual_cb.isChecked())
                    
                    # Emit signal
                    self.plot_updated.emit()
                    
            # Update parent's status bar if available
            if hasattr(self.parent, 'status_bar'):
                if downsample_text == "No Downsampling":
                    self.parent.status_bar.showMessage("Plot updated (no downsampling)", 3000)
                else:
                    self.parent.status_bar.showMessage(f"Plot updated with {downsample_text} downsampling using {agg_method} method", 3000)
        
        except Exception as e:
            # Log the error
            import logging
            import traceback
            logging.getLogger(__name__).error(f"Error updating plot: {e}")
            logging.getLogger(__name__).error(traceback.format_exc())
            
            # Update status bar if available
            if hasattr(self.parent, 'status_bar'):
                self.parent.status_bar.showMessage(f"Error updating plot: {str(e)}", 5000)
    
    def update_date_range(self, which, qdate):
        """Forward date range update to parent."""
        self.parent.update_date_range(which, qdate)
    
    def set_auto_date_range(self):
        """Forward auto date range to parent."""
        self.parent.set_auto_date_range()
    
    def on_custom_well_changed(self, well_name):
        """Handle style control updates for the selected well directly in the dialog."""
        if not well_name:
            return
            
        # Enable style controls
        self.line_style_combo.setEnabled(True)
        self.custom_width_spinner.setEnabled(True)
        self.color_button.setEnabled(True)
        self.manual_marker_combo.setEnabled(True)
        self.manual_size_spinner.setEnabled(True)
        self.manual_color_button.setEnabled(True)
        
        # Access plot handler from parent
        plot_handler = self.parent.plot_handler
        
        # Get well properties from plot handler
        if hasattr(plot_handler, 'well_properties') and well_name in plot_handler.well_properties:
            well_props = plot_handler.well_properties[well_name]
            
            # Line style properties
            line_props = well_props['line']
            line_style = line_props.get('line_style', '-')
            line_style_map = {
                "-": "Solid",
                "--": "Dashed",
                ":": "Dotted",
                "-.": "Dash-Dot",
                "": "None"
            }
            self.line_style_combo.setCurrentText(line_style_map.get(line_style, "Solid"))
            
            # Line width
            self.custom_width_spinner.setValue(line_props.get('line_width', 1.5))
            
            # Line color
            line_color = line_props.get('color', "#1f77b4")
            self.color_button.setStyleSheet(f"background-color: {line_color};")
            
            # Manual marker properties
            manual_props = well_props['manual']
            marker = manual_props.get('marker', 'o')
            marker_map = {
                "o": "Circle",
                "s": "Square",
                "^": "Triangle",
                "d": "Diamond",
                "x": "X",
                "+": "Plus"
            }
            self.manual_marker_combo.setCurrentText(marker_map.get(marker, "Circle"))
            
            # Manual marker size
            try:
                size_val = manual_props.get('marker_size', 80)
                self.manual_size_spinner.setValue(size_val)
            except (TypeError, ValueError):
                self.manual_size_spinner.setValue(80)
            
            # Manual color
            manual_color = manual_props.get('color', line_color)
            self.manual_color_button.setStyleSheet(f"background-color: {manual_color};")
            
            # Store in parent's local variables for backward compatibility
            parent = self.parent
            parent.well_line_styles[well_name] = line_style
            parent.well_line_widths[well_name] = line_props.get('line_width', 1.5)
            parent.well_colors[well_name] = line_color
        else:
            # Properties don't exist yet for this well, create them with default values
            props = plot_handler.initialize_well_properties(well_name)
            
            # Update UI controls with default values
            line_props = props['line']
            manual_props = props['manual']
            
            # Line style
            self.line_style_combo.setCurrentText("Solid")
            
            # Line width
            self.custom_width_spinner.setValue(line_props.get('line_width', 1.5))
            
            # Line color
            line_color = line_props.get('color', "#1f77b4")
            self.color_button.setStyleSheet(f"background-color: {line_color};")
            
            # Manual marker
            self.manual_marker_combo.setCurrentText("Circle")
            
            # Manual size
            self.manual_size_spinner.setValue(manual_props.get('marker_size', 80))
            
            # Manual color
            manual_color = manual_props.get('color', line_color)
            self.manual_color_button.setStyleSheet(f"background-color: {manual_color};")
            
            # Store in parent's local variables for backward compatibility
            parent = self.parent
            parent.well_line_styles[well_name] = "-"
            parent.well_line_widths[well_name] = 1.5
            parent.well_colors[well_name] = line_color
    
    def update_well_style(self):
        """Update the style for the selected well."""
        well_name = self.custom_well_combo.currentText()
        if not well_name:
            return
            
        try:
            # Get line style from combo box
            style_name = self.line_style_combo.currentText()
            style_map = {
                "Solid": "-",
                "Dashed": "--",
                "Dotted": ":",
                "Dash-Dot": "-.",
                "None": ""
            }
            line_style = style_map.get(style_name, "-")
            
            # Get line width from spinner
            line_width = self.custom_width_spinner.value()
            
            # Get color from button
            color = self.color_button.styleSheet().split(":")[-1].strip("; ")
            
            # Store values in parent's local dictionaries for backward compatibility
            self.parent.well_line_styles[well_name] = line_style
            self.parent.well_line_widths[well_name] = line_width
            self.parent.well_colors[well_name] = color
            
            # Create style dictionary for plot handler
            style_dict = {
                'line_style': line_style,
                'line_width': line_width,
                'color': color
            }
            
            # Update the plot handler
            self.parent.plot_handler.db_path = self.parent.db_path
            self.parent.plot_handler.set_well_style(well_name, style_dict)
            
            # Update status message
            self.parent.status_bar.showMessage(f"Updated style for {well_name}", 3000)
            
            # Update plot
            self.parent.update_plot()
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error updating well style: {e}")
            import traceback
            logging.getLogger(__name__).error(traceback.format_exc())
            self.parent.status_bar.showMessage(f"Error updating style: {str(e)}", 5000)
    
    def update_manual_style(self):
        """Update the manual reading style for the selected well."""
        well_name = self.custom_well_combo.currentText()
        if not well_name:
            return
            
        try:
            # Get marker style from combo box
            marker_name = self.manual_marker_combo.currentText()
            marker_map = {
                "Circle": "o",
                "Square": "s",
                "Triangle": "^",
                "Diamond": "d",
                "X": "x",
                "Plus": "+"
            }
            marker_style = marker_map.get(marker_name, "o")
            
            # Get marker size from spinner
            marker_size = self.manual_size_spinner.value()
            
            # Get color from button
            color = self.manual_color_button.styleSheet().split(":")[-1].strip("; ")
            
            # Create style dictionary for plot handler
            style_dict = {
                'marker': marker_style,
                'marker_size': marker_size,
                'color': color
            }
            
            # Update the plot handler with manual style
            manual_well_name = f"{well_name}_manual"
            self.parent.plot_handler.db_path = self.parent.db_path
            self.parent.plot_handler.set_well_style(manual_well_name, style_dict)
            
            # Update status bar
            self.parent.status_bar.showMessage(f"Updated manual reading style for {well_name}", 3000)
            
            # Update plot
            self.parent.update_plot()
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error updating manual style: {e}")
            import traceback
            logging.getLogger(__name__).error(traceback.format_exc())
            self.parent.status_bar.showMessage(f"Error updating style: {str(e)}", 5000)
    
    def select_well_color(self):
        """Open color picker and set the selected color for the well."""
        from PyQt5.QtWidgets import QColorDialog
        
        well_name = self.custom_well_combo.currentText()
        if not well_name:
            return
            
        # Get current color
        current_style = self.color_button.styleSheet()
        if "background-color:" in current_style:
            current_color = current_style.split("background-color:")[-1].strip("; ")
            try:
                from PyQt5.QtGui import QColor
                current_color = QColor(current_color)
            except:
                from PyQt5.QtGui import QColor
                current_color = QColor("#1f77b4")  # Default blue
        else:
            from PyQt5.QtGui import QColor
            current_color = QColor("#1f77b4")  # Default blue
            
        # Open color dialog
        color = QColorDialog.getColor(current_color, self, "Select Color for Well Line")
        
        if color.isValid():
            # Update the color button
            self.color_button.setStyleSheet(f"background-color: {color.name()};")
            
            # Update the well style
            self.update_well_style()
    
    def select_manual_color(self):
        """Open color picker and set the selected color for manual readings."""
        from PyQt5.QtWidgets import QColorDialog
        
        well_name = self.custom_well_combo.currentText()
        if not well_name:
            return
            
        # Get current color
        current_style = self.manual_color_button.styleSheet()
        if "background-color:" in current_style:
            current_color = current_style.split("background-color:")[-1].strip("; ")
            try:
                from PyQt5.QtGui import QColor
                current_color = QColor(current_color)
            except:
                from PyQt5.QtGui import QColor
                current_color = QColor("#1f77b4")  # Default blue
        else:
            from PyQt5.QtGui import QColor
            current_color = QColor("#1f77b4")  # Default blue
            
        # Open color dialog
        color = QColorDialog.getColor(current_color, self, "Select Color for Manual Readings")
        
        if color.isValid():
            # Update the color button
            self.manual_color_button.setStyleSheet(f"background-color: {color.name()};")
            
            # Update the manual style
            self.update_manual_style()
    
    def update_plot_title(self):
        """Forward plot title update to parent."""
        self.parent.update_plot_title()
    
    def update_axis_font(self):
        """Forward axis font update to parent."""
        self.parent.update_axis_font()
    
    def update_axis_labels(self):
        """Forward axis labels update to parent."""
        self.parent.update_axis_labels()
    
    def update_legend_position(self):
        """Forward legend position update to parent."""
        self.parent.update_legend_position()
    
    def update_legend_draggable(self):
        """Forward legend draggable update to parent."""
        self.parent.update_legend_draggable()
    
    def update_legend_font(self):
        """Forward legend font update to parent."""
        self.parent.update_legend_font()
    
    def toggle_grid(self, state):
        """Forward grid toggle to parent."""
        self.parent.toggle_grid(state)
    
    def toggle_water_year_highlight(self, state):
        """Forward water year highlight toggle to parent."""
        self.parent.toggle_water_year_highlight(state)
    
    def toggle_gaps_highlight(self, state):
        """Forward gaps highlight toggle to parent."""
        self.parent.toggle_gaps_highlight(state)
    
    def on_trend_checkbox_changed(self, state):
        """Forward trend checkbox change to parent."""
        self.parent.on_trend_checkbox_changed(state)
    
    def toggle_trend_controls(self, state):
        """Forward trend controls toggle to parent."""
        self.parent.toggle_trend_controls(state)
    
    def on_trend_setting_changed(self, *args):
        """Forward trend setting change to parent."""
        self.parent.on_trend_setting_changed(*args)
    
    def select_trend_color(self):
        """Forward trend color selection to parent."""
        self.parent.select_trend_color()
    
    def sync_from_parent(self):
        """Synchronize control values from parent to ensure consistency."""
        try:
            # Data controls
            if hasattr(self.parent, 'data_type_combo'):
                self.data_type_combo.setCurrentText(self.parent.data_type_combo.currentText())
            
            if hasattr(self.parent, 'downsample_combo'):
                self.downsample_combo.setCurrentText(self.parent.downsample_combo.currentText())
            
            if hasattr(self.parent, 'aggregate_combo'):
                self.aggregate_combo.setCurrentText(self.parent.aggregate_combo.currentText())
            
            # Date range
            if hasattr(self.parent, 'start_date_edit'):
                self.start_date_edit.setDate(self.parent.start_date_edit.date())
            
            if hasattr(self.parent, 'end_date_edit'):
                self.end_date_edit.setDate(self.parent.end_date_edit.date())
            
            # Style controls
            if hasattr(self.parent, 'custom_well_combo'):
                self.custom_well_combo.clear()
                self.custom_well_combo.addItems([self.parent.custom_well_combo.itemText(i) for i in range(self.parent.custom_well_combo.count())])
                self.custom_well_combo.setCurrentText(self.parent.custom_well_combo.currentText())
                self.custom_well_combo.setEnabled(self.parent.custom_well_combo.isEnabled())
            
            if hasattr(self.parent, 'line_style_combo'):
                self.line_style_combo.setCurrentText(self.parent.line_style_combo.currentText())
                self.line_style_combo.setEnabled(self.parent.line_style_combo.isEnabled())
            
            if hasattr(self.parent, 'custom_width_spinner'):
                self.custom_width_spinner.setValue(self.parent.custom_width_spinner.value())
                self.custom_width_spinner.setEnabled(self.parent.custom_width_spinner.isEnabled())
            
            if hasattr(self.parent, 'color_button'):
                self.color_button.setStyleSheet(self.parent.color_button.styleSheet())
                self.color_button.setEnabled(self.parent.color_button.isEnabled())
            
            if hasattr(self.parent, 'manual_marker_combo'):
                self.manual_marker_combo.setCurrentText(self.parent.manual_marker_combo.currentText())
                self.manual_marker_combo.setEnabled(self.parent.manual_marker_combo.isEnabled())
            
            if hasattr(self.parent, 'manual_size_spinner'):
                self.manual_size_spinner.setValue(self.parent.manual_size_spinner.value())
                self.manual_size_spinner.setEnabled(self.parent.manual_size_spinner.isEnabled())
            
            if hasattr(self.parent, 'manual_color_button'):
                self.manual_color_button.setStyleSheet(self.parent.manual_color_button.styleSheet())
                self.manual_color_button.setEnabled(self.parent.manual_color_button.isEnabled())
            
            # Labels
            if hasattr(self.parent, 'title_input'):
                if hasattr(self.parent.title_input, 'currentText'):
                    self.title_input.setCurrentText(self.parent.title_input.currentText())
                elif hasattr(self.parent.title_input, 'text'):
                    # Handle QLineEdit vs QComboBox
                    self.title_input.setCurrentText(self.parent.title_input.text())
            
            if hasattr(self.parent, 'x_axis_input'):
                if hasattr(self.parent.x_axis_input, 'currentText'):
                    self.x_axis_input.setCurrentText(self.parent.x_axis_input.currentText())
                elif hasattr(self.parent.x_axis_input, 'text'):
                    self.x_axis_input.setCurrentText(self.parent.x_axis_input.text())
            
            if hasattr(self.parent, 'y_axis_input'):
                if hasattr(self.parent.y_axis_input, 'currentText'):
                    self.y_axis_input.setCurrentText(self.parent.y_axis_input.currentText())
                elif hasattr(self.parent.y_axis_input, 'text'):
                    self.y_axis_input.setCurrentText(self.parent.y_axis_input.text())
            
            if hasattr(self.parent, 'font_size_spinner'):
                self.font_size_spinner.setValue(self.parent.font_size_spinner.value())
            
            if hasattr(self.parent, 'show_grid_cb'):
                self.show_grid_cb.setChecked(self.parent.show_grid_cb.isChecked())
            
            # Legend
            if hasattr(self.parent, 'legend_position_combo'):
                self.legend_position_combo.setCurrentText(self.parent.legend_position_combo.currentText())
            
            if hasattr(self.parent, 'legend_font_spinner'):
                self.legend_font_spinner.setValue(self.parent.legend_font_spinner.value())
            
            if hasattr(self.parent, 'legend_draggable_cb'):
                self.legend_draggable_cb.setChecked(self.parent.legend_draggable_cb.isChecked())
            
            if hasattr(self.parent, 'highlight_water_year_cb'):
                self.highlight_water_year_cb.setChecked(self.parent.highlight_water_year_cb.isChecked())
            
            if hasattr(self.parent, 'highlight_gaps_cb'):
                self.highlight_gaps_cb.setChecked(self.parent.highlight_gaps_cb.isChecked())
            
            # Trend
            if hasattr(self.parent, 'show_trend_cb'):
                self.show_trend_cb.setChecked(self.parent.show_trend_cb.isChecked())
            
            if hasattr(self.parent, 'trend_type_combo'):
                self.trend_type_combo.setCurrentText(self.parent.trend_type_combo.currentText())
                self.trend_type_combo.setEnabled(self.parent.trend_type_combo.isEnabled())
            
            if hasattr(self.parent, 'trend_degree_spinner'):
                self.trend_degree_spinner.setValue(self.parent.trend_degree_spinner.value())
                self.trend_degree_spinner.setEnabled(self.parent.trend_degree_spinner.isEnabled())
            
            if hasattr(self.parent, 'trend_style_combo'):
                self.trend_style_combo.setCurrentText(self.parent.trend_style_combo.currentText())
                self.trend_style_combo.setEnabled(self.parent.trend_style_combo.isEnabled())
            
            if hasattr(self.parent, 'trend_width_spinner'):
                self.trend_width_spinner.setValue(self.parent.trend_width_spinner.value())
                self.trend_width_spinner.setEnabled(self.parent.trend_width_spinner.isEnabled())
            
            if hasattr(self.parent, 'trend_color_button'):
                self.trend_color_button.setStyleSheet(self.parent.trend_color_button.styleSheet())
                self.trend_color_button.setEnabled(self.parent.trend_color_button.isEnabled())
            
            # Export
            if hasattr(self.parent, 'export_downsample_cb'):
                self.export_downsample_cb.setChecked(self.parent.export_downsample_cb.isChecked())
        
        except Exception as e:
            logger.error(f"Error syncing controls from parent: {e}")
            # Continue without crashing 
    
    # Add a new method to handle custom well change internally without recursion
    def _internal_custom_well_changed(self, well_name):
        """Handle well selection changes internally without calling back to parent."""
        if not well_name:
            return
            
        logger.debug(f"Plot controls dialog: internal custom well changed to {well_name}")
        
        # Call our own implementation directly
        self.on_custom_well_changed(well_name)
        
        # Update parent's UI to stay in sync, but without triggering callbacks
        if self.parent and hasattr(self.parent, 'custom_well_combo'):
            # Block signals to prevent infinite recursion
            self.parent.custom_well_combo.blockSignals(True)
            index = self.parent.custom_well_combo.findText(well_name)
            if index >= 0:
                self.parent.custom_well_combo.setCurrentIndex(index)
            self.parent.custom_well_combo.blockSignals(False) 