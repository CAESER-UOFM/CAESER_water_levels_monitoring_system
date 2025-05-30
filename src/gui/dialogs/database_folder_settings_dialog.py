from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QFileDialog, QMessageBox,
                           QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseFolderSettingsDialog(QDialog):
    def __init__(self, settings_handler, parent=None):
        super().__init__(parent)
        self.settings_handler = settings_handler
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Database Folder Settings")
        self.resize(600, 250)  # Reduced height since we removed the cache section
        layout = QVBoxLayout(self)
        
        # Help text at the top
        help_text = QLabel(
            "Configure the folder where your database files are stored. "
            "This folder will be loaded at startup, and available databases will be shown in the dropdown."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(help_text)
        
        # Database Folder Group
        folder_group = QGroupBox("Database Folder")
        folder_layout = QVBoxLayout(folder_group)
        
        # Local database directory
        local_dir_layout = QHBoxLayout()
        local_dir_label = QLabel("Database Folder:")
        self.local_db_dir = QLineEdit()
        self.local_db_dir.setPlaceholderText("Path to database folder")
        browse_dir_btn = QPushButton("Browse...")
        browse_dir_btn.clicked.connect(self.browse_local_dir)
        
        local_dir_layout.addWidget(local_dir_label)
        local_dir_layout.addWidget(self.local_db_dir, 1)
        local_dir_layout.addWidget(browse_dir_btn)
        folder_layout.addLayout(local_dir_layout)
        
        # Database folder help text
        folder_help = QLabel(
            "This folder will be used to store and access database files. "
            "The application will load this folder at startup and show available databases in the dropdown menu."
        )
        folder_help.setWordWrap(True)
        folder_help.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        folder_layout.addWidget(folder_help)
        
        # Current folder info
        current_folder_layout = QHBoxLayout()
        current_folder_label = QLabel("Current Folder:")
        
        initial_folder = self.settings_handler.get_setting("local_db_directory", "")
        folder_text = initial_folder if os.path.isdir(initial_folder) else "No folder selected"
        
        self.current_folder_value = QLabel(folder_text)
        self.current_folder_value.setStyleSheet("font-weight: bold;")
        
        current_folder_layout.addWidget(current_folder_label)
        current_folder_layout.addWidget(self.current_folder_value, 1)
        folder_layout.addLayout(current_folder_layout)
        
        # Load at startup option
        startup_layout = QHBoxLayout()
        startup_label = QLabel("Load folder at startup:")
        self.load_at_startup = QCheckBox()
        self.load_at_startup.setChecked(True)
        
        startup_layout.addWidget(startup_label)
        startup_layout.addWidget(self.load_at_startup)
        startup_layout.addStretch()
        folder_layout.addLayout(startup_layout)
        
        # Add the folder group to the main layout
        layout.addWidget(folder_group)
        
        # Add some vertical spacing
        layout.addSpacing(10)
        
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
        
    def browse_local_dir(self):
        """Browse for local database directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Database Folder",
            ""
        )
        
        if dir_path:
            self.local_db_dir.setText(dir_path)
    
    def load_settings(self):
        """Load settings from settings handler"""
        # Get database directory from settings
        self.local_db_dir.setText(self.settings_handler.get_setting("local_db_directory", ""))
        
        # Get startup loading option
        self.load_at_startup.setChecked(self.settings_handler.get_setting("load_db_folder_at_startup", True))
    
    def save_settings(self):
        """Save settings to settings handler"""
        # Make sure the folder exists
        db_folder = self.local_db_dir.text()
        if db_folder and not os.path.isdir(db_folder):
            try:
                os.makedirs(db_folder, exist_ok=True)
                logger.info(f"Created database folder: {db_folder}")
            except Exception as e:
                logger.error(f"Error creating database folder: {e}")
                QMessageBox.critical(self, "Error", f"Failed to create database folder: {str(e)}")
                return
        
        # Save database folder settings
        self.settings_handler.set_setting("local_db_directory", db_folder)
        self.settings_handler.set_setting("load_db_folder_at_startup", self.load_at_startup.isChecked())
        
        # Show success message and close dialog
        QMessageBox.information(self, "Settings Saved", "Database folder settings have been saved.")
        self.accept() 