import sqlite3
from pathlib import Path
import logging
from datetime import datetime
from .initializer import DatabaseInitializer
from .models.well import WellModel
from .models.water_level import WaterLevelModel
from .models.barologger import BarologgerModel
from typing import List, Dict, Optional, Tuple
from sqlite3.dbapi2 import Connection
import queue
from PyQt5.QtCore import QObject, pyqtSignal
import time
import psutil  # Add psutil import for memory detection

logger = logging.getLogger(__name__)

class DatabaseManager(QObject):
    """
    Manages database connections and operations for the water level monitoring application.
    
    Features:
    - Dynamic SQLite optimization based on available system memory
    - Connection pooling to improve performance
    - Google Drive synchronization support
    - Signals for database changed/synced events
    - Cloud database support with manual save functionality
    
    Note: Requires psutil package for memory detection and optimization
    """
    
    database_changed = pyqtSignal(str)  # Signal emitting db name
    database_synced = pyqtSignal(str)   # Signal emitting when db is synced with Google Drive
    database_modified = pyqtSignal()    # Signal emitting when db is modified

    def __init__(self):
        super().__init__()
        self.current_db = None
        self._well_model = None
        self._water_level_model = None
        self._baro_model = None
        self._connection_pool = queue.Queue(maxsize=5)  # Pool size of 5
        self.is_google_drive_db = False
        self.google_drive_handler = None
        self._modified_since_sync = False  # Track if database has been modified since last sync
        self.settings_handler = None  # Add settings_handler attribute
        
        # Cloud database support
        self.is_cloud_database = False
        self.cloud_project_name = None
        self.cloud_project_info = None
        self.temp_db_path = None
        self.is_cloud_modified = False
        self.change_tracker = None
        
    def set_google_drive_handler(self, handler):
        """Set the Google Drive handler for database operations"""
        self.google_drive_handler = handler
        
    def set_settings_handler(self, handler):
        """Set the settings handler for database operations"""
        self.settings_handler = handler
        
    def set_user_auth_service(self, service):
        """Set the user authentication service for change tracking"""
        self._user_auth_service = service
        
    def open_cloud_database(self, temp_path: str, project_name: str, project_info: Dict):
        """
        Open a cloud database from a temporary path.
        
        Args:
            temp_path: Path to the temporary database file
            project_name: Name of the cloud project
            project_info: Project information dictionary
        """
        # Reset cloud state
        self.is_cloud_database = True
        self.cloud_project_name = project_name
        self.cloud_project_info = project_info
        self.temp_db_path = temp_path
        self.is_cloud_modified = False
        
        # Initialize change tracker if we have the required dependencies
        if hasattr(self, '_user_auth_service') and self._user_auth_service:
            from ..gui.handlers.change_tracker import ChangeTracker
            self.change_tracker = ChangeTracker(self, self._user_auth_service)
            logger.info(f"Change tracking initialized for cloud database: {project_name}")
        
        # Open as regular database
        self.open_database(Path(temp_path))
        
    def mark_cloud_modified(self):
        """Mark cloud database as modified"""
        if self.is_cloud_database:
            self.is_cloud_modified = True
            self.database_modified.emit()
            
    def reset_cloud_state(self):
        """Reset cloud database state"""
        self.is_cloud_database = False
        self.cloud_project_name = None
        self.cloud_project_info = None
        self.temp_db_path = None
        self.is_cloud_modified = False
        self.change_tracker = None
    
    def configure_connection(self, conn):
        """
        Configure SQLite connection with optimized PRAGMA settings based on available system memory.
        
        Args:
            conn: SQLite connection to configure
        """
        # Get system memory (in GB)
        available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        # Basic settings that work everywhere
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = OFF')
        
        # Adapt settings to available memory
        if available_memory_gb > 16:
            # High-performance settings for well-equipped machines
            conn.execute('PRAGMA cache_size = -204800')       # 200MB cache
            conn.execute('PRAGMA mmap_size = 8589934592')     # 8GB mmap
            logger.info(f"Using high-performance SQLite settings (mem: {available_memory_gb:.1f}GB)")
        elif available_memory_gb > 8:
            # Medium settings
            conn.execute('PRAGMA cache_size = -102400')       # 100MB cache
            conn.execute('PRAGMA mmap_size = 4294967296')     # 4GB mmap
            logger.info(f"Using medium SQLite settings (mem: {available_memory_gb:.1f}GB)")
        else:
            # Conservative settings for limited resources
            conn.execute('PRAGMA cache_size = -10240')        # 10MB cache
            conn.execute('PRAGMA mmap_size = 1073741824')     # 1GB mmap
            logger.info(f"Using conservative SQLite settings (mem: {available_memory_gb:.1f}GB)")
        
        # Common settings for all configurations
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA page_size = 8192')
        
    def _create_connection(self) -> Connection:
        """Create a new database connection"""
        if not self.current_db:
            raise Exception("No database selected")
        
        conn = sqlite3.connect(self.current_db)
        self.configure_connection(conn)
        return conn
    
    def get_connection(self) -> Connection:
        """Get a connection from the pool, or create one if needed."""
        # First check if we have any in the pool
        try:
            if not self._connection_pool.empty():
                conn = self._connection_pool.get(block=False)
                return conn
        except Exception as e:
            logger.error(f"Error retrieving connection from pool: {e}")
        
        # None in pool, create new connection
        try:
            # Create new connection with optimized settings
            conn = self._create_connection()
            return conn
        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            raise

            
    def return_connection(self, conn: Connection):
        """Return a connection to the pool, ensuring minimal connection closures"""
        try:
            if conn:
                self._connection_pool.put_nowait(conn)
                logger.debug("Returned connection to pool")
            else:
                logger.warning("Attempted to return a None connection")
        except queue.Full:
            logger.warning("Connection pool full, closing excess connection")
            conn.close()

    
    @property
    def well_model(self):
        if self._well_model is None and self.current_db:
            self._well_model = WellModel(self.current_db)
            # Set the db_manager reference
            if hasattr(self._well_model, 'set_db_manager'):
                self._well_model.set_db_manager(self)
        return self._well_model
        
    @property
    def water_level_model(self):
        if self._water_level_model is None and self.current_db:
            self._water_level_model = WaterLevelModel(self.current_db)
            # Set the db_manager reference
            if hasattr(self._water_level_model, 'set_db_manager'):
                self._water_level_model.set_db_manager(self)
        return self._water_level_model
        
    @property
    def baro_model(self):
        if self._baro_model is None and self.current_db:
            self._baro_model = BarologgerModel(self.current_db)
            # Set the db_manager reference
            if hasattr(self._baro_model, 'set_db_manager'):
                self._baro_model.set_db_manager(self)
        return self._baro_model
    
    @property
    def has_unsaved_changes(self):
        """Return True if the database has been modified since the last sync"""
        return self.is_google_drive_db and self._modified_since_sync
    
    def create_database(self, db_path: str, use_google_drive=False):
        """Create a new database"""
        if use_google_drive and self.google_drive_handler:
            # Create database in Google Drive
            local_path = self.google_drive_handler.create_database(Path(db_path).name)
            if local_path:
                path = Path(local_path)
                initializer = DatabaseInitializer(path)
                initializer.initialize_database()
                self.current_db = path
                self.is_google_drive_db = True  # This is still needed for sync functionality
                self._modified_since_sync = False  # New database is synced initially
                logger.info(f"Created new database in Google Drive: {path}")
                self.database_changed.emit(Path(db_path).name)
                return True
            else:
                logger.error("Failed to create database in Google Drive")
                return False
        else:
            # Create local database
            path = Path(db_path)
            initializer = DatabaseInitializer(path)
            initializer.initialize_database()
            self.current_db = path
            self.is_google_drive_db = False
            self._modified_since_sync = False
            logger.info(f"Created new database: {path}")
            self.database_changed.emit(Path(db_path).name)
            return True
    
    def open_database(self, db_path: str, use_google_drive=False):
        """Open database with improved cleanup and error handling"""
        try:
            # All databases are treated as local after initialization
            path = Path(db_path)
            
            # Set Google Drive flag based on filename suffix
            self.is_google_drive_db = "_(drive)" in path.name
            self._modified_since_sync = False
            
            if not path.exists():
                raise FileNotFoundError(f"Database not found: {path}")

            # If it's the same database, just return
            if self.current_db == path:
                logger.info(f"Database {db_path} is already open.")
                return True

            # Clear existing connections and models first
            self.close()
            
            # Initialize if empty
            if path.stat().st_size == 0:
                initializer = DatabaseInitializer(path)
                initializer.initialize_database()

            # Set new database and create models
            self.current_db = path
            # Only emit after successful switch - use the full name including path
            self.database_changed.emit(path.name)
            logger.info(f"Opened database: {path}")
            return True

        except Exception as e:
            logger.error(f"Error opening database {db_path}: {e}")
            self.close()  # Clean up on error
            raise

    def sync_with_google_drive(self):
        """Sync the current database with Google Drive"""
        if not self.is_google_drive_db or not self.google_drive_handler or not self.current_db:
            logger.warning("Cannot sync: not a Google Drive database or no handler available")
            return False
            
        try:
            # Upload the current database to Google Drive
            if self.google_drive_handler.upload_database(self.current_db):
                logger.info(f"Synced database {self.current_db.name} with Google Drive")
                self._modified_since_sync = False  # Reset modification flag after successful sync
                self.database_synced.emit(self.current_db.name)
                return True
            else:
                logger.error(f"Failed to sync database {self.current_db.name} with Google Drive")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing database with Google Drive: {e}")
            return False

    def import_wells(self, wells_data: List[Dict]) -> Tuple[bool, str]:
        """Import wells into database"""
        if not self.current_db:
            raise Exception("No database selected")
            
        try:
            success, message = self.well_model.import_wells(wells_data)
            if success:
                logger.info(message)
                # Mark as modified but don't automatically sync
                if self.is_google_drive_db:
                    self._modified_since_sync = True
                # Also mark cloud database as modified
                if self.is_cloud_database:
                    self.mark_cloud_modified()
            else:
                logger.error(f"Error importing wells: {message}")
            return success, message
            
        except Exception as e:
            logger.error(f"Error in DatabaseManager import: {e}")
            return False, str(e)
    
    def update_well_picture(self, well_number: str, picture_path: str) -> bool:
        """Update the picture for a specific well"""
        if not self.current_db or not self.well_model:
            raise Exception("No database selected")
            
        success = self.well_model.update_well_picture(well_number, picture_path)
        
        # Mark as modified but don't automatically sync
        if success and self.is_google_drive_db:
            self._modified_since_sync = True
            
        return success
    
    def get_well_picture_path(self, well_number: str) -> str:
        """Get the full path to a well's picture"""
        if not self.current_db or not self.well_model:
            raise Exception("No database selected")
            
        return self.well_model.get_well_picture_path(well_number)
    
    def get_database_stats(self) -> Optional[Dict]:
        """Get current database statistics"""
        if not self.current_db:
            return None
            
        try:
            with sqlite3.connect(self.current_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM wells")
                well_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM transducers 
                    WHERE end_date IS NULL
                """)
                transducer_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM barologgers 
                    WHERE status = 'active'
                """)
                baro_count = cursor.fetchone()[0]
                
                return {
                    'name': self.current_db.name,
                    'well_count': well_count,
                    'transducer_count': transducer_count,
                    'barologger_count': baro_count,
                    'last_update': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'is_google_drive': self.is_google_drive_db,
                    'has_unsaved_changes': self.has_unsaved_changes
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return None
    
    def close(self):
        """Enhanced cleanup of database resources without automatic sync"""
        logger.debug("Entering close() method")
        start_time = time.time()
        try:
            # Clear all models
            self._well_model = None
            self._water_level_model = None
            self._baro_model = None

            # Clear connection pool
            logger.debug("Starting connection pool cleanup loop")
            connections_closed = 0
            loop_start_time = time.time()
            while True:
                conn = None
                try:
                    conn = self._connection_pool.get_nowait()
                    if conn:
                        connections_closed += 1
                        close_start_time = time.time()
                        logger.debug(f"Closing connection #{connections_closed}...")
                        conn.close()
                        close_end_time = time.time()
                        logger.debug(f"Connection #{connections_closed} closed (took {close_end_time - close_start_time:.4f} seconds)")
                    else:
                        logger.debug("Pool returned None connection object.")
                except queue.Empty:
                    logger.debug("Connection pool is empty, breaking loop.")
                    break
                except Exception as close_exc:
                    logger.error(f"Error closing connection #{connections_closed}: {close_exc}")
                    if conn: 
                        logger.debug(f"Attempting to close connection #{connections_closed} again after error.")
                        try:
                           conn.close()
                        except Exception as retry_exc:
                            logger.error(f"Failed to close connection #{connections_closed} on retry: {retry_exc}")

            loop_end_time = time.time()
            logger.debug(f"Finished connection pool cleanup loop. Closed {connections_closed} connections (loop took {loop_end_time - loop_start_time:.4f} seconds)")

            # Clear current database last
            self.current_db = None
            self.is_google_drive_db = False
            self._modified_since_sync = False

        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
        finally:
            end_time = time.time()
            logger.debug(f"Exiting close() method (total time: {end_time - start_time:.4f} seconds)")

    # Method to mark database as modified
    def mark_as_modified(self):
        """Mark the database as having unsaved changes"""
        if self.is_google_drive_db:
            self._modified_since_sync = True
        
        # Always emit the database_modified signal for UI updates
        self.database_modified.emit()