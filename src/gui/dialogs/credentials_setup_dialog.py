"""
Credentials Setup Dialog for Water Level Monitoring Application
Helps users set up Google API credentials when they're missing.
"""

import os
import json
import shutil
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QFileDialog, QMessageBox,
                           QTabWidget, QWidget, QGroupBox, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

class CredentialsSetupDialog(QDialog):
    """Dialog to help users set up Google API credentials"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Google API Credentials Setup")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        # Get the config directory
        self.config_dir = Path(__file__).parent.parent.parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🔑 Google API Credentials Required")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Info text
        info_text = QLabel("""
This application requires Google API credentials to access Google Drive features.
You need two credential files to use the full functionality:
        """)
        info_text.setWordWrap(True)
        info_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_text)
        
        # Create tabs for different setup methods
        tab_widget = QTabWidget()
        
        # Tab 1: Download from Google Drive
        google_drive_tab = self.create_google_drive_tab()
        tab_widget.addTab(google_drive_tab, "☁️ From Google Drive")
        
        # Tab 2: Manual file selection
        manual_tab = self.create_manual_tab()
        tab_widget.addTab(manual_tab, "📁 Select Files Manually")
        
        # Tab 3: Instructions for getting credentials
        instructions_tab = self.create_instructions_tab()
        tab_widget.addTab(instructions_tab, "📋 How to Get Credentials")
        
        layout.addWidget(tab_widget)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.skip_btn = QPushButton("Skip (Limited Functionality)")
        self.skip_btn.clicked.connect(self.skip_setup)
        button_layout.addWidget(self.skip_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def create_google_drive_tab(self):
        """Create tab for Google Drive credentials download"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        instructions = QLabel("""
<b>For Authorized Users with Google Drive Access:</b><br><br>
1. <a href="https://drive.google.com/file/d/1Qn4jAPXTrT7GBzU6JdG6W-KogT4yZBlR/view?usp=drive_link">Click here to access the credentials folder</a><br>
2. Download both credential files from the folder<br>
3. Click "Select Downloaded Folder" below and choose your Downloads folder<br>
4. The application will automatically find and copy the credential files
        """)
        instructions.setWordWrap(True)
        instructions.setOpenExternalLinks(True)
        layout.addWidget(instructions)
        
        # Note about access
        access_note = QLabel("""
<i>Note: If you can't access the link above, you haven't been granted access to the credentials.
Contact the repository owner to request access.</i>
        """)
        access_note.setWordWrap(True)
        access_note.setStyleSheet("color: #666; font-style: italic; margin: 10px;")
        layout.addWidget(access_note)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        
        self.folder_path_label = QLabel("No folder selected")
        self.folder_path_label.setStyleSheet("border: 1px solid #ccc; padding: 8px; background: #f9f9f9;")
        folder_layout.addWidget(self.folder_path_label)
        
        select_folder_btn = QPushButton("Select Downloaded Folder")
        select_folder_btn.clicked.connect(self.select_credentials_folder)
        folder_layout.addWidget(select_folder_btn)
        
        layout.addLayout(folder_layout)
        
        # Alternative: Direct file selection
        direct_layout = QHBoxLayout()
        direct_layout.addWidget(QLabel("Or select files directly:"))
        
        select_files_btn = QPushButton("Select Downloaded Files")
        select_files_btn.clicked.connect(self.select_downloaded_files)
        direct_layout.addWidget(select_files_btn)
        
        layout.addLayout(direct_layout)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        return widget
        
    def create_manual_tab(self):
        """Create tab for manual file selection"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        instructions = QLabel("""
