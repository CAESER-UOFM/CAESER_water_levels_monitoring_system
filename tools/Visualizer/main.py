import sys
import os
import logging
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication  # This import is needed here

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set specific loggers to DEBUG level
rise_logger = logging.getLogger('gui.tabs.recharge.rise_tab')
rise_logger.setLevel(logging.DEBUG)

# Flag to skip requirements check - set to True after first run
SKIP_REQUIREMENTS_CHECK = False

def check_requirements():
    """Check if all required packages are installed and install them if missing."""
    # Use global statement at beginning of function
    global SKIP_REQUIREMENTS_CHECK
    
    # Skip requirements check if flag is set
    if SKIP_REQUIREMENTS_CHECK:
        logger.debug("Skipping requirements check (disabled)")
        return True
        
    logger.debug("Starting requirements check...")
    required_packages = [
        'PyQt5',
        'pandas',
        'matplotlib',
        'scipy',
        'numpy',
        'folium',
        'geopandas',
        'PyQtWebEngine',
        'psutil'  # Add psutil to required packages for memory detection
    ]
    missing_packages = []
    
    logger.debug("Checking each required package...")
    # Check all packages at once using importlib.util to avoid importing them
    import importlib.util
    for package in required_packages:
        logger.debug(f"Checking package: {package}")
        try:
            # Use importlib.util.find_spec for faster checking without importing
            spec = importlib.util.find_spec(package)
            if spec is not None:
                # Try to get version info using pkg_resources
                try:
                    import pkg_resources
                    version = pkg_resources.get_distribution(package).version
                    logger.debug(f"Package {package} is already installed (version {version})")
                except (pkg_resources.DistributionNotFound, ImportError):
                    logger.debug(f"Package {package} is already installed (version unknown)")
            else:
                logger.warning(f"Required package {package} is not installed")
                missing_packages.append(package)
        except ImportError:
            logger.warning(f"Required package {package} is not installed")
            missing_packages.append(package)
    
    if missing_packages:
        logger.info(f"Found {len(missing_packages)} missing packages: {', '.join(missing_packages)}")
        print("Installing missing required packages...")
        try:
            import subprocess
            logger.debug(f"Using Python executable: {sys.executable}")
            logger.debug(f"Attempting to install packages: {missing_packages}")
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            logger.info("Successfully installed all missing packages")
            print("Successfully installed all missing packages.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing packages: {e}")
            print(f"Error installing packages: {e}")
            print("\nPlease install the missing packages manually using:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    
    # Create a flag file to skip requirements check in future runs
    try:
        flag_file = os.path.join(os.path.dirname(__file__), ".requirements_checked")
        with open(flag_file, "w") as f:
            f.write("Requirements check completed successfully")
        logger.debug(f"Created requirements check flag file: {flag_file}")
        SKIP_REQUIREMENTS_CHECK = True  # No need for global here now
    except Exception as e:
        logger.warning(f"Could not create requirements check flag file: {e}")
    
    logger.debug("Requirements check completed successfully")
    return True

def optimize_matplotlib():
    """Optimize matplotlib settings for better performance."""
    import matplotlib
    
    # Use a simple font family that's guaranteed to exist
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
    
    # Disable font manager logging
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
    
    # Use a non-interactive backend for better performance
    matplotlib.use('Agg')
    
    # Disable interactive mode
    matplotlib.interactive(False)
    
    # Set a lower figure DPI to improve rendering speed
    matplotlib.rcParams['figure.dpi'] = 80

def main():
    global SKIP_REQUIREMENTS_CHECK
    
    logger.debug("Starting application...")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Python executable: {sys.executable}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    
    # Check for requirements flag file to skip requirements check
    flag_file = os.path.join(os.path.dirname(__file__), ".requirements_checked")
    if os.path.exists(flag_file):
        SKIP_REQUIREMENTS_CHECK = True
        logger.debug("Requirements check will be skipped (flag file exists)")
    
    # Apply Qt attributes before initializing QApplication
    # This is critical to do before any Qt widgets are created
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Disable QtWebEngine sandbox to allow loading from network paths
    # This setting is critical for network paths
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    
    # First check if requirements are met
    logger.debug("Checking requirements...")
    if not check_requirements():
        logger.error("Requirements check failed")
        input("Press Enter to exit...")
        return 1
    
    logger.debug("Importing required packages...")
    # Optimize matplotlib before importing any visualization packages
    optimize_matplotlib()
    
    # Now import the rest of the packages
    import sqlite3
    from PyQt5.QtWidgets import QMessageBox, QFileDialog
    from PyQt5.QtWebEngineWidgets import QWebEngineSettings
    import json
    import time
    
    # Lazy import other modules only when needed
    from simple_db_manager import SimpleDatabaseManager
    
    # Show Python environment info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    
    logger.debug("Creating QApplication...")
    # Create the application
    app = QApplication(sys.argv)
    
    # Apply additional WebEngine optimizations after app is created
    logger.debug("Configuring WebEngine settings...")
    QWebEngineSettings.globalSettings().setAttribute(
        QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
    )
    QWebEngineSettings.globalSettings().setAttribute(
        QWebEngineSettings.LocalContentCanAccessFileUrls, True
    )
    QWebEngineSettings.globalSettings().setAttribute(
        QWebEngineSettings.AllowRunningInsecureContent, True
    )
    
    # Disable disk cache for WebEngine to improve performance
    QWebEngineSettings.globalSettings().setAttribute(
        QWebEngineSettings.WebGLEnabled, False  # Disable WebGL for better performance
    )
    
    # Get database path from settings if available
    settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
    default_db_path = r"S:\Water_Projects\CAESER\Water_Data_Series\water_levels_monitoring\CAESER_GENERAL.db"
    selected_well = None
    
    db_path = default_db_path
    
    # Try to load from settings first
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                saved_db_path = settings.get('database_path')
                selected_well = settings.get('selected_well')
                logger.debug(f"Read settings: DB path = {saved_db_path}, well = {selected_well}")
                
                if saved_db_path and os.path.exists(saved_db_path):
                    db_path = saved_db_path
                    logger.info(f"Using database path from settings: {db_path}")
                    if selected_well:
                        logger.info(f"Well selected from settings: {selected_well}")
                else:
                    logger.warning(f"Saved database path not found: {saved_db_path}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    logger.debug(f"Checking database path: {db_path}")
    
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at: {db_path}")
        
        # Ask user for database file
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Database Not Found")
        msg_box.setText(f"The database file was not found at:\n{db_path}")
        msg_box.setInformativeText("Would you like to select a database file?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        if msg_box.exec_() == QMessageBox.Yes:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(
                None, "Select Database File", "", 
                "SQLite Database Files (*.db *.sqlite);;All Files (*)", 
                options=options
            )
            
            if file_path and os.path.exists(file_path):
                db_path = file_path
                
                # Save to settings
                try:
                    settings = {'database_path': db_path}
                    if selected_well:
                        settings['selected_well'] = selected_well
                    with open(settings_path, 'w') as f:
                        json.dump(settings, f)
                    logger.info(f"Saved database path to settings: {db_path}")
                except Exception as e:
                    logger.error(f"Error saving settings: {e}")
            else:
                logger.error("No database file selected")
                QMessageBox.critical(None, "Error", "No database file was selected. The application will now exit.")
                return 1
        else:
            # User chose not to select a database file
            logger.error("User cancelled database selection")
            QMessageBox.critical(None, "Error", "A database file is required to run this application.")
            return 1
    
    try:
        # Verify the database file is valid and can be connected to
        logger.debug(f"Verifying database file: {db_path}")
        
        # Always use quick validation for faster startup
        use_quick_validation = True
        logger.info(f"Using quick validation for faster startup")
        
        try:
            # Measure database load time
            start_time = time.time()
            
            # Use minimal validation - just check if SQLite can open the file
            try:
                # Most lightweight connection possible for validation
                conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1&nolock=1", uri=True)
                # Just verify we can execute a simple query
                conn.execute("SELECT 1").fetchone()
                conn.close()
                logger.info("Quick database validation passed")
            except sqlite3.Error as e:
                logger.error(f"Database verification failed: {e}")
                QMessageBox.critical(None, "Error", f"Failed to open database: {str(e)}")
                return 1
            
            # Log verification time
            end_time = time.time()
            logger.info(f"Database verification completed in {(end_time - start_time)*1000:.1f}ms")
            
        except sqlite3.Error as e:
            logger.error(f"Database verification failed: {e}")
            QMessageBox.critical(None, "Error", f"Failed to open database: {str(e)}")
            return 1
        
        # Create database manager with optimized connection
        logger.info(f"Creating database manager for: {db_path}")
        start_time = time.time()
        
        # Use deferred initialization and read-only optimization for faster loading
        db_manager = SimpleDatabaseManager(db_path, quick_validation=True, deferred_init=True)
        end_time = time.time()
        logger.info(f"Database manager created in {(end_time - start_time)*1000:.1f}ms")
        
        # Optionally preload common data in background thread to improve first-use performance
        import threading
        
        # Create and show the dialog FIRST, then preload data
        # This allows the UI to appear more quickly while data loads in background
        from gui.dialogs.water_level_visualizer import WaterLevelVisualizer
        
        # Create and show the dialog
        logger.info("Creating visualizer dialog...")
        start_time = time.time()
        dialog = WaterLevelVisualizer(db_manager)
        
        # If a well was selected, show it in the dialog
        if selected_well:
            logger.info(f"Setting selected well to: {selected_well}")
            # Set this as a property so the dialog can access it after initializing
            dialog.pre_selected_well = selected_well
        
        # Show the dialog non-modally
        dialog.show()
        end_time = time.time()
        logger.info(f"Dialog creation and display completed in {(end_time - start_time)*1000:.1f}ms")
        
        # Process UI events to help load the wells table
        app.processEvents()
        
        # NOW start preloading in background after UI is visible
        preload_thread = threading.Thread(
            target=lambda: db_manager.preload_common_data(),
            daemon=True  # Make thread daemon so it doesn't block application exit
        )
        preload_thread.start()
        logger.info("Started background data preloading")
        
        # Save the database path to settings for next time
        try:
            settings = {'database_path': db_path}
            if selected_well:
                settings['selected_well'] = selected_well
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
            logger.info(f"Saved database path to settings: {db_path}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
        
        logger.debug("Starting event loop...")
        # Start the event loop
        return app.exec_()
        
    except Exception as e:
        logger.error(f"Error initializing application: {e}", exc_info=True)
        QMessageBox.critical(None, "Error", f"Failed to initialize application: {str(e)}")
        return 1

if __name__ == "__main__":
    logger.debug("Script started")
    sys.exit(main())
