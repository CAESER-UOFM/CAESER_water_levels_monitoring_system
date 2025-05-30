# Add environment variable to disable Google Drive API tokens
# This prevents automatic token refresh
import os
os.environ['GOOGLE_DRIVE_NO_AUTO_AUTH'] = '1'
# Disable stream flushing to prevent invalid argument errors on network drives
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

import sys
from pathlib import Path
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Setup logging with more minimal configuration
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for reduced verbosity
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
        # Removed file handler due to network folder access issues
    ]
)

# Set specific loggers to appropriate levels
logging.getLogger('PyQt5').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('googleapiclient').setLevel(logging.WARNING)
logging.getLogger('google.auth').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Keep DEBUG level for database-related operations to track timing
logging.getLogger('src.gui.main_window').setLevel(logging.INFO)
logging.getLogger('src.database.manager').setLevel(logging.INFO)

# Create a custom filter for performance logging
class PerformanceFilter(logging.Filter):
    def filter(self, record):
        # Only allow log messages about database loading times and critical operations
        if 'database change' in record.getMessage() or 'Database open operation' in record.getMessage():
            return True
        # Hide excessive PERF: messages unless they're about total time
        if 'PERF:' in record.getMessage() and 'Total' not in record.getMessage():
            return False
        return True

# Apply the filter to relevant loggers
main_window_logger = logging.getLogger('src.gui.main_window')
main_window_logger.addFilter(PerformanceFilter())
db_manager_logger = logging.getLogger('src.database.manager')
db_manager_logger.addFilter(PerformanceFilter())

# Set very low log level for extremely verbose components
logging.getLogger('src.gui.tabs.database_tab').setLevel(logging.WARNING)
logging.getLogger('src.gui.tabs.barologger_tab').setLevel(logging.WARNING)
logging.getLogger('src.gui.tabs.water_level_tab').setLevel(logging.WARNING)
logging.getLogger('src.gui.tabs.water_level_runs_tab').setLevel(logging.WARNING)

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