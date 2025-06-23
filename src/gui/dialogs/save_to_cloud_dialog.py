from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QDialogButtonBox, QPushButton)
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class SaveToCloudDialog(QDialog):
    """Dialog for saving database changes to cloud with change tracking"""
    
    def __init__(self, project_name, user_name, change_tracker=None, parent=None):
        """
        Initialize the save to cloud dialog.
        
        Args:
            project_name: Name of the project being saved
            user_name: Name of the current user
            change_tracker: Optional ChangeTracker instance for showing tracked changes
            parent: Parent widget
        """
        super().__init__(parent)
        self.project_name = project_name
        self.user_name = user_name
        self.change_tracker = change_tracker
        self.changes_description = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Save to Cloud - {self.project_name}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        
        # Project info
        project_label = QLabel(f"<b>Project:</b> {self.project_name}")
        layout.addWidget(project_label)
        
        # User info
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("<b>User:</b>"))
        user_label = QLabel(self.user_name)
        user_layout.addWidget(user_label)
        user_layout.addStretch()
        layout.addLayout(user_layout)
        
        # Separator
        layout.addSpacing(10)
        
        # Show tracked changes if available
        if self.change_tracker and self.change_tracker.changes:
            changes_summary = self.change_tracker.get_changes_summary()
            
            # Change summary section
            summary_label = QLabel("<b>Changes Summary:</b>")
            layout.addWidget(summary_label)
            
            summary_text = f"""
<b>Total Changes:</b> {changes_summary['total']} 
(<font color='#2E7D32'>{changes_summary['manual']} manual</font>, 
<font color='#1976D2'>{changes_summary['automatic']} automatic</font>)

<b>Detected Changes:</b><br/>
{self.change_tracker.get_manual_changes_description() or 'No manual changes detected'}
            """.strip()
            
            summary_display = QLabel(summary_text)
            summary_display.setWordWrap(True)
            summary_display.setStyleSheet("""
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px;
                margin: 5px 0px;
            """)
            layout.addWidget(summary_display)
            
            layout.addSpacing(10)
        
        # Change description
        desc_label = QLabel("<b>Describe your changes:</b>")
        desc_label.setStyleSheet("margin-top: 10px;")
        layout.addWidget(desc_label)
        
        self.change_text = QTextEdit()
        
        # Pre-populate with tracked changes if available
        if self.change_tracker and self.change_tracker.changes:
            suggested_description = self.change_tracker.get_manual_changes_description()
            if suggested_description and suggested_description != "No manual changes made":
                self.change_text.setPlainText(suggested_description)
        
        self.change_text.setPlaceholderText(
            "Please describe the changes you made...\n\n"
            "Examples:\n"
            "- Added water level readings for January 2024\n"
            "- Updated site coordinates for Location A\n"
            "- Corrected barologger data for Site B\n"
            "- Added new wells for monitoring project"
        )
        self.change_text.setMinimumHeight(150)
        layout.addWidget(self.change_text)
        
        # Warning about required description
        warning_label = QLabel("<i>* Change description is required</i>")
        warning_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(warning_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        
        # Customize button text
        save_button = button_box.button(QDialogButtonBox.Save)
        save_button.setText("Save to Cloud")
        
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # Focus on text edit
        self.change_text.setFocus()
        
    def validate_and_accept(self):
        """Validate the form and accept if valid"""
        description = self.change_text.toPlainText().strip()
        
        if not description:
            # Show error - description is required
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Description Required",
                "Please provide a description of your changes before saving."
            )
            self.change_text.setFocus()
            return
            
        self.changes_description = description
        self.accept()
        
    def get_changes_description(self):
        """Get the entered changes description"""
        return self.changes_description