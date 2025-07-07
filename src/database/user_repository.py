# -*- coding: utf-8 -*-
"""
User repository for database operations.

This module provides the UserRepository class that serves as the main interface
for user-related database operations, wrapping the UserModel.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .models.user_model import UserModel

logger = logging.getLogger(__name__)

class UserRepository:
    """
    Repository class for user data operations.
    
    This class provides a high-level interface for user management operations,
    abstracting the underlying database model implementation.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize the UserRepository
        
        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path
        self._user_model = None
    
    @property
    def user_model(self) -> UserModel:
        """Lazy loading of UserModel"""
        if self._user_model is None:
            self._user_model = UserModel(self.db_path)
        return self._user_model
    
    def set_db_manager(self, db_manager):
        """Set the database manager reference"""
        if self._user_model:
            self._user_model.set_db_manager(db_manager)
    
    def create_user(self, username: str, password_hash: str, salt: str, 
                   display_name: str, role: str = 'user') -> Tuple[bool, str]:
        """
        Create a new user
        
        Args:
            username: Unique username
            password_hash: Hashed password
            salt: Password salt
            display_name: Human-readable display name
            role: User role (admin, user, etc.)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate inputs
            if not username or not username.strip():
                return False, "Username cannot be empty"
            
            if not password_hash or not salt:
                return False, "Password hash and salt are required"
            
            if not display_name or not display_name.strip():
                return False, "Display name cannot be empty"
            
            # Validate role
            valid_roles = ['admin', 'user', 'guest']
            if role not in valid_roles:
                return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            
            # Create user using model
            return self.user_model.create_user(
                username.strip(), 
                password_hash, 
                salt, 
                display_name.strip(), 
                role
            )
            
        except Exception as e:
            logger.error(f"Error in UserRepository.create_user: {e}")
            return False, f"Failed to create user: {str(e)}"
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username
        
        Args:
            username: Username to search for
            
        Returns:
            User dictionary or None if not found
        """
        try:
            if not username or not username.strip():
                return None
            
            return self.user_model.get_user_by_username(username.strip())
            
        except Exception as e:
            logger.error(f"Error in UserRepository.get_user_by_username: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Get user by ID
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User dictionary or None if not found
        """
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                return None
            
            return self.user_model.get_user_by_id(user_id)
            
        except Exception as e:
            logger.error(f"Error in UserRepository.get_user_by_id: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Update user information
        
        Args:
            user_id: User ID to update
            **kwargs: Fields to update
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                return False, "Invalid user ID"
            
            # Validate role if provided
            if 'role' in kwargs:
                valid_roles = ['admin', 'user', 'guest']
                if kwargs['role'] not in valid_roles:
                    return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            
            # Validate username if provided
            if 'username' in kwargs:
                username = kwargs['username']
                if not username or not username.strip():
                    return False, "Username cannot be empty"
                kwargs['username'] = username.strip()
            
            # Validate display_name if provided
            if 'display_name' in kwargs:
                display_name = kwargs['display_name']
                if not display_name or not display_name.strip():
                    return False, "Display name cannot be empty"
                kwargs['display_name'] = display_name.strip()
            
            return self.user_model.update_user(user_id, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in UserRepository.update_user: {e}")
            return False, f"Failed to update user: {str(e)}"
    
    def update_password(self, user_id: int, password_hash: str, salt: str) -> Tuple[bool, str]:
        """
        Update user password
        
        Args:
            user_id: User ID to update
            password_hash: New password hash
            salt: New password salt
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not password_hash or not salt:
                return False, "Password hash and salt are required"
            
            return self.user_model.update_user(
                user_id, 
                password_hash=password_hash, 
                salt=salt
            )
            
        except Exception as e:
            logger.error(f"Error in UserRepository.update_password: {e}")
            return False, f"Failed to update password: {str(e)}"
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID to update
            
        Returns:
            Success status
        """
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                return False
            
            return self.user_model.update_last_login(user_id)
            
        except Exception as e:
            logger.error(f"Error in UserRepository.update_last_login: {e}")
            return False
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete (deactivate) a user
        
        Args:
            user_id: User ID to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                return False, "Invalid user ID"
            
            return self.user_model.delete_user(user_id)
            
        except Exception as e:
            logger.error(f"Error in UserRepository.delete_user: {e}")
            return False, f"Failed to delete user: {str(e)}"
    
    def list_users(self, include_inactive: bool = False) -> List[Dict]:
        """
        List all users
        
        Args:
            include_inactive: Whether to include inactive users
            
        Returns:
            List of user dictionaries (without password info)
        """
        try:
            users = self.user_model.list_users(include_inactive)
            
            # Remove sensitive information from the response
            safe_users = []
            for user in users:
                safe_user = {k: v for k, v in user.items() 
                           if k not in ['password_hash', 'salt']}
                safe_users.append(safe_user)
            
            return safe_users
            
        except Exception as e:
            logger.error(f"Error in UserRepository.list_users: {e}")
            return []
    
    def get_user_count(self) -> int:
        """
        Get total number of active users
        
        Returns:
            Number of active users
        """
        try:
            return self.user_model.get_user_count()
            
        except Exception as e:
            logger.error(f"Error in UserRepository.get_user_count: {e}")
            return 0
    
    def username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if username already exists
        
        Args:
            username: Username to check
            exclude_id: User ID to exclude from check (for updates)
            
        Returns:
            True if username exists, False otherwise
        """
        try:
            if not username or not username.strip():
                return False
            
            return self.user_model.username_exists(username.strip(), exclude_id)
            
        except Exception as e:
            logger.error(f"Error in UserRepository.username_exists: {e}")
            return True  # Assume exists on error to prevent duplicates
    
    def authenticate_user(self, username: str, password_hash: str) -> Optional[Dict]:
        """
        Authenticate a user with username and password hash
        
        Args:
            username: Username to authenticate
            password_hash: Expected password hash
            
        Returns:
            User dictionary (without sensitive info) if authenticated, None otherwise
        """
        try:
            if not username or not password_hash:
                return None
            
            user = self.get_user_by_username(username)
            if not user:
                return None
            
            # Check if password hash matches
            if user['password_hash'] != password_hash:
                return None
            
            # Update last login
            self.update_last_login(user['id'])
            
            # Return user info without sensitive data
            safe_user = {k: v for k, v in user.items() 
                        if k not in ['password_hash', 'salt']}
            
            return safe_user
            
        except Exception as e:
            logger.error(f"Error in UserRepository.authenticate_user: {e}")
            return None
    
    def get_admin_users(self) -> List[Dict]:
        """
        Get all admin users
        
        Returns:
            List of admin users (without sensitive info)
        """
        try:
            all_users = self.list_users()
            return [user for user in all_users if user.get('role') == 'admin']
            
        except Exception as e:
            logger.error(f"Error in UserRepository.get_admin_users: {e}")
            return []
    
    def has_admin_user(self) -> bool:
        """
        Check if there's at least one admin user
        
        Returns:
            True if admin user exists, False otherwise
        """
        try:
            admin_users = self.get_admin_users()
            return len(admin_users) > 0
            
        except Exception as e:
            logger.error(f"Error in UserRepository.has_admin_user: {e}")
            return False