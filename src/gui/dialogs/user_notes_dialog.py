# -*- coding: utf-8 -*-
"""
User Notes Dialog

Provides a comprehensive interface for managing user notes about water level data analysis with:
- Add notes about specific time ranges or full data
- Complete notes history tracking like a chat system
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
    QGroupBox, QHeaderView, QFrame, QScrollArea, QDateTimeEdit,
    QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)

class UserNotesDialog(QDialog):
    """Dialog for managing user notes about water level data analysis"""
    
    note_added = pyqtSignal(str, str, str)  # well_number, note_text, time_range_info
    
    def __init__(self, db_manager, well_number: str, user_name: str, parent=None):
        """
        Initialize the user notes dialog.
        
        Args:
            db_manager: Database manager instance
            well_number: Number of the well to manage notes for
            user_name: Name of the current user
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.well_number = well_number
        self.user_name = user_name
        self.parent_widget = parent  # Store parent reference for accessing change tracker
        
        self.setup_ui()
        self.load_notes_history()
        
    def setup_ui(self):
        """Setup the dialog UI with tabbed interface"""
        self.setWindowTitle(f"User Notes - Well {self.well_number}")
        self.setMinimumSize(700, 600)
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
        
        well_info_label = QLabel(f"<b>Well:</b> {self.well_number}")
        well_info_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(well_info_label)
        
        user_label = QLabel(f"<b>User:</b> {self.user_name}")
        user_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(user_label)
        
        notes_count_label = QLabel(f"<b>Notes:</b> <span id='notes_count'>Loading...</span>")
        notes_count_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(notes_count_label)
        
        header_layout.addStretch()
        layout.addWidget(header_frame)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.create_add_note_tab()
        self.create_notes_history_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def create_add_note_tab(self):
        """Create the add note tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Note Section
        note_group = QGroupBox("Add Data Analysis Note")
        note_group.setStyleSheet("""
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
        note_layout = QFormLayout(note_group)
        note_layout.setVerticalSpacing(15)
        
        # Time range selection
        time_range_label = QLabel("Time Range:")
        time_range_label.setStyleSheet("font-weight: bold;")
        note_layout.addRow(time_range_label)
        
        # Radio buttons for time range type
        self.time_range_group = QButtonGroup()
        
        time_range_widget = QWidget()
        time_range_layout = QVBoxLayout(time_range_widget)
        time_range_layout.setContentsMargins(20, 0, 0, 0)
        
        self.full_range_radio = QRadioButton("Full data range")
        self.full_range_radio.setChecked(True)
        self.full_range_radio.setStyleSheet("font-size: 12px; margin-bottom: 5px;")
        self.time_range_group.addButton(self.full_range_radio, 0)
        time_range_layout.addWidget(self.full_range_radio)
        
        self.specific_range_radio = QRadioButton("Specific time range")
        self.specific_range_radio.setStyleSheet("font-size: 12px; margin-bottom: 10px;")
        self.time_range_group.addButton(self.specific_range_radio, 1)
        time_range_layout.addWidget(self.specific_range_radio)
        
        # Date range widgets (disabled initially)
        date_range_widget = QWidget()
        date_range_layout = QHBoxLayout(date_range_widget)
        date_range_layout.setContentsMargins(20, 0, 0, 0)
        
        date_range_layout.addWidget(QLabel("From:"))
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setDateTime(QDateTime.currentDateTime().addDays(-30))
        self.start_datetime.setCalendarPopup(True)
        self.start_datetime.setEnabled(False)
        self.start_datetime.setStyleSheet("""
            QDateTimeEdit {
                padding: 5px;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 11px;
            }
            QDateTimeEdit:disabled {
                background-color: #f5f5f5;
                color: #999;
            }
            QDateTimeEdit:enabled {
                border-color: #0084ff;
            }
        """)
        date_range_layout.addWidget(self.start_datetime)
        
        date_range_layout.addWidget(QLabel("To:"))
        self.end_datetime = QDateTimeEdit()
        self.end_datetime.setDateTime(QDateTime.currentDateTime())
        self.end_datetime.setCalendarPopup(True)
        self.end_datetime.setEnabled(False)
        self.end_datetime.setStyleSheet(self.start_datetime.styleSheet())
        date_range_layout.addWidget(self.end_datetime)
        
        date_range_layout.addStretch()
        time_range_layout.addWidget(date_range_widget)
        
        note_layout.addRow(time_range_widget)
        
        # Connect radio button signals
        self.full_range_radio.toggled.connect(self.on_time_range_changed)
        self.specific_range_radio.toggled.connect(self.on_time_range_changed)
        
        # Note text section
        note_label = QLabel("Note:")
        note_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        note_layout.addRow(note_label)
        
        self.note_text = QTextEdit()
        self.note_text.setMinimumHeight(150)
        self.note_text.setPlaceholderText(
            "Enter your observations about the water level data...\n\n"
            "Examples:\n"
            "• I see that the levels between March 15-20 show an unusual spike\n"
            "• The data looks good overall but there might be an issue around the summer period\n"
            "• Notice the seasonal pattern is different from previous years\n"
            "• What do you think about the readings during the drought period?"
        )
        self.note_text.setStyleSheet("""
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
        note_layout.addRow(self.note_text)
        
        layout.addWidget(note_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.clear_button.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_button)
        
        self.save_note_button = QPushButton("Save Note")
        self.save_note_button.setStyleSheet("""
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
        self.save_note_button.clicked.connect(self.save_note)
        button_layout.addWidget(self.save_note_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📝 Add Note")
        
    def create_notes_history_tab(self):
        """Create the notes history tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # History section header
        history_label = QLabel("Notes History")
        history_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(history_label)
        
        # History table
        self.notes_table = QTableWidget()
        self.notes_table.setColumnCount(4)
        self.notes_table.setHorizontalHeaderLabels([
            "Date/Time", "User", "Time Range", "Note"
        ])
        
        # Style the table
        self.notes_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #0084ff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: bold;
            }
        """)
        
        # Configure table properties
        self.notes_table.setAlternatingRowColors(True)
        self.notes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.notes_table.verticalHeader().setVisible(False)
        self.notes_table.setWordWrap(True)
        
        # Set column widths
        header = self.notes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date/Time
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # User
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Time Range
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Note
        
        layout.addWidget(self.notes_table)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        refresh_button = QPushButton("🔄 Refresh")
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
        refresh_button.clicked.connect(self.load_notes_history)
        refresh_layout.addWidget(refresh_button)
        
        layout.addLayout(refresh_layout)
        
        self.tab_widget.addTab(tab, "💬 Notes History")
        
    def on_time_range_changed(self):
        """Handle time range radio button changes"""
        is_specific = self.specific_range_radio.isChecked()
        self.start_datetime.setEnabled(is_specific)
        self.end_datetime.setEnabled(is_specific)
        
    def clear_form(self):
        """Clear the add note form"""
        self.note_text.clear()
        self.full_range_radio.setChecked(True)
        self.start_datetime.setDateTime(QDateTime.currentDateTime().addDays(-30))
        self.end_datetime.setDateTime(QDateTime.currentDateTime())
        
    def load_notes_history(self):
        """Load notes history for the current well"""
        try:
            if not self.db_manager.current_db:
                return
                
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='user_notes'
                """)
                
                if not cursor.fetchone():
                    # Table doesn't exist yet, show empty history
                    self.notes_table.setRowCount(0)
                    return
                
                # Get notes history
                cursor.execute("""
                    SELECT created_at, user_name, time_range_type, time_range_start, 
                           time_range_end, note_text
                    FROM user_notes 
                    WHERE well_number = ?
                    ORDER BY created_at DESC
                """, (self.well_number,))
                
                notes = cursor.fetchall()
                
                # Populate table
                self.notes_table.setRowCount(len(notes))
                
                for row, (created_at, user, time_range_type, time_range_start, 
                         time_range_end, note_text) in enumerate(notes):
                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_time = created_at
                    
                    # Format time range
                    if time_range_type == 'full':
                        time_range_str = "Full range"
                    else:
                        try:
                            start_dt = datetime.fromisoformat(time_range_start.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(time_range_end.replace('Z', '+00:00'))
                            time_range_str = f"{start_dt.strftime('%m/%d/%y')} - {end_dt.strftime('%m/%d/%y')}"
                        except:
                            time_range_str = "Specific range"
                    
                    # Add items to table
                    self.notes_table.setItem(row, 0, QTableWidgetItem(formatted_time))
                    self.notes_table.setItem(row, 1, QTableWidgetItem(user or "Unknown"))
                    self.notes_table.setItem(row, 2, QTableWidgetItem(time_range_str))
                    
                    # Note text item with word wrap
                    note_item = QTableWidgetItem(note_text or "")
                    note_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
                    self.notes_table.setItem(row, 3, note_item)
                
                # Adjust row heights for content
                self.notes_table.resizeRowsToContents()
                
                # If no notes, show a message
                if len(notes) == 0:
                    self.notes_table.setRowCount(1)
                    no_notes_item = QTableWidgetItem("No notes recorded for this well")
                    no_notes_item.setTextAlignment(Qt.AlignCenter)
                    self.notes_table.setItem(0, 0, no_notes_item)
                    self.notes_table.setSpan(0, 0, 1, 4)
                    
        except Exception as e:
            logger.error(f"Error loading notes history: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load notes history: {str(e)}")
        
    def save_note(self):
        """Save the note to database"""
        try:
            note_text = self.note_text.toPlainText().strip()
            
            # Validation
            if not note_text:
                QMessageBox.warning(self, "Note Required", 
                    "Please enter a note before saving.")
                return
            
            # Get time range info
            if self.full_range_radio.isChecked():
                time_range_type = 'full'
                time_range_start = None
                time_range_end = None
                time_range_display = "Full data range"
            else:
                time_range_type = 'specific'
                time_range_start = self.start_datetime.dateTime().toPyDateTime().isoformat()
                time_range_end = self.end_datetime.dateTime().toPyDateTime().isoformat()
                start_str = self.start_datetime.dateTime().toString('MM/dd/yyyy')
                end_str = self.end_datetime.dateTime().toString('MM/dd/yyyy')
                time_range_display = f"{start_str} - {end_str}"
            
            # Save to database
            if self.save_note_to_db(note_text, time_range_type, time_range_start, time_range_end):
                # Track the change if this is a cloud database
                if (hasattr(self.db_manager, 'change_tracker') and 
                    self.db_manager.change_tracker):
                    from ..handlers.change_tracker import ChangeType, ChangeAction
                    self.db_manager.change_tracker.track_change(
                        change_type=ChangeType.MANUAL,
                        action=ChangeAction.INSERT,
                        table_name="user_notes",
                        record_id=self.well_number,
                        field_name=None,
                        old_value=None,
                        new_value=note_text[:100] + "..." if len(note_text) > 100 else note_text,
                        description=f"User note added for well {self.well_number}: {time_range_display}",
                        context={
                            "well_number": self.well_number,
                            "time_range_type": time_range_type,
                            "note_length": len(note_text),
                            "ui_action": "add_user_note"
                        }
                    )
                
                # Mark database as modified
                self.db_manager.mark_as_modified()
                
                # Emit signal for external updates
                self.note_added.emit(self.well_number, note_text, time_range_display)
                
                # Show success message
                QMessageBox.information(self, "Note Saved", 
                    "Note saved successfully!")
                
                # Reload history
                self.load_notes_history()
                
                # Clear form
                self.clear_form()
                
                # Switch to history tab to show the new note
                self.tab_widget.setCurrentIndex(1)
            
        except Exception as e:
            logger.error(f"Error saving note: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save note: {str(e)}")
    
    def save_note_to_db(self, note_text: str, time_range_type: str, 
                       time_range_start: str, time_range_end: str) -> bool:
        """Save note to database"""
        try:
            if not self.db_manager.current_db:
                return False
                
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                # Insert note record
                cursor.execute("""
                    INSERT INTO user_notes 
                    (well_number, user_name, note_text, time_range_type, 
                     time_range_start, time_range_end, timestamp_created)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.well_number,
                    self.user_name,
                    note_text,
                    time_range_type,
                    time_range_start,
                    time_range_end,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"Note saved for well {self.well_number} by {self.user_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving note to database: {e}")
            return False