import os
import logging
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """
    Centralized service for Google Drive authentication and operations using OAuth2.
    Provides user-based authentication with automatic token refresh.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    _instance = None
    
    @classmethod
    def get_instance(cls, settings_handler=None):
        """Get or create the singleton instance of GoogleDriveService"""
        if cls._instance is None and settings_handler is not None:
            cls._instance = cls(settings_handler)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for re-initialization)"""
        cls._instance = None
    
    def __init__(self, settings_handler):
        """Initialize the Google Drive service."""
        if GoogleDriveService._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
            
        self.settings_handler = settings_handler
        self.credentials = None
        self.service = None
        self.authenticated = False
        self.user_email = None
        
    def authenticate(self, force=False, interactive=True):
        """
        Authenticate with Google Drive using OAuth2 credentials.
        
        Args:
            force: Force re-authentication even if already authenticated
            interactive: If False, won't open browser - just checks for existing valid token
        """
        # Only proceed with authentication if explicitly forced or not already authenticated
        if self.authenticated and not force:
            return True
            
        try:
            # Get paths for OAuth files
            app_dir = Path(__file__).parent.parent.parent.parent
            config_dir = app_dir / "config"
            
            # Token file stores the user's access and refresh tokens
            token_path = config_dir / 'token_oauth.json'
            
            # Get the OAuth client secret file path from settings or use default
            client_secret_path = self.settings_handler.get_setting("oauth_client_secret_path", "")
            if not client_secret_path or not os.path.exists(client_secret_path):
                # Try to find OAuth client secret file in config directory
                client_secret_path = config_dir / 'client_secret_oauth.json'
                if not client_secret_path.exists():
                    # Look for any client_secret file
                    client_secret_files = list(config_dir.glob("client_secret*.json"))
                    if client_secret_files:
                        # Exclude old service account files
                        oauth_files = [f for f in client_secret_files if not self._is_service_account_file(f)]
                        if oauth_files:
                            client_secret_path = oauth_files[0]
                            logger.info(f"Found OAuth client secret file: {client_secret_path.name}")
                        else:
                            logger.error("No OAuth client secret file found in config directory")
                            self.authenticated = False
                            return False
                    else:
                        logger.error("No client secret files found in config directory")
                        self.authenticated = False
                        return False
            else:
                client_secret_path = Path(client_secret_path)
            
            # Update the setting for future use
            self.settings_handler.set_setting("oauth_client_secret_path", str(client_secret_path))
            
            # Check if token already exists
            if token_path.exists():
                self.credentials = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
                logger.debug("Found existing OAuth token")
            
            # If there are no (valid) credentials available
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("OAuth token expired, refreshing...")
                    try:
                        self.credentials.refresh(Request())
                        # Save the refreshed token
                        with open(token_path, 'w') as token:
                            token.write(self.credentials.to_json())
                        logger.info("OAuth token refreshed successfully")
                    except Exception as e:
                        logger.warning(f"Token refresh failed: {e}")
                        # If refresh fails and we're not interactive, return False
                        if not interactive:
                            self.authenticated = False
                            return False
                        # If interactive, we'll fall through to the OAuth flow below
                        self.credentials = None
                else:
                    # No valid token - need to authenticate
                    if not interactive:
                        logger.info("No valid OAuth token found and interactive=False")
                        self.authenticated = False
                        return False
                    
                    logger.info("No valid OAuth token found, starting authentication flow...")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(client_secret_path), self.SCOPES)
                    
                    # Run the OAuth flow - this will open a browser
                    logger.info("Opening browser for Google authentication...")
                    try:
                        self.credentials = flow.run_local_server(
                            port=0,
                            success_message='Authentication successful! You can close this window and return to the application.'
                        )
                    except Exception as e:
                        logger.error(f"OAuth flow error: {e}")
                        logger.error("Please ensure you have a web browser available and try again.")
                        self.authenticated = False
                        return False
                    
                    # Save the credentials for next run
                    with open(token_path, 'w') as token:
                        token.write(self.credentials.to_json())
                    logger.info(f"OAuth token saved to {token_path}")
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.authenticated = True
            
            # Get user info
            try:
                about = self.service.about().get(fields="user").execute()
                self.user_email = about.get('user', {}).get('emailAddress', 'Unknown')
                logger.info(f"Successfully authenticated with Google Drive as: {self.user_email}")
            except Exception as e:
                logger.warning(f"Could not retrieve user email: {e}")
                self.user_email = "Authenticated User"
            
            return True
            
        except Exception as e:
            logger.error(f"OAuth authentication error: {e}")
            self.authenticated = False
            return False
    
    def _is_service_account_file(self, file_path):
        """Check if a JSON file is a service account file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('type') == 'service_account'
        except:
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
        
    def get_user_email(self):
        """Get the authenticated user's email address"""
        return self.user_email
    
    def get_service_account_email(self):
        """Legacy method for compatibility - returns user email instead"""
        return self.get_user_email()
    
    def revoke_authentication(self):
        """Revoke the stored OAuth token"""
        try:
            # Get token path
            app_dir = Path(__file__).parent.parent.parent.parent
            token_path = app_dir / "config" / 'token_oauth.json'
            
            # Delete token file if it exists
            if token_path.exists():
                token_path.unlink()
                logger.info("OAuth token revoked successfully")
            
            # Reset authentication state
            self.credentials = None
            self.service = None
            self.authenticated = False
            self.user_email = None
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking OAuth token: {e}")
            return False