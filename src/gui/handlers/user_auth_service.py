import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import shutil

logger = logging.getLogger(__name__)

class UserAuthService:
    """
    Service for user authentication and management.
    Handles user login, verification, and management of user credentials stored in Google Drive.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, drive_service=None, settings_handler=None):
        """Get or create the singleton instance of UserAuthService"""
        if cls._instance is None and drive_service is not None and settings_handler is not None:
            cls._instance = cls(drive_service, settings_handler)
        return cls._instance
    
    def __init__(self, drive_service, settings_handler):
        """Initialize the user authentication service."""
        if UserAuthService._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
            
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        self.users_file_name = "water_levels_users.json"
        self.local_users_path = Path.home() / '.water_levels' / self.users_file_name
        self.users = {}
        self.current_user = None
        self.is_guest = False
        
    def initialize(self) -> bool:
        """
        Initialize the user authentication service.
        Creates a default users file with admin user if it doesn't exist.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Create directory for local users file if it doesn't exist
            os.makedirs(os.path.dirname(self.local_users_path), exist_ok=True)
            
            # Check if we have a local file
            if not os.path.exists(self.local_users_path):
                # Create default users file
                self._create_default_users_file()
                logger.info("Created default users file locally")
                # Load the default users we just created
                self._load_users()
            else:
                # Don't load users yet - we'll do it when needed
                logger.debug("Users file exists, will load when needed")
                self.users = {}
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing user authentication service: {e}")
            return False
    
    def _create_default_users_file(self):
        """Create a default users file with an admin user."""
        default_users = {
            "admin": {
                "password": "admin",  # Default password should be changed
                "name": "Administrator",
                "role": "admin"
            }
        }
        
        with open(self.local_users_path, 'w') as f:
            json.dump(default_users, f, indent=4)
    
    def _load_users(self):
        """Load users from the local users file."""
        try:
            if os.path.exists(self.local_users_path):
                with open(self.local_users_path, 'r') as f:
                    self.users = json.load(f)
                logger.debug(f"Loaded {len(self.users)} users from {self.local_users_path}")
            else:
                logger.warning(f"Users file not found at {self.local_users_path}")
                self.users = {}
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            self.users = {}
    
    def _save_users(self):
        """Save users to the local users file."""
        try:
            with open(self.local_users_path, 'w') as f:
                json.dump(self.users, f, indent=4)
            logger.debug(f"Saved {len(self.users)} users to {self.local_users_path}")
            
            # Upload to Google Drive if authenticated
            if self.drive_service.authenticated:
                self._upload_users_file()
            
            return True
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            return False
    
    def _find_users_file_id(self):
        """Find the ID of the users file in Google Drive."""
        try:
            service = self.drive_service.get_service()
            if not service:
                return None
                
            # Get the folder ID from settings
            folder_id = self.settings_handler.get_setting("google_drive_folder_id")
            if not folder_id:
                logger.warning("Google Drive folder ID not configured")
                return None
            
            # Search for the users file in the folder
            query = f"name='{self.users_file_name}' and '{folder_id}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            if items:
                return items[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error finding users file: {e}")
            return None
    
    def _download_users_file(self):
        """Download the users file from Google Drive."""
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.warning("Google Drive service not available for downloading users file")
                return False
                
            file_id = self._find_users_file_id()
            if not file_id:
                logger.info("Users file not found in Google Drive")
                return False
            
            # Create a backup of any existing file before proceeding
            if os.path.exists(self.local_users_path):
                backup_path = str(self.local_users_path) + ".backup"
                try:
                    shutil.copy2(self.local_users_path, backup_path)
                    logger.info(f"Created backup of users file at {backup_path}")
                except Exception as backup_error:
                    logger.error(f"Failed to create backup of users file: {backup_error}")
            
            try:
                request = service.files().get_media(fileId=file_id)
                file_handle = io.BytesIO()
                downloader = MediaIoBaseDownload(file_handle, request)
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                # Save the downloaded file
                with open(self.local_users_path, 'wb') as f:
                    f.write(file_handle.getvalue())
                
                logger.info(f"Downloaded users file to {self.local_users_path}")
                return True
            except Exception as download_error:
                logger.error(f"Error during download: {download_error}")
                # If we have a backup, restore it
                if os.path.exists(backup_path):
                    try:
                        shutil.copy2(backup_path, self.local_users_path)
                        logger.info(f"Restored users file from backup")
                    except Exception as restore_error:
                        logger.error(f"Failed to restore users file from backup: {restore_error}")
                return False
            
        except Exception as e:
            logger.error(f"Error downloading users file: {e}")
            return False
    
    def _upload_users_file(self):
        """Upload the users file to Google Drive."""
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.warning("Google Drive service not available for uploading users file")
                return False
                
            folder_id = self.settings_handler.get_setting("google_drive_folder_id")
            if not folder_id:
                logger.warning("Google Drive folder ID not configured")
                return False
            
            # Check if file already exists
            file_id = self._find_users_file_id()
            
            file_metadata = {
                'name': self.users_file_name,
                'mimeType': 'application/json'
            }
            
            media = MediaFileUpload(
                self.local_users_path,
                mimetype='application/json',
                resumable=True
            )
            
            try:
                if file_id:
                    # Update existing file
                    service.files().update(
                        fileId=file_id,
                        media_body=media
                    ).execute()
                    logger.info(f"Updated users file in Google Drive")
                else:
                    # Create new file
                    file_metadata['parents'] = [folder_id]
                    service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    logger.info(f"Created users file in Google Drive")
                
                return True
            except Exception as upload_error:
                logger.error(f"Error during upload: {upload_error}")
                # Check for authentication errors
                if "invalid_grant" in str(upload_error).lower() or "unauthorized" in str(upload_error).lower():
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        None,
                        "Authentication Error",
                        "Your Google Drive authentication has expired or is invalid.\n\n"
                        "Please go to Tools > Google Drive Settings and re-authenticate."
                    )
                return False
            
        except Exception as e:
            logger.error(f"Error uploading users file: {e}")
            return False
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: The username to authenticate
            password: The password to authenticate
            
        Returns:
            Tuple of (success, message)
        """
        # Load users if not already loaded
        if not self.users:
            self._load_users()
            
        # Ensure admin user exists
        if "admin" not in self.users:
            logger.warning("Admin user not found in users file, creating default admin user")
            self.users["admin"] = {
                "password": "admin",
                "name": "Administrator",
                "role": "admin"
            }
            self._save_users()
            
        if username not in self.users:
            return False, f"User {username} not found"
            
        if self.users[username]["password"] != password:
            return False, "Invalid password"
            
        self.current_user = username
        self.is_guest = False
        logger.info(f"User {username} logged in successfully")
        return True, "Login successful"
    
    def login_as_guest(self) -> Tuple[bool, str]:
        """
        Login as a guest user.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.current_user = None
            self.is_guest = True
            
            logger.info("Logged in as guest")
            return True, "Welcome, Guest"
            
        except Exception as e:
            logger.error(f"Error during guest login: {e}")
            return False, f"Login error: {str(e)}"
    
    def logout(self):
        """Log out the current user."""
        self.current_user = None
        self.is_guest = False
        logger.info("User logged out")
    
    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated."""
        return self.current_user is not None or self.is_guest
    
    def is_admin(self) -> bool:
        """Check if the current user is an admin."""
        if not self.current_user or self.is_guest:
            return False
        return self.users.get(self.current_user, {}).get("role") == "admin"
    
    def get_current_user_info(self) -> Dict:
        """Get information about the current user."""
        if self.is_guest:
            return {
                "username": "guest",
                "name": "Guest",
                "role": "guest"
            }
        elif self.current_user:
            user_info = self.users.get(self.current_user, {}).copy()
            user_info.pop("password", None)  # Remove password from the returned info
            user_info["username"] = self.current_user
            return user_info
        else:
            return {}
    
    def add_user(self, username: str, password: str, name: str, role: str) -> Tuple[bool, str]:
        """
        Add a new user.
        
        Args:
            username: The username for the new user
            password: The password for the new user
            name: The display name for the new user
            role: The role for the new user (admin or tech)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user already exists
            if username in self.users:
                return False, f"User {username} already exists"
            
            # Validate role
            if role not in ["admin", "tech"]:
                return False, f"Invalid role: {role}"
            
            # Add user
            self.users[username] = {
                "password": password,
                "name": name,
                "role": role
            }
            
            # Save users
            if self._save_users():
                logger.info(f"Added user {username}")
                return True, f"User {username} added successfully"
            else:
                return False, "Failed to save users"
            
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False, f"Error adding user: {str(e)}"
    
    def update_user(self, username: str, password: str = None, name: str = None, role: str = None) -> Tuple[bool, str]:
        """
        Update an existing user.
        
        Args:
            username: The username of the user to update
            password: The new password (optional)
            name: The new display name (optional)
            role: The new role (optional)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user exists
            if username not in self.users:
                return False, f"User {username} not found"
            
            # Update user
            if password:
                self.users[username]["password"] = password
            if name:
                self.users[username]["name"] = name
            if role and role in ["admin", "tech"]:
                self.users[username]["role"] = role
            
            # Save users
            if self._save_users():
                logger.info(f"Updated user {username}")
                return True, f"User {username} updated successfully"
            else:
                return False, "Failed to save users"
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False, f"Error updating user: {str(e)}"
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """
        Delete a user.
        
        Args:
            username: The username of the user to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user exists
            if username not in self.users:
                return False, f"User {username} not found"
            
            # Check if it's the last admin
            if self.users[username]["role"] == "admin":
                admin_count = sum(1 for user in self.users.values() if user["role"] == "admin")
                if admin_count <= 1:
                    return False, "Cannot delete the last admin user"
            
            # Delete user
            del self.users[username]
            
            # Save users
            if self._save_users():
                logger.info(f"Deleted user {username}")
                return True, f"User {username} deleted successfully"
            else:
                return False, "Failed to save users"
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, f"Error deleting user: {str(e)}"
    
    def get_all_users(self) -> List[Dict]:
        """
        Get a list of all users.
        
        Returns:
            List of user dictionaries
        """
        try:
            users_list = []
            for username, user_info in self.users.items():
                user_dict = user_info.copy()
                user_dict.pop("password", None)  # Remove password from the returned info
                user_dict["username"] = username
                users_list.append(user_dict)
            return users_list
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return [] 