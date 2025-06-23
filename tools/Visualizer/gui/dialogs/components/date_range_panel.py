from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit,
    QGroupBox, QPushButton
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from datetime import datetime, timedelta

class DateRangePanel(QWidget):
    """Panel for date range selection."""
    
    # Signals
    date_range_changed = pyqtSignal(dict)  # Emitted when date range changes
    auto_range_clicked = pyqtSignal()  # Emitted when auto range button is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.date_range = {'start': None, 'end': None}
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(4)
        
        # Start date
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("Start:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        self.start_date_edit.dateChanged.connect(
            lambda date: self.update_date_range('start', date)
        )
        start_date_layout.addWidget(self.start_date_edit)
        layout.addLayout(start_date_layout)
        
        # End date
        end_date_layout = QHBoxLayout()
        end_date_layout.addWidget(QLabel("End:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(
            lambda date: self.update_date_range('end', date)
        )
        end_date_layout.addWidget(self.end_date_edit)
        layout.addLayout(end_date_layout)
        
        # Auto range button
        auto_range_btn = QPushButton("Auto Range")
        auto_range_btn.setToolTip("Set date range based on available data in selected wells")
        auto_range_btn.clicked.connect(self.auto_range_clicked.emit)
        layout.addWidget(auto_range_btn)
        
        # Add stretch to push everything up
        layout.addStretch()
    
    def update_date_range(self, which, qdate):
        """Update the date range for plotting."""
        py_date = qdate.toPyDate()
        self.date_range[which] = py_date
        
        # Emit signal with updated date range
        self.date_range_changed.emit(self.date_range)
    
    def get_date_range(self):
        """Get the current date range."""
        return self.date_range
    
    def set_date_range(self, start_date=None, end_date=None):
        """Set the date range."""
        if start_date:
            self.start_date_edit.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.date_range['start'] = start_date
        
        if end_date:
            self.end_date_edit.setDate(QDate(end_date.year, end_date.month, end_date.day))
            self.date_range['end'] = end_date
        
        # Emit signal with updated date range
        self.date_range_changed.emit(self.date_range)
    
    def set_auto_date_range(self, min_date, max_date):
        """Set the date range automatically based on available data."""
        if min_date and max_date:
            # Set date range with a small buffer (1 day on each side if possible)
            self.set_date_range(min_date, max_date)
            
            # Emit signal to notify that auto range was set
            self.auto_range_clicked.emit() 