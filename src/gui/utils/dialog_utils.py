"""
Dialog utilities for creating responsive, properly-sized dialogs.

This module provides utilities to prevent common dialog sizing issues
like content cutoff and poor responsiveness across different screen sizes.
"""

import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

logger = logging.getLogger(__name__)


class DialogUtils:
    """Utilities for creating responsive dialogs that always fit content properly."""
    
    @staticmethod
    def setup_responsive_dialog(dialog, min_width=400, min_height=300, max_screen_ratio=0.8):
        """
        Setup a dialog to be responsive and properly sized for content.
        
        Args:
            dialog: QDialog instance
            min_width: Minimum dialog width (default: 400)
            min_height: Minimum dialog height (default: 300)
            max_screen_ratio: Maximum ratio of screen size to use (default: 0.8 = 80%)
        """
        # Set minimum sizes but allow growth
        dialog.setMinimumWidth(min_width)
        dialog.setMinimumHeight(min_height)
        
        # Auto-adjust size after UI is built (use QTimer to ensure layout is complete)
        QTimer.singleShot(0, lambda: DialogUtils.adjust_dialog_size(dialog, max_screen_ratio))
    
    @staticmethod
    def adjust_dialog_size(dialog, max_screen_ratio=0.8):
        """
        Automatically adjust dialog size to fit content properly.
        
        Args:
            dialog: QDialog instance
            max_screen_ratio: Maximum ratio of screen size to use (default: 0.8 = 80%)
        """
        try:
            # Calculate the preferred size based on content
            dialog.adjustSize()
            
            # Get the size hint from the layout
            size_hint = dialog.sizeHint()
            
            # Add padding for safety (50px padding)
            preferred_width = max(size_hint.width() + 50, dialog.minimumWidth())
            preferred_height = max(size_hint.height() + 50, dialog.minimumHeight())
            
            # Get screen dimensions to ensure dialog fits on screen
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            max_width = int(screen_geometry.width() * max_screen_ratio)
            max_height = int(screen_geometry.height() * max_screen_ratio)
            
            # Constrain to screen size
            final_width = min(preferred_width, max_width)
            final_height = min(preferred_height, max_height)
            
            # Resize the dialog
            dialog.resize(final_width, final_height)
            
            # Center the dialog
            DialogUtils.center_dialog(dialog)
            
            logger.debug(f"Dialog auto-sized to {final_width}x{final_height} (hint: {size_hint.width()}x{size_hint.height()})")
            
        except Exception as e:
            logger.error(f"Error adjusting dialog size: {e}")
            # Fallback: center the dialog at its current size
            DialogUtils.center_dialog(dialog)
    
    @staticmethod
    def center_dialog(dialog):
        """
        Center the dialog on the parent window or screen.
        
        Args:
            dialog: QDialog instance
        """
        try:
            if dialog.parent():
                # Center on parent window
                parent_geometry = dialog.parent().geometry()
                x = parent_geometry.x() + (parent_geometry.width() - dialog.width()) // 2
                y = parent_geometry.y() + (parent_geometry.height() - dialog.height()) // 2
                
                # Ensure the dialog stays on screen
                screen = QApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()
                
                x = max(screen_geometry.x(), min(x, screen_geometry.right() - dialog.width()))
                y = max(screen_geometry.y(), min(y, screen_geometry.bottom() - dialog.height()))
                
                dialog.move(x, y)
            else:
                # Center on screen if no parent
                screen = QApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()
                x = screen_geometry.x() + (screen_geometry.width() - dialog.width()) // 2
                y = screen_geometry.y() + (screen_geometry.height() - dialog.height()) // 2
                dialog.move(x, y)
                
        except Exception as e:
            logger.error(f"Error centering dialog: {e}")
    
    @staticmethod
    def make_label_responsive(label):
        """
        Make a label responsive by enabling word wrapping and proper sizing.
        
        Args:
            label: QLabel instance
        """
        label.setWordWrap(True)
        label.setMinimumWidth(0)  # Allow shrinking
        label.setSizePolicy(label.sizePolicy().horizontalPolicy(), label.sizePolicy().verticalPolicy())
    
    @staticmethod
    def apply_responsive_dialog_style(dialog):
        """
        Apply responsive styling that works well across different screen sizes.
        
        Args:
            dialog: QDialog instance
        """
        dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #333333;
            }
            QLabel {
                /* Ensure labels can wrap and resize properly */
                word-wrap: break-word;
            }
            QRadioButton {
                /* Make radio buttons more responsive */
                padding: 8px;
                margin: 4px 0;
            }
            QGroupBox {
                /* Responsive group boxes */
                font-weight: bold;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 8px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
                background-color: #ffffff;
            }
        """)