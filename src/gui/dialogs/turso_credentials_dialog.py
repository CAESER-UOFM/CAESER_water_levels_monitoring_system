import os
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QTextEdit, QFormLayout,
                           QGroupBox, QMessageBox, QTabWidget, QWidget,
                           QComboBox, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

class TursoCredentialsDialog(QDialog):
    """Dialog for configuring Turso database credentials"""
    
    credentials_updated = pyqtSignal()
    
    def __init__(self, settings_handler, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.setWindowTitle("Turso Database Configuration")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Configure Turso Database Credentials")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Information
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(100)
        info_text.setHtml("""
        <p>Turso is a distributed SQLite database service used for syncing optimized 
        versions of project databases to the cloud. This enables fast data access 
        for web and mobile applications.</p>
        <p><b>Supported Projects:</b> CAESER_GENERAL, MEGASITE, SANDY_CREEK</p>
        """)
        layout.addWidget(info_text)
        
        # Tabs for different credential sets
        self.tabs = QTabWidget()
        
        # General credentials tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        self.auth_token_input = QLineEdit()
        self.auth_token_input.setEchoMode(QLineEdit.Password)
        self.auth_token_input.setPlaceholderText("Turso authentication token")
        general_layout.addRow("Auth Token:", self.auth_token_input)
        
        self.tabs.addTab(general_tab, "General Settings")
        
        # Project-specific credentials
        self.project_tabs = {}
        projects = [
            ("CAESER_GENERAL", "caeser-general"),
            ("MEGASITE", "megasite"),
            ("SANDY_CREEK", "sandy-creek")
        ]
        
        for project_name, db_name in projects:
            project_tab = QWidget()
            project_layout = QFormLayout(project_tab)
            
            # Database URL
            url_input = QLineEdit()
            url_input.setPlaceholderText(f"libsql://{db_name}-[org].turso.io")
            setattr(self, f"{project_name.lower()}_url", url_input)
            project_layout.addRow("Database URL:", url_input)
            
            # Access token
            token_input = QLineEdit()
            token_input.setEchoMode(QLineEdit.Password)
            token_input.setPlaceholderText("Database-specific access token")
            setattr(self, f"{project_name.lower()}_token", token_input)
            project_layout.addRow("Access Token:", token_input)
            
            # Test connection button
            test_btn = QPushButton(f"Test {project_name} Connection")
            test_btn.clicked.connect(lambda checked, p=project_name: self.test_connection(p))
            project_layout.addRow("", test_btn)
            
            self.tabs.addTab(project_tab, project_name.replace("_", " ").title())
            self.project_tabs[project_name] = project_tab
            
        layout.addWidget(self.tabs)
        
        # Auto-sync settings
        sync_group = QGroupBox("Auto-Sync Settings")
        sync_layout = QFormLayout()
        
        self.auto_sync_enabled = QComboBox()
        self.auto_sync_enabled.addItems(["Disabled", "Enabled"])
        sync_layout.addRow("Turso Auto-Sync:", self.auto_sync_enabled)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import Settings")
        import_btn.clicked.connect(self.import_settings)
        button_layout.addWidget(import_btn)
        
        export_btn = QPushButton("Export Settings")
        export_btn.clicked.connect(self.export_settings)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def load_settings(self):
        """Load existing Turso settings"""
        try:
            # Load general auth token
            auth_token = self.settings_handler.get_setting("turso_auth_token", "")
            self.auth_token_input.setText(auth_token)
            
            # Load project-specific settings
            projects = ["CAESER_GENERAL", "MEGASITE", "SANDY_CREEK"]
            for project in projects:
                url_key = f"turso_{project.lower()}_url"
                token_key = f"turso_{project.lower()}_token"
                
                url = self.settings_handler.get_setting(url_key, "")
                token = self.settings_handler.get_setting(token_key, "")
                
                url_input = getattr(self, f"{project.lower()}_url")
                token_input = getattr(self, f"{project.lower()}_token")
                
                url_input.setText(url)
                token_input.setText(token)
            
            # Load auto-sync setting
            auto_sync = self.settings_handler.get_setting("turso_auto_sync_enabled", False)
            self.auto_sync_enabled.setCurrentIndex(1 if auto_sync else 0)
            
        except Exception as e:
            logger.error(f"Error loading Turso settings: {e}")
            
    def save_settings(self):
        """Save Turso settings"""
        try:
            # Save general auth token
            self.settings_handler.set_setting("turso_auth_token", 
                                            self.auth_token_input.text().strip())
            
            # Save project-specific settings
            projects = ["CAESER_GENERAL", "MEGASITE", "SANDY_CREEK"]
            for project in projects:
                url_input = getattr(self, f"{project.lower()}_url")
                token_input = getattr(self, f"{project.lower()}_token")
                
                url_key = f"turso_{project.lower()}_url"
                token_key = f"turso_{project.lower()}_token"
                
                self.settings_handler.set_setting(url_key, url_input.text().strip())
                self.settings_handler.set_setting(token_key, token_input.text().strip())
            
            # Save auto-sync setting
            auto_sync = self.auto_sync_enabled.currentIndex() == 1
            self.settings_handler.set_setting("turso_auto_sync_enabled", auto_sync)
            
            # Save settings to file
            self.settings_handler.save_settings()
            
            # Emit signal
            self.credentials_updated.emit()
            
            QMessageBox.information(self, "Success", 
                                  "Turso credentials saved successfully!")
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving Turso settings: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to save settings: {str(e)}")
            
    def test_connection(self, project_name):
        """Test connection to a specific Turso database"""
        try:
            url_input = getattr(self, f"{project_name.lower()}_url")
            token_input = getattr(self, f"{project_name.lower()}_token")
            
            url = url_input.text().strip()
            token = token_input.text().strip()
            
            if not url or not token:
                QMessageBox.warning(self, "Missing Credentials",
                                  "Please enter both URL and token for this project.")
                return
                
            # Import turso handler for testing
            from ..handlers.turso_handler import TursoHandler
            
            # Test the connection
            handler = TursoHandler(None, None)  # Temporary instance
            success, message = handler.test_connection(url, token)
            
            if success:
                QMessageBox.information(self, "Connection Successful",
                                      f"Successfully connected to {project_name} database!")
            else:
                QMessageBox.warning(self, "Connection Failed",
                                  f"Failed to connect to {project_name}:\n{message}")
                
        except ImportError:
            # If handler not implemented yet
            QMessageBox.information(self, "Test Connection",
                                  f"Would test connection to {project_name} database.\n"
                                  f"URL: {url}\n"
                                  f"Token: {'*' * 10}...")
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            QMessageBox.critical(self, "Error",
                               f"Failed to test connection: {str(e)}")
                               
    def import_settings(self):
        """Import Turso settings from JSON file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Turso Settings",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Check if it has the expected format
            if 'turso_settings' in data:
                settings = data['turso_settings']
            else:
                # Assume the whole file is settings
                settings = data
                
            # Apply settings to UI
            if 'turso_auth_token' in settings:
                self.auth_token_input.setText(settings['turso_auth_token'])
                
            # Apply project-specific settings
            projects = ['caeser_general', 'megasite', 'sandy_creek']
            for project in projects:
                url_key = f'turso_{project}_url'
                token_key = f'turso_{project}_token'
                
                if url_key in settings:
                    url_input = getattr(self, f"{project}_url")
                    url_input.setText(settings[url_key])
                    
                if token_key in settings:
                    token_input = getattr(self, f"{project}_token")
                    token_input.setText(settings[token_key])
                    
            # Apply auto-sync setting
            if 'turso_auto_sync_enabled' in settings:
                self.auto_sync_enabled.setCurrentIndex(1 if settings['turso_auto_sync_enabled'] else 0)
                
            QMessageBox.information(self, "Import Successful",
                                  "Turso settings imported successfully!\n"
                                  "Please review the settings and click Save.")
                                  
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            QMessageBox.critical(self, "Import Error",
                               f"Failed to import settings: {str(e)}")
                               
    def export_settings(self):
        """Export current Turso settings to JSON file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Turso Settings",
                "turso_settings_export.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
                
            # Collect current settings
            settings = {
                'turso_auth_token': self.auth_token_input.text().strip()
            }
            
            # Collect project-specific settings
            projects = ['caeser_general', 'megasite', 'sandy_creek']
            for project in projects:
                url_input = getattr(self, f"{project}_url")
                token_input = getattr(self, f"{project}_token")
                
                url_key = f'turso_{project}_url'
                token_key = f'turso_{project}_token'
                
                url_value = url_input.text().strip()
                token_value = token_input.text().strip()
                
                if url_value:
                    settings[url_key] = url_value
                if token_value:
                    settings[token_key] = token_value
                    
            # Add auto-sync setting
            settings['turso_auto_sync_enabled'] = self.auto_sync_enabled.currentIndex() == 1
            
            # Create export data
            export_data = {
                'turso_settings': settings,
                'exported_at': os.environ.get('USERNAME', os.environ.get('USER', 'unknown')),
                'instructions': [
                    "To import these settings:",
                    "1. Open CAESER Water Levels Monitoring app",
                    "2. Go to Settings → Turso Database Settings",
                    "3. Click 'Import Settings' and select this file"
                ]
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            QMessageBox.information(self, "Export Successful",
                                  f"Turso settings exported to:\n{file_path}")
                                  
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            QMessageBox.critical(self, "Export Error",
                               f"Failed to export settings: {str(e)}")
                               
    def install_turso_cli(self):
        """Help user install Turso CLI"""
        try:
            # Check if already installed
            import subprocess
            result = subprocess.run(['turso', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                QMessageBox.information(self, "Already Installed",
                                      f"Turso CLI is already installed!\n\nVersion: {result.stdout.strip()}")
                return
        except:
            pass
            
        # Show installation dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Install Turso CLI")
        msg.setText("Turso CLI enables fast database uploads (minutes instead of hours).\n\n"
                   "To install, you need to run one command in Terminal.")
        msg.setInformativeText("Click 'Open Terminal' to start the installation.")
        
        # Add buttons
        terminal_btn = msg.addButton("Open Terminal", QMessageBox.ActionRole)
        copy_btn = msg.addButton("Copy Command", QMessageBox.ActionRole)
        cancel_btn = msg.addButton(QMessageBox.Cancel)
        
        msg.exec_()
        
        if msg.clickedButton() == terminal_btn:
            # Open Terminal with the command ready
            import subprocess
            apple_script = '''
            tell application "Terminal"
                activate
                do script "echo 'Installing Turso CLI...' && curl -sSfL https://get.tur.so/install.sh | bash && echo && echo 'Installation complete! Now run: turso auth login' && echo"
            end tell
            '''
            subprocess.run(['osascript', '-e', apple_script])
            
            QMessageBox.information(self, "Terminal Opened",
                                  "Terminal is now open with the installation command.\n\n"
                                  "After installation completes, run:\n"
                                  "turso auth login\n\n"
                                  "Then close and reopen this dialog.")
                                  
        elif msg.clickedButton() == copy_btn:
            # Copy installation command to clipboard
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText("curl -sSfL https://get.tur.so/install.sh | bash")
            
            QMessageBox.information(self, "Command Copied",
                                  "Installation command copied to clipboard!\n\n"
                                  "1. Open Terminal (in Applications > Utilities)\n"
                                  "2. Paste the command (Cmd+V)\n"
                                  "3. Press Enter\n"
                                  "4. After installation, run: turso auth login")