<b>Select credential files manually:</b><br><br>
You need to select two files:<br>
• Service Account JSON file (for Google Drive access)<br>
• OAuth Client Secret JSON file (for user authentication)
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Service account file
        service_group = QGroupBox("Service Account File")
        service_layout = QVBoxLayout(service_group)
        
        service_info = QLabel("File should be named like: your-project-xxxxx.json")
        service_info.setStyleSheet("color: #666; font-style: italic;")
        service_layout.addWidget(service_info)
        
        service_file_layout = QHBoxLayout()
        self.service_file_label = QLabel("No file selected")
        self.service_file_label.setStyleSheet("border: 1px solid #ccc; padding: 8px; background: #f9f9f9;")
        service_file_layout.addWidget(self.service_file_label)
        
        select_service_btn = QPushButton("Select Service Account File")
        select_service_btn.clicked.connect(self.select_service_account_file)
        service_file_layout.addWidget(select_service_btn)
        
        service_layout.addLayout(service_file_layout)
        layout.addWidget(service_group)
        
        # OAuth client secret file
        oauth_group = QGroupBox("OAuth Client Secret File")
        oauth_layout = QVBoxLayout(oauth_group)
        
        oauth_info = QLabel("File should be named like: client_secret_xxxxx.json")
        oauth_info.setStyleSheet("color: #666; font-style: italic;")
        oauth_layout.addWidget(oauth_info)
        
        oauth_file_layout = QHBoxLayout()
        self.oauth_file_label = QLabel("No file selected")
        self.oauth_file_label.setStyleSheet("border: 1px solid #ccc; padding: 8px; background: #f9f9f9;")
        oauth_file_layout.addWidget(self.oauth_file_label)
        
        select_oauth_btn = QPushButton("Select OAuth Client File")
        select_oauth_btn.clicked.connect(self.select_oauth_client_file)
        oauth_file_layout.addWidget(select_oauth_btn)
        
        oauth_layout.addLayout(oauth_file_layout)
        layout.addWidget(oauth_group)
        
        # Apply button
        apply_btn = QPushButton("Apply Selected Files")
        apply_btn.clicked.connect(self.apply_manual_files)
        layout.addWidget(apply_btn)
        
        # Status
        self.manual_status_label = QLabel("")
        self.manual_status_label.setWordWrap(True)
        layout.addWidget(self.manual_status_label)
        
        layout.addStretch()
        return widget
        
    def create_instructions_tab(self):
        """Create tab with instructions for getting credentials"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Scrollable area for instructions
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        instructions_html = """
<h3>How to Get Google API Credentials</h3>

<h4>Option 1: Contact Repository Owner</h4>
<p>If you're an authorized user, contact the repository owner for access to the private credentials repository.</p>

<h4>Option 2: Create Your Own Credentials</h4>
<p><b>Service Account (for Google Drive):</b></p>
<ol>
<li>Go to <a href="https://console.cloud.google.com">Google Cloud Console</a></li>
<li>Create a new project or select existing project</li>
<li>Enable Google Drive API</li>
<li>Go to "IAM & Admin" → "Service Accounts"</li>
<li>Create a service account</li>
<li>Download the JSON key file</li>
<li>Share your Google Drive folder with the service account email</li>
</ol>

<p><b>OAuth Client Secret (for user authentication):</b></p>
<ol>
<li>In the same Google Cloud project</li>
<li>Go to "APIs & Services" → "Credentials"</li>
<li>Create "OAuth 2.0 Client ID"</li>
<li>Choose "Desktop application"</li>
<li>Download the JSON file</li>
</ol>

<p><b>Important:</b> Make sure both files are from the same Google Cloud project!</p>

