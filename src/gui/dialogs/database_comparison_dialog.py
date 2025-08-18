"""
Database Comparison Dialog
Shows changes made to the local working copy (wlm_) compared to the cloud database.
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QMessageBox, QGroupBox,
                           QScrollArea, QWidget, QFrame, QTabWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseComparisonDialog(QDialog):
    """Dialog to compare local changes against cloud database"""
    
    def __init__(self, db_manager, change_tracker, cloud_db_handler, user_auth_service, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.change_tracker = change_tracker
        self.cloud_db_handler = cloud_db_handler
        self.user_auth_service = user_auth_service
        
        self.setWindowTitle("Compare Local Changes")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.load_changes()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📊 Database Changes Comparison")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Info section
        info_group = QGroupBox("Database Information")
        info_layout = QVBoxLayout(info_group)
        
        self.db_info_label = QLabel()
        self.db_info_label.setWordWrap(True)
        info_layout.addWidget(self.db_info_label)
        
        layout.addWidget(info_group)
        
        # Create tabs for different types of changes
        self.tab_widget = QTabWidget()
        
        # All Changes tab
        self.all_changes_tab = self.create_all_changes_tab()
        self.tab_widget.addTab(self.all_changes_tab, "📝 All Changes")
        
        # Manual Changes tab
        self.manual_changes_tab = self.create_manual_changes_tab()
        self.tab_widget.addTab(self.manual_changes_tab, "✏️ Manual Changes")
        
        # Automatic Changes tab
        self.auto_changes_tab = self.create_auto_changes_tab()
        self.tab_widget.addTab(self.auto_changes_tab, "🤖 Auto-Sync Changes")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_changes)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.save_to_cloud_btn = QPushButton("☁️ Save to Cloud")
        self.save_to_cloud_btn.clicked.connect(self.save_to_cloud)
        self.save_to_cloud_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; }")
        button_layout.addWidget(self.save_to_cloud_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def create_all_changes_tab(self):
        """Create tab showing all changes"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.all_changes_text = QTextEdit()
        self.all_changes_text.setReadOnly(True)
        self.all_changes_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.all_changes_text)
        
        return widget
        
    def create_manual_changes_tab(self):
        """Create tab showing manual changes only"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.manual_changes_text = QTextEdit()
        self.manual_changes_text.setReadOnly(True)
        self.manual_changes_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.manual_changes_text)
        
        return widget
        
    def create_auto_changes_tab(self):
        """Create tab showing automatic changes only"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.auto_changes_text = QTextEdit()
        self.auto_changes_text.setReadOnly(True)
        self.auto_changes_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.auto_changes_text)
        
        return widget
        
    def load_changes(self):
        """Load and display changes from the change tracker"""
        try:
            # Update database info
            db_name = self.db_manager.current_db or "Unknown"
            project_name = self.db_manager.cloud_project_name or "Unknown"
            user_email = self.user_auth_service.current_user.get('email', 'Unknown') if self.user_auth_service.current_user else "Not logged in"
            
            db_info = f"""
📁 <b>Local Database:</b> {db_name}
☁️ <b>Cloud Project:</b> {project_name}
👤 <b>Current User:</b> {user_email}
📅 <b>Last Check:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            self.db_info_label.setText(db_info)
            
            if not self.change_tracker or not self.change_tracker.changes:
                no_changes_msg = "ℹ️ No changes detected in the local working copy.\n\nThis means your local database matches the cloud version."
                self.all_changes_text.setText(no_changes_msg)
                self.manual_changes_text.setText(no_changes_msg)
                self.auto_changes_text.setText(no_changes_msg)
                self.save_to_cloud_btn.setEnabled(False)
                return
            
            # Get changes
            all_changes = self.change_tracker.changes
            
            # Format all changes
            all_changes_text = self.format_changes(all_changes, "All Changes")
            self.all_changes_text.setText(all_changes_text)
            
            # Filter manual changes
            manual_changes = [change for change in all_changes if change.get('change_type') == 'MANUAL']
            manual_changes_text = self.format_changes(manual_changes, "Manual Changes")
            self.manual_changes_text.setText(manual_changes_text)
            
            # Filter automatic changes
            auto_changes = [change for change in all_changes if change.get('change_type') == 'AUTOMATIC']
            auto_changes_text = self.format_changes(auto_changes, "Automatic Changes")
            self.auto_changes_text.setText(auto_changes_text)
            
            # Enable save button if there are changes
            self.save_to_cloud_btn.setEnabled(len(all_changes) > 0)
            
        except Exception as e:
            logger.error(f"Error loading changes: {e}")
            error_msg = f"❌ Error loading changes: {str(e)}"
            self.all_changes_text.setText(error_msg)
            self.manual_changes_text.setText(error_msg)
            self.auto_changes_text.setText(error_msg)
            
    def format_changes(self, changes, title):
        """Format changes for display"""
        if not changes:
            return f"ℹ️ No {title.lower()} found."
            
        formatted = f"📋 {title} ({len(changes)} total)\n"
        formatted += "=" * 60 + "\n\n"
        
        for i, change in enumerate(changes, 1):
            change_type = change.get('change_type', 'UNKNOWN')
            action = change.get('action', 'UNKNOWN')
            table_name = change.get('table_name', 'unknown_table')
            description = change.get('description', 'No description')
            timestamp = change.get('timestamp', 'Unknown time')
            context = change.get('context', {})
            
            # Format timestamp
            try:
                if timestamp != 'Unknown time':
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted_time = timestamp
            except:
                formatted_time = str(timestamp)
            
            formatted += f"🔸 Change #{i}\n"
            formatted += f"   Type: {change_type}\n"
            formatted += f"   Action: {action}\n"
            formatted += f"   Table: {table_name}\n"
            formatted += f"   Description: {description}\n"
            formatted += f"   Time: {formatted_time}\n"
            
            if context:
                formatted += f"   Context: {context}\n"
                
            formatted += "\n"
            
        return formatted
        
    def save_to_cloud(self):
        """Trigger save to cloud from parent window"""
        try:
            # Close this dialog first
            self.accept()
            
            # Get parent window and trigger save
            if self.parent():
                parent = self.parent()
                if hasattr(parent, '_save_to_cloud'):
                    success = parent._save_to_cloud()
                    if success:
                        QMessageBox.information(self, "Success", "Changes saved to cloud successfully!")
                    else:
                        QMessageBox.warning(self, "Failed", "Failed to save changes to cloud.")
                else:
                    QMessageBox.warning(self, "Error", "Cannot trigger save from comparison dialog.")
            else:
                QMessageBox.warning(self, "Error", "Parent window not available.")
                
        except Exception as e:
            logger.error(f"Error triggering save to cloud: {e}")
            QMessageBox.critical(self, "Error", f"Error saving to cloud: {str(e)}")