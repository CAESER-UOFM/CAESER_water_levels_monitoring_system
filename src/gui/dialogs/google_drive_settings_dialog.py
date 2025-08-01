from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QFileDialog, QMessageBox,
                           QCheckBox, QGroupBox, QProgressDialog)
from PyQt5.QtCore import Qt
import logging
import os
from ..handlers.google_drive_service import GoogleDriveService
from pathlib import Path

logger = logging.getLogger(__name__)

class GoogleDriveSettingsDialog(QDialog):
    def __init__(self, settings_handler, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.drive_service = GoogleDriveService.get_instance(settings_handler)
        self.setup_ui()
        self.load_settings()
        self.update_auth_status()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Google Drive Settings")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        
        # Help text at the top
        help_text = QLabel(
            "Configure Google Drive integration for cloud features. "
            "Authentication is required to access Google Drive for uploading data, "
            "downloading databases, and synchronizing files."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(help_text)
        
        # Authentication Status Group
        auth_group = QGroupBox("Authentication Status")
        auth_layout = QVBoxLayout(auth_group)
        
        # Status display
        status_layout = QHBoxLayout()
        status_label = QLabel("Status:")
        self.status_display = QLabel("Checking...")
        self.status_display.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_display)
        status_layout.addStretch()
        auth_layout.addLayout(status_layout)
        
        # User display (if authenticated)
        user_layout = QHBoxLayout()
        user_label = QLabel("Account:")
        self.user_display = QLabel("Not connected")
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_display)
        user_layout.addStretch()
        auth_layout.addLayout(user_layout)
        
        # Connection buttons
        button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect to Google Drive")
        self.connect_btn.clicked.connect(self.connect_to_drive)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_from_drive)
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        auth_layout.addLayout(button_layout)
        
        # Authentication help
        auth_help = QLabel(
            "Click 'Connect to Google Drive' to authenticate with your Google account. "
            "This will open a web browser where you can grant permission to access your Google Drive."
        )
        auth_help.setWordWrap(True)
        auth_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        auth_layout.addWidget(auth_help)
        
        layout.addWidget(auth_group)
        
        # Folder Configuration Group
        folder_group = QGroupBox("Folder Configuration")
        folder_layout = QVBoxLayout(folder_group)
        
        # Main Folder ID
        main_folder_layout = QHBoxLayout()
        main_folder_label = QLabel("Main Folder ID:")
        self.folder_id = QLineEdit()
        self.folder_id.setPlaceholderText("Google Drive Folder ID for Data")
        folder_help = QLabel("(ID from the shared folder URL)")
        folder_help.setStyleSheet("color: gray; font-style: italic;")
        
        main_folder_layout.addWidget(main_folder_label)
        main_folder_layout.addWidget(self.folder_id, 1)
        main_folder_layout.addWidget(folder_help)
        folder_layout.addLayout(main_folder_layout)
        
        # Main Folder help text
        main_folder_help = QLabel(
            "The main folder where databases and project files are stored. "
            "Find the folder ID in the URL: https://drive.google.com/drive/folders/FOLDER_ID"
        )
        main_folder_help.setWordWrap(True)
        main_folder_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        folder_layout.addWidget(main_folder_help)
        
        # XLE Files Folder ID
        xle_folder_layout = QHBoxLayout()
        xle_folder_label = QLabel("XLE Files Folder ID:")
        self.xle_folder_id = QLineEdit()
        self.xle_folder_id.setPlaceholderText("Google Drive Folder ID for XLE Files")
        xle_folder_help = QLabel("(ID from the XLE files folder URL)")
        xle_folder_help.setStyleSheet("color: gray; font-style: italic;")
        
        xle_folder_layout.addWidget(xle_folder_label)
        xle_folder_layout.addWidget(self.xle_folder_id, 1)
        xle_folder_layout.addWidget(xle_folder_help)
        folder_layout.addLayout(xle_folder_layout)
        
        # XLE Folder help text
        xle_folder_help = QLabel(
            "The folder where XLE data files from sensors are uploaded."
        )
        xle_folder_help.setWordWrap(True)
        xle_folder_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        folder_layout.addWidget(xle_folder_help)
        
        # Projects Folder ID
        projects_folder_layout = QHBoxLayout()
        projects_folder_label = QLabel("Projects Folder ID:")
        self.projects_folder_id = QLineEdit()
        self.projects_folder_id.setPlaceholderText("Google Drive Folder ID for Projects")
        projects_folder_help = QLabel("(ID from the projects folder URL)")
        projects_folder_help.setStyleSheet("color: gray; font-style: italic;")
        
        projects_folder_layout.addWidget(projects_folder_label)
        projects_folder_layout.addWidget(self.projects_folder_id, 1)
        projects_folder_layout.addWidget(projects_folder_help)
        folder_layout.addLayout(projects_folder_layout)
        
        layout.addWidget(folder_group)
        
        # Dialog buttons
        dialog_button_layout = QHBoxLayout()
        dialog_button_layout.addStretch()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        dialog_button_layout.addWidget(self.save_btn)
        dialog_button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(dialog_button_layout)
        
    def update_auth_status(self):
        """Update the authentication status display"""
        if self.drive_service and self.drive_service.authenticated:
            self.status_display.setText("✓ Connected")
            self.status_display.setStyleSheet("color: green; font-weight: bold;")
            
            user_email = self.drive_service.get_user_email()
            self.user_display.setText(user_email or "Authenticated User")
            
            self.connect_btn.setText("Reconnect")
            self.disconnect_btn.setEnabled(True)
            self.test_btn.setEnabled(True)
        else:
            self.status_display.setText("✗ Not Connected")
            self.status_display.setStyleSheet("color: red; font-weight: bold;")
            
            self.user_display.setText("Not connected")
            
            self.connect_btn.setText("Connect to Google Drive")
            self.disconnect_btn.setEnabled(False)
            self.test_btn.setEnabled(False)
    
    def connect_to_drive(self):
        """Connect to Google Drive using OAuth"""
        try:
            # Show progress
            progress = QProgressDialog("Connecting to Google Drive...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # Attempt authentication with browser interaction
            success = self.drive_service.authenticate(force=True, interactive=True)
            
            progress.close()
            
            if success:
                QMessageBox.information(
                    self, 
                    "Connection Successful", 
                    f"Successfully connected to Google Drive as:\n{self.drive_service.get_user_email()}"
                )
                self.update_auth_status()
            else:
                QMessageBox.warning(
                    self, 
                    "Connection Failed", 
                    "Failed to connect to Google Drive. Please check your internet connection and try again."
                )
                
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"An error occurred while connecting to Google Drive:\n\n{str(e)}"
            )
    
    def disconnect_from_drive(self):
        """Disconnect from Google Drive"""
        reply = QMessageBox.question(
            self,
            "Disconnect from Google Drive",
            "Are you sure you want to disconnect from Google Drive?\n\n"
            "This will disable cloud features until you reconnect.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.drive_service.revoke_authentication():
                QMessageBox.information(
                    self,
                    "Disconnected",
                    "Successfully disconnected from Google Drive."
                )
                self.update_auth_status()
            else:
                QMessageBox.warning(
                    self,
                    "Disconnect Failed",
                    "Failed to disconnect from Google Drive."
                )
    
    def test_connection(self):
        """Test the Google Drive connection"""
        if not self.drive_service or not self.drive_service.authenticated:
            QMessageBox.warning(self, "Not Connected", "Please connect to Google Drive first.")
            return
            
        try:
            progress = QProgressDialog("Testing connection...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # Test the connection by getting drive info
            service = self.drive_service.get_service()
            if service:
                about = service.about().get(fields="storageQuota,user").execute()
                user_email = about.get('user', {}).get('emailAddress', 'Unknown')
                quota = about.get('storageQuota', {})
                usage_gb = int(quota.get('usage', 0)) / (1024**3)
                limit_gb = int(quota.get('limit', 0)) / (1024**3)
                
                progress.close()
                
                QMessageBox.information(
                    self,
                    "Connection Test Successful",
                    f"Connected as: {user_email}\n"
                    f"Storage: {usage_gb:.2f} GB / {limit_gb:.2f} GB used"
                )
            else:
                progress.close()
                QMessageBox.warning(self, "Test Failed", "Failed to get Google Drive service.")
                
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(
                self,
                "Connection Test Failed", 
                f"Failed to test connection:\n\n{str(e)}"
            )
    
    def load_settings(self):
        """Load current settings"""
        # Load folder IDs
        self.folder_id.setText(
            self.settings_handler.get_setting("google_drive_folder_id", "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK")
        )
        self.xle_folder_id.setText(
            self.settings_handler.get_setting("google_drive_xle_folder_id", "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW")
        )
        self.projects_folder_id.setText(
            self.settings_handler.get_setting("google_drive_projects_folder_id", "1JjiXRblLAf6rdhiOzrAaYik8bjNpBc9s")  
        )
    
    def save_settings(self):
        """Save settings"""
        try:
            # Save folder IDs
            self.settings_handler.set_setting("google_drive_folder_id", self.folder_id.text().strip())
            self.settings_handler.set_setting("google_drive_xle_folder_id", self.xle_folder_id.text().strip())
            self.settings_handler.set_setting("google_drive_projects_folder_id", self.projects_folder_id.text().strip())
            
            QMessageBox.information(self, "Settings Saved", "Google Drive settings have been saved successfully.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n\n{str(e)}")
    
    def browse_client_secret(self):
        """Legacy method - no longer used for OAuth"""
        QMessageBox.information(
            self,
            "OAuth Authentication", 
            "This application now uses OAuth authentication. "
            "Please use the 'Connect to Google Drive' button to authenticate."
        )