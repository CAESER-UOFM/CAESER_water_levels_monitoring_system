from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QMessageBox, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class MonetSettingsDialog(QDialog):
    def __init__(self, settings_handler, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Monet API Settings")
        self.resize(500, 250)
        layout = QVBoxLayout(self)
        
        # Help text at the top
        help_text = QLabel(
            "Configure the credentials for accessing the ArcGIS Monet API. "
            "These settings are required to fetch water level measurements from the Monet system."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(help_text)
        
        # API Credentials Group
        creds_group = QGroupBox("API Credentials")
        creds_layout = QFormLayout(creds_group)
        
        # Username field
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your ArcGIS username")
        creds_layout.addRow("Username:", self.username_edit)
        
        # Password field
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your ArcGIS password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        creds_layout.addRow("Password:", self.password_edit)
        
        # API URL field
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter Monet API URL")
        creds_layout.addRow("API URL:", self.url_edit)
        
        # Add a note about security
        security_note = QLabel(
            "Note: Your password is stored locally and is never shared with third parties."
        )
        security_note.setWordWrap(True)
        security_note.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        creds_layout.addRow("", security_note)
        
        layout.addWidget(creds_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(test_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load settings from settings handler"""
        # Get credentials from settings
        self.username_edit.setText(self.settings_handler.get_setting("monet_username", ""))
        
        # For security, don't load the password directly into the UI
        # Only set it if the user has not yet configured a password
        if not self.settings_handler.get_setting("monet_password", ""):
            self.password_edit.clear()
        else:
            # Indicate that a password is already set
            self.password_edit.setPlaceholderText("Password already set (leave empty to keep current)")
            
        # Load the API URL
        self.url_edit.setText(self.settings_handler.get_setting(
            "monet_api_url", 
            "https://services1.arcgis.com/EX9Lx0EdFAxE7zvX/arcgis/rest/services/MONET/FeatureServer/2/query"
        ))
    
    def test_connection(self):
        """Test the connection to the Monet API"""
        from ..handlers.fetch_monet import generate_arcgis_token
        
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        # If password field is empty, use the stored password
        if not password:
            password = self.settings_handler.get_setting("monet_password", "")
        
        if not username or not password:
            QMessageBox.warning(self, "Missing Credentials", "Please enter both username and password.")
            return
        
        try:
            # Show a "testing" message
            QMessageBox.information(self, "Testing Connection", "Testing connection to Monet API...")
            
            # Try to generate a token
            token = generate_arcgis_token(username, password, verbose=False)
            
            if token:
                QMessageBox.information(self, "Connection Successful", 
                                       "Successfully connected to the Monet API!")
            else:
                QMessageBox.critical(self, "Connection Failed", 
                                   "Failed to connect to the Monet API. Please check your credentials.")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", 
                               f"Error testing connection: {str(e)}")
    
    def save_settings(self):
        """Save settings to settings handler"""
        username = self.username_edit.text()
        password = self.password_edit.text()
        url = self.url_edit.text()
        
        # Validate
        if not username:
            QMessageBox.warning(self, "Missing Username", "Please enter a username.")
            return
            
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter the API URL.")
            return
        
        # Save username and URL
        self.settings_handler.set_setting("monet_username", username)
        self.settings_handler.set_setting("monet_api_url", url)
        
        # Only update password if it was changed (not empty)
        if password:
            self.settings_handler.set_setting("monet_password", password)
        
        # Update the Monet status indicator in the main window if possible
        main_window = self.parent()
        if main_window and hasattr(main_window, 'monet_status_label'):
            main_window.monet_status_label.setText(f"Connected as {username}")
            main_window.monet_status_label.setStyleSheet("color: #007700; font-weight: bold;")
        
        # Show success message and close dialog
        QMessageBox.information(self, "Settings Saved", "Monet API settings have been saved.")
        self.accept() 