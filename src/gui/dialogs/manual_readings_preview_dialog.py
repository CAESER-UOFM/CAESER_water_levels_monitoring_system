"""
Dialog for previewing manual readings before import.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QCheckBox,
                           QDialogButtonBox, QWidget, QHBoxLayout)
from PyQt5.QtCore import Qt

class ManualReadingsPreviewDialog(QDialog):
    def __init__(self, df, wells_dict, parent=None):
        super().__init__(parent)
        self.df = df
        self.wells_dict = wells_dict
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Manual Readings Preview")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        
        # Add Select All checkbox
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.setChecked(True)  # Checked by default
        self.select_all_cb.stateChanged.connect(self.toggle_all_wells)
        layout.addWidget(self.select_all_cb)
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Include", "Overwrite", "Well Number", 
            "Measurements", "Avg DTW", "Max", "Min"
        ])
        layout.addWidget(self.table)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.calculate_statistics()

    def toggle_all_wells(self, state):
        """Toggle all well checkboxes"""
        for row in range(self.table.rowCount()):
            include_widget = self.table.cellWidget(row, 0)
            if include_widget is None or include_widget.layout() is None or include_widget.layout().count() == 0:
                continue
            include_cb = include_widget.layout().itemAt(0).widget()
            if include_cb:
                include_cb.setChecked(state == Qt.Checked)

    def calculate_statistics(self):
        """Calculate and display statistics for each well"""
        # Group by well and calculate statistics
        stats = self.df.groupby('well_number').agg({
            'dtw_1': ['count', 'mean', 'max', 'min']
        }).reset_index()
        
        # Populate table
        self.table.setRowCount(len(stats))
    
        for row, (_, data) in enumerate(stats.iterrows()):
            # Create include checkbox widget for the current row
            include_cb = QCheckBox()
            include_cb.setChecked(True)  # Pre-check the checkbox by default
            include_widget = QWidget()
            include_layout = QHBoxLayout(include_widget)
            include_layout.setContentsMargins(0, 0, 0, 0)
            include_layout.setSpacing(0)
            include_layout.addWidget(include_cb)
            include_layout.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 0, include_widget)
            
            # Overwrite checkbox
            overwrite_cb = QCheckBox()
            overwrite_cell = QWidget()
            overwrite_layout = QHBoxLayout(overwrite_cell)
            overwrite_layout.setContentsMargins(0, 0, 0, 0)
            overwrite_layout.setSpacing(0)
            overwrite_layout.addWidget(overwrite_cb)
            overwrite_layout.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 1, overwrite_cell)
            
            # Well number: force extraction as scalar string
            well_val = data['well_number']
            if not isinstance(well_val, str):
                try:
                    well_val = well_val.values[0]
                except Exception:
                    well_val = str(well_val)
            well_val = str(well_val).strip()
            
            # Set table items
            from PyQt5.QtWidgets import QTableWidgetItem
            self.table.setItem(row, 2, QTableWidgetItem(well_val))
            self.table.setItem(row, 3, QTableWidgetItem(str(int(data[('dtw_1', 'count')]))))
            self.table.setItem(row, 4, QTableWidgetItem(f"{data[('dtw_1', 'mean')]:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{data[('dtw_1', 'max')]:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{data[('dtw_1', 'min')]:.2f}"))
            
            # Set alignment for numeric columns
            for col in range(3, 7):
                item = self.table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def get_selected_wells(self):
        """Retrieve selected wells along with their overwrite preferences"""
        selected = {}
        for row in range(self.table.rowCount()):
            include_widget = self.table.cellWidget(row, 0)
            if include_widget is None or include_widget.layout() is None or include_widget.layout().count() == 0:
                continue
            include_cb = include_widget.layout().itemAt(0).widget()
            if include_cb and include_cb.isChecked():
                well_item = self.table.item(row, 2)  # Well Number is in column 2
                if well_item:
                    well = well_item.text()
                    overwrite = False
                    overwrite_widget = self.table.cellWidget(row, 1)
                    if overwrite_widget is not None and overwrite_widget.layout() is not None and overwrite_widget.layout().count() > 0:
                        overwrite_cb = overwrite_widget.layout().itemAt(0).widget()
                        if overwrite_cb:
                            overwrite = overwrite_cb.isChecked()
                    selected[well] = {'overwrite': overwrite}
        return selected 