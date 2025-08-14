"""
Professional button styling utility for consistent dialog button appearance.

This module provides standardized button styles that follow the application's
color-coded design system for different button functions.
"""

class ButtonStyles:
    """Provides standardized button styles for different button types."""
    
    @staticmethod
    def get_create_button_style():
        """Green theme for creation/add actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #e8f5e8;
                color: #2e7d32;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
                border-color: #4caf50;
            }
            QPushButton:pressed {
                background-color: #a5d6a7;
                border-color: #388e3c;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_edit_button_style():
        """Blue theme for edit/modify actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #bbdefb;
                border-color: #2196f3;
            }
            QPushButton:pressed {
                background-color: #90caf9;
                border-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_delete_button_style():
        """Red theme for delete/remove actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #ffebee;
                color: #d32f2f;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #ffcdd2;
                border-color: #f44336;
            }
            QPushButton:pressed {
                background-color: #ef9a9a;
                border-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_import_button_style():
        """Light blue theme for import/load actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #e7f3ff;
                color: #0066cc;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #cce7ff;
                border-color: #0080ff;
            }
            QPushButton:pressed {
                background-color: #b3daff;
                border-color: #0066cc;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_save_button_style():
        """Green theme for save actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #e8f5e8;
                color: #2e7d32;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
                border-color: #4caf50;
            }
            QPushButton:pressed {
                background-color: #a5d6a7;
                border-color: #388e3c;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_cancel_button_style():
        """Gray theme for cancel/close actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f5f5f5;
                color: #666666;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
                border-color: #666666;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_primary_button_style():
        """Blue theme for primary actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #bbdefb;
                border-color: #2196f3;
            }
            QPushButton:pressed {
                background-color: #90caf9;
                border-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def get_warning_button_style():
        """Orange theme for warning actions"""
        return """
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #fff8e1;
                color: #f57c00;
                font-weight: 500;
                min-height: 28px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #ffecb3;
                border-color: #ff9800;
            }
            QPushButton:pressed {
                background-color: #ffe082;
                border-color: #f57c00;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
    
    @staticmethod
    def apply_button_style(button, style_type):
        """
        Apply a button style to a QPushButton.
        
        Args:
            button: QPushButton instance
            style_type: String indicating the style type ('create', 'edit', 'delete', 
                       'import', 'save', 'cancel', 'primary', 'warning')
        """
        style_map = {
            'create': ButtonStyles.get_create_button_style(),
            'edit': ButtonStyles.get_edit_button_style(),
            'delete': ButtonStyles.get_delete_button_style(),
            'import': ButtonStyles.get_import_button_style(),
            'save': ButtonStyles.get_save_button_style(),
            'cancel': ButtonStyles.get_cancel_button_style(),
            'primary': ButtonStyles.get_primary_button_style(),
            'warning': ButtonStyles.get_warning_button_style(),
        }
        
        if style_type in style_map:
            button.setStyleSheet(style_map[style_type])
    
    # Convenience methods for common button types
    @staticmethod
    def apply_primary_button_style(button):
        """Apply primary button style (blue theme)"""
        button.setStyleSheet(ButtonStyles.get_primary_button_style())
    
    @staticmethod
    def apply_secondary_button_style(button):
        """Apply secondary button style (gray theme)"""
        button.setStyleSheet(ButtonStyles.get_cancel_button_style())
    
    @staticmethod
    def apply_save_button_style(button):
        """Apply save button style (green theme)"""
        button.setStyleSheet(ButtonStyles.get_save_button_style())
    
    @staticmethod
    def apply_delete_button_style(button):
        """Apply delete button style (red theme)"""
        button.setStyleSheet(ButtonStyles.get_delete_button_style())