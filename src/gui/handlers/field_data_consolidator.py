# -*- coding: utf-8 -*-
"""
Hybrid Field Data Consolidator for Water Level Monitoring System

Handles consolidation of field data from Google Drive SOLINST folder 
to SMOO FIELD_DATA_CONSOLIDATED folder structure.

Google Drive SOLINST (source) → SMOO FIELD_DATA_CONSOLIDATED (target)

@author: Created for Google Drive → SMOO transition
"""

import os
import shutil
import logging
import tempfile
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Callable, Tuple
from googleapiclient.http import MediaIoBaseDownload
from ...config.paths import DefaultPaths

logger = logging.getLogger(__name__)

class HybridFieldDataConsolidator:
    """Handles field data consolidation from Google Drive to SMOO"""
    
    def __init__(self, drive_service, settings_handler):
        """
        Initialize hybrid field data consolidator
        
        Args:
            drive_service: Google Drive service instance
            settings_handler: Settings handler instance
        """
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        
        # Google Drive source (SOLINST folder)
        self.solinst_folder_id = self.settings_handler.get_setting("google_drive_solinst_folder_id", "")
        
        # SMOO target (FIELD_DATA_CONSOLIDATED)
        self.smoo_root = self.settings_handler.get_setting("shared_drive_root", DefaultPaths.SHARED_DRIVE_BASE)
        self.consolidated_folder = os.path.join(self.smoo_root, "FIELD_DATA_CONSOLIDATED")
        
        logger.info(f"Hybrid Consolidator initialized:")
        logger.info(f"  Google Drive SOLINST ID: {self.solinst_folder_id}")
        logger.info(f"  SMOO Consolidated: {self.consolidated_folder}")
    
    def check_access(self) -> bool:
        """Check if both Google Drive and SMOO are accessible"""
        try:
            # Check Google Drive service
            if not self.drive_service.service:
                logger.error("Google Drive service not available")
                return False
            
            # Check SOLINST folder ID
            if not self.solinst_folder_id:
                logger.error("SOLINST folder ID not configured")
                return False
            
            # Check SMOO access
            if not os.path.exists(self.smoo_root):
                logger.error(f"SMOO root path not accessible: {self.smoo_root}")
                return False
            
            # Create consolidated folder if needed
            if not os.path.exists(self.consolidated_folder):
                os.makedirs(self.consolidated_folder, exist_ok=True)
                logger.info(f"Created consolidated folder: {self.consolidated_folder}")
            
            # Test SMOO write permissions
            test_file = os.path.join(self.smoo_root, f"test_access_{int(datetime.now().timestamp())}.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.debug("SMOO write access confirmed")
                return True
            except Exception as e:
                logger.error(f"No write access to SMOO: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return False
    
    def scan_google_drive_solinst(self) -> List[Dict]:
        """
        Scan Google Drive SOLINST folder for new XLE files using service account handler
        
        Returns:
            List of file info dictionaries
        """
        try:
            # Set the SOLINST folder ID if not set
            if self.solinst_folder_id:
                self.drive_service.set_solinst_folder_id(self.solinst_folder_id)
            
            # Use the service account handler's built-in method
            files_found = self.drive_service.list_xle_files()
            
            # Convert to format expected by consolidator
            consolidated_files = []
            for file_info in files_found:
                consolidated_file = {
                    'id': file_info['id'],
                    'name': file_info['name'], 
                    'size': int(file_info.get('size', 0)),
                    'modified_time': file_info['modifiedTime']
                }
                consolidated_files.append(consolidated_file)
                logger.debug(f"Found Google Drive XLE: {file_info['name']} (Modified: {file_info['modifiedTime']})")
            
            logger.info(f"Found {len(consolidated_files)} XLE files in Google Drive SOLINST")
            return consolidated_files
            
        except Exception as e:
            logger.error(f"Error scanning Google Drive SOLINST: {e}")
            return []
    
    def extract_xle_metadata(self, file_path: str) -> Dict:
        """
        Extract basic metadata from XLE file for organization
        
        Args:
            file_path: Path to XLE file
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'serial_number': 'unknown',
            'location': 'unknown',  
            'start_date': None,
            'end_date': None,
            'instrument_type': 'unknown'
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)  # Read first 1KB for metadata
                
                # Extract serial number
                if 'Serial_number=' in content:
                    serial_line = [line for line in content.split('\n') if 'Serial_number=' in line]
                    if serial_line:
                        metadata['serial_number'] = serial_line[0].split('=')[-1].strip()
                
                # Extract location
                if 'Location=' in content:
                    location_line = [line for line in content.split('\n') if 'Location=' in line]
                    if location_line:
                        metadata['location'] = location_line[0].split('=')[-1].strip()
                
                # Determine instrument type from filename or content
                filename = os.path.basename(file_path).lower()
                if any(keyword in filename for keyword in ['baro', 'bar']):
                    metadata['instrument_type'] = 'barologger'
                elif any(keyword in filename for keyword in ['level', 'lev', 'wl']):
                    metadata['instrument_type'] = 'levellogger'
                else:
                    metadata['instrument_type'] = 'levellogger'  # Default
        
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
        
        return metadata
    
    def organize_file_by_date(self, file_path: str, metadata: Dict) -> str:
        """
        Determine target folder for file based on date and metadata
        
        Args:
            file_path: Source file path
            metadata: Extracted metadata
            
        Returns:
            Target folder path in consolidated structure
        """
        try:
            # Get file modification date as fallback
            file_stat = os.stat(file_path)
            file_date = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Create folder structure: FIELD_DATA_CONSOLIDATED/YYYY-MM/
            year_month = file_date.strftime("%Y-%m")
            target_folder = os.path.join(self.consolidated_folder, year_month)
            
            # Ensure target folder exists
            os.makedirs(target_folder, exist_ok=True)
            
            logger.debug(f"Target folder for {os.path.basename(file_path)}: {target_folder}")
            return target_folder
            
        except Exception as e:
            logger.error(f"Error determining target folder: {e}")
            # Fallback to current month
            current_month = datetime.now().strftime("%Y-%m")
            fallback_folder = os.path.join(self.consolidated_folder, current_month)
            os.makedirs(fallback_folder, exist_ok=True)
            return fallback_folder
    
    def consolidate_file(self, file_info: Dict, progress_callback: Optional[Callable] = None) -> bool:
        """
        Consolidate a single file from Google Drive SOLINST to SMOO consolidated folder
        
        Args:
            file_info: Google Drive file information dictionary
            progress_callback: Optional progress callback function
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_id = file_info['id']
            filename = file_info['name']
            file_size = file_info['size']
            
            if progress_callback:
                progress_callback(f"Downloading {filename}...", 0)
            
            # Download file from Google Drive to temp location
            service = self.drive_service.service
            request = service.files().get_media(fileId=file_id)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xle') as temp_file:
                downloader = MediaIoBaseDownload(temp_file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if progress_callback and status:
                        progress = int(status.progress() * 50)  # First 50% for download
                        progress_callback(f"Downloading {filename}...", progress)
                
                temp_path = temp_file.name
            
            if progress_callback:
                progress_callback(f"Organizing {filename}...", 50)
            
            # Extract metadata for organization
            metadata = self.extract_xle_metadata(temp_path)
            
            # Determine target folder
            target_folder = self.organize_file_by_date(temp_path, metadata)
            target_path = os.path.join(target_folder, filename)
            
            # Check if file already exists in SMOO target
            if os.path.exists(target_path):
                # Compare file sizes to see if it's the same file
                target_size = os.path.getsize(target_path)
                
                if file_size == target_size:
                    logger.info(f"File already consolidated: {filename}")
                    os.remove(temp_path)  # Clean up temp file
                    if progress_callback:
                        progress_callback(f"Already exists: {filename}", 100)
                    return True
                else:
                    # Create unique name for different file
                    timestamp = datetime.now().strftime("%H%M%S")
                    name, ext = os.path.splitext(filename)
                    target_path = os.path.join(target_folder, f"{name}_{timestamp}{ext}")
            
            if progress_callback:
                progress_callback(f"Saving {filename}...", 75)
            
            # Move file from temp to SMOO target location
            logger.info(f"Consolidating: {filename} -> {os.path.relpath(target_path, self.consolidated_folder)}")
            shutil.move(temp_path, target_path)
            
            if progress_callback:
                progress_callback(f"Consolidated: {filename}", 100)
            
            return True
            
        except Exception as e:
            logger.error(f"Error consolidating file {file_info['name']}: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            if progress_callback:
                progress_callback(f"Error: {file_info['name']}", 100)
            return False
    
    def consolidate_field_data(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Consolidate all field data from Google Drive SOLINST to SMOO organized structure
        
        Args:
            progress_callback: Optional progress callback function (message, percent)
            
        Returns:
            True if consolidation successful, False otherwise
        """
        try:
            logger.info("Starting hybrid field data consolidation (Google Drive → SMOO)...")
            
            if progress_callback:
                progress_callback("Checking access...", 0)
            
            # Check both Google Drive and SMOO access
            if not self.check_access():
                logger.error("Cannot access Google Drive or SMOO")
                if progress_callback:
                    progress_callback("Access check failed", 100)
                return False
            
            if progress_callback:
                progress_callback("Scanning Google Drive SOLINST...", 10)
            
            # Scan Google Drive for files
            files_to_consolidate = self.scan_google_drive_solinst()
            
            if not files_to_consolidate:
                logger.info("No files found to consolidate in Google Drive SOLINST")
                if progress_callback:
                    progress_callback("No files to consolidate", 100)
                return True
            
            logger.info(f"Found {len(files_to_consolidate)} files to consolidate from Google Drive")
            
            # Consolidate each file and track metadata
            successful_count = 0
            total_files = len(files_to_consolidate)
            monthly_metadata = {}  # Track files by month for metadata generation
            
            for i, file_info in enumerate(files_to_consolidate):
                # Calculate progress (10% for scanning, 80% for processing, 10% for metadata)
                base_progress = 10 + int((i / total_files) * 80)
                
                def file_progress_callback(message, percent):
                    if progress_callback:
                        # Map file progress to overall progress
                        file_range = 80 / total_files  # Each file gets this % range
                        overall_progress = base_progress + int((percent / 100) * file_range)
                        progress_callback(message, min(overall_progress, 89))
                
                # Consolidate file and get metadata
                success, file_metadata = self.consolidate_file_with_metadata(file_info, file_progress_callback)
                if success and file_metadata:
                    successful_count += 1
                    
                    # Group by month for metadata.json generation
                    month_key = file_metadata.get('month_folder', 'unknown')
                    if month_key not in monthly_metadata:
                        monthly_metadata[month_key] = {
                            'folder': month_key,
                            'generated_date': datetime.now().isoformat(),
                            'files': []
                        }
                    monthly_metadata[month_key]['files'].append(file_metadata)
            
            # Generate metadata.json files for each month
            if progress_callback:
                progress_callback("Generating metadata files...", 90)
            
            metadata_success = self._generate_metadata_files(monthly_metadata)
            
            logger.info(f"Consolidation complete: {successful_count}/{total_files} files processed successfully")
            if metadata_success:
                logger.info(f"Generated metadata files for {len(monthly_metadata)} month folders")
            
            if progress_callback:
                progress_callback(f"Complete: {successful_count}/{total_files} files consolidated", 100)
            
            return successful_count > 0
            
        except Exception as e:
            logger.error(f"Error during field data consolidation: {e}")
            if progress_callback:
                progress_callback(f"Error: {str(e)}", 100)
            return False
    
    def consolidate_file_with_metadata(self, file_info: Dict, progress_callback: Optional[Callable] = None) -> Tuple[bool, Optional[Dict]]:
        """
        Consolidate a single file and return metadata for metadata.json generation
        
        Args:
            file_info: Google Drive file information dictionary
            progress_callback: Optional progress callback function
            
        Returns:
            Tuple of (success, metadata_dict)
        """
        try:
            file_id = file_info['id']
            filename = file_info['name']
            file_size = file_info['size']
            
            if progress_callback:
                progress_callback(f"Downloading {filename}...", 0)
            
            # Download file from Google Drive to temp location
            service = self.drive_service.service
            request = service.files().get_media(fileId=file_id)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xle') as temp_file:
                downloader = MediaIoBaseDownload(temp_file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if progress_callback and status:
                        progress = int(status.progress() * 50)  # First 50% for download
                        progress_callback(f"Downloading {filename}...", progress)
                
                temp_path = temp_file.name
            
            if progress_callback:
                progress_callback(f"Organizing {filename}...", 50)
            
            # Extract metadata for organization
            metadata = self.extract_xle_metadata(temp_path)
            
            # Determine target folder
            target_folder = self.organize_file_by_date(temp_path, metadata)
            target_path = os.path.join(target_folder, filename)
            
            # Get month folder name for metadata
            month_folder = os.path.basename(target_folder)
            
            # Check if file already exists in SMOO target
            file_exists = False
            if os.path.exists(target_path):
                # Compare file sizes to see if it's the same file
                target_size = os.path.getsize(target_path)
                
                if file_size == target_size:
                    logger.info(f"File already consolidated: {filename}")
                    os.remove(temp_path)  # Clean up temp file
                    if progress_callback:
                        progress_callback(f"Already exists: {filename}", 100)
                    file_exists = True
                else:
                    # Create unique name for different file
                    timestamp = datetime.now().strftime("%H%M%S")
                    name, ext = os.path.splitext(filename)
                    target_path = os.path.join(target_folder, f"{name}_{timestamp}{ext}")
                    filename = f"{name}_{timestamp}{ext}"  # Update filename for metadata
            
            if not file_exists:
                if progress_callback:
                    progress_callback(f"Saving {filename}...", 75)
                
                # Move file from temp to SMOO target location
                logger.info(f"Consolidating: {filename} -> {os.path.relpath(target_path, self.consolidated_folder)}")
                shutil.move(temp_path, target_path)
            
            if progress_callback:
                progress_callback(f"Consolidated: {filename}", 100)
            
            # Create metadata entry
            file_metadata = {
                'filename': filename,
                'shared_drive_file_path': target_path,
                'serial_number': metadata.get('serial_number', 'unknown'),
                'cae_number': metadata.get('serial_number', 'unknown'),  # Use serial as CAE number
                'location': metadata.get('location', 'unknown'),
                'device_type': metadata.get('instrument_type', 'unknown'),
                'actual_start_date': metadata.get('start_date', ''),
                'actual_end_date': metadata.get('end_date', ''),
                'file_size': file_size,
                'file_modified_time': file_info['modified_time'],
                'processed_date': datetime.now().isoformat(),
                'month_folder': month_folder
            }
            
            return True, file_metadata
            
        except Exception as e:
            logger.error(f"Error consolidating file {file_info['name']}: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            if progress_callback:
                progress_callback(f"Error: {file_info['name']}", 100)
            return False, None
    
    def _generate_metadata_files(self, monthly_metadata: Dict) -> bool:
        """
        Generate metadata.json files for each month folder
        
        Args:
            monthly_metadata: Dictionary of month data with file metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success_count = 0
            
            for month_folder, metadata in monthly_metadata.items():
                try:
                    # Create metadata.json path
                    month_path = os.path.join(self.consolidated_folder, month_folder)
                    metadata_path = os.path.join(month_path, 'metadata.json')
                    
                    # Ensure month folder exists
                    os.makedirs(month_path, exist_ok=True)
                    
                    # Write metadata.json file
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"Generated metadata.json for {month_folder} with {len(metadata['files'])} files")
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error generating metadata for {month_folder}: {e}")
            
            return success_count == len(monthly_metadata)
            
        except Exception as e:
            logger.error(f"Error generating metadata files: {e}")
            return False
    
    def get_consolidated_folder_info(self) -> Dict:
        """
        Get information about the consolidated folder structure
        
        Returns:
            Dictionary with folder structure information
        """
        info = {
            'consolidated_folder': self.consolidated_folder,
            'months_available': [],
            'total_files': 0,
            'accessible': False
        }
        
        try:
            if not os.path.exists(self.consolidated_folder):
                return info
            
            info['accessible'] = True
            
            # Scan for month folders
            for item in os.listdir(self.consolidated_folder):
                month_path = os.path.join(self.consolidated_folder, item)
                if os.path.isdir(month_path) and len(item) == 7:  # YYYY-MM format
                    file_count = len([f for f in os.listdir(month_path) if f.lower().endswith('.xle')])
                    info['months_available'].append({
                        'month': item,
                        'path': month_path,
                        'file_count': file_count
                    })
                    info['total_files'] += file_count
            
            # Sort months by date
            info['months_available'].sort(key=lambda x: x['month'])
            
            logger.info(f"Consolidated folder info: {len(info['months_available'])} months, {info['total_files']} total files")
            
        except Exception as e:
            logger.error(f"Error getting consolidated folder info: {e}")
        
        return info