from PyQt5.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QFont
import logging

logger = logging.getLogger(__name__)

class LoadingSplash(QSplashScreen):
    """Simple loading splash screen for the visualizer."""
    
    def __init__(self):
        # Create a simple pixmap for the splash screen
        pixmap = QPixmap(400, 200)
        pixmap.fill(Qt.white)
        
        painter = QPainter(pixmap)
        painter.setPen(Qt.black)
        
        # Draw title
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(20, 50, "Water Level Data Visualizer")
        
        # Draw subtitle
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(20, 80, "Loading, please wait...")
        
        painter.end()
        
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        
        self.setWindowTitle("Loading...")
        self.show()
        
        # Center on screen
        self.move_to_center()
        
    def move_to_center(self):
        """Move splash screen to center of screen."""
        try:
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.desktop().screenGeometry()
            size = self.geometry()
            self.move(
                (screen.width() - size.width()) // 2,
                (screen.height() - size.height()) // 2
            )
        except Exception as e:
            logger.debug(f"Could not center splash screen: {e}")
    
    def update_message(self, message):
        """Update the message shown on the splash screen."""
        self.showMessage(
            message,
            Qt.AlignBottom | Qt.AlignHCenter,
            Qt.black
        )
        
    def close_splash(self):
        """Close the splash screen."""
        self.close()