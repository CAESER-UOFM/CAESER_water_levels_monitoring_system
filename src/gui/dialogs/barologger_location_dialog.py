# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 14:27:01 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                           QLineEdit, QDateTimeEdit, QPushButton,
                           QDialogButtonBox, QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt, QDateTime

class BarologgerLocationDialog(QDialog):
    def __init__(self, baro_model, serial_number, current_location, parent=None):
        super().__init__(parent)
        self.baro_model = baro_model
        self.serial_number = serial_number
        self.current_location = current_location
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Update Barologger Location")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Current location (read-only)
        current_loc = QLineEdit(self.current_location)
        current_loc.setReadOnly(True)
        form.addRow("Current Location:", current_loc)
        
        # New location
        self.new_location = QLineEdit()
        form.addRow("New Location:", self.new_location)
        
        # Change date
        self.change_date = QDateTimeEdit()
        self.change_date.setDateTime(QDateTime.currentDateTime())
        self.change_date.setCalendarPopup(True)
        form.addRow("Change Date:", self.change_date)
        
        # Reason/Notes
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Enter reason for location change...")
        form.addRow("Notes:", self.notes)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_data(self) -> dict:
        """Get form data as dictionary"""
        return {
            'serial_number': self.serial_number,
            'new_location': self.new_location.text(),
            'change_date': self.change_date.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
            'notes': self.notes.toPlainText()
        }
    
    def validate(self) -> bool:
        """Validate form data"""
        if not self.new_location.text():
            QMessageBox.warning(self, "Validation Error", "New location is required")
            return False
            
        if self.new_location.text() == self.current_location:
            QMessageBox.warning(self, "Validation Error", "New location must be different")
            return False
            
        if not self.notes.toPlainText():
            QMessageBox.warning(self, "Validation Error", "Please provide a reason for the change")
            return False
            
        return True
    
    def accept(self):
        """Handle dialog acceptance"""
        if not self.validate():
            return
            
        try:
            success, message = self.baro_model.update_location(
                self.serial_number,
                self.new_location.text(),
                self.change_date.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
                self.notes.toPlainText()
            )
            
            if success:
                super().accept()
            else:
                QMessageBox.critical(self, "Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))