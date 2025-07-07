"""
Enhanced Save Options Dialog

Dialog for choosing save options when closing app with unsaved changes,
specifically handling the case where user uploaded during session but made more changes.
Offers: Save to Cloud, Save as Draft, Restore to Last Upload, Restore to Original, Discard Changes
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QButtonGroup, QRadioButton, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from ..utils.button_styles import ButtonStyles
from ..utils.dialog_utils import DialogUtils

logger = logging.getLogger(__name__)


class EnhancedSaveOptionsDialog(QDialog):
    """Enhanced dialog for choosing save options when closing with unsaved changes after upload"""
    
    def __init__(self, project_name: str, change_tracker=None, cloud_handler=None, scenario: str = "changes_since_upload", parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.change_tracker = change_tracker
        self.cloud_handler = cloud_handler
        self.scenario = scenario
        self.choice = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the enhanced dialog UI"""
        self.setWindowTitle("Unsaved Changes After Upload")
        
        # Set minimum size with ability to expand
        self.setMinimumSize(750, 650)  # Wider to accommodate text properly
        self.resize(750, 650)
        
        # Set white background with more compact styling
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #333333;
            }
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 8px;
                margin: 6px 0;
                border-radius: 6px;
                background-color: #f8f9fa;
                border: 2px solid transparent;
                min-height: 20px;
            }
            QRadioButton:checked {
                background-color: #e7f3ff;
                border: 2px solid #007bff;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                margin-right: 6px;
            }
        """)
        
        # Main layout with better spacing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Warning icon
        icon_label = QLabel("📤")
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Changes Made After Upload")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #e65100; margin-left: 10px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Main message - more compact
        message = QLabel(
            f"You made changes to '<b>{self.project_name}</b>' after uploading to the cloud. Choose how to handle them:"
        )
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                font-size: 13px; 
                color: #495057;
                margin: 8px 0;
                line-height: 1.3;
            }
        """)
        main_layout.addWidget(message)
        
        # Show change summary if available - more compact
        if self.change_tracker and self.change_tracker.changes:
            changes_summary = self.change_tracker.get_changes_summary()
            summary_text = f"<b>{changes_summary['total']} additional changes</b> since upload"
            
            summary_label = QLabel(summary_text)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 3px;
                    padding: 6px;
                    font-size: 11px;
                    color: #856404;
                    margin: 4px 0;
                }
            """)
            main_layout.addWidget(summary_label)
        
        # Radio button group
        self.button_group = QButtonGroup()
        
        # Create options layout with better spacing
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)
        
        # Option 1: Save additional changes to Cloud
        self.cloud_radio = QRadioButton("💾 Upload Additional Changes")
        self.cloud_radio.setStyleSheet("color: #2196f3; font-weight: bold;")
        self.cloud_radio.setChecked(True)  # Default option
        self.button_group.addButton(self.cloud_radio, 1)
        options_layout.addWidget(self.cloud_radio)
        
        cloud_desc = QLabel("Upload your new changes to the cloud database")
        cloud_desc.setWordWrap(True)
        cloud_desc.setStyleSheet("margin-left: 28px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        options_layout.addWidget(cloud_desc)
        
        # Option 2: Save as Draft
        self.draft_radio = QRadioButton("📝 Save Additional Changes as Draft")
        self.draft_radio.setStyleSheet("color: #4caf50; font-weight: bold;")
        self.button_group.addButton(self.draft_radio, 2)
        options_layout.addWidget(self.draft_radio)
        
        draft_desc = QLabel("Save your additional changes locally to continue working later")
        draft_desc.setWordWrap(True)
        draft_desc.setStyleSheet("margin-left: 28px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        options_layout.addWidget(draft_desc)
        
        # Option 3: Restore to Last Upload
        self.restore_upload_radio = QRadioButton("⏮️ Restore to Last Upload")
        self.restore_upload_radio.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.button_group.addButton(self.restore_upload_radio, 3)
        options_layout.addWidget(self.restore_upload_radio)
        
        restore_upload_desc = QLabel("Discard additional changes and return to the uploaded state")
        restore_upload_desc.setWordWrap(True)
        restore_upload_desc.setStyleSheet("margin-left: 28px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        options_layout.addWidget(restore_upload_desc)
        
        # Option 4: Restore to Original
        self.restore_original_radio = QRadioButton("⏪ Restore to Original Download")
        self.restore_original_radio.setStyleSheet("color: #9c27b0; font-weight: bold;")
        self.button_group.addButton(self.restore_original_radio, 4)
        options_layout.addWidget(self.restore_original_radio)
        
        restore_original_desc = QLabel("Discard all session changes and return to the originally downloaded state")
        restore_original_desc.setWordWrap(True)
        restore_original_desc.setStyleSheet("margin-left: 28px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        options_layout.addWidget(restore_original_desc)
        
        # Option 5: Discard All Changes
        self.discard_radio = QRadioButton("🗑️ Discard Additional Changes")
        self.discard_radio.setStyleSheet("color: #f44336; font-weight: bold;")
        self.button_group.addButton(self.discard_radio, 5)
        options_layout.addWidget(self.discard_radio)
        
        discard_desc = QLabel("Close without saving additional changes (keep uploaded state)")
        discard_desc.setWordWrap(True)
        discard_desc.setStyleSheet("margin-left: 28px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        options_layout.addWidget(discard_desc)
        
        main_layout.addLayout(options_layout)
        
        main_layout.addStretch()
        
        # Buttons - more compact
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #6c757d;
                border: 2px solid #dee2e6;
                padding: 6px 16px;
                border-radius: 6px;
                font-size: 12px;
                min-width: 70px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 70px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        ok_button.clicked.connect(self.accept_choice)
        ok_button.setDefault(True)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        main_layout.addLayout(button_layout)
    
    def accept_choice(self):
        """Accept the selected choice"""
        selected_id = self.button_group.checkedId()
        
        if selected_id == 1:
            self.choice = "save_cloud"
        elif selected_id == 2:
            self.choice = "save_draft"
        elif selected_id == 3:
            self.choice = "restore_upload"
        elif selected_id == 4:
            self.choice = "restore_original"
        elif selected_id == 5:
            self.choice = "discard"
        
        self.accept()
    
    def get_choice(self):
        """Get the user's choice"""
        return self.choice