import logging
import shutil
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class XLEFileOrganizer:
    """Organizes imported XLE files into appropriate folders"""
    
    def __init__(self, app_root_dir: Path = None, db_name: str = None, settings_handler=None):
        """
        Initialize the file organizer.
        
        Args:
            app_root_dir: Deprecated - will be ignored in favor of settings_handler
            db_name: Database/project name for organizing files
            settings_handler: Settings handler to get XLE import directory
        """
        # Get XLE import directory from settings, fallback to old behavior if not available
        if settings_handler:
            # Use app directory instead of current working directory as fallback
            app_dir = Path(__file__).parent.parent.parent.parent
            xle_import_base = Path(settings_handler.get_setting("xle_import_directory", str(app_dir / "imported_xle_files")))
            logger.debug(f"DEBUG: XLEFileOrganizer using settings xle_import_base: {xle_import_base}")
        else:
            # Fallback to app directory instead of current working directory
            app_dir = Path(__file__).parent.parent.parent.parent
            xle_import_base = app_dir / "imported_xle_files"
            logger.warning(f"DEBUG: XLEFileOrganizer no settings_handler, using app_dir fallback: {xle_import_base}")
            if app_root_dir:
                logger.warning("XLEFileOrganizer: app_root_dir parameter is deprecated, use settings_handler instead")
                xle_import_base = app_root_dir / "imported_xle_files"
        
        self.db_name = db_name
        logger.debug(f"DEBUG: XLEFileOrganizer db_name: {repr(db_name)}")
        
        # Create base import folder with database name if provided
        if db_name:
            logger.debug(f"DEBUG: Creating import folder with db_name: {xle_import_base} / {db_name}")
            self.import_folder = xle_import_base / db_name
        else:
            logger.debug(f"DEBUG: No db_name, using base import folder: {xle_import_base}")
            self.import_folder = xle_import_base
            
        self.baro_folder = self.import_folder / "barologgers"
        self.transducer_folder = self.import_folder / "transducers"
        
        logger.info(f"XLE file organizer initialized with import folder: {self.import_folder}")
        
        # Create directory structure if it doesn't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure the directory structure exists"""
        try:
            self.import_folder.mkdir(parents=True, exist_ok=True)
            self.baro_folder.mkdir(parents=True, exist_ok=True)
            self.transducer_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory structure ensured at {self.import_folder}")
        except Exception as e:
            logger.error(f"Error creating directory structure: {e}")
    
    def _format_date(self, dt: datetime) -> str:
        """Format date as year_month_day"""
        return dt.strftime("%Y_%m_%d")
    
    def _format_filename(self, location: str, start_date: datetime, end_date: datetime) -> str:
        """Format the filename according to the specified pattern"""
        # If same year, only include year once
        if start_date.year == end_date.year:
            filename = f"{location}_{self._format_date(start_date)}_To_{end_date.strftime('%m_%d')}"
        else:
            filename = f"{location}_{self._format_date(start_date)}_To_{self._format_date(end_date)}"
        
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
        try:
            logger.info(f"Organizing file: {original_file}")
            logger.info(f"Serial: {serial_number}, Location: {location}")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Create serial number subfolder if it doesn't exist
            serial_folder = self.baro_folder / serial_number
            serial_folder.mkdir(exist_ok=True)
            logger.info(f"Created/verified serial folder: {serial_folder}")
            
            # Generate new filename
            new_filename = f"{self._format_filename(location, start_date, end_date)}.xle"
            new_file_path = serial_folder / new_filename
            logger.info(f"New file path will be: {new_file_path}")
            
            # Check if file with same date range already exists
            for existing_file in serial_folder.glob("*.xle"):
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
            logger.error(f"Error organizing barologger file: {e}", exc_info=True)
            return None
            
    def organize_transducer_file(self, original_file: Path, serial_number: str, 
                               location: str, start_date: datetime, end_date: datetime,
                               well_number: str = None) -> Path:
        """
        Copy and organize a transducer file - EXACT copy of working barologger logic
        """
        try:
            logger.info(f"Organizing file: {original_file}")
            logger.info(f"Serial: {serial_number}, Location: {location}")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Use well_number for folder if provided, otherwise serial_number
            folder_key = well_number if well_number else serial_number
            
            # Create subfolder if it doesn't exist
            target_folder = self.transducer_folder / folder_key
            target_folder.mkdir(exist_ok=True)
            logger.info(f"Created/verified folder: {target_folder}")
            
            # Generate new filename - EXACT same pattern as barologgers
            new_filename = f"{self._format_filename(location, start_date, end_date)}.xle"
            new_file_path = target_folder / new_filename
            logger.info(f"New file path will be: {new_file_path}")
            
            # Check if file with same date range already exists - EXACT same pattern as barologgers
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
            
            # Copy the file - EXACT same pattern as barologgers
            logger.info(f"Copying from {original_file} to {new_file_path}")
            shutil.copy2(original_file, new_file_path)
            logger.info(f"File successfully copied to {new_file_path}")
            
            return new_file_path
        
        except Exception as e:
            logger.error(f"Error organizing transducer file: {e}", exc_info=True)
            return None
