"""
Save Options Dialog

Dialog for choosing save options when closing app with unsaved changes.
Offers: Save to Cloud, Save as Draft, Discard Changes
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class SaveOptionsDialog(QDialog):
    """Dialog for choosing save options when closing with unsaved changes"""
    
    def __init__(self, project_name: str, change_tracker=None, parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.change_tracker = change_tracker
        self.choice = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Unsaved Changes")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.resize(650, 550)
        
        # Center the dialog on the parent window
        if self.parent():
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        
        # Set white background
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #333333;
            }
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                padding: 12px 8px;
                margin: 8px 0;
                border-radius: 6px;
                background-color: #f8f9fa;
                border: 2px solid transparent;
            }
            QRadioButton:checked {
                background-color: #e7f3ff;
                border: 2px solid #007bff;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
                margin-right: 8px;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Warning icon
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("You Have Unsaved Changes")
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
        
        # Main message
        message = QLabel(
            f"You have unsaved changes in '<b>{self.project_name}</b>'.\\n"
            f"Choose how you want to proceed:"
        )
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                font-size: 14px; 
                color: #495057;
                margin: 10px 0;
                line-height: 1.4;
            }
        """)
        main_layout.addWidget(message)
        
        # Show change summary if available
        if self.change_tracker and self.change_tracker.changes:
            changes_summary = self.change_tracker.get_changes_summary()
            summary_text = f"<b>Changes detected:</b> {changes_summary['total']} modifications"
            
            summary_label = QLabel(summary_text)
            summary_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 12px;
                    color: #495057;
                }
            """)
            main_layout.addWidget(summary_label)
        
        # Options
        options_label = QLabel("<b>Choose an option:</b>")
        options_label.setStyleSheet("font-size: 14px; margin-top: 15px;")
        main_layout.addWidget(options_label)
        
        # Radio button group
        self.button_group = QButtonGroup()
        
        # Option 1: Save to Cloud
        self.cloud_radio = QRadioButton("💾 Save to Cloud")
        self.cloud_radio.setStyleSheet("color: #2196f3; font-weight: bold;")
        self.cloud_radio.setChecked(True)  # Default option
        self.button_group.addButton(self.cloud_radio, 1)
        main_layout.addWidget(self.cloud_radio)
        
        cloud_desc = QLabel("Upload changes to the cloud database immediately")
        cloud_desc.setStyleSheet("margin-left: 30px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        main_layout.addWidget(cloud_desc)
        
        main_layout.addSpacing(15)
        
        # Option 2: Save as Draft
        self.draft_radio = QRadioButton("📝 Save as Draft")
        self.draft_radio.setStyleSheet("color: #4caf50; font-weight: bold;")
        self.button_group.addButton(self.draft_radio, 2)
        main_layout.addWidget(self.draft_radio)
        
        draft_desc = QLabel("Save changes locally to continue working later (offline)")
        draft_desc.setStyleSheet("margin-left: 30px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        main_layout.addWidget(draft_desc)
        
        main_layout.addSpacing(15)
        
        # Option 3: Discard Changes
        self.discard_radio = QRadioButton("🗑️ Discard Changes")
        self.discard_radio.setStyleSheet("color: #f44336; font-weight: bold;")
        self.button_group.addButton(self.discard_radio, 3)
        main_layout.addWidget(self.discard_radio)
        
        discard_desc = QLabel("Close without saving (all changes will be lost)")
        discard_desc.setStyleSheet("margin-left: 30px; margin-bottom: 10px; color: #666; font-size: 12px; line-height: 1.4;")
        main_layout.addWidget(discard_desc)
        
        main_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 25, 0, 0)
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #6c757d;
                border: 2px solid #dee2e6;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
                color: #495057;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
                min-height: 40px;
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
            self.choice = "discard"
        
        self.accept()
    
    def get_choice(self):
        """Get the user's choice"""
        return self.choice