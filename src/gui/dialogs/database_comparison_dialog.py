from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QDialogButtonBox, QPushButton, QComboBox,
                             QTableWidget, QTableWidgetItem, QTabWidget, QWidget,
                             QSplitter, QProgressBar, QMessageBox, QCheckBox,
                             QGroupBox, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import logging
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseComparisonDialog(QDialog):
    """Dialog for comparing local changes against cloud database versions"""
    
    def __init__(self, db_manager, change_tracker, cloud_handler, user_auth_service, parent=None):
        """
        Initialize the database comparison dialog.
        
        Args:
            db_manager: DatabaseManager instance
            change_tracker: ChangeTracker instance  
            cloud_handler: CloudDatabaseHandler instance
            user_auth_service: UserAuthService instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.change_tracker = change_tracker
        self.cloud_handler = cloud_handler
        self.user_auth_service = user_auth_service
        
        # State variables
        self.project_name = getattr(db_manager, 'cloud_project_name', 'Unknown')
        self.current_user = user_auth_service.current_user or "Unknown"
        self.cloud_versions = []
        self.selected_cloud_version = None
        self.proposal_db_path = None
        self.comparison_data = {}
        
        self.setup_ui()
        self.load_cloud_versions()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Database Changes Comparison - {self.project_name}")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        main_layout = QVBoxLayout(self)
        
        # Header section
        self._setup_header_section(main_layout)
        
        # Version selection section
        self._setup_version_selection(main_layout)
        
        # Status section
        self._setup_status_section(main_layout)
        
        # Main comparison area (initially hidden)
        self._setup_comparison_area(main_layout)
        
        # Buttons
        self._setup_buttons(main_layout)
        
    def _setup_header_section(self, layout):
        """Setup the header information section"""
        header_group = QGroupBox("Project Information")
        header_layout = QVBoxLayout(header_group)
        
        # Project and user info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>Project:</b> {self.project_name}"))
        info_layout.addStretch()
        info_layout.addWidget(QLabel(f"<b>User:</b> {self.current_user}"))
        header_layout.addLayout(info_layout)
        
        # Changes summary
        if self.change_tracker and self.change_tracker.changes:
            changes_summary = self.change_tracker.get_changes_summary()
            summary_text = f"""
