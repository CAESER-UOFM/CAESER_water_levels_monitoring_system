from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QProgressBar, QTextEdit, QApplication)
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class WaterLevelProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._canceled = False
        
        # Make dialog independent of parent window
        self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the progress dialog UI"""
        self.setWindowTitle("Progress")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)
        
        # Main progress bar
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # Cancel button
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Initialize progress bar
        self.progress.setValue(0)
        
    def update_status(self, message: str):
        """Update status message"""
        self.status_label.setText(message)
        QApplication.processEvents()
        
    def update_progress(self, value: int, maximum: int):
        """Update main progress bar"""
        self.progress.setMaximum(maximum)
        self.progress.setValue(value)
        QApplication.processEvents()
        
    def log_message(self, message: str):
        """Add a message to the log"""
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
        QApplication.processEvents()
        
    def cancel(self):
        """Handle cancel button click"""
        self._canceled = True
        self.log_message("Canceling operation...")
        self.cancel_btn.setEnabled(False)
        QApplication.processEvents()
        
    def was_canceled(self) -> bool:
        """Check if operation was canceled"""
        return self._canceled

    def finish_operation(self):
        """Change cancel button to close after operation completes"""
        self.cancel_btn.setText("Close")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.close)
        self.log_message("\nOperation completed. You can review the log and close this window.")
        QApplication.processEvents()

class QTextEditHandler(logging.Handler):
    """Custom logging handler that writes to QTextEdit"""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
        
    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)
        # Auto-scroll to bottom
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )
        QApplication.processEvents()
