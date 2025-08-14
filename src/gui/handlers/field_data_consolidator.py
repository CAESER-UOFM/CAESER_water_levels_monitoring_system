import logging
import os
import re
from datetime import datetime
from pathlib import Path
import json
import tempfile
import io
from .google_service_account import GoogleServiceAccountHandler

logger = logging.getLogger(__name__)

class FieldDataConsolidator:
    """Consolidates XLE files from SOLINST folder (via service account) to SMOO shared drive"""
    
    def __init__(self, service_account_handler=None, settings_handler=None):
        """
        Initialize with service account handler for SOLINST folder access and SMOO destination.
        
        Args:
            service_account_handler: GoogleServiceAccountHandler for SOLINST folder access
            settings_handler: Settings handler for configuration
        """
        self.service_account_handler = service_account_handler
        self.settings_handler = settings_handler
        
        # SMOO destination configuration (replaces consolidated_folder_id)
        self.shared_drive_field_data_path = settings_handler.get_setting("shared_drive_field_data", "") if settings_handler else ""
        
        # Always use SMOO shared drive mode
        
        logger.info("FieldDataConsolidator initialized - Service Account → SMOO mode")
        if self.shared_drive_field_data_path:
            logger.info(f"SMOO destination: {self.shared_drive_field_data_path}")
        else:
            logger.warning("SMOO destination path not configured")
    
    # === SHARED DRIVE DESTINATION METHODS ===
    
    def _get_shared_drive_consolidated_path(self):
        """Get S: drive consolidated folder path"""
        if not self.shared_drive_field_data_path:
            logger.error("Shared drive field data path not configured")
            return None
        return self.shared_drive_field_data_path
    
    def _create_shared_drive_monthly_folder(self, year_month):
        """Create monthly folder on S: drive"""
        try:
            base_path = self._get_shared_drive_consolidated_path()
            if not base_path:
                return None
            
            folder_path = os.path.join(base_path, year_month)
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"Created/verified shared drive monthly folder: {folder_path}")
            return folder_path
        except Exception as e:
            logger.error(f"Error creating shared drive monthly folder {year_month}: {e}")
            return None
    
    def _download_and_save_to_shared_drive(self, file_info, target_folder_path):
        """Download from SOLINST folder (via service account) and save to SMOO drive"""
        try:
            import shutil
            
            if not self.service_account_handler or not self.service_account_handler.is_authenticated():
                logger.error("Service account handler not available or not authenticated")
                return None
            
            # Generate corrected filename
            new_filename = self.generate_corrected_filename(file_info)
            target_file_path = os.path.join(target_folder_path, new_filename)
            
            # Check if file already exists and is up to date
            if os.path.exists(target_file_path):
                existing_modified = datetime.fromtimestamp(os.path.getmtime(target_file_path))
                source_modified = datetime.fromisoformat(file_info['modified_time'].replace('Z', '+00:00')).replace(tzinfo=None)
                
                if source_modified <= existing_modified:
                    logger.debug(f"File {new_filename} already up to date in SMOO drive")
                    return target_file_path
                else:
                    logger.info(f"Updating existing file {new_filename} with newer version")
            
            # Download file from SOLINST folder using service account
            temp_file_path = self.service_account_handler.download_file(file_info['id'])
            if not temp_file_path:
                logger.error(f"Failed to download file {file_info['name']} from SOLINST folder")
                return None
            
            # Copy to SMOO drive
            shutil.copy2(temp_file_path, target_file_path)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            logger.info(f"Downloaded {file_info['name']} as {new_filename} to SMOO drive")
            return target_file_path
            
        except Exception as e:
            logger.error(f"Error downloading and saving file {file_info['name']}: {e}")
            return None
    
    def _write_shared_drive_metadata(self, folder_path, metadata):
        """Write metadata.json to S: drive folder"""
        try:
            metadata_path = os.path.join(folder_path, "metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.debug(f"Updated metadata.json in shared drive folder: {folder_path}")
        except Exception as e:
            logger.error(f"Error writing shared drive metadata to {folder_path}: {e}")
            raise
    
    # === ORIGINAL GOOGLE DRIVE METHODS (updated for hybrid mode) ===
        
    def get_or_create_consolidated_folder(self):
        """Get or create the FIELD_DATA_CONSOLIDATED folder (hybrid mode)"""
        try:
            # Always use shared drive mode - ensure S: drive folder exists
            base_path = self._get_shared_drive_consolidated_path()
            if not base_path:
                logger.error("Shared drive consolidated path not configured")
                return None
            
            # Create base folder if it doesn't exist
            os.makedirs(base_path, exist_ok=True)
            logger.info(f"Verified shared drive consolidated folder: {base_path}")
            return base_path
            
        except Exception as e:
            logger.error(f"Error getting/creating consolidated folder: {e}")
            return None
    
    def get_or_create_monthly_folder(self, year_month):
        """Get or create a monthly folder (e.g., '2025-01') in the consolidated folder (hybrid mode)"""
        try:
            # Always use shared drive mode
                # Shared drive mode - create local folder
                return self._create_shared_drive_monthly_folder(year_month)
            else:
                # Google Drive mode - original logic
                if not self.consolidated_folder_id:
                    if not self.get_or_create_consolidated_folder():
                        return None
                
                # Check if monthly folder exists
                query = f"'{self.consolidated_folder_id}' in parents and name='{year_month}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
                folders = results.get('files', [])
                
                if folders:
                    folder_id = folders[0]['id']
                    logger.debug(f"Found existing monthly folder {year_month}: {folder_id}")
                else:
                    # Create the monthly folder
                    folder_metadata = {
                        'name': year_month,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [self.consolidated_folder_id]
                    }
                    folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
                    folder_id = folder.get('id')
                    logger.info(f"Created monthly folder {year_month}: {folder_id}")
                
                return folder_id
            
        except Exception as e:
            logger.error(f"Error getting/creating monthly folder {year_month}: {e}")
            return None
    
    def update_folder_metadata(self, folder_ref, year_month, file_ref):
        """Update or create metadata.json in the specified folder after adding a file (hybrid mode)"""
        try:
            import json
            import io
            from datetime import datetime
            from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
            
            # Always use shared drive mode
                # Shared drive mode - folder_ref is folder path, file_ref is file path
                folder_path = folder_ref
                file_path = file_ref
                
                # Get file info from local file
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                
                # Get file metadata by reading the local file
                file_metadata = self._get_file_metadata_from_local_file(file_path, filename)
                if not file_metadata:
                    logger.warning(f"Could not extract metadata from {filename}")
                    return
                
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
                self._write_shared_drive_metadata(folder_path, metadata)
                
            else:
                # Google Drive mode - original logic
                folder_id = folder_ref
                copied_file_id = file_ref
                
                # Step 1: Get file info for the copied file
                file_info = self.drive_service.files().get(
                    fileId=copied_file_id,
                    fields="id, name, size, modifiedTime"
                ).execute()
                
                # Step 2: Read the file content to get actual data info
                file_metadata = self.get_file_metadata_from_drive(copied_file_id, file_info['name'])
                if not file_metadata:
                    logger.warning(f"Could not extract metadata from {file_info['name']}")
                    return
                
                # Step 3: Check if metadata.json exists in folder
                query = f"'{folder_id}' in parents and name='metadata.json' and trashed=false"
                results = self.drive_service.files().list(q=query, fields="files(id)").execute()
                metadata_files = results.get('files', [])
                
                # Step 4: Load existing metadata or create new
                if metadata_files:
                    # Download existing metadata
                    metadata_file_id = metadata_files[0]['id']
                    request = self.drive_service.files().get_media(fileId=metadata_file_id)
                    content = io.BytesIO()
                    downloader = MediaIoBaseDownload(content, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                    
                    content.seek(0)
                    metadata = json.loads(content.read().decode('utf-8'))
                else:
                    # Create new metadata structure
                    metadata = {
                        'folder': year_month,
                        'generated_date': datetime.now().isoformat(),
                        'files': []
                    }
                    metadata_file_id = None
                
                # Step 5: Update file list (replace if exists, add if new)
                file_entry = {
                    'filename': file_info['name'],
                    'google_drive_file_id': copied_file_id,
                    'serial_number': file_metadata.get('serial_number', 'unknown'),
                    'cae_number': file_metadata.get('cae_number', 'unknown'),
                    'location': file_metadata.get('location', 'unknown'),
                    'device_type': file_metadata.get('device_type', 'unknown'),
                    'actual_start_date': file_metadata.get('actual_start_date', ''),
                    'actual_end_date': file_metadata.get('actual_end_date', ''),
                    'file_size': int(file_info.get('size', 0)),
                    'drive_modified_time': file_info.get('modifiedTime', ''),
                    'processed_date': datetime.now().isoformat()
                }
                
                # Remove any existing entry with same filename or file_id
                metadata['files'] = [
                    f for f in metadata['files'] 
                    if f.get('filename') != file_info['name'] and f.get('google_drive_file_id') != copied_file_id
                ]
                
                # Add the new/updated entry
                metadata['files'].append(file_entry)
                
                # Update generation date
                metadata['generated_date'] = datetime.now().isoformat()
                
                # Step 6: Upload updated metadata.json
                json_content = json.dumps(metadata, indent=2)
                media = MediaIoBaseUpload(
                    io.BytesIO(json_content.encode()),
                    mimetype='application/json',
                    resumable=True
                )
                
                if metadata_file_id:
                    # Update existing file
                    self.drive_service.files().update(
                        fileId=metadata_file_id,
                        media_body=media
                    ).execute()
                    logger.debug(f"Updated existing metadata.json in {year_month} folder")
                else:
                    # Create new file
                    file_metadata_obj = {
                        'name': 'metadata.json', 
                        'parents': [folder_id]
                    }
                    self.drive_service.files().create(
                        body=file_metadata_obj,
                        media_body=media,
                        fields='id'
                    ).execute()
                    logger.debug(f"Created new metadata.json in {year_month} folder")
                
        except Exception as e:
            logger.error(f"Error updating folder metadata: {e}")
            raise
            
    def get_file_metadata_from_drive(self, file_id, filename):
        """Get metadata by downloading and reading the file from Drive"""
        try:
            import tempfile
            import io
            from ..handlers.solinst_reader import SolinstReader
            from pathlib import Path
            from googleapiclient.http import MediaIoBaseDownload
            
            # Download file content
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(suffix='.xle', delete=False) as tmp_file:
                file_content.seek(0)
                tmp_file.write(file_content.read())
                tmp_path = tmp_file.name
            
            try:
                # Read XLE file
                reader = SolinstReader()
                df, metadata = reader.read_xle(Path(tmp_path))
                
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
                
            finally:
                # Clean up temp file
                import os
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error reading file metadata from {filename}: {e}")
            
        return None
    
    def _get_file_metadata_from_local_file(self, file_path, filename):
        """Get metadata by reading local file (for shared drive mode)"""
        try:
            from ..handlers.solinst_reader import SolinstReader
            from pathlib import Path
            
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
    
    def extract_date_from_filename(self, filename):
        """Extract date information from XLE filename"""
        try:
            # Pattern: Anything_YYYY_MM_DD_To_MM_DD.xle or Anything_YYYY_MM_DD_To_YYYY_MM_DD.xle
            # Examples: 
            # - 2197347_MAWT-SS222_2025_04_28_To_05_22.xle
            # - 2000606_WEATHER STATION_2025_03_26_To_04_30.xle
            # - 2181050_HA:A-013_2025_04_28_To_05_22.xle
            
            # Updated patterns to handle various filename formats with flexible digit counts and suffixes
            # Pattern 1: Files starting with underscore (missing location) - _YYYY_MM_DD_To_YYYY_MM_DD.xle
            pattern_no_location = r'^_(\d{4})_(\d{1,2})_(\d{1,2})_To_(\d{4})_(\d{1,2})_(\d{1,2})(?:_[^.]*)?\.xle'
            match = re.match(pattern_no_location, filename, re.IGNORECASE)
            
            if match:
                start_year, start_month, start_day, end_year, end_month, end_day = match.groups()
                year_month = f"{end_year}-{end_month.zfill(2)}"
                cae = "UNKNOWN"  # No location in filename
                logger.debug(f"Matched no-location pattern for {filename}")
            else:
                # Pattern 2: Non-standard date format - Location_M_D_To_M_D_suffix.xle (e.g., PS-PT_6_25_To_7_26_NC_DST.xle)
                pattern_short_date = r'(.+?)_(\d{1,2})_(\d{1,2})_To_(\d{1,2})_(\d{1,2})_(.+)?\.xle'
                match = re.match(pattern_short_date, filename, re.IGNORECASE)
                
                if match:
                    cae = match.group(1)
                    # For short dates without year, use current year as fallback
                    import datetime
                    current_year = datetime.datetime.now().year
                    year_month = f"{current_year}-{match.group(4).zfill(2)}"  # Use end month
                    logger.debug(f"Matched short date pattern for {filename}, using current year {current_year}")
                else:
                    # Pattern 3: Full dates with times - Location_YYYY_MM_DD_HHMMSS_YYYY_MM_DD_HHMMSS[_suffix].xle
                    pattern_full_time = r'(.+?)_(\d{4})_(\d{1,2})_(\d{1,2})_(\d{6})_(\d{4})_(\d{1,2})_(\d{1,2})_(\d{6})(?:_[^.]*)?\.xle'
                    match = re.match(pattern_full_time, filename, re.IGNORECASE)
                    
                    if match:
                        cae, start_year, start_month, start_day, start_time, end_year, end_month, end_day, end_time = match.groups()
                        year_month = f"{end_year}-{end_month.zfill(2)}"
                        logger.debug(f"Matched full pattern with time for {filename}")
                    else:
                        # Pattern 4: Full dates without times with flexible digits and suffixes
                        pattern_full = r'(.+?)_(\d{4})_(\d{1,2})_(\d{1,2})_To_(\d{4})_(\d{1,2})_(\d{1,2})(?:_[^.]*)?\.xle'
                        match = re.match(pattern_full, filename, re.IGNORECASE)
                        
                        if match:
                            cae, start_year, start_month, start_day, end_year, end_month, end_day = match.groups()
                            year_month = f"{end_year}-{end_month.zfill(2)}"
                            logger.debug(f"Matched full pattern for {filename}")
                        else:
                            # Pattern 5: Abbreviated dates (without year in end date) with flexible digits and suffixes
                            pattern_abbrev = r'(.+?)_(\d{4})_(\d{1,2})_(\d{1,2})_To_(\d{1,2})_(\d{1,2})(?:_[^.]*)?\.xle'
                            match = re.match(pattern_abbrev, filename, re.IGNORECASE)
                            
                            if match:
                                cae, start_year, start_month, start_day, end_month, end_day = match.groups()
                                end_year = start_year
                                year_month = f"{end_year}-{end_month.zfill(2)}"
                                logger.debug(f"Matched abbreviated pattern for {filename}")
                            else:
                                logger.warning(f"Could not parse date from filename: {filename}")
                                return None
            
            # Build return dict with available data
            result = {
                'cae': cae.strip() if 'cae' in locals() else 'UNKNOWN',
                'year_month': year_month
            }
            
            # Add dates if we have complete date info
            if 'start_year' in locals() and 'start_month' in locals() and 'start_day' in locals():
                result['start_date'] = f"{start_year}-{start_month.zfill(2)}-{start_day.zfill(2)}"
            
            if 'end_year' in locals() and 'end_month' in locals() and 'end_day' in locals():
                result['end_date'] = f"{end_year}-{end_month.zfill(2)}-{end_day.zfill(2)}"
            
            return result
                
        except Exception as e:
            logger.error(f"Error extracting date from filename {filename}: {e}")
            return None
    
    def get_actual_year_month_from_xle(self, file_info):
        """Read XLE file to determine the correct year-month folder based on actual data"""
        try:
            import tempfile
            from ..handlers.solinst_reader import SolinstReader
            
            if not self.service_account_handler or not self.service_account_handler.is_authenticated():
                logger.error("Service account handler not available for reading XLE file")
                return None
            
            # Download file to temporary location using service account
            logger.debug(f"Reading {file_info['name']} to determine correct month folder...")
            temp_file_path = self.service_account_handler.download_file(file_info['id'])
            if not temp_file_path:
                logger.error(f"Failed to download {file_info['name']} for analysis")
                return None
            
            try:
                # Read XLE file to get actual data
                reader = SolinstReader()
                df, metadata = reader.read_xle(Path(temp_file_path))
                
                # Get actual last date from data to determine folder
                if not df.empty and 'timestamp' in df.columns:
                    last_date = df['timestamp'].max()
                    # Use the last date to determine which month folder
                    year_month = last_date.strftime('%Y-%m')
                    logger.info(f"File {file_info['name']} belongs in {year_month} folder based on actual data")
                    return year_month
                else:
                    logger.warning(f"No data found in {file_info['name']}, falling back to filename parsing")
                    return self.extract_date_from_filename(file_info['name'])
                    
            finally:
                # Clean up temp file
                import os
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error reading actual dates from {file_info['name']}: {e}")
            # If anything fails, fall back to the parsed year_month
            return file_info.get('year_month')
    
    def generate_corrected_filename(self, file_info):
        """Generate corrected filename by reading actual XLE data"""
        try:
            import tempfile
            import io
            from ..handlers.solinst_reader import SolinstReader
            
            # Download file to memory
            logger.debug(f"Downloading {file_info['name']} to read actual dates...")
            request = self.drive_service.files().get_media(fileId=file_info['id'])
            file_content = io.BytesIO()
            
            # Use the media download functionality
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(suffix='.xle', delete=False) as tmp_file:
                tmp_file.write(file_content.read())
                tmp_path = tmp_file.name
            
            try:
                # Read XLE file to get actual data
                reader = SolinstReader()
                df, metadata = reader.read_xle(Path(tmp_path))
                
                # Get actual first and last dates from data
                if not df.empty and 'timestamp' in df.columns:
                    first_date = df['timestamp'].min()
                    last_date = df['timestamp'].max()
                    
                    # Get location from metadata (not from filename!)
                    location = metadata.location.strip()
                    
                    # Remove any problematic characters from location
                    location = location.replace(':', '').replace('/', '_').replace('\\', '_')
                    
                    # Format: Location_YYYY_MM_DD_To_YYYY_MM_DD.xle
                    # Using actual data dates, not the metadata start/stop times
                    new_filename = f"{location}_{first_date.strftime('%Y_%m_%d')}_To_{last_date.strftime('%Y_%m_%d')}.xle"
                    
                    logger.info(f"Generated new filename from metadata: {new_filename} (original: {file_info['name']})")
                    logger.debug(f"  Location from metadata: {metadata.location}")
                    logger.debug(f"  Data date range: {first_date} to {last_date}")
                    
                    return new_filename
                else:
                    logger.warning(f"No data found in {file_info['name']}, using original name")
                    return file_info['name']
                    
            finally:
                # Clean up temp file
                import os
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error generating corrected filename for {file_info['name']}: {e}")
            # If anything fails, return original filename
            return file_info['name']
    
    def scan_field_folder(self, folder_id):
        """Scan a field folder for XLE files"""
        try:
            xle_files = []
            
            logger.info(f"Starting scan of field folder: {folder_id}")
            
            # First test if we can access the folder at all
            try:
                folder_info = self.drive_service.files().get(fileId=folder_id, fields="name, id").execute()
                logger.info(f"Successfully accessed folder: {folder_info.get('name', 'Unknown')} (ID: {folder_id})")
            except Exception as e:
                logger.error(f"Cannot access folder {folder_id}: {e}")
                logger.error("Make sure the folder is shared with the service account: water-levels-monitoring@water-levels-monitoring-451921.iam.gserviceaccount.com")
                return []
            
            # Only search for XLE files in the main folder (not subfolders)
            query = f"'{folder_id}' in parents and name contains '.xle' and trashed=false"
            logger.debug(f"Searching for XLE files with query: {query}")
            
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)",
                pageSize=1000  # Ensure we get all files
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} XLE files in main folder {folder_id}")
            if files:
                for file in files:
                    logger.debug(f"  - {file['name']}")
            
            for file in files:
                date_info = self.extract_date_from_filename(file['name'])
                if date_info:
                    file_info = {
                        'id': file['id'],
                        'name': file['name'],
                        'modified_time': file['modifiedTime'],
                        'size': file.get('size', 0),
                        **date_info
                    }
                    xle_files.append(file_info)
            
            return xle_files
            
        except Exception as e:
            logger.error(f"Error scanning field folder {folder_id}: {e}")
            return []
    
    def copy_file_to_consolidated(self, file_info, target_folder):
        """Copy a file from field folder to consolidated folder with corrected filename (hybrid mode)"""
        try:
            # Always use shared drive mode - download and save to S: drive
            return self._download_and_save_to_shared_drive(file_info, target_folder)
            
        except Exception as e:
            logger.error(f"Error copying file {file_info['name']}: {e}")
            return None
    
    def get_or_create_archived_folder(self, source_folder_id):
        """Get or create an 'archived' folder in the source folder"""
        try:
            # Check if archived folder already exists
            query = f"'{source_folder_id}' in parents and name='archived' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(q=query, fields="files(id)").execute()
            folders = results.get('files', [])
            
            if folders:
                return folders[0]['id']
            
            # Create archived folder
            folder_metadata = {
                'name': 'archived',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [source_folder_id]
            }
            folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created 'archived' folder in {source_folder_id}")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error creating archived folder: {e}")
            return None
    
    def move_to_archived(self, file_id, source_folder_id, archived_folder_id):
        """Move a file to the archived folder"""
        try:
            # Move file from source folder to archived folder
            self.drive_service.files().update(
                fileId=file_id,
                addParents=archived_folder_id,
                removeParents=source_folder_id,
                fields='id, parents'
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error moving file to archived: {e}")
            return False
    
    def consolidate_solinst_data(self, progress_callback=None):
        """Main method to consolidate XLE files from SOLINST folder to SMOO"""
        try:
            logger.info("Starting SOLINST data consolidation to SMOO...")
            
            # Check service account authentication
            if not self.service_account_handler or not self.service_account_handler.is_authenticated():
                logger.error("Service account handler not available or not authenticated")
                return False
            
            # Check SOLINST folder access
            if not self.service_account_handler.check_folder_access():
                logger.error("SOLINST folder not accessible via service account")
                return False
            
            # Ensure SMOO destination folder exists
            if not self._get_shared_drive_consolidated_path():
                logger.error("SMOO destination path not configured")
                return False
            
            if progress_callback:
                progress_callback("Scanning SOLINST folder for XLE files...", 10)
            
            # Get all XLE files from SOLINST folder
            files = self.service_account_handler.list_xle_files()
            if not files:
                logger.info("No XLE files found in SOLINST folder")
                return True
            
            total_files = len(files)
            processed_files = 0
            monthly_folders = {}
            
            logger.info(f"Found {total_files} XLE files in SOLINST folder")
            
            if progress_callback:
                progress_callback(f"Found {total_files} XLE files to process...", 20)
            
            # Process each XLE file from SOLINST folder
            for i, file_info in enumerate(files):
                file_num = i + 1
                
                if progress_callback:
                    progress = 30 + int((i / total_files) * 60)
                    progress_callback(f"Processing file {file_num}/{total_files}: {file_info['name']}", progress)
                
                # Convert file_info format to match expected structure
                standardized_file_info = {
                    'id': file_info['id'],
                    'name': file_info['name'],
                    'modified_time': file_info.get('modifiedTime', ''),
                    'size': file_info.get('size', 0)
                }
                
                # Get actual year-month from XLE data
                actual_year_month = self.get_actual_year_month_from_xle(standardized_file_info)
                if not actual_year_month:
                    logger.warning(f"Could not determine year-month for {file_info['name']}, skipping")
                    processed_files += 1
                    continue
                
                # Get or create monthly folder on SMOO
                if actual_year_month not in monthly_folders:
                    if progress_callback:
                        progress_callback(f"Creating SMOO folder for {actual_year_month}...", progress)
                    monthly_folders[actual_year_month] = self._create_shared_drive_monthly_folder(actual_year_month)
                
                target_folder_path = monthly_folders[actual_year_month]
                if target_folder_path:
                    # Download from SOLINST and save to SMOO
                    if progress_callback:
                        progress_callback(f"Downloading {file_info['name']} to SMOO...", progress)
                    
                    saved_file_path = self._download_and_save_to_shared_drive(standardized_file_info, target_folder_path)
                    
                    if saved_file_path:
                        # Update metadata.json in SMOO folder
                        if progress_callback:
                            progress_callback(f"Updating SMOO metadata for {actual_year_month}...", progress)
                        
                        try:
                            metadata = {
                                'last_updated': datetime.now().isoformat(),
                                'files_processed': processed_files + 1,
                                'latest_file': os.path.basename(saved_file_path)
                            }
                            self._write_shared_drive_metadata(target_folder_path, metadata)
                            logger.debug(f"Updated metadata.json in SMOO {actual_year_month} folder")
                        except Exception as e:
                            logger.error(f"Failed to update SMOO metadata for {actual_year_month}: {e}")
                        
                        processed_files += 1
                        logger.info(f"Successfully processed {file_info['name']} to SMOO")
                    else:
                        logger.error(f"Failed to download {file_info['name']} to SMOO")
                else:
                    logger.error(f"Could not create SMOO folder for {actual_year_month}")
            
            # Final summary
            if progress_callback:
                progress_callback(f"Consolidation complete: {processed_files}/{total_files} files processed", 100)
            
            logger.info(f"SOLINST data consolidation completed: {processed_files}/{total_files} files processed")
            return processed_files > 0
            
        except Exception as e:
            logger.error(f"Error during SOLINST data consolidation: {e}")
            return False