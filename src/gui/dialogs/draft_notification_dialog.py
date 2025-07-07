"""
Draft Notification Dialogs

Dialogs for handling local draft notifications:
1. Draft available on startup
2. Cloud version changed while working on draft
3. Draft save confirmation
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


class DraftAvailableDialog(QDialog):
    """Dialog shown when a draft is available on startup."""
    
    def __init__(self, project_name: str, draft_info: dict, parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.draft_info = draft_info
        self.choice = None
        
        self.setWindowTitle("Local Draft Available")
        self.setModal(True)
        self.resize(500, 350)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        icon_label = QLabel("📝")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Local Draft Found")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1976d2;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Information
        info_text = (
            f"You have unsaved local changes for '{self.project_name}'.\n\n"
            f"Draft created: {self._format_timestamp(self.draft_info.get('draft_created_at'))}\n"
            f"Last updated: {self._format_timestamp(self.draft_info.get('draft_updated_at'))}\n"
            f"Changes: {self.draft_info.get('changes_description', 'Local modifications')}"
        )
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # Options
        options_group = QGroupBox("What would you like to do?")
        options_layout = QVBoxLayout(options_group)
        
        self.button_group = QButtonGroup()
        
        # Option 1: Continue with draft
        self.continue_radio = QRadioButton("Continue working on my local changes")
        self.continue_radio.setStyleSheet("font-weight: bold; color: #1976d2;")
        self.continue_radio.setChecked(True)  # Default
        self.button_group.addButton(self.continue_radio, 1)
        options_layout.addWidget(self.continue_radio)
        
        continue_desc = QLabel("📝 Resume work on your local draft with unsaved changes.")
        continue_desc.setStyleSheet("margin-left: 20px; color: #666; font-size: 11px;")
        options_layout.addWidget(continue_desc)
        
        # Option 2: Download fresh copy
        self.fresh_radio = QRadioButton("Download fresh copy from cloud")
        self.fresh_radio.setStyleSheet("font-weight: bold; color: #f57c00;")
        self.button_group.addButton(self.fresh_radio, 2)
        options_layout.addWidget(self.fresh_radio)
        
        fresh_desc = QLabel("⚠️ Discard local changes and start with latest cloud version.")
        fresh_desc.setStyleSheet("margin-left: 20px; color: #666; font-size: 11px;")
        options_layout.addWidget(fresh_desc)
        
        layout.addWidget(options_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        proceed_button = QPushButton("Proceed")
        proceed_button.clicked.connect(self.on_proceed)
        proceed_button.setStyleSheet("""
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
        button_layout.addWidget(proceed_button)
        layout.addLayout(button_layout)
        
    def on_proceed(self):
        """Handle proceed button click"""
        checked_button = self.button_group.checkedButton()
        if not checked_button:
            return
            
        button_id = self.button_group.id(checked_button)
        
        if button_id == 1:
            self.choice = 'continue_draft'
        elif button_id == 2:
            # Confirm discarding changes
            reply = QMessageBox.question(
                self,
                "Confirm Discard Changes",
                "Are you sure you want to discard your local changes? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            self.choice = 'download_fresh'
            
        self.accept()
        
    def get_choice(self):
        """Get the user's choice"""
        return self.choice
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp_str or "Unknown"


class CloudVersionChangedDialog(QDialog):
    """Dialog shown when cloud version changed while working on draft."""
    
    def __init__(self, project_name: str, version_info: dict, parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.version_info = version_info
        
        self.setWindowTitle("Cloud Version Changed")
        self.setModal(True)
        self.resize(450, 250)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        icon_label = QLabel("🔄")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Cloud Version Changed")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #f57c00;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Information
        info_text = (
            f"The cloud version of '{self.project_name}' has been modified by another user "
            f"while you were working on your local draft.\n\n"
            f"Your local changes are safe and preserved. You can continue working locally "
            f"and resolve any conflicts when you're ready to save to the cloud."
        )
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 12px; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # Action button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("Continue Working Locally")
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("""
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
        
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)