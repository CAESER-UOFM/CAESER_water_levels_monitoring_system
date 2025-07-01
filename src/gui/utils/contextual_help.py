"""
Contextual Help Utilities
Easy-to-implement help system for better UX throughout the app.
"""

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QCursor
import webbrowser


class HelpButton(QPushButton):
    """
    Small help button that can be added next to any widget.
    """
    
    def __init__(self, help_text, help_type="info", parent=None):
        super().__init__("?", parent)
        self.help_text = help_text
        self.help_type = help_type
        
        # Style the button to be small and unobtrusive
        self.setFixedSize(20, 20)
        self.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                border: 1px solid #2196f3;
                border-radius: 10px;
                color: #1976d2;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2196f3;
                color: white;
            }
        """)
        
        self.clicked.connect(self.show_help)
        
        # Enhanced tooltip
        self.setup_tooltip()
    
    def setup_tooltip(self):
        """Setup enhanced tooltip."""
        if self.help_type == "info":
            icon = "ℹ️"
            color = "#2196f3"
        elif self.help_type == "warning":
            icon = "⚠️"
            color = "#ff9800"
        elif self.help_type == "tip":
            icon = "💡"
            color = "#4caf50"
        else:
            icon = "❓"
            color = "#9e9e9e"
        
        tooltip_html = f"""
        <div style="padding: 8px; max-width: 250px; font-family: Arial, sans-serif; 
                    background: white; border: 1px solid #ddd; border-radius: 4px;">
            <div style="color: {color}; font-weight: bold; margin-bottom: 3px;">
                {icon} Click for help
            </div>
            <div style="color: #555; font-size: 12px;">
                {self.help_text[:100]}{'...' if len(self.help_text) > 100 else ''}
            </div>
        </div>
        """
        self.setToolTip(tooltip_html)
    
    def show_help(self):
        """Show detailed help popup."""
        popup = HelpPopup(self.help_text, self.help_type, self)
        popup.show_near_widget(self)


class HelpPopup(QFrame):
    """
    Popup window for detailed help content.
    """
    
    def __init__(self, help_text, help_type="info", parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.help_text = help_text
        self.help_type = help_type
        
        self.setup_ui()
        
        # Auto-hide timer
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hide)
        
    def setup_ui(self):
        """Setup popup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with icon
        header_layout = QHBoxLayout()
        
        if self.help_type == "info":
            icon = "ℹ️"
            bg_color = "#e3f2fd"
            border_color = "#2196f3"
        elif self.help_type == "warning":
            icon = "⚠️"
            bg_color = "#fff3e0"
            border_color = "#ff9800"
        elif self.help_type == "tip":
            icon = "💡"
            bg_color = "#e8f5e8"
            border_color = "#4caf50"
        else:
            icon = "❓"
            bg_color = "#f5f5f5"
            border_color = "#9e9e9e"
        
        # Style the popup
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: #333;
                font-family: Arial, sans-serif;
            }}
        """)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 14))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Help")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #333;
                background: rgba(0,0,0,0.1);
                border-radius: 10px;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        
        # Help content
        content_label = QLabel(self.help_text)
        content_label.setWordWrap(True)
        content_label.setFont(QFont("Arial", 10))
        content_label.setStyleSheet("color: #333; line-height: 1.4;")
        layout.addWidget(content_label)
        
        self.setMaximumWidth(300)
        self.adjustSize()
    
    def show_near_widget(self, widget):
        """Show popup near the specified widget."""
        # Position popup near the widget
        global_pos = widget.mapToGlobal(widget.rect().bottomLeft())
        self.move(global_pos.x(), global_pos.y() + 5)
        self.show()
        
        # Auto-hide after 10 seconds
        self.hide_timer.start(10000)
    
    def enterEvent(self, event):
        """Stop auto-hide when mouse enters."""
        self.hide_timer.stop()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Restart auto-hide when mouse leaves."""
        self.hide_timer.start(3000)  # Shorter timeout after leaving
        super().leaveEvent(event)


