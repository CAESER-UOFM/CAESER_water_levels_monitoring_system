"""
Unified Google Drive Credentials Setup Dialog
Consolidates all Google Drive authentication and folder configuration in one place.
Only requires service account authentication (OAuth client secrets are not used).
"""

import os
import json
import shutil
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QFileDialog, QMessageBox,
                           QTabWidget, QWidget, QGroupBox, QScrollArea,
                           QProgressDialog, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

class UnifiedCredentialsDialog(QDialog):
    """Unified dialog for Google Drive credentials and folder setup"""
    
    def __init__(self, settings_handler, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.setWindowTitle("Google Drive Setup")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        
        # Get the config directory
        self.config_dir = Path(__file__).parent.parent.parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        self.setup_ui()
        self.load_current_settings()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🔑 Google Drive Setup")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Info text
        info_text = QLabel("""
This dialog configures Google Drive integration for the Water Level Monitoring System.
Only a service account JSON file is required - no OAuth client secrets needed.
        """)
        info_text.setWordWrap(True)
        info_text.setAlignment(Qt.AlignCenter)
        info_text.setStyleSheet("color: #555; font-style: italic; margin: 10px;")
        layout.addWidget(info_text)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # Tab 1: Service Account Setup
        service_account_tab = self.create_service_account_tab()
        tab_widget.addTab(service_account_tab, "🔐 Service Account")
        
        # Tab 2: Folder Configuration
        folder_config_tab = self.create_folder_config_tab()
        tab_widget.addTab(folder_config_tab, "📁 Folder Setup")
        
        # Tab 3: Instructions
        instructions_tab = self.create_instructions_tab()
        tab_widget.addTab(instructions_tab, "📋 Instructions")
        
        layout.addWidget(tab_widget)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.clicked.connect(self.save_and_apply)
        self.save_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 8px; }")
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def create_service_account_tab(self):
        """Create service account setup tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Service Account Group
        service_group = QGroupBox("Service Account Authentication")
        service_layout = QVBoxLayout(service_group)
        
        # Info
        service_info = QLabel("""
<b>Service Account File Required</b><br>
This is the only credential file needed. OAuth client secrets are not used by this application.
        """)
        service_info.setWordWrap(True)
        service_layout.addWidget(service_info)
        
        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Service Account JSON:")
        self.service_account_path = QLineEdit()
        self.service_account_path.setPlaceholderText("Path to service account .json file")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_service_account)
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.service_account_path, 1)
        file_layout.addWidget(browse_btn)
        service_layout.addLayout(file_layout)
        
        # File info
        file_info = QLabel("File should be named like: your-project-name-123456.json")
        file_info.setStyleSheet("color: #666; font-style: italic; margin: 5px;")
        service_layout.addWidget(file_info)
        
        # Download from Google Drive option
        download_group = QGroupBox("Download from Google Drive (Authorized Users)")
        download_layout = QVBoxLayout(download_group)
        
        download_info = QLabel("""
