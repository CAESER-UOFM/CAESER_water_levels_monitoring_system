"""
Version Conflict Resolution Dialog

Handles database version conflicts when saving to Google Drive.
Provides user options for resolving conflicts when cloud database was modified by another user.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QButtonGroup, QRadioButton, QGroupBox, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class VersionConflictDialog(QDialog):
    """Dialog to handle version conflicts when saving database to cloud."""
    
    def __init__(self, project_name: str, original_time: str, current_time: str, 
                 changes_description: str, parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.original_time = original_time
        self.current_time = current_time
        self.changes_description = changes_description
        self.resolution = None
        
        self.setWindowTitle("Database Version Conflict")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with warning icon and title
        header_layout = QHBoxLayout()
        
        # Warning icon
        warning_label = QLabel("⚠️")
        warning_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(warning_label)
        
        # Title
        title_label = QLabel("Version Conflict Detected")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #d32f2f;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Conflict explanation
        explanation = QLabel(
            f"The database '{self.project_name}' has been modified by another user "
            f"while you were working on it. This creates a version conflict that needs to be resolved."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #555; font-size: 12px; margin: 10px 0;")
        layout.addWidget(explanation)
        
        # Version information
        version_group = QGroupBox("Version Information")
        version_layout = QVBoxLayout(version_group)
        
        # Format timestamps for display
        try:
            orig_dt = datetime.fromisoformat(self.original_time.replace('Z', '+00:00'))
            curr_dt = datetime.fromisoformat(self.current_time.replace('Z', '+00:00'))
            
            orig_formatted = orig_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            curr_formatted = curr_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            orig_formatted = self.original_time
            curr_formatted = self.current_time
        
        version_layout.addWidget(QLabel(f"<b>Your version downloaded at:</b> {orig_formatted}"))
        version_layout.addWidget(QLabel(f"<b>Current cloud version modified at:</b> {curr_formatted}"))
        
        if self.changes_description:
            version_layout.addWidget(QLabel(f"<b>Your changes:</b> {self.changes_description}"))
            
        layout.addWidget(version_group)
        
        # Resolution options
        options_group = QGroupBox("Choose Resolution")
        options_layout = QVBoxLayout(options_group)
        
        self.button_group = QButtonGroup()
        
        # Option 1: Overwrite
        self.overwrite_radio = QRadioButton("Overwrite cloud version with my changes")
        self.overwrite_radio.setStyleSheet("font-weight: bold; color: #d32f2f;")
        self.button_group.addButton(self.overwrite_radio, 1)
        options_layout.addWidget(self.overwrite_radio)
        
        overwrite_desc = QLabel(
            "⚠️ This will replace the cloud version with your changes. "
            "The other user's changes will be moved to a backup folder."
        )
        overwrite_desc.setStyleSheet("margin-left: 20px; color: #666; font-size: 11px;")
        overwrite_desc.setWordWrap(True)
        options_layout.addWidget(overwrite_desc)
        
        # Option 2: Save as new version
        self.new_version_radio = QRadioButton("Save as new version (recommended)")
        self.new_version_radio.setStyleSheet("font-weight: bold; color: #1976d2;")
        self.new_version_radio.setChecked(True)  # Default selection
        self.button_group.addButton(self.new_version_radio, 2)
        options_layout.addWidget(self.new_version_radio)
        
        new_version_desc = QLabel(
            "✅ This creates a new version with a timestamp. Both versions are preserved. "
            "A conflict resolution todo will be created for manual merge later."
        )
        new_version_desc.setStyleSheet("margin-left: 20px; color: #666; font-size: 11px;")
        new_version_desc.setWordWrap(True)
        options_layout.addWidget(new_version_desc)
        
        # Option 3: Cancel
        self.cancel_radio = QRadioButton("Cancel - Don't save now")
        self.cancel_radio.setStyleSheet("font-weight: bold;")
        self.button_group.addButton(self.cancel_radio, 3)
        options_layout.addWidget(self.cancel_radio)
        
        cancel_desc = QLabel(
            "↩️ Return to local work without saving. You can resolve the conflict later."
        )
        cancel_desc.setStyleSheet("margin-left: 20px; color: #666; font-size: 11px;")
        cancel_desc.setWordWrap(True)
        options_layout.addWidget(cancel_desc)
        
        layout.addWidget(options_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.proceed_button = QPushButton("Proceed")
        self.proceed_button.clicked.connect(self.on_proceed)
        self.proceed_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.proceed_button)
        layout.addLayout(button_layout)
        
    def on_proceed(self):
        """Handle proceed button click"""
        checked_button = self.button_group.checkedButton()
        if not checked_button:
            QMessageBox.warning(self, "No Selection", "Please select a resolution option.")
            return
            
        button_id = self.button_group.id(checked_button)
        
        if button_id == 1:
            self.resolution = 'overwrite'
            # Show confirmation for risky operation
            reply = QMessageBox.question(
                self, 
                "Confirm Overwrite",
                "Are you sure you want to overwrite the cloud version? "
                "This will move the other user's changes to a backup folder.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        elif button_id == 2:
            self.resolution = 'new_version'
        elif button_id == 3:
            self.resolution = 'cancel'
            
        logger.info(f"User chose conflict resolution: {self.resolution}")
        self.accept()
        
    def get_resolution(self):
        """Get the user's chosen resolution"""
        return self.resolution