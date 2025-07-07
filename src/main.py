import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from src.gui.main_window import MainWindow
from src.gui.handlers.style_handler import StyleHandler  # Import StyleHandler

def configure_logging():
    """Configure the logging system."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger first with just console logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Set up console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)
    
    # Try to set up file logging, but don't fail if there are network issues
    try:
        # Check logs directory exists
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        log_file = os.path.join(logs_dir, 'water_level_monitor.log')
        
        # Set up logging to file with error handling
        file_handler = logging.FileHandler(log_file, delay=True)  # delay=True prevents immediate file open
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Just log to console if file logging fails
        console_handler.setLevel(logging.DEBUG)  # Increase console logging level to compensate
        print(f"Warning: Could not set up file logging: {e}")
    
    # Suppress verbose logging from some libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PyQt5').setLevel(logging.WARNING)
    
    return root_logger

def main():
    """Main entry point for the application."""
    # Configure logging first
    logger = configure_logging()
    logger.info("Starting Water Level Monitoring System")
    
    # Create the application
    app = QApplication(sys.argv)
    app.setApplicationName("Water Level Monitoring System")
    
    # Apply consistent styling across the entire application
    StyleHandler.apply_application_style(app)
    
    # Set application-wide attributes
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