If you have access to the credentials repository, you can download the service account file directly:
        """)
        download_info.setWordWrap(True)
        download_layout.addWidget(download_info)
        
        download_btn_layout = QHBoxLayout()
        download_link = QLabel('<a href="https://drive.google.com/file/d/1Qn4jAPXTrT7GBzU6JdG6W-KogT4yZBlR/view?usp=drive_link">Access Credentials Folder</a>')
        download_link.setOpenExternalLinks(True)
        download_btn_layout.addWidget(download_link)
        
        auto_download_btn = QPushButton("Select Downloaded File")
        auto_download_btn.clicked.connect(self.select_downloaded_service_account)
        download_btn_layout.addWidget(auto_download_btn)
        download_btn_layout.addStretch()
        
        download_layout.addLayout(download_btn_layout)
        service_layout.addWidget(download_group)
        
        # Status
        self.service_status = QLabel("")
        self.service_status.setWordWrap(True)
        service_layout.addWidget(self.service_status)
        
        layout.addWidget(service_group)
        layout.addStretch()
        return widget
        
    def create_folder_config_tab(self):
        """Create folder configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Folder Configuration Group
        folder_group = QGroupBox("Google Drive Folder Configuration")
        folder_layout = QVBoxLayout(folder_group)
        
        # Info
        folder_info = QLabel("""
Configure the Google Drive folders used by the application. 
You can find folder IDs in the URL of your Google Drive folders.
        """)
        folder_info.setWordWrap(True)
        folder_layout.addWidget(folder_info)
        
        # Main database folder
        main_layout = QHBoxLayout()
        main_label = QLabel("Main Database Folder:")
        self.main_folder_id = QLineEdit()
        self.main_folder_id.setPlaceholderText("Folder ID for main databases (water_levels_monitoring)")
        main_layout.addWidget(main_label)
        main_layout.addWidget(self.main_folder_id, 1)
        folder_layout.addLayout(main_layout)
        
        main_help = QLabel("Default: CAESER shared folder for databases")
        main_help.setStyleSheet("color: #666; font-style: italic; margin-left: 20px;")
        folder_layout.addWidget(main_help)
        
        # XLE files folder
        xle_layout = QHBoxLayout()
        xle_label = QLabel("XLE Files Folder:")
        self.xle_folder_id = QLineEdit()
        self.xle_folder_id.setPlaceholderText("Folder ID for XLE files monitoring")
        xle_layout.addWidget(xle_label)
        xle_layout.addWidget(self.xle_folder_id, 1)
        folder_layout.addLayout(xle_layout)
        
        xle_help = QLabel("Default: Solinst folder for field laptop XLE files")
        xle_help.setStyleSheet("color: #666; font-style: italic; margin-left: 20px;")
        folder_layout.addWidget(xle_help)
        
        # Field data folders
        field_layout = QHBoxLayout()
        field_label = QLabel("Field Data Folders:")
        self.field_folders = QLineEdit()
        self.field_folders.setPlaceholderText("Comma-separated folder IDs for field data")
        field_layout.addWidget(field_label)
        field_layout.addWidget(self.field_folders, 1)
        folder_layout.addLayout(field_layout)
        
        field_help = QLabel("Multiple folder IDs separated by commas (for field laptops)")
        field_help.setStyleSheet("color: #666; font-style: italic; margin-left: 20px;")
        folder_layout.addWidget(field_help)
        
        # Projects folder
        projects_layout = QHBoxLayout()
        projects_label = QLabel("Projects Folder:")
        self.projects_folder_id = QLineEdit()
        self.projects_folder_id.setPlaceholderText("Folder ID for projects (optional)")
        projects_layout.addWidget(projects_label)
        projects_layout.addWidget(self.projects_folder_id, 1)
        folder_layout.addLayout(projects_layout)
        
        projects_help = QLabel("Optional: Specific projects folder")
        projects_help.setStyleSheet("color: #666; font-style: italic; margin-left: 20px;")
        folder_layout.addWidget(projects_help)
        
        layout.addWidget(folder_group)
        
        # Auto-check settings
        auto_group = QGroupBox("Automatic Features")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_check_startup = QCheckBox("Auto-check Google Drive on startup")
        auto_layout.addWidget(self.auto_check_startup)
        
        layout.addWidget(auto_group)
        
        # Folder status
        self.folder_status = QLabel("")
        self.folder_status.setWordWrap(True)
        layout.addWidget(self.folder_status)
        
        layout.addStretch()
        return widget
        
    def create_instructions_tab(self):
        """Create instructions tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        instructions_html = """
<h3>Google Drive Setup Instructions</h3>

<h4>Service Account Setup</h4>
<p><b>Option 1: For Authorized Users</b></p>
<ol>
<li>Access the <a href="https://drive.google.com/file/d/1Qn4jAPXTrT7GBzU6JdG6W-KogT4yZBlR/view?usp=drive_link">credentials repository</a></li>
<li>Download the service account JSON file</li>
<li>Use "Select Downloaded File" to import it</li>
</ol>

