import os
import logging
import tempfile
import shutil
from pathlib import Path
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
import json
from .google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)

class GoogleDriveDatabaseHandler:
    """
    Handles database operations with Google Drive.
    Allows downloading and uploading database files from/to Google Drive.
    """
    
    def __init__(self, settings_handler):
        """Initialize the Google Drive database handler."""
        self.settings_handler = settings_handler
        self.drive_service = GoogleDriveService.get_instance(settings_handler)
        self.local_db_path = None
        self.drive_db_id = None
        self.folder_id = None
        
    def authenticate(self):
        """Authenticate with Google Drive."""
        if self.drive_service.authenticate():
            # Set folder ID after successful authentication - explicitly use the database folder ID
            self.folder_id = self.settings_handler.get_setting("google_drive_folder_id", "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK")
            if not self.folder_id:
                logger.error("Google Drive folder ID not set")
                return False
            logger.info(f"Using Google Drive folder ID for database: {self.folder_id}")
            return True
        return False
    
    def find_database(self, db_name="CAESER_GENERAL.db"):
        """Find a database file in the Google Drive folder."""
        service = self.drive_service.get_service()
        if not service or not self.folder_id:
            logger.error("Not authenticated or folder ID not set")
            return None
            
        try:
            query = f"name = '{db_name}' and '{self.folder_id}' in parents and trashed = false"
            results = service.files().list(
                q=query,
                fields="files(id, name, modifiedTime)",
                spaces='drive'
            ).execute()
            
            files = results.get('files', [])
            if not files:
                logger.info(f"Database {db_name} not found in Google Drive")
                return None
                
            # Use the first file found
            self.drive_db_id = files[0]['id']
            return files[0]
            
        except Exception as e:
            logger.error(f"Error finding database: {e}")
            return None
    
    def download_database(self, db_name="CAESER_GENERAL.db", local_dir=None):
        """
        Download a database file from Google Drive.
        
        Args:
            db_name: Name of the database file
            local_dir: Local directory to save the file (defaults to app directory)
            
        Returns:
            Path to the downloaded file or None if failed
        """
        service = self.drive_service.get_service()
        if not service:
            if not self.authenticate():
                return None
            service = self.drive_service.get_service()
                
        try:
            # Find the database file
            db_file = self.find_database(db_name)
            if not db_file:
                return None
                
            # Determine local path with (drive) suffix
            if not local_dir:
                local_dir = self.settings_handler.get_setting("local_db_directory", str(Path.cwd()))
                
            # Add (drive) suffix to the filename
            db_name_parts = db_name.split('.')
            if len(db_name_parts) > 1:
                local_db_name = f"{db_name_parts[0]}_(drive).{db_name_parts[1]}"
            else:
                local_db_name = f"{db_name}_(drive)"
                
            local_path = Path(local_dir) / local_db_name
            
            # Download the file
            request = service.files().get_media(fileId=self.drive_db_id)
            
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            
            logger.info(f"Downloaded database to {local_path}")
            self.local_db_path = local_path
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading database: {e}")
            return None
    
    def upload_database(self, local_path=None):
        """
        Upload a database file to Google Drive.
        
        Args:
            local_path: Path to the local database file
            
        Returns:
            True if successful, False otherwise
        """
        service = self.drive_service.get_service()
        if not service:
            if not self.authenticate():
                return False
            service = self.drive_service.get_service()
                
        try:
            if not local_path and self.local_db_path:
                local_path = self.local_db_path
                
            if not local_path or not os.path.exists(local_path):
                logger.error("Local database file not found")
                return False
                
            # Check if file exists in Drive
            db_name = os.path.basename(local_path)
            db_file = self.find_database(db_name)
            
            if db_file:
                # Update existing file
                media = MediaFileUpload(local_path, resumable=True)
                service.files().update(
                    fileId=self.drive_db_id,
                    media_body=media
                ).execute()
                logger.info(f"Updated database {db_name} in Google Drive")
            else:
                # Create new file
                file_metadata = {
                    'name': db_name,
                    'parents': [self.folder_id]
                }
                media = MediaFileUpload(local_path, resumable=True)
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self.drive_db_id = file.get('id')
                logger.info(f"Created database {db_name} in Google Drive")
                
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database: {e}")
            return False
    
    def create_database(self, db_name="CAESER_GENERAL.db", local_dir=None):
        """
        Create a new empty database and upload it to Google Drive.
        
        Args:
            db_name: Name of the database file
            local_dir: Local directory to save the file (defaults to app directory)
            
        Returns:
            Path to the created file or None if failed
        """
        try:
            # Determine local path
            if not local_dir:
                local_dir = self.settings_handler.get_setting("local_db_directory", str(Path.cwd()))
                
            local_path = Path(local_dir) / db_name
            
            # Create empty database file
            with open(local_path, 'wb') as f:
                pass
                
            # Upload to Google Drive
            self.local_db_path = local_path
            if self.upload_database(local_path):
                return local_path
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            return None 