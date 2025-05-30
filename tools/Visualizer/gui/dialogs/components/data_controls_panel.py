from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal

class DataControlsPanel(QWidget):
    """Panel for data type and downsampling controls."""
    
    # Signals
    data_type_changed = pyqtSignal(str)  # Emitted when data type changes
    downsample_changed = pyqtSignal(str)  # Emitted when downsampling changes
    aggregate_changed = pyqtSignal(str)  # Emitted when aggregation method changes
    show_map_clicked = pyqtSignal()  # Emitted when show map button is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Data type selection
        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(QLabel("Data:"))
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["Water Level", "Temperature"])
        self.data_type_combo.currentIndexChanged.connect(
            lambda index: self.data_type_changed.emit(self.data_type_combo.currentText())
        )
        data_type_layout.addWidget(self.data_type_combo)
        layout.addLayout(data_type_layout)
        
        # Add downsampling
        downsample_layout = QHBoxLayout()
        downsample_layout.addWidget(QLabel("Sample:"))
        self.downsample_combo = QComboBox()
        self.downsample_combo.addItems([
            "No Downsampling", "30 Minutes", "1 Hour", "2 Hours", 
            "6 Hours", "12 Hours", "1 Day", "1 Week", "1 Month"
        ])
        self.downsample_combo.currentIndexChanged.connect(
            lambda index: self.downsample_changed.emit(self.downsample_combo.currentText())
        )
        downsample_layout.addWidget(self.downsample_combo)
        layout.addLayout(downsample_layout)
        
        # Add aggregation method option
        agg_layout = QHBoxLayout()
        agg_layout.addWidget(QLabel("Method:"))
        self.aggregate_combo = QComboBox()
        self.aggregate_combo.addItems(["Mean", "Median", "Min", "Max"])
        self.aggregate_combo.currentIndexChanged.connect(
            lambda index: self.aggregate_changed.emit(self.aggregate_combo.currentText())
        )
        agg_layout.addWidget(self.aggregate_combo)
        layout.addLayout(agg_layout)
        
        # Add map button
        map_button_layout = QHBoxLayout()
        self.show_map_button = QPushButton("Show Well Map")
        self.show_map_button.clicked.connect(self.show_map_clicked.emit)
        map_button_layout.addWidget(self.show_map_button)
        layout.addLayout(map_button_layout)
        
        # Add stretch to push everything up
        layout.addStretch()
    
    def get_data_type(self):
        """Get the currently selected data type."""
        return self.data_type_combo.currentText()
    
    def get_downsample_interval(self):
        """Get the currently selected downsampling interval."""
        return self.downsample_combo.currentText()
    
    def get_aggregate_method(self):
        """Get the currently selected aggregation method."""
        return self.aggregate_combo.currentText()
    
    def set_data_type(self, data_type):
        """Set the data type selection."""
        index = self.data_type_combo.findText(data_type)
        if index >= 0:
            self.data_type_combo.setCurrentIndex(index)
    
    def set_downsample_interval(self, interval):
        """Set the downsampling interval selection."""
        index = self.downsample_combo.findText(interval)
        if index >= 0:
            self.downsample_combo.setCurrentIndex(index)
    
    def set_aggregate_method(self, method):
        """Set the aggregation method selection."""
        index = self.aggregate_combo.findText(method)
        if index >= 0:
            self.aggregate_combo.setCurrentIndex(index) 