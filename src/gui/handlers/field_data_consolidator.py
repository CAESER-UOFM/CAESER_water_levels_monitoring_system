import logging
import os
import re
from datetime import datetime
from pathlib import Path
import json
import tempfile
import io

logger = logging.getLogger(__name__)

class FieldDataConsolidator:
    """Consolidates XLE files from multiple field data folders into organized structure"""
    
    def __init__(self, drive_service, settings_handler):
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        self.consolidated_folder_id = None
        
    def get_or_create_consolidated_folder(self):
        """Get or create the FIELD_DATA_CONSOLIDATED folder in water_levels_monitoring"""
        try:
            # Get main water_levels_monitoring folder
            main_folder_id = self.settings_handler.get_setting("google_drive_folder_id")
            if not main_folder_id:
                logger.error("Main Google Drive folder ID not configured")
                return None
            
            # Check if FIELD_DATA_CONSOLIDATED folder exists
            query = f"'{main_folder_id}' in parents and name='FIELD_DATA_CONSOLIDATED' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                self.consolidated_folder_id = folders[0]['id']
                logger.info(f"Found existing FIELD_DATA_CONSOLIDATED folder: {self.consolidated_folder_id}")
                
                # Update settings even for existing folder to ensure it's saved
                self.settings_handler.set_setting("consolidated_field_data_folder", self.consolidated_folder_id)
            else:
                # Create the folder
                folder_metadata = {
                    'name': 'FIELD_DATA_CONSOLIDATED',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [main_folder_id]
                }
                folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
                self.consolidated_folder_id = folder.get('id')
                logger.info(f"Created FIELD_DATA_CONSOLIDATED folder: {self.consolidated_folder_id}")
                
                # Update settings
                self.settings_handler.set_setting("consolidated_field_data_folder", self.consolidated_folder_id)
            
            return self.consolidated_folder_id
            
        except Exception as e:
            logger.error(f"Error getting/creating consolidated folder: {e}")
            return None
    
    def get_or_create_monthly_folder(self, year_month):
        """Get or create a monthly folder (e.g., '2025-01') in the consolidated folder"""
        try:
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
    
    def extract_date_from_filename(self, filename):
        """Extract date information from XLE filename"""
        try:
            # Pattern: Anything_YYYY_MM_DD_To_MM_DD.xle or Anything_YYYY_MM_DD_To_YYYY_MM_DD.xle
            # Examples: 
            # - 2197347_MAWT-SS222_2025_04_28_To_05_22.xle
            # - 2000606_WEATHER STATION_2025_03_26_To_04_30.xle
            # - 2181050_HA:A-013_2025_04_28_To_05_22.xle
            
            # Updated patterns to handle time component (HHMMSS)
            # Pattern 1: Full dates with times - Location_YYYY_MM_DD_HHMMSS_YYYY_MM_DD_HHMMSS.xle
            pattern_full_time = r'(.+?)_(\d{4})_(\d{2})_(\d{2})_(\d{6})_(\d{4})_(\d{2})_(\d{2})_(\d{6})\.xle'
            match = re.match(pattern_full_time, filename, re.IGNORECASE)
            
            if match:
                cae, start_year, start_month, start_day, start_time, end_year, end_month, end_day, end_time = match.groups()
                year_month = f"{end_year}-{end_month.zfill(2)}"
                logger.debug(f"Matched full pattern with time for {filename}")
            else:
                # Pattern 2: Full dates without times
                pattern_full = r'(.+?)_(\d{4})_(\d{2})_(\d{2})_To_(\d{4})_(\d{2})_(\d{2})\.xle'
                match = re.match(pattern_full, filename, re.IGNORECASE)
                
                if match:
                    cae, start_year, start_month, start_day, end_year, end_month, end_day = match.groups()
                    year_month = f"{end_year}-{end_month.zfill(2)}"
                else:
                    # Pattern 3: Abbreviated dates (without year in end date)
                    pattern_abbrev = r'(.+?)_(\d{4})_(\d{2})_(\d{2})_To_(\d{2})_(\d{2})\.xle'
                    match = re.match(pattern_abbrev, filename, re.IGNORECASE)
                    
                    if match:
                        cae, start_year, start_month, start_day, end_month, end_day = match.groups()
                        end_year = start_year
                        year_month = f"{end_year}-{end_month.zfill(2)}"
                    else:
                        logger.warning(f"Could not parse date from filename: {filename}")
                        return None
            
            return {
                'cae': cae.strip(),
                'start_date': f"{start_year}-{start_month.zfill(2)}-{start_day.zfill(2)}",
                'end_date': f"{end_year}-{end_month.zfill(2)}-{end_day.zfill(2)}",
                'year_month': year_month
            }
                
        except Exception as e:
            logger.error(f"Error extracting date from filename {filename}: {e}")
            return None
    
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
    
    def copy_file_to_consolidated(self, file_info, target_folder_id):
        """Copy a file from field folder to consolidated folder with corrected filename"""
        try:
            # Generate new filename based on actual data content
            new_filename = self.generate_corrected_filename(file_info)
            
            # Check if file already exists in target folder
            query = f"'{target_folder_id}' in parents and name='{new_filename}' and trashed=false"
            results = self.drive_service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
            existing_files = results.get('files', [])
            
            if existing_files:
                # File exists, check if it's newer
                existing_file = existing_files[0]
                existing_modified = datetime.fromisoformat(existing_file['modifiedTime'].replace('Z', '+00:00'))
                source_modified = datetime.fromisoformat(file_info['modified_time'].replace('Z', '+00:00'))
                
                if source_modified <= existing_modified:
                    logger.debug(f"File {new_filename} already up to date in consolidated folder")
                    return existing_file['id']
                else:
                    logger.info(f"Updating existing file {new_filename} with newer version")
                    # Delete old version
                    self.drive_service.files().delete(fileId=existing_file['id']).execute()
            
            # Copy the file with new name
            copy_metadata = {
                'name': new_filename,
                'parents': [target_folder_id]
            }
            
            copied_file = self.drive_service.files().copy(
                fileId=file_info['id'],
                body=copy_metadata,
                fields='id'
            ).execute()
            
            logger.info(f"Copied {file_info['name']} as {new_filename} to consolidated folder")
            return copied_file.get('id')
            
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
    
    def consolidate_field_data(self, progress_callback=None):
        """Main method to consolidate all field data"""
        try:
            logger.info("Starting field data consolidation...")
            
            # Get field data folders from settings
            field_folders = self.settings_handler.get_setting("field_data_folders", [])
            if not field_folders:
                logger.warning("No field data folders configured")
                return False
            
            # Ensure consolidated folder exists
            if not self.get_or_create_consolidated_folder():
                logger.error("Could not create consolidated folder")
                return False
            
            total_files = 0
            processed_files = 0
            monthly_folders = {}
            
            # First pass: scan all field folders to count files
            all_files = []
            field_folder_archives = {}  # Track archived folder for each field folder
            
            for i, folder_id in enumerate(field_folders):
                if progress_callback:
                    progress_callback(f"Scanning field folder {i+1}/{len(field_folders)}...", 
                                    int((i / len(field_folders)) * 30))
                
                files = self.scan_field_folder(folder_id)
                
                if progress_callback and len(files) > 0:
                    progress_callback(f"Found {len(files)} XLE files in folder {i+1}", 
                                    int((i / len(field_folders)) * 30))
                
                # Add source folder info to each file
                for file in files:
                    file['source_folder_id'] = folder_id
                
                all_files.extend(files)
                total_files += len(files)
                
                # Get or create archived folder for this field folder
                if len(files) > 0:
                    if progress_callback:
                        progress_callback(f"Creating archived folder for field folder {i+1}...", 
                                        int((i / len(field_folders)) * 30))
                    archived_folder_id = self.get_or_create_archived_folder(folder_id)
                    if archived_folder_id:
                        field_folder_archives[folder_id] = archived_folder_id
            
            logger.info(f"Found {total_files} total XLE files to process")
            
            # Second pass: organize and copy files
            for file_info in all_files:
                file_num = processed_files + 1
                
                if progress_callback:
                    progress = 30 + int((processed_files / total_files) * 60)
                    progress_callback(f"Processing file {file_num}/{total_files}: {file_info['name']}", progress)
                
                # Get or create monthly folder
                year_month = file_info['year_month']
                if year_month not in monthly_folders:
                    if progress_callback:
                        progress_callback(f"Creating folder for {year_month}...", progress)
                    monthly_folders[year_month] = self.get_or_create_monthly_folder(year_month)
                
                target_folder_id = monthly_folders[year_month]
                if target_folder_id:
                    # Copy file to consolidated folder
                    if progress_callback:
                        progress_callback(f"Reading {file_info['name']} to determine actual dates...", progress)
                    
                    copied_file_id = self.copy_file_to_consolidated(file_info, target_folder_id)
                    
                    if copied_file_id:
                        if progress_callback:
                            progress_callback(f"Moving {file_info['name']} to archived folder...", progress)
                        
                        # Move original file to archived folder
                        source_folder_id = file_info['source_folder_id']
                        archived_folder_id = field_folder_archives.get(source_folder_id)
                        
                        if archived_folder_id:
                            if self.move_to_archived(file_info['id'], source_folder_id, archived_folder_id):
                                logger.info(f"Moved {file_info['name']} to archived folder")
                                if progress_callback:
                                    progress_callback(f"✓ Completed {file_info['name']}", progress)
                            else:
                                logger.warning(f"Failed to move {file_info['name']} to archived folder")
                                if progress_callback:
                                    progress_callback(f"⚠ Warning: Could not archive {file_info['name']}", progress)
                
                processed_files += 1
            
            if progress_callback:
                summary = f"✓ Consolidation complete! Processed {processed_files} files into {len(monthly_folders)} monthly folders"
                progress_callback(summary, 100)
            
            logger.info(f"Field data consolidation completed. Processed {processed_files} files into {len(monthly_folders)} monthly folders")
            return True
            
        except Exception as e:
            logger.error(f"Error during field data consolidation: {e}")
            return False