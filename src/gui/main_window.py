# src/gui/main_window.py

import sys
import os
import shutil
import subprocess  # Add this import for the subprocess module
import time
from pathlib import Path
import pandas as pd
import logging
import matplotlib
from PyQt5.QtGui import QIcon, QResizeEvent, QMoveEvent, QScreen
from PyQt5.QtWidgets import (
    QAction, QDialog, QProgressDialog, QMainWindow, QInputDialog, QTabWidget, 
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, 
    QPushButton, QFileDialog, QMessageBox, QSizePolicy, QMenu,
    QFrame, QApplication  # Added QFrame and QApplication to the imports
)
from PyQt5.QtCore import QTimer, Qt, QUrl, QEvent
import json
from googleapiclient.http import MediaIoBaseDownload
from .handlers.auto_update_handler import AutoUpdateHandler
# Configure matplotlib once at startup
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['font.size'] = 10

from .tabs.database_tab import DatabaseTab
from .tabs.barologger_tab import BarologgerTab
from .tabs.water_level_tab import WaterLevelTab
from .tabs.recharge.recharge_tab import RechargeTab
from .tabs.water_level_runs_tab import WaterLevelRunsTab
from .tabs.geophysical_data_tab import GeophysicalDataTab
from ..database.manager import DatabaseManager
from .handlers.settings_handler import SettingsHandler
# Legacy Google Drive dialog - replaced by UnifiedCredentialsDialog
# from .dialogs.google_drive_settings_dialog import GoogleDriveSettingsDialog
from .dialogs.monet_settings_dialog import MonetSettingsDialog  # Import the new dialog
# REMOVED: Google Drive OAuth handlers - replaced by service account
# from .handlers.google_drive_db_handler import GoogleDriveDatabaseHandler
# from .handlers.google_drive_service import GoogleDriveService
from .handlers.cloud_database_handler import CloudDatabaseHandler
from .handlers.shared_drive_db_handler import SharedDriveDbHandler
from .handlers.user_auth_service import UserAuthService
from .dialogs.login_dialog import LoginDialog
from .dialogs.user_management_dialog import UserManagementDialog
from .dialogs.save_to_cloud_dialog import SaveToCloudDialog
# from .dialogs.database_comparison_dialog import DatabaseComparisonDialog  # Temporarily disabled - file was removed
from .handlers.progress_dialog_handler import progress_dialog
from .handlers.style_handler import StyleHandler  # Import the style handler
from .dialogs.application_help_system import ApplicationHelpSystem
from .handlers.auto_updater import AutoUpdater
from .handlers.shared_drive_updater import SharedDriveUpdater
from .dialogs.feedback_dialog import FeedbackDialog
from .handlers.version_checker import VersionChecker
from .dialogs.shared_drive_settings_dialog import SharedDriveSettingsDialog
from .dialogs.unified_credentials_dialog import UnifiedCredentialsDialog
from .dialogs.draft_selection_dialog import DraftSelectionDialog

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
        
        # REMOVED: Google Drive OAuth service initialization
        # self.drive_service = GoogleDriveService.get_instance(self.settings_handler)
        # self.drive_db_handler = None
        
        
        # Initialize Cloud database handler (will be set after authentication)
        self.cloud_db_handler = None
        
        # Initialize user authentication service with users database
        # Use app directory instead of current working directory
        app_dir = Path(__file__).parent.parent.parent
        config_dir = app_dir / "config"
        config_dir.mkdir(exist_ok=True)  # Ensure config directory exists
        users_db_path = config_dir / "users.db"
        logger.info(f"Using users database path: {users_db_path}")
        # REMOVED: Google Drive dependency from UserAuthService
        self.user_auth_service = UserAuthService.get_instance(None, self.settings_handler, str(users_db_path))
        
        # Initialize the user auth service (create admin user)
        if not self.user_auth_service.initialize():
            QMessageBox.critical(self, "Error", "Failed to initialize user authentication service")
            return
        
        # Set user auth service in database manager for change tracking
        self.db_manager.set_user_auth_service(self.user_auth_service)
        
        # Flag to track database loading operations
        self._loading_databases = False
        self._last_db_load_time = 0
        
        # Flag to track initialization phase
        self._initialization_phase = True
        
        # Flag to track Google Drive authentication completion
        self._google_drive_just_authenticated = False
        
        # Track the current screen to detect changes
        self.current_screen = None
        
        # Initialize Google Drive monitor (will be set after authentication)
        self.drive_monitor = None
        
        # Initialize the auto update handler (will be fully configured after tabs are created)
        self.auto_update_handler = None
        
        # Initialize auto-updater system
        self.auto_updater = None
        self._setup_auto_updater()
        
        # Initialize shared drive updater system
        self.shared_drive_updater = None
        self._setup_shared_drive_updater()
        
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
        
        # REMOVED: Google Drive OAuth initialization
        # Continue directly with initialization (no Google Drive check needed)
        QTimer.singleShot(100, self._finish_initialization)
        
        self.progress_dialog.setValue(40)
        self.progress_dialog.setLabelText("Setting up application menu...")
    
    # REMOVED: _check_drive_and_continue_init - Google Drive OAuth authentication
    # This method handled Google Drive login dialogs and is no longer needed
    
    def show_login_dialog(self):
        """Show the login dialog and handle authentication"""
        login_dialog = LoginDialog(self, auth_service=self.user_auth_service)
        
        # Set login mode to always require authentication
        login_dialog.set_force_login(True)
        
        # Show the dialog
        result = login_dialog.exec_()
        
        if result == QDialog.Accepted:
            # Proper user authentication completed
            self.user_auth_service.is_guest = False
            
            # Update status bar with current user
            self.update_user_status()
            
            # Login was successful
            return True
        else:
            # Dialog was rejected (Exit button)
            return False
    
    # Guest login functionality removed - all users must authenticate properly
    
    # REMOVED: handle_drive_login - Google Drive OAuth login handling
    # This method managed Google Drive authentication flows and is no longer needed
    
    # REMOVED: Google Drive OAuth authentication method
    # def authenticate_google_drive(self, force=False, interactive=True):
    #     """Authenticate with Google Drive and set up database handler"""
    #     # This method has been removed as part of OAuth 2.0 to service account transition
    #     logger.warning("Google Drive OAuth authentication is no longer supported")
    #     return False
    
    def _initialize_cloud_database_handler(self):
        """
        Initialize the appropriate cloud database handler (Shared Drive or Google Drive).
        
        Returns:
            True if a cloud handler was initialized, False otherwise
        """
        try:
            # Check if shared drive should be used and is accessible
            if self.settings_handler.get_setting("use_shared_drive", False):
                logger.info("Checking shared drive access...")
                shared_handler = SharedDriveDbHandler(self.settings_handler)
                
                if shared_handler._check_shared_drive_access():
                    logger.info("Shared drive accessible - using SharedDriveDbHandler")
                    self.cloud_db_handler = shared_handler
                    
                    # Set database manager for operations
                    self.cloud_db_handler.set_database_manager(self.db_manager)
                    # Set cloud handler in database manager for import dialogs
                    self.db_manager.set_cloud_db_handler(self.cloud_db_handler)
                    
                    return True
                else:
                    logger.warning("Shared drive not accessible - cloud features disabled")
                    self.cloud_db_handler = None
                    return False
            else:
                # REMOVED: Google Drive OAuth-based cloud handler
                # self.cloud_db_handler = CloudDatabaseHandler(self.drive_service, self.settings_handler)
                logger.info("Google Drive OAuth handlers removed - using shared drive only")
                self.cloud_db_handler = None
                return False
                    
        except Exception as e:
            logger.error(f"Error initializing cloud database handler: {e}")
            self.cloud_db_handler = None
            return False
    
    def apply_application_styling(self):
        """Apply consistent styling to the application."""
        # Apply platform-specific styling
        app = QApplication.instance()
        if app:
            StyleHandler.apply_application_style(app)
    
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
        
        # Create header with application title and help button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        # Add spacer to center the title
        header_layout.addStretch()
        
        title_label = QLabel("Water Level Monitoring System")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #3070B0;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Add spacer to center the title
        header_layout.addStretch()
        
        # Add feedback button (shown when Google Drive credentials are set)
        self.feedback_btn = QPushButton("📝 Feedback")
        self.feedback_btn.setMaximumWidth(100)
        self.feedback_btn.setMaximumHeight(30)
        self.feedback_btn.setToolTip("Submit feedback or bug reports")
        self.feedback_btn.clicked.connect(self.open_feedback_dialog)
        self.feedback_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #007bff;
                border-radius: 4px;
                background-color: #007bff;
                color: white;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
        """)
        # Initially hidden, shown when Google Drive credentials are set
        self.feedback_btn.setVisible(False)
        header_layout.addWidget(self.feedback_btn)
        
        # Add help button on the right
        self.help_btn = QPushButton("❓ Help")
        self.help_btn.setMaximumWidth(80)
        self.help_btn.setMaximumHeight(30)
        self.help_btn.setToolTip("Open help system")
        self.help_btn.clicked.connect(self.open_help_system)
        self.help_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        header_layout.addWidget(self.help_btn)
        
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
        self.db_combo.setMaxVisibleItems(10)  # Show up to 10 items without scrolling
        
        # Fix the dropdown visibility issue - make items visible
        self.db_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #AAAAAA;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: white;
                color: black;
            }
            QComboBox:hover {
                border: 1px solid #3070B0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #3070B0;
                selection-color: white;
                border: 1px solid #AAAAAA;
                max-height: 300px;
            }
            QComboBox QAbstractItemView::item {
                color: black;
                background-color: white;
                min-height: 25px;
                padding: 3px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #E0E0E0;
                color: black;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3070B0;
                color: white;
            }
        """)

        self._db_combo_connection = None
        self._connect_db_combo()
        

        # Style the buttons
        self.new_db_btn = QPushButton("New")
        self.new_db_btn.setStyleSheet(StyleHandler.get_action_button_style())
        self.new_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.new_db_btn.clicked.connect(self._create_new_database)
        self.new_db_btn.setToolTip("Create a new database")
        
        # Add Reload Database button
        self.reload_db_btn = QPushButton("Reload")
        self.reload_db_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.reload_db_btn.clicked.connect(self._reload_database)
        self.reload_db_btn.setToolTip("Reload the current database from disk")
        self.reload_db_btn.setEnabled(False)  # Initially disabled until a database is selected
        self._update_reload_button_style()
        
        # Add Save to SMOO button (initially hidden)
        self.save_cloud_btn = QPushButton("Save to SMOO")
        self.save_cloud_btn.setStyleSheet("""
            background-color: #2E7D32;
            color: white;
            border: 1px solid #1B5E20;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 13px;
            min-height: 20px;
        """)
        self.save_cloud_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.save_cloud_btn.clicked.connect(self._save_to_cloud)
        self.save_cloud_btn.setToolTip("Save changes to the cloud database")
        self.save_cloud_btn.setVisible(False)
        
        # Add Compare Changes button (initially hidden)
        self.compare_changes_btn = QPushButton("Compare Changes")
        self.compare_changes_btn.setStyleSheet("""
            background-color: #2196F3;
            color: white;
            border: 1px solid #1976D2;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 13px;
            min-height: 20px;
        """)
        self.compare_changes_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.compare_changes_btn.clicked.connect(self._compare_changes)
        self.compare_changes_btn.setToolTip("Compare local changes against cloud database")
        self.compare_changes_btn.setVisible(False)
        
        # Add Create Local Copy button (initially hidden)
        self.create_local_copy_btn = QPushButton("Create Local Copy")
        self.create_local_copy_btn.setStyleSheet("""
            background-color: #FF9800;
            color: white;
            border: 1px solid #F57C00;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 13px;
            min-height: 20px;
        """)
        self.create_local_copy_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.create_local_copy_btn.clicked.connect(self._create_local_copy)
        self.create_local_copy_btn.setToolTip("Create a permanent local copy of this cloud database")
        self.create_local_copy_btn.setVisible(False)

        # Add buttons to layout
        db_layout.addWidget(self.db_combo)
        db_layout.addWidget(self.reload_db_btn)
        db_layout.addWidget(self.new_db_btn)
        db_layout.addWidget(self.save_cloud_btn)
        db_layout.addWidget(self.compare_changes_btn)
        db_layout.addWidget(self.create_local_copy_btn)

        main_layout.addLayout(db_layout)
        
        # Load available databases but don't select any by default
        # Only load local databases during setup - cloud databases will be loaded after authentication
        self._load_local_databases_only()
        
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
        self._add_recharge_tab()
        self._add_geophysical_data_tab()
        self._add_water_level_runs_tab()
        
        # Initially disable runs tab and style it appropriately (no database loaded)
        self.tab_widget.setTabEnabled(5, False)  # Runs tab is now index 5
        self._update_runs_tab_style(False)
        
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
        
        # Add cloud mode indicator
        self.cloud_mode_label = QLabel("")
        self.cloud_mode_label.setStyleSheet("""
            font-weight: bold;
            color: #2E7D32;
            padding-right: 10px;
        """)
        self.status_bar.addPermanentWidget(self.cloud_mode_label)
        
        # Add folder info to status bar
        import os  # ensure os is available
        initial_folder = self.settings_handler.get_setting("local_db_directory", "")
        folder_text = self._get_display_path(initial_folder if os.path.isdir(initial_folder) else "")
        self.folder_info_label = QLabel(f"Folder: {folder_text}")
        self.folder_info_label.setStyleSheet("""
            font-weight: bold;
            color: #3070B0;
            padding-right: 5px;
        """)
        self.folder_info_label.setToolTip(f"Database folder: {initial_folder}")
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
            
    def _get_display_path(self, full_path):
        """Get a user-friendly display path by showing only the relative portion"""
        if not full_path:
            return "No folder selected"
            
        try:
            from pathlib import Path
            path = Path(full_path)
            
            # Try to get relative path from user's home directory
            try:
                home = Path.home()
                rel_path = path.relative_to(home)
                return f"~/{rel_path}"
            except ValueError:
                pass
            
            # If not under home, try to show just the last few directories
            parts = path.parts
            if len(parts) > 3:
                return f".../{'/'.join(parts[-3:])}"
            else:
                return str(path)
                
        except Exception:
            # Fallback to original path if anything goes wrong
            return full_path

    def _load_local_databases_only(self):
        """Load only local databases during initial UI setup."""
        self.db_combo.clear()
        
        # Load local databases
        local_db_files = [db for db in Path().glob("*.db") if "_(drive)" not in db.name]
        
        if local_db_files:
            self.db_combo.addItem("-- Local Databases --")
            for db_file in local_db_files:
                self.db_combo.addItem(f"LOCAL: {db_file.name}")
        else:
            self.db_combo.addItem("No local databases found")
            self.db_combo.setEnabled(False)
    
    def _load_databases(self):
        """Load available databases into the combo box."""
        # Prevent duplicate concurrent loading
        if self._loading_databases:
            logger.debug("Database loading already in progress, skipping duplicate call")
            return
            
        # Set the loading flag
        self._loading_databases = True
        
        # Disconnect signals temporarily to prevent cascading events
        self._disconnect_db_combo()
        
        try:
            self.db_combo.clear()
            
            # Load local databases from configured directory
            app_dir = Path(__file__).parent.parent.parent
            local_db_directory = Path(self.settings_handler.get_setting("local_db_directory", str(app_dir)))
            if local_db_directory.exists():
                local_db_files = [db for db in local_db_directory.glob("*.db") if "_(drive)" not in db.name]
            else:
                logger.warning(f"Database directory does not exist: {local_db_directory}")
                logger.warning(f"App directory: {app_dir}")
                logger.warning(f"Database directory setting: {self.settings_handler.get_setting('local_db_directory', 'NOT_FOUND')}")
                logger.warning(f"Absolute path would be: {local_db_directory.resolve()}")
                local_db_files = []
            has_databases = False
            
            # Add local databases section
            if local_db_files:
                self.db_combo.addItem("-- Local Databases --")
                for db_file in local_db_files:
                    self.db_combo.addItem(f"LOCAL: {db_file.name}")
                    logger.debug(f"Added local database to dropdown: {db_file.name}")
                has_databases = True
            
            # Add cloud databases section
            if self.cloud_db_handler:
                try:
                    logger.info("Loading cloud projects...")
                    
                    # Check if cloud handler is available and can access projects
                    cloud_accessible = False
                    if hasattr(self.cloud_db_handler, 'drive_service'):
                        # Google Drive handler
                        cloud_accessible = (hasattr(self.cloud_db_handler.drive_service, 'authenticated') and 
                                          self.cloud_db_handler.drive_service.authenticated)
                    else:
                        # Shared Drive handler - always accessible if initialized
                        cloud_accessible = True
                    
                    if cloud_accessible:
                        logger.info("Cloud service accessible, fetching projects...")
                        cloud_projects = self.cloud_db_handler.list_projects()
                        if cloud_projects:
                            logger.info(f"Found {len(cloud_projects)} cloud projects")
                            if has_databases:
                                self.db_combo.insertSeparator(self.db_combo.count())
                            self.db_combo.addItem("-- Cloud Projects --")
                            for project in cloud_projects:
                                locked_indicator = " (LOCKED)" if project.get('locked_by') else ""
                                self.db_combo.addItem(f"CLOUD: {project['name']}{locked_indicator}")
                                logger.info(f"Added cloud project to dropdown: {project['name']} (Database: {project['database_name']})")
                            has_databases = True
                        else:
                            logger.info("No cloud projects found")
                    else:
                        logger.warning("Drive service not authenticated - skipping cloud projects")
                except Exception as e:
                    logger.error(f"Error loading cloud projects: {e}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
            else:
                logger.warning("Cloud database handler is None - cannot load cloud projects")
            
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
                
                # Find and select the item - check for LOCAL: prefix first
                prefixed_name = f"LOCAL: {current_db_name}"
                index = self.db_combo.findText(prefixed_name)
                if index >= 0:
                    self.db_combo.setCurrentIndex(index)
                    logger.debug(f"Selected database in dropdown at index {index}: {prefixed_name}")
                else:
                    # Fallback: try cloud database format or exact match
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
        import traceback
        start_time = time.time()
        logger.info(f"PERF: Starting database change handling for {db_name}")
        
        if not db_name or db_name == "No databases found" or db_name.startswith("--"):
            # No valid database selected - disable reload button
            self.reload_db_btn.setEnabled(False)
            self._update_reload_button_style()
            return
            
        # If we're already loading databases or the combo box triggered this change, don't process further
        if self._loading_databases:
            return
            
        try:
            # Parse database name to determine type
            is_local_db = db_name.startswith("LOCAL: ")
            is_cloud_db = db_name.startswith("CLOUD: ")
            is_drive_db = "_(drive)" in db_name
            
            if is_local_db:
                clean_db_name = db_name[7:].strip()  # Remove "LOCAL: " prefix and strip spaces
                self._open_local_database(clean_db_name, start_time)
                return
            elif is_cloud_db:
                clean_project_name = db_name[7:].replace(" (LOCKED)", "").strip()  # Remove "CLOUD: " prefix and lock indicator, then strip spaces
                self._open_cloud_database(clean_project_name, start_time)
                return
            else:
                # Fallback for old format (without emojis)
                # Check if the database is already open
                current_db_name = self.db_manager.current_db.name if self.db_manager.current_db else None
                if current_db_name and current_db_name == db_name:
                    logger.info(f"PERF: Database {db_name} is already open, skipping")
                    return
            
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
            if not db_name:
                logger.error("DEBUG: _on_database_changed db_name is None/empty!")
                progress_dialog.complete()
                return
                
            logger.debug(f"DEBUG: _on_database_changed checking db_name: {repr(db_name)}")
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
                
                # Double-check db_name before creating path
                if not db_name:
                    logger.error("DEBUG: db_name is None/empty in open_database call!")
                    raise ValueError("Database name cannot be None or empty")
                    
                db_file_path = str(Path() / db_name)
                logger.debug(f"DEBUG: _on_database_changed calling open_database with: {repr(db_file_path)}")
                
                if 'quick_validation' in sig.parameters:
                    self.db_manager.open_database(db_file_path, quick_validation=is_large_db)
                else:
                    # Use the original method if quick_validation is not supported
                    self.db_manager.open_database(db_file_path)
                
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
            
            # Don't reload here - it causes issues
            
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
                
                # For cloud databases, look for the cloud project name in dropdown
                if self.db_manager.is_cloud_database and hasattr(self.db_manager, 'cloud_project_name'):
                    cloud_display_name = f"CLOUD: {self.db_manager.cloud_project_name}"
                    index = self.db_combo.findText(cloud_display_name)
                else:
                    # For local databases, find by exact name
                    local_display_name = f"LOCAL: {current_db_name}"
                    index = self.db_combo.findText(local_display_name)
                    if index < 0:
                        # Fallback to just the name
                        index = self.db_combo.findText(current_db_name)
                
                if index >= 0:
                    self.db_combo.setCurrentIndex(index)
                else:
                    self.db_combo.setCurrentIndex(-1)
            else:
                self.db_combo.setCurrentIndex(-1)
            self._loading_databases = False
        except Exception as e:
            logger.error(f"Error in _on_database_changed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Disable reload button on error
            self.reload_db_btn.setEnabled(False)
            self._update_reload_button_style()
            QMessageBox.critical(self, "Database Error", f"Failed to open database: {e}")

    def _open_local_database(self, db_name: str, start_time: float):
        """Open a local database"""
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
            return
        
        # Reset cloud state
        self.db_manager.reset_cloud_state()
        self._update_cloud_ui(False)
        
        # Show progress dialog
        progress_dialog.show(f"Opening database: {db_name}", "Loading Database")
        progress_dialog.update(5, "Initializing database connection...")
        QApplication.processEvents()
        
        # Open the database using the configured database directory
        # Use app directory instead of current working directory
        app_dir = Path(__file__).parent.parent.parent
        local_db_directory = Path(self.settings_handler.get_setting("local_db_directory", str(app_dir)))
        db_path = local_db_directory / db_name
        self.db_manager.open_database(db_path)
        
        # Update UI
        self._complete_database_opening(db_name, start_time)
        
    def _open_cloud_database(self, project_name: str, start_time: float):
        """Open a cloud database"""
        logger.info(f"Attempting to open cloud database: {project_name}")
        if not self.cloud_db_handler:
            logger.error("Cloud database handler not available")
            QMessageBox.warning(self, "Cloud Not Available", 
                              "Cloud database functionality is not available.")
            return
            
        # Check for unsaved changes in current cloud database
        if (self.db_manager.is_cloud_database and 
            self.db_manager.is_cloud_modified):
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes in the current cloud database.\n"
                "Do you want to save before switching?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                if not self._save_to_cloud():
                    return  # Save failed, don't switch
            elif reply == QMessageBox.Cancel:
                return
                
        # Get project info
        cloud_projects = self.cloud_db_handler.list_projects()
        project_info = None
        for project in cloud_projects:
            if project['name'] == project_name:
                project_info = project
                break
                
        if not project_info:
            QMessageBox.warning(self, "Project Not Found", 
                              f"Cloud project '{project_name}' not found.")
            return
        
        
        # Check for existing draft
        has_draft = self.cloud_db_handler.has_draft(project_name)
        prefer_draft = False
        
        if has_draft:
            draft_info = self.cloud_db_handler.get_draft_info(project_name)
            
            # Show enhanced draft selection dialog
            dialog = DraftSelectionDialog(
                project_name,
                draft_info,
                project_info,
                self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                selection = dialog.get_selection()
                if selection == 'draft':
                    prefer_draft = True
                elif selection == 'cloud':
                    prefer_draft = False
                    # Clear the draft since user chose to download fresh
                    self.cloud_db_handler.clear_draft(project_name)
            else:
                # User cancelled
                return
            
        # Note: No lock checking needed for downloading - locks are only for collaborative editing
        # We'll check/acquire locks when the user tries to save changes back to cloud
        
        
        # Smart version tracking - check if we can use local cache
        force_download = False  # Track if user chose to force download
        logger.info(f"Version checking: prefer_draft={prefer_draft}")
        if not prefer_draft:  # Only check cache if not using draft
            cloud_version_time = project_info.get('modified_time', '')
            logger.info(f"Checking version status for {project_name} with cloud time: {cloud_version_time}")
            version_comparison = self.cloud_db_handler.check_version_status(project_name, cloud_version_time)
            logger.info(f"Version comparison result: {version_comparison}")
            
            # If we have a valid local cache, show version choice dialog
            local_db_exists = version_comparison.get('local_db_exists', False)
            logger.info(f"local_db_exists flag: {local_db_exists}")
            if local_db_exists:
                from .dialogs.version_choice_dialog import VersionChoiceDialog
                
                version_dialog = VersionChoiceDialog(
                    project_name,
                    version_comparison,
                    self
                )
                
                if version_dialog.exec_() == QDialog.Accepted:
                    choice = version_dialog.get_choice()
                    if choice == "use_cache":
                        # Use local database instead of downloading (working database has priority over cache)
                        db_type = version_comparison.get('db_type', 'cache')
                        
                        if db_type in ['working', 'working_outdated']:
                            # Use working database
                            working_db_path = version_comparison.get('working_db_path')
                            if working_db_path and os.path.exists(working_db_path):
                                logger.info(f"Using preserved working database: {working_db_path}")
                                if db_type == 'working_outdated':
                                    logger.warning(f"Working database is outdated but user chose to continue with it")
                                cached_path = working_db_path
                            else:
                                # Fallback to regular cache if working database missing
                                cached_path = self.cloud_db_handler.get_cached_database_path(project_name)
                                logger.info(f"Working database missing, using cached database: {cached_path}")
                        else:
                            # Use regular cache
                            cached_path = self.cloud_db_handler.get_cached_database_path(project_name)
                            logger.info(f"Using cached database: {cached_path}")
                        
                        if cached_path:
                            
                            # Show brief progress
                            progress_dialog.show(f"Loading cached database: {project_name}", "Loading Cache")
                            
                            # Make sure progress dialog stays on top
                            if progress_dialog.progress_dialog:
                                progress_dialog.progress_dialog.setWindowFlags(
                                    progress_dialog.progress_dialog.windowFlags() | Qt.WindowStaysOnTopHint
                                )
                                progress_dialog.progress_dialog.show()
                            
                            progress_dialog.update(50, "Opening cached database...")
                            QApplication.processEvents()
                            
                            # Open the cached database
                            self.db_manager.open_cloud_database(cached_path, project_name, project_info)
                            self.db_manager.cloud_download_time = version_comparison.get('local_time', '')
                            
                            # Update UI
                            self._update_cloud_ui(True, project_name)
                            
                            # Determine display name and complete opening
                            version_status = version_comparison.get('message', '')
                            if version_comparison.get('status') == 'current':
                                display_name = f"{project_name} (Cloud - Latest)"
                            else:
                                display_name = f"{project_name} (Cloud - Cached)"
                            
                            progress_dialog.update(100, "Cache loaded successfully!")
                            QApplication.processEvents()
                            progress_dialog.close()
                            
                            # Complete opening
                            self._complete_database_opening(display_name, start_time)
                            
                            # Add version status to cloud label
                            self.cloud_mode_label.setText(f"SMOO: {project_name} - {version_status}")
                            return
                    elif choice == "download_fresh":
                        # User explicitly chose to download fresh - bypass automatic cache
                        force_download = True
                        logger.info(f"User chose to download fresh, bypassing cache for {project_name}")
                else:
                    # User cancelled version choice
                    logger.info("User cancelled version choice dialog")
                    return
            else:
                logger.info("No local database exists, proceeding with direct download")
            # If no local cache available, proceed with direct download
        else:
            logger.info("Skipping version check due to draft preference")
            
        # Show progress dialog for download
        progress_dialog.show(f"Opening cloud project: {project_name}", "Loading Cloud Database")
        
        # Make sure progress dialog stays on top
        if progress_dialog.progress_dialog:
            progress_dialog.progress_dialog.setWindowFlags(
                progress_dialog.progress_dialog.windowFlags() | Qt.WindowStaysOnTopHint
            )
            progress_dialog.progress_dialog.show()
        
        # Check if we're loading draft or downloading from cloud
        if prefer_draft and self.cloud_db_handler.has_draft(project_name):
            progress_dialog.update(10, f"Loading draft for {project_name}...")
            logger.info(f"Loading draft for project {project_name}")
            logger.info(f"Starting draft load...")
        else:
            progress_dialog.update(10, f"Downloading {project_info['database_name']}...")
            logger.info(f"Downloading cloud database: {project_info['database_name']} from project {project_name}")
            logger.info(f"Starting download of {project_info['database_name']}...")
        
        QApplication.processEvents()
        
        # Create progress callback to update UI
        def download_progress_callback(progress_percent, status_message):
            # Map download progress (0-100%) to overall progress (10-80%)
            overall_progress = 10 + int(progress_percent * 0.7)  # 70% of total progress for download
            progress_dialog.update(overall_progress, status_message)
            QApplication.processEvents()
        
        temp_path = self.cloud_db_handler.download_database(project_name, project_info, download_progress_callback, prefer_draft, force_download)
        if not temp_path:
            progress_dialog.close()
            if prefer_draft and self.cloud_db_handler.has_draft(project_name):
                logger.error("Draft load failed - no temporary path returned")
                QMessageBox.critical(self, "Draft Load Failed", 
                                   "Failed to load draft database.")
            else:
                logger.error("Download failed - no temporary path returned")
                QMessageBox.critical(self, "Download Failed", 
                                   "Failed to download cloud database.")
            return
            
        # Log appropriate success message
        if prefer_draft and self.cloud_db_handler.has_draft(project_name):
            logger.info(f"Draft loaded successfully to: {temp_path}")
        else:
            logger.info(f"Cloud database downloaded successfully to: {temp_path}")
        progress_dialog.update(85, "Opening database...")
        QApplication.processEvents()
        
        # Open as cloud database
        self.db_manager.open_cloud_database(temp_path, project_name, project_info)
        
        # Store download time for draft version tracking
        self.db_manager.cloud_download_time = project_info.get('modified_time', '')
        
        # Create session backup of the original downloaded database
        if not prefer_draft:  # Only create original backup for fresh downloads, not draft loads
            self.cloud_db_handler.create_session_backup(
                project_name, temp_path, 'original'
            )
            logger.info(f"Created original session backup for: {project_name}")
        
        # Update version tracking for downloaded database
        if not prefer_draft:  # Only track downloads, not draft loads
            cloud_version_time = project_info.get('modified_time', '')
            self.cloud_db_handler.update_local_version_tracking(
                project_name, cloud_version_time, temp_path, "download"
            )
            logger.info(f"Updated version tracking for downloaded database: {project_name}")
            
            # Ensure working database is preserved and not cleaned up
            self.cloud_db_handler.ensure_working_database_preserved(project_name)
        
        # If we loaded a draft, set the correct modification states
        if prefer_draft and has_draft:
            # FIXED: Set proper draft state tracking
            self.db_manager.is_cloud_modified = True     # Draft has changes vs cloud (enables Upload)
            self.db_manager.is_loaded_from_draft = True  # Track that we loaded from draft
            self.db_manager.is_draft_modified = False    # No NEW changes vs draft yet
            
            # Store the existing draft changes description for later use
            self.db_manager.draft_changes_description = draft_info.get('changes_description', '')
            logger.info("Draft loaded - enabled upload (has changes vs cloud), but no new changes vs draft yet")
        else:
            # Clear draft state if not loading a draft
            self.db_manager.is_loaded_from_draft = False
            self.db_manager.is_draft_modified = False
            self.db_manager.draft_changes_description = None
        
        # Update UI for cloud mode
        self._update_cloud_ui(True, project_name)
        
        # Determine display name based on whether draft was loaded
        if prefer_draft and has_draft:
            display_name = f"{project_name} (Draft)"
            # Update UI to show draft state with modifications
            self.save_cloud_btn.setEnabled(True)
            self.compare_changes_btn.setEnabled(True)
            self.cloud_mode_label.setText(f"SMOO: {project_name} (Draft - Has Changes)")
        else:
            display_name = f"{project_name} (Cloud)"
        
        # Complete opening
        self._complete_database_opening(display_name, start_time)
        
    def _complete_database_opening(self, display_name: str, start_time: float):
        """Complete the database opening process"""
        # Update progress for tab loading (adjust for cloud vs local)
        is_cloud = "(Cloud)" in display_name
        initial_progress = 85 if is_cloud else 60  # Cloud databases start at 85% due to download
        
        # Rebuild XLE tracking now that database is fully loaded (important for drafts)
        if is_cloud and self.cloud_db_handler:
            project_name = display_name.replace(" (Cloud)", "").replace(" (Draft)", "")
            logger.info(f"Calling XLE tracking rebuild for project: '{project_name}'")
            self.cloud_db_handler.rebuild_xle_tracking_after_database_load(project_name)
        
        # Update window title
        self.setWindowTitle(f"Water Level Monitoring - {display_name}")
        
        # Update database info in status bar
        self.db_info_label.setText(f"Database: {display_name}")
        
        # Enable tabs and load data - use correct method names
        logger.info("Loading database tab...")
        if "database" in self._tabs:
            try:
                self._tabs["database"].refresh_data()
            except Exception as e:
                logger.debug(f"Database tab refresh: {e}")
        
        logger.info("Loading barologger tab...")
        if "barologger" in self._tabs:
            try:
                self._tabs["barologger"].refresh_data()
            except Exception as e:
                logger.debug(f"Barologger tab refresh: {e}")
        
        logger.info("Loading water level tab...")
        if "water_level" in self._tabs:
            try:
                self._tabs["water_level"].refresh_data()
            except Exception as e:
                logger.debug(f"Water level tab refresh: {e}")
        
        logger.info("Loading recharge tab...")
        if "recharge" in self._tabs:
            try:
                self._tabs["recharge"].sync_database_selection("CAESER_GENERAL")
            except Exception as e:
                logger.debug(f"Recharge tab refresh: {e}")
        
        # For cloud databases, enable runs tab
        if self.db_manager.is_cloud_database:
            logger.info("Loading runs tab...")
            if "water_level_runs" in self._tabs:
                try:
                    self._tabs["water_level_runs"].refresh_data()
                except Exception as e:
                    logger.debug(f"Runs tab refresh: {e}")
            self.tab_widget.setTabEnabled(5, True)  # Enable runs tab
            self._update_runs_tab_style(True)  # Style as enabled/cloud
        else:
            self.tab_widget.setTabEnabled(5, False)  # Disable runs tab for local
            self._update_runs_tab_style(False)  # Style as disabled/local
        
        # Enable the other tabs
        for i in range(5):  # Database, Barologger, Water Level, Recharge, Geophysical Data tabs
            self.tab_widget.setTabEnabled(i, True)
        
        # Enable reload button now that a database is loaded
        self.reload_db_btn.setEnabled(True)
        self._update_reload_button_style()
        
        total_time = time.time() - start_time
        logger.info(f"PERF: Total database change time: {total_time*1000:.2f}ms")
        logger.info("Database loaded successfully")
        
        # Close the progress dialog if it's still open
        try:
            if progress_dialog.progress_dialog and progress_dialog.progress_dialog.isVisible():
                progress_dialog.close()
        except Exception as e:
            logger.debug(f"Progress dialog was already closed: {e}")
        
    def _update_reload_button_style(self):
        """Update reload button styling based on enabled/disabled state"""
        if self.reload_db_btn.isEnabled():
            # Enabled state - clear blue theme
            self.reload_db_btn.setStyleSheet(StyleHandler.get_action_button_style())
        else:
            # Disabled state - grayed out appearance
            self.reload_db_btn.setStyleSheet("""
                background-color: #f5f5f5;
                color: #a0a0a0;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 400;
                font-size: 13px;
                min-height: 20px;
            """)
    
    def _update_cloud_ui(self, is_cloud: bool, project_name: str = None):
        """Update UI elements for cloud mode"""
        if is_cloud:
            self.save_cloud_btn.setVisible(True)
            self.save_cloud_btn.setEnabled(False)  # Initially disabled
            self.compare_changes_btn.setVisible(True)
            self.compare_changes_btn.setEnabled(False)  # Initially disabled
            self.create_local_copy_btn.setVisible(True)
            self.create_local_copy_btn.setEnabled(True)  # Always enabled for cloud databases
            self.cloud_mode_label.setText(f"SMOO: {project_name}")
        else:
            self.save_cloud_btn.setVisible(False)
            self.compare_changes_btn.setVisible(False)
            self.create_local_copy_btn.setVisible(False)
            self.cloud_mode_label.setText("")
                    
    def _update_runs_tab_style(self, is_enabled: bool):
        """Update the visual style of the runs tab based on enabled/disabled state"""
        try:
            from PyQt5.QtGui import QColor
            from PyQt5.QtCore import QVariant
            
            if is_enabled:
                # Cloud database - enabled state (remove all custom styling)
                # Get the original text color from another tab (tab 0 = Wells)
                original_color = self.tab_widget.tabBar().tabTextColor(0)
                
                # Apply the same color as other tabs
                if original_color.isValid():
                    self.tab_widget.tabBar().setTabTextColor(5, original_color)
                else:
                    # Fallback: clear custom color completely
                    self.tab_widget.tabBar().setTabTextColor(5, QColor())
                
                # Clear any custom tab data
                self.tab_widget.tabBar().setTabData(5, QVariant())
                
                # Force repaint to ensure visual update
                self.tab_widget.tabBar().update()
                logger.debug("Runs tab enabled: restored to match other tabs")
            else:
                # Local database - disabled state (grayed out with different background)
                self.tab_widget.tabBar().setTabTextColor(5, QColor(150, 150, 150))  # Gray text
                self.tab_widget.tabBar().setTabData(5, "disabled")
                
                # Apply custom stylesheet for disabled state
                self._apply_runs_tab_stylesheet()
                logger.debug("Runs tab disabled: applied gray styling")
        except Exception as e:
            logger.debug(f"Error updating runs tab style: {e}")
            
    def _apply_runs_tab_stylesheet(self):
        """Apply custom stylesheet to differentiate the runs tab when disabled"""
        # Get current stylesheet and add runs tab specific styling
        current_style = self.tab_widget.styleSheet()
        
        # Add disabled runs tab styling
        runs_tab_style = """
            QTabBar::tab:disabled {
                background-color: #E8E8E8;
                color: #999999;
                border: 1px solid #CCCCCC;
            }
            QTabBar::tab:disabled:hover {
                background-color: #E0E0E0;
            }
        """
        
        # Only add the style if it's not already there
        if "QTabBar::tab:disabled" not in current_style:
            self.tab_widget.setStyleSheet(current_style + runs_tab_style)
    
    def _compare_changes(self):
        """Open the database comparison dialog"""
        try:
            if not self.db_manager.is_cloud_database:
                QMessageBox.information(self, "Information", "This feature is only available for cloud databases.")
                return
            
            if not hasattr(self, 'change_tracker') or not self.change_tracker:
                QMessageBox.warning(self, "Warning", "Change tracking is not available.")
                return
            
            # Check if there are any changes to compare
            if not self.change_tracker.changes:
                QMessageBox.information(self, "No Changes", "No local changes detected to compare.")
                return
            
            # Check if we have cloud database handler
            if not hasattr(self, 'cloud_db_handler') or not self.cloud_db_handler:
                QMessageBox.warning(self, "Warning", "Cloud database handler is not available.")
                return
            
            # Check if user is authenticated
            if not hasattr(self, 'user_auth_service') or not self.user_auth_service.current_user:
                QMessageBox.warning(self, "Warning", "Please log in first.")
                return
            
            # Open the comparison dialog - TEMPORARILY DISABLED
            # dialog = DatabaseComparisonDialog(
            #     self.db_manager,
            #     self.change_tracker,
            #     self.cloud_db_handler,
            #     self.user_auth_service,
            #     self
            # )
            # 
            # # Show dialog
            # result = dialog.exec_()
            # 
            # # If user accepted changes in the dialog, we could trigger save here
            # if result == QDialog.Accepted:
            
            # Temporary workaround - show message
            QMessageBox.information(self, "Feature Temporarily Disabled", 
                                  "Database comparison feature is temporarily disabled.")
            return
                
        except Exception as e:
            logger.error(f"Error opening comparison dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open comparison dialog: {str(e)}")
            
    def _save_to_cloud(self) -> bool:
        """Save changes to cloud database"""
        if not self.db_manager.is_cloud_database:
            return False
            
        if not self.db_manager.is_cloud_modified:
            QMessageBox.information(self, "No Changes", "No changes to save.")
            return True
        
        # UPLOAD CONFLICT DETECTION: Check if cloud version has been updated since our local download
        try:
            # Get current cloud projects to check latest version
            cloud_projects = self.cloud_db_handler.list_projects()
            current_cloud_version = None
            
            for project in cloud_projects:
                if project['name'] == self.db_manager.cloud_project_name:
                    current_cloud_version = project.get('modified_time', '')
                    break
            
            if current_cloud_version and self.db_manager.cloud_download_time:
                # Compare our local base version with current cloud version
                from datetime import datetime
                try:
                    local_base_time = datetime.fromisoformat(self.db_manager.cloud_download_time.replace('Z', '+00:00'))
                    cloud_current_time = datetime.fromisoformat(current_cloud_version.replace('Z', '+00:00'))
                    
                    # If cloud is newer than our base, we have a conflict
                    if cloud_current_time > local_base_time:
                        time_diff = (cloud_current_time - local_base_time).total_seconds()
                        logger.warning(f"Upload conflict detected: Cloud version is {time_diff:.0f} seconds newer than local base")
                        
                        # Show conflict resolution dialog
                        conflict_msg = (
                            f"Upload Conflict Detected!\n\n"
                            f"The cloud database has been updated since you downloaded it:\n"
                            f"• Your local version is based on: {self.db_manager.cloud_download_time}\n"
                            f"• Current cloud version: {current_cloud_version}\n\n"
                            f"Uploading now would overwrite newer cloud changes.\n\n"
                            f"What would you like to do?"
                        )
                        
                        reply = QMessageBox()
                        reply.setIcon(QMessageBox.Warning)
                        reply.setWindowTitle("Upload Conflict")
                        reply.setText(conflict_msg)
                        
                        # Add custom buttons
                        overwrite_btn = reply.addButton("Overwrite Cloud Version", QMessageBox.ActionRole)
                        download_btn = reply.addButton("Download Latest & Merge", QMessageBox.ActionRole)
                        proposal_btn = reply.addButton("Save as Proposal", QMessageBox.ActionRole)
                        cancel_btn = reply.addButton("Cancel Upload", QMessageBox.RejectRole)
                        
                        reply.setDefaultButton(proposal_btn)  # Collaborative option as default
                        reply.exec_()
                        
                        if reply.clickedButton() == overwrite_btn:
                            logger.info("User chose to overwrite cloud version - proceeding with upload")
                            # Continue with upload
                        elif reply.clickedButton() == download_btn:
                            logger.info("User chose to download latest and merge - saving draft first")
                            # Save as draft first, then switch to cloud version
                            if self._save_as_draft_before_download():
                                # Reload the project to get latest cloud version
                                QMessageBox.information(self, "Draft Saved", 
                                    "Your changes have been saved as a draft. The latest cloud version will now be loaded.")
                                self._open_cloud_project(self.db_manager.cloud_project_name)
                            return False
                        elif reply.clickedButton() == proposal_btn:
                            logger.info("User chose to save as proposal - opening comparison dialog")
                            # Open database comparison dialog for proposal creation
                            try:
                                from .dialogs.database_comparison_dialog import DatabaseComparisonDialog
                                comparison_dialog = DatabaseComparisonDialog(
                                    self.db_manager,
                                    self.db_manager.change_tracker,
                                    self.cloud_db_handler,
                                    self.user_auth_service,
                                    self
                                )
                                comparison_dialog.exec_()
                                return False  # Don't proceed with normal upload
                            except ImportError as e:
                                logger.error(f"Database comparison dialog not available: {e}")
                                QMessageBox.critical(self, "Feature Unavailable", 
                                    "The proposal system is not available. Please try another option.")
                                return False
                            except Exception as e:
                                logger.error(f"Error opening comparison dialog: {e}")
                                QMessageBox.critical(self, "Error", 
                                    f"Failed to open proposal dialog: {str(e)}")
                                return False
                        else:  # cancel_btn or dialog closed
                            logger.info("User cancelled upload due to conflict")
                            return False
                            
                except Exception as e:
                    logger.error(f"Error parsing timestamps for conflict detection: {e}")
                    # Continue with upload if we can't determine conflict
                    
            else:
                logger.debug("No timestamp comparison available - proceeding with upload")
                
        except Exception as e:
            logger.error(f"Error checking for upload conflicts: {e}")
            # Continue with upload if conflict detection fails
            
        # Get current user
        current_user = self.user_auth_service.current_user or "Unknown User"
        
        # Show save dialog
        dialog = SaveToCloudDialog(
            self.db_manager.cloud_project_name,
            current_user,
            self.db_manager.change_tracker,
            self.db_manager.draft_changes_description,
            self
        )
        
        if dialog.exec_() != QDialog.Accepted:
            return False
            
        # Get change description
        changes_desc = dialog.get_changes_description()
        
        # Show progress with always on top
        progress_dialog.show("Saving to cloud...", "Saving Changes", cancelable=False)
        
        # Make sure progress dialog stays on top
        if progress_dialog.progress_dialog:
            progress_dialog.progress_dialog.setWindowFlags(
                progress_dialog.progress_dialog.windowFlags() | Qt.WindowStaysOnTopHint
            )
            progress_dialog.progress_dialog.show()
        
        # Create progress callback
        def save_progress_callback(progress_percent, status_message):
            progress_dialog.update(progress_percent, status_message)
            QApplication.processEvents()
        
        # Save to cloud with progress tracking
        success = self.cloud_db_handler.save_database(
            self.db_manager.cloud_project_name,
            self.db_manager.cloud_project_info,
            str(self.db_manager.current_db),  # Use current working database instead of cached
            current_user,
            changes_desc,
            self.db_manager.change_tracker,
            save_progress_callback
        )
        
        progress_dialog.close()
        
        if success:
            # Create session backup of the uploaded state
            self.cloud_db_handler.create_session_backup(
                self.db_manager.cloud_project_name,
                str(self.db_manager.current_db),  # Use current working database
                'last_uploaded'
            )
            
            # Clear change tracker since changes have been uploaded
            self.db_manager.change_tracker.clear_changes()
            
            # Update UI
            self.db_manager.is_cloud_modified = False
            self.save_cloud_btn.setEnabled(False)
            self.compare_changes_btn.setEnabled(False)
            self.cloud_mode_label.setText(f"SMOO: {self.db_manager.cloud_project_name}")
            
            # DEBUG: Verify database state after upload
            import os
            current_db_path = str(self.db_manager.current_db)
            if current_db_path and os.path.exists(current_db_path):
                file_size_after_upload = os.path.getsize(current_db_path)
                logger.info(f"UPLOAD_DEBUG: Database file size after upload: {file_size_after_upload} bytes")
                logger.info(f"UPLOAD_DEBUG: Database path after upload: {current_db_path}")
                
                # CRITICAL FIX: Remove uploaded database from cleanup list
                # The uploaded database is now our current working database and should NOT be cleaned up
                if (self.cloud_db_handler and hasattr(self.cloud_db_handler, 'temp_files') and 
                    current_db_path in self.cloud_db_handler.temp_files):
                    self.cloud_db_handler.temp_files.remove(current_db_path)
                    logger.info(f"UPLOAD_DEBUG: Removed uploaded database from cleanup list: {current_db_path}")
            else:
                logger.warning(f"UPLOAD_DEBUG: Database file not found after upload: {current_db_path}")
            
            # Clean up draft after successful upload (local DB is now current)
            if self.cloud_db_handler.has_draft(self.db_manager.cloud_project_name):
                self.cloud_db_handler.clear_draft(self.db_manager.cloud_project_name)
                logger.info(f"Draft cleaned up after successful upload for: {self.db_manager.cloud_project_name}")
            
            # Get ACTUAL Google Drive timestamp after upload (not generated timestamp)
            try:
                # Small delay to ensure Google Drive has processed the upload
                import time
                time.sleep(1)
                
                # Get fresh project list to get latest timestamps
                cloud_projects = self.cloud_db_handler.list_projects()
                actual_cloud_time = None
                for project in cloud_projects:
                    if project['name'] == self.db_manager.cloud_project_name:
                        actual_cloud_time = project.get('modified_time', '')
                        break
                
                if actual_cloud_time:
                    self.db_manager.cloud_download_time = actual_cloud_time
                    
                    # Update version tracking with ACTUAL Google Drive timestamp
                    self.cloud_db_handler.update_local_version_tracking(
                        self.db_manager.cloud_project_name, 
                        actual_cloud_time,  # Use actual Google Drive timestamp
                        str(self.db_manager.current_db),
                        "upload"
                    )
                    logger.info(f"Version tracking updated with actual Google Drive timestamp: {actual_cloud_time}")
                else:
                    logger.warning("Could not get actual Google Drive timestamp after upload - using fallback")
                    # Fallback to generated timestamp if we can't get actual one
                    from datetime import datetime
                    fallback_time = datetime.now().isoformat() + 'Z'
                    self.db_manager.cloud_download_time = fallback_time
                    self.cloud_db_handler.update_local_version_tracking(
                        self.db_manager.cloud_project_name, 
                        fallback_time,
                        str(self.db_manager.current_db),
                        "upload"
                    )
            except Exception as e:
                logger.error(f"Error getting actual timestamp after upload: {e}")
                # Fallback to generated timestamp
                from datetime import datetime
                fallback_time = datetime.now().isoformat() + 'Z'
                self.db_manager.cloud_download_time = fallback_time
                self.cloud_db_handler.update_local_version_tracking(
                    self.db_manager.cloud_project_name, 
                    fallback_time,
                    str(self.db_manager.current_db),
                    "upload"
                )
            
            logger.info("Local database is now the current cloud version - no download needed")
            
            QMessageBox.information(self, "Success", "Database saved to cloud successfully!")
            return True
        else:
            QMessageBox.critical(self, "Save Failed", "Failed to save database to cloud.")
            return False
    
    def _create_local_copy(self):
        """Create a permanent local copy of the current cloud database"""
        if not self.db_manager.is_cloud_database:
            QMessageBox.warning(self, "Not Cloud Database", "This feature is only available for cloud databases.")
            return
        
        try:
            # Get save location from user - default to databases directory
            # Use app directory instead of current working directory
            app_dir = Path(__file__).parent.parent.parent
            databases_dir = app_dir / "databases"
            databases_dir.mkdir(exist_ok=True)  # Ensure databases directory exists
            
            default_name = f"{self.db_manager.cloud_project_name}_local_copy.db"
            default_path = databases_dir / default_name
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Create Local Copy",
                str(default_path),
                "SQLite Database (*.db)"
            )
            
            if not file_path:
                return
            
            # Show confirmation dialog with details
            reply = QMessageBox.question(
                self,
                "Create Local Copy",
                f"Create a permanent local copy of the cloud database?\n\n"
                f"Cloud Project: {self.db_manager.cloud_project_name}\n"
                f"Local File: {file_path}\n\n"
                f"This will create an independent local database that you can modify \n"
                f"without affecting the cloud version. The local copy will include \n"
                f"all current data and changes.\n\n"
                f"Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Create progress dialog
            progress = QProgressDialog("Creating local copy...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            
            progress.setValue(20)
            progress.setLabelText("Copying database file...")
            QApplication.processEvents()
            
            # Copy the current cloud database file to the specified location
            shutil.copy2(str(self.db_manager.current_db), file_path)
            
            progress.setValue(60)
            progress.setLabelText("Updating database metadata...")
            QApplication.processEvents()
            
            # Update the copied database to remove cloud-specific metadata
            import sqlite3
            with sqlite3.connect(file_path) as conn:
                cursor = conn.cursor()
                
                # Remove cloud-specific metadata if it exists
                try:
                    cursor.execute("DELETE FROM metadata WHERE key LIKE 'cloud_%'")
                    cursor.execute("DELETE FROM metadata WHERE key = 'is_cloud_database'")
                    cursor.execute("DELETE FROM metadata WHERE key = 'project_name'")
                    
                    # Add local copy metadata
                    from datetime import datetime
                    cursor.execute(
                        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                        ('local_copy_created', datetime.now().isoformat())
                    )
                    cursor.execute(
                        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                        ('original_cloud_project', self.db_manager.cloud_project_name)
                    )
                    cursor.execute(
                        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                        ('copy_type', 'local_copy')
                    )
                    
                    conn.commit()
                    logger.info(f"Updated metadata for local copy: {file_path}")
                    
                except sqlite3.OperationalError as e:
                    # Metadata table might not exist, that's okay
                    logger.info(f"Metadata table not found in copied database (this is normal): {e}")
            
            progress.setValue(90)
            progress.setLabelText("Finalizing...")
            QApplication.processEvents()
            
            progress.setValue(100)
            progress.close()
            
            # Ask if user wants to open the local copy
            reply = QMessageBox.question(
                self,
                "Local Copy Created",
                f"Local copy created successfully!\n\n"
                f"Location: {file_path}\n\n"
                f"Would you like to open the local copy now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Refresh database list to include the new local copy
                self._load_databases()
                
                # Select the newly created database in the combo box
                db_filename = Path(file_path).name
                for i in range(self.db_combo.count()):
                    if self.db_combo.itemText(i) == db_filename:
                        self.db_combo.setCurrentIndex(i)
                        logger.info(f"Selected newly created local copy: {db_filename}")
                        break
            
            logger.info(f"Successfully created local copy: {file_path}")
            
        except Exception as e:
            logger.error(f"Error creating local copy: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create local copy:\n{str(e)}"
            )

    def _save_as_draft_on_close(self) -> bool:
        """Save current changes as a local draft when closing the app"""
        try:
            if not self.db_manager.is_cloud_database:
                return True
                
            project_name = self.db_manager.cloud_project_name
            
            # FIXED: Check if we actually have NEW changes vs draft
            if self.db_manager.is_loaded_from_draft and not self.db_manager.is_draft_modified:
                logger.info(f"No new changes since loading draft for {project_name} - keeping existing draft")
                return True  # Don't create duplicate draft
                
            # Get change description from change tracker
            changes_desc = ""
            if self.db_manager.change_tracker and self.db_manager.change_tracker.changes:
                changes_desc = self.db_manager.change_tracker.get_manual_changes_description()
            
            # If we loaded from draft but made new changes, update description to include previous changes
            if self.db_manager.is_loaded_from_draft and self.db_manager.draft_changes_description:
                # Combine previous draft changes with new changes
                prev_desc = self.db_manager.draft_changes_description
                if changes_desc and prev_desc:
                    changes_desc = f"{prev_desc} + NEW: {changes_desc}"
                elif prev_desc:
                    changes_desc = prev_desc
            
            # Save the draft (this will replace existing draft if we loaded from one)
            success = self.cloud_db_handler.save_as_draft(
                self.db_manager.cloud_project_name,
                str(self.db_manager.current_db),
                self.db_manager.cloud_download_time,
                changes_desc
            )
            
            if success:
                if self.db_manager.is_loaded_from_draft:
                    logger.info(f"Draft updated with new changes for project: {project_name}")
                else:
                    logger.info(f"Draft saved successfully for project: {project_name}")
                return True
            else:
                QMessageBox.warning(self, "Draft Save Failed", "Failed to save draft. Continue closing anyway?")
                return True  # Allow closing even if draft save fails
                
        except Exception as e:
            logger.error(f"Error saving draft on close: {e}")
            QMessageBox.warning(self, "Draft Save Error", f"Error saving draft: {e}. Continue closing anyway?")
            return True  # Allow closing even if draft save fails
    
    def _save_as_draft_before_download(self) -> bool:
        """Save current changes as a local draft before downloading latest cloud version"""
        try:
            if not self.db_manager.is_cloud_database:
                return True
                
            # Get change description from change tracker
            changes_desc = ""
            if self.db_manager.change_tracker and self.db_manager.change_tracker.changes:
                changes_desc = self.db_manager.change_tracker.get_manual_changes_description()
            
            # Save the draft
            success = self.cloud_db_handler.save_as_draft(
                self.db_manager.cloud_project_name,
                str(self.db_manager.current_db),
                self.db_manager.cloud_download_time,
                changes_desc
            )
            
            if success:
                logger.info(f"Draft saved before download for project: {self.db_manager.cloud_project_name}")
                return True
            else:
                QMessageBox.critical(self, "Draft Save Failed", 
                    "Failed to save your changes as a draft. Cannot proceed with downloading latest version.")
                return False
                
        except Exception as e:
            logger.error(f"Error saving draft before download: {e}")
            QMessageBox.critical(self, "Draft Save Error", 
                f"Error saving draft: {e}. Cannot proceed with downloading latest version.")
            return False

    def _sync_database(self):
        """Sync the current database with Google Drive"""
        if not self.db_manager.current_db:
            QMessageBox.warning(self, "No Database", "No database is currently open.")
            return
            
        if not self.db_manager.is_google_drive_db:
            QMessageBox.warning(self, "Local Database", 
                              "The current database is local and cannot be synced with Google Drive.")
            return
            
        # REMOVED: Google Drive OAuth authentication check
        # QMessageBox.warning(self, "Not Authenticated", "Not authenticated with Google Drive. Please log in first.")
        logger.warning("Google Drive OAuth authentication removed - manual sync disabled")
            
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
    
    def _restore_to_last_upload(self) -> bool:
        """Restore database to the last uploaded state."""
        try:
            project_name = self.db_manager.cloud_project_name
            last_uploaded_path = self.cloud_db_handler.get_session_backup_path(
                project_name, 'last_uploaded'
            )
            
            if not last_uploaded_path:
                QMessageBox.warning(self, "No Backup", 
                    "No last uploaded backup available.")
                return False
            
            # Copy the backup over the current database
            import shutil
            shutil.copy2(last_uploaded_path, str(self.db_manager.current_db))
            
            # Reset modification state
            self.db_manager.is_cloud_modified = False
            self.db_manager.change_tracker.clear_changes()
            
            QMessageBox.information(self, "Restored", 
                "Database restored to last uploaded state.")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring to last upload: {e}")
            QMessageBox.critical(self, "Restore Failed", 
                f"Failed to restore database: {str(e)}")
            return False
    
    def _restore_to_original(self) -> bool:
        """Restore database to the original downloaded state."""
        try:
            project_name = self.db_manager.cloud_project_name
            original_path = self.cloud_db_handler.get_session_backup_path(
                project_name, 'original'
            )
            
            if not original_path:
                QMessageBox.warning(self, "No Backup", 
                    "No original backup available.")
                return False
            
            # Copy the backup over the current database
            import shutil
            shutil.copy2(original_path, str(self.db_manager.current_db))
            
            # Reset modification state
            self.db_manager.is_cloud_modified = False
            self.db_manager.change_tracker.clear_changes()
            
            QMessageBox.information(self, "Restored", 
                "Database restored to original downloaded state.")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring to original: {e}")
            QMessageBox.critical(self, "Restore Failed", 
                f"Failed to restore database: {str(e)}")
            return False
    
    def _discard_working_changes(self) -> bool:
        """Discard working changes by completely closing connections and deleting working files."""
        try:
            import os
            import time
            
            project_name = self.db_manager.cloud_project_name
            current_db_path = str(self.db_manager.current_db)
            
            # STEP 1: Completely disconnect from database
            logger.info("Discarding working changes - completely closing database")
            
            # Reset models first (they hold connections)
            self.db_manager._well_model = None
            self.db_manager._water_level_model = None
            self.db_manager._baro_model = None
            self.db_manager._user_repository = None
            
            # Close all connections in the pool
            self.db_manager.close()
            
            # Reset current database reference  
            self.db_manager.current_db = None
            
            # Give Windows a moment to release file handles and force garbage collection
            import gc
            gc.collect()  # Force garbage collection to ensure connections are cleaned up
            time.sleep(0.3)  # Increased wait time for Windows to release handles
            
            # STEP 2: Delete working database files with retry logic
            if current_db_path and "wlm_" in os.path.basename(current_db_path):
                files_to_remove = [
                    current_db_path + "-shm",  # Delete shm first
                    current_db_path + "-wal",  # Then wal
                    current_db_path           # Main database last
                ]
                
                for file_path in files_to_remove:
                    if not os.path.exists(file_path):
                        continue
                        
                    # Retry logic for Windows file locking
                    success = False
                    max_retries = 5
                    
                    for attempt in range(max_retries):
                        try:
                            os.remove(file_path)
                            logger.info(f"Successfully deleted working database file: {file_path}")
                            success = True
                            break
                        except PermissionError as perm_e:
                            if attempt < max_retries - 1:
                                wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                                logger.debug(f"File locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                logger.warning(f"Could not remove {file_path} after {max_retries} attempts: {perm_e} - file may still be in use")
                        except Exception as other_e:
                            logger.warning(f"Could not remove {file_path}: {other_e}")
                            break
                    
                    if success:
                        # Small delay between files to let Windows release handles
                        time.sleep(0.05)
            
            # STEP 3: Reset cloud state
            self.db_manager.reset_cloud_state()
            
            logger.info("Successfully discarded working changes and deleted working files")
            return True
            
        except Exception as e:
            logger.error(f"Error discarding working changes: {e}")
            return False

    def closeEvent(self, event):
        """Handle application close event with proper cleanup."""
        try:
            # Check for unsaved cloud database changes
            if (hasattr(self, 'db_manager') and self.db_manager and 
                self.db_manager.is_cloud_database and self.db_manager.is_cloud_modified):
                
                # FIXED: Skip dialog if loaded from draft but no new changes made
                logger.info(f"DRAFT_DEBUG: is_loaded_from_draft={self.db_manager.is_loaded_from_draft}, is_draft_modified={self.db_manager.is_draft_modified}")
                if (self.db_manager.is_loaded_from_draft and not self.db_manager.is_draft_modified):
                    logger.info("Loaded from draft with no new changes - closing without dialog")
                    # Still call the cleanup to log the "keeping existing draft" message
                    self._save_as_draft_on_close()
                    event.accept()
                    return
                
                # Enhanced logic: Check what kind of changes we have
                project_name = self.db_manager.cloud_project_name
                current_db_path = str(self.db_manager.current_db)
                
                # Check if we have changes since last upload vs since download
                has_changes_since_upload = self.cloud_db_handler.has_session_changes_since_upload(
                    project_name, current_db_path
                )
                has_changes_since_download = self.cloud_db_handler.has_session_changes_since_download(
                    project_name, current_db_path
                )
                
                # Determine dialog type based on session state
                if has_changes_since_upload:
                    # User uploaded during session but made more changes
                    from .dialogs.enhanced_save_options_dialog import EnhancedSaveOptionsDialog
                    
                    dialog = EnhancedSaveOptionsDialog(
                        project_name,
                        self.db_manager.change_tracker,
                        self.cloud_db_handler,
                        "changes_since_upload",
                        self
                    )
                else:
                    # Regular unsaved changes since download
                    from .dialogs.save_options_dialog import SaveOptionsDialog
                    
                    dialog = SaveOptionsDialog(
                        self.db_manager.cloud_project_name,
                        self.db_manager.change_tracker,
                        self
                    )
                
                result = dialog.exec_()
                if result != QDialog.Accepted:
                    # User cancelled
                    event.ignore()
                    return
                    
                choice = dialog.get_choice()
                if choice == "save_cloud":
                    # Save to cloud before closing
                    if not self._save_to_cloud():
                        event.ignore()
                        return
                elif choice == "save_draft":
                    # Save as local draft
                    if not self._save_as_draft_on_close():
                        event.ignore()
                        return
                elif choice == "restore_upload":
                    # Restore to last uploaded state (new option)
                    if not self._restore_to_last_upload():
                        event.ignore()
                        return
                elif choice == "restore_original":
                    # Restore to original downloaded state (new option)
                    if not self._restore_to_original():
                        event.ignore()
                        return
                elif choice == "discard":
                    # Discard changes: clean up working copy, keep only cached database
                    if not self._discard_working_changes():
                        event.ignore()
                        return
            
            # Clean up cloud database resources with enhanced cleanup
            if hasattr(self, 'cloud_db_handler') and self.cloud_db_handler:
                # Close database connections before cleanup
                logger.info("Closing database connections before cleanup")
                if hasattr(self, 'db_manager') and self.db_manager:
                    self.db_manager.close()
                    
                # Force garbage collection to ensure all connections are released
                import gc, time
                gc.collect()
                time.sleep(0.2)  # Give Windows time to release file handles
                
                # Enhanced cleanup with force cleanup of working databases
                self.cloud_db_handler.cleanup_temp_files(force_cleanup_working_dbs=True)
                # Clean up session backups
                self.cloud_db_handler.cleanup_session_backups()
                
            # REMOVED: Google Drive OAuth disconnection
            # No longer needed since OAuth is removed
            
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
                    # Use app directory instead of current working directory
                    app_dir = Path(__file__).parent.parent.parent
                    data_path = app_dir / "data"
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
        
        # Add user management action
        manage_users_action = QAction("Manage Users", self)
        manage_users_action.triggered.connect(self.show_user_management)
        user_menu.addAction(manage_users_action)
        
        # Add user status to status bar
        self.login_status_label = QLabel("Not logged in")
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
        
        # Service Account setup for XLE file sync
        service_account_settings_action = QAction("Service Account Setup (XLE Sync)", self)
        service_account_settings_action.triggered.connect(self.setup_service_account)
        settings_menu.addAction(service_account_settings_action)
        
        # Monet API settings
        monet_settings_action = QAction("Monet API Settings", self)
        monet_settings_action.triggered.connect(self.open_monet_settings)
        settings_menu.addAction(monet_settings_action)

        # Add Water Level Meter Correction action
        water_level_correction_action = QAction("Water Level Meter Correction", self)
        water_level_correction_action.triggered.connect(self.open_water_level_correction)
        settings_menu.addAction(water_level_correction_action)
        
        # Add Turso Database settings
        turso_settings_action = QAction("Turso Database Settings", self)
        turso_settings_action.triggered.connect(self.open_turso_settings)
        settings_menu.addAction(turso_settings_action)

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
        # Add separator
        auto_sync_menu.addSeparator()
        # Sync to Turso
        sync_turso_action = QAction("Sync to Turso Database", self)
        sync_turso_action.triggered.connect(self.sync_to_turso)
        auto_sync_menu.addAction(sync_turso_action)
        
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
        
        # Add Find Files by Date Range action
        find_files_by_date_range_action = QAction("Find Files by Date Range", self)
        find_files_by_date_range_action.triggered.connect(self.open_find_files_by_date_range)
        tools_menu.addAction(find_files_by_date_range_action)
        
        # Update menu
        update_menu = menu_bar.addMenu("Update")
        
        # Show current version action
        show_version_action = QAction("About Version", self)
        show_version_action.triggered.connect(self.show_version_info)
        update_menu.addAction(show_version_action)
        
        # Add separator for shared drive updates
        update_menu.addSeparator()
        
        # Check for shared drive updates action
        check_shared_updates_action = QAction("Check Shared Drive Updates", self)
        check_shared_updates_action.triggered.connect(self.check_for_shared_updates)
        update_menu.addAction(check_shared_updates_action)
        
        # Shared drive settings action
        shared_drive_settings_action = QAction("Shared Drive Settings", self)
        shared_drive_settings_action.triggered.connect(self.open_shared_drive_settings)
        update_menu.addAction(shared_drive_settings_action)
    
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
    
    def open_turso_settings(self):
        """Open the Turso database settings dialog"""
        from .dialogs.turso_credentials_dialog import TursoCredentialsDialog
        dialog = TursoCredentialsDialog(self.settings_handler, self)
        if dialog.exec_() == QDialog.Accepted:
            # Settings are saved by the dialog
            pass

    def toggle_auto_sync(self):
        """Toggle auto sync functionality"""
        # Placeholder for future auto sync implementation
        QMessageBox.information(self, "Auto Sync", "Auto Sync feature will be implemented soon!")

    def auto_sync_barologgers(self):
        """Run guided or automatic sync for barologger XLE files with Google Drive integration"""
        # Check if current database is a cloud database
        if not self.db_manager.current_db or not self.db_manager.is_cloud_database:
            QMessageBox.warning(
                self, 
                "Local Database Selected", 
                "Auto Sync is only available for cloud databases.\n\n"
                "Please open a cloud database or create a new cloud database to use Auto Sync functionality."
            )
            return
        
        # Initialize handler if needed
        if self.auto_update_handler is None:
            # REMOVED: AutoUpdateHandler with Google Drive OAuth dependency
            # self.auto_update_handler = AutoUpdateHandler(...)
            logger.info("Auto-update handler disabled - requires service account adaptation")
        
        # Delegate to the handler
        self.auto_update_handler.auto_sync_barologgers()
    
    def auto_sync_water_levels(self):
        """Run guided or automatic sync for water level XLE files with Google Drive integration"""
        # Check if current database is a cloud database
        if not self.db_manager.current_db or not self.db_manager.is_cloud_database:
            QMessageBox.warning(
                self, 
                "Local Database Selected", 
                "Auto Sync is only available for cloud databases.\n\n"
                "Please open a cloud database or create a new cloud database to use Auto Sync functionality."
            )
            return
        
        # Initialize handler if needed
        if self.auto_update_handler is None:
            # REMOVED: AutoUpdateHandler with Google Drive OAuth dependency
            # self.auto_update_handler = AutoUpdateHandler(...)
            logger.info("Auto-update handler disabled - requires service account adaptation")
        
        # Delegate to the handler
        self.auto_update_handler.auto_sync_water_levels()
    
    def sync_to_turso(self):
        """Manually sync the current database to Turso"""
        # Check if we have a cloud database open
        if not self.db_manager.is_cloud_database:
            QMessageBox.warning(
                self,
                "Cloud Database Required",
                "Turso sync is only available for cloud databases.\n\n"
                "Please open a cloud database (CAESER_GENERAL, MEGASITE, or SANDY_CREEK) to use this feature."
            )
            return
            
        # Get current project name
        project_name = self.db_manager.cloud_project_name
        supported_projects = ["CAESER_GENERAL", "MEGASITE", "SANDY_CREEK"]
        
        if project_name not in supported_projects:
            QMessageBox.warning(
                self,
                "Unsupported Project",
                f"Project '{project_name}' is not supported for Turso sync.\n\n"
                f"Supported projects: {', '.join(supported_projects)}"
            )
            return
            
        # Confirm sync
        reply = QMessageBox.question(
            self,
            "Sync to Turso",
            f"This will sync the {project_name} database to Turso.\n\n"
            f"The process will:\n"
            f"1. Create an optimized version of the database\n"
            f"2. Upload it to Turso (replacing existing data)\n"
            f"3. Log the operation\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Use optimized handler that works on all platforms
            from .handlers.turso_handler_optimized import TursoHandlerOptimized
            turso_handler = TursoHandlerOptimized(self.db_manager, self.settings_handler)
            turso_handler.sync_to_turso(project_name, self)
    
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
    
    def show_user_management(self):
        """Show the user management dialog"""
        try:
            dialog = UserManagementDialog(self.user_auth_service, self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error opening user management dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open user management: {str(e)}")

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
        """Open the online water level data visualizer in browser"""
        try:
            import webbrowser
            
            # URL for the new online visualizer
            visualizer_url = "https://caeser-water-level-visualizer.netlify.app/"
            
            # Show confirmation dialog with information
            reply = QMessageBox.question(
                self,
                "Open Online Visualizer",
                f"This will open the CAESER Water Level Visualizer in your default web browser.\n\n"
                f"URL: {visualizer_url}\n\n"
                f"The online visualizer provides:\n"
                f"• Interactive water level plotting\n"
                f"• Database upload and analysis\n"
                f"• Export capabilities\n"
                f"• Mobile-friendly interface\n\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Open the URL in the default browser
                webbrowser.open(visualizer_url)
                logger.info(f"Opened online visualizer: {visualizer_url}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open online visualizer: {str(e)}"
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

    def open_find_files_by_date_range(self):
        """Launch the Find Files by Date Range tool"""
        try:
            # Get the path to the tools directory relative to the current file
            tools_dir = Path(__file__).parent.parent.parent / "tools"
            find_date_range_path = tools_dir / "find_files_by_date_range.py"
            
            if not find_date_range_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find Find Files by Date Range tool at {find_date_range_path}"
                )
                return
                
            # Launch the script as a subprocess
            subprocess.Popen([sys.executable, str(find_date_range_path)])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch Find Files by Date Range tool: {str(e)}"
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
            if not self.db_manager.current_db:
                logger.error("DEBUG: _reload_database called but current_db is None!")
                QMessageBox.warning(self, "Database Error", "Cannot reload database: current database is None.")
                return
                
            current_db_path = str(self.db_manager.current_db)
            logger.debug(f"DEBUG: _reload_database current_db_path: {repr(current_db_path)}")
            
            if current_db_path == "None" or not current_db_path:
                logger.error("DEBUG: current_db_path is 'None' or empty, cannot reload!")
                QMessageBox.warning(self, "Database Error", "Cannot reload database: invalid database path.")
                return
                
            current_db_name = Path(current_db_path).name

            # Show progress dialog
            progress_dialog.show("Reloading database...", "Database Reload")
            progress_dialog.update(20, "Closing current database connection...")

            # Close current database connection
            self.db_manager.close()

            progress_dialog.update(50, "Opening database from disk...")

            # Reopen the database
            logger.debug(f"DEBUG: _reload_database calling open_database with: {repr(current_db_path)}")
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
                display_path = self._get_display_path(selected_folder)
                self.folder_info_label.setText(f"Folder: {display_path}")
                self.folder_info_label.setToolTip(f"Database folder: {selected_folder}")
                
                # Note: Don't change working directory - use absolute paths instead
                try:
                    self.logger.debug(f"Using database folder: {selected_folder}")
                    
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
        
    def _add_recharge_tab(self):
        """Add the recharge tab"""
        tab = RechargeTab(self.db_manager)
        self._tabs["recharge"] = tab
        self.tab_widget.addTab(tab, "Recharge")
        
    def _add_geophysical_data_tab(self):
        """Add the geophysical data tab"""
        tab = GeophysicalDataTab(self.db_manager)
        self._tabs["geophysical_data"] = tab
        self.tab_widget.addTab(tab, "Geophysical Data")
        
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
                    # Note: Don't change working directory - use absolute paths instead  
                    display_path = self._get_display_path(initial_folder)
                    self.folder_info_label.setText(f"Folder: {display_path}")
                    self.folder_info_label.setToolTip(f"Database folder: {initial_folder}")
                    
                    # Reload databases from the new directory (after directory change)
                    # This is needed because authentication might have already loaded databases from the wrong path
                    logger.debug(f"Reloading databases from the correct path: {initial_folder}")
                    
                    # Skip reload if Google Drive just authenticated to avoid clearing cloud projects
                    if not self._google_drive_just_authenticated:
                        self._load_databases()
                    else:
                        logger.info("Skipping database reload - Google Drive authentication just completed")
                        self._google_drive_just_authenticated = False
                    
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
        """Load any available database from the configured databases directory"""
        try:
            # Get the configured database directory
            # Use app directory instead of current working directory
            app_dir = Path(__file__).parent.parent.parent
            local_db_directory = Path(self.settings_handler.get_setting("local_db_directory", str(app_dir)))
            
            if not local_db_directory.exists():
                logger.warning(f"Database directory does not exist: {local_db_directory}")
                return False
                
            # Look for any .db files in the directory
            db_files = [db for db in local_db_directory.glob("*.db") if "_(drive)" not in db.name]
            
            if db_files:
                # Load the first database found
                first_db = db_files[0]
                logger.info(f"Loading database: {first_db}")
                self.db_manager.open_database(str(first_db))
                
                # Update the database info label
                self._update_db_info_label()
                
                logger.info(f"Loaded database: {first_db}")
                if len(db_files) > 1:
                    logger.info(f"Found {len(db_files)} databases, loaded first one")
                return True
                
            # No databases found
            logger.warning(f"No databases found in {local_db_directory}")
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
            
            # REMOVED: Google Drive OAuth authentication check
            # if not self.drive_service.authenticated: ...
            logger.info("Google Drive OAuth authentication removed - skipping auth check")
            
            # Update progress
            if self.progress_dialog:
                self.progress_dialog.setValue(start_progress + 2)
                self.progress_dialog.setLabelText("Initializing Google Drive monitor...")
            
            # Skip XLE monitor initialization for cloud databases - not needed
            if not hasattr(self, 'drive_monitor') or self.drive_monitor is None:
                self.drive_monitor = None
            
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
                # REMOVED: AutoUpdateHandler with Google Drive OAuth dependency
                # self.auto_update_handler = AutoUpdateHandler(...)
                logger.info("Auto-update handler disabled - requires service account adaptation")
            
            # Final steps
            self.progress_dialog.setValue(100)
            self.progress_dialog.setLabelText("Initialization complete!")
            
            # End initialization phase
            self._initialization_phase = False
            
            # Close the progress dialog
            QTimer.singleShot(500, self._close_progress_dialog)
            
            # Check for updates on startup
            QTimer.singleShot(1000, self._check_updates_on_startup)
            
            # Check for credentials after a short delay
            QTimer.singleShot(2000, self._check_credentials_on_startup)
        
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

    def open_help_system(self):
        """Open the application help system"""
        try:
            help_system = ApplicationHelpSystem(self)
            help_system.show()
            logger.info("Application help system opened")
        except Exception as e:
            logger.error(f"Error opening help system: {e}")
            QMessageBox.critical(self, "Help Error", f"Failed to open help system: {str(e)}")

    def open_feedback_dialog(self):
        """Open the feedback dialog for submitting bug reports and feature requests"""
        try:
            # REMOVED: Google Drive OAuth dependency check
            # QMessageBox.warning(self, "Feedback Unavailable", "Feedback submission requires Google Drive integration.")
            logger.warning("Feedback system disabled - requires service account adaptation")
            
            # Get current user name
            user_name = "Anonymous"
            if hasattr(self, 'user_auth_service') and self.user_auth_service:
                try:
                    current_user_info = self.user_auth_service.get_current_user_info()
                    if current_user_info:
                        user_name = current_user_info.get('username', 'Anonymous')
                except Exception:
                    pass  # Use default if we can't get user info
            
            # REMOVED: Feedback dialog with Google Drive OAuth dependency
            # feedback_dialog = FeedbackDialog(parent=self, drive_service=self.drive_service, user_name=user_name)
            QMessageBox.information(self, "Feedback System", "Feedback system is temporarily disabled during Google Drive service account transition.")
            return
            
        except Exception as e:
            logger.error(f"Error opening feedback dialog: {e}")
            QMessageBox.critical(self, "Feedback Error", 
                               f"Failed to open feedback dialog:\n{str(e)}")

    def _update_feedback_button_visibility(self):
        """Update feedback button visibility based on Google Drive authentication status"""
        try:
            # REMOVED: Google Drive OAuth-dependent feedback button visibility
            # is_authenticated = (hasattr(self, 'drive_service') and self.drive_service ...)
            if hasattr(self, 'feedback_btn'):
                self.feedback_btn.setVisible(False)  # Hidden during OAuth transition
                
            if is_authenticated:
                logger.debug("Feedback button shown - Google Drive authentication detected")
            else:
                logger.debug("Feedback button hidden - No Google Drive authentication")
                
        except Exception as e:
            logger.error(f"Error updating feedback button visibility: {e}")
            # Hide button on error to be safe
            if hasattr(self, 'feedback_btn'):
                self.feedback_btn.setVisible(False)

    def update_user_status(self):
        """Update the user status label in the status bar with current user info"""
        try:
            if hasattr(self, 'user_auth_service') and self.user_auth_service:
                current_user_info = self.user_auth_service.get_current_user_info()
                if current_user_info and 'username' in current_user_info:
                    username = current_user_info['username']
                    self.login_status_label.setText(username)
                    logger.info(f"Updated status bar with username: {username}")
                else:
                    self.login_status_label.setText("Unknown User")
                    logger.warning("Could not get username from user_auth_service")
            else:
                self.login_status_label.setText("Not logged in")
                logger.warning("No user_auth_service available")
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            self.login_status_label.setText("Error")

    def _setup_auto_updater(self):
        """Setup the auto-updater system"""
        try:
            # Determine app root directory
            app_root = Path(__file__).parent.parent.parent
            
            # Check if we're in installed app structure
            if (app_root / "version.json").exists():
                # We're in the installed app structure
                self.auto_updater = AutoUpdater(app_root)
            elif (app_root / "config" / "version.json").exists():
                # We're in development structure
                self.auto_updater = AutoUpdater(app_root)
            else:
                # Create a version file if it doesn't exist (development mode)
                logger.info("Creating version file for development mode")
                version_file = app_root / "version.json"
                import json
                from datetime import datetime
                version_data = {
                    "version": "1.0.0-dev",
                    "release_date": datetime.now().isoformat(),
                    "description": "Development version",
                    "github_repo": "benjaled/water_levels_monitoring_-for_external_edits-",
                    "auto_update": {
                        "enabled": False,  # Disabled in dev mode
                        "check_on_startup": False,
                        "backup_count": 3
                    }
                }
                try:
                    with open(version_file, 'w') as f:
                        json.dump(version_data, f, indent=2)
                    self.auto_updater = AutoUpdater(app_root)
                except Exception as e:
                    logger.warning(f"Could not create version file: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to setup auto-updater: {e}")
    
    def _setup_shared_drive_updater(self):
        """Setup the shared drive updater system"""
        try:
            # Determine app root directory
            app_root = Path(__file__).parent.parent.parent
            
            # Get shared drive path from settings
            shared_drive_path = self.settings_handler.get_setting("shared_drive_path", "")
            
            # Initialize shared drive updater
            self.shared_drive_updater = SharedDriveUpdater(app_root, shared_drive_path)
            
            logger.info("Shared drive updater initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup shared drive updater: {e}")
            
    def check_for_updates(self):
        """Check for application updates"""
        if not self.auto_updater:
            return
            
        try:
            update_info = self.auto_updater.check_for_updates()
            if update_info:
                if self.auto_updater.prompt_for_update(update_info, self):
                    success = self.auto_updater.apply_update(update_info, self)
                    if success:
                        # Update applied successfully, ask to restart
                        reply = QMessageBox.question(self, "Update Complete", 
                                                   "Update applied successfully. Restart the application now?",
                                                   QMessageBox.Yes | QMessageBox.No)
                        if reply == QMessageBox.Yes:
                            QApplication.quit()
            else:
                logger.info("No updates available")
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            
    def _check_updates_on_startup(self):
        """Check for updates on startup (if enabled)"""
        if not self.auto_updater:
            return
            
        try:
            # Only check if auto-update is enabled and not in development mode
            if hasattr(self.auto_updater, 'version_checker'):
                current_version = self.auto_updater.current_version
                if not current_version.endswith('-dev'):
                    # Schedule update check for after initialization
                    QTimer.singleShot(3000, self.check_for_updates)  # Check after 3 seconds
        except Exception as e:
            logger.error(f"Startup update check failed: {e}")
            
    def show_version_info(self):
        """Show current version information"""
        try:
            if self.auto_updater:
                current_version = self.auto_updater.current_version
                app_root = self.auto_updater.app_root
                
                message = f"""Water Level Monitoring System
                
Current Version: {current_version}
Installation Path: {app_root}

GitHub Repository: {self.auto_updater.github_repo}
Auto-Update: {'Enabled' if hasattr(self.auto_updater, 'version_checker') else 'Disabled'}

Click 'Check for Updates' in the Update menu to manually check for newer versions."""
                
                QMessageBox.information(self, "Version Information", message)
            else:
                QMessageBox.information(self, "Version Information", 
                                      "Version information not available.\nAuto-updater not initialized.")
        except Exception as e:
            logger.error(f"Error showing version info: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show version info: {str(e)}")
    
    def check_for_shared_updates(self):
        """Check for application updates from shared drive"""
        if not self.shared_drive_updater:
            QMessageBox.warning(self, "Shared Drive Updates", 
                              "Shared drive updater not initialized.\n\n"
                              "Please configure the shared drive path in Settings.")
            return
            
        try:
            # Check for updates
            update_info = self.shared_drive_updater.check_for_updates()
            
            if update_info:
                # Update available - show prompt
                if self.shared_drive_updater.prompt_for_update(update_info, self):
                    success = self.shared_drive_updater.apply_update(update_info, self)
                    if success:
                        # Update process started - app will close
                        QApplication.quit()
            else:
                # No updates available or shared drive not accessible
                status_message = self.shared_drive_updater.get_update_status_message()
                QMessageBox.information(self, "No Updates Available", 
                                      f"No updates found.\n\n{status_message}")
                
        except Exception as e:
            logger.error(f"Shared drive update check failed: {e}")
            QMessageBox.critical(self, "Update Error", 
                               f"Error checking for shared drive updates:\n{str(e)}")
    
    def open_shared_drive_settings(self):
        """Open shared drive settings dialog"""
        try:
            dialog = SharedDriveSettingsDialog(
                self.settings_handler, 
                self.shared_drive_updater, 
                self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Settings were saved, reinitialize the shared drive updater
                self._setup_shared_drive_updater()
                logger.info("Shared drive settings updated")
                
        except Exception as e:
            logger.error(f"Error opening shared drive settings: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Error opening shared drive settings:\n{str(e)}")
            
    def _check_credentials_on_startup(self):
        """Check for Google Drive credentials on startup"""
        try:
            # Skip this check since we now handle OAuth authentication properly in the main startup flow
            logger.info("Credential check skipped - OAuth authentication handled in main startup flow")
            return
                
        except Exception as e:
            logger.error(f"Error checking credentials: {e}")
            
    def setup_service_account(self):
        """Open service account setup dialog for XLE file sync to SMOO"""
        QMessageBox.information(
            self,
            "Service Account Setup",
            "Service Account Setup for XLE file synchronization to SMOO.\n\n"
            "This will be configured to:\n"
            "• Use Google Drive service account (no OAuth required)\n"
            "• Sync XLE files from SOLINST folder to SMOO\n"
            "• Transfer metadata and consolidated files\n\n"
            "Feature coming soon - currently under development."
        )
    
    def setup_credentials(self):
        """Open unified credentials setup dialog manually"""
        try:
            dialog = UnifiedCredentialsDialog(self.settings_handler, self)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                # Settings were updated, reload Google Drive components
                try:
                    # Reinitialize Google Drive service completely
                    if hasattr(self, 'drive_service'):
                        logger.info("Reinitializing Google Drive service with new credentials")
                        # REMOVED: Google Drive OAuth service reinitialization
                        # GoogleDriveService.reset_instance()
                        # self.drive_service = GoogleDriveService.get_instance(self.settings_handler)
                        logger.info("Google Drive OAuth reinitialization removed - using service account approach")
                        
                        # Initialize Google Drive database handler
                        if not hasattr(self, 'drive_db_handler') or self.drive_db_handler is None:
                            self.drive_db_handler = GoogleDriveDatabaseHandler(self.settings_handler)
                        self.drive_db_handler.authenticate()
                        
                        # Set Google Drive handler for database manager
                        self.db_manager.set_google_drive_handler(self.drive_db_handler)
                        
                        logger.info("Google Drive components reinitialized successfully")
                        
                        # Reload databases after successful component initialization
                        logger.info("Reloading databases after credential setup")
                        QTimer.singleShot(100, self._load_databases)
                        
                        # Update feedback button visibility
                        self._update_feedback_button_visibility()
                    else:
                        logger.warning("Google Drive service not authenticated after credential setup")
                        # Still reload databases to show local ones
                        logger.info("Reloading local databases only")
                        QTimer.singleShot(100, self._load_databases)
                    
                    # Update water level runs tab if it exists
                    if 'water_level_runs' in self._tabs:
                        runs_tab = self._tabs['water_level_runs']
                        
                        # REMOVED: Google Drive OAuth-dependent runs loading
                        # if self.drive_service and self.drive_service.authenticated: ...
                    
                    # Update barologger tab if it exists
                    # REMOVED: Google Drive OAuth-dependent tab state updates
                    # if 'barologger' in self._tabs: barologger_tab.update_drive_state(...)
                    # if 'water_level' in self._tabs: water_level_tab.update_drive_state(...)
                    logger.info("Tab Google Drive state updates removed - OAuth no longer used")
                    
                    QMessageBox.information(self, "Setup Complete", 
                                          "Google Drive setup completed successfully!\n\n" +
                                          "The application is now using the new configuration.")
                except Exception as reload_error:
                    logger.error(f"Error reloading after credentials update: {reload_error}")
                    QMessageBox.warning(self, "Reload Warning", 
                                      "Settings saved but some components may need a restart to update fully.")
            
        except Exception as e:
            logger.error(f"Error opening credentials setup: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open credentials setup: {str(e)}")

    def mark_database_modified(self):
        """Mark the current database as having unsaved changes."""
        if self.db_manager and self.db_manager.current_db:
            # Handle cloud database modifications
            if self.db_manager.is_cloud_database:
                self.db_manager.is_cloud_modified = True
                self.save_cloud_btn.setEnabled(True)
                self.compare_changes_btn.setEnabled(True)
                self.cloud_mode_label.setText(f"SMOO: {self.db_manager.cloud_project_name} (MODIFIED)")
            elif self.db_manager.is_google_drive_db:
                self.db_manager._modified_since_sync = True
            
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
        """Create a new database with optional CSV pre-population."""
        try:
            # Import the database setup dialog
            from .dialogs.database_setup_dialog import DatabaseSetupDialog
            
            # Show the database setup dialog
            setup_dialog = DatabaseSetupDialog(self)
            if setup_dialog.exec_() == QDialog.Accepted:
                # If a database was created, load it
                if hasattr(setup_dialog, '_created_db_path') and setup_dialog._created_db_path:
                    self.db_manager.open_database(setup_dialog._created_db_path)
                    # Database was created successfully, refresh the UI
                    self._update_db_info_label()
                    # Refresh the database dropdown to show the new database
                    self._load_databases()
                    self.status_bar.showMessage("New database created and loaded successfully", 3000)
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")