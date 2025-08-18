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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Callable
from googleapiclient.http import MediaIoBaseDownload
from ...config.paths import DefaultPaths
from ..utils.file_organizer import XLEFileOrganizer

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
        
        # Initialize XLE file organizer for proper organization
        self.xle_organizer = XLEFileOrganizer(
            app_root_dir=Path(self.consolidated_folder),
            db_name="FIELD_DATA_CONSOLIDATED",  # Use as project name
            settings_handler=settings_handler
        )
        
        # Timestamp tracking for incremental sync
        self.sync_timestamp_file = os.path.join(self.consolidated_folder, ".last_field_sync_timestamp.json")
        
        logger.info(f"Hybrid Consolidator initialized:")
        logger.info(f"  Google Drive SOLINST ID: {self.solinst_folder_id}")
        logger.info(f"  SMOO Consolidated: {self.consolidated_folder}")
        logger.info(f"  Using new SMOO XLE workflow for organization")
        logger.info(f"  Timestamp tracking: {self.sync_timestamp_file}")
    
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
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful field sync
        
        Returns:
            Last sync timestamp or None if never synced
        """
        try:
            if os.path.exists(self.sync_timestamp_file):
                with open(self.sync_timestamp_file, 'r') as f:
                    data = json.load(f)
                    timestamp_str = data.get('last_sync_timestamp')
                    if timestamp_str:
                        # Parse ISO format timestamp
                        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return None
        except Exception as e:
            logger.warning(f"Could not read last sync timestamp: {e}")
            return None
    
    def save_sync_timestamp(self, timestamp: datetime = None) -> bool:
        """
        Save the current sync timestamp
        
        Args:
            timestamp: Timestamp to save (defaults to current time)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.sync_timestamp_file), exist_ok=True)
            
            data = {
                'last_sync_timestamp': timestamp.isoformat(),
                'sync_completed_at': datetime.now(timezone.utc).isoformat(),
                'smoo_consolidated_folder': self.consolidated_folder
            }
            
            with open(self.sync_timestamp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"INCREMENTAL_SYNC: Saved sync timestamp: {timestamp.isoformat()}")
            return True
            
        except Exception as e:
            logger.error(f"Could not save sync timestamp: {e}")
            return False
    
    def scan_google_drive_solinst(self, incremental: bool = True) -> List[Dict]:
        """
        Scan Google Drive SOLINST folder for XLE files with optional incremental filtering
        
        Args:
            incremental: If True, only return files newer than last sync
        
        Returns:
            List of file info dictionaries
        """
        try:
            # Get last sync timestamp for incremental sync
            last_sync = None
            if incremental:
                logger.info(f"🕒 INCREMENTAL_SYNC: Checking timestamp file: {self.sync_timestamp_file}")
                logger.info(f"🕒 INCREMENTAL_SYNC: Timestamp file exists: {os.path.exists(self.sync_timestamp_file)}")
                
                last_sync = self.get_last_sync_timestamp()
                if last_sync:
                    logger.info(f"🕒 INCREMENTAL_SYNC: Last sync timestamp: {last_sync.isoformat()}")
                    logger.info(f"🕒 INCREMENTAL_SYNC: Only syncing files modified after {last_sync.isoformat()}")
                else:
                    logger.info("🕒 INCREMENTAL_SYNC: No previous sync found, downloading all files")
            else:
                logger.info("🔄 FULL_SYNC: Force full sync requested, downloading all files")
            
            # Set the SOLINST folder ID if not set
            if self.solinst_folder_id:
                self.drive_service.set_solinst_folder_id(self.solinst_folder_id)
            
            # Use the service account handler's built-in method
            logger.info("📂 GOOGLE_DRIVE: Scanning SOLINST folder for XLE files...")
            files_found = self.drive_service.list_xle_files()
            logger.info(f"📂 GOOGLE_DRIVE: Found {len(files_found)} total XLE files in SOLINST folder")
            
            # Convert to format expected by consolidator and filter by timestamp
            consolidated_files = []
            skipped_count = 0
            
            for file_info in files_found:
                # Parse file modification time
                file_modified_str = file_info['modifiedTime']
                try:
                    # Google Drive uses RFC 3339 format: 2024-01-01T12:00:00.000Z
                    file_modified = datetime.fromisoformat(file_modified_str.replace('Z', '+00:00'))
                except Exception as time_error:
                    logger.warning(f"Could not parse modification time for {file_info['name']}: {time_error}")
                    file_modified = None
                
                # Apply incremental filtering
                if incremental and last_sync and file_modified:
                    if file_modified <= last_sync:
                        skipped_count += 1
                        logger.info(f"⏭️ INCREMENTAL_SYNC: Skipping {file_info['name']} (Modified: {file_modified_str}, Last sync: {last_sync.isoformat()})")
                        continue
                
                consolidated_file = {
                    'id': file_info['id'],
                    'name': file_info['name'], 
                    'size': int(file_info.get('size', 0)),
                    'modified_time': file_modified_str,
                    'modified_datetime': file_modified
                }
                consolidated_files.append(consolidated_file)
                
                if incremental and last_sync:
                    logger.info(f"✅ INCREMENTAL_SYNC: Will sync {file_info['name']} (Modified: {file_modified_str})")
                else:
                    logger.info(f"📄 Found Google Drive XLE: {file_info['name']} (Modified: {file_modified_str})")
            
            # Enhanced summary logging
            total_files = len(files_found)
            new_files = len(consolidated_files)
            
            if incremental and last_sync:
                logger.info(f"📊 INCREMENTAL_SYNC SUMMARY:")
                logger.info(f"📊 Total files in Google Drive SOLINST: {total_files}")
                logger.info(f"📊 Files skipped (not modified since last sync): {skipped_count}")
                logger.info(f"📊 New/modified files to sync: {new_files}")
                if skipped_count > 0:
                    logger.info(f"📊 Last sync was: {last_sync.isoformat()}")
            else:
                logger.info(f"📊 SYNC SUMMARY: Found {new_files} XLE files in Google Drive SOLINST")
            
            return consolidated_files
            
        except Exception as e:
            logger.error(f"Error scanning Google Drive SOLINST: {e}")
            return []
    
    def extract_xle_metadata(self, file_path: str) -> Dict:
        """
        Extract comprehensive metadata from XLE file using proper XML parsing
        
        Args:
            file_path: Path to XLE file
            
        Returns:
            Dictionary with extracted metadata including dates, device info, etc.
        """
        metadata = {
            'serial_number': 'unknown',
            'location': 'unknown',  
            'start_date': None,
            'end_date': None,
            'instrument_type': 'levellogger',  # Default to levellogger
            'well_number': None,
            'device_type': 'transducer'  # Default for XLEFileOrganizer
        }
        
        try:
            # Parse XML properly
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract instrument info
            instrument_info = root.find('.//Instrument_info')
            if instrument_info is not None:
                # Serial number
                serial_elem = instrument_info.find('Serial_number')
                if serial_elem is not None and serial_elem.text:
                    metadata['serial_number'] = serial_elem.text.strip()
                
                # Location  
                location_elem = instrument_info.find('Location')
                if location_elem is not None and location_elem.text:
                    metadata['location'] = location_elem.text.strip()
                
                # Model to determine device type
                model_elem = instrument_info.find('Model')
                if model_elem is not None and model_elem.text:
                    model = model_elem.text.lower()
                    if 'baro' in model:
                        metadata['instrument_type'] = 'barologger'
                        metadata['device_type'] = 'barologger'
                    else:
                        metadata['instrument_type'] = 'levellogger' 
                        metadata['device_type'] = 'transducer'
            
            # Extract date range from data
            data_section = root.find('.//Data')
            if data_section is not None:
                log_entries = data_section.findall('.//Log')
                if log_entries:
                    try:
                        # Get first and last data points
                        first_log = log_entries[0]
                        last_log = log_entries[-1]
                        
                        # Parse start date
                        first_date = first_log.find('Date')
                        first_time = first_log.find('Time') 
                        if first_date is not None and first_time is not None:
                            date_str = f"{first_date.text} {first_time.text}"
                            metadata['start_date'] = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
                        
                        # Parse end date
                        last_date = last_log.find('Date')
                        last_time = last_log.find('Time')
                        if last_date is not None and last_time is not None:
                            date_str = f"{last_date.text} {last_time.text}"
                            metadata['end_date'] = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
                            
                    except Exception as date_error:
                        logger.warning(f"Could not parse dates from XLE file: {date_error}")
            
            # For barologgers, use serial number; for transducers, try to extract well info
            if metadata['device_type'] == 'transducer':
                # Try to extract well number from location
                location = metadata['location'].upper()
                if 'WELL' in location or 'W-' in location or 'MW' in location:
                    # Extract well identifier
                    import re
                    well_match = re.search(r'(WELL[_\s-]*\d+|W-?\d+|MW[_\s-]*\d+)', location)
                    if well_match:
                        metadata['well_number'] = well_match.group(1).replace(' ', '_').replace('-', '_')
                    else:
                        metadata['well_number'] = location.replace(' ', '_')[:20]  # Fallback
                else:
                    metadata['well_number'] = location.replace(' ', '_')[:20]  # Use location as well ID
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            # Try fallback text parsing
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2048)  # Read more content for fallback
                    
                    # Basic serial number extraction
                    if 'Serial_number=' in content:
                        serial_line = [line for line in content.split('\n') if 'Serial_number=' in line]
                        if serial_line:
                            metadata['serial_number'] = serial_line[0].split('=')[-1].strip()
                    
                    # Basic location extraction
                    if 'Location=' in content:
                        location_line = [line for line in content.split('\n') if 'Location=' in line]
                        if location_line:
                            metadata['location'] = location_line[0].split('=')[-1].strip()
                            
            except Exception as fallback_error:
                logger.error(f"Fallback metadata extraction also failed: {fallback_error}")
        
        logger.debug(f"Extracted metadata for {os.path.basename(file_path)}: {metadata}")
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
            
            # Extract comprehensive metadata for proper organization
            metadata = self.extract_xle_metadata(temp_path)
            
            logger.info(f"FIELD_SYNC: Organizing {filename} using SMOO XLE workflow")
            logger.info(f"FIELD_SYNC: Device type: {metadata['device_type']}, Serial: {metadata['serial_number']}, Location: {metadata['location']}")
            
            # Use XLEFileOrganizer for proper organization with SMOO structure
            if metadata['device_type'] == 'barologger':
                target_path = self.xle_organizer.organize_barologger_file(
                    Path(temp_path),
                    metadata['serial_number'],
                    metadata['location'],
                    metadata['start_date'] or datetime.now(),
                    metadata['end_date'] or datetime.now()
                )
            else:  # transducer
                well_number = metadata['well_number'] or metadata['location']
                target_path = self.xle_organizer.organize_transducer_file(
                    Path(temp_path),
                    metadata['serial_number'],
                    metadata['location'],
                    metadata['start_date'] or datetime.now(),
                    metadata['end_date'] or datetime.now(),
                    well_number
                )
            
            if target_path and target_path.exists():
                logger.info(f"FIELD_SYNC: Successfully organized to SMOO structure: {target_path}")
                if progress_callback:
                    progress_callback(f"Organized: {filename}", 75)
            else:
                # Fallback to simple copy if XLE organizer fails
                logger.warning(f"FIELD_SYNC: XLE organizer failed, using fallback organization")
                fallback_folder = self.organize_file_by_date(temp_path, metadata)
                target_path = os.path.join(fallback_folder, filename)
                
                # Check if file already exists
                if os.path.exists(target_path):
                    target_size = os.path.getsize(target_path)
                    if file_size == target_size:
                        logger.info(f"File already consolidated: {filename}")
                        os.remove(temp_path)
                        if progress_callback:
                            progress_callback(f"Already exists: {filename}", 100)
                        return True
                
                if progress_callback:
                    progress_callback(f"Saving {filename}...", 75)
                
                shutil.move(temp_path, target_path)
                target_path = Path(target_path)
            
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
    
    def consolidate_field_data(self, progress_callback: Optional[Callable] = None, force_full_sync: bool = False) -> bool:
        """
        Consolidate all field data from Google Drive SOLINST to SMOO organized structure
        
        Args:
            progress_callback: Optional progress callback function (message, percent)
            force_full_sync: If True, download all files regardless of timestamp
            
        Returns:
            True if consolidation successful, False otherwise
        """
        try:
            sync_type = "FULL SYNC" if force_full_sync else "INCREMENTAL SYNC"
            logger.info(f"Starting hybrid field data consolidation (Google Drive → SMOO) - {sync_type}...")
            
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
            
            # Scan Google Drive for files (with incremental sync unless forced)
            files_to_consolidate = self.scan_google_drive_solinst(incremental=not force_full_sync)
            
            if not files_to_consolidate:
                logger.info("No new files found to consolidate in Google Drive SOLINST")
                if progress_callback:
                    progress_callback("No new files to consolidate", 100)
                # Even if no files, update timestamp to mark this sync attempt
                self.save_sync_timestamp()
                return True
            
            logger.info(f"Found {len(files_to_consolidate)} files to consolidate from Google Drive")
            
            # Consolidate each file
            successful_count = 0
            total_files = len(files_to_consolidate)
            
            for i, file_info in enumerate(files_to_consolidate):
                # Calculate progress (10% for scanning, 90% for processing)
                base_progress = 10 + int((i / total_files) * 90)
                
                def file_progress_callback(message, percent):
                    if progress_callback:
                        # Map file progress to overall progress
                        file_range = 90 / total_files  # Each file gets this % range
                        overall_progress = base_progress + int((percent / 100) * file_range)
                        progress_callback(message, min(overall_progress, 99))
                
                success = self.consolidate_file(file_info, file_progress_callback)
                if success:
                    successful_count += 1
            
            logger.info(f"Consolidation complete: {successful_count}/{total_files} files processed successfully")
            
            # Save sync timestamp after successful consolidation
            if successful_count > 0:
                # Use the latest file modification time as sync timestamp
                latest_file_time = None
                for file_info in files_to_consolidate:
                    if file_info.get('modified_datetime'):
                        if latest_file_time is None or file_info['modified_datetime'] > latest_file_time:
                            latest_file_time = file_info['modified_datetime']
                
                if latest_file_time:
                    self.save_sync_timestamp(latest_file_time)
                    logger.info(f"INCREMENTAL_SYNC: Updated sync timestamp to {latest_file_time.isoformat()}")
                else:
                    # Fallback to current time
                    self.save_sync_timestamp()
                    logger.info("INCREMENTAL_SYNC: Updated sync timestamp to current time")
            else:
                # Even if no files succeeded, update timestamp to avoid re-processing same files
                self.save_sync_timestamp()
            
            if progress_callback:
                if successful_count > 0:
                    progress_callback(f"Complete: {successful_count}/{total_files} files consolidated (incremental sync)", 100)
                else:
                    progress_callback(f"Complete: No files needed consolidation (incremental sync)", 100)
            
            return successful_count > 0 or total_files == 0  # Success if files processed or no files needed
            
        except Exception as e:
            logger.error(f"Error during field data consolidation: {e}")
            if progress_callback:
                progress_callback(f"Error: {str(e)}", 100)
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