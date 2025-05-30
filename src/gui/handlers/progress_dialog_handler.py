# -*- coding: utf-8 -*-
"""
Simple handler for showing progress dialogs during data loading operations.
"""

from PyQt5.QtWidgets import QProgressDialog, QApplication
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class ProgressDialogHandler:
    """
    A simple handler for showing progress dialogs during data loading operations.
    Can be used from any part of the application to provide consistent user feedback.
    """
    
    def __init__(self):
        self.progress_dialog = None
        
    def show(self, message="Loading data...", title="Please Wait", 
             min_duration=500, modal=True, min_width=400, cancelable=False):
        """
        Show a progress dialog with the given message.
        
        Args:
            message: Message to display in the dialog
            title: Dialog title
            min_duration: Minimum duration in ms before showing (prevents flashing for quick operations)
            modal: Whether the dialog blocks user interaction with the parent window
            min_width: Minimum width of the dialog in pixels
            cancelable: Whether the dialog can be cancelled by the user
        """
        try:
            # Close any existing dialog first
            self.close()
            
            # Create new progress dialog
            self.progress_dialog = QProgressDialog()
            self.progress_dialog.setWindowTitle(title)
            self.progress_dialog.setLabelText(message)
            
            if modal:
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                
            # Setup dialog properties
            self.progress_dialog.setMinimumDuration(min_duration)
            self.progress_dialog.setMinimumWidth(min_width)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setRange(0, 100)
            self.progress_dialog.setValue(0)
            
            # Setup cancel button
            if not cancelable:
                self.progress_dialog.setCancelButton(None)
                
            # Apply consistent styling
            self.progress_dialog.setStyleSheet("""
                QProgressDialog {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
                QProgressBar {
                    border: 1px solid #aaa;
                    border-radius: 3px;
                    background-color: #fff;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                    width: 10px;
                    margin: 0.5px;
                }
            """)
            
            # Show the dialog
            self.progress_dialog.show()
            
            # Process events to make dialog visible immediately
            QApplication.processEvents()
            
            logger.debug(f"Progress dialog shown with message: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error showing progress dialog: {e}")
            return False
    
    def update(self, value, message=None):
        """
        Update the progress dialog with a new value and optional message.
        
        Args:
            value: Progress value (0-100)
            message: Optional new message to display
        """
        if not self.progress_dialog:
            return False
            
        try:
            # Update progress value
            self.progress_dialog.setValue(value)
            
            # Update message if provided
            if message:
                self.progress_dialog.setLabelText(message)
                
            # Process events to update UI immediately
            QApplication.processEvents()
            return True
            
        except Exception as e:
            logger.error(f"Error updating progress dialog: {e}")
            return False
    
    def close(self):
        """Close the progress dialog if it exists."""
        if self.progress_dialog:
            try:
                self.progress_dialog.close()
                self.progress_dialog = None
                return True
            except Exception as e:
                logger.error(f"Error closing progress dialog: {e}")
                return False
        return True

# Create a singleton instance that can be imported and used anywhere
progress_dialog = ProgressDialogHandler()
