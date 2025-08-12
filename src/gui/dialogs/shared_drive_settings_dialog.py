"""
Shared Drive Settings Dialog
Configure shared drive path for organizational updates
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QMessageBox, QGroupBox,
    QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from pathlib import Path
import logging
from ...config.paths import DefaultPaths

logger = logging.getLogger(__name__)

class SharedDriveSettingsDialog(QDialog):
    """Dialog for configuring shared drive update settings"""
    
    def __init__(self, settings_handler, shared_drive_updater=None, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.shared_drive_updater = shared_drive_updater
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Shared Drive Update Settings")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Organizational Update Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Configure the shared network drive path where your organization's\n"
            "latest application updates are stored."
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(desc_label)
        
        # Shared Drive Path Group
        path_group = QGroupBox("Shared Drive Configuration")
        path_layout = QVBoxLayout(path_group)
        
        # Path input
        path_input_layout = QHBoxLayout()
        path_input_layout.addWidget(QLabel("Shared Drive Path:"))
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(f"e.g., {DefaultPaths.SHARED_DRIVE_BASE}")
        self.path_input.textChanged.connect(self.on_path_changed)
        path_input_layout.addWidget(self.path_input)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_for_path)
        path_input_layout.addWidget(self.browse_button)
        
        path_layout.addLayout(path_input_layout)
        
        # Test connection button
        test_layout = QHBoxLayout()
        self.test_button = QPushButton("🔍 Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)
        
        self.status_label = QLabel("Status: Not tested")
        self.status_label.setStyleSheet("color: #666;")
        test_layout.addWidget(self.status_label)
        test_layout.addStretch()
        
        path_layout.addLayout(test_layout)
        
        layout.addWidget(path_group)
        
        # Options Group
        options_group = QGroupBox("Update Options")
        options_layout = QVBoxLayout(options_group)
        
        self.auto_check_checkbox = QCheckBox("Check for updates on startup")
        self.auto_check_checkbox.setToolTip("Automatically check shared drive for updates when app starts")
        options_layout.addWidget(self.auto_check_checkbox)
        
        self.notifications_checkbox = QCheckBox("Show update notifications")
        self.notifications_checkbox.setToolTip("Show notifications when updates are available")
        options_layout.addWidget(self.notifications_checkbox)
        
        layout.addWidget(options_group)
        
        # Information text
        info_group = QGroupBox("How It Works")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QTextEdit()
        info_text.setMaximumHeight(120)
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "1. Your IT administrator places the latest app version on the shared drive\n"
            "2. The app checks the shared drive for newer versions\n"
            "3. If found, you can update with one click\n"
            "4. The app automatically backs up your current version before updating\n"
            "5. If update fails, your previous version is automatically restored"
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
        """Load current settings"""
        try:
            # Load shared drive path
            shared_path = self.settings_handler.get_setting("shared_drive_path", "")
            self.path_input.setText(shared_path)
            
            # Load options
            auto_check = self.settings_handler.get_setting("shared_drive_auto_check", True)
            self.auto_check_checkbox.setChecked(auto_check)
            
            notifications = self.settings_handler.get_setting("shared_drive_notifications", True)
            self.notifications_checkbox.setChecked(notifications)
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def on_path_changed(self):
        """Handle path input changes"""
        self.status_label.setText("Status: Not tested")
        self.status_label.setStyleSheet("color: #666;")
    
    def browse_for_path(self):
        """Browse for shared drive folder"""
        try:
            path = QFileDialog.getExistingDirectory(
                self,
                "Select Shared Drive Folder",
                self.path_input.text()
            )
            
            if path:
                self.path_input.setText(path)
                
        except Exception as e:
            logger.error(f"Error browsing for path: {e}")
            QMessageBox.warning(self, "Error", f"Error browsing for folder:\n{str(e)}")
    
    def test_connection(self):
        """Test connection to shared drive"""
        try:
            path = self.path_input.text().strip()
            
            if not path:
                self.status_label.setText("Status: Please enter a path first")
                self.status_label.setStyleSheet("color: #ff6600;")
                return
            
            # Test basic path access
            shared_path = Path(path)
            
            if not shared_path.exists():
                self.status_label.setText("Status: ❌ Path does not exist")
                self.status_label.setStyleSheet("color: #cc0000;")
                return
            
            if not shared_path.is_dir():
                self.status_label.setText("Status: ❌ Path is not a directory")
                self.status_label.setStyleSheet("color: #cc0000;")
                return
            
            # Test read access
            try:
                list(shared_path.iterdir())
            except PermissionError:
                self.status_label.setText("Status: ❌ No read permission")
                self.status_label.setStyleSheet("color: #cc0000;")
                return
            
            # Check for version file
            version_file = shared_path / "version.json"
            if not version_file.exists():
                self.status_label.setText("Status: ⚠️ Accessible but no version.json found")
                self.status_label.setStyleSheet("color: #ff6600;")
                return
            
            # Check for src folder
            src_folder = shared_path / "src"
            if not src_folder.exists():
                self.status_label.setText("Status: ⚠️ Accessible but no src folder found")
                self.status_label.setStyleSheet("color: #ff6600;")
                return
            
            self.status_label.setText("Status: ✅ Connection successful!")
            self.status_label.setStyleSheet("color: #007700;")
            
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            self.status_label.setText(f"Status: ❌ Error: {str(e)}")
            self.status_label.setStyleSheet("color: #cc0000;")
    
    def save_settings(self):
        """Save settings and close dialog"""
        try:
            path = self.path_input.text().strip()
            
            # Validate path if provided
            if path:
                if not Path(path).exists():
                    reply = QMessageBox.question(
                        self,
                        "Path Not Found",
                        f"The path '{path}' does not exist or is not accessible.\n\n"
                        "Save anyway? (You can test it later when the shared drive is available)",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return
            
            # Save settings
            self.settings_handler.set_setting("shared_drive_path", path)
            self.settings_handler.set_setting("shared_drive_auto_check", self.auto_check_checkbox.isChecked())
            self.settings_handler.set_setting("shared_drive_notifications", self.notifications_checkbox.isChecked())
            
            # Update the shared drive updater if available
            if self.shared_drive_updater and path:
                self.shared_drive_updater.shared_drive_path = path
                self.shared_drive_updater.shared_version_file = Path(path) / "version.json"
                self.shared_drive_updater.shared_src_folder = Path(path) / "src"
            
            QMessageBox.information(self, "Settings Saved", "Shared drive settings have been saved successfully!")
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{str(e)}")