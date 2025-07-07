# -*- coding: utf-8 -*-
"""
Water Levels Protocol Feedback Dialog

Specialized feedback system for CAESER team members to track suggestions
and improvements for water levels data processing protocols. This system
helps refine manual processing protocols that follow CAESER-specific methods
beyond standard USGS protocols.

@author: claude
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QLineEdit, QGroupBox, QProgressBar,
    QMessageBox, QFormLayout, QFrame, QCheckBox, QScrollArea,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)

class WaterLevelsProtocolFeedbackUploadThread(QThread):
    """Thread for uploading water levels protocol feedback to Google Drive"""
    
    progress_updated = pyqtSignal(str)  # Status message
    upload_completed = pyqtSignal(bool, str)  # Success, message
    
    def __init__(self, feedback_data, drive_service, folder_id):
        super().__init__()
        self.feedback_data = feedback_data
        self.drive_service = drive_service
        self.folder_id = folder_id
    
    def ensure_protocol_feedback_folder_exists(self):
        """Ensure the water levels protocol feedback subfolder exists within App_Feedback"""
        try:
            parent_folder_id = self.folder_id  # This should be the main parent folder, we'll find App_Feedback first
            
            self.progress_updated.emit("Checking parent folder...")
            
            # Verify parent folder exists
            if parent_folder_id:
                try:
                    service = self.drive_service.get_service()
                    if not service:
                        raise Exception("Google Drive service not available")
                    parent_folder = service.files().get(fileId=parent_folder_id).execute()
                    logger.info(f"Parent folder accessible: {parent_folder.get('name')}")
                except Exception as e:
                    logger.warning(f"Could not access parent folder {parent_folder_id}: {e}")
                    parent_folder_id = None
            
            # First, find or create the App_Feedback folder
            self.progress_updated.emit("Searching for App_Feedback folder...")
            app_feedback_folder_id = None
            try:
                if parent_folder_id:
                    query = f"name='App_Feedback' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
                else:
                    query = "name='App_Feedback' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                
                service = self.drive_service.get_service()
                if not service:
                    raise Exception("Google Drive service not available")
                results = service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, parents)'
                ).execute()
                
                files = results.get('files', [])
                if files:
                    existing_folder = files[0]
                    app_feedback_folder_id = existing_folder['id']
                    folder_name = existing_folder['name']
                    logger.info(f"Found existing App_Feedback folder: {folder_name} (ID: {app_feedback_folder_id})")
                    self.progress_updated.emit(f"Using existing App_Feedback folder: {folder_name}")
            except Exception as e:
                logger.warning(f"Error searching for App_Feedback folder: {e}")
            
            # Create App_Feedback folder if it doesn't exist
            if not app_feedback_folder_id:
                self.progress_updated.emit("Creating App_Feedback folder...")
                
                folder_metadata = {
                    'name': 'App_Feedback',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'description': 'User feedback and bug reports from CAESER Water Levels Monitoring System'
                }
                
                if parent_folder_id:
                    folder_metadata['parents'] = [parent_folder_id]
                
                service = self.drive_service.get_service()
                if not service:
                    raise Exception("Google Drive service not available")
                folder = service.files().create(
                    body=folder_metadata,
                    fields='id,name,webViewLink,parents'
                ).execute()
                
                app_feedback_folder_id = folder.get('id')
                folder_name = folder.get('name')
                logger.info(f"Created App_Feedback folder: {folder_name} (ID: {app_feedback_folder_id})")
                self.progress_updated.emit(f"Created App_Feedback folder: {folder_name}")
            
            # Search for existing "water_levels_protocol_feedbacks" subfolder within App_Feedback
            self.progress_updated.emit("Searching for protocol feedback subfolder...")
            try:
                query = f"name='water_levels_protocol_feedbacks' and mimeType='application/vnd.google-apps.folder' and '{app_feedback_folder_id}' in parents and trashed=false"
                
                service = self.drive_service.get_service()
                if not service:
                    raise Exception("Google Drive service not available")
                results = service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, parents)'
                ).execute()
                
                files = results.get('files', [])
                if files:
                    existing_folder = files[0]
                    folder_id = existing_folder['id']
                    folder_name = existing_folder['name']
                    logger.info(f"Found existing protocol feedback subfolder: {folder_name} (ID: {folder_id})")
                    self.progress_updated.emit(f"Using existing subfolder: {folder_name}")
                    return folder_id
            except Exception as e:
                logger.warning(f"Error searching for protocol feedback subfolder: {e}")
            
            # Create new water_levels_protocol_feedbacks subfolder within App_Feedback
            self.progress_updated.emit("Creating protocol feedback subfolder...")
            
            folder_metadata = {
                'name': 'water_levels_protocol_feedbacks',
                'mimeType': 'application/vnd.google-apps.folder',
                'description': 'CAESER team feedback for water levels data processing protocol improvements'
            }
            
            # Set parent to App_Feedback folder, not the main parent
            folder_metadata['parents'] = [app_feedback_folder_id]
            
            service = self.drive_service.get_service()
            if not service:
                raise Exception("Google Drive service not available")
            folder = service.files().create(
                body=folder_metadata,
                fields='id,name,webViewLink,parents'
            ).execute()
            
            folder_id = folder.get('id')
            folder_name = folder.get('name')
            parents = folder.get('parents', [])
            
            logger.info(f"Created protocol feedback subfolder: {folder_name} (ID: {folder_id}) in parent: {parents}")
            self.progress_updated.emit(f"Created subfolder: {folder_name}")
            
            return folder_id
            
        except Exception as e:
            logger.error(f"Error ensuring protocol feedback subfolder exists: {e}")
            return self.folder_id  # Fallback to parent folder
    
    def run(self):
        """Upload water levels protocol feedback to Google Drive"""
        try:
            self.progress_updated.emit("Preparing protocol feedback data...")
            
            # Ensure the protocol feedback folder exists
            actual_folder_id = self.ensure_protocol_feedback_folder_exists()
            
            # Create filename with timestamp and well info
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            well_number = self.feedback_data.get('well_number', 'unknown_well').replace('/', '_')
            protocol_type = self.feedback_data.get('protocol_type', 'general').lower().replace(' ', '_')
            filename = f"protocol_{protocol_type}_{well_number}_{timestamp}.json"
            
            self.progress_updated.emit("Creating protocol feedback file...")
            
            # Convert feedback data to JSON
            json_content = json.dumps(self.feedback_data, indent=2, default=str)
            
            self.progress_updated.emit("Uploading to Google Drive...")
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'description': f"Water Levels Protocol Feedback: {self.feedback_data.get('protocol_type', 'General')} - Well {well_number}"
            }
            
            if actual_folder_id:
                file_metadata['parents'] = [actual_folder_id]
            
            # Upload file
            from googleapiclient.http import MediaInMemoryUpload
            media = MediaInMemoryUpload(
                json_content.encode('utf-8'),
                mimetype='application/json',
                resumable=True
            )
            
            service = self.drive_service.get_service()
            if not service:
                raise Exception("Google Drive service not available")
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            self.progress_updated.emit("Protocol feedback uploaded successfully!")
            
            # Return success with file info
            file_info = f"File ID: {file.get('id')}"
            self.upload_completed.emit(True, file_info)
            
        except Exception as e:
            logger.error(f"Error uploading protocol feedback: {e}")
            self.upload_completed.emit(False, str(e))

class WaterLevelsProtocolFeedbackDialog(QDialog):
    """Dialog for collecting CAESER team feedback on water levels processing protocols"""
    
    def __init__(self, parent=None, drive_service=None, user_name=None, well_number=None, current_data_info=None):
        super().__init__(parent)
        self.drive_service = drive_service
        self.user_name = user_name or "Anonymous"
        self.well_number = well_number or "Unknown"
        self.current_data_info = current_data_info or {}
        self.feedback_folder_id = self.get_app_feedback_folder_id()
        self.upload_thread = None
        
        self.setup_ui()
        self.setModal(True)
    
    def get_app_feedback_folder_id(self):
        """Get the App_Feedback folder ID where protocol subfolder will be created"""
        # This should be the existing App_Feedback folder ID
        app_feedback_folder_id = "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"  # This will be updated to actual App_Feedback folder
        
        if self.drive_service:
            try:
                # For now, return the known folder ID
                # In production, this could be retrieved from settings or searched for
                return app_feedback_folder_id
            except Exception as e:
                logger.warning(f"Could not verify App_Feedback folder: {e}")
                return app_feedback_folder_id
        
        return app_feedback_folder_id
    
    def setup_ui(self):
        """Setup the protocol feedback dialog UI"""
        self.setWindowTitle("Water Levels Protocol Feedback - CAESER Team")
        self.setMinimumSize(1000, 750)
        self.resize(1200, 900)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # Header
        header_label = QLabel("Water Levels Processing Protocol Feedback")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            f"Submit feedback for improving CAESER water levels data processing protocols.\n"
            f"Currently reviewing: Well {self.well_number}\n\n"
            "Help us refine our manual processing methods beyond standard USGS protocols "
            "by identifying potential improvements, issues, or better approaches."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px; background-color: #f0f8ff; padding: 10px; border-radius: 5px;")
        main_layout.addWidget(desc_label)
        
        # Current Session Info
        session_group = QGroupBox("Current Session Information")
        session_layout = QFormLayout(session_group)
        
        self.well_info_label = QLabel(f"Well: {self.well_number}")
        self.well_info_label.setStyleSheet("font-weight: bold;")
        session_layout.addRow("Well Number:", self.well_info_label)
        
        # Add data range info if available
        if self.current_data_info:
            data_range = f"{self.current_data_info.get('start_date', 'N/A')} to {self.current_data_info.get('end_date', 'N/A')}"
            data_points = self.current_data_info.get('total_points', 'N/A')
            session_layout.addRow("Data Range:", QLabel(data_range))
            session_layout.addRow("Data Points:", QLabel(str(data_points)))
        
        main_layout.addWidget(session_group)
        
        # Feedback form
        form_group = QGroupBox("Protocol Feedback Details")
        form_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Protocol type/area
        self.protocol_type_combo = QComboBox()
        self.protocol_type_combo.setMinimumWidth(300)
        self.protocol_type_combo.setMinimumHeight(30)
        self.protocol_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.protocol_type_combo.addItems([
            "Manual Spike Correction",
            "Barometric Compensation",
            "Baseline Adjustment",
            "Data Quality Assessment",
            "Flag Assignment Logic",
            "Outlier Detection",
            "Gap Filling Methods",
            "Metadata Handling",
            "Quality Control Checks",
            "Data Validation Rules",
            "Processing Workflow",
            "General Protocol"
        ])
        form_layout.addRow("Protocol Area:", self.protocol_type_combo)
        
        # Issue/Suggestion type
        self.issue_type_combo = QComboBox()
        self.issue_type_combo.setMinimumWidth(300)
        self.issue_type_combo.setMinimumHeight(30)
        self.issue_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.issue_type_combo.addItems([
            "Potential Issue Found",
            "Process Improvement Suggestion", 
            "Alternative Method Proposal",
            "Quality Concern",
            "Efficiency Improvement",
            "Documentation Gap",
            "Best Practice Recommendation",
            "Error Pattern Identified",
            "Validation Issue",
            "General Observation"
        ])
        form_layout.addRow("Feedback Type:", self.issue_type_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setMinimumWidth(200)
        self.priority_combo.setMinimumHeight(30)
        self.priority_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Subject
        self.subject_edit = QLineEdit()
        self.subject_edit.setMinimumWidth(400)
        self.subject_edit.setMinimumHeight(30)
        self.subject_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.subject_edit.setPlaceholderText("Brief summary of the protocol feedback")
        form_layout.addRow("Subject:", self.subject_edit)
        
        main_layout.addWidget(form_group)
        
        # Detailed description
        desc_group = QGroupBox("Detailed Protocol Feedback")
        desc_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        desc_layout = QVBoxLayout(desc_group)
        desc_layout.setContentsMargins(10, 10, 10, 10)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(
            "Please provide detailed information about the protocol feedback:\n\n"
            "• What specific aspect of the protocol needs attention?\n"
            "• What did you observe that prompted this feedback?\n"
            "• How does this affect data quality or processing efficiency?\n"
            "• What alternative approach would you recommend?\n"
            "• Any specific examples or evidence supporting your feedback?\n"
            "• How critical is this issue for our protocol development?\n\n"
            "Be as specific as possible to help improve our processing methods."
        )
        self.description_edit.setMinimumHeight(200)
        self.description_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Enable word wrapping and scrolling
        self.description_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.description_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.description_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        desc_layout.addWidget(self.description_edit)
        
        main_layout.addWidget(desc_group)
        
        # Data context (optional)
        context_group = QGroupBox("Data Context (Optional)")
        context_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        context_layout = QFormLayout(context_group)
        context_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.data_context_edit = QTextEdit()
        self.data_context_edit.setPlaceholderText(
            "Optional: Describe the specific data conditions or context where this issue was observed:\n"
            "• Date range or time period\n"
            "• Data characteristics (spikes, gaps, patterns)\n"
            "• Environmental conditions\n"
            "• Instrument-specific behavior\n"
            "• Comparison with other wells"
        )
        self.data_context_edit.setMinimumHeight(100)
        self.data_context_edit.setMaximumHeight(150)
        self.data_context_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Enable word wrapping and scrolling
        self.data_context_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.data_context_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.data_context_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        context_layout.addRow("Data Context:", self.data_context_edit)
        
        main_layout.addWidget(context_group)
        
        # Team member info
        team_group = QGroupBox("Team Member Information")
        team_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        team_layout = QFormLayout(team_group)
        team_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.team_member_edit = QLineEdit()
        self.team_member_edit.setText(self.user_name)
        self.team_member_edit.setMinimumWidth(300)
        self.team_member_edit.setMinimumHeight(30)
        self.team_member_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.team_member_edit.setPlaceholderText("Your name/ID for follow-up")
        team_layout.addRow("Team Member:", self.team_member_edit)
        
        self.follow_up_check = QCheckBox("Available for follow-up discussion")
        self.follow_up_check.setChecked(True)
        team_layout.addRow("", self.follow_up_check)
        
        main_layout.addWidget(team_group)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        self.status_label.setVisible(False)
        main_layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.submit_btn = QPushButton("Submit Protocol Feedback")
        self.submit_btn.clicked.connect(self.submit_feedback)
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        button_layout.addWidget(self.submit_btn)
        
        main_layout.addLayout(button_layout)
        
        # Focus on subject field
        self.subject_edit.setFocus()
    
    def validate_form(self):
        """Validate form inputs"""
        if not self.subject_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter a subject for your protocol feedback.")
            self.subject_edit.setFocus()
            return False
        
        if not self.description_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", 
                              "Please provide a detailed description of your protocol feedback.")
            self.description_edit.setFocus()
            return False
        
        if not self.team_member_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter your team member name for accountability.")
            self.team_member_edit.setFocus()
            return False
        
        return True
    
    def submit_feedback(self):
        """Submit protocol feedback to Google Drive"""
        if not self.validate_form():
            return
        
        if not self.drive_service:
            QMessageBox.critical(self, "Error", 
                               "Google Drive service not available. Please check your connection.")
            return
        
        # Disable submit button and show progress
        self.submit_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setVisible(True)
        
        # Prepare feedback data
        feedback_data = {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "feedback_type": "water_levels_protocol",
            "team_member": self.team_member_edit.text().strip(),
            "well_number": self.well_number,
            "protocol_type": self.protocol_type_combo.currentText(),
            "issue_type": self.issue_type_combo.currentText(),
            "priority": self.priority_combo.currentText(),
            "subject": self.subject_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "data_context": self.data_context_edit.toPlainText().strip() if self.data_context_edit.toPlainText().strip() else None,
            "current_data_info": self.current_data_info,
            "available_for_followup": self.follow_up_check.isChecked(),
            "app_version": "1.0.0",
            "submission_id": f"protocol_{self.team_member_edit.text().strip()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Start upload thread
        self.upload_thread = WaterLevelsProtocolFeedbackUploadThread(
            feedback_data, self.drive_service, self.feedback_folder_id
        )
        self.upload_thread.progress_updated.connect(self.update_progress)
        self.upload_thread.upload_completed.connect(self.on_upload_completed)
        self.upload_thread.start()
    
    def update_progress(self, message):
        """Update progress status"""
        self.status_label.setText(message)
    
    def on_upload_completed(self, success, message):
        """Handle upload completion"""
        self.progress_bar.setVisible(False)
        self.submit_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("Protocol feedback submitted successfully!")
            self.status_label.setStyleSheet("color: #2e7d32; font-style: italic;")
            
            QMessageBox.information(self, "Success", 
                                  "Thank you for your protocol feedback! It has been successfully submitted "
                                  "to the CAESER team for review and protocol improvement.")
            self.accept()
        else:
            self.status_label.setText(f"Upload failed: {message}")
            self.status_label.setStyleSheet("color: #dc3545; font-style: italic;")
            
            QMessageBox.critical(self, "Upload Error", 
                               f"Failed to submit protocol feedback:\n{message}\n\n"
                               "Please check your internet connection and try again.")
    
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.upload_thread and self.upload_thread.isRunning():
            reply = QMessageBox.question(self, "Cancel Upload", 
                                       "Protocol feedback is being uploaded. Are you sure you want to cancel?",
                                       QMessageBox.Yes | QMessageBox.No, 
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.upload_thread.terminate()
                self.upload_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()