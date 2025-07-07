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
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Date/Time", "User", "Old Flag", "New Flag", "Comment"
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
        
        # Set column widths
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date/Time
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # User
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Old Flag
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # New Flag
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Comment
        
        layout.addWidget(self.history_table)
        
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
                
                # Get flag change history
                cursor.execute("""
                    SELECT timestamp, user_name, old_flag_value, new_flag_value, comment
                    FROM well_flag_changes 
                    WHERE well_id = ?
                    ORDER BY timestamp DESC
                """, (self.well_id,))
                
                history = cursor.fetchall()
                
                # Populate table
                self.history_table.setRowCount(len(history))
                
                for row, (timestamp, user, old_flag, new_flag, comment) in enumerate(history):
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
                    
                    self.history_table.setItem(row, 4, QTableWidgetItem(comment or ""))
                
                # If no history, show a message
                if len(history) == 0:
                    self.history_table.setRowCount(1)
                    no_history_item = QTableWidgetItem("No flag changes recorded for this well")
                    no_history_item.setTextAlignment(Qt.AlignCenter)
                    self.history_table.setItem(0, 0, no_history_item)
                    self.history_table.setSpan(0, 0, 1, 5)
                    
        except Exception as e:
            logger.error(f"Error loading flag history: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load flag history: {str(e)}")
    
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
            if new_flag == self.current_flag:
                QMessageBox.information(self, "No Change", 
                    "The selected flag is the same as the current flag.")
                return
                
            if not comment:
                QMessageBox.warning(self, "Comment Required", 
                    "Please enter a comment explaining the flag change.")
                return
            
            # Save to database
            if self.save_flag_change_to_db(new_flag, comment):
                # Update well flag in wells table
                self.update_well_flag(new_flag)
                
                # Emit signal for external updates
                self.flag_changed.emit(self.well_id, new_flag, comment)
                
                # Show success message
                QMessageBox.information(self, "Flag Updated", 
                    f"Flag updated successfully from '{self.current_flag}' to '{new_flag}'.")
                
                # Update current flag and reload history
                self.current_flag = new_flag
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
                
        except Exception as e:
            logger.error(f"Error updating well flag: {e}")
            raise