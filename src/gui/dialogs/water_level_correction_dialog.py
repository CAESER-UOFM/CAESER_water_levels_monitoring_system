from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                           QHeaderView, QMessageBox, QComboBox)
from PyQt5.QtCore import Qt
import csv
import io
import sqlite3
import logging

logger = logging.getLogger(__name__)

class WaterLevelCorrectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Water Level Meter Correction")
        self.setModal(True)
        self.resize(600, 800)
        
        # Get database path from parent (MainWindow)
        self.db_manager = parent.db_manager if parent else None
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add meter selection/creation section
        meter_layout = QHBoxLayout()
        self.meter_combo = QComboBox()
        self.meter_combo.currentIndexChanged.connect(self.load_meter_data)
        meter_layout.addWidget(QLabel("Select Meter:"))
        meter_layout.addWidget(self.meter_combo, 1)
        layout.addLayout(meter_layout)
        
        # Add name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Add serial number input
        serial_layout = QHBoxLayout()
        serial_label = QLabel("Serial Number:")
        self.serial_input = QLineEdit()
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.serial_input)
        layout.addLayout(serial_layout)
        
        # Add table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Range Start (ft)", "Range End (ft)", "Correction Factor"])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        # Initialize table with ranges
        self.initialize_table()
        layout.addWidget(self.table)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_button)
        
        paste_button = QPushButton("Paste from Clipboard")
        paste_button.clicked.connect(self.paste_from_clipboard)
        button_layout.addWidget(paste_button)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_data)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Load existing meters
        self.load_existing_meters()

    def load_existing_meters(self):
        """Load existing meters into combo box"""
        if not self.db_manager or not self.db_manager.current_db:
            return
            
        try:
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT name, serial_number 
                    FROM water_level_meter_corrections 
                    ORDER BY name
                """)
                meters = cursor.fetchall()
                
                self.meter_combo.clear()
                self.meter_combo.addItem("Create New Meter...", None)
                
                for name, serial in meters:
                    self.meter_combo.addItem(f"{name} ({serial})", (name, serial))
                    
        except Exception as e:
            logger.error(f"Error loading existing meters: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load existing meters: {str(e)}")

    def load_meter_data(self, index):
        """Load data for selected meter"""
        if index <= 0:  # Create New Meter
            self.name_input.clear()
            self.serial_input.clear()
            self.initialize_table()
            return
            
        meter_data = self.meter_combo.currentData()
        if not meter_data:
            return
            
        name, serial = meter_data
        self.name_input.setText(name)
        self.serial_input.setText(serial)
        
        try:
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT range_start, range_end, correction_factor 
                    FROM water_level_meter_corrections 
                    WHERE name = ? AND serial_number = ?
                    ORDER BY range_start
                """, (name, serial))
                data = cursor.fetchall()
                
                self.initialize_table()
                for i, (start, end, factor) in enumerate(data):
                    if i < self.table.rowCount():
                        self.table.setItem(i, 0, QTableWidgetItem(str(start)))
                        self.table.setItem(i, 1, QTableWidgetItem(str(end)))
                        self.table.setItem(i, 2, QTableWidgetItem(str(factor)))
                        
        except Exception as e:
            logger.error(f"Error loading meter data: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load meter data: {str(e)}")

    def save_data(self):
        """Save the correction factors to the database"""
        if not self.db_manager or not self.db_manager.current_db:
            QMessageBox.warning(self, "Error", "No database is currently open")
            return
            
        name = self.name_input.text().strip()
        serial = self.serial_input.text().strip()
        
        if not name or not serial:
            QMessageBox.warning(self, "Error", "Name and Serial Number are required")
            return
            
        try:
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                cursor = conn.cursor()
                
                # Delete existing entries for this meter
                cursor.execute("""
                    DELETE FROM water_level_meter_corrections 
                    WHERE name = ? AND serial_number = ?
                """, (name, serial))
                
                # Insert new data
                for row in range(self.table.rowCount()):
                    start = float(self.table.item(row, 0).text())
                    end = float(self.table.item(row, 1).text())
                    factor = float(self.table.item(row, 2).text())
                    
                    cursor.execute("""
                        INSERT INTO water_level_meter_corrections 
                        (name, serial_number, range_start, range_end, correction_factor)
                        VALUES (?, ?, ?, ?, ?)
                    """, (name, serial, start, end, factor))
                
                conn.commit()
                
            QMessageBox.information(self, "Success", "Water level meter corrections saved successfully")
            self.load_existing_meters()  # Refresh the combo box
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving meter data: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save meter data: {str(e)}")

    def initialize_table(self):
        """Initialize the table with ranges from 0 to 200 ft in 10 ft increments"""
        ranges = []
        for i in range(0, 200, 10):
            ranges.append((i, i + 10))
        
        self.table.setRowCount(len(ranges))
        
        for i, (start, end) in enumerate(ranges):
            self.table.setItem(i, 0, QTableWidgetItem(str(start)))
            self.table.setItem(i, 1, QTableWidgetItem(str(end)))
            self.table.setItem(i, 2, QTableWidgetItem("0.0"))

    def copy_to_clipboard(self):
        """Copy table data to clipboard in CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(["Range Start (ft)", "Range End (ft)", "Correction Factor"])
        
        # Write data
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            writer.writerow(row_data)
        
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(output.getvalue())
        QMessageBox.information(self, "Success", "Table data copied to clipboard")

    def paste_from_clipboard(self):
        """Paste CSV data from clipboard into table"""
        try:
            clipboard = QApplication.clipboard().text()
            f = io.StringIO(clipboard)
            reader = csv.reader(f)
            
            # Skip header row
            next(reader)
            
            # Read data
            data = list(reader)
            
            if len(data) != self.table.rowCount():
                raise ValueError("Pasted data must have the same number of rows as the table")
            
            # Update table
            for row, row_data in enumerate(data):
                if len(row_data) != 3:
                    raise ValueError(f"Row {row + 1} must have exactly 3 columns")
                
                for col, value in enumerate(row_data):
                    self.table.setItem(row, col, QTableWidgetItem(value.strip()))
            
            QMessageBox.information(self, "Success", "Data pasted successfully")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to paste data: {str(e)}")