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
from ...database.user_repository import UserRepository
from ...database.password_manager import PasswordManager

logger = logging.getLogger(__name__)

class UserAuthService:
    """
    Service for user authentication and management.
    Handles user login, verification, and management of user credentials using database storage.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, drive_service=None, settings_handler=None, db_path=None):
        """Get or create the singleton instance of UserAuthService"""
        if cls._instance is None and drive_service is not None and settings_handler is not None:
            cls._instance = cls(drive_service, settings_handler, db_path)
        return cls._instance
    
    def __init__(self, drive_service, settings_handler, db_path=None):
        """Initialize the user authentication service."""
        if UserAuthService._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
            
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        self.users_file_name = "water_levels_users.json"
        self.local_users_path = Path.home() / '.water_levels' / self.users_file_name
        self.current_user = None
        self.current_user_data = None
        self.is_guest = False
        
        # Database components
        if db_path:
            self.user_repository = UserRepository(Path(db_path))
        else:
            # Fallback to default users database
            config_dir = Path(__file__).parent.parent.parent.parent / "config"
            users_db_path = config_dir / "users.db"
            self.user_repository = UserRepository(users_db_path)
        
    def initialize(self) -> bool:
        """
        Initialize the user authentication service.
        Always ensures admin/admin user exists.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Creating/verifying admin user...")
            
            # Always try to create admin user - if it exists, it will just fail gracefully
            password_hash, salt = PasswordManager.hash_password("admin")
            success, message = self.user_repository.create_user(
                username="admin",
                password_hash=password_hash,
                salt=salt,
                display_name="Administrator",
                role="admin"
            )
            
            if success:
                logger.info("Created admin user (username: admin, password: admin)")
            else:
                # Check if it failed because user already exists
                existing_user = self.user_repository.get_user_by_username("admin")
                if existing_user:
                    logger.info("Admin user already exists")
                else:
                    logger.error(f"Failed to create admin user: {message}")
                    return False
            
            # Verify admin user exists
            admin_user = self.user_repository.get_user_by_username("admin")
            if admin_user:
                logger.info("Admin user verified - login should work with admin/admin")
                return True
            else:
                logger.error("Admin user verification failed")
                return False
            
        except Exception as e:
            logger.error(f"Error initializing user authentication service: {e}")
            return False
    
    def _legacy_create_default_users_file(self):
        """Legacy method - kept for potential fallback scenarios."""
        default_users = {
            "admin": {
                "password": "admin",
                "name": "Administrator",
                "role": "admin"
            }
        }
        
        with open(self.local_users_path, 'w') as f:
            json.dump(default_users, f, indent=4)
    
    def _save_users_backup(self):
        """Legacy method - kept for Google Drive sync compatibility."""
        try:
            # Create a backup JSON for Google Drive sync if needed
            users_list = self.user_repository.list_users()
            users_dict = {}
            for user in users_list:
                users_dict[user['username']] = {
                    'name': user['display_name'],
                    'role': user['role'],
                    'password': '[ENCRYPTED]'  # Don't expose real passwords
                }
            
            with open(self.local_users_path, 'w') as f:
                json.dump(users_dict, f, indent=4)
            logger.debug(f"Saved {len(users_dict)} users backup to {self.local_users_path}")
            
            # Upload to Google Drive if authenticated
            if self.drive_service.authenticated:
                self._upload_users_file()
            
            return True
        except Exception as e:
            logger.error(f"Error saving users backup: {e}")
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
        try:
            if not username or not password:
                return False, "Username and password are required"
            
            # Get user from database
            user = self.user_repository.get_user_by_username(username)
            if not user:
                logger.warning(f"Login attempt for non-existent user: {username}")
                return False, "Invalid username or password"
            
            # Verify password
            if not PasswordManager.verify_password(password, user['password_hash'], user['salt']):
                logger.warning(f"Invalid password for user: {username}")
                return False, "Invalid username or password"
            
            # Update last login
            self.user_repository.update_last_login(user['id'])
            
            # Set current user
            self.current_user = username
            self.current_user_data = user
            self.is_guest = False
            
            logger.info(f"User {username} logged in successfully")
            return True, "Login successful"
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False, "Login failed due to system error"
    
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
        if self.current_user:
            logger.info(f"User {self.current_user} logged out")
        self.current_user = None
        self.current_user_data = None
        self.is_guest = False
    
    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated."""
        return self.current_user is not None or self.is_guest
    
    def is_admin(self) -> bool:
        """Check if the current user is an admin."""
        if not self.current_user or self.is_guest or not self.current_user_data:
            return False
        return self.current_user_data.get("role") == "admin"
    
    def get_current_user_info(self) -> Dict:
        """Get information about the current user."""
        if self.is_guest:
            return {
                "username": "guest",
                "display_name": "Guest",
                "role": "guest"
            }
        elif self.current_user and self.current_user_data:
            user_info = self.current_user_data.copy()
            # Remove sensitive information
            user_info.pop("password_hash", None)
            user_info.pop("salt", None)
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
            role: The role for the new user (admin, user, guest)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate password strength
            is_strong, strength_message = PasswordManager.is_strong_password(password)
            if not is_strong:
                return False, f"Password too weak: {strength_message}"
            
            # Hash password
            password_hash, salt = PasswordManager.hash_password(password)
            
            # Create user in database
            success, message = self.user_repository.create_user(
                username=username,
                password_hash=password_hash,
                salt=salt,
                display_name=name,
                role=role
            )
            
            if success:
                logger.info(f"Added user {username}")
            
            return success, message
            
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
            # Get user from database
            user = self.user_repository.get_user_by_username(username)
            if not user:
                return False, f"User {username} not found"
            
            update_data = {}
            
            # Update password if provided
            if password:
                # Validate password strength
                is_strong, strength_message = PasswordManager.is_strong_password(password)
                if not is_strong:
                    return False, f"Password too weak: {strength_message}"
                
                # Hash new password
                password_hash, salt = PasswordManager.hash_password(password)
                update_data['password_hash'] = password_hash
                update_data['salt'] = salt
            
            # Update display name if provided
            if name:
                update_data['display_name'] = name
            
            # Update role if provided
            if role:
                update_data['role'] = role
            
            if not update_data:
                return False, "No updates provided"
            
            # Update user in database
            success, message = self.user_repository.update_user(user['id'], **update_data)
            
            if success:
                logger.info(f"Updated user {username}")
                # Update current user data if it's the same user
                if self.current_user == username:
                    self.current_user_data = self.user_repository.get_user_by_username(username)
            
            return success, message
            
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
            # Get user from database
            user = self.user_repository.get_user_by_username(username)
            if not user:
                return False, f"User {username} not found"
            
            # Check if it's the last admin
            if user["role"] == "admin":
                admin_users = self.user_repository.get_admin_users()
                if len(admin_users) <= 1:
                    return False, "Cannot delete the last admin user"
            
            # Check if user is currently logged in
            if self.current_user == username:
                return False, "Cannot delete currently logged in user"
            
            # Delete user from database
            success, message = self.user_repository.delete_user(user['id'])
            
            if success:
                logger.info(f"Deleted user {username}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, f"Error deleting user: {str(e)}"
    
    def get_all_users(self) -> List[Dict]:
        """
        Get a list of all users.
        
        Returns:
            List of user dictionaries (without sensitive info)
        """
        try:
            return self.user_repository.list_users()
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return [] 