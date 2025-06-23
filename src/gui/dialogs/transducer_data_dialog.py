# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 12:08:01 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                           QComboBox, QCheckBox, QPushButton, QLabel,
                           QDialogButtonBox, QTableWidget, QTableWidgetItem,
                           QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
from ...handlers.transducer_file_handler import TransducerFileHandler

class TransducerDataDialog(QDialog):
    def __init__(self, transducer_model, file_path=None, parent=None):
        super().__init__(parent)
        self.transducer_model = transducer_model
        self.file_path = file_path
        self.file_handler = TransducerFileHandler()
        self.data_preview = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Import Transducer Data")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel(self.file_path or "No file selected")
        file_layout.addWidget(self.file_label)
        if not self.file_path:
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(self.browse_file)
            file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # Import options
        options_layout = QFormLayout()
        
        # Transducer selection
        self.transducer_combo = QComboBox()
        self.load_transducers()
        options_layout.addRow("Transducer:", self.transducer_combo)
        
        # Import options
        self.overwrite_cb = QCheckBox("Overwrite existing readings")
        self.compensate_cb = QCheckBox("Apply barometric compensation")
        options_layout.addRow("", self.overwrite_cb)
        options_layout.addRow("", self.compensate_cb)
        
        layout.addLayout(options_layout)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.setup_preview_table()
        layout.addWidget(self.preview_table)
        
        # Statistics
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        if self.file_path:
            self.load_file_preview()
    
    def load_transducers(self):
        """Load available transducers into combo box"""
        transducers = self.transducer_model.get_active_transducers()
        for transducer in transducers:
            self.transducer_combo.addItem(
                f"{transducer['serial_number']} - {transducer['description']}", 
                transducer['serial_number']
            )
    
    def setup_preview_table(self):
        """Setup the data preview table"""
        headers = ["Timestamp", "Level", "Temperature", "Status"]
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
    
    def browse_file(self):
        """Open file browser"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "All Files (*.*);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if file_path:
            self.file_path = file_path
            self.file_label.setText(file_path)
            self.load_file_preview()
    
    def load_file_preview(self):
        """Load and display file preview"""
        try:
            self.data_preview = self.file_handler.parse_file(self.file_path)
            
            # Show first 100 rows in preview
            preview_data = self.data_preview[:100]
            self.preview_table.setRowCount(len(preview_data))
            
            for row, reading in enumerate(preview_data):
                self.preview_table.setItem(row, 0, QTableWidgetItem(str(reading['timestamp'])))
                self.preview_table.setItem(row, 1, QTableWidgetItem(str(reading['level'])))
                self.preview_table.setItem(row, 2, QTableWidgetItem(str(reading.get('temperature', ''))))
                self.preview_table.setItem(row, 3, QTableWidgetItem(reading.get('status', '')))
            
            # Update statistics
            self.update_statistics()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse file: {str(e)}")
    
    def update_statistics(self):
        """Update statistics label"""
        if not self.data_preview:
            return
            
        stats = self.file_handler.get_statistics(self.data_preview)
        stats_text = (
            f"Total Records: {stats['total_records']}\n"
            f"Date Range: {stats['start_date']} to {stats['end_date']}\n"
            f"Level Range: {stats['min_level']} to {stats['max_level']}"
        )
        
        self.stats_label.setText(stats_text)
    
    def accept(self):
        """Handle dialog acceptance"""
        if not self.file_path:
            QMessageBox.warning(self, "Warning", "Please select a file to import")
            return
            
        if self.transducer_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Warning", "Please select a transducer")
            return
            
        try:
            serial_number = self.transducer_combo.currentData()
            
            success, message = self.transducer_model.import_readings(
                serial_number=serial_number,
                readings=self.data_preview,
                filename=self.file_path,
                overwrite=self.overwrite_cb.isChecked(),
                apply_compensation=self.compensate_cb.isChecked()
            )
            
            if success:
                QMessageBox.information(self, "Success", message)
                super().accept()
            else:
                QMessageBox.critical(self, "Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))