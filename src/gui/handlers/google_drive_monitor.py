import os
import logging
from pathlib import Path
import json
from datetime import datetime, timedelta
from googleapiclient.http import MediaIoBaseDownload
import io
import tempfile
from ..handlers.solinst_reader import SolinstReader
from .google_drive_service import GoogleDriveService
import pandas as pd

logger = logging.getLogger(__name__)

class GoogleDriveMonitor:
    """
    Monitors a Google Drive folder for XLE files, renames them based on metadata,
    and moves them to appropriate folders.
    """
    
    def __init__(self, folder_id=None, settings_handler=None):
        """Initialize the Google Drive monitor."""
        self.folder_id = folder_id
        self.settings_handler = settings_handler
        self.drive_service = GoogleDriveService.get_instance(settings_handler)
        self.solinst_reader = SolinstReader()
        self.all_folder_id = None
        self.runs_folder_id = None
        self.processed_files = set()  # Keep track of processed files
        
    def authenticate(self, client_secret_path=None):
        """Authenticate with Google Drive."""
        if self.drive_service.authenticate():
            # If folder_id is not set, try to get it from settings
            if not self.folder_id and self.settings_handler:
                # Use the XLE files folder ID instead of the database folder ID
                self.folder_id = self.settings_handler.get_setting("google_drive_xle_folder_id", "")
                if not self.folder_id:
                    # Fall back to the regular folder ID if XLE folder ID is not set
                    self.folder_id = self.settings_handler.get_setting("google_drive_folder_id", "")
                logger.info(f"Using Google Drive folder ID for XLE files: {self.folder_id}")
            return True
        return False
    
    def set_folder_id(self, folder_id):
        """Set the folder ID to monitor."""
        self.folder_id = folder_id
        
    def initialize_folders(self):
        """Initialize or create the 'all' and 'runs' folders in the main folder."""
        if not self.folder_id:
            logger.error("No folder ID available")
            return False
            
        service = self.drive_service.get_service()
        if not service:
            logger.error("No service available")
            return False
            
        try:
            # Check if 'all' folder exists
            query = f"name = 'all' and '{self.folder_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'"
            results = service.files().list(q=query, spaces='drive').execute()
            all_folders = results.get('files', [])
            
            if all_folders:
                self.all_folder_id = all_folders[0]['id']
                logger.info(f"Found existing 'all' folder: {self.all_folder_id}")
            else:
                # Create 'all' folder
                folder_metadata = {
                    'name': 'all',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [self.folder_id]
                }
                all_folder = service.files().create(body=folder_metadata, fields='id').execute()
                self.all_folder_id = all_folder.get('id')
                logger.info(f"Created 'all' folder: {self.all_folder_id}")
            
            # Check if 'runs' folder exists
            query = f"name = 'runs' and '{self.folder_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'"
            results = service.files().list(q=query, spaces='drive').execute()
            runs_folders = results.get('files', [])
            
            if runs_folders:
                self.runs_folder_id = runs_folders[0]['id']
                logger.info(f"Found existing 'runs' folder: {self.runs_folder_id}")
            else:
                # Create 'runs' folder
                folder_metadata = {
                    'name': 'runs',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [self.folder_id]
                }
                runs_folder = service.files().create(body=folder_metadata, fields='id').execute()
                self.runs_folder_id = runs_folder.get('id')
                logger.info(f"Created 'runs' folder: {self.runs_folder_id}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error initializing folders: {e}")
            return False
    
    def check_for_new_files(self, well_runs=None):
        """Check for new XLE files and organize them into appropriate run folders."""
        if not self.folder_id or not self.drive_service.get_service():
            logger.error("No folder ID or service available")
            return None
        
        try:
            # Initialize folders if needed
            if not self.initialize_folders():
                return None
            
            service = self.drive_service.get_service()
            
            # Get all XLE files in the main folder
            query = f"'{self.folder_id}' in parents and trashed = false and fileExtension = 'xle'"
            files = service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
            
            if not files:
                logger.info("No new XLE files found")
                return {}
            
            logger.info(f"Found {len(files)} XLE files to process")
            
            processed_files_dict = {}
            
            for file in files:
                if file['id'] in self.processed_files:
                    continue
                
                temp_file = self._download_file(file['id'])
                if not temp_file:
                    continue
                
                try:
                    # Read XLE file metadata and data
                    df, metadata = self.solinst_reader.read_xle(temp_file)
                    
                    # Add debug logging
                    logger.debug(f"DataFrame columns: {df.columns}")
                    logger.debug(f"DataFrame first few rows: \n{df.head()}")
                    
                    # Get actual start and end dates from the timestamp_utc column
                    if not df.empty:
                        actual_start = df['timestamp_utc'].min()
                        actual_end = df['timestamp_utc'].max()
                        logger.debug(f"Start: {actual_start}, End: {actual_end}")
                    else:
                        logger.warning(f"No data found in file {file['id']}")
                        continue
                    
                    # Generate new file name using actual dates
                    new_name = self._generate_file_name(metadata, actual_start, actual_end)
                    
                    # Move to 'all' folder with new name
                    service.files().update(
                        fileId=file['id'],
                        body={'name': new_name},
                        addParents=self.all_folder_id,
                        removeParents=self.folder_id,
                        fields='id, parents'
                    ).execute()
                    
                    # Process run folders using actual end date
                    start_month = actual_end.strftime("%Y_%m")
                    
                    folder_id = self.create_run_folder(start_month)  # This will get or create a single folder
                    if folder_id:
                        # Copy file to the folder
                        logger.info(f"Copying {new_name} to run folder {folder_id}")
                        service.files().copy(
                            fileId=file['id'],
                            body={
                                'name': new_name,
                                'parents': [folder_id]
                            }
                        ).execute()
                    
                    # Track processed file
                    location = metadata.location.strip().upper()
                    if location not in processed_files_dict:
                        processed_files_dict[location] = []
                    
                    processed_files_dict[location].append({
                        'file_name': new_name,
                        'start_date': actual_start,
                        'end_date': actual_end,
                        'file_id': file['id']
                    })
                    
                    self.processed_files.add(file['id'])
                    
                finally:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                    
            return processed_files_dict
            
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
            return None
    
    def _download_file(self, file_id):
        """Download a file from Google Drive to a temporary location."""
        service = self.drive_service.get_service()
        if not service:
            return None
            
        try:
            # Create a temporary file
            fd, temp_path = tempfile.mkstemp(suffix='.xle')
            os.close(fd)
            
            # Download the file
            request = service.files().get_media(fileId=file_id)
            with open(temp_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def _generate_file_name(self, metadata, actual_start, actual_end):
        """Generate a standardized file name based on metadata and actual data dates."""
        # Format: SERIALNUMBER_LOCATION_YYYY_MM_DD_To_YYYY_MM_DD.xle
        location = metadata.location.strip().upper()
        serial_number = metadata.serial_number.strip().upper()
        
        # Format start date from actual data
        start_year = actual_start.strftime("%Y")
        start_month = actual_start.strftime("%m")
        start_day = actual_start.strftime("%d")
        
        # Format end date from actual data
        end_year = actual_end.strftime("%Y")
        end_month = actual_end.strftime("%m")
        end_day = actual_end.strftime("%d")
        
        # If years are the same, only include year once
        if start_year == end_year:
            return f"{serial_number}_{location}_{start_year}_{start_month}_{start_day}_To_{end_month}_{end_day}.xle"
        else:
            return f"{serial_number}_{location}_{start_year}_{start_month}_{start_day}_To_{end_year}_{end_month}_{end_day}.xle"
    
    def create_run_folder(self, folder_name):
        """Get or create a folder in the runs directory"""
        try:
            # Look for folder in runs folder, explicitly check not trashed
            query = f"'{self.runs_folder_id}' in parents and name = '{folder_name}' and trashed = false"
            logger.debug(f"Looking for active folder '{folder_name}' in runs folder")
            
            results = self.drive_service.get_service().files().list(
                q=query, 
                spaces='drive',
                fields='files(id, name, trashed)',
                pageSize=1
            ).execute()
            
            if results.get('files'):
                folder = results['files'][0]
                if folder.get('trashed', False):
                    logger.warning(f"Found folder '{folder_name}' but it's in trash. Creating new one.")
                    # Fall through to create new folder
                else:
                    logger.info(f"Using existing folder: {folder_name}")
                    return folder['id']
            
            # Create new folder in runs folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.runs_folder_id]
            }
            
            folder = self.drive_service.get_service().files().create(
                body=file_metadata, 
                fields='id'
            ).execute()
            
            logger.info(f"Created new folder: {folder_name}")
            return folder['id']
            
        except Exception as e:
            logger.error(f"Error with run folder '{folder_name}': {e}")
            return None 