<b>Local Changes:</b> {changes_summary['total']} total changes 
(<span style='color: #2E7D32'>{changes_summary['manual']} manual</span>, 
<span style='color: #1976D2'>{changes_summary['automatic']} automatic</span>)
<br/>
<b>Affected Tables:</b> {', '.join(changes_summary.get('by_table', {}).keys()) or 'None'}
            """.strip()
            
            summary_label = QLabel(summary_text)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet("""
                background-color: #E8F5E8;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 10px;
                margin: 5px 0px;
            """)
            header_layout.addWidget(summary_label)
        else:
            no_changes_label = QLabel("<b>No local changes detected</b>")
            no_changes_label.setStyleSheet("""
                background-color: #FFF3E0;
                border: 1px solid #FF9800;
                border-radius: 4px;
                padding: 10px;
                margin: 5px 0px;
            """)
            header_layout.addWidget(no_changes_label)
        
        layout.addWidget(header_group)
    
    def _setup_version_selection(self, layout):
        """Setup cloud version selection section"""
        version_group = QGroupBox("Cloud Version Selection")
        version_layout = QVBoxLayout(version_group)
        
        # Version selection
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Compare against:"))
        
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(300)
        self.version_combo.currentTextChanged.connect(self.on_version_selection_changed)
        selection_layout.addWidget(self.version_combo)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_cloud_versions)
        selection_layout.addWidget(self.refresh_btn)
        
        selection_layout.addStretch()
        version_layout.addLayout(selection_layout)
        
        # Version status info
        self.version_status_label = QLabel("Loading cloud versions...")
        self.version_status_label.setWordWrap(True)
        version_layout.addWidget(self.version_status_label)
        
        layout.addWidget(version_group)
    
    def _setup_status_section(self, layout):
        """Setup status and progress section"""
        self.status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(self.status_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Select a cloud version to compare against")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(self.status_group)
    
    def _setup_comparison_area(self, layout):
        """Setup the main comparison display area"""
        self.comparison_group = QGroupBox("Changes Comparison")
        self.comparison_group.setVisible(False)
        comparison_layout = QVBoxLayout(self.comparison_group)
        
        # Create tab widget for different tables
        self.comparison_tabs = QTabWidget()
        comparison_layout.addWidget(self.comparison_tabs)
        
        # Action buttons for comparison
        action_layout = QHBoxLayout()
        
        self.accept_all_btn = QPushButton("Accept All Changes")
        self.accept_all_btn.clicked.connect(self.accept_all_changes)
        self.accept_all_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        action_layout.addWidget(self.accept_all_btn)
        
        self.create_proposal_btn = QPushButton("Save as Proposal")
        self.create_proposal_btn.clicked.connect(self.create_proposal)
        action_layout.addWidget(self.create_proposal_btn)
        
        action_layout.addStretch()
        
        self.reject_all_btn = QPushButton("Cancel")
        self.reject_all_btn.clicked.connect(self.reject)
        action_layout.addWidget(self.reject_all_btn)
        
        comparison_layout.addLayout(action_layout)
        
        layout.addWidget(self.comparison_group)
    
    def _setup_buttons(self, layout):
        """Setup dialog buttons"""
        button_layout = QHBoxLayout()
        
        self.compare_btn = QPushButton("Start Comparison")
        self.compare_btn.clicked.connect(self.start_comparison)
        self.compare_btn.setEnabled(False)
        self.compare_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        button_layout.addWidget(self.compare_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_cloud_versions(self):
        """Load available cloud versions"""
        try:
            self.version_combo.clear()
            self.version_combo.addItem("Loading...", None)
            
            # Get project list from cloud
            projects = self.cloud_handler.list_projects()
            current_project = next((p for p in projects if p['name'] == self.project_name), None)
            
            if current_project:
                self.cloud_versions = [current_project]  # For now, just use the current version
                self.version_combo.clear()
                
                # Add the current cloud version
                version_text = f"Latest Cloud Version ({current_project.get('modified_time', 'Unknown time')})"
                self.version_combo.addItem(version_text, current_project)
                
                # Check if user is working with latest version
                local_version_info = self.cloud_handler.version_manager.get_local_version_info(self.project_name)
                if local_version_info:
                    cloud_time = current_project.get('modified_time', '')
                    local_time = local_version_info.get('local_version_time', '')
                    
                    if cloud_time == local_time:
                        status_text = "✅ You are working with the latest cloud version"
                        status_style = "color: #2E7D32; font-weight: bold;"
                    else:
                        status_text = "⚠️ Your local version may be outdated. Consider downloading the latest version first."
                        status_style = "color: #F57C00; font-weight: bold;"
                else:
                    status_text = "ℹ️ Local version information not available"
                    status_style = "color: #1976D2;"
                
                self.version_status_label.setText(status_text)
                self.version_status_label.setStyleSheet(status_style)
                self.compare_btn.setEnabled(True)
            else:
                self.version_combo.addItem("No cloud versions found", None)
                self.version_status_label.setText("❌ Project not found in cloud")
                self.version_status_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
                
        except Exception as e:
            logger.error(f"Error loading cloud versions: {e}")
            self.version_combo.clear()
            self.version_combo.addItem("Error loading versions", None)
            self.version_status_label.setText(f"❌ Error: {str(e)}")
            self.version_status_label.setStyleSheet("color: #D32F2F;")
    
    def on_version_selection_changed(self):
        """Handle version selection change"""
        current_data = self.version_combo.currentData()
        if current_data:
            self.selected_cloud_version = current_data
            self.compare_btn.setEnabled(True)
            self.status_label.setText("Ready to compare changes")
        else:
            self.selected_cloud_version = None
            self.compare_btn.setEnabled(False)
            self.status_label.setText("Select a valid cloud version")
    
    def start_comparison(self):
        """Start the comparison process"""
        if not self.selected_cloud_version:
            QMessageBox.warning(self, "Warning", "Please select a cloud version to compare against")
            return
        
        if not self.change_tracker.changes:
            QMessageBox.information(self, "Information", "No local changes to compare")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Creating proposal database...")
            
            # Import the ProposalDatabaseCreator
            from ..handlers.proposal_database_creator import ProposalDatabaseCreator
            
            # Create proposal database
            proposal_creator = ProposalDatabaseCreator(self.db_manager, self.change_tracker)
            self.proposal_db_path = proposal_creator.create_temporary_proposal(self.selected_cloud_version)
            
            if not self.proposal_db_path:
                raise Exception("Failed to create proposal database")
            
            self.progress_bar.setValue(50)
            self.status_label.setText("Analyzing changes...")
            
            # Analyze the proposal database
            self.comparison_data = proposal_creator.get_proposal_statistics(self.proposal_db_path)
            
            self.progress_bar.setValue(100)
            self.status_label.setText("Comparison ready")
            
            # Show comparison results
            self._populate_comparison_display()
            self.comparison_group.setVisible(True)
            
            # Hide progress bar after a short delay
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
            
        except Exception as e:
            logger.error(f"Error during comparison: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create comparison: {str(e)}")
            self.progress_bar.setVisible(False)
            self.status_label.setText("Comparison failed")
    
    def _populate_comparison_display(self):
        """Populate the comparison display with results"""
        try:
            # Clear existing tabs
            self.comparison_tabs.clear()
            
            table_stats = self.comparison_data.get('table_statistics', {})
            
            for table_name, stats in table_stats.items():
                tab_widget = self._create_table_comparison_tab(table_name, stats)
                self.comparison_tabs.addTab(tab_widget, f"{table_name.title()} ({sum(stats.values())})")
            
            if not table_stats:
                # No changes tab
                no_changes_widget = QWidget()
                layout = QVBoxLayout(no_changes_widget)
                label = QLabel("No changes detected in proposal database")
                label.setAlignment(Qt.AlignCenter)
                layout.addWidget(label)
                self.comparison_tabs.addTab(no_changes_widget, "No Changes")
            
        except Exception as e:
            logger.error(f"Error populating comparison display: {e}")
    
    def _create_table_comparison_tab(self, table_name, stats):
        """Create a tab showing changes for a specific table"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Statistics summary
        stats_text = []
        if stats.get('added', 0) > 0:
            stats_text.append(f"<span style='color: #4CAF50'>{stats['added']} added</span>")
        if stats.get('modified', 0) > 0:
            stats_text.append(f"<span style='color: #FF9800'>{stats['modified']} modified</span>") 
        if stats.get('deleted', 0) > 0:
            stats_text.append(f"<span style='color: #F44336'>{stats['deleted']} deleted</span>")
        
        if stats_text:
            summary_label = QLabel(f"<b>Changes:</b> {', '.join(stats_text)}")
            summary_label.setWordWrap(True)
            layout.addWidget(summary_label)
        
        # Table showing the actual changes
        table_widget = QTableWidget()
        layout.addWidget(table_widget)
        
        # Populate table with change details
        self._populate_changes_table(table_widget, table_name)
        
        return widget
    
    def _populate_changes_table(self, table_widget, table_name):
        """Populate a table widget with change details"""
        try:
            if not self.proposal_db_path or not os.path.exists(self.proposal_db_path):
                return
            
            conn = sqlite3.connect(self.proposal_db_path)
            cursor = conn.cursor()
            
            proposal_table = f"proposal_{table_name}"
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (proposal_table,))
            if not cursor.fetchone():
                conn.close()
                return
            
            # Get table structure (excluding our added columns)
            cursor.execute(f"PRAGMA table_info({proposal_table})")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info if col[1] not in ['proposal_action', 'proposal_change_id']]
            
            # Get the data
            cursor.execute(f"SELECT *, proposal_action FROM {proposal_table} ORDER BY proposal_action, ROWID")
            rows = cursor.fetchall()
            
            if rows:
                # Setup table
                table_widget.setRowCount(len(rows))
                table_widget.setColumnCount(len(columns) + 1)  # +1 for action column
                
                headers = columns + ['Action']
                table_widget.setHorizontalHeaderLabels(headers)
                
                # Populate rows
                for row_idx, row_data in enumerate(rows):
                    action = row_data[-1]  # Last column is proposal_action
                    
                    # Set row background color based on action
                    if action == 'added':
                        bg_color = "#E8F5E8"  # Light green
                    elif action == 'modified':
                        bg_color = "#FFF3E0"  # Light orange
                    elif action == 'deleted':
                        bg_color = "#FFEBEE"  # Light red
                    else:
                        bg_color = "#FFFFFF"  # White
                    
                    for col_idx, value in enumerate(row_data[:-2]):  # Exclude proposal columns
                        item = QTableWidgetItem(str(value) if value is not None else "")
                        item.setBackground(Qt.GlobalColor.white)
                        table_widget.setItem(row_idx, col_idx, item)
                    
                    # Action column
                    action_item = QTableWidgetItem(action.title())
                    action_item.setBackground(Qt.GlobalColor.white)
                    if action == 'added':
                        action_item.setForeground(Qt.GlobalColor.darkGreen)
                    elif action == 'modified':
                        action_item.setForeground(Qt.darkYellow)
                    elif action == 'deleted':
                        action_item.setForeground(Qt.GlobalColor.red)
                    table_widget.setItem(row_idx, len(columns), action_item)
                
                # Resize columns to content
                table_widget.resizeColumnsToContents()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error populating changes table for {table_name}: {e}")
    
    def create_proposal(self):
        """Create a proposal from the current changes"""
        try:
            if not self.proposal_db_path:
                QMessageBox.warning(self, "Warning", "No proposal data available")
                return
            
            # Get description from user
            description = self.change_tracker.get_manual_changes_description()
            if not description or description == "No manual changes made":
                description = f"Database changes from {self.current_user}"
            
            # Upload proposal
            success = self.cloud_handler.upload_proposal(
                self.project_name,
                self.proposal_db_path,
                self.current_user,
                description
            )
            
            if success:
                QMessageBox.information(self, "Success", "Proposal uploaded successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to upload proposal")
                
        except Exception as e:
            logger.error(f"Error creating proposal: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create proposal: {str(e)}")
    
    def accept_all_changes(self):
        """Accept all changes and apply them to the main database"""
        try:
            # For now, this would trigger the normal save process
            # In the future, this could merge the proposal database into the main database
            reply = QMessageBox.question(
                self, 
                "Accept Changes", 
                "Accept all changes and save to cloud database?\n\nThis will upload your changes using the normal save process.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.accept()
                # The parent can handle the actual save process
                
        except Exception as e:
            logger.error(f"Error accepting changes: {e}")
            QMessageBox.critical(self, "Error", f"Failed to accept changes: {str(e)}")
    
    def closeEvent(self, event):
        """Clean up when dialog is closed"""
        try:
            # Clean up temporary proposal database
            if self.proposal_db_path and os.path.exists(self.proposal_db_path):
                os.remove(self.proposal_db_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")
        
        super().closeEvent(event)