<h4>File Naming</h4>
<p>Files should be named:</p>
<ul>
<li><code>your-project-name-xxxxx.json</code> (Service Account)</li>
<li><code>client_secret_xxxxx.json</code> (OAuth Client)</li>
</ul>
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
        
    def select_credentials_folder(self):
        """Select folder containing credential files"""
        folder = QFileDialog.getExistingDirectory(self, "Select Downloads Folder (or folder with credential files)")
        if folder:
            folder_path = Path(folder)
            self.folder_path_label.setText(str(folder_path))
            
            # Look for credential files in the folder
            self.copy_credentials_from_folder(folder_path)
            
    def select_downloaded_files(self):
        """Select downloaded credential files directly"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Downloaded Credential Files", "", "JSON Files (*.json)")
        if files:
            try:
                copied_files = []
                
                for file_path in files:
                    file_name = Path(file_path).name
                    if "water-levels-monitoring" in file_name or len(file_name) > 50:
                        # Likely service account file
                        dest = self.config_dir / file_name
                        shutil.copy2(file_path, dest)
                        copied_files.append(f"Service Account: {file_name}")
                    elif "client_secret" in file_name:
                        # OAuth client file
                        dest = self.config_dir / file_name
                        shutil.copy2(file_path, dest)
                        copied_files.append(f"OAuth Client: {file_name}")
                        
                if copied_files:
                    self.status_label.setText(f"✅ Successfully copied:\n" + "\n".join(copied_files))
                    self.status_label.setStyleSheet("color: green;")
                    
                    QMessageBox.information(self, "Success", 
                                          "Credentials copied successfully!\nRestart the application to use Google Drive features.")
                    self.accept()
                else:
                    self.status_label.setText("❌ No valid credential files found in selection.")
                    self.status_label.setStyleSheet("color: red;")
                    
            except Exception as e:
                self.status_label.setText(f"❌ Error copying files: {str(e)}")
                self.status_label.setStyleSheet("color: red;")
            
    def copy_credentials_from_folder(self, folder_path):
        """Copy credential files from selected folder"""
        try:
            copied_files = []
            
            # Look for service account file
            for file in folder_path.glob("*.json"):
                if "service" in file.name.lower() or len(file.name) > 50:
                    # Likely a service account file (they tend to have long names)
                    dest = self.config_dir / file.name
                    shutil.copy2(file, dest)
                    copied_files.append(f"Service Account: {file.name}")
                    
                elif "client_secret" in file.name.lower():
                    # OAuth client secret file
                    dest = self.config_dir / file.name
                    shutil.copy2(file, dest)
                    copied_files.append(f"OAuth Client: {file.name}")
                    
            if copied_files:
                self.status_label.setText(f"✅ Successfully copied:\n" + "\n".join(copied_files))
                self.status_label.setStyleSheet("color: green;")
                
                # Show success message and close
                QMessageBox.information(self, "Success", 
                                      "Credentials copied successfully!\nRestart the application to use Google Drive features.")
                self.accept()
            else:
                self.status_label.setText("❌ No credential files found in the selected folder.")
                self.status_label.setStyleSheet("color: red;")
                
        except Exception as e:
            self.status_label.setText(f"❌ Error copying files: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            
    def select_service_account_file(self):
        """Select service account JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Service Account JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.service_file_label.setText(file_path)
            self.service_account_file = file_path
            
    def select_oauth_client_file(self):
        """Select OAuth client secret JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select OAuth Client Secret JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.oauth_file_label.setText(file_path)
            self.oauth_client_file = file_path
            
    def apply_manual_files(self):
        """Apply manually selected files"""
        try:
            copied_files = []
            
            if hasattr(self, 'service_account_file'):
                dest = self.config_dir / Path(self.service_account_file).name
                shutil.copy2(self.service_account_file, dest)
                copied_files.append(f"Service Account: {dest.name}")
                
            if hasattr(self, 'oauth_client_file'):
                dest = self.config_dir / Path(self.oauth_client_file).name
                shutil.copy2(self.oauth_client_file, dest)
                copied_files.append(f"OAuth Client: {dest.name}")
                
            if copied_files:
                self.manual_status_label.setText(f"✅ Successfully copied:\n" + "\n".join(copied_files))
                self.manual_status_label.setStyleSheet("color: green;")
                
                QMessageBox.information(self, "Success", 
                                      "Credentials copied successfully!\nRestart the application to use Google Drive features.")
                self.accept()
            else:
                self.manual_status_label.setText("❌ Please select both credential files.")
                self.manual_status_label.setStyleSheet("color: red;")
                
        except Exception as e:
            self.manual_status_label.setText(f"❌ Error copying files: {str(e)}")
            self.manual_status_label.setStyleSheet("color: red;")
            
    def skip_setup(self):
        """Skip credential setup"""
        reply = QMessageBox.question(self, "Skip Setup", 
                                    "Are you sure you want to skip credential setup?\n\n" +
                                    "The application will work but Google Drive features will be disabled.",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.accept()
            
    @staticmethod
    def check_credentials_exist(config_dir=None):
        """Check if credential files exist"""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent.parent / "config"
            
        # Look for service account file
        service_account_files = list(config_dir.glob("*-*.json"))
        service_account_files = [f for f in service_account_files 
                               if "client_secret" not in f.name and "TEMPLATE" not in f.name]
        
        # Look for OAuth client secret file  
        oauth_files = list(config_dir.glob("client_secret_*.json"))
        oauth_files = [f for f in oauth_files if "TEMPLATE" not in f.name]
        
        return len(service_account_files) > 0 and len(oauth_files) > 0