<p><b>Option 2: Create Your Own Service Account</b></p>
<ol>
<li>Go to <a href="https://console.cloud.google.com">Google Cloud Console</a></li>
<li>Create or select a project</li>
<li>Enable Google Drive API</li>
<li>Go to "IAM & Admin" → "Service Accounts"</li>
<li>Create a service account with a descriptive name</li>
<li>Download the JSON key file</li>
<li>Share your Google Drive folders with the service account email</li>
</ol>

<h4>Finding Folder IDs</h4>
<p>Google Drive folder IDs can be found in the URL when viewing a folder:</p>
<p><code>https://drive.google.com/drive/folders/FOLDER_ID_HERE</code></p>

<h4>Required Folder Permissions</h4>
<p>Make sure to share these folders with your service account email:</p>
<ul>
<li><b>Main Database Folder:</b> Read/Write access for database storage</li>
<li><b>XLE Files Folder:</b> Read access for monitoring new files</li>
<li><b>Field Data Folders:</b> Read access for field laptop integration</li>
</ul>

<h4>Default Folder IDs</h4>
<ul>
<li><b>Main Database:</b> 1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK (CAESER shared folder)</li>
<li><b>XLE Files:</b> 1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW (Solinst folder)</li>
<li><b>Field Data:</b> 1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW (Same as XLE for field laptops)</li>
</ul>

