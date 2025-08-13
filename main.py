# Add environment variable to disable Google Drive API tokens
# This prevents automatic token refresh
import os
os.environ['GOOGLE_DRIVE_NO_AUTO_AUTH'] = '1'
# Disable stream flushing to prevent invalid argument errors on network drives
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

# Set matplotlib backend to avoid CORS font issues
import matplotlib
matplotlib.use('Qt5Agg')

import sys
from pathlib import Path
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Setup minimal logging - only essential startup info
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Allow INFO level for main application startup
logging.getLogger('__main__').setLevel(logging.INFO)
logging.getLogger('src.gui.handlers.settings_handler').setLevel(logging.INFO)
logging.getLogger('src.gui.main_window').setLevel(logging.INFO)

# Enable detailed logging for auto-sync debugging
logging.getLogger('src.gui.handlers.auto_update_handler').setLevel(logging.INFO)
logging.getLogger('src.gui.handlers.field_data_consolidator').setLevel(logging.INFO)
logging.getLogger('src.gui.handlers.runs_folder_monitor').setLevel(logging.INFO)

# Enable DEBUG level logging for shared drive database handler (draft debugging)
logging.getLogger('src.gui.handlers.shared_drive_db_handler').setLevel(logging.DEBUG)

# Suppress noisy third-party libraries
logging.getLogger('PyQt5').setLevel(logging.ERROR)
logging.getLogger('matplotlib').setLevel(logging.ERROR)
logging.getLogger('PIL').setLevel(logging.ERROR)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('google.auth').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# Add the project root directory to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logger.info(f"Python version: {sys.version}")
logger.info(f"Project root: {PROJECT_ROOT}")

# Ensure QtWebEngine can be imported safely
logger.info("Setting up Qt attributes")
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Now import GUI components
logger.info("Importing GUI components")
from PyQt5.QtWebEngineWidgets import QWebEngineView
from src.gui.main_window import MainWindow
from src.database.manager import DatabaseManager

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundles"""
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = PROJECT_ROOT
    return base_path / Path(relative_path)

def main():
    try:
        logger.info("Initializing QApplication")
        
        # Enable high DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        app = QApplication(sys.argv)
        
        # Load icon via resource_path for bundle support
        icon_path = resource_path('src/gui/icons/app_icon.webp')
        if not icon_path.exists():
            icon_path = resource_path('src/gui/icons/app_icon.ico')
            logger.debug(f"Webp icon not found, falling back to ico: {icon_path.absolute()}")
        
        logger.info(f"Loading icon from: {icon_path.absolute()}")
        
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        else:
            logger.warning(f"No icon file found at {icon_path.absolute()}")
            
        logger.info("Creating main window")
        window = MainWindow()
        # Use the same icon path that worked for the app
        window.setWindowIcon(QIcon(str(icon_path)))
        
        logger.info("Showing main window")
        window.show()
        
        # Log screen information
        screen = window.screen()
        logger.info(f"Initial screen: {screen.name()}, "
                   f"Size: {screen.size().width()}x{screen.size().height()}")
        
        logger.info("Application initialized successfully")
        logger.info("Entering application main loop")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical("Fatal error in main application", exc_info=True)
        raise SystemExit(1) from e

if __name__ == "__main__":
    logger.info("Starting application")
    main()