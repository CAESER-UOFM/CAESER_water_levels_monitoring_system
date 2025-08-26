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
        self.setFixedSize(450, 350)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Center the dialog on screen
        self.center_on_screen()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Add app icon with exact same layout as login dialog
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
        
        # Style with enhanced black metallic gradient background
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:0.2 #2c2c2c, stop:0.5 #1a1a1a, 
                    stop:0.8 #0f0f0f, stop:1 #000000);
                border-radius: 15px;
                border: 3px solid qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #888888, stop:0.5 #555555, stop:1 #333333);
            }
        """)
    
    def setup_circular_mascot(self, layout):
        """Add circular mascot container exactly matching login dialog"""
        try:
            # Import required Qt components
            from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
            from PyQt5.QtGui import QIcon
            from PyQt5.QtCore import QSize
            
            # Create icon layout with stretches exactly like login dialog
            icon_layout = QHBoxLayout()
            
            # Create a centered container for the icon exactly like login dialog
            icon_container = QFrame()
            icon_container.setLayout(QVBoxLayout())
            icon_container.layout().setAlignment(Qt.AlignCenter)
            
            # Create icon frame with maximum size to eliminate all cutoff
            self.icon_frame = QFrame()
            self.icon_frame.setObjectName("iconFrame") 
            self.icon_frame.setFixedSize(150, 150)
            self.icon_frame.setStyleSheet("""
                #iconFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 25), 
                        stop:0.5 rgba(200, 200, 200, 15), 
                        stop:1 rgba(150, 150, 150, 10));
                    border-radius: 75px;
                    border: 3px solid qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 60), 
                        stop:0.5 rgba(180, 180, 180, 50), 
                        stop:1 rgba(120, 120, 120, 40));
                }
            """)
            
            # Create inner layout with more padding to center icon better
            icon_inner_layout = QVBoxLayout(self.icon_frame)
            icon_inner_layout.setContentsMargins(10, 10, 10, 10)
            
            # Create icon label exactly like login dialog
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            
            # Use exact same path approach as login dialog 
            icon_dir = Path(__file__).parent.parent / "icons"
            icon_path = icon_dir / "app_icon.webp"
            if not icon_path.exists():
                icon_path = icon_dir / "water_level_meter.png"
            
            if icon_path.exists():
                # Load with even larger size to fit bigger container
                icon = QIcon(str(icon_path))
                pixmap = icon.pixmap(120, 120)  # Even larger size for bigger container
                icon_label.setPixmap(pixmap)
                
                # Add breathing animation exactly like login dialog
                self.add_breathing_animation()
                
            else:
                # Fallback
                icon_label.setText("🌊")
                icon_label.setStyleSheet("font-size: 36px; color: white;")
            
            # Add label to inner layout exactly like login dialog
            icon_inner_layout.addWidget(icon_label)
            
            # Add icon frame to the centered container exactly like login dialog
            icon_container.layout().addWidget(self.icon_frame)
            
            # Add stretches and container exactly like login dialog
            icon_layout.addStretch()
            icon_layout.addWidget(icon_container)
            icon_layout.addStretch()
            layout.addLayout(icon_layout)
            layout.addSpacing(10)  # Same spacing as login dialog
            
        except Exception as e:
            # Simple fallback
            placeholder = QLabel("🌊")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setFixedSize(100, 100)
            placeholder.setStyleSheet("""
                QLabel {
                    font-size: 36px;
                    background: rgba(255, 255, 255, 30);
                    border: 2px solid rgba(255, 255, 255, 60);
                    border-radius: 50px;
                    color: white;
                }
            """)
            layout.addWidget(placeholder)
    
    def add_breathing_animation(self):
        """Add breathing animation exactly matching login dialog"""
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QSize
        
        try:
            # Create breathing animation with maximum container size
            self.breathe_animation = QPropertyAnimation(self.icon_frame, b"minimumSize")
            self.breathe_animation.setDuration(4000)  # Same duration as login
            self.breathe_animation.setStartValue(QSize(150, 150))  # Updated for maximum container
            self.breathe_animation.setEndValue(QSize(160, 160))
            self.breathe_animation.setEasingCurve(QEasingCurve.InOutSine)
            
            # Create second animation with maximum container size
            self.breathe_animation_2 = QPropertyAnimation(self.icon_frame, b"minimumSize")
            self.breathe_animation_2.setDuration(4000)
            self.breathe_animation_2.setStartValue(QSize(160, 160))
            self.breathe_animation_2.setEndValue(QSize(150, 150))
            self.breathe_animation_2.setEasingCurve(QEasingCurve.InOutSine)
            
            # Link animations exactly like login dialog
            self.breathe_animation.finished.connect(self.breathe_animation_2.start)
            self.breathe_animation_2.finished.connect(self.breathe_animation.start)
            
            # Keep icon centered exactly like login dialog
            def update_maximum_size():
                size = self.icon_frame.minimumSize()
                self.icon_frame.setMaximumSize(size)
                
            self.breathe_animation.valueChanged.connect(update_maximum_size)
            self.breathe_animation_2.valueChanged.connect(update_maximum_size)
            
            # Start animation exactly like login dialog
            self.breathe_animation.start()
            
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
            if hasattr(self, 'breathe_animation'):
                self.breathe_animation.stop()
            if hasattr(self, 'breathe_animation_2'):
                self.breathe_animation_2.stop()
        except:
            pass
        self.close()