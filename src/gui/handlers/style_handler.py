"""
Style handler for consistent styling across the water level monitoring application.
"""

class StyleHandler:
    """Provides consistent styling for the entire application."""
    
    @staticmethod
    def get_common_stylesheet():
        """Return the common base stylesheet for the application."""
        return """
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            
            QPushButton {
                border: 1px solid #AAAAAA;
                border-radius: 4px;
                padding: 4px 15px;
                background-color: #F0F0F0;
            }
            
            QPushButton:hover {
                background-color: #E0E0E0;
                border: 1px solid #3070B0;
            }
            
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
            
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
                border: 1px solid #AAAAAA;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: white;
            }
            
            QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {
                border: 1px solid #3070B0;
            }
            
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
                border: 1px solid #3070B0;
            }
            
            QTableWidget {
                border: 1px solid #CCCCCC;
                gridline-color: #E0E0E0;
                selection-background-color: #3070B0;
                selection-color: white;
            }
            
            QHeaderView::section {
                background-color: #F0F0F0;
                padding: 4px;
                border: 1px solid #CCCCCC;
                border-top: none;
                border-left: none;
            }
            
            QStatusBar {
                background-color: #F0F0F0;
                border-top: 1px solid #CCCCCC;
            }
            
            QSplitter::handle {
                background-color: #E0E0E0;
            }
            
            QSplitter::handle:horizontal {
                width: 2px;
            }
            
            QSplitter::handle:vertical {
                height: 2px;
            }
            
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 12px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                min-height: 20px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #3070B0;
            }
        """
    
    @staticmethod
    def get_action_button_style():
        """Return styling for action buttons."""
        return """
            background-color: #3070B0;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 6px 12px;
        """
    
    @staticmethod
    def get_secondary_button_style():
        """Return styling for secondary buttons."""
        return """
            background-color: #5090D0;
            color: white;
            border-radius: 4px;
            padding: 6px 12px;
        """
    
    @staticmethod
    def get_close_button_style():
        """Return styling for close/cancel buttons."""
        return """
            background-color: #B03050;
            color: white;
            border-radius: 4px;
            padding: 6px 12px;
        """
    
    @staticmethod
    def apply_application_style(app):
        """Apply the application-wide stylesheet to QApplication."""
        app.setStyleSheet(StyleHandler.get_common_stylesheet())
