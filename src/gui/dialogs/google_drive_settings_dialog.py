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
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Google Drive Settings")
        self.resize(600, 350)  # Increased height for additional help text
        layout = QVBoxLayout(self)
        
        # Help text at the top
        help_text = QLabel(
            "These settings are required for Google Drive integration. "
            "The client secret file is needed for authentication, and the folder IDs "
            "specify where your files will be stored in Google Drive."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(help_text)
        
        # Google Drive Authentication Group
        auth_group = QGroupBox("Google Drive Authentication")
        auth_layout = QVBoxLayout(auth_group)
        
        # Client secret file
        secret_layout = QHBoxLayout()
        secret_label = QLabel("Client Secret File:")
        self.secret_path = QLineEdit()
        self.secret_path.setPlaceholderText("Path to client_secret.json")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_client_secret)
        
        secret_layout.addWidget(secret_label)
        secret_layout.addWidget(self.secret_path, 1)
        secret_layout.addWidget(browse_btn)
        auth_layout.addLayout(secret_layout)
        
        # Client secret help text
        secret_help = QLabel(
            "The client_secret.json file is included with the application and should be automatically detected. "
            "If you need to use a different file, please contact your administrator."
        )
        secret_help.setWordWrap(True)
        secret_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        auth_layout.addWidget(secret_help)
        
        # Folder ID
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Main Folder ID:")
        self.folder_id = QLineEdit()
        self.folder_id.setPlaceholderText("Google Drive Folder ID for Data")
        folder_help = QLabel("(ID from the shared folder URL)")
        folder_help.setStyleSheet("color: gray; font-style: italic;")
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_id, 1)
        folder_layout.addWidget(folder_help)
        auth_layout.addLayout(folder_layout)
        
        # Folder ID help text
        folder_id_help = QLabel(
            "The default folder ID is set to the CAESER shared folder. "
            "You can find the folder ID in the URL of your Google Drive folder: "
            "https://drive.google.com/drive/folders/FOLDER_ID"
        )
        folder_id_help.setWordWrap(True)
        folder_id_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        auth_layout.addWidget(folder_id_help)
        
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
        auth_layout.addLayout(xle_folder_layout)
        
        # XLE Folder ID help text
        xle_folder_id_help = QLabel(
            "This folder ID is for the folder containing XLE files. "
            "This is used for monitoring and auto-syncing XLE files from Google Drive."
        )
        xle_folder_id_help.setWordWrap(True)
        xle_folder_id_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        auth_layout.addWidget(xle_folder_id_help)
        
        # Authentication status
        status_layout = QHBoxLayout()
        status_label = QLabel("Authentication Status:")
        self.status_value = QLabel("Not authenticated")
        self.status_value.setStyleSheet("font-weight: bold;")
        self.auth_btn = QPushButton("Authenticate")
        self.auth_btn.clicked.connect(self.authenticate)
        
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_value, 1)
        status_layout.addWidget(self.auth_btn)
        auth_layout.addLayout(status_layout)
        
        # Auto-check on startup
        auto_layout = QHBoxLayout()
        auto_label = QLabel("Auto-check on startup:")
        self.auto_check = QCheckBox()
        
        auto_layout.addWidget(auto_label)
        auto_layout.addWidget(self.auto_check)
        auto_layout.addStretch()
        auth_layout.addLayout(auto_layout)
        
        layout.addWidget(auth_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Update authentication status
        self.update_auth_status()
        
    def browse_client_secret(self):
        """Browse for client secret file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Client Secret JSON File",
            "",
            "JSON files (*.json)"
        )
        
        if file_path:
            self.secret_path.setText(file_path)
    
    def authenticate(self):
        """Authenticate with Google Drive and perform complete initialization"""
        # Create progress dialog
        progress = QProgressDialog("Authenticating with Google Drive...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Google Drive Setup")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        progress.setValue(10)
        
        try:
            # Save current settings first
            self.settings_handler.set_setting("google_drive_secret_path", self.secret_path.text())
            self.settings_handler.set_setting("google_drive_folder_id", self.folder_id.text())
            self.settings_handler.set_setting("google_drive_xle_folder_id", self.xle_folder_id.text())
            
            # Update progress
            progress.setValue(20)
            progress.setLabelText("Authenticating with Google Drive...")
            
            # Try to authenticate
            if self.drive_service.authenticate(force=True):
                # Get main window reference
                main_window = self.parent()
                
                # Update progress
                progress.setValue(40)
                progress.setLabelText("Setting up Google Drive components...")
                
                # Initialize or update Google Drive database handler
                if not hasattr(main_window, 'drive_db_handler') or main_window.drive_db_handler is None:
                    from ..handlers.google_drive_db_handler import GoogleDriveDatabaseHandler
                    main_window.drive_db_handler = GoogleDriveDatabaseHandler(self.settings_handler)
                
                # Initialize the database handler with the authenticated service
                main_window.drive_db_handler.drive_service = self.drive_service
                main_window.drive_db_handler.folder_id = self.folder_id.text()
                
                # Update progress
                progress.setValue(50)
                progress.setLabelText("Setting up Google Drive data handler...")
                
                # Initialize or update Google Drive data handler
                if not hasattr(main_window, 'drive_data_handler') or main_window.drive_data_handler is None:
                    from ..handlers.google_drive_data_handler import GoogleDriveDataHandler
                    main_window.drive_data_handler = GoogleDriveDataHandler(self.settings_handler)
                
                # Initialize the data handler with the authenticated service
                main_window.drive_data_handler.drive_service = self.drive_service
                main_window.drive_data_handler.folder_id = self.folder_id.text()
                
                # Update progress
                progress.setValue(60)
                progress.setLabelText("Setting up Google Drive monitor...")
                
                # Initialize or update Google Drive monitor
                xle_folder_id = self.xle_folder_id.text()
                if not hasattr(main_window, 'drive_monitor') or main_window.drive_monitor is None:
                    from ..handlers.google_drive_monitor import GoogleDriveMonitor
                    main_window.drive_monitor = GoogleDriveMonitor(xle_folder_id, self.settings_handler)
                else:
                    main_window.drive_monitor.set_folder_id(xle_folder_id)
                
                # Initialize the monitor with the authenticated service
                main_window.drive_monitor.drive_service = self.drive_service
                
                # Update progress
                progress.setValue(70)
                progress.setLabelText("Downloading data folders from Google Drive...")
                
                # Download data folders
                self.download_data_folders(main_window, progress)
                
                # Update progress
                progress.setValue(90)
                progress.setLabelText("Checking for XLE files in Google Drive...")
                
                # Initialize folders in the monitor
                main_window.drive_monitor.initialize_folders()
                
                # Check for new files (file organization)
                main_window.drive_monitor.check_for_new_files()
                
                # Update progress
                progress.setValue(100)
                progress.setLabelText("Setup completed successfully!")
                
                # Show success message
                QMessageBox.information(self, "Setup Successful", 
                                      "Successfully set up Google Drive integration.")
                                    
                # Notify any Water Level Runs tabs that we're connected
                if hasattr(main_window, '_tabs') and 'water_level_runs' in main_window._tabs:
                    runs_tab = main_window._tabs['water_level_runs']
                    if hasattr(runs_tab, 'load_existing_runs'):
                        runs_tab.load_existing_runs()
            else:
                QMessageBox.warning(self, "Authentication Failed", 
                                 "Failed to authenticate with Google Drive. Please check your settings.")
            
            # Update status
            self.update_auth_status()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during Google Drive setup: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error during Google Drive setup: {str(e)}")
        finally:
            # Close progress dialog
            if progress.isVisible():
                progress.close()
    
    def download_data_folders(self, main_window, progress=None):
        """Download data folders from Google Drive"""
        try:
            if progress:
                progress.setLabelText("Downloading data folder from Google Drive...")
            
            # Download data folder
            result = main_window.drive_data_handler.download_data_folder()
            
            if not result:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Failed to download data folder from Google Drive")
            
            if progress:
                progress.setValue(progress.value() + 10)
            
            return result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error downloading data folders: {e}", exc_info=True)
            return False
    
    def update_auth_status(self):
        """Update the authentication status display"""
        if self.drive_service.authenticated:
            self.status_value.setText("Authenticated")
            self.status_value.setStyleSheet("color: green; font-weight: bold;")
            self.auth_btn.setText("Re-authenticate")
        else:
            self.status_value.setText("Not authenticated")
            self.status_value.setStyleSheet("color: red; font-weight: bold;")
            self.auth_btn.setText("Authenticate")
            
    def load_settings(self):
        """Load settings from settings handler"""
        # Get client secret path from settings
        client_secret_path = self.settings_handler.get_setting("google_drive_secret_path", "")
        
        # If the path is not set or the file doesn't exist, try to find a default one
        if not client_secret_path or not os.path.exists(client_secret_path):
            config_dir = Path.cwd() / "config"
            if config_dir.exists():
                # Look for client_secret*.json files
                secret_files = list(config_dir.glob("client_secret*.json"))
                if secret_files:
                    client_secret_path = str(secret_files[0])
        
        self.secret_path.setText(client_secret_path)
        
        # Get folder IDs from settings
        self.folder_id.setText(self.settings_handler.get_setting("google_drive_folder_id", "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"))
        self.xle_folder_id.setText(self.settings_handler.get_setting("google_drive_xle_folder_id", "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"))
        
        # Get auto-check setting
        self.auto_check.setChecked(self.settings_handler.get_setting("google_drive_auto_check", False))
        
    def save_settings(self):
        """Save settings to settings handler"""
        # Save Google Drive settings
        self.settings_handler.set_setting("google_drive_secret_path", self.secret_path.text())
        self.settings_handler.set_setting("google_drive_folder_id", self.folder_id.text())
        self.settings_handler.set_setting("google_drive_xle_folder_id", self.xle_folder_id.text())
        self.settings_handler.set_setting("google_drive_auto_check", self.auto_check.isChecked())
        
        # Close the dialog
        self.accept() 