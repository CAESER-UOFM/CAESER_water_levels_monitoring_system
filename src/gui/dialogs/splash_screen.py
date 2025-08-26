"""
CAESER Water Levels Monitoring System
Splash Screen Dialog

A welcoming splash screen shown during application startup to provide
immediate feedback and branded experience while components load.
"""

import os
import random
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QMovie

class SplashScreen(QDialog):
    """
    Splash screen dialog with CAESER mascot and loading messages.
    Shows immediately on startup to prevent frozen appearance.
    """
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_messages()
        self.setup_timer()
        
    def setup_ui(self):
        """Create the splash screen interface"""
        self.setWindowTitle("CAESER Water Levels")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Center the dialog on screen
        self.center_on_screen()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Mascot image
        self.setup_mascot_image(layout)
        
        # Title and subtitle
        self.setup_title_section(layout)
        
        # Loading message
        self.loading_label = QLabel("Welcome to CAESER! 🌊")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.loading_label)
        
        # Progress dots
        self.progress_label = QLabel("●●●")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #3498db;
                letter-spacing: 3px;
            }
        """)
        layout.addWidget(self.progress_label)
        
        # Add stretch to push everything toward center
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 2px solid #3498db;
                border-radius: 10px;
            }
        """)
    
    def setup_mascot_image(self, layout):
        """Add the CAESER mascot image"""
        try:
            # Path to the mascot image
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            mascot_path = os.path.join(project_root, "src", "gui", "icons", "app_icon.webp")
            
            if os.path.exists(mascot_path):
                mascot_label = QLabel()
                pixmap = QPixmap(mascot_path)
                # Scale to reasonable size for splash
                scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                mascot_label.setPixmap(scaled_pixmap)
                mascot_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(mascot_label)
            else:
                # Fallback if image not found
                placeholder = QLabel("🌊")
                placeholder.setAlignment(Qt.AlignCenter)
                placeholder.setStyleSheet("font-size: 48px;")
                layout.addWidget(placeholder)
        except Exception:
            # Fallback emoji if anything goes wrong
            placeholder = QLabel("🌊")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("font-size: 48px;")
            layout.addWidget(placeholder)
    
    def setup_title_section(self, layout):
        """Add title and subtitle"""
        title_label = QLabel("CAESER")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("Water Levels Monitoring System")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(subtitle_label)
    
    def setup_messages(self):
        """Setup rotating loading messages"""
        self.loading_messages = [
            "Welcome to CAESER! 🌊",
            "Initializing water level magic...",
            "Loading your groundwater data...",
            "Preparing monitoring tools...",
            "Getting ready to dive deep! 🚰",
            "Connecting to water wisdom...",
            "Calibrating sensors...",
            "Loading aquifer insights...",
            "Preparing data visualization..."
        ]
        self.message_index = 0
    
    def setup_timer(self):
        """Setup timers for animations"""
        # Message rotation timer
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.rotate_message)
        self.message_timer.start(1500)  # Change message every 1.5 seconds
        
        # Progress dots animation timer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.animate_progress)
        self.progress_timer.start(500)  # Animate dots every 0.5 seconds
        self.progress_state = 0
    
    def center_on_screen(self):
        """Center the splash screen on the display"""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def rotate_message(self):
        """Rotate through loading messages"""
        self.message_index = (self.message_index + 1) % len(self.loading_messages)
        self.loading_label.setText(self.loading_messages[self.message_index])
    
    def animate_progress(self):
        """Animate the progress dots"""
        dots_patterns = ["●○○", "○●○", "○○●", "●○○"]
        self.progress_label.setText(dots_patterns[self.progress_state])
        self.progress_state = (self.progress_state + 1) % len(dots_patterns)
    
    def update_message(self, message: str):
        """Update the loading message (called from main application)"""
        self.loading_label.setText(message)
    
    def close_splash(self):
        """Clean shutdown of the splash screen"""
        self.message_timer.stop()
        self.progress_timer.stop()
        self.close()