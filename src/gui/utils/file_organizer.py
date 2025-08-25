import logging
import shutil
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Import SharedDatabaseXLEManager for temp storage
try:
    from ..handlers.shared_database_xle_manager import SharedDatabaseXLEManager
except ImportError:
    # Fallback if import fails
    SharedDatabaseXLEManager = None
    logger.warning("SharedDatabaseXLEManager not available - shared database temp storage disabled")

class XLEFileOrganizer:
    """Organizes imported XLE files into appropriate folders"""
    
    def __init__(self, app_root_dir: Path = None, db_name: str = None, settings_handler=None, cache_dir: str = None):
        """
        Initialize the file organizer.
        
        Args:
            app_root_dir: Deprecated - will be ignored in favor of settings_handler
            db_name: Database/project name for organizing files
            settings_handler: Settings handler to get XLE import directory
            cache_dir: Cache directory for shared database temp storage
        """
        # Detect if this is a shared database (wlm_ prefix indicates working copy)
        self.db_name = db_name
        self.cache_dir = cache_dir
        self.is_shared_database = db_name and db_name.startswith('wlm_')
        logger.debug(f"DEBUG: XLEFileOrganizer db_name: {repr(db_name)}")
        logger.debug(f"DEBUG: XLEFileOrganizer is_shared_database: {self.is_shared_database}")
        
        # Get XLE import directory - different logic for shared vs local databases
        if self.is_shared_database and settings_handler:
            # For shared databases, use S: drive imported_xle_files folder
            shared_drive_root = settings_handler.get_setting("shared_drive_root", "")
            if shared_drive_root:
                xle_import_base = Path(shared_drive_root) / "imported_xle_files"
                logger.info(f"XLE_ORGANIZER: Using S: drive path for shared database: {xle_import_base}")
            else:
                # Fallback: use hardcoded S: drive path
                s_drive_base = "S:/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring_system"
                xle_import_base = Path(s_drive_base) / "imported_xle_files"
                logger.warning(f"XLE_ORGANIZER: Using fallback S: drive path: {xle_import_base}")
        else:
            # For local databases, use local imported_xle_files directory from settings
            if settings_handler:
                # Use app directory instead of current working directory as fallback
                app_dir = Path(__file__).parent.parent.parent.parent
                xle_import_base = Path(settings_handler.get_setting("xle_import_directory", str(app_dir / "imported_xle_files")))
                logger.debug(f"XLE_ORGANIZER: Using local settings path: {xle_import_base}")
            else:
                # Fallback to app directory instead of current working directory
                app_dir = Path(__file__).parent.parent.parent.parent
                xle_import_base = app_dir / "imported_xle_files"
                logger.warning(f"XLE_ORGANIZER: No settings_handler, using app_dir fallback: {xle_import_base}")
                if app_root_dir:
                    logger.warning("XLEFileOrganizer: app_root_dir parameter is deprecated, use settings_handler instead")
                    xle_import_base = app_root_dir / "imported_xle_files"
        
        if self.is_shared_database:
            # Extract project name from wlm_ prefix
            self.project_name = db_name[4:]  # Remove 'wlm_' prefix
            logger.debug(f"DEBUG: Detected shared database mode for project: {self.project_name}")
            
            # Initialize shared database XLE manager for temp storage
            if SharedDatabaseXLEManager and cache_dir:
                self.shared_xle_manager = SharedDatabaseXLEManager(cache_dir)
                self.use_temp_storage = True
                logger.info(f"XLE file organizer initialized for shared database: {self.project_name} (temp storage)")
            else:
                logger.warning("Shared database detected but temp storage not available - falling back to permanent storage")
                self.use_temp_storage = False
                self.shared_xle_manager = None
                
                # Set up permanent storage structure for fallback
                if db_name:
                    self.import_folder = xle_import_base / db_name
                else:
                    self.import_folder = xle_import_base
                    
                self.baro_folder = self.import_folder / "barologgers"
                self.transducer_folder = self.import_folder / "transducers"
        else:
            # Local database mode - use permanent storage
            self.use_temp_storage = False
            self.shared_xle_manager = None
            self.project_name = db_name
            
            # Create base import folder with database name if provided
            if db_name:
                logger.debug(f"DEBUG: Creating import folder with db_name: {xle_import_base} / {db_name}")
                self.import_folder = xle_import_base / db_name
            else:
                logger.debug(f"DEBUG: No db_name, using base import folder: {xle_import_base}")
                self.import_folder = xle_import_base
                
            self.baro_folder = self.import_folder / "barologgers"
            self.transducer_folder = self.import_folder / "transducers"
            
            logger.info(f"XLE file organizer initialized for local database with import folder: {self.import_folder}")
        
        # Create directory structure if it doesn't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure the directory structure exists"""
        try:
            # Only create directories if we're using permanent storage
            if hasattr(self, 'import_folder') and not self.use_temp_storage:
                self.import_folder.mkdir(parents=True, exist_ok=True)
                self.baro_folder.mkdir(parents=True, exist_ok=True)
                self.transducer_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"Directory structure ensured at {self.import_folder}")
            else:
                logger.debug("Skipping directory creation for temp storage mode")
        except Exception as e:
            logger.error(f"Error creating directory structure: {e}")
    
    def _format_date(self, dt: datetime) -> str:
        """Format date as year_month_day"""
        return dt.strftime("%Y_%m_%d")
    
    def _format_filename(self, serial_number: str, location: str, start_date: datetime, end_date: datetime) -> str:
        """
        Format the filename according to the standardized pattern: {serial}_{location}_{dates}
        This matches the IntelligentFilenameGenerator format for consistency across the app
        """
        # Format dates
        start_formatted = self._format_date(start_date)
        
        # Same year optimization
        if start_date.year == end_date.year:
            end_formatted = end_date.strftime('%m_%d')
            filename = f"{serial_number}_{location}_{start_formatted}_To_{end_formatted}"
        else:
            end_formatted = self._format_date(end_date)
            filename = f"{serial_number}_{location}_{start_formatted}_To_{end_formatted}"
        
        # Replace any invalid filename characters
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            filename = filename.replace(char, '_')
        
        return filename
    
    def organize_barologger_file(self, original_file: Path, serial_number: str, 
                              location: str, start_date: datetime, end_date: datetime) -> Path:
        """
        Copy and organize a barologger file to the appropriate folder structure
        
        Args:
            original_file: Original XLE file path
            serial_number: Barologger serial number
            location: Location description
            start_date: Start date of the data
            end_date: End date of the data
            
        Returns:
            Path to the organized file
        """
        if self.use_temp_storage and self.shared_xle_manager:
            return self._organize_shared_database_file(
                original_file, 'barologger', serial_number, location, 
                start_date, end_date, None
            )
        else:
            return self._organize_local_database_file(
                original_file, 'barologger', serial_number, location,
                start_date, end_date, None
            )
            
    def organize_transducer_file(self, original_file: Path, serial_number: str, 
                               location: str, start_date: datetime, end_date: datetime,
                               well_number: str = None) -> Path:
        """
        Copy and organize a transducer file
        
        Args:
            original_file: Original XLE file path
            serial_number: Transducer serial number
            location: Location description
            start_date: Start date of the data
            end_date: End date of the data
            well_number: Well number for organization
            
        Returns:
            Path to the organized file
        """
        if self.use_temp_storage and self.shared_xle_manager:
            return self._organize_shared_database_file(
                original_file, 'transducer', serial_number, location,
                start_date, end_date, well_number
            )
        else:
            return self._organize_local_database_file(
                original_file, 'transducer', serial_number, location,
                start_date, end_date, well_number
            )
    
    def _organize_shared_database_file(self, original_file: Path, device_type: str, 
                                     serial_number: str, location: str,
                                     start_date: datetime, end_date: datetime,
                                     well_number: str = None) -> Path:
        """
        Organize XLE file for shared database (temp storage during draft phase)
        
        Args:
            original_file: Original XLE file path
            device_type: 'barologger' or 'transducer'
            serial_number: Device serial number
            location: Location description
            start_date: Start date of data
            end_date: End date of data
            well_number: Well number for transducers
            
        Returns:
            Path to temp stored file
        """
        try:
            logger.info(f"Organizing shared database {device_type} file: {original_file}")
            logger.info(f"Project: {self.project_name}, Serial: {serial_number}, Location: {location}")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Store file in temp location using SharedDatabaseXLEManager
            temp_path = self.shared_xle_manager.store_temp_xle(
                str(original_file), self.project_name, device_type,
                serial_number, location, start_date, end_date, well_number
            )
            
            logger.info(f"Shared database file stored in temp location: {temp_path}")
            return Path(temp_path)
            
        except Exception as e:
            logger.error(f"Error organizing shared database {device_type} file: {e}", exc_info=True)
            return None
    
    def _organize_local_database_file(self, original_file: Path, device_type: str,
                                    serial_number: str, location: str,
                                    start_date: datetime, end_date: datetime,
                                    well_number: str = None) -> Path:
        """
        Organize XLE file for local database (permanent storage)
        
        Args:
            original_file: Original XLE file path
            device_type: 'barologger' or 'transducer'
            serial_number: Device serial number
            location: Location description
            start_date: Start date of data
            end_date: End date of data
            well_number: Well number for transducers
            
        Returns:
            Path to organized file
        """
        try:
            logger.info(f"Organizing local database {device_type} file: {original_file}")
            logger.info(f"Serial: {serial_number}, Location: {location}")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Determine target folder
            if device_type == 'barologger':
                target_folder = self.baro_folder / serial_number
            else:  # transducer
                folder_key = well_number if well_number else serial_number
                target_folder = self.transducer_folder / folder_key
            
            # Create folder if it doesn't exist
            target_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created/verified folder: {target_folder}")
            
            # Generate new filename
            new_filename = f"{self._format_filename(serial_number, location, start_date, end_date)}.xle"
            new_file_path = target_folder / new_filename
            logger.info(f"New file path will be: {new_file_path}")
            
            # Check if file with same date range already exists
            for existing_file in target_folder.glob("*.xle"):
                # Extract date range from filename
                if location in existing_file.stem:
                    existing_parts = existing_file.stem.split('_')
                    if len(existing_parts) >= 5:  # Enough parts for a date range
                        try:
                            # Get indices where "To" appears
                            to_indices = [i for i, part in enumerate(existing_parts) if part == "To"]
                            if to_indices:
                                to_index = to_indices[0]
                                # Extract dates around the "To"
                                existing_start_date_parts = existing_parts[to_index-3:to_index]
                                
                                # If dates match, we'll replace the file
                                if f"{'_'.join(existing_start_date_parts)}" == self._format_date(start_date):
                                    logger.info(f"Found existing file with same date range: {existing_file}")
                                    # Remove the old file
                                    existing_file.unlink()
                                    logger.info(f"Deleted existing file: {existing_file}")
                        except Exception as e:
                            logger.warning(f"Error comparing dates in filename {existing_file}: {e}")
            
            # Copy the file
            logger.info(f"Copying from {original_file} to {new_file_path}")
            shutil.copy2(original_file, new_file_path)
            logger.info(f"File successfully copied to {new_file_path}")
            
            return new_file_path
            
        except Exception as e:
            logger.error(f"Error organizing local database {device_type} file: {e}", exc_info=True)
            return None
