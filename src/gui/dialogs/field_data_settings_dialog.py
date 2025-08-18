"""
Field Data Settings Dialog
Configure multiple field laptop Google Drive folders for data consolidation
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QTextEdit, QScrollArea,
    QWidget, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

class FieldLaptopWidget(QWidget):
    """Widget for managing a single field laptop folder configuration"""
    
    remove_requested = pyqtSignal(object)  # Emitted when remove button is clicked
    
    def __init__(self, laptop_name="", folder_id="", parent=None):
        super().__init__(parent)
        self.laptop_name = laptop_name
        self.folder_id = folder_id
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the laptop widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Laptop name input
        self.name_input = QLineEdit(self.laptop_name)
        self.name_input.setPlaceholderText("e.g., Laptop_1")
        self.name_input.setMaximumWidth(100)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)
        
        # Folder ID input
        self.folder_input = QLineEdit(self.folder_id)
        self.folder_input.setPlaceholderText("Google Drive Folder ID")
        layout.addWidget(QLabel("Folder ID:"))
        layout.addWidget(self.folder_input)
        
        # Test button
        self.test_button = QPushButton("🔍 Test")
        self.test_button.clicked.connect(self.test_folder_access)
        self.test_button.setMaximumWidth(60)
        layout.addWidget(self.test_button)
        
        # Status label
        self.status_label = QLabel("Not tested")
        self.status_label.setStyleSheet("color: #666;")
        self.status_label.setMaximumWidth(100)
        layout.addWidget(self.status_label)
        
        # Remove button
        self.remove_button = QPushButton("❌")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_button.setMaximumWidth(30)
        self.remove_button.setToolTip("Remove this field laptop")
        layout.addWidget(self.remove_button)
    
    def test_folder_access(self):
        """Test access to this folder using Google Drive service"""
        folder_id = self.folder_input.text().strip()
        if not folder_id:
            self.status_label.setText("❌ No ID")
            self.status_label.setStyleSheet("color: #cc0000;")
            return
        
        try:
            # Import Google service handler
            from ...handlers.google_service_account import GoogleServiceAccountHandler
            from ...handlers.settings_handler import SettingsHandler
            
            # Get existing service if available (from parent dialog)
            parent_dialog = self.parent()
            while parent_dialog and not hasattr(parent_dialog, 'google_service'):
                parent_dialog = parent_dialog.parent()
            
            if parent_dialog and hasattr(parent_dialog, 'google_service') and parent_dialog.google_service:
                google_service = parent_dialog.google_service
            else:
                # Create temporary service for testing
                settings_handler = SettingsHandler()
                google_service = GoogleServiceAccountHandler(settings_handler)
                if not google_service.authenticate():
                    self.status_label.setText("❌ Auth failed")
                    self.status_label.setStyleSheet("color: #cc0000;")
                    return
            
            # Test folder access
            google_service.set_solinst_folder_id(folder_id)
            files = google_service.list_xle_files()
            
            self.status_label.setText(f"✅ {len(files)} files")
            self.status_label.setStyleSheet("color: #007700;")
            
        except Exception as e:
            logger.error(f"Error testing folder {folder_id}: {e}")
            self.status_label.setText("❌ Error")
            self.status_label.setStyleSheet("color: #cc0000;")
    
    def get_laptop_config(self):
        """Get the current laptop configuration"""
        return {
            'name': self.name_input.text().strip(),
            'folder_id': self.folder_input.text().strip()
        }
    
    def is_valid(self):
        """Check if this laptop configuration is valid"""
        config = self.get_laptop_config()
        return bool(config['name'] and config['folder_id'])


class FieldDataSettingsDialog(QDialog):
    """Dialog for configuring field laptop Google Drive folders"""
    
    def __init__(self, settings_handler, google_service=None, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.google_service = google_service
        self.laptop_widgets = []
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Field Data Settings")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Field Laptop Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Configure Google Drive folders for multiple field laptops.\n"
            "Each laptop's SOLINST folder will be scanned for XLE data files."
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(desc_label)
        
        # Field Laptops Group
        laptops_group = QGroupBox("Field Laptop Folders")
        laptops_layout = QVBoxLayout(laptops_group)
        
        # Scroll area for laptop widgets
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.addStretch()  # Push content to top
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)
        
        laptops_layout.addWidget(self.scroll_area)
        
        # Add laptop button
        add_button_layout = QHBoxLayout()
        self.add_laptop_button = QPushButton("➕ Add Field Laptop")
        self.add_laptop_button.clicked.connect(self.add_laptop)
        self.add_laptop_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_button_layout.addWidget(self.add_laptop_button)
        add_button_layout.addStretch()
        
        laptops_layout.addLayout(add_button_layout)
        layout.addWidget(laptops_group)
        
        # Test All button
        test_all_layout = QHBoxLayout()
        self.test_all_button = QPushButton("🔍 Test All Folders")
        self.test_all_button.clicked.connect(self.test_all_folders)
        self.test_all_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        test_all_layout.addWidget(self.test_all_button)
        test_all_layout.addStretch()
        
        layout.addLayout(test_all_layout)
        
        # Information text
        info_group = QGroupBox("How It Works")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QTextEdit()
        info_text.setMaximumHeight(120)
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "1. Add each field laptop by specifying a name and Google Drive folder ID\n"
            "2. The folder ID can be found in the Google Drive URL after '/folders/'\n"
            "3. Each laptop's SOLINST folder will be scanned for XLE data files\n"
            "4. Data from all laptops will be consolidated into monthly folders\n"
            "5. Files will be tagged with their source laptop for tracking"
        )
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("💾 Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #3070B0;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2060A0;
            }
        """)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #707070;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load current field laptop settings"""
        try:
            # Load existing laptop configurations
            laptop_configs = [
                ("Laptop_1", "google_drive_laptop_1_folder_id"),
                ("Laptop_2", "google_drive_laptop_2_folder_id"), 
                ("Laptop_3", "google_drive_laptop_3_folder_id"),
                ("Laptop_4", "google_drive_laptop_4_folder_id"),
                ("Laptop_5", "google_drive_laptop_5_folder_id")
            ]
            
            for laptop_name, setting_key in laptop_configs:
                folder_id = self.settings_handler.get_setting(setting_key, "")
                if folder_id:
                    self.add_laptop(laptop_name, folder_id)
            
            # If no laptops configured, add a default empty one
            if not self.laptop_widgets:
                self.add_laptop("Laptop_1", "")
                
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def add_laptop(self, name="", folder_id=""):
        """Add a new field laptop widget"""
        if not name:
            # Generate default name
            name = f"Laptop_{len(self.laptop_widgets) + 1}"
        
        laptop_widget = FieldLaptopWidget(name, folder_id, self.scroll_widget)
        laptop_widget.remove_requested.connect(self.remove_laptop)
        
        # Insert before the stretch at the end
        self.scroll_layout.insertWidget(len(self.laptop_widgets), laptop_widget)
        self.laptop_widgets.append(laptop_widget)
        
        # Add separator line (except for first widget)
        if len(self.laptop_widgets) > 1:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setStyleSheet("color: #ccc;")
            self.scroll_layout.insertWidget(len(self.laptop_widgets) - 1, separator)
    
    def remove_laptop(self, laptop_widget):
        """Remove a field laptop widget"""
        if len(self.laptop_widgets) <= 1:
            QMessageBox.information(
                self,
                "Cannot Remove",
                "At least one field laptop must be configured."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Remove Laptop",
            f"Remove {laptop_widget.name_input.text()} configuration?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Find and remove the widget and its separator
            index = self.laptop_widgets.index(laptop_widget)
            self.laptop_widgets.remove(laptop_widget)
            laptop_widget.setParent(None)
            laptop_widget.deleteLater()
            
            # Remove separator if it exists
            if index > 0:  # Remove separator above this widget
                separator_index = index * 2 - 1  # Account for separators
                if separator_index < self.scroll_layout.count() - 1:  # Don't remove the stretch
                    separator = self.scroll_layout.itemAt(separator_index).widget()
                    if separator:
                        separator.setParent(None)
                        separator.deleteLater()
    
    def test_all_folders(self):
        """Test access to all configured field laptop folders"""
        if not self.google_service:
            # Try to create temporary service
            try:
                from ...handlers.google_service_account import GoogleServiceAccountHandler
                self.google_service = GoogleServiceAccountHandler(self.settings_handler)
                if not self.google_service.authenticate():
                    QMessageBox.warning(
                        self,
                        "Authentication Failed",
                        "Could not authenticate with Google Drive. Please check your service account configuration."
                    )
                    return
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not initialize Google Drive service:\n{str(e)}"
                )
                return
        
        # Test each laptop widget
        for laptop_widget in self.laptop_widgets:
            if laptop_widget.folder_input.text().strip():
                laptop_widget.test_folder_access()
    
    def save_settings(self):
        """Save field laptop settings"""
        try:
            # Validate all laptop configurations
            valid_laptops = []
            for laptop_widget in self.laptop_widgets:
                config = laptop_widget.get_laptop_config()
                if config['name'] and config['folder_id']:
                    valid_laptops.append(config)
                elif config['name'] or config['folder_id']:
                    # Partial configuration
                    QMessageBox.warning(
                        self,
                        "Incomplete Configuration",
                        f"Laptop '{config['name']}' has incomplete configuration.\n"
                        "Please provide both name and folder ID, or remove this entry."
                    )
                    return
            
            if not valid_laptops:
                QMessageBox.warning(
                    self,
                    "No Laptops Configured",
                    "At least one field laptop must be configured."
                )
                return
            
            # Check for duplicate names
            names = [laptop['name'] for laptop in valid_laptops]
            if len(names) != len(set(names)):
                QMessageBox.warning(
                    self,
                    "Duplicate Names",
                    "Each field laptop must have a unique name."
                )
                return
            
            # Clear existing laptop settings
            for i in range(1, 10):  # Clear up to 10 possible laptops
                self.settings_handler.set_setting(f"google_drive_laptop_{i}_folder_id", "")
            
            # Save new configurations
            for i, laptop in enumerate(valid_laptops, 1):
                setting_key = f"google_drive_laptop_{i}_folder_id"
                self.settings_handler.set_setting(setting_key, laptop['folder_id'])
                logger.info(f"Saved {laptop['name']} -> {setting_key}: {laptop['folder_id']}")
            
            QMessageBox.information(
                self,
                "Settings Saved",
                f"Field laptop settings have been saved successfully!\n"
                f"Configured {len(valid_laptops)} field laptops."
            )
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{str(e)}")