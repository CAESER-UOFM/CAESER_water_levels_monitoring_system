# -*- coding: utf-8 -*-
"""
SMOO Water Levels Protocol Feedback Dialog
For collecting CAESER team feedback on water levels processing protocols
Saves feedback directly to SMOO shared drive
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
    QMessageBox, QFormLayout, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from ..utils.button_styles import ButtonStyles

logger = logging.getLogger(__name__)

class SMOOProtocolFeedbackSaveThread(QThread):
    """Thread for saving protocol feedback to SMOO shared drive"""
    
    progress_updated = pyqtSignal(str)  # Status message
    save_completed = pyqtSignal(bool, str)  # Success, message
    
    def __init__(self, feedback_data, shared_drive_handler, feedback_folder_path):
        super().__init__()
        self.feedback_data = feedback_data
        self.shared_drive_handler = shared_drive_handler
        self.feedback_folder_path = feedback_folder_path
    
    def ensure_protocol_feedback_folder_exists(self):
        """Ensure the water levels protocol feedback folders exist in SMOO"""
        try:
            self.progress_updated.emit("Checking protocol feedback folder structure...")
            
            # Create base App_Feedback folder if it doesn't exist
            app_feedback_path = os.path.join(self.feedback_folder_path, "App_Feedback")
            if not os.path.exists(app_feedback_path):
                self.progress_updated.emit("Creating App_Feedback folder...")
                os.makedirs(app_feedback_path, exist_ok=True)
                logger.info(f"Created App_Feedback folder: {app_feedback_path}")
            
            # Create water_levels_protocol_feedbacks subfolder
            protocol_feedback_path = os.path.join(app_feedback_path, "water_levels_protocol_feedbacks")
            if not os.path.exists(protocol_feedback_path):
                self.progress_updated.emit("Creating protocol feedback subfolder...")
                os.makedirs(protocol_feedback_path, exist_ok=True)
                logger.info(f"Created protocol feedback subfolder: {protocol_feedback_path}")
            
            return protocol_feedback_path
            
        except Exception as e:
            logger.error(f"Error ensuring protocol feedback folder exists: {e}")
            raise
    
    def run(self):
        """Save protocol feedback to SMOO shared drive"""
        try:
            self.progress_updated.emit("Starting protocol feedback save...")
            
            # Ensure protocol feedback folder structure exists
            target_folder = self.ensure_protocol_feedback_folder_exists()
            
            # Generate unique filename with well information
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            well_info = self.feedback_data.get('well_number', 'unknown')
            filename = f"protocol_feedback_{timestamp}_well_{well_info}_{self.feedback_data.get('user_name', 'anonymous')}.json"
            file_path = os.path.join(target_folder, filename)
            
            self.progress_updated.emit("Saving protocol feedback file...")
            
            # Prepare feedback data with metadata
            feedback_with_metadata = {
                "submission_info": {
                    "timestamp": datetime.now().isoformat(),
                    "user_name": self.feedback_data.get('user_name', 'Anonymous'),
                    "app_version": "CAESER Water Levels Monitor - Protocol Feedback",
                    "submission_method": "SMOO Shared Drive",
                    "feedback_type": "Water Levels Protocol"
                },
                "well_context": {
                    "well_number": self.feedback_data.get('well_number'),
                    "data_info": self.feedback_data.get('current_data_info', {})
                },
                "protocol_feedback": self.feedback_data
            }
            
            # Save JSON file to shared drive
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_with_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Protocol feedback saved successfully: {file_path}")
            self.progress_updated.emit("Protocol feedback saved successfully!")
            
            self.save_completed.emit(True, f"Protocol feedback saved to: {filename}")
            
        except Exception as e:
            error_msg = f"Failed to save protocol feedback: {str(e)}"
            logger.error(error_msg)
            self.save_completed.emit(False, error_msg)

class SMOOWaterLevelsProtocolFeedbackDialog(QDialog):
    """SMOO-compatible dialog for collecting CAESER team feedback on water levels processing protocols"""
    
    def __init__(self, parent=None, shared_drive_handler=None, user_name=None, well_number=None, current_data_info=None):
        super().__init__(parent)
        
        self.shared_drive_handler = shared_drive_handler
        self.user_name = user_name or "Anonymous"
        self.well_number = well_number or "Unknown"
        self.current_data_info = current_data_info or {}
        self.save_thread = None
        
        # Get feedback folder path from shared drive handler
        self.feedback_folder_path = self._get_feedback_folder_path()
        
        self.setWindowTitle("📋 Water Levels Protocol Feedback")
        self.setModal(True)
        self.resize(700, 800)
        
        self.setup_ui()
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
        return os.path.expanduser("~/Desktop/CAESER_Protocol_Feedback")
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout()
        
        # Title and description
        title_label = QLabel("📋 Water Levels Protocol Feedback")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "This form is specifically designed for CAESER team members to provide feedback on water levels "
            "data processing protocols, methodologies, and workflow improvements."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin: 10px 0; font-style: italic;")
        layout.addWidget(desc_label)
        
        # Context information
        context_group = QGroupBox("Current Data Context")
        context_layout = QFormLayout()
        
        # Well number (read-only)
        well_label = QLabel(f"<b>{self.well_number}</b>")
        context_layout.addRow("Well Number:", well_label)
        
        # Data info if available
        if self.current_data_info:
            if 'start_date' in self.current_data_info:
                context_layout.addRow("Data Period:", 
                                    QLabel(f"{self.current_data_info['start_date']} to {self.current_data_info['end_date']}"))
            if 'total_points' in self.current_data_info:
                context_layout.addRow("Data Points:", 
                                    QLabel(f"{self.current_data_info['total_points']:,}"))
        
        context_group.setLayout(context_layout)
        layout.addWidget(context_group)
        
        # User information
        user_group = QGroupBox("Team Member Information")
        user_layout = QFormLayout()
        
        self.user_name_edit = QLineEdit(self.user_name)
        self.user_name_edit.setPlaceholderText("Your name or CAESER team ID")
        user_layout.addRow("Name:", self.user_name_edit)
        
        self.role_edit = QLineEdit()
        self.role_edit.setPlaceholderText("Your role (e.g., Researcher, Graduate Student, PI)")
        user_layout.addRow("Role:", self.role_edit)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Feedback classification
        feedback_group = QGroupBox("Protocol Feedback Details")
        feedback_layout = QVBoxLayout()
        
        # Feedback category
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "🔄 Data Processing Workflow",
            "📊 Analysis Methodology", 
            "🛠️ Tool/Software Improvement",
            "📋 Protocol Documentation",
            "⚠️ Quality Control Process",
            "🎯 Accuracy/Validation Issue",
            "💡 General Process Improvement"
        ])
        category_layout.addWidget(self.category_combo)
        category_layout.addStretch()
        
        feedback_layout.addLayout(category_layout)
        
        # Priority level
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("Priority:"))
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems([
            "🟢 Low - Enhancement suggestion",
            "🟡 Medium - Process improvement",
            "🟠 High - Affects data quality",
            "🔴 Critical - Blocking workflow"
        ])
        feedback_layout.addLayout(priority_layout)
        priority_layout.addWidget(self.priority_combo)
        priority_layout.addStretch()
        
        # Subject
        self.subject_edit = QLineEdit()
        self.subject_edit.setPlaceholderText("Brief summary of the protocol feedback")
        feedback_layout.addWidget(QLabel("Subject:"))
        feedback_layout.addWidget(self.subject_edit)
        
        # Detailed description
        feedback_layout.addWidget(QLabel("Detailed Feedback:"))
        self.details_edit = QTextEdit()
        self.details_edit.setPlaceholderText(
            "Please provide detailed feedback about the water levels processing protocol:\n\n"
            "For workflow issues:\n"
            "- Which step in the process is problematic?\n"
            "- What specific challenges are you encountering?\n"
            "- How does this affect your analysis?\n\n"
            "For methodology improvements:\n"
            "- What changes would improve the protocol?\n"
            "- Are there literature references or best practices to consider?\n"
            "- How would this benefit the overall data quality?\n\n"
            "For tool improvements:\n"
            "- Which features are missing or need enhancement?\n"
            "- How would the improvement streamline your workflow?\n"
            "- Any specific technical requirements?\n\n"
            "Please be as specific as possible to help us improve the system."
        )
        self.details_edit.setMinimumHeight(200)
        feedback_layout.addWidget(self.details_edit)
        
        # Additional options
        options_layout = QVBoxLayout()
        
        self.follow_up_cb = QCheckBox("I'm available for follow-up discussion")
        self.follow_up_cb.setToolTip("Check this if you're willing to discuss this feedback further with the development team")
        options_layout.addWidget(self.follow_up_cb)
        
        self.urgent_cb = QCheckBox("This feedback is time-sensitive")
        self.urgent_cb.setToolTip("Check this if this feedback needs immediate attention")
        options_layout.addWidget(self.urgent_cb)
        
        feedback_layout.addLayout(options_layout)
        
        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)
        
        # Progress indicators
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
        
        self.submit_btn = QPushButton("📤 Submit Protocol Feedback")
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
                border-color: #6f42c1;
                outline: none;
            }
            QCheckBox {
                margin: 5px 0;
            }
        """)
        
        # Apply button styles
        ButtonStyles.apply_primary_button_style(self.submit_btn)
        ButtonStyles.apply_secondary_button_style(self.cancel_btn)
    
    def validate_input(self):
        """Validate user input before submission"""
        if not self.subject_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a subject for your protocol feedback.")
            self.subject_edit.setFocus()
            return False
        
        if not self.details_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please provide detailed feedback about the protocol.")
            self.details_edit.setFocus()
            return False
        
        if len(self.details_edit.toPlainText().strip()) < 20:
            QMessageBox.warning(self, "Validation Error", "Please provide more detailed feedback (at least 20 characters).")
            self.details_edit.setFocus()
            return False
        
        return True
    
    def submit_feedback(self):
        """Submit the protocol feedback"""
        if not self.validate_input():
            return
        
        # Prepare feedback data
        feedback_data = {
            "user_name": self.user_name_edit.text().strip() or "Anonymous",
            "role": self.role_edit.text().strip(),
            "well_number": self.well_number,
            "current_data_info": self.current_data_info,
            "feedback_category": self.category_combo.currentText(),
            "priority_level": self.priority_combo.currentText(),
            "subject": self.subject_edit.text().strip(),
            "detailed_feedback": self.details_edit.toPlainText().strip(),
            "follow_up_available": self.follow_up_cb.isChecked(),
            "time_sensitive": self.urgent_cb.isChecked(),
            "timestamp": datetime.now().isoformat(),
            "protocol_info": {
                "feedback_type": "Water Levels Protocol",
                "submission_context": "Water Level Edit Dialog",
                "app_version": "CAESER Water Levels Monitor"
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
        self.save_thread = SMOOProtocolFeedbackSaveThread(
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
        self.submit_btn.setText("📤 Submit Protocol Feedback")
        
        if success:
            QMessageBox.information(
                self,
                "Protocol Feedback Submitted",
                f"✅ Your protocol feedback has been successfully saved!\n\n"
                f"{message}\n\n"
                "Thank you for helping improve our water levels processing protocols!"
            )
            self.accept()  # Close dialog on success
        else:
            QMessageBox.critical(
                self,
                "Submission Failed",
                f"❌ Failed to submit protocol feedback:\n\n{message}\n\n"
                "Please try again or contact the development team if the problem persists."
            )
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Stop thread if running
        if self.save_thread and self.save_thread.isRunning():
            self.save_thread.quit()
            self.save_thread.wait()
        
        super().closeEvent(event)