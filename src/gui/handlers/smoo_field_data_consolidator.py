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
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Callable
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
        
        # Google Drive sources (Multiple field laptop SOLINST folders)
        self.field_laptop_folders = self._get_field_laptop_folders()
        
        # Legacy single folder support (for backward compatibility)
        self.solinst_folder_id = self.settings_handler.get_setting("google_drive_solinst_folder_id", "")
        
        # SMOO target (FIELD_DATA_CONSOLIDATED) - use cross-platform path manager
        from ...config.smoo_paths import get_smoo_path, is_smoo_available
        if is_smoo_available():
            self.smoo_root = get_smoo_path("base")
            self.consolidated_folder = get_smoo_path("field_data")
        else:
            # Fallback to settings for backward compatibility
            self.smoo_root = self.settings_handler.get_setting("shared_drive_root", DefaultPaths.SHARED_DRIVE_BASE)
            self.consolidated_folder = os.path.join(self.smoo_root, "FIELD_DATA_CONSOLIDATED")
        
        # Field data consolidation organizes files by YYYY-MM date folders
        # This is SEPARATE from XLE import organization (which uses well/serial folders)
        logger.info(f"Field data consolidation will organize files by end date in: {self.consolidated_folder}")
        
        # Timestamp tracking for incremental sync
        self.sync_timestamp_file = os.path.join(self.consolidated_folder, ".last_field_sync_timestamp.json")
        
        logger.info(f"Multi-Folder Field Data Consolidator initialized:")
        if self.field_laptop_folders:
            logger.info(f"  Found {len(self.field_laptop_folders)} field laptop folders:")
            for laptop_name, folder_id in self.field_laptop_folders.items():
                logger.info(f"    {laptop_name}: {folder_id}")
        elif self.solinst_folder_id:
            logger.info(f"  Legacy single folder mode: {self.solinst_folder_id}")
        else:
            logger.warning("  No field laptop folders configured!")
        logger.info(f"  SMOO Consolidated: {self.consolidated_folder}")
        logger.info(f"  Using YYYY-MM date-based organization (NOT XLE import structure)")
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
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"Timestamp file is empty: {self.sync_timestamp_file}")
                        return None
                    data = json.loads(content)
                    timestamp_str = data.get('last_sync_timestamp')
                    if timestamp_str:
                        # Parse ISO format timestamp
                        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return None
        except Exception as e:
            logger.warning(f"Could not read last sync timestamp: {e}")
            logger.warning(f"Timestamp file path: {self.sync_timestamp_file}")
            # Try to read raw content for debugging
            try:
                with open(self.sync_timestamp_file, 'r') as f:
                    raw_content = f.read()
                    logger.warning(f"Raw timestamp file content (first 100 chars): '{raw_content[:100]}'")
            except:
                pass
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
    
    def _get_field_laptop_folders(self) -> Dict[str, str]:
        """
        Get field laptop folder configurations from settings
        
        Returns:
            Dictionary mapping laptop names to folder IDs
        """
        field_folders = {}
        
        # Check for individual laptop folder settings
        laptop_configs = [
            ("Laptop_1", "google_drive_laptop_1_folder_id"),
            ("Laptop_2", "google_drive_laptop_2_folder_id"), 
            ("Laptop_3", "google_drive_laptop_3_folder_id")
        ]
        
        for laptop_name, setting_key in laptop_configs:
            folder_id = self.settings_handler.get_setting(setting_key, "")
            if folder_id:
                field_folders[laptop_name] = folder_id
                logger.debug(f"Found {laptop_name} folder: {folder_id}")
        
        return field_folders
    
    def scan_google_drive_solinst(self, incremental: bool = True) -> List[Dict]:
        """
        Scan Google Drive SOLINST folders (multiple field laptops) for XLE files with optional incremental filtering
        
        Args:
            incremental: If True, only return files newer than last sync
        
        Returns:
            List of file info dictionaries with laptop source information
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
            
            # Determine which folders to scan
            folders_to_scan = []
            
            if self.field_laptop_folders:
                # Multi-folder mode: scan all configured laptop folders
                logger.info(f"📂 MULTI_FOLDER: Scanning {len(self.field_laptop_folders)} field laptop folders...")
                for laptop_name, folder_id in self.field_laptop_folders.items():
                    folders_to_scan.append((laptop_name, folder_id))
            elif self.solinst_folder_id:
                # Legacy single folder mode
                logger.info("📂 LEGACY_MODE: Scanning single SOLINST folder...")
                folders_to_scan.append(("Legacy_SOLINST", self.solinst_folder_id))
            else:
                logger.error("❌ No field laptop folders configured!")
                return []
            
            # Scan each folder and collect files
            all_files = []
            
            for laptop_name, folder_id in folders_to_scan:
                logger.info(f"📂 SCANNING: {laptop_name} (ID: {folder_id})...")
                
                try:
                    # Set the folder ID for this scan
                    self.drive_service.set_solinst_folder_id(folder_id)
                    
                    # Scan this specific folder
                    files_found = self.drive_service.list_xle_files()
                    logger.info(f"📂 {laptop_name}: Found {len(files_found)} XLE files")
                    
                    # Add laptop source information to each file
                    for file_info in files_found:
                        file_info['source_laptop'] = laptop_name
                        file_info['source_folder_id'] = folder_id
                    
                    all_files.extend(files_found)
                    
                except Exception as folder_error:
                    logger.error(f"❌ Error scanning {laptop_name}: {folder_error}")
                    continue
            
            logger.info(f"📂 TOTAL: Found {len(all_files)} XLE files across all field laptop folders")
            
            # Convert to format expected by consolidator and filter by timestamp
            consolidated_files = []
            skipped_count = 0
            
            for file_info in all_files:
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
                    'modified_datetime': file_modified,
                    'source_laptop': file_info.get('source_laptop', 'Unknown'),
                    'source_folder_id': file_info.get('source_folder_id', '')
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
    
    
    def get_actual_year_month_from_xle(self, file_path: str) -> str:
        """
        Read XLE file to determine the correct year-month folder based on actual data end date
        (Following main branch logic)
        
        Args:
            file_path: Path to downloaded XLE file
            
        Returns:
            Year-month string (YYYY-MM) based on actual data end date
        """
        try:
            from ..handlers.solinst_reader import SolinstReader
            
            # Read XLE file to get actual data
            reader = SolinstReader()
            df, metadata = reader.read_xle(Path(file_path))
            
            # Get actual last date from data to determine folder
            if not df.empty and 'timestamp' in df.columns:
                last_date = df['timestamp'].max()
                # Use the last date to determine which month folder
                year_month = last_date.strftime('%Y-%m')
                logger.info(f"File {os.path.basename(file_path)} belongs in {year_month} folder based on actual data end date")
                return year_month
            else:
                logger.warning(f"No data found in {os.path.basename(file_path)}, using file modification date")
                # Fallback to file modification date
                file_stat = os.stat(file_path)
                file_date = datetime.fromtimestamp(file_stat.st_mtime)
                return file_date.strftime('%Y-%m')
                
        except Exception as e:
            logger.error(f"Error reading actual dates from {os.path.basename(file_path)}: {e}")
            # If anything fails, fall back to file modification date
            try:
                file_stat = os.stat(file_path)
                file_date = datetime.fromtimestamp(file_stat.st_mtime)
                return file_date.strftime('%Y-%m')
            except Exception as fallback_error:
                logger.error(f"Even fallback date failed: {fallback_error}")
                # Ultimate fallback to current month
                return datetime.now().strftime('%Y-%m')
    
    def generate_corrected_filename(self, file_path: str, original_filename: str) -> str:
        """
        Generate corrected filename by reading actual XLE data
        (Following main branch logic)
        
        Args:
            file_path: Path to downloaded XLE file
            original_filename: Original filename from Google Drive
            
        Returns:
            Corrected filename based on actual data
        """
        try:
            from ..handlers.solinst_reader import SolinstReader
            
            # Read XLE file to get actual data
            reader = SolinstReader()
            df, metadata = reader.read_xle(Path(file_path))
            
            # Get actual first and last dates from data
            if not df.empty and 'timestamp' in df.columns:
                first_date = df['timestamp'].min()
                last_date = df['timestamp'].max()
                
                # Get location from metadata (not from filename!)
                location = metadata.location.strip() if metadata.location else 'UNKNOWN'
                
                # Remove any problematic characters from location
                location = location.replace(':', '').replace('/', '_').replace('\\', '_')
                
                # Format: Location_YYYY_MM_DD_To_YYYY_MM_DD.xle
                # Using actual data dates, not the metadata start/stop times
                new_filename = f"{location}_{first_date.strftime('%Y_%m_%d')}_To_{last_date.strftime('%Y_%m_%d')}.xle"
                
                logger.info(f"Generated corrected filename: {new_filename} (original: {original_filename})")
                logger.debug(f"  Location from metadata: {metadata.location}")
                logger.debug(f"  Data date range: {first_date} to {last_date}")
                
                return new_filename
            else:
                logger.warning(f"No data found in {original_filename}, using original name")
                return original_filename
                
        except Exception as e:
            logger.error(f"Error generating corrected filename for {original_filename}: {e}")
            # If anything fails, return original filename
            return original_filename
    
    def get_file_metadata_from_local_file(self, file_path: str, filename: str) -> Optional[Dict]:
        """
        Get metadata by reading local file (for metadata.json generation)
        (Following main branch logic)
        
        Args:
            file_path: Path to local XLE file
            filename: Filename
            
        Returns:
            Metadata dictionary or None if failed
        """
        try:
            from ..handlers.solinst_reader import SolinstReader
            
            # Read XLE file directly
            reader = SolinstReader()
            df, metadata = reader.read_xle(Path(file_path))
            
            if not df.empty and 'timestamp' in df.columns:
                first_date = df['timestamp'].min()
                last_date = df['timestamp'].max()
                
                return {
                    'serial_number': str(metadata.serial_number) if metadata.serial_number else 'unknown',
                    'cae_number': metadata.location.replace(':', '') if metadata.location else 'unknown',
                    'location': metadata.location if metadata.location else 'unknown',
                    'device_type': 'barologger' if 'baro' in filename.lower() else 'water_level',
                    'actual_start_date': first_date.isoformat(),
                    'actual_end_date': last_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error reading local file metadata from {filename}: {e}")
            
        return None
    
    def update_folder_metadata(self, folder_path: str, year_month: str, file_path: str, filename: str, laptop_source: str = "Unknown") -> bool:
        """
        Update or create metadata.json in the specified folder after adding a file
        (Following main branch logic for SMOO shared drive mode)
        
        Args:
            folder_path: Target folder path
            year_month: Year-month string
            file_path: Path to the consolidated file
            filename: Filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get file info from local file
            file_size = os.path.getsize(file_path)
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            
            # Get file metadata by reading the local file
            file_metadata = self.get_file_metadata_from_local_file(file_path, filename)
            if not file_metadata:
                logger.warning(f"Could not extract metadata from {filename}")
                return False
            
            # Load existing metadata or create new
            metadata_path = os.path.join(folder_path, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    'folder': year_month,
                    'generated_date': datetime.now().isoformat(),
                    'files': []
                }
            
            # Create file entry
            file_entry = {
                'filename': filename,
                'shared_drive_file_path': file_path,
                'source_laptop': laptop_source,
                'serial_number': file_metadata.get('serial_number', 'unknown'),
                'cae_number': file_metadata.get('cae_number', 'unknown'),
                'location': file_metadata.get('location', 'unknown'),
                'device_type': file_metadata.get('device_type', 'unknown'),
                'actual_start_date': file_metadata.get('actual_start_date', ''),
                'actual_end_date': file_metadata.get('actual_end_date', ''),
                'file_size': file_size,
                'file_modified_time': file_modified,
                'processed_date': datetime.now().isoformat()
            }
            
            # Remove any existing entry with same filename
            metadata['files'] = [
                f for f in metadata['files'] 
                if f.get('filename') != filename
            ]
            
            # Add the new/updated entry
            metadata['files'].append(file_entry)
            metadata['generated_date'] = datetime.now().isoformat()
            
            # Write to shared drive
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.debug(f"Updated metadata.json in {folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating folder metadata in {folder_path}: {e}")
            return False
    
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
            laptop_source = file_info.get('source_laptop', 'Unknown_Laptop')
            
            if progress_callback:
                progress_callback(f"[{laptop_source}] Downloading {filename}...", 0)
            
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
                        progress_callback(f"[{laptop_source}] Downloading {filename}...", progress)
                
                temp_path = temp_file.name
            
            if progress_callback:
                progress_callback(f"Organizing {filename}...", 50)
            
            # Determine target folder using actual data end date (main branch logic)
            if progress_callback:
                progress_callback(f"[{laptop_source}] Reading {filename} data to determine correct month folder...", 55)
            
            actual_year_month = self.get_actual_year_month_from_xle(temp_path)
            target_folder = os.path.join(self.consolidated_folder, actual_year_month)
            
            # Ensure target folder exists
            os.makedirs(target_folder, exist_ok=True)
            
            # Generate corrected filename based on actual data
            if progress_callback:
                progress_callback(f"[{laptop_source}] Generating corrected filename for {filename}...", 60)
            
            corrected_filename = self.generate_corrected_filename(temp_path, filename)
            target_path = os.path.join(target_folder, corrected_filename)
            
            logger.info(f"FIELD_SYNC: Target folder: {actual_year_month}")
            logger.info(f"FIELD_SYNC: Corrected filename: {corrected_filename}")
            
            if progress_callback:
                progress_callback(f"[{laptop_source}] Target: {actual_year_month}/{corrected_filename}", 65)
            
            # Check if file already exists and is up to date
            if os.path.exists(target_path):
                existing_modified = datetime.fromtimestamp(os.path.getmtime(target_path))
                # Use file info modified time as source reference
                source_modified = datetime.fromisoformat(file_info['modified_time'].replace('Z', '+00:00')).replace(tzinfo=None)
                
                if source_modified <= existing_modified:
                    logger.info(f"File {corrected_filename} already up to date in {actual_year_month}")
                    os.remove(temp_path)
                    if progress_callback:
                        progress_callback(f"[{laptop_source}] Already up to date: {corrected_filename}", 100)
                    return True
                else:
                    logger.info(f"[{laptop_source}] Updating existing file {corrected_filename} with newer version")
            
            if progress_callback:
                progress_callback(f"[{laptop_source}] Saving {corrected_filename}...", 75)
            
            # Move file to target location
            shutil.move(temp_path, target_path)
            logger.info(f"FIELD_SYNC: Saved file to: {target_path}")
            
            # Update metadata.json for this month folder
            if progress_callback:
                progress_callback(f"[{laptop_source}] Updating metadata for {actual_year_month}...", 85)
            
            try:
                self.update_folder_metadata(target_folder, actual_year_month, target_path, corrected_filename, laptop_source)
                logger.debug(f"Updated metadata.json in {actual_year_month} folder for {corrected_filename}")
            except Exception as e:
                logger.error(f"Failed to update metadata for {actual_year_month}: {e}")
            
            target_path = Path(target_path)
            if progress_callback:
                progress_callback(f"[{laptop_source}] ✅ Consolidated to: {actual_year_month}/{corrected_filename}", 90)
            
            if progress_callback:
                final_location = str(target_path.parent) if isinstance(target_path, Path) else os.path.dirname(target_path)
                progress_callback(f"[{laptop_source}] ✅ Final: {os.path.basename(final_location)}/{corrected_filename}", 100)
            
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
        using YYYY-MM date-based folders (following main branch logic)
        
        Args:
            progress_callback: Optional progress callback function (message, percent)
            force_full_sync: If True, download all files regardless of timestamp
            
        Returns:
            True if consolidation successful, False otherwise
        """
        try:
            sync_type = "FULL SYNC" if force_full_sync else "INCREMENTAL SYNC"
            logger.info(f"Starting field data consolidation (Google Drive → SMOO) - {sync_type}...")
            
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
            
            # Consolidate each file and track monthly folders for metadata
            successful_count = 0
            total_files = len(files_to_consolidate)
            monthly_folders = set()  # Track which month folders were updated
            
            for i, file_info in enumerate(files_to_consolidate):
                # Calculate progress (10% for scanning, 85% for processing, 5% for metadata)
                base_progress = 10 + int((i / total_files) * 85)
                
                def file_progress_callback(message, percent):
                    if progress_callback:
                        # Map file progress to overall progress
                        file_range = 85 / total_files  # Each file gets this % range
                        overall_progress = base_progress + int((percent / 100) * file_range)
                        progress_callback(message, min(overall_progress, 94))
                
                success = self.consolidate_file(file_info, file_progress_callback)
                if success:
                    successful_count += 1
                    # Track which month folder this file went to for metadata updates
                    # (this is handled within consolidate_file via update_folder_metadata)
            
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
                    progress_callback(f"Complete: {successful_count}/{total_files} files consolidated with metadata", 100)
                else:
                    progress_callback(f"Complete: No files needed consolidation", 100)
            
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