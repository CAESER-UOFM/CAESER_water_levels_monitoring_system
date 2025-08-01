"""
Unified Google Drive OAuth Setup Dialog
Consolidates all Google Drive authentication and folder configuration in one place.
Uses OAuth2 authentication instead of service accounts.
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
from ..handlers.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)

class UnifiedCredentialsDialog(QDialog):
    """Unified dialog for Google Drive OAuth authentication and folder setup"""
    
    def __init__(self, settings_handler, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.drive_service = GoogleDriveService.get_instance(settings_handler)
        self.setWindowTitle("Google Drive Setup")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        
        # Get the config directory
        self.config_dir = Path(__file__).parent.parent.parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        self.setup_ui()
        self.load_current_settings()
        self.update_auth_status()
        
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
OAuth authentication is used to securely connect to your Google Drive account.
        """)
        info_text.setWordWrap(True)
        info_text.setAlignment(Qt.AlignCenter)
        info_text.setStyleSheet("color: #555; font-style: italic; margin: 10px;")
        layout.addWidget(info_text)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # Tab 1: OAuth Authentication
        oauth_tab = self.create_oauth_tab()
        tab_widget.addTab(oauth_tab, "🔐 OAuth Authentication")
        
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
        
    def create_oauth_tab(self):
        """Create OAuth authentication tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
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
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        button_layout.addStretch()
        auth_layout.addLayout(button_layout)
        
        layout.addWidget(auth_group)
        
        # OAuth Help
        help_group = QGroupBox("How OAuth Works")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QLabel("""
<b>OAuth Authentication Process:</b><br>
1. Click "Connect to Google Drive" below<br>
2. Your web browser will open automatically<br>
3. Log in with your Google account<br>
4. Grant permission to access Google Drive<br>
5. Return to this application - you're connected!<br><br>

<b>Benefits:</b><br>
• Uses your own Google Drive storage<br>
• Secure authentication (no passwords stored)<br>
• Easy to revoke access if needed<br>
• No complex file management
        """)
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #555;")
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_group)
        
        layout.addStretch()
        return widget
        
    def create_folder_config_tab(self):
        """Create folder configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Folder Configuration Group
        folder_group = QGroupBox("Google Drive Folders")
        folder_layout = QVBoxLayout(folder_group)
        
        # Main Folder ID
        main_folder_layout = QHBoxLayout()
        main_folder_label = QLabel("Main Folder ID:")
        self.folder_id = QLineEdit()
        self.folder_id.setPlaceholderText("Google Drive Folder ID for Data")
        main_folder_layout.addWidget(main_folder_label)
        main_folder_layout.addWidget(self.folder_id, 1)
        folder_layout.addLayout(main_folder_layout)
        
        # Main Folder help
        main_help = QLabel("The main folder where databases and project files are stored.")
        main_help.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        folder_layout.addWidget(main_help)
        
        # XLE Files Folder ID
        xle_folder_layout = QHBoxLayout()
        xle_folder_label = QLabel("XLE Files Folder ID:")
        self.xle_folder_id = QLineEdit()
        self.xle_folder_id.setPlaceholderText("Google Drive Folder ID for XLE Files")
        xle_folder_layout.addWidget(xle_folder_label)
        xle_folder_layout.addWidget(self.xle_folder_id, 1)
        folder_layout.addLayout(xle_folder_layout)
        
        # XLE help
        xle_help = QLabel("The folder where XLE data files from sensors are uploaded.")
        xle_help.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        folder_layout.addWidget(xle_help)
        
        # Projects Folder ID
        projects_folder_layout = QHBoxLayout()
        projects_folder_label = QLabel("Projects Folder ID:")
        self.projects_folder_id = QLineEdit()
        self.projects_folder_id.setPlaceholderText("Google Drive Folder ID for Projects")
        projects_folder_layout.addWidget(projects_folder_label)
        projects_folder_layout.addWidget(self.projects_folder_id, 1)
        folder_layout.addLayout(projects_folder_layout)
        
        # Projects help
        projects_help = QLabel("The folder where project databases and files are organized.")
        projects_help.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        folder_layout.addWidget(projects_help)
        
        layout.addWidget(folder_group)
        
        # Folder ID Help
        help_group = QGroupBox("How to Find Folder IDs")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QLabel("""
<b>To find a Google Drive folder ID:</b><br>
1. Open the folder in Google Drive (in your web browser)<br>
2. Look at the URL in the address bar<br>
3. The folder ID is the long string after "folders/"<br><br>

<b>Example:</b><br>
URL: https://drive.google.com/drive/folders/<b>1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK</b><br>
Folder ID: <b>1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK</b>
        """)
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #555;")
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_group)
        
        layout.addStretch()
        return widget
        
    def create_instructions_tab(self):
        """Create instructions tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create a scroll area for the instructions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        instructions_widget = QWidget()
        instructions_layout = QVBoxLayout(instructions_widget)
        
        instructions_text = QLabel("""
