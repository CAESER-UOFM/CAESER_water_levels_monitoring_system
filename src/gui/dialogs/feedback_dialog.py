# -*- coding: utf-8 -*-
"""
Feedback Dialog - For submitting bug reports and feature requests
Uploads feedback to Google Drive for developer review
"""

import json
import logging
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

class FeedbackUploadThread(QThread):
    """Thread for uploading feedback to Google Drive"""
    
    progress_updated = pyqtSignal(str)  # Status message
    upload_completed = pyqtSignal(bool, str)  # Success, message
    
    def __init__(self, feedback_data, drive_service, folder_id):
        super().__init__()
        self.feedback_data = feedback_data
        self.drive_service = drive_service
        self.folder_id = folder_id
    
    def ensure_feedback_folder_exists(self):
        """Ensure the App_Feedback and general_feedback subfolders exist"""
        try:
            parent_folder_id = self.folder_id  # This is the parent folder ID
            
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
                    parent_folder_id = None  # Use root folder as fallback
            
            # First, ensure "App_Feedback" subfolder exists
            self.progress_updated.emit("Searching for App_Feedback subfolder...")
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
                    logger.info(f"Found existing App_Feedback subfolder: {folder_name} (ID: {app_feedback_folder_id})")
                    self.progress_updated.emit(f"Using existing App_Feedback folder: {folder_name}")
            except Exception as e:
                logger.warning(f"Error searching for App_Feedback subfolder: {e}")
            
            # Create App_Feedback subfolder if it doesn't exist
            if not app_feedback_folder_id:
                self.progress_updated.emit("Creating App_Feedback subfolder...")
                
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
                logger.info(f"Created App_Feedback subfolder: {folder_name} (ID: {app_feedback_folder_id})")
                self.progress_updated.emit(f"Created App_Feedback folder: {folder_name}")
            
            # Now ensure "general_feedback" subfolder exists within App_Feedback
            self.progress_updated.emit("Searching for general_feedback subfolder...")
            try:
                query = f"name='general_feedback' and mimeType='application/vnd.google-apps.folder' and '{app_feedback_folder_id}' in parents and trashed=false"
                
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
                    logger.info(f"Found existing general_feedback subfolder: {folder_name} (ID: {folder_id})")
                    self.progress_updated.emit(f"Using existing general_feedback folder: {folder_name}")
                    return folder_id
            except Exception as e:
                logger.warning(f"Error searching for general_feedback subfolder: {e}")
            
            # Create general_feedback subfolder
            self.progress_updated.emit("Creating general_feedback subfolder...")
            
            folder_metadata = {
                'name': 'general_feedback',
                'mimeType': 'application/vnd.google-apps.folder',
                'description': 'General user feedback and bug reports from CAESER Water Levels Monitoring System'
            }
            
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
            
            logger.info(f"Created general_feedback subfolder: {folder_name} (ID: {folder_id}) in App_Feedback: {parents}")
            self.progress_updated.emit(f"Created general_feedback folder: {folder_name}")
            
            return folder_id
            
        except Exception as e:
            logger.error(f"Error ensuring feedback folder structure: {e}")
            # If we can't create or access the subfolders, try to use the parent folder directly
            logger.warning("Using parent folder as fallback for feedback")
            return self.folder_id
    
    def run(self):
        """Upload feedback to Google Drive"""
        try:
            self.progress_updated.emit("Preparing feedback data...")
            
            # Ensure the feedback folder exists
            actual_folder_id = self.ensure_feedback_folder_exists()
            
            # Create filename with timestamp and type
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            feedback_type = self.feedback_data.get('type', 'feedback').lower().replace(' ', '_')
            filename = f"{feedback_type}_{timestamp}.json"
            
            self.progress_updated.emit("Creating feedback file...")
            
            # Convert feedback data to JSON
            json_content = json.dumps(self.feedback_data, indent=2, default=str)
            
            self.progress_updated.emit("Uploading to Google Drive...")
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'description': f"User feedback: {self.feedback_data.get('type', 'General')} - {self.feedback_data.get('subject', 'No subject')}"
            }
            
            # Add parent folder if we have one
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
            
            self.progress_updated.emit("Upload completed successfully!")
            
            # Return success with file info
            file_info = f"File ID: {file.get('id')}"
            self.upload_completed.emit(True, file_info)
            
        except Exception as e:
            logger.error(f"Error uploading feedback: {e}")
            self.upload_completed.emit(False, str(e))

