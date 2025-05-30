import os
import logging
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """
    Centralized service for Google Drive authentication and operations.
    Provides a single point of authentication for all Google Drive operations.
    """
    
    # If modifying these scopes, delete the token.json file
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
        self.token_path = Path.home() / '.water_levels' / 'token.json'
        self.credentials = None
        self.service = None
        self.authenticated = False
        
    def authenticate(self, force=False):
        """Authenticate with Google Drive and create a Drive API service instance."""
        # Check if auto-authentication is disabled via environment variable
        import os
        if os.environ.get('GOOGLE_DRIVE_NO_AUTO_AUTH') == '1' and not force:
            logger.debug("Auto-authentication disabled, skipping")
            self.authenticated = False
            return False
        
        # Only proceed with authentication if explicitly forced to or user-initiated
        if self.authenticated and not force:
            return True
            
        try:
            # Get the client secret path from settings
            client_secret_path = self.settings_handler.get_setting("google_drive_secret_path", "")
            
            # If the specified path doesn't exist, try to find a default one in the config directory
            if not client_secret_path or not os.path.exists(client_secret_path):
                logger.warning("Client secret file not found at specified path, looking for default")
                config_dir = Path.cwd() / "config"
                if config_dir.exists():
                    # Look for client_secret*.json files
                    secret_files = list(config_dir.glob("client_secret*.json"))
                    if secret_files:
                        client_secret_path = str(secret_files[0])
                        logger.info(f"Using default client secret file: {client_secret_path}")
                        # Update the setting for future use
                        self.settings_handler.set_setting("google_drive_secret_path", client_secret_path)
            
            # If we still don't have a valid client secret file, show an error
            if not client_secret_path or not os.path.exists(client_secret_path):
                logger.error("Client secret file not found or not specified")
                self.authenticated = False
                return False
                
            # Create directory for token if it doesn't exist
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            
            # Check if we have valid credentials
            token_valid = False
            if os.path.exists(self.token_path):
                try:
                    with open(self.token_path, 'r') as token_file:
                        try:
                            token_info = json.load(token_file)
                            self.credentials = Credentials.from_authorized_user_info(token_info, self.SCOPES)
                            token_valid = True
                        except json.JSONDecodeError:
                            logger.error("Invalid token file format, will re-authenticate")
                            os.remove(self.token_path)
                            self.credentials = None
                        except Exception as e:
                            logger.error(f"Error loading token: {e}")
                            os.remove(self.token_path)
                            self.credentials = None
                except Exception as e:
                    logger.error(f"Error opening token file: {e}")
                    # Try to remove the token file if it's causing issues
                    try:
                        os.remove(self.token_path)
                    except:
                        pass
                    self.credentials = None
            
            # If there are no valid credentials, let the user log in
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    try:
                        logger.debug("Refreshing expired token")
                        self.credentials.refresh(Request())
                        token_valid = True
                    except Exception as e:
                        logger.error(f"Error refreshing token: {e}")
                        self.credentials = None
                
                if not self.credentials or not self.credentials.valid:
                    logger.info("No valid credentials found, starting OAuth flow")
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            client_secret_path, self.SCOPES)
                        # This will open a browser window for the user to authenticate
                        self.credentials = flow.run_local_server(port=0)
                        token_valid = True
                    except Exception as e:
                        logger.error(f"Error during OAuth flow: {e}")
                        self.authenticated = False
                        return False
                
                # Save the credentials for the next run
                if token_valid:
                    try:
                        with open(self.token_path, 'w') as token:
                            token_json = self.credentials.to_json()
                            if isinstance(token_json, str):
                                token.write(token_json)
                            else:
                                token.write(json.dumps(token_json))
                            logger.debug("Saved new token to disk")
                    except Exception as e:
                        logger.error(f"Error saving token: {e}")
                        # Continue anyway, we have valid credentials in memory
            
            # Build the Drive service only if we have valid credentials
            if token_valid:
                self.service = build('drive', 'v3', credentials=self.credentials)
                self.authenticated = True
                logger.info("Successfully authenticated with Google Drive")
                return True
            else:
                logger.warning("Authentication failed - invalid or missing token")
                self.authenticated = False
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
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