<h2>Setting up Google Drive Integration</h2>

<h3>Step 1: Connect to Google Drive</h3>
<ol>
<li>Go to the "OAuth Authentication" tab</li>
<li>Click "Connect to Google Drive"</li>
<li>Your web browser will open automatically</li>
<li>Log in with your Google account if prompted</li>
<li>Click "Allow" to grant permissions</li>
<li>Return to this application</li>
</ol>

<h3>Step 2: Configure Folders (Optional)</h3>
<p>The default folder IDs are already configured for the CAESER project. You only need to change these if you want to use different folders:</p>
<ul>
<li><b>Main Folder:</b> Where databases and main files are stored</li>
<li><b>XLE Files Folder:</b> Where sensor data files are uploaded</li>
<li><b>Projects Folder:</b> Where project-specific data is organized</li>
</ul>

<h3>Step 3: Test and Save</h3>
<ol>
<li>Click "Test Connection" to verify everything works</li>
<li>Click "Save & Apply" to save your settings</li>
</ol>

<h3>Troubleshooting</h3>
<p><b>Browser doesn't open:</b> Make sure you have a default web browser set.</p>
<p><b>Permission denied:</b> Check that you granted all requested permissions in the browser.</p>
<p><b>Connection test fails:</b> Verify your internet connection and try reconnecting.</p>

<h3>Security Notes</h3>
<ul>
<li>Your Google account credentials are never stored by this application</li>
<li>You can revoke access anytime through your Google Account settings</li>
<li>Only the permissions you grant are used (Google Drive access)</li>
</ul>
        """)
        instructions_text.setWordWrap(True)
        instructions_text.setOpenExternalLinks(True)
        instructions_layout.addWidget(instructions_text)
        instructions_layout.addStretch()
        
        scroll.setWidget(instructions_widget)
        layout.addWidget(scroll)
        
        return widget
    
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
    
    def load_current_settings(self):
        """Load current settings into the form"""
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
    
    def save_and_apply(self):
        """Save settings and apply changes"""
        try:
            # Save folder IDs
            self.settings_handler.set_setting("google_drive_folder_id", self.folder_id.text().strip())
            self.settings_handler.set_setting("google_drive_xle_folder_id", self.xle_folder_id.text().strip())
            self.settings_handler.set_setting("google_drive_projects_folder_id", self.projects_folder_id.text().strip())
            
            QMessageBox.information(self, "Settings Saved", "Google Drive settings have been saved successfully.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n\n{str(e)}")
    
    def browse_service_account_file(self):
        """Legacy method - no longer used for OAuth"""
        QMessageBox.information(
            self,
            "OAuth Authentication", 
            "This application now uses OAuth authentication. "
            "Please use the 'Connect to Google Drive' button to authenticate."
        )
    
    @staticmethod
    def check_credentials_configured():
        """Check if OAuth credentials are configured (static method for compatibility)"""
        try:
            # Check if OAuth client secret file exists
            app_dir = Path(__file__).parent.parent.parent.parent
            config_dir = app_dir / "config"
            
            # Look for OAuth client secret file
            oauth_files = list(config_dir.glob("client_secret*.json"))
            if not oauth_files:
                return False
                
            # Filter out service account files
            for file_path in oauth_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        # If it's not a service account file, it's likely OAuth
                        if data.get('type') != 'service_account':
                            return True
                except:
                    continue
                    
            return False
        except Exception:
            return False