class FeedbackDialog(QDialog):
    """Dialog for collecting and submitting user feedback"""
    
    def __init__(self, parent=None, drive_service=None, user_name=None):
        super().__init__(parent)
        self.drive_service = drive_service
        self.user_name = user_name or "Anonymous"
        self.feedback_folder_id = self.get_or_create_feedback_folder_id()
        self.upload_thread = None
        
        self.setup_ui()
        self.setModal(True)
    
    def get_or_create_feedback_folder_id(self):
        """Get the parent folder ID where feedback subfolder will be created"""
        # The provided folder ID is the PARENT folder where we'll create a feedback subfolder
        parent_folder_id = "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"
        
        # If drive service is available, we can verify the parent folder exists
        if self.drive_service:
            try:
                # Try to access the parent folder
                service = self.drive_service.get_service()
                if not service:
                    raise Exception("Google Drive service not available")
                folder = service.files().get(fileId=parent_folder_id).execute()
                logger.info(f"Using parent folder for feedback: {folder.get('name')}")
                return parent_folder_id
            except Exception as e:
                logger.warning(f"Parent folder not accessible: {e}")
                # Will try to create feedback folder in root during upload
                return None
        
        # If no drive service, return the parent ID (will be handled during upload)
        return parent_folder_id
    
    def setup_ui(self):
        """Setup the feedback dialog UI"""
        self.setWindowTitle("Submit Feedback - CAESER Water Levels Monitoring")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_label = QLabel("Submit Feedback")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            "Help us improve the CAESER Water Levels Monitoring System by reporting bugs "
            "or suggesting new features. Your feedback will be sent to the development team."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(desc_label)
        
        # Feedback form
        form_group = QGroupBox("Feedback Details")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        # Feedback type
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Bug Report",
            "Feature Request", 
            "Enhancement Suggestion",
            "Data Issue",
            "Performance Issue",
            "User Interface Issue",
            "Documentation Issue",
            "General Feedback"
        ])
        self.type_combo.setCurrentText("Bug Report")
        form_layout.addRow("Type:", self.type_combo)
        
        # Subject
        self.subject_edit = QLineEdit()
        self.subject_edit.setPlaceholderText("Brief description of the issue or suggestion")
        form_layout.addRow("Subject:", self.subject_edit)
        
        # Priority (for bug reports)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Component
        self.component_combo = QComboBox()
        self.component_combo.addItems([
            "General",
            "Water Level Tab",
            "Barologger Tab", 
            "Recharge Tab",
            "Database Management",
            "Data Import/Export",
            "Plotting/Visualization",
            "Google Drive Integration",
            "User Authentication",
            "Performance",
            "Other"
        ])
        form_layout.addRow("Component:", self.component_combo)
        
        main_layout.addWidget(form_group)
        
        # Detailed description
        desc_group = QGroupBox("Detailed Description")
        desc_layout = QVBoxLayout(desc_group)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(
            "Please provide detailed information:\n\n"
            "For Bug Reports:\n"
            "- Steps to reproduce the issue\n"
            "- Expected behavior\n"
            "- Actual behavior\n"
            "- Any error messages\n\n"
            "For Feature Requests:\n"
            "- Describe the desired functionality\n"
            "- Explain how it would be used\n"
            "- Any specific requirements"
        )
        self.description_edit.setMinimumHeight(200)
        desc_layout.addWidget(self.description_edit)
        
        main_layout.addWidget(desc_group)
        
        # Contact info (optional)
        contact_group = QGroupBox("Contact Information (Optional)")
        contact_layout = QFormLayout(contact_group)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("your.email@example.com (for follow-up)")
        contact_layout.addRow("Email:", self.email_edit)
        
        main_layout.addWidget(contact_group)
        
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
        ButtonStyles.apply_button_style(self.cancel_btn, 'cancel')
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.submit_btn = QPushButton("Submit Feedback")
        ButtonStyles.apply_button_style(self.submit_btn, 'primary')
        self.submit_btn.clicked.connect(self.submit_feedback)
        button_layout.addWidget(self.submit_btn)
        
        main_layout.addLayout(button_layout)
        
        # Connect type change to update priority visibility
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        
        # Focus on subject field
        self.subject_edit.setFocus()
    
    def on_type_changed(self, feedback_type):
        """Handle feedback type change"""
        # Show/hide priority based on type
        if feedback_type == "Bug Report":
            self.priority_combo.setVisible(True)
        else:
            self.priority_combo.setVisible(True)  # Keep visible for all types
    
    def validate_form(self):
        """Validate form inputs"""
        if not self.subject_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", 
                              "Please enter a subject for your feedback.")
            self.subject_edit.setFocus()
            return False
        
        if not self.description_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", 
                              "Please provide a detailed description.")
            self.description_edit.setFocus()
            return False
        
        return True
    
    def submit_feedback(self):
        """Submit feedback to Google Drive"""
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
            "user": self.user_name,
            "type": self.type_combo.currentText(),
            "subject": self.subject_edit.text().strip(),
            "priority": self.priority_combo.currentText(),
            "component": self.component_combo.currentText(),
            "description": self.description_edit.toPlainText().strip(),
            "email": self.email_edit.text().strip() if self.email_edit.text().strip() else None,
            "app_version": "1.0.0",  # You might want to get this dynamically
            "submission_id": f"{self.user_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Start upload thread
        self.upload_thread = FeedbackUploadThread(
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
            self.status_label.setText("Feedback submitted successfully!")
            self.status_label.setStyleSheet("color: #28a745; font-style: italic;")
            
            QMessageBox.information(self, "Success", 
                                  "Thank you for your feedback! It has been successfully submitted "
                                  "to the development team for review.")
            self.accept()
        else:
            self.status_label.setText(f"Upload failed: {message}")
            self.status_label.setStyleSheet("color: #dc3545; font-style: italic;")
            
            QMessageBox.critical(self, "Upload Error", 
                               f"Failed to submit feedback:\n{message}\n\n"
                               "Please check your internet connection and try again.")
    
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.upload_thread and self.upload_thread.isRunning():
            reply = QMessageBox.question(self, "Cancel Upload", 
                                       "Feedback is being uploaded. Are you sure you want to cancel?",
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