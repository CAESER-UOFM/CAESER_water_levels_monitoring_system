"""
Google Drive Settings Dialog (Field Data)
Configure service account authentication and multiple field laptop folders
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QTextEdit, QScrollArea,
    QWidget, QGridLayout, QFrame, QFileDialog, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging
import os
from pathlib import Path

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
        layout.setContentsMargins(8, 8, 8, 8)  # Better margins for Windows
        layout.setSpacing(8)
        
        # Laptop name input with label
        name_label = QLabel("Name:")
        name_label.setMinimumWidth(50)
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit(self.laptop_name)
        self.name_input.setPlaceholderText("e.g., Laptop_1")
        self.name_input.setMinimumWidth(80)
        self.name_input.setMaximumWidth(120)  # Increased for better visibility
        layout.addWidget(self.name_input)
        
        # Folder ID input with label  
        folder_label = QLabel("Folder ID:")
        folder_label.setMinimumWidth(60)
        layout.addWidget(folder_label)
        
        self.folder_input = QLineEdit(self.folder_id)
        self.folder_input.setPlaceholderText("Google Drive Folder ID")
        self.folder_input.setMinimumWidth(200)  # Ensure adequate space for folder IDs
        layout.addWidget(self.folder_input)
        
        # Test button
        self.test_button = QPushButton("🔍 Test")
        self.test_button.clicked.connect(self.test_folder_access)
        self.test_button.setMinimumWidth(70)
        self.test_button.setMaximumWidth(80)
        layout.addWidget(self.test_button)
        
        # Status label
        self.status_label = QLabel("Not tested")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        self.status_label.setMinimumWidth(80)
        self.status_label.setMaximumWidth(120)
        self.status_label.setWordWrap(True)  # Allow text wrapping on small screens
        layout.addWidget(self.status_label)
        
        # Remove button
        self.remove_button = QPushButton("❌")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_button.setMinimumWidth(35)
        self.remove_button.setMaximumWidth(40)
        self.remove_button.setToolTip("Remove this field laptop")
        layout.addWidget(self.remove_button)
        
        # Set minimum height for the widget
        self.setMinimumHeight(40)
    
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


class GoogleDriveFieldDataDialog(QDialog):
    """Dialog for configuring Google Drive service account and field laptop folders"""
    
    def __init__(self, settings_handler, google_service=None, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.google_service = google_service
        self.laptop_widgets = []
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Set up the dialog UI with tabs for service account and field laptops"""
        self.setWindowTitle("Google Drive Settings (Field Data)")
        self.setMinimumSize(900, 700)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Google Drive Field Data Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Configure Google Drive service account authentication and field laptop folders.\n"
            "Downloads XLE files from multiple field laptops and organizes them in SMOO."
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(desc_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Setup tabs
        self.setup_service_account_tab()
        self.setup_field_laptops_tab()
        
        # Buttons
        self.setup_buttons(layout)
    
    def setup_service_account_tab(self):
        """Setup the Service Account configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Instructions
        instructions_group = QGroupBox("Service Account Setup")
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions = QLabel(
            "Service Account authentication for XLE file synchronization:\n\n"
            "• Downloads XLE files from Google Drive SOLINST folders\n"
            "• Organizes files in SMOO FIELD_DATA_CONSOLIDATED by date\n"
            "• No OAuth required - uses service account key\n"
            "• Supports multiple field laptop folders simultaneously\n\n"
            "Select your service account JSON key file:"
        )
        instructions.setWordWrap(True)
        instructions_layout.addWidget(instructions)
        layout.addWidget(instructions_group)
        
        # File selection group
        file_group = QGroupBox("Service Account Key File")
        file_layout = QVBoxLayout(file_group)
        
        # File path input
        file_input_layout = QHBoxLayout()
        self.service_file_edit = QLineEdit()
        self.service_file_edit.setPlaceholderText("Path to service account JSON file...")
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_service_account_file)
        browse_btn.setMaximumWidth(80)
        
        file_input_layout.addWidget(QLabel("File Path:"))
        file_input_layout.addWidget(self.service_file_edit)
        file_input_layout.addWidget(browse_btn)
        file_layout.addLayout(file_input_layout)
        
        # Test button
        test_layout = QHBoxLayout()
        self.test_service_btn = QPushButton("🔍 Test Connection")
        self.test_service_btn.clicked.connect(self.test_service_account)
        self.test_service_btn.setStyleSheet("""
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
        test_layout.addWidget(self.test_service_btn)
        test_layout.addStretch()
        file_layout.addLayout(test_layout)
        
        layout.addWidget(file_group)
        
        # Status area
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout(status_group)
        
        self.service_status_area = QTextEdit()
        self.service_status_area.setMaximumHeight(120)
        self.service_status_area.setPlaceholderText("Connection status will appear here...")
        self.service_status_area.setReadOnly(True)
        status_layout.addWidget(self.service_status_area)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "🔐 Service Account")
    
    def setup_field_laptops_tab(self):
        """Setup the Field Laptops configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)  # Add spacing for better Windows rendering
        
        # Field Laptops Group
        laptops_group = QGroupBox("Field Laptop Folders")
        laptops_layout = QVBoxLayout(laptops_group)
        laptops_layout.setSpacing(8)
        
        # Scroll area for laptop widgets
        self.scroll_area = QScrollArea()
        self.scroll_area.setFrameStyle(QFrame.StyledPanel)  # Better frame visibility on Windows
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(5)
        self.scroll_layout.addStretch()  # Push content to top
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(250)  # Increased height for better visibility
        
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
        info_text.setMaximumHeight(100)
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
        
        self.tab_widget.addTab(tab, "📁 Field Laptops")
    
    def setup_buttons(self, layout):
        """Setup dialog buttons"""
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
    
    # Service Account Methods
    def browse_service_account_file(self):
        """Browse for service account JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Service Account JSON File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.service_file_edit.setText(file_path)
    
    def test_service_account(self):
        """Test service account connection"""
        try:
            file_path = self.service_file_edit.text().strip()
            if not file_path:
                self.service_status_area.setText("❌ Please select a service account file first")
                return
            
            if not os.path.exists(file_path):
                self.service_status_area.setText(f"❌ File not found: {file_path}")
                return
            
            self.service_status_area.setText("🔄 Testing service account connection...")
            
            # Test the service account
            from ...handlers.google_service_account import GoogleServiceAccountHandler
            
            # Temporarily save the file path to test it
            original_path = self.settings_handler.get_setting("service_account_key_file", "")
            self.settings_handler.set_setting("service_account_key_file", file_path)
            
            try:
                test_service = GoogleServiceAccountHandler(self.settings_handler)
                if test_service.authenticate():
                    # Test basic drive access
                    projects = test_service.service.files().list(
                        q="mimeType='application/vnd.google-apps.folder'",
                        pageSize=1
                    ).execute()
                    
                    self.service_status_area.setText(
                        "✅ Service account connection successful!\n"
                        f"✅ File: {os.path.basename(file_path)}\n"
                        f"✅ Google Drive API access confirmed\n"
                        f"✅ Ready to scan field laptop folders"
                    )
                    self.google_service = test_service  # Update the service instance
                else:
                    self.service_status_area.setText("❌ Authentication failed - check your service account file")
            except Exception as auth_error:
                self.service_status_area.setText(f"❌ Authentication error: {str(auth_error)}")
            finally:
                # Restore original path if test failed
                if not hasattr(self, 'google_service') or not self.google_service:
                    self.settings_handler.set_setting("service_account_key_file", original_path)
                
        except Exception as e:
            logger.error(f"Error testing service account: {e}")
            self.service_status_area.setText(f"❌ Error testing connection: {str(e)}")
    
    def load_settings(self):
        """Load current service account and field laptop settings"""
        try:
            # Load service account settings
            service_account_path = self.settings_handler.get_setting("service_account_key_file", "")
            self.service_file_edit.setText(service_account_path)
            
            if service_account_path and os.path.exists(service_account_path):
                self.service_status_area.setText(
                    f"✅ Configured: {os.path.basename(service_account_path)}\n"
                    "Click 'Test Connection' to verify access"
                )
            else:
                self.service_status_area.setText("No service account configured")
            
            # Load existing laptop configurations with default folder IDs
            laptop_configs = [
                ("Laptop_1", "google_drive_laptop_1_folder_id", "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"),
                ("Laptop_2", "google_drive_laptop_2_folder_id", "1JaBHPHdImlxkVxB24eOW8Z83zPK2unSz"), 
                ("Laptop_3", "google_drive_laptop_3_folder_id", "1jnuWTCWdW_HTTnoxr2zOge_gkvEGd19T"),
                ("Laptop_4", "google_drive_laptop_4_folder_id", ""),
                ("Laptop_5", "google_drive_laptop_5_folder_id", "")
            ]
            
            # Always load the first 3 laptops with default folder IDs pre-populated
            for i, (laptop_name, setting_key, default_folder_id) in enumerate(laptop_configs[:3]):  # Only first 3
                folder_id = self.settings_handler.get_setting(setting_key, default_folder_id)
                self.add_laptop(laptop_name, folder_id)
            
            # Load additional laptops (4+) only if they have configured folder IDs
            for laptop_name, setting_key, default_folder_id in laptop_configs[3:]:  # Laptops 4+
                folder_id = self.settings_handler.get_setting(setting_key, default_folder_id)
                if folder_id:  # Only add if configured
                    self.add_laptop(laptop_name, folder_id)
            
            logger.info(f"Loaded {len(self.laptop_widgets)} field laptop configurations")
                
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
        """Save service account and field laptop settings"""
        logger.info("🔧 SAVE_DEBUG: Starting save_settings method...")

        try:
            # Validate and save service account settings
            service_account_path = self.service_file_edit.text().strip()
            logger.info(f"🔧 SAVE_DEBUG: Service account path: '{service_account_path}'")

            if service_account_path:
                if not os.path.exists(service_account_path):
                    reply = QMessageBox.question(
                        self,
                        "Service Account File Not Found",
                        f"The service account file '{service_account_path}' does not exist.\n\n"
                        "Save anyway? (You can update it later when the file is available)",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return
                
                # Save service account path
                self.settings_handler.set_setting("service_account_key_file", service_account_path)
                logger.info(f"Saved service account path: {service_account_path}")
            
            # Validate all laptop configurations
            logger.info(f"🔧 SAVE_DEBUG: Found {len(self.laptop_widgets)} laptop widgets to validate")
            valid_laptops = []

            for i, laptop_widget in enumerate(self.laptop_widgets):
                config = laptop_widget.get_laptop_config()
                logger.info(f"🔧 SAVE_DEBUG: Laptop {i+1} config: name='{config['name']}', folder_id='{config['folder_id']}'")

                if config['name'] and config['folder_id']:
                    valid_laptops.append(config)
                    logger.info(f"🔧 SAVE_DEBUG: ✅ Laptop {i+1} ({config['name']}) is valid")
                elif config['name'] or config['folder_id']:
                    # Partial configuration
                    logger.warning(f"🔧 SAVE_DEBUG: ❌ Laptop {i+1} has incomplete config")
                    QMessageBox.warning(
                        self,
                        "Incomplete Configuration",
                        f"Laptop '{config['name']}' has incomplete configuration.\n"
                        "Please provide both name and folder ID, or remove this entry."
                    )
                    return
                else:
                    logger.info(f"🔧 SAVE_DEBUG: ⏭️ Laptop {i+1} is empty, skipping")
            
            logger.info(f"🔧 SAVE_DEBUG: Found {len(valid_laptops)} valid laptop configurations")

            if not valid_laptops:
                logger.warning("🔧 SAVE_DEBUG: ⚠️ No valid laptops found, asking user...")
                reply = QMessageBox.question(
                    self,
                    "No Laptops Configured",
                    "No field laptops are configured. This will disable multi-folder scanning.\n\n"
                    "Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    logger.info("🔧 SAVE_DEBUG: User chose not to continue without laptops")
                    return
                logger.info("🔧 SAVE_DEBUG: User chose to continue without laptops")
            
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
            logger.info("🔧 SAVE_DEBUG: Clearing existing laptop settings (1-10)...")
            for i in range(1, 10):  # Clear up to 10 possible laptops
                setting_key = f"google_drive_laptop_{i}_folder_id"
                self.settings_handler.set_setting(setting_key, "")
                logger.debug(f"🔧 SAVE_DEBUG: Cleared {setting_key}")

            # Save new configurations
            logger.info(f"🔧 SAVE_DEBUG: Saving {len(valid_laptops)} new laptop configurations...")
            for i, laptop in enumerate(valid_laptops, 1):
                setting_key = f"google_drive_laptop_{i}_folder_id"
                folder_id = laptop['folder_id']

                logger.info(f"🔧 SAVE_DEBUG: About to save {laptop['name']} -> {setting_key}: {folder_id}")
                self.settings_handler.set_setting(setting_key, folder_id)

                # Verify it was saved
                saved_value = self.settings_handler.get_setting(setting_key, "VERIFICATION_FAILED")
                if saved_value == folder_id:
                    logger.info(f"🔧 SAVE_DEBUG: ✅ Successfully saved {laptop['name']} -> {setting_key}: {folder_id}")
                else:
                    logger.error(f"🔧 SAVE_DEBUG: ❌ SAVE VERIFICATION FAILED for {setting_key}!")
                    logger.error(f"🔧 SAVE_DEBUG: Expected: '{folder_id}', Got: '{saved_value}'")

            logger.info("🔧 SAVE_DEBUG: All laptop settings saved, showing success dialog...")

            # Success message
            service_msg = f"✅ Service Account: {'Configured' if service_account_path else 'Not configured'}"
            laptops_msg = f"✅ Field Laptops: {len(valid_laptops)} configured"

            QMessageBox.information(
                self,
                "Settings Saved",
                f"Google Drive field data settings saved successfully!\n\n"
                f"{service_msg}\n"
                f"{laptops_msg}"
            )

            logger.info("🔧 SAVE_DEBUG: Success dialog shown, save_settings method complete")
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{str(e)}")


# For backward compatibility, create an alias
FieldDataSettingsDialog = GoogleDriveFieldDataDialog