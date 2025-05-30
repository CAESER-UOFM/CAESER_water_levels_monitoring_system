"""
Dialog for adding manual water level readings.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QDateTimeEdit, QDoubleSpinBox,
                           QLineEdit, QTextEdit, QDialogButtonBox,
                           QDateEdit, QTimeEdit)
from PyQt5.QtCore import QDateTime, Qt, QDate, QTime
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AddManualReadingDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Add Manual Reading")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Well selection
        well_layout = QHBoxLayout()
        well_label = QLabel("Well:")
        self.well_combo = QComboBox()
        self.populate_wells()
        well_layout.addWidget(well_label)
        well_layout.addWidget(self.well_combo)
        layout.addLayout(well_layout)
        
        # Separate Date and Time fields
        date_time_layout = QHBoxLayout()
        
        # Date field with calendar
        date_label = QLabel("Date:")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setStyleSheet("""
            QDateEdit {
                padding: 4px;
                border: 1px solid #aaa;
                border-radius: 3px;
                background-color: #f8f8f8;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: 1px solid #aaa;
                background-color: #e0e0e0;
            }
            QDateEdit::drop-down:hover {
                background-color: #d0d0d0;
            }
            QDateEdit:hover {
                background-color: #f0f0f0;
                border-color: #888;
            }
        """)
        self.date_edit.setToolTip("Click to edit or use the dropdown button for calendar selection")
        
        # Time field with dedicated time editor
        time_label = QLabel("Time:")
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("hh:mm AP")  # 12-hour format with AM/PM
        self.time_edit.setStyleSheet("""
            QTimeEdit {
                padding: 4px;
                border: 1px solid #aaa;
                border-radius: 3px;
                background-color: #f8f8f8;
            }
            QTimeEdit::up-button, QTimeEdit::down-button {
                subcontrol-origin: border;
                width: 16px;
            }
            QTimeEdit::up-button {
                subcontrol-position: top right;
            }
            QTimeEdit::down-button {
                subcontrol-position: bottom right;
            }
            QTimeEdit:hover {
                background-color: #f0f0f0;
                border-color: #888;
            }
        """)
        self.time_edit.setToolTip("Click to edit or use the up/down buttons to adjust time")
        
        # Add widgets to layout
        date_time_layout.addWidget(date_label)
        date_time_layout.addWidget(self.date_edit)
        date_time_layout.addWidget(time_label)
        date_time_layout.addWidget(self.time_edit)
        
        layout.addLayout(date_time_layout)
        
        # DTW measurements
        dtw_layout = QHBoxLayout()
        dtw_layout.addWidget(QLabel("DTW 1:"))
        self.dtw1_edit = QDoubleSpinBox()
        self.dtw1_edit.setRange(0, 999.99)
        self.dtw1_edit.setDecimals(2)
        dtw_layout.addWidget(self.dtw1_edit)
        
        dtw_layout.addWidget(QLabel("DTW 2 (optional):"))
        self.dtw2_edit = QDoubleSpinBox()
        self.dtw2_edit.setRange(0, 999.99)
        self.dtw2_edit.setDecimals(2)
        dtw_layout.addWidget(self.dtw2_edit)
        layout.addLayout(dtw_layout)
        
        # Collected by
        collector_layout = QHBoxLayout()
        collector_label = QLabel("Collected by:")
        self.collector_edit = QLineEdit()
        collector_layout.addWidget(collector_label)
        collector_layout.addWidget(self.collector_edit)
        layout.addLayout(collector_layout)
        
        # Comments
        layout.addWidget(QLabel("Comments:"))
        self.comments_edit = QTextEdit()
        self.comments_edit.setMaximumHeight(60)
        layout.addWidget(self.comments_edit)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def populate_wells(self):
        """Populate wells dropdown from database"""
        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT well_number, cae_number FROM wells ORDER BY well_number")
                wells = cursor.fetchall()
                
                for well_number, cae in wells:
                    display_text = f"{well_number}"
                    if cae:
                        display_text += f" ({cae})"
                    self.well_combo.addItem(display_text, well_number)
        except Exception as e:
            logger.error(f"Error populating wells: {e}")
    
    def get_data(self):
        """Get form data as dictionary"""
        well_number = self.well_combo.currentData()
        
        # Combine date and time into a single datetime object
        selected_date = self.date_edit.date().toPyDate()
        selected_time = self.time_edit.time().toPyTime()
        measurement_date = datetime.combine(selected_date, selected_time)
        
        dtw1 = self.dtw1_edit.value()
        dtw2 = self.dtw2_edit.value() if self.dtw2_edit.value() > 0 else None
        collector = self.collector_edit.text()
        comments = self.comments_edit.toPlainText()
        
        return {
            'well_number': well_number,
            'measurement_date': measurement_date,
            'dtw1': dtw1,
            'dtw2': dtw2,
            'collector': collector,
            'comments': comments
        } 