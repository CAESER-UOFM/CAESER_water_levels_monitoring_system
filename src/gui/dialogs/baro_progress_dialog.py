from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, 
                           QTextEdit, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
import logging

logger = logging.getLogger(__name__)

class BaroProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canceled = False
        
        # Make dialog independent of parent window
        self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        
        logger.debug("Initializing BaroProgressDialog")
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the progress dialog UI"""
        self.setWindowTitle("Progress")
        self.resize(600, 400)  # Match water level dialog size
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Detailed log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Cancel button in its own layout
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Initialize progress bar
        self.progress_bar.setValue(0)
        
    def closeEvent(self, event):
        """Prevent dialog from being closed except through cancel button"""
        if not self.canceled:
            event.ignore()
        else:
            event.accept()

    def reject(self):
        """Handle dialog rejection (Cancel button)"""
        self.canceled = True
        super().reject()
        
    def update_progress(self, value: int, max_value: int):
        """Update progress bar"""
        logger.debug(f"Updating progress: value={value}, max={max_value}")
        self.progress_bar.setMaximum(max_value)
        self.progress_bar.setValue(value)
        
        # Change button text when complete
        if value >= max_value:
            self.cancel_btn.setText("Close")
            self.cancel_btn.setEnabled(True)
        
        # Force immediate update
        self.progress_bar.repaint()
        QApplication.processEvents()
        
    def update_status(self, message: str):
        """Update status label"""
        logger.debug(f"Status update: {message}")
        self.status_label.setText(message)
        # Force immediate update
        self.status_label.repaint()
        QApplication.processEvents()
        
    def log_message(self, message: str):
        """Add message to log"""
        logger.debug(f"Log message: {message}")
        self.log_text.append(message)
        # Force immediate update
        self.log_text.repaint()
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        QApplication.processEvents()
        
    def was_canceled(self) -> bool:
        """Check if operation was canceled"""
        return self.canceled
        
    def finish_operation(self):
        """Called when operation is complete to change cancel button to close"""
        self.cancel_btn.setText("Close")
        self.cancel_btn.setEnabled(True)
        QApplication.processEvents()
