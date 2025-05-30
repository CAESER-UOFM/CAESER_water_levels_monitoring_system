from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QGroupBox, QAbstractItemView, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal

class WellSelectionPanel(QWidget):
    """Panel for well selection and filtering."""
    
    # Signals
    selection_changed = pyqtSignal(list)  # Emitted when well selection changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_wells = []
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Well selection table
        well_group = QGroupBox("Available Wells")
        well_layout = QVBoxLayout(well_group)
        
        self.well_table = QTableWidget()
        self.well_table.setColumnCount(7)
        self.well_table.setHorizontalHeaderLabels([
            "Well Number", "CAE Number", "Top of Casing", 
            "Aquifer", "Well Field", "Cluster", "Data Source"
        ])
        self.well_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.well_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.well_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        well_layout.addWidget(self.well_table)
        
        # Add search/filter options
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_input = QComboBox()
        self.filter_input.setEditable(True)
        self.filter_input.editTextChanged.connect(self.filter_wells)
        filter_layout.addWidget(self.filter_input)
        well_layout.addLayout(filter_layout)
        
        layout.addWidget(well_group)
    
    def load_wells(self, wells_data, column_names):
        """Load wells data into the table."""
        self.well_table.setRowCount(0)  # Clear table
        self.well_table.setSortingEnabled(False)
        
        # Set up table with available columns
        self.well_table.setColumnCount(len(column_names))
        self.well_table.setHorizontalHeaderLabels(column_names)
        
        # Add wells to table
        for i, row_data in enumerate(wells_data):
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
        
        # Set up column resizing behavior
        header = self.well_table.horizontalHeader()
        for i in range(self.well_table.columnCount()):
            # Allow manual resizing
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            # Set minimum width to fit header text
            header.setMinimumSectionSize(header.sectionSize(i))
        
        # First resize to fit content
        self.well_table.resizeColumnsToContents()
        
        # Then set minimum widths to prevent columns from becoming too narrow
        for i in range(self.well_table.columnCount()):
            current_width = self.well_table.columnWidth(i)
            header.setMinimumSectionSize(current_width)
        
        self.well_table.setSortingEnabled(True)
    
    def filter_wells(self, filter_text):
        """Filter the wells table based on the search text."""
        filter_text = filter_text.lower()
        for row in range(self.well_table.rowCount()):
            item = self.well_table.item(row, 0)
            if item:
                well_number = item.text().lower()
                self.well_table.setRowHidden(row, filter_text not in well_number)
    
    def on_selection_changed(self):
        """Handle well selection changes in the table."""
        self.selected_wells = []
        for item in self.well_table.selectedItems():
            well_number = item.text()
            if well_number not in self.selected_wells:
                self.selected_wells.append(well_number)
        
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_wells)
    
    def get_selected_wells(self):
        """Get the list of currently selected wells."""
        return self.selected_wells
    
    def clear_selection(self):
        """Clear the current well selection."""
        self.well_table.clearSelection()
        self.selected_wells = []
        self.selection_changed.emit([]) 