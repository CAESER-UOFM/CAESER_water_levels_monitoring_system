import os
import logging
import json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """
    Centralized service for Google Drive authentication and operations using Service Account.
    Provides automatic authentication without user interaction.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    _instance = None
    
    @classmethod
    def get_instance(cls, settings_handler=None):
        """Get or create the singleton instance of GoogleDriveService"""
        if cls._instance is None and settings_handler is not None:
            cls._instance = cls(settings_handler)
        return cls._instance
    
    def __init__(self, settings_handler):
        """Initialize the Google Drive service."""
        if GoogleDriveService._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
            
        self.settings_handler = settings_handler
        self.credentials = None
        self.service = None
        self.authenticated = False
        self.service_account_email = None
        
    def authenticate(self, force=False):
        """Authenticate with Google Drive using Service Account credentials."""
        # Only proceed with authentication if explicitly forced or not already authenticated
        if self.authenticated and not force:
            return True
            
        try:
            # Get the service account key file path from settings
            service_account_path = self.settings_handler.get_setting("service_account_key_path", "")
            logger.debug(f"DEBUG: service_account_key_path from settings: '{service_account_path}'")
            
            # If not set in settings, try to find the file in config directory
            if not service_account_path or not os.path.exists(service_account_path):
                logger.warning("DEBUG: Service account key not found in settings, searching config directory")
                config_dir = Path.cwd() / "config"
                logger.warning(f"DEBUG: Checking config directory: {config_dir}")
                logger.warning(f"DEBUG: Config directory exists: {config_dir.exists()}")
                
                if config_dir.exists():
                    # List all files in config directory for debugging
                    all_files = list(config_dir.glob("*"))
                    logger.warning(f"DEBUG: All files in config directory: {[f.name for f in all_files]}")
                    
                    # Look for service account JSON files (exclude client_secret files)
                    service_account_files = [
                        f for f in config_dir.glob("*.json") 
                        if not f.name.startswith("client_secret") and "service_account" in f.name.lower()
                    ]
                    logger.warning(f"DEBUG: Found explicit service account files: {[f.name for f in service_account_files]}")
                    
                    # If no explicit service account files, look for any JSON files that might be service accounts
                    if not service_account_files:
                        potential_files = [
                            f for f in config_dir.glob("*.json")
                            if not f.name.startswith("client_secret")
                        ]
                        logger.warning(f"DEBUG: Checking potential service account files: {[f.name for f in potential_files]}")
                        
                        # Check if any of these are service account files by looking at content
                        for file_path in potential_files:
                            try:
                                with open(file_path, 'r') as f:
                                    data = json.load(f)
                                    if data.get('type') == 'service_account':
                                        service_account_files.append(file_path)
                                        logger.warning(f"DEBUG: Found service account file by content: {file_path.name}")
                            except Exception as e:
                                logger.warning(f"DEBUG: Error checking file {file_path.name}: {e}")
                                continue
                    
                    if service_account_files:
                        service_account_path = str(service_account_files[0])
                        logger.warning(f"DEBUG: Using service account file: {service_account_path}")
                        # Update the setting for future use
                        self.settings_handler.set_setting("service_account_key_path", service_account_path)
                    else:
                        logger.warning("DEBUG: No service account files found in config directory")
            else:
                logger.warning(f"DEBUG: Using service account path from settings: {service_account_path}")
            
            # If we still don't have a valid service account file
            if not service_account_path or not os.path.exists(service_account_path):
                logger.error("DEBUG: Service account key file not found - authentication should fail")
                self.authenticated = False
                return False
            
            # Load service account credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=self.SCOPES
            )
            
            # Get service account email for logging
            with open(service_account_path, 'r') as f:
                service_account_info = json.load(f)
                self.service_account_email = service_account_info.get('client_email')
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.authenticated = True
            
            logger.info(f"Successfully authenticated with Google Drive using service account: {self.service_account_email}")
            return True
            
        except Exception as e:
            logger.error(f"Service account authentication error: {e}")
            self.authenticated = False
            return False
    
    def get_service(self):
        """
        Get the authenticated Google Drive service.
        
        Returns:
            The authenticated service or None if not authenticated
        """
        if not self.authenticated:
            if not self.authenticate():
                return None
        return self.service
        
    def get_service_account_email(self):
        """Get the service account email address"""
        return self.service_account_email