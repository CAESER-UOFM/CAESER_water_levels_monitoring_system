# src/gui/main_window.py

import sys
import os
import shutil
import subprocess  # Add this import for the subprocess module
from pathlib import Path
import pandas as pd
import logging
import matplotlib
from PyQt5.QtGui import QIcon, QResizeEvent, QMoveEvent, QScreen
from PyQt5.QtWidgets import (
    QAction, QDialog, QProgressDialog, QMainWindow, QInputDialog, QTabWidget, 
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, 
    QPushButton, QFileDialog, QMessageBox, QSizePolicy, QMenu,
    QFrame  # Added QFrame to the imports
)
from PyQt5.QtCore import QTimer, Qt, QUrl, QEvent
from PyQt5.QtWidgets import QApplication
import json
from googleapiclient.http import MediaIoBaseDownload
from .handlers.auto_update_handler import AutoUpdateHandler
# Configure matplotlib once at startup
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['font.size'] = 10

from .tabs.database_tab import DatabaseTab
from .tabs.barologger_tab import BarologgerTab
from .tabs.water_level_tab import WaterLevelTab
from .tabs.water_level_runs_tab import WaterLevelRunsTab
from ..database.manager import DatabaseManager
from .handlers.settings_handler import SettingsHandler
from .dialogs.google_drive_settings_dialog import GoogleDriveSettingsDialog
from .dialogs.monet_settings_dialog import MonetSettingsDialog  # Import the new dialog
from .handlers.google_drive_monitor import GoogleDriveMonitor
from .handlers.google_drive_db_handler import GoogleDriveDatabaseHandler
from .handlers.google_drive_data_handler import GoogleDriveDataHandler
from .handlers.google_drive_service import GoogleDriveService
from .handlers.user_auth_service import UserAuthService
from .dialogs.login_dialog import LoginDialog
from .dialogs.user_management_dialog import UserManagementDialog
from .handlers.progress_dialog_handler import progress_dialog
from .handlers.style_handler import StyleHandler  # Import the style handler

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window with tab-based interface for water level monitoring."""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize settings handler
        self.settings_handler = SettingsHandler()
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        self.db_manager.database_changed.connect(self._on_database_changed)
        self.db_manager.database_synced.connect(self._handle_database_synced)
        
        # Set the settings handler in the database manager
        self.db_manager.set_settings_handler(self.settings_handler)
        
        # Connect to the database_modified signal if it exists
        if hasattr(self.db_manager, 'database_modified'):
            self.db_manager.database_modified.connect(self.mark_database_modified)
        
        # Initialize Google Drive service
        self.drive_service = GoogleDriveService.get_instance(self.settings_handler)
        
        # Initialize Google Drive database handler (will be set after authentication)
        self.drive_db_handler = None
        
        # Initialize Google Drive data handler (will be set after authentication)
        self.drive_data_handler = None
        
        # Initialize user authentication service
        self.user_auth_service = UserAuthService.get_instance(self.drive_service, self.settings_handler)
        
        # Flag to track database loading operations
        self._loading_databases = False
        
        # Flag to track initialization phase
        self._initialization_phase = True
        
        # Track the current screen to detect changes
        self.current_screen = None
        
        # Initialize Google Drive monitor (will be set after authentication)
        self.drive_monitor = None
        
        # Initialize the auto update handler (will be fully configured after tabs are created)
        self.auto_update_handler = None
        
        # Apply application-wide styling
        self.apply_application_styling()
        
        # Set up UI
        self.setup_ui()
        
        # Center window on screen
        self.center_window()
        
        # Store initial screen for change detection
        self.current_screen = self.screen()
        self.current_dpi_factor = self.current_screen.devicePixelRatio()
        
        # Progress dialog will be created after successful login
        self.progress_dialog = None
        
        # Show login dialog
        if not self.show_login_dialog():
            # Exit if login fails
            sys.exit(0)
            
        # Create and show progress dialog after successful login
        self.progress_dialog = QProgressDialog("Initializing application...", None, 0, 100, self)
        self.progress_dialog.setWindowTitle("Loading")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(500)  # Show after 500ms
        self.progress_dialog.setValue(0)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None)  # No cancel button
        # Set fixed size to prevent random expansion
        self.progress_dialog.setFixedSize(400, 100)
        # Ensure consistent styling
        self.progress_dialog.setStyleSheet("QProgressDialog { background-color: #f0f0f0; }")
        self.progress_dialog.show()
        
        # Initialize Google Drive monitor (will be set after authentication)
        self.drive_monitor = None
        
        # Log successful initialization
        self.logger.info("Main window initialized successfully")
        
        # Remove the Google Drive authentication on startup
        # if not self.user_auth_service.is_guest:
        #     self.progress_dialog.setValue(20)
        #     self.progress_dialog.setLabelText("Authenticating with Google Drive...")
        #     # Pass force=False to respect the environment variable
        #     QTimer.singleShot(100, lambda: self.authenticate_google_drive(force=False))
        
        self.progress_dialog.setValue(40)
        self.progress_dialog.setLabelText("Setting up application menu...")
        
        # Schedule the progress dialog to close and load database
        QTimer.singleShot(500, self._finish_initialization)
    
    def show_login_dialog(self):
        """Show the login dialog and handle authentication"""
        login_dialog = LoginDialog(self)
        
        # Set login mode to always require authentication
        login_dialog.set_force_login(True)
        
        # Show the dialog
        result = login_dialog.exec_()
        
        if result == QDialog.Accepted:
            # For compatibility with existing code, set all users as "not guest"
            # This ensures all tabs will be available regardless of login type
            self.user_auth_service.is_guest = False
            
            # Login was successful
            return True
        else:
            # Dialog was rejected (Exit button)
            return False
    
    def handle_guest_login(self):
        """Handle guest login request"""
        # Set flag but don't differentiate privileges anymore
        success, message = self.user_auth_service.login_as_guest()
        # Set is_guest to False to ensure all features are available
        if success:
            self.user_auth_service.is_guest = False
        return success
    
    def handle_drive_login(self):
        """Handle Google Drive login request"""
        # Initialize user authentication service
        if not self.user_auth_service.initialize():
            QMessageBox.critical(self, "Error", "Failed to initialize user authentication service")
            return False
        
        # Check if client secret file is set and exists
        client_secret_path = self.settings_handler.get_setting("google_drive_secret_path", "")
        
        # If the client secret path is not set or the file doesn't exist, try to find it in the config directory
        if not client_secret_path or not os.path.exists(client_secret_path):
            logger.warning("Client secret file not found at specified path, looking for default")
            config_dir = Path.cwd() / "config"
            if config_dir.exists():
                # Look for client_secret*.json files
                secret_files = list(config_dir.glob("client_secret*.json"))
                if secret_files:
                    client_secret_path = str(secret_files[0])
                    logger.info(f"Using default client secret file: {client_secret_path}")
                    # Update the setting for future use
                    self.settings_handler.set_setting("google_drive_secret_path", client_secret_path)
        
        # If we still don't have a valid client secret file, prompt the user
        if not client_secret_path or not os.path.exists(client_secret_path):
            # First-time setup - prompt user to configure Google Drive
            reply = QMessageBox.question(
                self,
                "Google Drive Setup Required",
                "The client secret file for Google Drive authentication was not found.\n\n"
                "You need to set up Google Drive integration to use this application fully.\n\n"
                "Would you like to configure Google Drive settings now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Open Google Drive settings dialog
                self.open_google_drive_settings()
                
                # Check if settings were configured
                client_secret_path = self.settings_handler.get_setting("google_drive_secret_path", "")
                if not client_secret_path or not os.path.exists(client_secret_path):
                    # Still not configured, continue as guest
                    QMessageBox.information(
                        self,
                        "Guest Mode",
                        "Google Drive is not configured. You will continue in guest mode with limited functionality."
                    )
                    return self.handle_guest_login()
            else:
                # User chose not to configure, continue as guest
                QMessageBox.information(
                    self,
                    "Guest Mode",
                    "You will continue in guest mode with limited functionality."
                )
                return self.handle_guest_login()
        
        # Authenticate with Google Drive
        if not self.authenticate_google_drive():
            reply = QMessageBox.question(
                self,
                "Authentication Error",
                "Failed to authenticate with Google Drive. This may be due to network issues or invalid credentials.\n\n"
                "Would you like to continue in guest mode with limited functionality?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                return self.handle_guest_login()
            else:
                return False
        
        # Successfully authenticated with Google Drive, now log in as admin
        success, message = self.user_auth_service.login("admin", "admin")
        
        if success:
            # Explicitly set is_guest to False to ensure all features are available
            self.user_auth_service.is_guest = False
            QMessageBox.information(self, "Login Successful", 
                                  "Successfully connected to CAESER Google Drive. You now have full access to the application.")
            return True
        else:
            # This should not happen if the default admin user exists
            QMessageBox.warning(self, "Login Error", 
                              "Failed to log in as administrator. " + message)
            
            # Try to continue as guest
            reply = QMessageBox.question(
                self,
                "Continue as Guest?",
                "Would you like to continue in guest mode with limited functionality?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                return self.handle_guest_login()
            else:
                return False
    
    def authenticate_google_drive(self, force=False):
        """Authenticate with Google Drive and set up database handler"""
        try:
            # Authenticate with Google Drive (pass the force parameter to override environment variable)
            if self.drive_service.authenticate(force=force):
                # Get folder ID from settings
                folder_id = self.settings_handler.get_setting("google_drive_folder_id", "")
                if not folder_id:
                    logger.warning("Google Drive folder ID not set, using default")
                    folder_id = "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"  # Default CAESER folder ID
                    self.settings_handler.set_setting("google_drive_folder_id", folder_id)
                
                # Initialize Google Drive database handler
                self.drive_db_handler = GoogleDriveDatabaseHandler(self.settings_handler)
                if self.drive_db_handler.authenticate():
                    logger.info("Successfully authenticated with Google Drive")
                    
                    # Initialize Google Drive data handler
                    self.drive_data_handler = GoogleDriveDataHandler(self.settings_handler)
                    self.drive_data_handler.authenticate()
                    
                    # Download data folders
                    success = self.drive_data_handler.download_data_folder()
                    if not success:
                        logger.warning("Failed to download data folder from Google Drive, but continuing with authentication")
                    
                    # Set up Google Drive monitor with the XLE files folder ID
                    xle_folder_id = self.settings_handler.get_setting("google_drive_xle_folder_id", "")
                    if not xle_folder_id:
                        logger.warning("Google Drive XLE folder ID not set, using default")
                        xle_folder_id = "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"  # Default XLE files folder ID
                        self.settings_handler.set_setting("google_drive_xle_folder_id", xle_folder_id)
                    
                    self.drive_monitor = GoogleDriveMonitor(xle_folder_id, self.settings_handler)
                    self.drive_monitor.authenticate()
                    
                    # Initialize folders and check for new files
                    self.drive_monitor.initialize_folders()
                    self.drive_monitor.check_for_new_files()
                    
                    # Set Google Drive handler for database manager
                    self.db_manager.set_google_drive_handler(self.drive_db_handler)
                    
                    # Update water level runs tab if it exists
                    if hasattr(self, '_tabs') and 'water_level_runs' in self._tabs:
                        runs_tab = self._tabs['water_level_runs']
                        if hasattr(runs_tab, 'update_drive_state'):
                            runs_tab.update_drive_state(True)
                    
                    # Update barologger tab if it exists
                    if hasattr(self, '_tabs') and 'barologger' in self._tabs:
                        barologger_tab = self._tabs['barologger']
                        if hasattr(barologger_tab, 'update_drive_state'):
                            barologger_tab.update_drive_state(True)
                    
                    # Update water level tab if it exists
                    if hasattr(self, '_tabs') and 'water_level' in self._tabs:
                        water_level_tab = self._tabs['water_level']
                        if hasattr(water_level_tab, 'update_drive_state'):
                            water_level_tab.update_drive_state(True)
                    
                    return True
                else:
                    logger.error("Failed to authenticate Google Drive database handler")
            else:
                logger.error("Failed to authenticate with Google Drive")
                
            return False
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive: {e}")
            return False
    
    def apply_application_styling(self):
        """Apply consistent styling to the application."""
        # Apply the common stylesheet to this window
        self.setStyleSheet(StyleHandler.get_common_stylesheet())
        
        # Also set application-wide palette and style properties
        app = QApplication.instance()
        if app:
            app.setStyleSheet(StyleHandler.get_common_stylesheet())
    
    def setup_ui(self):
        """Set up the main window UI"""
        # Set window properties
        self.setWindowTitle("Water Level Monitoring System")
        
        # Try webp first, fall back to ico if needed
        icon_path = Path('src/gui/icons/app_icon.webp')
        if not icon_path.exists():
            icon_path = Path('src/gui/icons/app_icon.ico')
        
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.resize(1200, 800)
        self.setMinimumSize(1000, 800)  # Set minimum size
        
        # Initialize tab dictionary
        self._tabs = {}
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create header with application title
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title_label = QLabel("Water Level Monitoring System")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #3070B0;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        main_layout.addWidget(header_widget)
        
        # Add a line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #CCDDEE;")
        main_layout.addWidget(line)
        
        # Create database selection area
        db_layout = QHBoxLayout()
        db_layout.setContentsMargins(0, 0, 0, 0)  # Reduce margins to keep elements closer
        db_layout.setSpacing(10)  # Reduce spacing between widgets

        # Add spacer to push elements to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        db_layout.addWidget(spacer)

        # Add database label with right alignment
        db_label = QLabel("Database:")
        db_label.setStyleSheet("font-weight: bold;")
        db_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        db_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        db_layout.addWidget(db_label)

        # Configure combobox with smaller maximum width
        self.db_combo = QComboBox()
        self.db_combo.setMinimumWidth(250)
        self.db_combo.setMaximumWidth(350)  # Reduced maximum width
        self.db_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.db_combo.setPlaceholderText("Select a database")  # Add placeholder text

        self._db_combo_connection = None
        self._connect_db_combo()

        # Style the buttons
        new_db_btn = QPushButton("New")
        new_db_btn.setStyleSheet(StyleHandler.get_secondary_button_style())
        new_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        new_db_btn.clicked.connect(self._create_new_database)

        # Add Reload Database button
        reload_db_btn = QPushButton("Reload")
        reload_db_btn.setStyleSheet(StyleHandler.get_secondary_button_style())
        reload_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        reload_db_btn.clicked.connect(self._reload_database)
        reload_db_btn.setToolTip("Reload the current database from disk")

        # Only include Reload and New buttons
        db_layout.addWidget(self.db_combo)
        db_layout.addWidget(reload_db_btn)
        db_layout.addWidget(new_db_btn)

        main_layout.addLayout(db_layout)
        
        # Load available databases but don't select any by default
        self._load_databases()
        
        # Create tab widget with styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCDDEE;
                border-radius: 4px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #F0F4F8;
                border: 1px solid #CCDDEE;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #E0E8F0;
            }
        """)
        self.tab_widget.currentChanged.connect(self._handle_tab_change)
        
        # Add tabs
        self._add_database_tab()
        self._add_barologger_tab()
        self._add_water_level_tab()
        self._add_water_level_runs_tab()
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Add status bar with styling
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #F0F4F8;
                color: #335588;
                border-top: 1px solid #CCDDEE;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        self.status_bar.showMessage("Ready")
        
        # Add database info to status bar
        self.db_info_label = QLabel("No database loaded")
        self.db_info_label.setStyleSheet("""
            font-weight: bold;
            color: #3070B0;
            padding-right: 5px;
        """)
        self.status_bar.addPermanentWidget(self.db_info_label)
        
        # Add folder info to status bar
        import os  # ensure os is available
        initial_folder = self.settings_handler.get_setting("local_db_directory", "")
        folder_text = initial_folder if os.path.isdir(initial_folder) else "No folder selected"
        self.folder_info_label = QLabel(f"Folder: {folder_text}")
        self.folder_info_label.setStyleSheet("""
            font-weight: bold;
            color: #3070B0;
            padding-right: 5px;
        """)
        self.folder_info_label.setToolTip(f"Database folder: {folder_text}")
        self.status_bar.addPermanentWidget(self.folder_info_label)
        
        # Setup menu
        self.setup_menu()
    
    def logout(self):
        """Log out the current user and restart the application"""
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to log out? Any unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.user_auth_service.logout()
            QMessageBox.information(self, "Logged Out", "You have been logged out successfully.")
            
            # Restart the application
            python = sys.executable
            os.execl(python, python, *sys.argv)
    
    def _connect_db_combo(self):
        """Connect the database combo box signal"""
        if self._db_combo_connection is None:
            self._db_combo_connection = self.db_combo.currentTextChanged.connect(self._on_database_changed)
            
    def _disconnect_db_combo(self):
        """Disconnect the database combo box signal"""
        if self._db_combo_connection is not None:
            self.db_combo.currentTextChanged.disconnect(self._on_database_changed)
            self._db_combo_connection = None

    def _load_databases(self):
        """Load available databases into the combo box."""
        # Set the loading flag
        self._loading_databases = True
        
        # Disconnect signals temporarily to prevent cascading events
        self._disconnect_db_combo()
        
        try:
            self.db_combo.clear()
            
            # Load only local databases initially
            local_db_files = [db for db in Path().glob("*.db") if "_(drive)" not in db.name]
            has_databases = False
            
            if local_db_files:
                for db_file in local_db_files:
                    self.db_combo.addItem(db_file.name)
                    logger.debug(f"Added local database to dropdown: {db_file.name}")
                has_databases = True
            
            if not has_databases:
                self.db_combo.addItem("No databases found")
                self.db_combo.setEnabled(False)
            else:
                self.db_combo.setEnabled(True)
                
            # If we have a current database, select it in the dropdown
            # Otherwise leave the dropdown without selection
            if self.db_manager.current_db:
                current_db_name = self.db_manager.current_db.name
                logger.debug(f"Current database: {current_db_name}")
                
                # Find and select the item
                index = self.db_combo.findText(current_db_name)
                if index >= 0:
                    self.db_combo.setCurrentIndex(index)
                    logger.debug(f"Selected database in dropdown at index {index}: {current_db_name}")
                else:
                    logger.warning(f"Could not find database {current_db_name} in dropdown")
            elif has_databases:
                # If we have databases but none is selected, set the index to -1
                self.db_combo.setCurrentIndex(-1)
                self.db_combo.setPlaceholderText("Select a database")
                logger.debug("No database currently loaded - showing placeholder text")
        finally:
            # Reset the loading flag
            self._loading_databases = False
            
            # Reconnect signals
            self._connect_db_combo()

    def _on_database_changed(self, db_name: str):
        """Handle database selection changes."""
        import time
        start_time = time.time()
        logger.info(f"PERF: Starting database change handling for {db_name}")
        
        if not db_name or db_name == "No databases found" or db_name.startswith("---"):
            return
            
        # If we're already loading databases or the combo box triggered this change, don't process further
        if self._loading_databases:
            return
            
        try:
            # Check if the database is already open
            current_db_name = self.db_manager.current_db.name if self.db_manager.current_db else None
            if current_db_name and current_db_name == db_name:
                logger.info(f"PERF: Database {db_name} is already open, skipping")
                return
            
            # Check if it's a Google Drive database (just for UI purposes)
            is_drive_db = "_(drive)" in db_name
            
            # Only allow Google Drive databases for non-guest users
            if is_drive_db and self.user_auth_service.is_guest:
                logger.warning(f"Guest user attempted to access Google Drive database {db_name}")
                QMessageBox.warning(self, "Access Denied", 
                                  "Guest users cannot access Google Drive databases.")
                # Clear the selection and return
                self._loading_databases = True
                self.db_combo.setCurrentIndex(-1)
                self._loading_databases = False
                return
            
            # Show progress dialog before opening database
            progress_dialog.show(f"Opening database: {db_name}", "Loading Database")
            progress_dialog.update(5, "Initializing database connection...")
            QApplication.processEvents()  # Process events to update UI
            
            # Open the database (all databases are treated as local)
            logger.info(f"PERF: Beginning to open database: {db_name}")
            
            # Check if the database is large (> 100MB) to use optimized opening
            db_path = Path() / db_name
            is_large_db = False
            try:
                file_size_mb = db_path.stat().st_size / (1024 * 1024)
                is_large_db = file_size_mb > 100
                progress_dialog.update(10, f"Preparing to open database ({file_size_mb:.2f} MB)...")
                QApplication.processEvents()
                
                if is_large_db:
                    logger.info(f"PERF: Large database detected ({file_size_mb:.2f} MB), using quick validation")
                    progress_dialog.update(15, "Large database detected, optimizing validation...")
                    QApplication.processEvents()
            except Exception as e:
                logger.warning(f"Could not determine database size: {e}")
                progress_dialog.update(10, "Preparing to open database...")
                QApplication.processEvents()
            
            # Open the database with quick validation for large databases
            db_open_start = time.time()
            progress_dialog.update(20, "Opening database connection...")
            QApplication.processEvents()
            
            # Pass use_quick_validation=True for large databases to skip expensive checks
            try:
                progress_dialog.update(30, "Validating database structure...")
                QApplication.processEvents()
                
                # Check if the method can accept the quick_validation parameter
                import inspect
                sig = inspect.signature(self.db_manager.open_database)
                
                if 'quick_validation' in sig.parameters:
                    self.db_manager.open_database(str(Path() / db_name), quick_validation=is_large_db)
                else:
                    # Use the original method if quick_validation is not supported
                    self.db_manager.open_database(str(Path() / db_name))
                
                progress_dialog.update(45, "Database opened, initializing tables...")
                QApplication.processEvents()
                
            except Exception as db_open_error:
                # Handle database opening errors
                logger.error(f"Error opening database: {db_open_error}")
                # Propagate the exception after updating UI
                progress_dialog.update(100, f"Error: Failed to open database")
                QApplication.processEvents()
                raise db_open_error
            
            db_open_end = time.time()
            logger.info(f"PERF: Database open operation took {(db_open_end - db_open_start)*1000:.2f}ms")
            
            progress_dialog.update(70, "Loading application views...")
            QApplication.processEvents()
            
            # Update UI
            self._update_db_info_label()
            self.status_bar.showMessage(f"Database '{db_name}' opened successfully", 3000)
            
            # Reload the database list to ensure the current selection is shown
            QTimer.singleShot(100, self._load_databases)
            
            progress_dialog.update(100, f"Database '{db_name}' loaded successfully!")
            QApplication.processEvents()
            
            # Give users time to see the completion message
            QTimer.singleShot(800, progress_dialog.close)
            
            total_time = time.time() - start_time
            logger.info(f"PERF: Total database change handling took {total_time*1000:.2f}ms")
            
        except Exception as e:
            # Close progress dialog on error
            progress_dialog.update(100, f"Error: Failed to open database")
            QApplication.processEvents()
            error_time = time.time() - start_time
            logger.error(f"PERF: Error changing database after {error_time*1000:.2f}ms: {e}")
            
            # Give users time to see the error message before showing the error dialog
            QTimer.singleShot(1000, progress_dialog.close)
            
            # Show detailed error in a message box
            error_msg = f"Failed to open database: {str(e)}"
            QMessageBox.critical(self, "Database Error", error_msg)
            
            # Reset the combo box selection on error
            self._loading_databases = True
            if self.db_manager.current_db:
                # Try to select the current database if there is one
                current_db_name = self.db_manager.current_db.name
                index = self.db_combo.findText(current_db_name)
                if index >= 0:
                    self.db_combo.setCurrentIndex(index)
                else:
                    self.db_combo.setCurrentIndex(-1)
            else:
                self.db_combo.setCurrentIndex(-1)
            self._loading_databases = False

    def _sync_database(self):
        """Sync the current database with Google Drive"""
        if not self.db_manager.current_db:
            QMessageBox.warning(self, "No Database", "No database is currently open.")
            return
            
        if not self.db_manager.is_google_drive_db:
            QMessageBox.warning(self, "Local Database", 
                              "The current database is local and cannot be synced with Google Drive.")
            return
            
        if not self.drive_service.authenticated:
            QMessageBox.warning(self, "Not Authenticated", 
                              "Not authenticated with Google Drive. Please log in first.")
            return
            
        # Sync the database
        if self.db_manager.sync_with_google_drive():
            QMessageBox.information(self, "Sync Complete", 
                                  f"Database '{self.db_manager.current_db.name}' has been synced with Google Drive.")
        else:
            QMessageBox.warning(self, "Sync Failed", 
                              "Failed to sync database with Google Drive. Please try again later.")

    def _handle_tab_change(self, index):
        """Handle tab changes with lazy loading of content."""
        # First check if we're in cleanup mode or if tab_widget has been deleted
        if not hasattr(self, 'tab_widget') or self.tab_widget is None:
            logger.debug("Tab widget no longer exists, skipping tab change handling")
            return

        # Check if we're in initialization phase
        if self._initialization_phase:
            logger.debug(f"Tab change during initialization phase, skipping progress dialog for tab {index}")
            return
        
        if index not in self._tabs:
            tab_widget = self.tab_widget.widget(index)
            if tab_widget is None:
                logger.debug(f"No widget found for tab index {index}, skipping")
                return
            
            if tab_widget.layout() is None:
                # Show loading indicator
                progress = QProgressDialog(f"Loading tab content...", None, 0, 100, self)
                progress.setWindowTitle("Loading")
                progress.setWindowModality(Qt.WindowModal)
                progress.setCancelButton(None)
                # Set fixed size to prevent random expansion
                progress.setFixedSize(400, 100)
                # Ensure consistent styling
                progress.setStyleSheet("""
                    QProgressDialog {
                        background-color: #f0f0f0;
                        border: 1px solid #ccc;
                        border-radius: 5px;
                    }
                    QProgressBar {
                        border: 1px solid #aaa;
                        border-radius: 3px;
                        background-color: #fff;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #2196F3;
                        width: 10px;
                        margin: 0.5px;
                    }
                """)
                progress.setValue(10)
                
                tab_layout = QVBoxLayout(tab_widget)
                
                # Create appropriate tab content
                try:
                    progress.setValue(30)
                    tab_content = None
                    if index == 0:
                        progress.setLabelText("Loading Wells tab...")
                        tab_content = DatabaseTab(self.db_manager)
                    elif index == 1:
                        progress.setLabelText("Loading Barometric Data tab...")
                        tab_content = BarologgerTab(self.db_manager)
                        progress.setValue(50)
                        # The barologger tab will handle its own data loading in initial_data_load
                    elif index == 2:
                        progress.setLabelText("Loading Water Levels tab...")
                        tab_content = WaterLevelTab(self.db_manager)
                    elif index == 3:
                        progress.setLabelText("Loading Runs tab...")
                        tab_content = WaterLevelRunsTab(self.db_manager)
                    
                    progress.setValue(70)
                    
                    if tab_content:
                        tab_layout.addWidget(tab_content)
                        self._tabs[index] = tab_content
                        logger.debug(f"Loaded tab content for index {index}")
                    
                    progress.setValue(100)
                    # Add a small delay before closing to make progress visible
                    QTimer.singleShot(300, progress.close)
                    
                except Exception as e:
                    logger.error(f"Error loading tab content for index {index}: {e}")
                    error_label = QLabel(f"Error loading tab content: {str(e)}")
                    error_label.setStyleSheet("color: red;")
                    tab_layout.addWidget(error_label)
                    progress.close()
        else:
            # Tab already loaded, show a progress dialog for data refresh
            tab_content = self._tabs[index]
            
            # Show loading indicator for data refresh
            progress = QProgressDialog(f"Refreshing tab data...", None, 0, 100, self)
            progress.setWindowTitle("Loading")
            progress.setWindowModality(Qt.WindowModal)
            progress.setCancelButton(None)
            progress.setFixedSize(400, 100)
            progress.setStyleSheet("""
                QProgressDialog {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
                QProgressBar {
                    border: 1px solid #aaa;
                    border-radius: 3px;
                    background-color: #fff;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                    width: 10px;
                    margin: 0.5px;
                }
            """)
            progress.setValue(10)
            
            try:
                # Update progress
                progress.setValue(30)
                
                # Set appropriate label based on tab type
                if index == 0:
                    progress.setLabelText("Refreshing Wells data...")
                elif index == 1:
                    progress.setLabelText("Refreshing Barometric data...")
                elif index == 2:
                    progress.setLabelText("Refreshing Water Levels data...")
                elif index == 3:
                    progress.setLabelText("Refreshing Runs data...")
                
                # Update progress
                progress.setValue(50)
                
                # Let the tab handle its own refresh if it has a refresh method
                if hasattr(tab_content, 'refresh_data') and callable(tab_content.refresh_data):
                    tab_content.refresh_data()
                
                # Update progress
                progress.setValue(100)
                # Add a small delay before closing to make progress visible
                QTimer.singleShot(300, progress.close)
                
            except Exception as e:
                logger.error(f"Error refreshing tab content for index {index}: {e}")
                progress.close()
                QMessageBox.warning(self, "Refresh Error", f"Error refreshing tab data: {str(e)}")

    def center_window(self):
        """Center the window on the current screen."""
        if not self.current_screen:
            self.current_screen = self.screen()
            
        frame_geometry = self.frameGeometry()
        screen_center = self.current_screen.availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())
    
    def closeEvent(self, event):
        """Handle application close event with proper cleanup."""
        try:
            # Explicitly disconnect from Google Drive before closing
            if hasattr(self, 'drive_service') and self.drive_service and self.drive_service.authenticated:
                logger.info("Disconnecting from Google Drive before closing application")
                try:
                    # Clear tokens to force re-authentication next time
                    if hasattr(self.drive_service, 'clear_credentials'):
                        self.drive_service.clear_credentials()
                    else:
                        # Alternative approach if no direct method exists
                        token_path = Path.home() / '.credentials' / 'water_levels_token.json'
                        if token_path.exists():
                            logger.info(f"Removing token file at {token_path}")
                            token_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Error disconnecting from Google Drive: {e}")
            
            # Check if there are unsaved changes
            if self.db_manager and self.db_manager.has_unsaved_changes:
                # Check if it's the CAESER_GENERAL database
                is_caeser_general = (self.db_manager.current_db and 
                                    self.db_manager.current_db.name == "CAESER_GENERAL_(drive).db")
                
                if is_caeser_general:
                    # Special warning for CAESER_GENERAL
                    reply = QMessageBox.question(
                        self,
                        "Unsaved Changes to CAESER_GENERAL",
                        "You have made changes to the CAESER_GENERAL database.\n\n"
                        "If you close without updating, these changes will NOT be saved to the Google Drive version.\n\n"
                        "Would you like to update the Google Drive version before closing?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # Update CAESER_GENERAL in Google Drive
                        self._update_caeser_general()
                        # Check if the update was successful
                        if self.db_manager.has_unsaved_changes:
                            # Update failed, ask if they still want to close
                            error_reply = QMessageBox.question(
                                self,
                                "Update Failed",
                                "Failed to update CAESER_GENERAL in Google Drive.\n\n"
                                "Do you still want to close the application? Your changes will be lost.",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No
                            )
                            
                            if error_reply == QMessageBox.No:
                                event.ignore()
                                return
                    elif reply == QMessageBox.Cancel:
                        event.ignore()
                        return
                else:
                    # Regular unsaved changes warning for other databases
                    reply = QMessageBox.question(
                        self,
                        "Unsaved Changes",
                        "You have unsaved changes in the Google Drive database. "
                        "These changes will be lost if you close without syncing. "
                        "Do you want to sync your changes before closing?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # Try to sync
                        if not self.db_manager.sync_with_google_drive():
                            # Sync failed
                            error_reply = QMessageBox.question(
                                self,
                                "Sync Failed",
                                "Failed to sync changes with Google Drive. "
                                "Do you still want to close the application?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No
                            )
                            
                            if error_reply == QMessageBox.No:
                                event.ignore()
                                return
                    elif reply == QMessageBox.Cancel:
                        event.ignore()
                        return
            
            # First, clear all references and destroy UI components
            try:
                logger.debug("Starting UI cleanup process")
                
                # Set a flag to indicate we're in cleanup mode
                self._cleanup_in_progress = True
                
                # Hide the window to prevent further user interaction
                self.hide()
                logger.debug("Main window hidden")

                # Disconnect any signals that might trigger tab changes
                if hasattr(self, 'tab_widget') and self.tab_widget is not None:
                    logger.debug("Disconnecting tab widget signals")
                    try:
                        self.tab_widget.currentChanged.disconnect()
                    except Exception as e:
                        logger.debug(f"Error disconnecting tab signals: {e}")

                # Clear and destroy all tabs first
                logger.debug(f"Starting cleanup of {len(self._tabs)} tabs")
                tabs_to_cleanup = list(self._tabs.items())  # Create a copy of items to iterate
                for tab_name, tab in tabs_to_cleanup:
                    try:
                        logger.debug(f"Cleaning up tab: {tab_name}")
                        if hasattr(tab, 'cleanup'):
                            tab.cleanup()
                            logger.debug(f"Tab {tab_name} cleanup method called")
                        
                        # Explicitly destroy tab widgets
                        if hasattr(tab, 'wells_table'):
                            logger.debug(f"Clearing wells table in {tab_name}")
                            tab.wells_table.clear()
                            tab.wells_table.setRowCount(0)
                            tab.wells_table.setColumnCount(0)
                        
                        if hasattr(tab, 'map_view'):
                            logger.debug(f"Clearing map view in {tab_name}")
                            tab.map_view.setUrl(QUrl('about:blank'))
                            tab.map_view.deleteLater()
                        
                        logger.debug(f"Deleting tab: {tab_name}")
                        tab.deleteLater()
                        
                        # Remove from tabs dictionary
                        self._tabs.pop(tab_name, None)
                        
                    except Exception as tab_error:
                        logger.error(f"Error cleaning up tab {tab_name}: {tab_error}")

                # Process events after tab cleanup
                logger.debug("Processing events after tab cleanup")
                QApplication.processEvents()

                # Clear the tab widget
                if hasattr(self, 'tab_widget') and self.tab_widget is not None:
                    logger.debug(f"Removing {self.tab_widget.count()} tabs from tab widget")
                    while self.tab_widget.count() > 0:
                        self.tab_widget.removeTab(0)
                    self.tab_widget.deleteLater()
                    self.tab_widget = None
                    logger.debug("Tab widget deleted")

                # Process events after widget cleanup
                logger.debug("Processing events after widget cleanup")
                QApplication.processEvents()

                # Close database connections
                if self.db_manager:
                    logger.debug("Closing database manager")
                    self.db_manager.close()
                    self.db_manager = None
                    logger.debug("Database manager closed and reference cleared")

                # Now delete the files
                try:
                    # Delete Google Drive database files
                    drive_db_files = list(Path().glob("*_(drive).db"))
                    for file_path in drive_db_files:
                        if file_path.exists():
                            logger.info(f"Deleting local copy of Google Drive database: {file_path}")
                            self._delete_with_retry(file_path)

                    # Always delete data folder on close to ensure fresh data on next connection
                    data_path = Path.cwd() / "data"
                    if data_path.exists():
                        logger.info(f"Cleaning up temporary data folder: {data_path}")
                        try:
                            # Use force delete immediately
                            import os
                            if os.name == 'nt':  # Windows
                                logger.debug("Using Windows force delete command")
                                os.system(f'rd /s /q "{data_path}"')
                            else:  # Unix/Linux/Mac
                                logger.debug("Using Unix force delete command")
                                os.system(f'rm -rf "{data_path}"')
                            
                            # Verify deletion
                            if not data_path.exists():
                                logger.info("Data folder successfully deleted")
                            else:
                                logger.warning("Force delete failed, folder still exists")
                                # Try alternative method as backup
                                self._delete_folder_with_retry(data_path)
                        except Exception as e:
                            logger.error(f"Error during force delete: {e}")
                            # Try alternative method as backup
                            self._delete_folder_with_retry(data_path)

                except Exception as e:
                    logger.error(f"Error during file cleanup: {e}")

            except Exception as e:
                logger.error(f"Error during UI cleanup: {e}", exc_info=True)

            finally:
                # Clear cleanup flag
                self._cleanup_in_progress = False

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

        finally:
            # Process any remaining events
            QApplication.processEvents()
            event.accept()

    def _delete_with_retry(self, path, max_retries=3, delay=1):
        """Delete a file with retries."""
        import time
        logger.info(f"Attempting to delete file: {path}")
        
        for attempt in range(max_retries):
            try:
                if path.is_file():
                    logger.debug(f"File exists, attempting deletion (attempt {attempt + 1})")
                    path.unlink(missing_ok=True)
                    if not path.exists():
                        logger.info(f"Successfully deleted file: {path}")
                        return True
                    else:
                        logger.warning(f"File still exists after unlink attempt {attempt + 1}: {path}")
                else:
                    logger.warning(f"Path is not a file: {path}")
                    return False
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to delete {path} after {max_retries} attempts: {e}")
                    return False
                logger.warning(f"Attempt {attempt + 1} to delete {path} failed: {e}")
                time.sleep(delay)
        return False

    def _delete_folder_with_retry(self, path, max_retries=3, delay=1):
        """Delete a folder with retries, using robust deletion methods."""
        import time
        import shutil
        from pathlib import Path
        
        logger.info(f"Starting folder deletion process for: {path}")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Deletion attempt {attempt + 1} for folder: {path}")
                
                # First try using shutil
                try:
                    logger.debug("Attempting shutil.rmtree...")
                    shutil.rmtree(path, ignore_errors=True)
                    if not path.exists():
                        logger.info(f"Successfully deleted folder using shutil.rmtree: {path}")
                        return True
                    logger.warning("shutil.rmtree completed but folder still exists")
                except Exception as e:
                    logger.warning(f"shutil.rmtree failed, trying alternative method: {e}")
                    
                    # If shutil fails, try manual deletion
                    if path.exists():
                        logger.debug("Starting manual deletion process...")
                        
                        # List all files before starting
                        all_files = list(path.rglob('*'))
                        logger.debug(f"Found {len(all_files)} items to process")
                        
                        # Make all files writable
                        logger.debug("Making files writable...")
                        for item in all_files:
                            try:
                                item.chmod(0o777)
                                logger.debug(f"Changed permissions for: {item}")
                            except Exception as chmod_error:
                                logger.warning(f"Failed to change permissions for {item}: {chmod_error}")
                        
                        # Delete files first
                        logger.debug("Deleting files...")
                        for item in all_files:
                            if item.is_file():
                                try:
                                    logger.debug(f"Attempting to delete file: {item}")
                                    self._delete_with_retry(item)
                                except Exception as file_error:
                                    logger.warning(f"Error deleting file {item}: {file_error}")
                        
                        # Then delete empty directories
                        logger.debug("Deleting directories...")
                        dirs_to_delete = sorted([item for item in all_files if item.is_dir()], 
                                             key=lambda x: len(str(x)), reverse=True)
                        logger.debug(f"Found {len(dirs_to_delete)} directories to delete")
                        
                        for item in dirs_to_delete:
                            try:
                                logger.debug(f"Attempting to remove directory: {item}")
                                item.rmdir()
                                logger.debug(f"Successfully removed directory: {item}")
                            except Exception as rmdir_error:
                                logger.warning(f"Failed to remove directory {item}: {rmdir_error}")
                        
                        # Finally remove the root directory
                        try:
                            logger.debug(f"Attempting to remove root directory: {path}")
                            path.rmdir()
                            logger.debug("Root directory removed successfully")
                        except Exception as root_error:
                            logger.warning(f"Failed to remove root directory: {root_error}")
                
                # Check if folder still exists
                if not path.exists():
                    logger.info(f"Successfully deleted folder on attempt {attempt + 1}")
                    return True
                
                # If we get here, the folder still exists
                remaining_files = list(path.rglob('*')) if path.exists() else []
                logger.warning(f"Folder still exists after attempt {attempt + 1}. "
                             f"Remaining items: {len(remaining_files)}")
                if remaining_files:
                    logger.debug("Remaining items:")
                    for item in remaining_files:
                        logger.debug(f"  - {item}")
                
                time.sleep(delay)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to delete folder {path} after {max_retries} attempts: {e}")
                    return False
                logger.warning(f"Attempt {attempt + 1} to delete folder {path} failed: {e}")
                time.sleep(delay)
        
        logger.error(f"Failed to delete folder after all attempts: {path}")
        return False

    def setup_menu(self):
        """Setup the application menu"""
        # Clear existing menu bar
        menu_bar = self.menuBar()
        menu_bar.clear()
        
        # User menu
        user_menu = menu_bar.addMenu("User")
        
        # Add submenu for user credentials
        user_credentials_menu = QMenu("Edit User Credentials", self)
        user_menu.addMenu(user_credentials_menu)
        
        # Load users from the users.json file
        config_dir = Path.cwd() / "config"
        users_file = config_dir / "users.json"
        
        if users_file.exists():
            try:
                with open(users_file, 'r') as f:
                    user_data = json.load(f)
                    
                    # Add each user as a menu item
                    for user in user_data.get('users', []):
                        username = user.get('username')
                        display_name = user.get('display_name', username)
                        
                        # Create action for this user
                        user_action = QAction(f"{display_name} ({username})", self)
                        user_action.triggered.connect(lambda checked, u=username: self.edit_user_credentials(u))
                        user_credentials_menu.addAction(user_action)
                        
                    # Add separator and "Add New User" option
                    user_credentials_menu.addSeparator()
                    add_user_action = QAction("Add New User", self)
                    add_user_action.triggered.connect(lambda: self.edit_user_credentials(None))
                    user_credentials_menu.addAction(add_user_action)
            except Exception as e:
                logger.error(f"Error loading users for menu: {e}")
        
        # Add user status to status bar
        self.login_status_label = QLabel("Admin")
        self.statusBar().addPermanentWidget(QLabel("User: "))
        self.statusBar().addPermanentWidget(self.login_status_label)
        
        # Add Monet API connection status to status bar
        self.monet_status_label = QLabel("Not connected")
        self.monet_status_label.setStyleSheet("color: #888;")
        self.statusBar().addPermanentWidget(QLabel(" | Monet API: "))
        self.statusBar().addPermanentWidget(self.monet_status_label)
        
        # Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        
        # Database Folder Settings action
        database_folder_action = QAction("Database Folder Settings", self)
        database_folder_action.triggered.connect(self.open_database_folder_settings)
        settings_menu.addAction(database_folder_action)
        
        # Google Drive settings
        google_drive_settings_action = QAction("Google Drive Settings", self)
        google_drive_settings_action.triggered.connect(self.open_google_drive_settings)
        settings_menu.addAction(google_drive_settings_action)
        
        # Monet API settings
        monet_settings_action = QAction("Monet API Settings", self)
        monet_settings_action.triggered.connect(self.open_monet_settings)
        settings_menu.addAction(monet_settings_action)

        # Add Water Level Meter Correction action
        water_level_correction_action = QAction("Water Level Meter Correction", self)
        water_level_correction_action.triggered.connect(self.open_water_level_correction)
        settings_menu.addAction(water_level_correction_action)

        # Add Auto Sync menu
        auto_sync_menu = menu_bar.addMenu("Auto Sync")
        # Sync Barologger Files
        sync_baro_action = QAction("Sync Barologger Files", self)
        sync_baro_action.triggered.connect(self.auto_sync_barologgers)
        auto_sync_menu.addAction(sync_baro_action)
        # Sync Water Level Files
        sync_water_action = QAction("Sync Water Level Files", self)
        sync_water_action.triggered.connect(self.auto_sync_water_levels)
        auto_sync_menu.addAction(sync_water_action)
        
        # Add icon-only menu next to Settings
        icon_menu = menu_bar.addMenu("")  # Empty text for icon-only menu
        icon_path = Path('src/gui/icons/water_level_meter.webp')
        if not icon_path.exists():
            icon_path = Path('src/gui/icons/water_level_meter.ico')
        if icon_path.exists():
            icon_menu.setIcon(QIcon(str(icon_path)))
        
        # Add actions to the icon menu
        water_level_action = QAction("Water Level Meter Settings", self)
        water_level_action.triggered.connect(self.open_water_level_correction)
        icon_menu.addAction(water_level_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        # Add Edit Tables action
        edit_tables_action = QAction("Edit Tables", self)
        edit_tables_action.triggered.connect(self.open_edit_tables_dialog)
        tools_menu.addAction(edit_tables_action)
        
        # Add Water Level Visualizer & Exporter action
        data_visualizer_action = QAction("Water Level Visualizer & Exporter", self)
        data_visualizer_action.triggered.connect(self.open_data_visualizer_dialog)
        tools_menu.addAction(data_visualizer_action)
        
        # Add XLE Metadata Editor action
        xle_metadata_editor_action = QAction("XLE Metadata Editor", self)
        xle_metadata_editor_action.triggered.connect(self.open_xle_metadata_editor)
        tools_menu.addAction(xle_metadata_editor_action)
        
        # Add LEV to XLE Converter action
        lev_to_xle_converter_action = QAction("LEV to XLE Converter", self)
        lev_to_xle_converter_action.triggered.connect(self.open_lev_to_xle_converter)
        tools_menu.addAction(lev_to_xle_converter_action)
        
        # Add CSV to XLE Converter action
        csv_to_xle_converter_action = QAction("CSV to XLE Converter", self)
        csv_to_xle_converter_action.triggered.connect(self.open_csv_to_xle_converter)
        tools_menu.addAction(csv_to_xle_converter_action)
        
        # Add Solinst Unit Converter action
        unit_converter_action = QAction("Solinst Unit Converter", self)
        unit_converter_action.triggered.connect(self.open_solinst_unit_converter)
        tools_menu.addAction(unit_converter_action)
        
        # Add Find XLE by Serial Number action
        find_xle_by_serial_action = QAction("Find XLE by Serial Number", self)
        find_xle_by_serial_action.triggered.connect(self.open_find_xle_by_serial)
        tools_menu.addAction(find_xle_by_serial_action)
    
    def edit_user_credentials(self, username):
        """Open a dialog to edit user credentials"""
        from .dialogs.edit_user_dialog import EditUserDialog
        
        try:
            # Create and show the edit user dialog
            dialog = EditUserDialog(username, self)
            if dialog.exec_() == QDialog.Accepted:
                # Reload the user menu to reflect changes
                self.setup_menu()
        except Exception as e:
            logger.error(f"Error editing user credentials: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit user credentials: {str(e)}")

    def open_google_drive_settings(self):
        """Open the Google Drive settings dialog"""
        dialog = GoogleDriveSettingsDialog(self.settings_handler, self)
        if dialog.exec_():
            # Reload databases after settings change
            self._load_databases()
            
            # Update water level runs tab if it exists
            if 'water_level_runs' in self._tabs:
                runs_tab = self._tabs['water_level_runs']
                
                # If we're authenticated, update the connection state
                if self.drive_service and self.drive_service.authenticated:
                    if hasattr(runs_tab, '_update_connection_state'):
                        runs_tab._update_connection_state(True)
                    if hasattr(runs_tab, 'load_existing_runs'):
                        runs_tab.load_existing_runs()
            
            # Update barologger tab if it exists
            if 'barologger' in self._tabs:
                barologger_tab = self._tabs['barologger']
                if hasattr(barologger_tab, 'update_drive_state'):
                    barologger_tab.update_drive_state(self.drive_service.authenticated)
            
            # Update water level tab if it exists
            if 'water_level' in self._tabs:
                water_level_tab = self._tabs['water_level']
                if hasattr(water_level_tab, 'update_drive_state'):
                    water_level_tab.update_drive_state(self.drive_service.authenticated)

    def open_monet_settings(self):
        """Open the Monet API settings dialog"""
        dialog = MonetSettingsDialog(self.settings_handler, self)
        if dialog.exec_() == QDialog.Accepted:
            # Update the Monet status after saving settings
            self._update_monet_status()

    def open_water_level_correction(self):
        """Open the water level meter correction dialog"""
        from .dialogs.water_level_correction_dialog import WaterLevelCorrectionDialog
        dialog = WaterLevelCorrectionDialog(self)
        dialog.exec_()

    def toggle_auto_sync(self):
        """Toggle auto sync functionality"""
        # Placeholder for future auto sync implementation
        QMessageBox.information(self, "Auto Sync", "Auto Sync feature will be implemented soon!")

    def auto_sync_barologgers(self):
        """Run guided or automatic sync for barologger XLE files with Google Drive integration"""
        # Initialize handler if needed
        if self.auto_update_handler is None:
            self.auto_update_handler = AutoUpdateHandler(
                parent=self, 
                db_manager=self.db_manager,
                drive_service=self.drive_service,
                drive_monitor=self.drive_monitor,
                settings_handler=self.settings_handler,
                tabs=self._tabs
            )
        
        # Delegate to the handler
        self.auto_update_handler.auto_sync_barologgers()
    
    def auto_sync_water_levels(self):
        """Run guided or automatic sync for water level XLE files with Google Drive integration"""
        # Initialize handler if needed
        if self.auto_update_handler is None:
            self.auto_update_handler = AutoUpdateHandler(
                parent=self, 
                db_manager=self.db_manager,
                drive_service=self.drive_service,
                drive_monitor=self.drive_monitor,
                settings_handler=self.settings_handler,
                tabs=self._tabs
            )
        
        # Delegate to the handler
        self.auto_update_handler.auto_sync_water_levels()
    
    def open_edit_tables_dialog(self):
        """Open the Edit Tables dialog"""
        from .dialogs.edit_tables_dialog import EditTablesDialog
        dialog = EditTablesDialog(self.db_manager, self)
        result = dialog.exec_()
        
        # Refresh tabs selectively when the dialog is closed
        if result == QDialog.Accepted or self.db_manager.has_unsaved_changes:
            # Update status bar to show refresh is happening
            self.status_bar.showMessage("Refreshing application data...")
            
            # Refresh only specific tabs and data that don't involve the large tables
            # (exclude water_level_readings, manual_level_readings, barometric_readings)
            for tab_name, tab in self._tabs.items():
                if tab_name == "database":  # Wells tab
                    # Always refresh the wells tab as it doesn't involve large tables
                    if hasattr(tab, 'refresh_data') and callable(tab.refresh_data):
                        tab.refresh_data(skip_large_tables=True)
                elif tab_name == "barologger":
                    # Refresh only the barologger info, not the readings
                    if hasattr(tab, 'refresh_barologger_info') and callable(tab.refresh_barologger_info):
                        tab.refresh_barologger_info()
                elif tab_name == "water_level":
                    # Refresh only the well/transducer info, not the readings
                    if hasattr(tab, 'refresh_transducer_info') and callable(tab.refresh_transducer_info):
                        tab.refresh_transducer_info()
                elif tab_name == "water_level_runs":
                    # Refresh the runs tab as it deals with metadata not the actual readings
                    if hasattr(tab, 'refresh_data') and callable(tab.refresh_data):
                        tab.refresh_data(skip_readings=True)
            
            # Update status bar
            self.status_bar.showMessage("Data refresh complete", 3000)  # Show for 3 seconds

    def moveEvent(self, event: QMoveEvent):
        """Handle window move events with debounce approach"""
        super().moveEvent(event)
        self._debounce_screen_change()
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle window resize events with debounce approach"""
        super().resizeEvent(event)
        self._debounce_screen_change()

    def _debounce_screen_change(self):
        """Debounce screen changes with visual masking overlay"""
        import time  # Add time import at the top
        
        # Cancel any pending update timer
        if hasattr(self, '_stability_timer') and self._stability_timer.isActive():
            self._stability_timer.stop()
        
        # Create the timer if it doesn't exist
        if not hasattr(self, '_stability_timer'):
            self._stability_timer = QTimer(self)
            self._stability_timer.setSingleShot(True)
            self._stability_timer.timeout.connect(self._check_and_update_screen)
        
        # If this is the first movement in a sequence, initialize tracking
        if not hasattr(self, '_in_transition') or not self._in_transition:
            # Store transition state
            self._in_transition = True
            self._transition_start_screen = self.screen()
            self._transition_start_time = time.time()
            
            # Create visual overlay to mask transitions
            self._create_transition_overlay()
            
            # Update status bar
            self.statusBar().showMessage("Adjusting layout for new display...")
        
        # Add max wait time check - force update if it's been more than 3 seconds
        elif hasattr(self, '_transition_start_time') and time.time() - self._transition_start_time > 3:
            logger.debug("Maximum transition wait time reached, forcing screen update")
            self._stability_timer.stop()
            self._check_and_update_screen()
            return
        
        # Start stability timer with reduced wait time (800ms instead of 2000ms)
        self._stability_timer.start(800)  # Reduced from 2000ms

    def _create_transition_overlay(self):
        """Create semi-transparent overlay during screen transitions"""
        if not hasattr(self, '_overlay') or self._overlay is None:
            self._overlay = QWidget(self)
            self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 15%);")
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_()
            self._overlay.show()

    def _check_and_update_screen(self):
        """Check if screen has changed after movement has stabilized"""
        try:
            # We're no longer in transition
            self._in_transition = False
            
            # Remove the overlay if it exists
            if hasattr(self, '_overlay') and self._overlay is not None:
                self._overlay.hide()
                self._overlay.deleteLater()
                self._overlay = None
            
            # Get the current screen
            new_screen = self.screen()
            new_dpi = new_screen.devicePixelRatio()
            
            # Check if the screen has actually changed
            if (new_screen != self._transition_start_screen or 
                abs(new_dpi - self.current_dpi_factor) > 0.05):
                
                logger.info(f"Screen changed after movement: from {self._transition_start_screen.name()} to {new_screen.name()}")
                logger.info(f"DPI ratio: from {self.current_dpi_factor} to {new_dpi}")
                
                # Update current screen and DPI references
                self.current_screen = new_screen
                self.current_dpi_factor = new_dpi
                
                # Update layouts for new screen
                self._update_layouts_for_screen()
                
                # Update status message
                self.statusBar().showMessage("Layout updated for new display", 3000)
            else:
                # Clear status message if no change occurred
                if self.statusBar().currentMessage() == "Adjusting layout for new display...":
                    self.statusBar().clearMessage()
                    
        except Exception as e:
            logger.error(f"Error checking screen change after stability: {e}")
            # Make sure to clean up in case of error
            if hasattr(self, '_overlay') and self._overlay is not None:
                self._overlay.hide()
                self._overlay.deleteLater()
                self._overlay = None

    def _update_layouts_for_screen(self):
        """Update layouts and widgets for the current screen's DPI"""
        try:
            # Temporarily block signals during adjustment
            self.blockSignals(True)
            
            # Block all move & resize event handlers during this operation
            self.installEventFilter(self)
            
            # Apply screen-specific sizing
            screen_rect = self.current_screen.availableGeometry()
            screen_size = screen_rect.size()
            
            # Calculate good default size based on screen resolution 
            # Use a simpler calculation - 75% of screen size
            width = min(int(screen_size.width() * 0.75), 1600)  # Cap at 1600px
            height = min(int(screen_size.height() * 0.75), 1000)  # Cap at 1000px
            
            # Adjust database combobox
            if hasattr(self, 'db_combo'):
                self.db_combo.setMinimumWidth(min(int(300 * (screen_size.width() / 1920)), 400))
                self.db_combo.setMaximumWidth(min(int(500 * (screen_size.width() / 1920)), 600))
            
            # First update the window size
            self.resize(width, height)
            
            # Center on the new screen
            self.center_window()
            
            # Wait a bit before updating tabs
            QTimer.singleShot(200, self._update_tab_layouts)
            
        except Exception as e:
            self.logger.error(f"Error updating layouts for screen change: {e}")
        finally:
            # Re-enable signals
            self.blockSignals(False)
            
            # Remove event filter 
            self.removeEventFilter(self)

    def _update_tab_layouts(self):
        """Update tab layouts after window resize is complete"""
        try:
            # Update tabs if they exist
            if hasattr(self, '_tabs'):
                for tab_name, tab in self._tabs.items():
                    if hasattr(tab, 'update_for_screen'):
                        try:
                            # Try with layout_only parameter
                            tab.update_for_screen(self.current_screen, layout_only=True)
                        except TypeError:
                            # Fall back to calling without the parameter
                            tab.update_for_screen(self.current_screen)
                    
                    # Force tab layout update
                    if hasattr(tab, 'layout'):
                        layout = tab.layout()
                        if layout:
                            layout.update()
                            layout.activate()
            
            # Update the central widget layout
            if self.centralWidget() and self.centralWidget().layout():
                self.centralWidget().layout().update()
                self.centralWidget().layout().activate()
                
            # Update the UI
            self.update()
            
        except Exception as e:
            logger.error(f"Error updating tab layouts: {e}")

    def eventFilter(self, obj, event):
        """Filter window events during transitions"""
        # Only block layout-related events during transition
        if hasattr(self, '_in_transition') and self._in_transition:
            if event.type() in (QEvent.LayoutRequest, QEvent.Move, QEvent.Resize):
                return True  # Block these events
        
        # Let other events pass through
        return super().eventFilter(obj, event)

    def _update_db_info_label(self):
        """Update the database info label with current database information."""
        if not hasattr(self, 'db_info_label'):
            return
            
        if not self.db_manager or not self.db_manager.current_db:
            self.db_info_label.setText("No database loaded")
            return
            
        # Get current database information
        db_name = self.db_manager.current_db.name
        
        # Get the path - the current_db itself might be a Path object or have a path attribute
        try:
            # First, check if current_db.path exists - it might be a string or Path
            if hasattr(self.db_manager.current_db, 'path'):
                db_path = self.db_manager.current_db.path
                # If it's a Path object, convert to string
                if hasattr(db_path, 'resolve'):
                    db_path = str(db_path.resolve())
            # If no path attribute, current_db itself might be a Path
            elif hasattr(self.db_manager.current_db, 'resolve'):
                db_path = str(self.db_manager.current_db.resolve())
            else:
                db_path = str(self.db_manager.current_db)  # Fallback to string representation
        except Exception as e:
            logger.error(f"Error getting database path: {e}")
            db_path = "Unknown path"
        
        # Check if it's a Google Drive database
        is_drive_db = "_(drive)" in db_name
        
        # Format text with database name and location type
        if is_drive_db:
            self.db_info_label.setText(f"DB: {db_name} (Google Drive)")
        else:
            self.db_info_label.setText(f"DB: {db_name} (Local)")
            
        # Add a tooltip with the full path
        self.db_info_label.setToolTip(f"Database path: {db_path}")

    def open_data_visualizer_dialog(self):
        """Open the standalone water level data visualizer application"""
        try:
            if not self.db_manager.current_db:
                QMessageBox.warning(self, "No Database", "Please open a database first.")
                return
                
            # Get the path to the new visualizer app
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            visualizer_path = tools_dir / "Visualizer" / "main.py"
            
            if not visualizer_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find Visualizer at {visualizer_path}"
                )
                return
                
            # Get the path to the database - ensure it's a string
            db_path = str(self.db_manager.current_db)
            
            # Create a temporary settings file to pass the database path
            settings_path = tools_dir / "Visualizer" / "settings.json"
            
            # Prepare settings with current database path
            settings = {
                'database_path': db_path,
                'selected_well': None
            }
            
            # Save settings
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
                
            logger.debug(f"Launching standalone visualizer with database: {db_path}")
            
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(visualizer_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch Water Level Visualizer: {str(e)}"
            )
    
    def open_xle_metadata_editor(self):
        """Launch the XLE Metadata Editor tool"""
        try:
            # Get the path to the tools directory relative to the current file
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            editor_path = tools_dir / "xle_metadata_editor.py"
            
            if not editor_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find XLE Metadata Editor at {editor_path}"
                )
                return
                
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(editor_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch XLE Metadata Editor: {str(e)}"
            )
    
    def open_lev_to_xle_converter(self):
        """Launch the LEV to XLE Converter tool"""
        try:
            # Get the path to the tools directory relative to the current file
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            converter_path = tools_dir / "solinst_lev_to_xle_converter.py"
            
            if not converter_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find LEV to XLE Converter at {converter_path}"
                )
                return
                
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(converter_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch LEV to XLE Converter: {str(e)}"
            )
    
    def open_csv_to_xle_converter(self):
        """Launch the CSV to XLE Converter tool"""
        try:
            # Get the path to the tools directory relative to the current file
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            converter_path = tools_dir / "csv_to_xle_converter.py"
            
            if not converter_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find CSV to XLE Converter at {converter_path}"
                )
                return
                
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(converter_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch CSV to XLE Converter: {str(e)}"
            )
    
    def open_solinst_unit_converter(self):
        """Launch the Solinst Unit Converter tool"""
        try:
            # Get the path to the tools directory relative to the current file
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            converter_path = tools_dir / "solinst_unit_converter.py"
            
            if not converter_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find Solinst Unit Converter at {converter_path}"
                )
                return
                
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(converter_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch Solinst Unit Converter: {str(e)}"
            )

    def open_find_xle_by_serial(self):
        """Launch the Find XLE by Serial Number tool"""
        try:
            # Get the path to the tools directory relative to the current file
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            find_xle_path = tools_dir / "find_xle_by_serial.py"
            
            if not find_xle_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find Find XLE by Serial Number tool at {find_xle_path}"
                )
                return
                
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(find_xle_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch Find XLE by Serial Number tool: {str(e)}"
            )

    def _reload_database(self):
        """Reload the current database from disk"""
        if not self.db_manager.current_db:
            QMessageBox.warning(self, "No Database", "No database is currently open.")
            return

        try:
            # Show confirmation dialog if database has unsaved changes
            if self.db_manager.has_unsaved_changes:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "There are unsaved changes in the database. These changes will be lost if you reload.\n\n"
                    "Do you want to continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return

            # Get current database path and name
            current_db_path = str(self.db_manager.current_db)
            current_db_name = Path(current_db_path).name

            # Show progress dialog
            progress_dialog.show("Reloading database...", "Database Reload")
            progress_dialog.update(20, "Closing current database connection...")

            # Close current database connection
            self.db_manager.close()

            progress_dialog.update(50, "Opening database from disk...")

            # Reopen the database
            self.db_manager.open_database(current_db_path)

            progress_dialog.update(70, "Refreshing application data...")

            # Refresh all tabs
            for tab in self._tabs.values():
                if hasattr(tab, 'refresh_data') and callable(tab.refresh_data):
                    tab.refresh_data()

            progress_dialog.update(90, "Updating interface...")

            # Update the database info label
            self._update_db_info_label()

            # Update status bar
            self.status_bar.showMessage(f"Database '{current_db_name}' reloaded successfully", 3000)

            progress_dialog.close()

            # Show success message
            QMessageBox.information(self, "Success", f"Database '{current_db_name}' has been reloaded successfully.")

        except Exception as e:
            progress_dialog.close()
            logger.error(f"Error reloading database: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reload database: {str(e)}")

    def change_database_folder(self):
        """DEPRECATED: Prompt user to select a new folder containing database files and reload."""
        # This method is maintained for backward compatibility
        logger.warning("The change_database_folder method is deprecated, using open_database_folder_settings instead")
        self.open_database_folder_settings()

    def open_database_folder_settings(self):
        """Open the database folder settings dialog"""
        from .dialogs.database_folder_settings_dialog import DatabaseFolderSettingsDialog
        
        dialog = DatabaseFolderSettingsDialog(self.settings_handler, self)
        if dialog.exec_() == QDialog.Accepted:
            # Get the selected folder
            selected_folder = self.settings_handler.get_setting("local_db_directory", "")
            
            if selected_folder and os.path.isdir(selected_folder):
                # Update folder info in status bar
                self.folder_info_label.setText(f"Folder: {selected_folder}")
                self.folder_info_label.setToolTip(f"Database folder: {selected_folder}")
                
                # Change to the selected directory
                try:
                    os.chdir(selected_folder)
                    self.logger.debug(f"Changed working directory to: {selected_folder}")
                    
                    # Populate the database dropdown without loading any database
                    self._load_databases()
                    
                    # Check if any databases were found
                    if self.db_combo.count() == 0 or self.db_combo.itemText(0) == "No databases found":
                        QMessageBox.warning(self, "Warning", "No .db files found in the selected folder.")
                    else:
                        # Show message
                        self.status_bar.showMessage("Database folder changed. Select a database from the dropdown to load it.", 5000)
                    
                    # Switch to Database tab
                    index = self.tab_widget.indexOf(self._tabs.get("database"))
                    if index != -1:
                        self.tab_widget.setCurrentIndex(index)
                        
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to change database folder: {e}")
            
            # Update runs tab if it exists to refresh data
            if "water_level_runs" in self._tabs:
                if hasattr(self._tabs["water_level_runs"], 'load_existing_runs'):
                    self._tabs["water_level_runs"].load_existing_runs()

    def _add_database_tab(self):
        """Add the database tab"""
        tab = DatabaseTab(self.db_manager)
        self._tabs["database"] = tab
        self.tab_widget.addTab(tab, "Wells")
        
    def _add_barologger_tab(self):
        """Add the barologger tab"""
        tab = BarologgerTab(self.db_manager)
        self._tabs["barologger"] = tab
        self.tab_widget.addTab(tab, "Barometric Data")
        
    def _add_water_level_tab(self):
        """Add the water level tab"""
        tab = WaterLevelTab(self.db_manager)
        self._tabs["water_level"] = tab
        self.tab_widget.addTab(tab, "Water Levels")
        
    def _add_water_level_runs_tab(self):
        """Add the water level runs tab"""
        # Always add the Runs tab, removing the guest check
        tab = WaterLevelRunsTab(self.db_manager)
        self._tabs["water_level_runs"] = tab
        self.tab_widget.addTab(tab, "Runs")

    def _finish_initialization(self):
        """Complete the initialization process after the UI is shown"""
        if not self.progress_dialog:
            return
            
        self.progress_dialog.setValue(60)
        self.progress_dialog.setLabelText("Finalizing initialization...")
        
        # Check if we should load database folder at startup
        load_folder_at_startup = self.settings_handler.get_setting("load_db_folder_at_startup", True)
        
        if load_folder_at_startup:
            # Get database folder from settings
            initial_folder = self.settings_handler.get_setting("local_db_directory", "")
            if initial_folder and os.path.isdir(initial_folder):
                self.progress_dialog.setValue(70)
                self.progress_dialog.setLabelText(f"Loading database folder: {initial_folder}")
                logger.debug(f"Initial folder is set to {initial_folder}, loading databases")
                
                try:
                    # Change to the initial folder and load databases
                    os.chdir(initial_folder)
                    self.folder_info_label.setText(f"Folder: {initial_folder}")
                    self.folder_info_label.setToolTip(f"Database folder: {initial_folder}")
                    
                    # Populate dropdown without selecting any database
                    self._load_databases()
                    
                    # Show a message to the user
                    self.status_bar.showMessage("Please select a database from the dropdown to load it", 5000)
                except Exception as e:
                    logger.error(f"Error loading initial database folder: {e}")
            else:
                self.progress_dialog.setValue(70)
                self.progress_dialog.setLabelText("No database folder configured")
                logger.debug("No initial folder set or invalid, waiting for user to select one")
                # Show a message to prompt the user
                QTimer.singleShot(500, lambda: self.status_bar.showMessage("Please set a database folder via Settings menu", 5000))
        else:
            self.progress_dialog.setValue(70)
            self.progress_dialog.setLabelText("Database auto-loading disabled")
            logger.debug("Database folder auto-loading is disabled")
        
        # We'll skip the barologger tab refresh here since it will be refreshed when the tab is selected
        # This prevents the double refresh we're seeing in the logs
        self.progress_dialog.setValue(85)
        self.progress_dialog.setLabelText("Preparing application tabs...")
        
        # Move to completion
        self.progress_dialog.setValue(90)
        self.progress_dialog.setLabelText("Finalizing startup...")
        self._complete_initialization()
        
        # Update the database info label after loading the database
        self._update_db_info_label()

    def load_local_database(self):
        """Load a local database - first try CAESER_GENERAL.db, then any available database"""
        try:
            # First, look for CAESER_GENERAL.db in the current directory
            caeser_general_path = Path() / "CAESER_GENERAL.db"
            if caeser_general_path.exists():
                logger.info(f"Found CAESER_GENERAL.db at {caeser_general_path}, loading it")
                self.db_manager.open_database(str(caeser_general_path))
                
                # Update the database info label
                self._update_db_info_label()
                
                logger.info(f"Loaded CAESER_GENERAL.db database")
                return True
                
            # If CAESER_GENERAL.db not found, try to load the first available database
            db_files = list(Path().glob("*.db"))
            if db_files:
                first_db = db_files[0]
                logger.info(f"CAESER_GENERAL.db not found, loading first available database: {first_db}")
                self.db_manager.open_database(str(first_db))
                
                # Update the database info label
                self._update_db_info_label()
                
                logger.info(f"Loaded default database: {first_db}")
                return True
                
            # No databases found
            logger.warning("No databases found to load")
            return False
                
        except Exception as e:
            logger.error(f"Error loading local database: {e}")
            return False

    def _check_drive_with_progress(self, start_progress):
        """Check Google Drive with progress updates"""
        try:
            # Update progress dialog
            if self.progress_dialog:
                self.progress_dialog.setValue(start_progress)
                self.progress_dialog.setLabelText("Connecting to Google Drive...")
            
            # First ensure we're authenticated
            if not self.drive_service.authenticated:
                if self.progress_dialog:
                    self.progress_dialog.setLabelText("Authenticating with Google Drive...")
                
                if not self.authenticate_google_drive():
                    self._complete_initialization()
                    return
            
            # Update progress
            if self.progress_dialog:
                self.progress_dialog.setValue(start_progress + 2)
                self.progress_dialog.setLabelText("Initializing Google Drive monitor...")
            
            # Ensure drive_monitor is initialized
            if not hasattr(self, 'drive_monitor') or self.drive_monitor is None:
                # Set up Google Drive monitor with the XLE files folder ID
                xle_folder_id = self.settings_handler.get_setting("google_drive_xle_folder_id", "")
                if not xle_folder_id:
                    logger.warning("Google Drive XLE folder ID not set, using default")
                    xle_folder_id = "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"  # Default XLE files folder ID
                    self.settings_handler.set_setting("google_drive_xle_folder_id", xle_folder_id)
                
                self.drive_monitor = GoogleDriveMonitor(xle_folder_id, self.settings_handler)
                if not self.drive_monitor.authenticate():
                    logger.error("Failed to authenticate Google Drive monitor")
                    self._complete_initialization()
                    return
            
            # Update progress
            if self.progress_dialog:
                self.progress_dialog.setValue(start_progress + 4)
                self.progress_dialog.setLabelText("Checking for new XLE files in Google Drive...")
            
            try:
                # Check for new files
                logger.info("Checking for new XLE files in Google Drive")
                self.drive_monitor.check_for_new_files()
                
                # Update progress
                if self.progress_dialog:
                    self.progress_dialog.setValue(start_progress + 8)
                    self.progress_dialog.setLabelText("Google Drive check completed successfully")
                
            except Exception as e:
                logger.error(f"Error checking Google Drive: {e}")
                
                # Update progress dialog if it exists
                if self.progress_dialog:
                    self.progress_dialog.setLabelText(f"Error checking Google Drive: {e}")
                    # Give user time to see the error
                    QTimer.singleShot(2000, lambda: self._complete_initialization())
                    return
            
            # Complete initialization
            self._complete_initialization()
            
        except Exception as e:
            logger.error(f"Error in Google Drive check: {e}")
            self._complete_initialization()
    
    def _complete_initialization(self):
        """Complete the initialization process"""
        if self.progress_dialog:
            self.progress_dialog.setValue(98)
            self.progress_dialog.setLabelText("Finalizing application setup...")
            
            # Initialize AutoUpdateHandler now that tabs are setup
            if self.auto_update_handler is None:
                self.auto_update_handler = AutoUpdateHandler(
                    parent=self, 
                    db_manager=self.db_manager,
                    drive_service=self.drive_service,
                    drive_monitor=self.drive_monitor,
                    settings_handler=self.settings_handler,
                    tabs=self._tabs
                )
            
            # Final steps
            self.progress_dialog.setValue(100)
            self.progress_dialog.setLabelText("Initialization complete!")
            
            # End initialization phase
            self._initialization_phase = False
            
            # Close the progress dialog
            QTimer.singleShot(500, self._close_progress_dialog)
        
        # Update the database info label with current database (if any)
        self._update_db_info_label()
        
        # Check and update Monet connection status
        self._update_monet_status()

    def _update_monet_status(self):
        """Check and update the Monet API connection status"""
        try:
            username = self.settings_handler.get_setting("monet_username", "")
            has_password = bool(self.settings_handler.get_setting("monet_password", ""))
            
            if username and has_password:
                self.monet_status_label.setText(f"Connected as {username}")
                self.monet_status_label.setStyleSheet("color: #007700; font-weight: bold;")
            else:
                self.monet_status_label.setText("Not configured")
                self.monet_status_label.setStyleSheet("color: #888;")
        except Exception as e:
            logger.error(f"Error updating Monet status: {e}")
            self.monet_status_label.setText("Status error")
            self.monet_status_label.setStyleSheet("color: #ff0000;")

    def _close_progress_dialog(self):
        """Close the progress dialog safely"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    def mark_database_modified(self):
        """Mark the current database as having unsaved changes."""
        if self.db_manager and self.db_manager.current_db:
            self.db_manager.mark_as_modified()
            
            # Update status bar to show modified status
            if self.db_manager.current_db.name == "CAESER_GENERAL_(drive).db":
                self.status_bar.showMessage("CAESER_GENERAL database modified - remember to update before closing")
            else:
                self.status_bar.showMessage("Database modified")
                
            # Update the database info label to show modified status
            if hasattr(self, 'db_info_label'):
                current_text = self.db_info_label.text()
                if " (Modified)" not in current_text:
                    self.db_info_label.setText(f"{current_text} (Modified)")

    def _handle_database_synced(self, db_name):
        """Handle database synced signal from the database manager"""
        # Update the status bar
        self.status_bar.showMessage(f"Database '{db_name}' synced with Google Drive")
        
        # Reset the modified flag in the UI
        if self.db_manager and self.db_manager.current_db and self.db_manager.current_db.name == db_name:
            # Clear any modified status messages
            if "modified" in self.status_bar.currentMessage().lower():
                self.status_bar.showMessage(f"Database '{db_name}' synced with Google Drive")
                
            # Update the database info label (remove any Modified status)
            self._update_db_info_label()

    def _perform_database_creation(self, file_path):
        """Perform the actual database creation with progress updates."""
        try:
            progress_dialog.update(5, "Initializing database parameters...")
            QApplication.processEvents()  # Process events to update UI
            
            # Get the database name for display purposes
            db_name = Path(file_path).name
            
            # Step 1: Create the database file
            progress_dialog.update(10, f"Creating database file: {db_name}")
            QApplication.processEvents()  # Process events to update UI
            self.db_manager.create_database(file_path)
            
            # Step 2: Setting up tables
            progress_dialog.update(30, "Creating well data tables...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(35, "Creating barologger tables...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(40, "Creating water level tables...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(45, "Creating metadata tables...")
            QApplication.processEvents()  # Process events to update UI
            
            # Step 3: Creating indexes for fast data access
            progress_dialog.update(50, "Creating database indexes...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(55, "Optimizing for barometric data...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(60, "Optimizing for water level data...")
            QApplication.processEvents()  # Process events to update UI
            
            # Step 4: Finalizing setup
            progress_dialog.update(70, "Finalizing database structure...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(75, "Setting database parameters...")
            QApplication.processEvents()  # Process events to update UI
            progress_dialog.update(80, "Verifying database integrity...")
            QApplication.processEvents()  # Process events to update UI
            
            # Step 5: Refreshing UI
            progress_dialog.update(85, "Refreshing database list...")
            QApplication.processEvents()  # Process events to update UI
            
            # Refresh the database list
            self._load_databases()
            
            progress_dialog.update(90, "Loading new database...")
            QApplication.processEvents()  # Process events to update UI
            
            # Select the newly created database
            new_db_name = Path(file_path).name
            self.db_combo.setCurrentText(new_db_name)
            
            progress_dialog.update(95, "Refreshing application views...")
            QApplication.processEvents()  # Process events to update UI
            
            # Refresh all tabs
            for tab in self._tabs.values():
                if hasattr(tab, 'refresh_data') and callable(tab.refresh_data):
                    tab.refresh_data()
            
            progress_dialog.update(100, f"Database '{db_name}' created successfully!")
            QApplication.processEvents()  # Process events to update UI
            
            # Give users a moment to see the completion message
            QTimer.singleShot(1000, progress_dialog.close)
            
            # Show success message
            self.status_bar.showMessage(f"New database '{db_name}' created successfully", 5000)
            
        except Exception as e:
            logger.error(f"Error during database creation: {e}")
            progress_dialog.update(100, "Error: Database creation failed")
            QApplication.processEvents()  # Process events to update UI
            QTimer.singleShot(1000, progress_dialog.close)
            QMessageBox.critical(self, "Database Creation Error", f"Failed to create database: {str(e)}")

    def _create_new_database(self):
        """Create a new database (local only)."""
        try:
            # Create local database only
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Create New Database",
                str(Path()),
                "Database files (*.db)"
            )
            
            if file_path:
                # Show progress dialog
                progress_dialog.show("Creating new database...", "Database Creation", min_duration=0)
                progress_dialog.update(10, "Initializing database structure...")
                QApplication.processEvents()  # Process events to update UI
                
                # Create the database
                QTimer.singleShot(100, lambda: self._perform_database_creation(file_path))
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            progress_dialog.close()  # Make sure to close the dialog on error
            QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")