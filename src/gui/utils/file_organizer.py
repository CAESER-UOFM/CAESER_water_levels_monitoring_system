import logging
import shutil
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class XLEFileOrganizer:
    """Organizes imported XLE files into appropriate folders"""
    
    def __init__(self, app_root_dir: Path, db_name: str = None):
        """Initialize the file organizer with the application root directory"""
        self.app_root_dir = app_root_dir
        self.db_name = db_name
        
        # Create base import folder with database name if provided
        if db_name:
            self.import_folder = app_root_dir / "imported_xle_files" / db_name
        else:
            self.import_folder = app_root_dir / "imported_xle_files"
            
        self.baro_folder = self.import_folder / "barologgers"
        self.transducer_folder = self.import_folder / "transducers"
        
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
        Copy and organize a transducer file to the appropriate folder structure.
        Files are organized by well number instead of serial number.
        
        Args:
            original_file: Original XLE file path
            serial_number: Transducer serial number
            location: Location description
            start_date: Start date of the data
            end_date: End date of the data
            well_number: Well number (used for folder organization)
            
        Returns:
            Path to the organized file
        """
        try:
            # Use well_number for the folder name if provided, otherwise fall back to serial_number
            folder_key = well_number if well_number else serial_number
            
            logger.info(f"Organizing transducer file: {original_file}")
            logger.info(f"Serial: {serial_number}, Location: {location}, Well: {folder_key}")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Create well number subfolder if it doesn't exist
            well_folder = self.transducer_folder / folder_key
            well_folder.mkdir(exist_ok=True)
            logger.info(f"Created/verified well folder: {well_folder}")
            
            # Generate new filename - include serial number in filename for reference
            filename_prefix = f"{serial_number}_{location}"
            
            # Fix for double underscore issue - format dates directly instead of using _format_filename with empty location
            if start_date.year == end_date.year:
                date_part = f"{self._format_date(start_date)}_To_{end_date.strftime('%m_%d')}"
            else:
                date_part = f"{self._format_date(start_date)}_To_{self._format_date(end_date)}"
                
            new_filename = f"{filename_prefix}_{date_part}.xle"
            new_file_path = well_folder / new_filename
            logger.info(f"New file path will be: {new_file_path}")
            
            # Check if original file exists
            if not original_file.exists():
                logger.error(f"Original file does not exist: {original_file}")
                return None
                
            # Check for existing files with same date range
            for existing_file in well_folder.glob("*.xle"):
                if serial_number in existing_file.stem and location in existing_file.stem:
                    existing_parts = existing_file.stem.split('_')
                    if len(existing_parts) >= 5:
                        try:
                            to_indices = [i for i, part in enumerate(existing_parts) if part == "To"]
                            if to_indices:
                                to_index = to_indices[0]
                                existing_start_date_parts = existing_parts[to_index-3:to_index]
                                
                                if f"{'_'.join(existing_start_date_parts)}" == self._format_date(start_date):
                                    logger.info(f"Found existing file with same date range: {existing_file}")
                                    existing_file.unlink()
                                    logger.info(f"Deleted existing file: {existing_file}")
                        except Exception as e:
                            logger.warning(f"Error comparing dates in filename {existing_file}: {e}")
            
            # Copy the file - add explicit copy logging
            logger.info(f"Copying from {original_file} to {new_file_path}")
            shutil.copy2(original_file, new_file_path)
            
            # Verify the copy succeeded
            if new_file_path.exists():
                logger.info(f"File successfully copied to {new_file_path}")
                return new_file_path
            else:
                logger.error(f"Copy operation failed - destination file not found: {new_file_path}")
                return None
        
        except Exception as e:
            logger.error(f"Error organizing transducer file: {e}", exc_info=True)
            return None
