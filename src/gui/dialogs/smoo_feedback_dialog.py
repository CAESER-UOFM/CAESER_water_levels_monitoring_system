# -*- coding: utf-8 -*-
"""
SMOO Feedback Dialog - For submitting bug reports and feature requests
Saves feedback directly to SMOO shared drive for developer review
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QLineEdit, QGroupBox, QProgressBar,
    QMessageBox, QFormLayout, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from ..utils.button_styles import ButtonStyles

logger = logging.getLogger(__name__)

class SMOOFeedbackSaveThread(QThread):
    """Thread for saving feedback to SMOO shared drive"""
    
    progress_updated = pyqtSignal(str)  # Status message
    save_completed = pyqtSignal(bool, str)  # Success, message
    
    def __init__(self, feedback_data, shared_drive_handler, feedback_folder_path):
        super().__init__()
        self.feedback_data = feedback_data
        self.shared_drive_handler = shared_drive_handler
        self.feedback_folder_path = feedback_folder_path
    
    def ensure_feedback_folder_exists(self):
        """Ensure the App_Feedback and general_feedback subfolders exist in SMOO"""
        try:
            self.progress_updated.emit("Checking feedback folder structure...")
            
            # Create base App_Feedback folder if it doesn't exist
            app_feedback_path = os.path.join(self.feedback_folder_path, "App_Feedback")
            if not os.path.exists(app_feedback_path):
                self.progress_updated.emit("Creating App_Feedback folder...")
                os.makedirs(app_feedback_path, exist_ok=True)
                logger.info(f"Created App_Feedback folder: {app_feedback_path}")
            
            # Create general_feedback subfolder
            general_feedback_path = os.path.join(app_feedback_path, "general_feedback")
            if not os.path.exists(general_feedback_path):
                self.progress_updated.emit("Creating general_feedback subfolder...")
                os.makedirs(general_feedback_path, exist_ok=True)
                logger.info(f"Created general_feedback subfolder: {general_feedback_path}")
            
            return general_feedback_path
            
        except Exception as e:
            logger.error(f"Error ensuring feedback folder exists: {e}")
            raise
    
    def run(self):
        """Save feedback to SMOO shared drive"""
        try:
            self.progress_updated.emit("Starting feedback save...")
            
            # Ensure feedback folder structure exists
            target_folder = self.ensure_feedback_folder_exists()
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"feedback_{timestamp}_{self.feedback_data.get('user_name', 'anonymous')}.json"
            file_path = os.path.join(target_folder, filename)
            
            self.progress_updated.emit("Saving feedback file...")
            
            # Prepare feedback data with metadata
            feedback_with_metadata = {
                "submission_info": {
                    "timestamp": datetime.now().isoformat(),
                    "user_name": self.feedback_data.get('user_name', 'Anonymous'),
                    "app_version": "CAESER Water Levels Monitor",
                    "submission_method": "SMOO Shared Drive"
                },
                "feedback": self.feedback_data
            }
            
            # Save JSON file to shared drive
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_with_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Feedback saved successfully: {file_path}")
            self.progress_updated.emit("Feedback saved successfully!")
            
            self.save_completed.emit(True, f"Feedback saved to: {filename}")
            
        except Exception as e:
            error_msg = f"Failed to save feedback: {str(e)}"
            logger.error(error_msg)
            self.save_completed.emit(False, error_msg)

class SMOOFeedbackDialog(QDialog):
    """SMOO-compatible feedback dialog for bug reports and feature requests"""
    
    def __init__(self, parent=None, shared_drive_handler=None, user_name="Anonymous"):
        super().__init__(parent)
        
        self.shared_drive_handler = shared_drive_handler
        self.user_name = user_name
        self.save_thread = None
        
        # Get feedback folder path from shared drive handler
        self.feedback_folder_path = self._get_feedback_folder_path()
        
        self.setWindowTitle("📝 System Feedback")
        self.setModal(True)
        self.resize(600, 700)
        
        self.init_ui()
        self.apply_styles()
    
    def _get_feedback_folder_path(self):
        """Get the base path for feedback storage in SMOO shared drive"""
        if self.shared_drive_handler:
            try:
                # Get the shared drive root path
                root_path = self.shared_drive_handler.get_shared_drive_root()
                # Create feedback path at root level
                feedback_path = os.path.join(root_path, "User_Feedback")
                return feedback_path
            except Exception as e:
                logger.error(f"Could not get shared drive root path: {e}")
        
        # Fallback to a safe default
        return os.path.expanduser("~/Desktop/CAESER_Feedback")
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("📝 Submit Feedback")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Help us improve the CAESER Water Levels Monitoring System by sharing your feedback, "
                           "bug reports, or feature requests. Your input is valuable!")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(desc_label)
        
        # User info group
        user_group = QGroupBox("User Information")
        user_layout = QFormLayout()
        
        self.user_name_edit = QLineEdit(self.user_name)
        self.user_name_edit.setPlaceholderText("Your name or identifier")
        user_layout.addRow("Name:", self.user_name_edit)
        
        self.contact_edit = QLineEdit()
        self.contact_edit.setPlaceholderText("Email or contact info (optional)")
        user_layout.addRow("Contact:", self.contact_edit)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Feedback group
        feedback_group = QGroupBox("Feedback Details")
        feedback_layout = QVBoxLayout()
        
        # Feedback type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "🐛 Bug Report",
            "💡 Feature Request", 
            "📝 General Feedback",
            "❓ Question/Support",
            "⚡ Performance Issue"
        ])
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        feedback_layout.addLayout(type_layout)
        
        # Subject
        self.subject_edit = QLineEdit()
        self.subject_edit.setPlaceholderText("Brief description of your feedback")
        feedback_layout.addWidget(QLabel("Subject:"))
        feedback_layout.addWidget(self.subject_edit)
        
        # Details
        feedback_layout.addWidget(QLabel("Details:"))
        self.details_edit = QTextEdit()
        self.details_edit.setPlaceholderText(
            "Please provide detailed information:\n\n"
            "For bugs:\n"
            "- What you were trying to do\n"
            "- What happened vs. what you expected\n"
            "- Steps to reproduce\n\n"
            "For features:\n"
            "- What functionality you'd like to see\n"
            "- How it would help your workflow\n\n"
            "For other feedback:\n"
            "- Any relevant details or context"
        )
        self.details_edit.setMinimumHeight(200)
        feedback_layout.addWidget(self.details_edit)
        
        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #007bff; font-style: italic;")
        layout.addWidget(self.progress_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.submit_btn = QPushButton("📤 Submit Feedback")
        self.submit_btn.clicked.connect(self.submit_feedback)
        self.submit_btn.setDefault(True)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.submit_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def apply_styles(self):
        """Apply consistent styling"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                background-color: #f8f9fa;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        
        # Apply button styles
        ButtonStyles.apply_primary_button_style(self.submit_btn)
        ButtonStyles.apply_secondary_button_style(self.cancel_btn)
    
    def validate_input(self):
        """Validate user input before submission"""
        if not self.subject_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a subject for your feedback.")
            self.subject_edit.setFocus()
            return False
        
        if not self.details_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please provide details about your feedback.")
            self.details_edit.setFocus()
            return False
        
        return True
    
    def submit_feedback(self):
        """Submit the feedback"""
        if not self.validate_input():
            return
        
        # Prepare feedback data
        feedback_data = {
            "user_name": self.user_name_edit.text().strip() or "Anonymous",
            "contact": self.contact_edit.text().strip(),
            "feedback_type": self.type_combo.currentText(),
            "subject": self.subject_edit.text().strip(),
            "details": self.details_edit.toPlainText().strip(),
            "timestamp": datetime.now().isoformat(),
            "app_info": {
                "name": "CAESER Water Levels Monitoring System",
                "submission_method": "SMOO Shared Drive"
            }
        }
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Disable submit button during save
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Submitting...")
        
        # Start save thread
        self.save_thread = SMOOFeedbackSaveThread(
            feedback_data, 
            self.shared_drive_handler, 
            self.feedback_folder_path
        )
        
        self.save_thread.progress_updated.connect(self.on_progress_updated)
        self.save_thread.save_completed.connect(self.on_save_completed)
        self.save_thread.start()
    
    def on_progress_updated(self, message):
        """Handle progress updates"""
        self.progress_label.setText(message)
    
    def on_save_completed(self, success, message):
        """Handle save completion"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.submit_btn.setEnabled(True)
        self.submit_btn.setText("📤 Submit Feedback")
        
        if success:
            QMessageBox.information(
                self,
                "Feedback Submitted",
                f"✅ Your feedback has been successfully saved!\n\n"
                f"{message}\n\n"
                "Thank you for helping us improve the system!"
            )
            self.accept()  # Close dialog on success
        else:
            QMessageBox.critical(
                self,
                "Submission Failed",
                f"❌ Failed to submit feedback:\n\n{message}\n\n"
                "Please try again or contact support if the problem persists."
            )
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Stop thread if running
        if self.save_thread and self.save_thread.isRunning():
            self.save_thread.quit()
            self.save_thread.wait()
        
        super().closeEvent(event)