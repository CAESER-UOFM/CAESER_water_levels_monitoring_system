# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 12:07:22 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                           QLineEdit, QDateEdit, QComboBox,
                           QPushButton, QDialogButtonBox, QMessageBox, QHBoxLayout, QFileDialog)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime
from pathlib import Path
from ..handlers.solinst_reader import SolinstReader
import logging 
logger = logging.getLogger(__name__)

class TransducerDialog(QDialog):
    def __init__(self, well_model, transducer_data=None, parent=None):
        super().__init__(parent)
        self.solinst_reader = SolinstReader()
        self.well_model = well_model
        self.transducer_data = transducer_data
        self.setup_ui()
        if transducer_data:
            self.load_transducer_data()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Transducer Details")
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Serial Number
        self.serial_number = QLineEdit()
        form.addRow("Serial Number:", self.serial_number)

        # After serial number field:
        serial_layout = QHBoxLayout()
        serial_layout.addWidget(self.serial_number)
        import_btn = QPushButton("Import from XLE...")
        import_btn.clicked.connect(self.import_from_xle)
        serial_layout.addWidget(import_btn)
        form.addRow("Serial Number:", serial_layout)

        # Well Selection
        self.well_combo = QComboBox()
        self.load_wells()
        form.addRow("Well:", self.well_combo)
        
        # Installation Date
        self.install_date = QDateEdit()
        self.install_date.setCalendarPopup(True)
        self.install_date.setDateTime(QDateTime.currentDateTime())
        form.addRow("Installation Date:", self.install_date)
        
        # Notes
        self.notes = QLineEdit()
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
        
        # Disable serial number if editing
        if self.transducer_data:
            self.serial_number.setEnabled(False)
    
    def load_wells(self):
        """Load available wells into combo box"""
        wells = self.well_model.get_all_wells()
        self.well_combo.addItem("", None)  # Empty option
        for well in wells:
            self.well_combo.addItem(
                f"{well['well_number']} - {well.get('description', '')}",
                well['well_number']
            )
    
    def load_transducer_data(self):
        """Load existing transducer data into form"""
        self.serial_number.setText(self.transducer_data['serial_number'])
        
        if self.transducer_data.get('well_number'):
            index = self.well_combo.findData(self.transducer_data['well_number'])
            if index >= 0:
                self.well_combo.setCurrentIndex(index)
        
        if self.transducer_data.get('installation_date'):
            install_date = QDateTime.fromString(
                self.transducer_data['installation_date'],
                "yyyy-MM-dd hh:mm:ss"
            )
            self.install_date.setDateTime(install_date)
        
        self.notes.setText(self.transducer_data.get('notes', ''))
    
    def get_data(self) -> dict:
        """Get form data as dictionary"""
        return {
            'serial_number': self.serial_number.text(),
            'well_number': self.well_combo.currentData(),
            'installation_date': self.install_date.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
            'notes': self.notes.text()
        }
    
    def validate(self) -> bool:
        """Validate form data"""
        if not self.serial_number.text():
            QMessageBox.warning(self, "Validation Error", "Serial number is required")
            return False
            
        if not self.well_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Well selection is required")
            return False
            
        return True
    
    def accept(self):
        if not self.validate():
            return
            
        data = self.get_data()
        
        try:
            # CHANGE THIS: Instead of using well_model.add_transducer, 
            # always use TransducerHandler.add_transducer
            from ..handlers.transducer_handler import TransducerHandler
            handler = TransducerHandler(self.well_model.db_path)
            
            # Process the registration with proper confirmation handling
            result = handler.add_transducer(data)
            
            # Handle both 2 and 3 return values
            if len(result) == 2:
                success, message = result
                additional_data = None
            else:
                success, message, additional_data = result
            
            if message == "needs_confirmation":
                # Show confirmation dialog
                from .transducer_location_dialog import TransducerLocationDialog
                
                # Add serial number to new_location for the dialog
                new_location = additional_data['new_location']
                new_location['serial_number'] = data['serial_number']
                
                dialog = TransducerLocationDialog(
                    additional_data['current_location'],
                    new_location,
                    parent=self
                )
                if dialog.exec_() == QDialog.Accepted:
                    # Update transducer location
                    result = handler.update_transducer(data)
                    
                    # Again, handle both 2 and 3 return values
                    if len(result) == 2:
                        success, message = result
                    else:
                        success, message, _ = result
                    
                    if success:
                        QMessageBox.information(self, "Success", message)
                        super().accept()
                    else:
                        QMessageBox.warning(self, "Warning", message)
            elif success:
                QMessageBox.information(self, "Success", message)
                super().accept()
            else:
                QMessageBox.warning(self, "Warning", message)
                
        except Exception as e:
            logger.error(f"Error in TransducerDialog.accept: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", str(e))
                
    def import_from_xle(self):
        """Import metadata from XLE file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select XLE File", "", "XLE files (*.xle)"
        )
        
        if file_path:
            try:
                df, metadata = self.solinst_reader.read_xle(Path(file_path))
                
                # Validate after reading
                if self.solinst_reader.is_barologger(metadata):
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Selected file is from a barologger"
                    )
                    return
                    
                self.serial_number.setText(metadata.serial_number)
                
                # Find well by CAE number
                wells = self.well_model.get_all_wells()
                matching_well = None
                for well in wells:
                    if well.get('cae_number') == metadata.location:
                        matching_well = well
                        break
                
                # Set well selection
                if matching_well:
                    index = self.well_combo.findData(matching_well['well_number'])
                    if index >= 0:
                        self.well_combo.setCurrentIndex(index)
                        self.notes.setText("")
                else:
                    no_match_text = "NO_MATCH - Location not found"
                    index = self.well_combo.findText(no_match_text)
                    if index < 0:
                        self.well_combo.insertItem(0, no_match_text, "NO_MATCH")
                    self.well_combo.setCurrentIndex(0)
                    self.notes.setText(f"Original location in file: {metadata.location}")
                
                start_date = QDateTime.fromString(
                    metadata.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "yyyy-MM-dd hh:mm:ss"
                )
                self.install_date.setDateTime(start_date)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read XLE file: {str(e)}")