from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QGroupBox, QDoubleSpinBox, QComboBox, QColorDialog, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

class PlotStylePanel(QWidget):
    """Panel for plot styling controls."""
    
    # Signals
    show_manual_changed = pyqtSignal(bool)  # Emitted when show manual checkbox changes
    show_grid_changed = pyqtSignal(bool)  # Emitted when show grid checkbox changes
    theme_changed = pyqtSignal(bool)  # Emitted when theme checkbox changes
    line_width_changed = pyqtSignal(float)  # Emitted when line width changes
    well_style_changed = pyqtSignal(str, dict)  # Emitted when well style changes (well_number, style_dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.well_colors = {}  # Dictionary to store custom colors for wells
        self.well_line_widths = {}  # Dictionary to store custom line widths
        self.well_line_styles = {}  # Dictionary to store custom line styles for wells
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Checkboxes in a more compact layout
        checkbox_layout = QHBoxLayout()
        self.show_manual_cb = QCheckBox("Manual")
        self.show_manual_cb.setToolTip("Show Manual Readings")
        self.show_manual_cb.setChecked(True)
        self.show_manual_cb.stateChanged.connect(
            lambda state: self.show_manual_changed.emit(state == Qt.Checked)
        )
        checkbox_layout.addWidget(self.show_manual_cb)
        
        self.show_grid_cb = QCheckBox("Grid")
        self.show_grid_cb.setToolTip("Show Grid Lines")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.stateChanged.connect(
            lambda state: self.show_grid_changed.emit(state == Qt.Checked)
        )
        checkbox_layout.addWidget(self.show_grid_cb)
        
        # Add theme toggle
        self.theme_cb = QCheckBox("Dark Theme")
        self.theme_cb.setToolTip("Toggle Dark/Light Theme")
        self.theme_cb.stateChanged.connect(
            lambda state: self.theme_changed.emit(state == Qt.Checked)
        )
        checkbox_layout.addWidget(self.theme_cb)
        
        layout.addLayout(checkbox_layout)
        
        # Line width in a compact layout
        line_width_layout = QHBoxLayout()
        line_width_layout.addWidget(QLabel("Width:"))
        self.line_width_spinner = QDoubleSpinBox()
        self.line_width_spinner.setRange(0.5, 5.0)
        self.line_width_spinner.setSingleStep(0.5)
        self.line_width_spinner.setValue(1.5)
        self.line_width_spinner.valueChanged.connect(
            lambda value: self.line_width_changed.emit(value)
        )
        line_width_layout.addWidget(self.line_width_spinner)
        layout.addLayout(line_width_layout)
        
        # Well style customization
        well_style_group = QGroupBox("Well Styling")
        well_style_layout = QVBoxLayout(well_style_group)
        
        self.custom_well_combo = QComboBox()
        self.custom_well_combo.setEnabled(False)
        self.custom_well_combo.currentTextChanged.connect(self.on_custom_well_changed)
        well_style_layout.addWidget(self.custom_well_combo)
        
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
        
        well_style_layout.addLayout(style_controls_layout)
        
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
        well_style_layout.addLayout(width_layout)
        
        layout.addWidget(well_style_group)
        
        # Add stretch to push everything up
        layout.addStretch()
    
    def set_selected_wells(self, wells):
        """Update the custom well combo box with selected wells."""
        self.custom_well_combo.clear()
        if wells:
            self.custom_well_combo.addItems(wells)
            self.custom_well_combo.setEnabled(True)
            self.color_button.setEnabled(True)
            self.custom_width_spinner.setEnabled(True)
            self.line_style_combo.setEnabled(True)
        else:
            self.custom_well_combo.setEnabled(False)
            self.color_button.setEnabled(False)
            self.custom_width_spinner.setEnabled(False)
            self.line_style_combo.setEnabled(False)
    
    def on_custom_well_changed(self, well_name):
        """Update the style controls when a different well is selected."""
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
            
            # Emit signal with updated style
            self.update_well_style()
    
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
        
        # Emit signal with updated style
        style_dict = {
            'color': self.well_colors.get(well, QColor(31, 119, 180)).name(),
            'line_width': self.well_line_widths[well],
            'line_style': self.well_line_styles[well]
        }
        self.well_style_changed.emit(well, style_dict)
    
    def get_well_style(self, well_number):
        """Get the style dictionary for a specific well."""
        return {
            'color': self.well_colors.get(well_number, QColor(31, 119, 180)).name(),
            'line_width': self.well_line_widths.get(well_number, self.line_width_spinner.value()),
            'line_style': self.well_line_styles.get(well_number, '-')
        }
    
    def get_show_manual(self):
        """Get whether manual readings should be shown."""
        return self.show_manual_cb.isChecked()
    
    def get_show_grid(self):
        """Get whether grid should be shown."""
        return self.show_grid_cb.isChecked()
    
    def get_theme_dark(self):
        """Get whether dark theme is enabled."""
        return self.theme_cb.isChecked()
    
    def get_line_width(self):
        """Get the default line width."""
        return self.line_width_spinner.value() 