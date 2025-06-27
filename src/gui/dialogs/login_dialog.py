import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QGroupBox,
    QGraphicsDropShadowEffect, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QRect, QSize
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPalette, QFont, QMovie, QLinearGradient, QPainter, QPainterPath
import logging

logger = logging.getLogger(__name__)

class LoginDialog(QDialog):
    # Define signals
    driveLoginRequested = pyqtSignal()
    guestLoginRequested = pyqtSignal()  # Add the missing signal
    
    def __init__(self, parent=None, auth_service=None):
        super().__init__(parent)
        
        self.setWindowTitle("Login")
        self.setMinimumWidth(340)  # Reduced by 15% from 400
        self.auth_service = auth_service
        
        self.setup_ui()
    
    def set_force_login(self, force):
        """Set whether login is required (no guest mode option)"""
        # This method is kept for compatibility but doesn't do anything now
        pass
        
    def setup_ui(self):
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create a container frame with rounded corners
        container = QFrame(self)
        container.setObjectName("loginContainer")
        container.setStyleSheet("""
            #loginContainer {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                   stop:0 #2C3E50, stop:1 #3498DB);
                border-radius: 15px;
                border: 2px solid #1B2631;
            }
        """)
        
        # Add drop shadow effect to container
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 0)
        container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add app icon with pulsing animation
        icon_layout = QHBoxLayout()
        
        # Create a centered container for the icon
        icon_container = QFrame()
        icon_container.setLayout(QVBoxLayout())
        icon_container.layout().setAlignment(Qt.AlignCenter)
        
        icon_frame = QFrame()
        icon_frame.setObjectName("iconFrame")
        icon_frame.setFixedSize(100, 100)
        icon_frame.setStyleSheet("""
            #iconFrame {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 50px;
                border: 2px solid rgba(255, 255, 255, 60);
            }
        """)
        
        icon_inner_layout = QVBoxLayout(icon_frame)
        icon_inner_layout.setContentsMargins(5, 5, 5, 5)
        
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Try webp first, fall back to ico if needed
        icon_path = Path('src/gui/icons/app_icon.webp')
        if not icon_path.exists():
            icon_path = Path('src/gui/icons/app_icon.ico')
        
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            pixmap = icon.pixmap(83, 83)
            icon_label.setPixmap(pixmap)
            
            # Create breathing animation
            self.breathe_animation = QPropertyAnimation(icon_frame, b"minimumSize")
            self.breathe_animation.setDuration(4000)  # Slow breathing animation
            self.breathe_animation.setStartValue(QSize(100, 100))
            self.breathe_animation.setEndValue(QSize(110, 110))
            self.breathe_animation.setEasingCurve(QEasingCurve.InOutSine)
            
            # Create the second part of the breathing animation
            self.breathe_animation_2 = QPropertyAnimation(icon_frame, b"minimumSize")
            self.breathe_animation_2.setDuration(4000)
            self.breathe_animation_2.setStartValue(QSize(110, 110))
            self.breathe_animation_2.setEndValue(QSize(100, 100))
            self.breathe_animation_2.setEasingCurve(QEasingCurve.InOutSine)
            
            # Link animations to create continuous breathing
            self.breathe_animation.finished.connect(self.breathe_animation_2.start)
            self.breathe_animation_2.finished.connect(self.breathe_animation.start)
            
            # Keep icon centered and properly sized
            def update_maximum_size():
                size = icon_frame.minimumSize()
                icon_frame.setMaximumSize(size)
                
            self.breathe_animation.valueChanged.connect(update_maximum_size)
            self.breathe_animation_2.valueChanged.connect(update_maximum_size)
            
            # Start the breathing animation
            self.breathe_animation.start()
        
        icon_inner_layout.addWidget(icon_label)
        
        # Add icon frame to the centered container
        icon_container.layout().addWidget(icon_frame)
        
        icon_layout.addStretch()
        icon_layout.addWidget(icon_container)
        icon_layout.addStretch()
        container_layout.addLayout(icon_layout)
        container_layout.addSpacing(10)
        
        # Create welcome message with custom font
        title_layout = QVBoxLayout()
        welcome_label = QLabel("Water Level Monitoring")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("""
            font-size: 22px; 
            font-weight: bold; 
            color: white; 
            font-family: 'Segoe UI', Arial;
            letter-spacing: 1px;
        """)
        title_layout.addWidget(welcome_label)
        
        # Create description label
        description = QLabel("Sign in to continue")
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 14px;")
        title_layout.addWidget(description)
        container_layout.addLayout(title_layout)
        container_layout.addSpacing(30)
        
        # Create login form with modern styling
        form_layout = QVBoxLayout()
        
        # Username field with icon
        username_frame = QFrame()
        username_frame.setObjectName("inputFrame")
        username_frame.setStyleSheet("""
            #inputFrame {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        username_frame.setMinimumHeight(45)
        username_layout = QHBoxLayout(username_frame)
        username_layout.setContentsMargins(10, 5, 10, 5)
        
        username_icon = QLabel("👤")
        username_icon.setStyleSheet("color: white; font-size: 18px;")
        username_layout.addWidget(username_icon)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 120);
            }
        """)
        username_layout.addWidget(self.username_input)
        form_layout.addWidget(username_frame)
        form_layout.addSpacing(15)
        
        # Password field with icon
        password_frame = QFrame()
        password_frame.setObjectName("inputFrame")
        password_frame.setStyleSheet("""
            #inputFrame {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        password_frame.setMinimumHeight(45)
        password_layout = QHBoxLayout(password_frame)
        password_layout.setContentsMargins(10, 5, 10, 5)
        
        password_icon = QLabel("🔒")
        password_icon.setStyleSheet("color: white; font-size: 18px;")
        password_layout.addWidget(password_icon)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 120);
            }
        """)
        password_layout.addWidget(self.password_input)
        form_layout.addWidget(password_frame)
        form_layout.addSpacing(30)
        
        container_layout.addLayout(form_layout)
        
        # Create buttons with hover effect
        button_layout = QHBoxLayout()
        
        exit_button = QPushButton("Exit")
        exit_button.setObjectName("exitButton")
        exit_button.setCursor(Qt.PointingHandCursor)
        exit_button.setStyleSheet("""
            #exitButton {
                background-color: rgba(231, 76, 60, 200);
                color: white;
                border-radius: 10px;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: bold;
            }
            #exitButton:hover {
                background-color: rgba(231, 76, 60, 255);
            }
            #exitButton:pressed {
                background-color: rgba(192, 57, 43, 255);
            }
        """)
        exit_button.setMinimumHeight(40)
        exit_button.clicked.connect(self.reject)
        
        self.login_button = QPushButton("Sign In")
        self.login_button.setObjectName("loginButton")
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setStyleSheet("""
            #loginButton {
                background-color: rgba(46, 204, 113, 200);
                color: white;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            #loginButton:hover {
                background-color: rgba(46, 204, 113, 255);
            }
            #loginButton:pressed {
                background-color: rgba(39, 174, 96, 255);
            }
        """)
        self.login_button.setMinimumHeight(40)
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.handle_login)
        
        button_layout.addWidget(exit_button)
        button_layout.addSpacing(15)
        button_layout.addWidget(self.login_button)
        
        container_layout.addLayout(button_layout)
        container_layout.addSpacing(10)
        
        # Add footer with copyright
        footer = QLabel("© 2025 CAESER, University of Memphis")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 12px;")
        container_layout.addWidget(footer)
        
        main_layout.addWidget(container)
        
        # Allow window to be moved by dragging
        self.mousePressPosition = None
        
    def mousePressEvent(self, event):
        """Enable window dragging"""
        if event.button() == Qt.LeftButton:
            self.mousePressPosition = event.globalPos()
            
    def mouseMoveEvent(self, event):
        """Enable window dragging"""
        if event.buttons() == Qt.LeftButton and self.mousePressPosition:
            delta = event.globalPos() - self.mousePressPosition
            self.move(self.pos() + delta)
            self.mousePressPosition = event.globalPos()
    
    def handle_guest_login(self):
        """Handle guest login button click"""
        if self.auth_service:
            success, message = self.auth_service.login_as_guest()
            if success:
                self.accept()
            else:
                self.show_animated_message(f"Guest login failed: {message}")
        else:
            self.show_animated_message("Authentication service not available.")
    
    def handle_login(self):
        """Handle login button click"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.show_animated_message("Please enter both username and password.")
            return
        
        # Validate credentials using authentication service
        if self.auth_service:
            success, message = self.auth_service.login(username, password)
            if success:
                self.accept()
            else:
                self.show_animated_message(message)
        else:
            self.show_animated_message("Authentication service not available.")
    
    def show_animated_message(self, message):
        """Show an animated error message inside the dialog"""
        if hasattr(self, 'message_label'):
            # Remove existing message if present
            self.message_label.deleteLater()
            
        # Create new message frame with animation
        self.message_label = QLabel(message)
        self.message_label.setObjectName("errorMessage")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            #errorMessage {
                background-color: rgba(231, 76, 60, 180);
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        # Insert message before the buttons
        layout = self.findChild(QFrame, "loginContainer").layout()
        layout.insertWidget(layout.count()-2, self.message_label)
        
        # Create fade in animation
        self.fade_in = QPropertyAnimation(self.message_label, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_in.start()
    
    def validate_credentials(self, username, password):
        """Validate user credentials - fallback method for legacy support"""
        # Look for config/users.json
        config_dir = Path.cwd() / "config"
        users_file = config_dir / "users.json"
        
        try:
            if not users_file.exists():
                logger.warning(f"Users file not found: {users_file}")
                # If no users file, accept default admin credentials
                return username == "admin" and password == "admin"
            
            # Load users from file
            with open(users_file, 'r') as f:
                user_data = json.load(f)
            
            # Check credentials
            for user in user_data.get('users', []):
                if user.get('username') == username and user.get('password') == password:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            # If any error, fall back to default admin check
            return username == "admin" and password == "admin"
    
    def closeEvent(self, event):
        """Handle dialog close event (X button)"""
        # Make sure the dialog is rejected when closed with the X button
        self.reject()
        event.accept()