class SmartTooltip:
    """
    Enhanced tooltip system with rich content and better positioning.
    """
    
    @staticmethod
    def add_to_widget(widget, content, tooltip_type="info", show_delay=500):
        """
        Add smart tooltip to any widget.
        
        Args:
            widget: The widget to add tooltip to
            content: Help content (can include HTML)
            tooltip_type: 'info', 'warning', 'tip', or 'error'
            show_delay: Delay before showing tooltip (ms)
        """
        
        # Icon and color based on type
        type_config = {
            "info": {"icon": "ℹ️", "color": "#2196f3", "bg": "#e3f2fd"},
            "warning": {"icon": "⚠️", "color": "#ff9800", "bg": "#fff3e0"},
            "tip": {"icon": "💡", "color": "#4caf50", "bg": "#e8f5e8"},
            "error": {"icon": "❌", "color": "#f44336", "bg": "#ffebee"}
        }
        
        config = type_config.get(tooltip_type, type_config["info"])
        
        tooltip_html = f"""
        <div style="padding: 10px; max-width: 280px; font-family: Arial, sans-serif;
                    background: {config['bg']}; border: 1px solid {config['color']}; 
                    border-radius: 6px;">
            <div style="color: {config['color']}; font-weight: bold; margin-bottom: 5px;">
                {config['icon']} Help
            </div>
            <div style="color: #333; line-height: 1.4; font-size: 12px;">
                {content}
            </div>
        </div>
        """
        
        widget.setToolTip(tooltip_html)


# Helper functions for easy integration
def add_help_button(parent_layout, help_text, help_type="info"):
    """
    Easy way to add a help button to any layout.
    
    Usage:
        help_btn = add_help_button(layout, "This button imports XLE files")
    """
    help_btn = HelpButton(help_text, help_type)
    parent_layout.addWidget(help_btn)
    return help_btn


def add_help_to_widget(widget, help_text, help_type="info"):
    """
    Easy way to add help tooltip to any existing widget.
    
    Usage:
        add_help_to_widget(my_button, "Click this to import data")
    """
    SmartTooltip.add_to_widget(widget, help_text, help_type)


# Pre-defined help content for common operations
COMMON_HELP = {
    "import_xle": {
        "text": "Import XLE files from Solinst data loggers. The app will automatically validate the data, apply quality control, and integrate it into your database.",
        "type": "info"
    },
    
    "barometric_compensation": {
        "text": "Barometric compensation removes atmospheric pressure effects from your water level readings. Make sure you have barologger data for the same time period.",
        "type": "tip"
    },
    
    "quality_flags": {
        "text": "Quality flags help you identify data problems: 🟢 Good data, 🟡 Questionable (review needed), 🔴 Error (exclude from analysis).",
        "type": "info"
    },
    
    "google_drive_sync": {
        "text": "Cloud sync keeps your team's data synchronized. Changes are automatically uploaded to Google Drive and conflicts are resolved intelligently.",
        "type": "info"
    },
    
    "recharge_calculations": {
        "text": "Choose RISE for event-based recharge, MRC for continuous estimates, or ERC for comprehensive analysis. Each method has different data requirements.",
        "type": "tip"
    }
}


def get_common_help(key):
    """Get pre-defined help content."""
    help_info = COMMON_HELP.get(key, {"text": "Help content not available.", "type": "info"})
    return help_info["text"], help_info["type"]


# Example usage in existing code:
"""
# In any dialog or widget, you can easily add contextual help:

from src.gui.utils.contextual_help import add_help_to_widget, add_help_button, get_common_help

class MyDialog(QDialog):
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Add help to existing button
        import_btn = QPushButton("Import XLE Files")
        help_text, help_type = get_common_help("import_xle")
        add_help_to_widget(import_btn, help_text, help_type)
        
        # Add standalone help button
        help_btn = add_help_button(layout, "This dialog helps you configure import settings")
        
        # Complex form with contextual help
        name_field = QLineEdit()
        add_help_to_widget(name_field, "Enter a unique name for this well", "tip")
        
        self.setLayout(layout)
"""