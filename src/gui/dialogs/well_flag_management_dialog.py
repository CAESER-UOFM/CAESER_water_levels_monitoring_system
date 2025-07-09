# -*- coding: utf-8 -*-
"""
Well Flag Management Dialog

Provides a comprehensive interface for managing well user flags with:
- Flag status changes with comments
- Complete change history tracking
- Collaboration features with user and timestamp tracking

@author: claude
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QFormLayout, QLabel, QComboBox, QTextEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)

class WellFlagManagementDialog(QDialog):
    """Dialog for managing well user flags with collaboration features"""
    
    flag_changed = pyqtSignal(str, str, str)  # well_id, new_flag, comment
    
    def __init__(self, db_manager, well_id: str, current_flag: str, user_name: str, parent=None):
        """
        Initialize the flag management dialog.
        
        Args:
            db_manager: Database manager instance
            well_id: ID of the well to manage
            current_flag: Current flag value
            user_name: Name of the current user
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.well_id = well_id
        self.current_flag = current_flag
        self.user_name = user_name
        
        self.flag_options = ['unchecked', 'error', 'approved']
        self.flag_colors = {
            'unchecked': '#f39c12',  # Orange
            'error': '#e74c3c',      # Red
            'approved': '#27ae60'    # Green
        }
        
        self.setup_ui()
        self.load_flag_history()
        
    def setup_ui(self):
        """Setup the dialog UI with tabbed interface"""
        self.setWindowTitle(f"Manage Flag - Well {self.well_id}")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Well information header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        well_info_label = QLabel(f"<b>Well:</b> {self.well_id}")
        well_info_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(well_info_label)
        
        current_flag_label = QLabel(f"<b>Current Flag:</b> <span style='color: {self.flag_colors.get(self.current_flag, '#000000')};'>{self.current_flag.title()}</span>")
        current_flag_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(current_flag_label)
        
        user_label = QLabel(f"<b>User:</b> {self.user_name}")
        user_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(user_label)
        
        header_layout.addStretch()
        layout.addWidget(header_frame)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.create_flag_change_tab()
        self.create_history_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def create_flag_change_tab(self):
        """Create the flag change tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Flag Change Section
        flag_group = QGroupBox("Change Flag Status")
        flag_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        flag_layout = QFormLayout(flag_group)
        flag_layout.setVerticalSpacing(10)
        
        # Current flag display
        current_flag_display = QLabel(f"<span style='color: {self.flag_colors.get(self.current_flag, '#000000')}; font-weight: bold;'>{self.current_flag.title()}</span>")
        current_flag_display.setStyleSheet("font-size: 14px; padding: 5px;")
        flag_layout.addRow("Current Flag:", current_flag_display)
        
        # New flag selection
        self.new_flag_combo = QComboBox()
        self.new_flag_combo.addItems([option.title() for option in self.flag_options])
        self.new_flag_combo.setCurrentText(self.current_flag.title())
        self.new_flag_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #0084ff;
            }
        """)
        flag_layout.addRow("New Flag:", self.new_flag_combo)
        
        # Comment section
        comment_label = QLabel("Comment (required for flag changes):")
        comment_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        flag_layout.addRow(comment_label)
        
        self.comment_text = QTextEdit()
        self.comment_text.setMaximumHeight(100)
        self.comment_text.setPlaceholderText("Enter a comment explaining the flag change...")
        self.comment_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                background-color: white;
            }
            QTextEdit:focus {
                border-color: #0084ff;
            }
        """)
        flag_layout.addRow(self.comment_text)
        
        layout.addWidget(flag_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save Flag Change")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.save_button.clicked.connect(self.save_flag_change)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Change Flag")
        
    def create_history_tab(self):
        """Create the flag history tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # History section header
        history_label = QLabel("Flag Change History")
        history_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(history_label)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Date/Time", "User", "Old Flag", "New Flag", "Comment", "Resolved"
        ])
        
        # Style the table
        self.history_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #0084ff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: bold;
            }
        """)
        
        # Configure table properties
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        
        # Enable text wrapping and auto-resize for better comment display
        self.history_table.setWordWrap(True)
        self.history_table.setTextElideMode(Qt.ElideNone)
        
        # Set column widths
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date/Time
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # User
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Old Flag
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # New Flag
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Comment
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Resolved
        
        # Enable automatic row height adjustment
        self.history_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Connect double-click signal for detailed comment view
        self.history_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        layout.addWidget(self.history_table)
        
        # Add helpful tip for users
        tip_label = QLabel("💡 Tip: Double-click on any comment to view it in full detail")
        tip_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-style: italic;
                font-size: 11px;
                margin-top: 5px;
                margin-bottom: 10px;
                padding: 5px;
                background-color: #f8f9fa;
                border-radius: 3px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(tip_label)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        refresh_button = QPushButton("Refresh History")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        refresh_button.clicked.connect(self.load_flag_history)
        refresh_layout.addWidget(refresh_button)
        
        layout.addLayout(refresh_layout)
        
        self.tab_widget.addTab(tab, "Change History")
        
    def load_flag_history(self):
        """Load flag change history for the current well"""
        try:
            if not self.db_manager.current_db:
                return
                
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='well_flag_changes'
                """)
                
                if not cursor.fetchone():
                    # Table doesn't exist yet, show empty history
                    self.history_table.setRowCount(0)
                    return
                
                # Check if resolution column exists
                cursor.execute("PRAGMA table_info(well_flag_changes)")
                columns = [column[1] for column in cursor.fetchall()]
                has_resolution = 'is_resolved' in columns
                
                # Get flag change history
                if has_resolution:
                    cursor.execute("""
                        SELECT id, timestamp, user_name, old_flag_value, new_flag_value, comment, is_resolved
                        FROM well_flag_changes 
                        WHERE well_id = ?
                        ORDER BY timestamp DESC
                    """, (self.well_id,))
                else:
                    cursor.execute("""
                        SELECT id, timestamp, user_name, old_flag_value, new_flag_value, comment, 0 as is_resolved
                        FROM well_flag_changes 
                        WHERE well_id = ?
                        ORDER BY timestamp DESC
                    """, (self.well_id,))
                
                history = cursor.fetchall()
                
                # Populate table
                self.history_table.setRowCount(len(history))
                
                for row, (record_id, timestamp, user, old_flag, new_flag, comment, is_resolved) in enumerate(history):
                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_time = timestamp
                    
                    # Add items to table
                    self.history_table.setItem(row, 0, QTableWidgetItem(formatted_time))
                    self.history_table.setItem(row, 1, QTableWidgetItem(user or "Unknown"))
                    
                    # Style flag cells with colors
                    old_flag_item = QTableWidgetItem(old_flag.title() if old_flag else "—")
                    if old_flag:
                        old_flag_item.setBackground(self.get_flag_color(old_flag))
                    self.history_table.setItem(row, 2, old_flag_item)
                    
                    new_flag_item = QTableWidgetItem(new_flag.title() if new_flag else "—")
                    if new_flag:
                        new_flag_item.setBackground(self.get_flag_color(new_flag))
                    self.history_table.setItem(row, 3, new_flag_item)
                    
                    # Create comment item with enhanced display
                    comment_text = comment or ""
                    comment_item = QTableWidgetItem(comment_text)
                    
                    # Set tooltip to show full comment
                    if comment_text:
                        comment_item.setToolTip(f"Full comment:\n{comment_text}")
                    
                    # Enable text wrapping for long comments
                    comment_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
                    
                    self.history_table.setItem(row, 4, comment_item)
                    
                    # Add resolution checkbox
                    from PyQt5.QtWidgets import QCheckBox, QWidget, QHBoxLayout
                    checkbox = QCheckBox()
                    checkbox.setChecked(bool(is_resolved))
                    checkbox.setProperty('record_id', record_id)  # Store record ID for updates
                    checkbox.stateChanged.connect(self.on_resolution_changed)
                    
                    # Center the checkbox in the cell
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.setAlignment(Qt.AlignCenter)
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    
                    self.history_table.setCellWidget(row, 5, checkbox_widget)
                
                # If no history, show a message
                if len(history) == 0:
                    self.history_table.setRowCount(1)
                    no_history_item = QTableWidgetItem("No flag changes recorded for this well")
                    no_history_item.setTextAlignment(Qt.AlignCenter)
                    self.history_table.setItem(0, 0, no_history_item)
                    self.history_table.setSpan(0, 0, 1, 6)
                else:
                    # Resize all rows to fit content properly
                    self.history_table.resizeRowsToContents()
                    
        except Exception as e:
            logger.error(f"Error loading flag history: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load flag history: {str(e)}")
    
    def on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click on table cells, especially for comment column"""
        try:
            # Only show detailed view for comment column (column 4)
            if column == 4:
                item = self.history_table.item(row, column)
                if item and item.text().strip():
                    self.show_comment_detail(item.text(), row)
        except Exception as e:
            logger.error(f"Error handling cell double-click: {e}")
    
    def show_comment_detail(self, comment_text: str, row: int):
        """Show detailed view of comment in a popup dialog"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
            
            # Get additional row information for context
            timestamp_item = self.history_table.item(row, 0)
            user_item = self.history_table.item(row, 1)
            old_flag_item = self.history_table.item(row, 2)
            new_flag_item = self.history_table.item(row, 3)
            
            timestamp = timestamp_item.text() if timestamp_item else "Unknown"
            user = user_item.text() if user_item else "Unknown"
            old_flag = old_flag_item.text() if old_flag_item else "—"
            new_flag = new_flag_item.text() if new_flag_item else "—"
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Flag Change Comment Details")
            dialog.setMinimumSize(500, 400)
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            
            # Context information
            context_label = QLabel(f"""
                <b>Flag Change Details:</b><br>
                <b>Date/Time:</b> {timestamp}<br>
                <b>User:</b> {user}<br>
                <b>Change:</b> {old_flag} → {new_flag}
            """)
            context_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 10px;
                    margin-bottom: 10px;
                }
            """)
            layout.addWidget(context_label)
            
            # Comment label
            comment_label = QLabel("<b>Full Comment:</b>")
            layout.addWidget(comment_label)
            
            # Comment text area (read-only)
            comment_display = QTextEdit()
            comment_display.setPlainText(comment_text)
            comment_display.setReadOnly(True)
            comment_display.setStyleSheet("""
                QTextEdit {
                    border: 2px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 12px;
                    background-color: white;
                }
            """)
            layout.addWidget(comment_display)
            
            # Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            close_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)
            
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing comment detail: {e}")
            QMessageBox.warning(self, "Error", f"Could not show comment details:\n{str(e)}")
    
    def get_flag_color(self, flag_value: str):
        """Get QColor for flag value"""
        from PyQt5.QtGui import QColor
        color_hex = self.flag_colors.get(flag_value.lower(), '#f8f9fa')
        color = QColor(color_hex)
        color.setAlpha(100)  # Make it semi-transparent
        return color
        
    def save_flag_change(self):
        """Save the flag change to database"""
        try:
            new_flag = self.new_flag_combo.currentText().lower()
            comment = self.comment_text.toPlainText().strip()
            
            # Validation
            if not comment:
                QMessageBox.warning(self, "Comment Required", 
                    "Please enter a comment.")
                return
            
            # Check if flag is changing or just adding a comment
            is_flag_change = new_flag != self.current_flag
            
            # Save to database
            if self.save_flag_change_to_db(new_flag, comment):
                # Only update well flag in wells table if flag actually changed
                if is_flag_change:
                    self.update_well_flag(new_flag)
                    # Emit signal for external updates when flag changes
                    self.flag_changed.emit(self.well_id, new_flag, comment)
                else:
                    # Just mark database as modified for comment-only additions
                    self.db_manager.mark_as_modified()
                    # Track the comment addition
                    if (hasattr(self.db_manager, 'change_tracker') and 
                        self.db_manager.change_tracker):
                        from ..handlers.change_tracker import ChangeType, ChangeAction
                        self.db_manager.change_tracker.track_change(
                            change_type=ChangeType.MANUAL,
                            action=ChangeAction.INSERT,
                            table_name="well_flag_changes",
                            record_id=self.well_id,
                            field_name="comment",
                            old_value=None,
                            new_value=comment[:100] + "..." if len(comment) > 100 else comment,
                            description=f"Additional comment added for well {self.well_id} (flag: {new_flag})",
                            context={
                                "well_number": self.well_id,
                                "flag_value": new_flag,
                                "ui_action": "add_flag_comment"
                            }
                        )
                
                # Show success message
                if is_flag_change:
                    QMessageBox.information(self, "Flag Updated", 
                        f"Flag updated successfully from '{self.current_flag}' to '{new_flag}'.")
                    # Update current flag only if it actually changed
                    self.current_flag = new_flag
                else:
                    QMessageBox.information(self, "Comment Added", 
                        f"Comment added successfully for flag '{new_flag}'.")
                
                # Reload history
                self.load_flag_history()
                
                # Reset form
                self.comment_text.clear()
                self.new_flag_combo.setCurrentText(new_flag.title())
                
                # Close dialog
                self.accept()
            
        except Exception as e:
            logger.error(f"Error saving flag change: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save flag change: {str(e)}")
    
    def save_flag_change_to_db(self, new_flag: str, comment: str) -> bool:
        """Save flag change record to database"""
        try:
            if not self.db_manager.current_db:
                return False
                
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                # Insert flag change record
                cursor.execute("""
                    INSERT INTO well_flag_changes 
                    (well_id, old_flag_value, new_flag_value, comment, user_name, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.well_id,
                    self.current_flag,
                    new_flag,
                    comment,
                    self.user_name,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"Flag change recorded: {self.well_id} {self.current_flag} -> {new_flag}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving flag change to database: {e}")
            return False
    
    def update_well_flag(self, new_flag: str):
        """Update the well flag in the wells table"""
        try:
            if not self.db_manager.current_db:
                return
                
            # Track the change if this is a cloud database
            if (hasattr(self.db_manager, 'change_tracker') and 
                self.db_manager.change_tracker):
                from ..handlers.change_tracker import ChangeType, ChangeAction
                self.db_manager.change_tracker.track_change(
                    change_type=ChangeType.MANUAL,
                    action=ChangeAction.UPDATE,
                    table_name="wells",
                    record_id=self.well_id,
                    field_name="user_flag",
                    old_value=self.current_flag,
                    new_value=new_flag,
                    description=f"User flag changed from '{self.current_flag}' to '{new_flag}' for well {self.well_id}",
                    context={
                        "well_number": self.well_id,
                        "ui_action": "flag_management_dialog"
                    }
                )
                
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                # Update well flag
                cursor.execute("""
                    UPDATE wells 
                    SET user_flag = ?
                    WHERE well_number = ?
                """, (new_flag, self.well_id))
                
                conn.commit()
                logger.info(f"Updated well {self.well_id} flag to {new_flag}")
                
            # Mark database as modified
            self.db_manager.mark_as_modified()
                
        except Exception as e:
            logger.error(f"Error updating well flag: {e}")
            raise
    
    def on_resolution_changed(self, state):
        """Handle resolution checkbox changes"""
        try:
            checkbox = self.sender()
            record_id = checkbox.property('record_id')
            is_resolved = checkbox.isChecked()
            
            if not self.db_manager.current_db:
                return
                
            # Update the resolution status in the database
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                # Add resolution column if it doesn't exist
                try:
                    cursor.execute("ALTER TABLE well_flag_changes ADD COLUMN is_resolved INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
                
                # Update resolution status
                cursor.execute("""
                    UPDATE well_flag_changes 
                    SET is_resolved = ?
                    WHERE id = ?
                """, (1 if is_resolved else 0, record_id))
                
                conn.commit()
                
            # Track the resolution change
            if (hasattr(self.db_manager, 'change_tracker') and 
                self.db_manager.change_tracker):
                from ..handlers.change_tracker import ChangeType, ChangeAction
                self.db_manager.change_tracker.track_change(
                    change_type=ChangeType.MANUAL,
                    action=ChangeAction.UPDATE,
                    table_name="well_flag_changes",
                    record_id=record_id,
                    field_name="is_resolved",
                    old_value=not is_resolved,
                    new_value=is_resolved,
                    description=f"Comment marked as {'resolved' if is_resolved else 'unresolved'} for well {self.well_id}",
                    context={
                        "well_number": self.well_id,
                        "ui_action": "resolve_comment"
                    }
                )
            
            # Mark database as modified
            self.db_manager.mark_as_modified()
            
            logger.info(f"Resolution status updated for record {record_id}: {'resolved' if is_resolved else 'unresolved'}")
            
        except Exception as e:
            logger.error(f"Error updating resolution status: {e}")
            # Revert checkbox state on error
            checkbox.setChecked(not checkbox.isChecked())