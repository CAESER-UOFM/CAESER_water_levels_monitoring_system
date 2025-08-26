"""
CAESER Water Levels Monitoring System
Splash Screen Dialog

A welcoming splash screen shown during application startup to provide
immediate feedback and branded experience while components load.
"""

import os
import random
from pathlib import Path
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
        """Create the splash screen interface matching login dialog style"""
        self.setWindowTitle("CAESER Water Levels")
        self.setFixedSize(380, 280)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Center the dialog on screen
        self.center_on_screen()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Circular mascot container (matching login style)
        self.setup_circular_mascot(layout)
        
        # Title matching login style
        title_label = QLabel("Water Level Monitoring")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: white;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Loading message
        self.loading_label = QLabel("Loading your groundwater data...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(self.loading_label)
        
        # Breathing progress dots
        self.progress_label = QLabel("●●●")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                letter-spacing: 4px;
            }
        """)
        layout.addWidget(self.progress_label)
        
        self.setLayout(layout)
        
        # Style to match login dialog - blue gradient background
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
    
    def setup_circular_mascot(self, layout):
        """Add circular mascot container matching login dialog"""
        try:
            # Create container for circular mascot
            mascot_container = QLabel()
            mascot_container.setFixedSize(100, 100)
            mascot_container.setAlignment(Qt.AlignCenter)
            
            # Use exact same path approach as login dialog 
            icon_dir = Path(__file__).parent.parent / "icons"
            mascot_path = icon_dir / "app_icon.webp"
            if not mascot_path.exists():
                mascot_path = icon_dir / "water_level_meter.png"
            
            if mascot_path.exists():
                # Load and prepare the mascot image
                pixmap = QPixmap(str(mascot_path))
                
                # Scale to fit circle
                scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                mascot_container.setPixmap(scaled_pixmap)
                
                # Create circular container with breathing animation
                mascot_container.setStyleSheet("""
                    QLabel {
                        background: rgba(255, 255, 255, 0.15);
                        border: 2px solid rgba(255, 255, 255, 0.3);
                        border-radius: 50px;
                        padding: 8px;
                    }
                """)
                
                # Add breathing animation
                self.add_breathing_animation(mascot_container)
                
            else:
                # Fallback with emoji
                mascot_container.setText("🌊")
                mascot_container.setStyleSheet("""
                    QLabel {
                        font-size: 36px;
                        background: rgba(255, 255, 255, 0.15);
                        border: 2px solid rgba(255, 255, 255, 0.3);
                        border-radius: 50px;
                        color: white;
                    }
                """)
                self.add_breathing_animation(mascot_container)
            
            layout.addWidget(mascot_container)
            
        except Exception as e:
            # Simple fallback
            placeholder = QLabel("🌊")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setFixedSize(100, 100)
            placeholder.setStyleSheet("""
                QLabel {
                    font-size: 36px;
                    background: rgba(255, 255, 255, 0.15);
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-radius: 50px;
                    color: white;
                }
            """)
            layout.addWidget(placeholder)
    
    def add_breathing_animation(self, widget):
        """Add subtle breathing animation to mascot matching login dialog style"""
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QSize
        
        try:
            # Create size-based breathing animation like login dialog
            self.breathing_animation = QPropertyAnimation(widget, b"minimumSize")
            self.breathing_animation.setDuration(3000)  # 3 second cycle
            self.breathing_animation.setStartValue(QSize(95, 95))
            self.breathing_animation.setEndValue(QSize(105, 105))
            self.breathing_animation.setEasingCurve(QEasingCurve.InOutSine)
            
            # Create return animation
            self.breathing_animation_2 = QPropertyAnimation(widget, b"minimumSize")
            self.breathing_animation_2.setDuration(3000)
            self.breathing_animation_2.setStartValue(QSize(105, 105))
            self.breathing_animation_2.setEndValue(QSize(95, 95))
            self.breathing_animation_2.setEasingCurve(QEasingCurve.InOutSine)
            
            # Link animations for continuous breathing
            self.breathing_animation.finished.connect(self.breathing_animation_2.start)
            self.breathing_animation_2.finished.connect(self.breathing_animation.start)
            self.breathing_animation.start()
            
        except Exception:
            # Skip animation if there are issues
            pass
    
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
        try:
            self.message_timer.stop()
            self.progress_timer.stop()
            if hasattr(self, 'breathing_animation'):
                self.breathing_animation.stop()
            if hasattr(self, 'breathing_animation_2'):
                self.breathing_animation_2.stop()
        except:
            pass
        self.close()