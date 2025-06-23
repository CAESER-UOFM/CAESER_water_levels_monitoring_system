from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
                           QLineEdit, QDateEdit, QPushButton, QLabel,
                           QDialogButtonBox, QMessageBox, QWidget, QFileDialog, QComboBox, QDateTimeEdit, QTextEdit)
from PyQt5.QtCore import Qt, QDateTime
from pathlib import Path
from ..handlers.solinst_reader import SolinstReader
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class BarologgerDialog(QDialog):
    def __init__(self, baro_model, parent=None, barologger_data: Optional[Dict] = None):
        super().__init__(parent)
        self.baro_model = baro_model
        self.barologger_data = barologger_data
        self.solinst_reader = SolinstReader()
        self.setWindowTitle("Barologger Details")
        self.setup_ui()
        
        # If editing existing barologger, fill in the data
        if self.barologger_data:
            self.fill_existing_data()

    def setup_ui(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Serial Number with XLE import option
        serial_layout = QHBoxLayout()
        self.serial_number = QLineEdit()
        import_btn = QPushButton("Import from XLE...")
        import_btn.clicked.connect(self.import_from_xle)
        serial_layout.addWidget(self.serial_number)
        serial_layout.addWidget(import_btn)
        form_layout.addRow("Serial Number:", serial_layout)

        # Location
        self.location = QLineEdit()
        form_layout.addRow("Location:", self.location)

        # Installation Date
        self.installation_date = QDateTimeEdit()
        self.installation_date.setCalendarPopup(True)
        self.installation_date.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("Installation Date:", self.installation_date)

        # Status
        self.status = QComboBox()
        self.status.addItems(['active', 'inactive', 'maintenance'])
        form_layout.addRow("Status:", self.status)

        # Notes
        self.notes = QTextEdit()
        form_layout.addRow("Notes:", self.notes)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def import_from_xle(self):
        """Import metadata from XLE file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select XLE File",
            "",
            "XLE files (*.xle)"
        )
        
        if file_path:
            try:
                df, metadata = self.solinst_reader.read_xle(Path(file_path))
                
                # Move validation after reading
                if not self.solinst_reader.is_barologger(metadata):
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Selected file is not from a Barologger"
                    )
                    return
                    
                # Populate fields with metadata
                self.serial_number.setText(metadata.serial_number)
                self.location.setText(metadata.location)
                start_date = QDateTime.fromString(
                    metadata.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "yyyy-MM-dd hh:mm:ss"
                )
                self.installation_date.setDateTime(start_date)
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to read XLE file: {str(e)}"
                )
    
    def fill_existing_data(self):
        """Fill form with existing barologger data"""
        try:
            self.serial_number.setText(self.barologger_data['serial_number'])
            self.serial_number.setReadOnly(True)  # Can't change serial number when editing
            
            self.location.setText(self.barologger_data['location_description'])
            
            if self.barologger_data['installation_date']:
                date = QDateTime.fromString(self.barologger_data['installation_date'], 
                                          Qt.ISODate)
                self.installation_date.setDateTime(date)
            
            status_index = self.status.findText(self.barologger_data['status'])
            if status_index >= 0:
                self.status.setCurrentIndex(status_index)
            
            self.notes.setText(self.barologger_data.get('notes', ''))
            
        except Exception as e:
            logger.error(f"Error filling barologger data: {e}")

    def get_data(self) -> Dict:
        """Get the form data as a dictionary"""
        return {
            'serial_number': self.serial_number.text(),
            'location_description': self.location.text(),
            'installation_date': self.installation_date.dateTime().toString(Qt.ISODate),
            'status': self.status.currentText(),
            'notes': self.notes.toPlainText()
        }
    
    def validate(self) -> bool:
        """Validate form data"""
        if not self.serial_number.text():
            QMessageBox.warning(self, "Validation Error", "Serial number is required")
            return False
            
        if not self.location.text():
            QMessageBox.warning(self, "Validation Error", "Location is required")
            return False
            
        return True
    
    def accept(self):
        """Handle dialog acceptance with support for both add and update"""
        if not self.validate():
            return
            
        try:
            data = self.get_data()
            
            if self.barologger_data:  # Editing existing barologger
                success, message = self.baro_model.update_barologger(data)
            else:  # Adding new barologger
                success, message = self.baro_model.add_barologger(data)
                
            if success:
                super().accept()
            else:
                QMessageBox.critical(self, "Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))