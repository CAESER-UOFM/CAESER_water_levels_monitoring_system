# -*- coding: utf-8 -*-
"""
SMOO Folder Scanner for Water Level Monitoring System

Replaces Google Drive API scanning with direct SMOO file system scanning
for consolidated field data folder structure.

This scanner provides the same interface as RunsFolderMonitor but operates
on SMOO file system instead of Google Drive API calls.

@author: Created for SMOO migration
"""

import os
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ...config.smoo_paths import get_smoo_path

logger = logging.getLogger(__name__)

class SMOOFolderScanner:
    """Scans SMOO FIELD_DATA_CONSOLIDATED folder structure for XLE files"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SMOO folder scanner
        
        Args:
            db_path: Database path for tracking readings (optional)
        """
        self.db_path = db_path
        self.latest_readings = {}
        
        # Get SMOO consolidated folder path
        self.consolidated_path = get_smoo_path("field_data")
        if not self.consolidated_path:
            logger.error("SMOO field data path not available")
            raise ValueError("SMOO field data path not accessible")
        
        self.consolidated_path = Path(self.consolidated_path)
        logger.info(f"SMOOFolderScanner initialized with path: {self.consolidated_path}")
        
        # Validate SMOO access
        if not self.consolidated_path.exists():
            logger.error(f"SMOO consolidated folder does not exist: {self.consolidated_path}")
            raise FileNotFoundError(f"SMOO consolidated folder not found: {self.consolidated_path}")
        
        logger.info(f"SMOOFolderScanner ready - scanning {self.consolidated_path}")
    
    def get_month_folders(self, year_month: str) -> Dict[str, str]:
        """
        Get folders for current and next month
        
        Args:
            year_month: Month in YYYY-MM format (e.g., "2025-02")
            
        Returns:
            dict: {month_name: folder_path} mapping
        """
        folders = {}
        
        try:
            # Parse current month
            year = int(year_month[:4])
            month = int(year_month[5:7])
            
            # Calculate next month
            if month == 12:
                next_month = f"{year + 1}-01"
            else:
                next_month = f"{year}-{month + 1:02d}"
            
            # Check for both current and next month folders
            for month_name in [year_month, next_month]:
                month_folder = self.consolidated_path / month_name
                if month_folder.exists() and month_folder.is_dir():
                    folders[month_name] = str(month_folder)
                    logger.debug(f"Found month folder: {month_name} at {month_folder}")
                else:
                    logger.debug(f"Month folder not found: {month_name}")
            
            logger.info(f"Found {len(folders)} month folders for {year_month}: {list(folders.keys())}")
            return folders
            
        except Exception as e:
            logger.error(f"Error getting month folders for {year_month}: {e}")
            return {}
    
    def scan_xle_files(self, folder_path: str) -> Dict[str, Dict]:
        """
        Scan metadata.json in folder and return dict mapping CAE -> latest reading data
        
        Args:
            folder_path: Path to month folder to scan
            
        Returns:
            dict: {cae_number: {'date': datetime, 'filename': str, 'file_path': str}} mapping
        """
        readings = {}
        
        try:
            folder = Path(folder_path)
            if not folder.exists():
                logger.warning(f"Folder does not exist: {folder_path}")
                return readings
            
            # Look for metadata.json in the folder
            metadata_file = folder / "metadata.json"
            if not metadata_file.exists():
                logger.debug(f"No metadata.json found in {folder_path}")
                return readings
            
            logger.debug(f"Reading metadata.json from {folder_path}")
            
            # Read and parse metadata.json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            files = metadata.get('files', [])
            logger.debug(f"Found {len(files)} files in metadata.json")
            
            for file_info in files:
                try:
                    cae_number = file_info.get('cae_number')
                    filename = file_info.get('filename')
                    actual_end_date_str = file_info.get('actual_end_date')
                    
                    if not cae_number or not filename or not actual_end_date_str:
                        logger.debug(f"Skipping file with missing metadata: {filename}")
                        continue
                    
                    # Parse the actual_end_date
                    try:
                        # Handle different date formats
                        if 'T' in actual_end_date_str:
                            actual_end_date = datetime.fromisoformat(actual_end_date_str.replace('Z', '+00:00'))
                        else:
                            actual_end_date = datetime.fromisoformat(actual_end_date_str)
                    except ValueError as e:
                        logger.warning(f"Could not parse date {actual_end_date_str} for {filename}: {e}")
                        continue
                    
                    # Construct full file path with fallback for filename mismatches
                    file_path = self._find_actual_file_path(folder, filename, cae_number)
                    
                    # Skip if file doesn't exist
                    if not file_path or not Path(file_path).exists():
                        logger.warning(f"File not found for {cae_number}: tried {filename}")
                        continue
                    
                    # Keep the latest reading for each CAE
                    if cae_number not in readings or actual_end_date > readings[cae_number]['date']:
                        readings[cae_number] = {
                            'date': actual_end_date,
                            'filename': filename,
                            'file_path': str(file_path)
                        }
                        logger.debug(f"Updated latest reading for {cae_number}: {actual_end_date} ({filename})")
                    
                except Exception as file_error:
                    logger.warning(f"Error processing metadata entry {file_info}: {file_error}")
                    continue
            
            logger.info(f"Scanned metadata in {folder_path}: found {len(readings)} unique CAE locations")
            return readings
            
        except Exception as e:
            logger.error(f"Error reading metadata.json in {folder_path}: {e}")
            return {}
    
    def _find_actual_file_path(self, folder: Path, metadata_filename: str, cae_number: str) -> str:
        """
        Find the actual file path, handling filename mismatches between metadata.json and actual files.
        
        Common mismatches:
        - metadata: HAA012_2025_06_23_To_2025_07_29.xle
        - actual:   HAA-012_2025_06_23_To_2025_07_29.xle (with hyphen)
        
        Args:
            folder: Path to the folder containing the files
            metadata_filename: Filename from metadata.json
            cae_number: CAE number for debugging
            
        Returns:
            str: Path to the actual file, or None if not found
        """
        # Try the exact filename from metadata first
        file_path = folder / metadata_filename
        if file_path.exists():
            return str(file_path)
        
        # Extract CAE number from filename to generate alternatives
        # metadata_filename format: HAA012_2025_06_23_To_2025_07_29.xle
        filename_parts = metadata_filename.split('_')
        if len(filename_parts) >= 2:
            original_cae_part = filename_parts[0]  # e.g., "HAA012"
            
            # Generate alternative CAE formats
            alternatives = []
            
            # If original doesn't have hyphen, try adding one after 3rd character
            if '-' not in original_cae_part and len(original_cae_part) >= 6:
                # HAA012 -> HAA-012
                alt_cae = original_cae_part[:3] + '-' + original_cae_part[3:]
                alternatives.append(alt_cae)
            
            # If original has hyphen, try removing it
            if '-' in original_cae_part:
                # HAA-012 -> HAA012
                alt_cae = original_cae_part.replace('-', '')
                alternatives.append(alt_cae)
            
            # Try each alternative filename
            for alt_cae in alternatives:
                alt_filename = metadata_filename.replace(original_cae_part, alt_cae)
                alt_file_path = folder / alt_filename
                if alt_file_path.exists():
                    logger.debug(f"Found file with alternative name: {alt_filename} (original: {metadata_filename})")
                    return str(alt_file_path)
        
        # If no alternatives work, log all files in folder for debugging
        try:
            existing_files = [f.name for f in folder.iterdir() if f.is_file() and f.name.endswith('.xle')]
            logger.warning(f"File not found for {cae_number}. Tried: {metadata_filename}. Available files: {existing_files}")
        except Exception as e:
            logger.warning(f"Could not list files in {folder}: {e}")
        
        return None
    
    def scan_barologger_files(self, folder_path: str) -> Dict[str, Dict]:
        """
        Scan metadata.json in folder and return dict mapping serial_number -> latest reading data
        Same as scan_xle_files but returns by serial_number instead of cae_number
        
        Args:
            folder_path: Path to month folder to scan
            
        Returns:
            dict: {serial_number: {'date': datetime, 'filename': str, 'file_path': str}} mapping
        """
        readings = {}
        
        try:
            folder = Path(folder_path)
            if not folder.exists():
                logger.warning(f"Folder does not exist: {folder_path}")
                return readings
            
            # Look for metadata.json in the folder
            metadata_file = folder / "metadata.json"
            if not metadata_file.exists():
                logger.debug(f"No metadata.json found in {folder_path}")
                return readings
            
            logger.debug(f"Reading metadata.json from {folder_path}")
            
            # Read and parse metadata.json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            files = metadata.get('files', [])
            logger.debug(f"Found {len(files)} files in metadata.json")
            
            for file_info in files:
                try:
                    serial_number = file_info.get('serial_number')
                    filename = file_info.get('filename')
                    actual_end_date_str = file_info.get('actual_end_date')
                    
                    if not serial_number or not filename or not actual_end_date_str:
                        logger.debug(f"Skipping file with missing barologger metadata: {filename}")
                        continue
                    
                    # Parse the actual_end_date
                    try:
                        # Handle different date formats
                        if 'T' in actual_end_date_str:
                            actual_end_date = datetime.fromisoformat(actual_end_date_str.replace('Z', '+00:00'))
                        else:
                            actual_end_date = datetime.fromisoformat(actual_end_date_str)
                    except ValueError as e:
                        logger.warning(f"Could not parse date {actual_end_date_str} for {filename}: {e}")
                        continue
                    
                    # Construct full file path with fallback for filename mismatches
                    file_path = self._find_actual_file_path(folder, filename, serial_number)
                    
                    # Skip if file doesn't exist
                    if not file_path or not Path(file_path).exists():
                        logger.warning(f"File not found for serial {serial_number}: tried {filename}")
                        continue
                    
                    # Keep the latest reading for each serial number
                    if serial_number not in readings or actual_end_date > readings[serial_number]['date']:
                        readings[serial_number] = {
                            'date': actual_end_date,
                            'filename': filename,
                            'file_path': str(file_path)
                        }
                        logger.debug(f"Updated latest reading for serial {serial_number}: {actual_end_date} ({filename})")
                    
                except Exception as file_error:
                    logger.warning(f"Error processing barologger metadata entry {file_info}: {file_error}")
                    continue
            
            logger.info(f"Scanned barologger metadata in {folder_path}: found {len(readings)} unique serial numbers")
            return readings
            
        except Exception as e:
            logger.error(f"Error reading barologger metadata.json in {folder_path}: {e}")
            return {}
    
    def extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """
        Extract the end date from an XLE filename.
        
        Handles multiple formats:
        - Standard: J140_2022_12_3_To_2023_01_02.xle
        - Abbreviated: J140_2022_12_3_To_12_22.xle
        - Timestamp: _Weather Station_2025_04_30_100000_2025_05_28_101736.xle
        
        Returns:
            datetime object representing the end date or None if extraction fails
        """
        try:
            # First try the standard format with '_To_'
            if '_To_' in filename:
                # Get the parts before and after '_To_'
                start_part, end_part = filename.split('_To_')
                # Remove file extension from end part
                end_part = end_part.split('.')[0]
                
                # Try to parse the end date
                end_date_parts = end_part.split('_')
                
                # Handle abbreviated format (year only has 2 digits)
                if len(end_date_parts) >= 3:
                    year = int(end_date_parts[0])
                    month = int(end_date_parts[1])
                    day = int(end_date_parts[2])
                    
                    # Handle 2-digit years (assume 20xx)
                    if year < 100:
                        year += 2000
                    
                    return datetime(year, month, day)
                    
            else:
                # Handle timestamp format: split by underscores and look for date pattern
                parts = filename.split('_')
                
                # Look for YYYY_MM_DD pattern
                for i in range(len(parts) - 2):
                    try:
                        year = int(parts[i])
                        month = int(parts[i + 1])
                        day = int(parts[i + 2])
                        
                        # Validate ranges
                        if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                            # This might be a date, check if there's a later date in the filename
                            # (for timestamp format, we want the end date)
                            potential_date = datetime(year, month, day)
                            
                            # Continue looking for a later date
                            for j in range(i + 3, len(parts) - 2):
                                try:
                                    year2 = int(parts[j])
                                    month2 = int(parts[j + 1])  
                                    day2 = int(parts[j + 2])
                                    
                                    if 2020 <= year2 <= 2030 and 1 <= month2 <= 12 and 1 <= day2 <= 31:
                                        later_date = datetime(year2, month2, day2)
                                        if later_date > potential_date:
                                            potential_date = later_date
                                except (ValueError, IndexError):
                                    continue
                            
                            return potential_date
                            
                    except (ValueError, IndexError):
                        continue
                        
        except Exception as e:
            logger.debug(f"Could not extract date from filename '{filename}': {e}")
            
        return None
    
    def get_latest_readings(self) -> Dict[str, Dict]:
        """
        Get latest readings for all locations across all available months
        
        Returns:
            dict: {location: {'date': datetime, 'filename': str}} mapping
        """
        all_readings = {}
        
        try:
            # Get all month folders in consolidated directory
            month_folders = self.get_all_available_month_folders()
            
            for month_name, folder_path in month_folders.items():
                logger.debug(f"Scanning month folder: {month_name}")
                
                # Get readings from this month folder
                month_readings = self.scan_xle_files(folder_path)
                
                # Update overall readings with latest data
                for location, data in month_readings.items():
                    if location not in all_readings or data['date'] > all_readings[location]['date']:
                        all_readings[location] = data
            
            logger.info(f"Found latest readings for {len(all_readings)} locations")
            return all_readings
            
        except Exception as e:
            logger.error(f"Error getting latest readings: {e}")
            return {}
    
    def get_all_available_month_folders(self) -> Dict[str, str]:
        """
        Get all available month folders in the consolidated folder
        
        Returns:
            dict: {month_name: folder_path} mapping
        """
        month_folders = {}
        
        try:
            if not self.consolidated_path.exists():
                logger.warning(f"Consolidated path does not exist: {self.consolidated_path}")
                return month_folders
            
            # Scan for directories that match YYYY-MM pattern
            for item in self.consolidated_path.iterdir():
                if item.is_dir():
                    folder_name = item.name
                    
                    # Check if folder name matches YYYY-MM pattern
                    if self._is_valid_month_folder(folder_name):
                        month_folders[folder_name] = str(item)
                        logger.debug(f"Found month folder: {folder_name}")
            
            logger.info(f"Found {len(month_folders)} month folders in consolidated directory")
            return month_folders
            
        except Exception as e:
            logger.error(f"Error getting all month folders: {e}")
            return {}
    
    def _is_valid_month_folder(self, folder_name: str) -> bool:
        """
        Check if folder name matches YYYY-MM pattern
        
        Args:
            folder_name: Name of folder to check
            
        Returns:
            bool: True if valid month folder format
        """
        try:
            parts = folder_name.split('-')
            if len(parts) != 2:
                return False
            
            year = int(parts[0])
            month = int(parts[1])
            
            # Validate ranges
            return 2020 <= year <= 2030 and 1 <= month <= 12
            
        except (ValueError, IndexError):
            return False
    
    def get_metadata_file_content(self, folder_path: str, metadata_filename: str) -> Optional[Dict]:
        """
        Get content of metadata.json file in a folder
        
        Args:
            folder_path: Path to folder containing metadata file
            metadata_filename: Name of metadata file (usually "metadata.json")
            
        Returns:
            dict: Metadata content or None if not found/invalid
        """
        try:
            metadata_path = Path(folder_path) / metadata_filename
            
            if not metadata_path.exists():
                logger.debug(f"Metadata file not found: {metadata_path}")
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            logger.debug(f"Loaded metadata from {metadata_path}")
            return metadata
            
        except Exception as e:
            logger.warning(f"Error reading metadata file {metadata_path}: {e}")
            return None
    
    def process_files(self, files_list: List[str], db_path: Optional[str] = None) -> List[str]:
        """
        Process a list of files to extract locations and readings
        Compatible interface with RunsFolderMonitor
        
        Args:
            files_list: List of file paths to process
            db_path: Database path (optional)
            
        Returns:
            list: Processed file locations
        """
        if db_path:
            self.db_path = db_path
            
        self.latest_readings = {}
        locations = []
        
        for file_path in files_list:
            try:
                filename = Path(file_path).name
                location = self.extract_location_from_filename(filename)
                date = self.extract_date_from_filename(filename)
                
                if location:
                    locations.append(location)
                    if date and (location not in self.latest_readings or date > self.latest_readings[location]['date']):
                        self.latest_readings[location] = {
                            'date': date,
                            'filename': filename,
                            'file_path': file_path
                        }
                        
            except Exception as e:
                logger.warning(f"Error processing file {file_path}: {e}")
                continue
        
        return locations
    
    def extract_location_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract location identifier from filename
        
        Args:
            filename: Name of file to process
            
        Returns:
            str: Location identifier or None if extraction fails
        """
        try:
            # Location is typically the first part before underscore
            return filename.split('_')[0]
        except (IndexError, AttributeError):
            return None