<h4>Note About OAuth Client Secrets</h4>
<p><b>OAuth client secrets are NOT required.</b> This application uses service account authentication only.</p>
        """
        
        instructions_label = QLabel(instructions_html)
        instructions_label.setWordWrap(True)
        instructions_label.setOpenExternalLinks(True)
        scroll_layout.addWidget(instructions_label)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        return widget
        
    def browse_service_account(self):
        """Browse for service account file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Service Account JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.service_account_path.setText(file_path)
            self.validate_service_account_file(file_path)
            
    def select_downloaded_service_account(self):
        """Select a downloaded service account file"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Downloaded Service Account File", "", "JSON Files (*.json)")
        
        if files:
            service_account_file = None
            
            # Look for service account file
            for file_path in files:
                if self.is_service_account_file(file_path):
                    service_account_file = file_path
                    break
            
            if service_account_file:
                # Copy to config directory
                dest_path = self.config_dir / Path(service_account_file).name
                try:
                    shutil.copy2(service_account_file, dest_path)
                    self.service_account_path.setText(str(dest_path))
                    self.service_status.setText(f"✅ Service account file copied to: {dest_path.name}")
                    self.service_status.setStyleSheet("color: green;")
                except Exception as e:
                    self.service_status.setText(f"❌ Error copying file: {str(e)}")
                    self.service_status.setStyleSheet("color: red;")
            else:
                self.service_status.setText("❌ No valid service account file found in selection.")
                self.service_status.setStyleSheet("color: red;")
                
    def is_service_account_file(self, file_path):
        """Check if a file is a service account JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('type') == 'service_account'
        except:
            return False
            
    def validate_service_account_file(self, file_path):
        """Validate service account file"""
        try:
            if not os.path.exists(file_path):
                self.service_status.setText("❌ File does not exist")
                self.service_status.setStyleSheet("color: red;")
                return False
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            if data.get('type') != 'service_account':
                self.service_status.setText("❌ Not a valid service account file")
                self.service_status.setStyleSheet("color: red;")
                return False
                
            email = data.get('client_email', 'Unknown')
            self.service_status.setText(f"✅ Valid service account: {email}")
            self.service_status.setStyleSheet("color: green;")
            return True
            
        except json.JSONDecodeError:
            self.service_status.setText("❌ Invalid JSON file")
            self.service_status.setStyleSheet("color: red;")
            return False
        except Exception as e:
            self.service_status.setText(f"❌ Error validating file: {str(e)}")
            self.service_status.setStyleSheet("color: red;")
            return False
            
    def load_current_settings(self):
        """Load current settings into the dialog"""
        # Service account path
        service_path = self.settings_handler.get_setting("service_account_key_path", "")
        self.service_account_path.setText(service_path)
        if service_path:
            self.validate_service_account_file(service_path)
            
        # Folder IDs
        self.main_folder_id.setText(
            self.settings_handler.get_setting("google_drive_folder_id", "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"))
        self.xle_folder_id.setText(
            self.settings_handler.get_setting("google_drive_xle_folder_id", "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"))
        self.projects_folder_id.setText(
            self.settings_handler.get_setting("google_drive_projects_folder_id", ""))
            
        # Field data folders (convert list to comma-separated string)
        field_folders = self.settings_handler.get_setting("field_data_folders", ["1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"])
        if isinstance(field_folders, list):
            self.field_folders.setText(", ".join(field_folders))
        else:
            self.field_folders.setText(str(field_folders))
            
        # Auto-check setting
        self.auto_check_startup.setChecked(
            self.settings_handler.get_setting("google_drive_auto_check", False))
            
    def test_connection(self):
        """Test Google Drive connection"""
        if not self.service_account_path.text():
            QMessageBox.warning(self, "Missing Service Account", 
                              "Please select a service account file first.")
            return
            
        if not self.validate_service_account_file(self.service_account_path.text()):
            QMessageBox.warning(self, "Invalid Service Account", 
                              "Please select a valid service account file.")
            return
            
        progress = QProgressDialog("Testing Google Drive connection...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Connection Test")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        try:
            # Test service account authentication
            progress.setValue(25)
            progress.setLabelText("Authenticating with service account...")
            
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path.text(),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            progress.setValue(50)
            progress.setLabelText("Building Drive service...")
            
            service = build('drive', 'v3', credentials=credentials)
            
            progress.setValue(75)
            progress.setLabelText("Testing folder access...")
            
            # Test access to main folder
            folder_id = self.main_folder_id.text()
            if folder_id:
                try:
                    service.files().get(fileId=folder_id).execute()
                    folder_access = "✅ Main folder accessible"
                except:
                    folder_access = "⚠️ Main folder not accessible"
            else:
                folder_access = "⚠️ No main folder ID specified"
                
            progress.setValue(100)
            progress.close()
            
            QMessageBox.information(self, "Connection Test Results", 
                                  f"✅ Service account authentication successful\n" +
                                  f"{folder_access}\n\n" +
                                  f"Service account: {credentials.service_account_email}")
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Connection Test Failed", 
                               f"Failed to connect to Google Drive:\n{str(e)}")
            
    def save_and_apply(self):
        """Save settings and apply configuration"""
        try:
            # Validate service account
            if not self.service_account_path.text():
                QMessageBox.warning(self, "Missing Service Account", 
                                  "Please select a service account file.")
                return
                
            if not self.validate_service_account_file(self.service_account_path.text()):
                QMessageBox.warning(self, "Invalid Service Account", 
                                  "Please select a valid service account file.")
                return
                
            # Save settings
            self.settings_handler.set_setting("service_account_key_path", self.service_account_path.text())
            self.settings_handler.set_setting("google_drive_folder_id", self.main_folder_id.text())
            self.settings_handler.set_setting("google_drive_xle_folder_id", self.xle_folder_id.text())
            self.settings_handler.set_setting("google_drive_projects_folder_id", self.projects_folder_id.text())
            self.settings_handler.set_setting("google_drive_auto_check", self.auto_check_startup.isChecked())
            
            # Parse field folders
            field_folders_text = self.field_folders.text().strip()
            if field_folders_text:
                field_folders_list = [f.strip() for f in field_folders_text.split(",") if f.strip()]
                self.settings_handler.set_setting("field_data_folders", field_folders_list)
            
            # Remove obsolete OAuth client secret setting
            self.settings_handler.set_setting("google_drive_secret_path", "")
            
            QMessageBox.information(self, "Settings Saved", 
                                  "Google Drive configuration saved successfully!\n\n" +
                                  "The application will now use the new settings.")
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {str(e)}")
            
    @staticmethod
    def check_credentials_configured(settings_handler):
        """Check if Google Drive credentials are properly configured"""
        service_account_path = settings_handler.get_setting("service_account_key_path", "")
        
        if not service_account_path or not os.path.exists(service_account_path):
            return False
            
        try:
            with open(service_account_path, 'r') as f:
                data = json.load(f)
                return data.get('type') == 'service_account'
        except:
            return False