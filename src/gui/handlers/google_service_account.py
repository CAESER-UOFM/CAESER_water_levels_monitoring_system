"""
Google Drive Service Account Handler for SOLINST folder access only.

This handler provides minimal Google Drive API access using service account authentication
specifically for monitoring and retrieving XLE files from the SOLINST folder.
It does NOT handle database storage operations - those are now handled by SMOO.
"""

import os
import logging
from pathlib import Path
import json
import tempfile
from typing import Optional, List, Dict, Tuple
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io

logger = logging.getLogger(__name__)

class GoogleServiceAccountHandler:
    """
    Handles Google Drive API access using service account credentials.
    Designed specifically for SOLINST folder monitoring and XLE file access.
    """
    
    def __init__(self, settings_handler=None):
        """Initialize the service account handler."""
        self.settings_handler = settings_handler
        self.service = None
        self.credentials = None
        self.authenticated = False
        self.solinst_folder_id = None
        
    def authenticate(self, service_account_key_path: str = None) -> bool:
        """
        Authenticate using service account credentials.
        
        Args:
            service_account_key_path: Path to service account JSON key file
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Get service account key path
            if not service_account_key_path:
                if self.settings_handler:
                    service_account_key_path = self.settings_handler.get_setting(
                        "service_account_key_file", ""
                    )
                
                if not service_account_key_path:
                    logger.error("No service account key path provided")
                    return False
            
            # Check if key file exists
            key_path = Path(service_account_key_path)
            if not key_path.exists():
                logger.warning(f"Service account key file not found at primary location: {service_account_key_path}")
                
                # Try fallback to local config directory
                if self.settings_handler and service_account_key_path.startswith("S:"):
                    logger.info("SMOO not accessible, trying local config directory...")
                    app_dir = Path(__file__).parent.parent.parent.parent
                    config_dir = app_dir / "config"
                    
                    # Look for any service account JSON file in local config
                    service_account_files = list(config_dir.glob("*service-account*.json"))
                    if not service_account_files:
                        service_account_files = [f for f in config_dir.glob("*.json") 
                                               if f.name != "settings.json" and not f.name.startswith("client_secret")]
                    
                    for potential_file in service_account_files:
                        try:
                            with open(potential_file, 'r') as f:
                                data = json.load(f)
                                if data.get('type') == 'service_account':
                                    logger.info(f"Found local service account file: {potential_file}")
                                    service_account_key_path = str(potential_file)
                                    key_path = potential_file
                                    break
                        except:
                            continue
                    else:
                        logger.error("No valid service account key file found in local config either")
                        return False
                else:
                    logger.error(f"Service account key file not found: {service_account_key_path}")
                    return False
            
            # Load service account credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_key_path,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            
            # Test the connection
            if self._test_connection():
                self.authenticated = True
                logger.info("Service account authentication successful")
                
                # Get SOLINST folder ID from settings
                if self.settings_handler:
                    self.solinst_folder_id = self.settings_handler.get_setting(
                        "google_drive_solinst_folder_id", ""
                    )
                    if self.solinst_folder_id:
                        logger.info(f"Using SOLINST folder ID: {self.solinst_folder_id}")
                    else:
                        logger.warning("SOLINST folder ID not configured in settings")
                
                return True
            else:
                logger.error("Service account authentication failed - connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during service account authentication: {e}")
            self.authenticated = False
            return False
    
    def _test_connection(self) -> bool:
        """Test the Google Drive API connection."""
        try:
            if not self.service:
                return False
                
            # Simple test - get user info about the service account
            about = self.service.about().get(fields="user").execute()
            logger.debug(f"Connected as service account: {about.get('user', {}).get('emailAddress', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_service(self):
        """Get the authenticated Google Drive service."""
        return self.service if self.authenticated else None
    
    def set_solinst_folder_id(self, folder_id: str):
        """Set the SOLINST folder ID to monitor."""
        self.solinst_folder_id = folder_id
        if self.settings_handler:
            self.settings_handler.set_setting("google_drive_solinst_folder_id", folder_id)
        logger.info(f"SOLINST folder ID set to: {folder_id}")
    
    def list_xle_files(self) -> List[Dict]:
        """
        List all XLE files in the SOLINST folder.
        
        Returns:
            List of file dictionaries with id, name, modifiedTime
        """
        if not self.authenticated or not self.solinst_folder_id:
            logger.error("Not authenticated or SOLINST folder ID not set")
            return []
        
        try:
            # Query for XLE files in the SOLINST folder
            query = f"'{self.solinst_folder_id}' in parents and trashed = false and fileExtension = 'xle'"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} XLE files in SOLINST folder")
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing XLE files: {e}")
            return []
    
    def download_file(self, file_id: str, destination_path: str = None) -> Optional[str]:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            destination_path: Local path to save file (optional - creates temp file if not provided)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        if not self.authenticated:
            logger.error("Not authenticated")
            return None
            
        try:
            # Create destination path if not provided
            if not destination_path:
                fd, destination_path = tempfile.mkstemp(suffix='.xle')
                os.close(fd)
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            
            with open(destination_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            logger.debug(f"Downloaded file {file_id} to {destination_path}")
            return destination_path
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary, or None if failed
        """
        if not self.authenticated:
            logger.error("Not authenticated")
            return None
            
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, modifiedTime, size, parents"
            ).execute()
            
            return file_metadata
            
        except Exception as e:
            logger.error(f"Error getting file metadata for {file_id}: {e}")
            return None
    
    def check_folder_access(self) -> bool:
        """
        Check if the SOLINST folder is accessible.
        
        Returns:
            True if folder is accessible, False otherwise
        """
        if not self.authenticated or not self.solinst_folder_id:
            return False
            
        try:
            # Try to get folder metadata
            folder_metadata = self.service.files().get(
                fileId=self.solinst_folder_id,
                fields="id, name, mimeType"
            ).execute()
            
            if folder_metadata.get('mimeType') == 'application/vnd.google-apps.folder':
                logger.info(f"SOLINST folder accessible: {folder_metadata.get('name')}")
                return True
            else:
                logger.error("SOLINST folder ID does not point to a folder")
                return False
                
        except Exception as e:
            logger.error(f"Error checking SOLINST folder access: {e}")
            return False
    
    def search_files_by_date_range(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Search for XLE files in the SOLINST folder within a date range.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            
        Returns:
            List of file dictionaries
        """
        if not self.authenticated or not self.solinst_folder_id:
            logger.error("Not authenticated or SOLINST folder ID not set")
            return []
        
        try:
            # Build query
            query = f"'{self.solinst_folder_id}' in parents and trashed = false and fileExtension = 'xle'"
            
            if start_date:
                query += f" and modifiedTime >= '{start_date}T00:00:00'"
            if end_date:
                query += f" and modifiedTime <= '{end_date}T23:59:59'"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} XLE files in date range {start_date} to {end_date}")
            
            return files
            
        except Exception as e:
            logger.error(f"Error searching files by date range: {e}")
            return []
    
    def is_authenticated(self) -> bool:
        """Check if the service account is authenticated."""
        return self.authenticated
    
    def get_folder_info(self) -> Optional[Dict]:
        """
        Get information about the SOLINST folder.
        
        Returns:
            Folder information dictionary, or None if failed
        """
        if not self.authenticated or not self.solinst_folder_id:
            return None
            
        try:
            folder_info = self.service.files().get(
                fileId=self.solinst_folder_id,
                fields="id, name, modifiedTime, parents"
            ).execute()
            
            return folder_info
            
        except Exception as e:
            logger.error(f"Error getting folder info: {e}")
            return None