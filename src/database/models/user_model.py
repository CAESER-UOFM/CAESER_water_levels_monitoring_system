# -*- coding: utf-8 -*-
"""
User model for database operations.

This module provides the UserModel class for managing user data in the database.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .base_model import BaseModel

logger = logging.getLogger(__name__)

class UserModel(BaseModel):
    """Model for managing user data in the database"""
    
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self.ensure_users_table()
    
    def ensure_users_table(self):
        """Ensure the users table exists with proper schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user',
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP NULL
                    )
                ''')
                
                # Create index for faster username lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_username 
                    ON users (username)
                ''')
                
                # Create index for active users
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_active 
                    ON users (is_active)
                ''')
                
                conn.commit()
                logger.info("Users table created/verified successfully")
                
        except Exception as e:
            logger.error(f"Error creating users table: {e}")
            raise
    
    def create_user(self, username: str, password_hash: str, salt: str, 
                   display_name: str, role: str = 'user') -> Tuple[bool, str]:
        """
        Create a new user in the database
        
        Args:
            username: Unique username
            password_hash: Hashed password
            salt: Password salt
            display_name: Human-readable display name
            role: User role (default: 'user')
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if username already exists
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                if cursor.fetchone():
                    return False, f"Username '{username}' already exists"
                
                # Insert new user
                cursor.execute('''
                    INSERT INTO users (username, password_hash, salt, display_name, role, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (username, password_hash, salt, display_name, role))
                
                conn.commit()
                user_id = cursor.lastrowid
                
                self.mark_modified()
                logger.info(f"Created user: {username} (ID: {user_id})")
                return True, f"User '{username}' created successfully"
                
        except Exception as e:
            logger.error(f"Error creating user '{username}': {e}")
            return False, str(e)
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username
        
        Args:
            username: Username to search for
            
        Returns:
            User dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, password_hash, salt, display_name, role, 
                           is_active, created_at, updated_at, last_login
                    FROM users 
                    WHERE username = ? AND is_active = 1
                ''', (username,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user '{username}': {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, password_hash, salt, display_name, role, 
                           is_active, created_at, updated_at, last_login
                    FROM users 
                    WHERE id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by ID '{user_id}': {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Update user information
        
        Args:
            user_id: User ID to update
            **kwargs: Fields to update (username, password_hash, salt, display_name, role, is_active)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            valid_fields = {'username', 'password_hash', 'salt', 'display_name', 'role', 'is_active'}
            update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
            
            if not update_fields:
                return False, "No valid fields to update"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False, f"User with ID {user_id} not found"
                
                # Check for username conflicts if updating username
                if 'username' in update_fields:
                    cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', 
                                 (update_fields['username'], user_id))
                    if cursor.fetchone():
                        return False, f"Username '{update_fields['username']}' already exists"
                
                # Build update query
                set_clause = ', '.join(f"{field} = ?" for field in update_fields.keys())
                set_clause += ', updated_at = CURRENT_TIMESTAMP'
                
                query = f'UPDATE users SET {set_clause} WHERE id = ?'
                values = list(update_fields.values()) + [user_id]
                
                cursor.execute(query, values)
                conn.commit()
                
                self.mark_modified()
                logger.info(f"Updated user ID {user_id}: {list(update_fields.keys())}")
                return True, f"User updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating user ID {user_id}: {e}")
            return False, str(e)
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID to update
            
        Returns:
            Success status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                
                self.mark_modified()
                return True
                
        except Exception as e:
            logger.error(f"Error updating last login for user ID {user_id}: {e}")
            return False
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Soft delete a user (set is_active to False)
        
        Args:
            user_id: User ID to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False, f"User with ID {user_id} not found"
                
                # Soft delete (deactivate)
                cursor.execute('''
                    UPDATE users 
                    SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                
                self.mark_modified()
                logger.info(f"Soft deleted user ID {user_id}: {user[0]}")
                return True, f"User '{user[0]}' deactivated successfully"
                
        except Exception as e:
            logger.error(f"Error deleting user ID {user_id}: {e}")
            return False, str(e)
    
    def list_users(self, include_inactive: bool = False) -> List[Dict]:
        """
        List all users
        
        Args:
            include_inactive: Whether to include inactive users
            
        Returns:
            List of user dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if include_inactive:
                    cursor.execute('''
                        SELECT id, username, display_name, role, is_active, 
                               created_at, updated_at, last_login
                        FROM users 
                        ORDER BY username
                    ''')
                else:
                    cursor.execute('''
                        SELECT id, username, display_name, role, is_active, 
                               created_at, updated_at, last_login
                        FROM users 
                        WHERE is_active = 1 
                        ORDER BY username
                    ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def get_user_count(self) -> int:
        """
        Get total number of active users
        
        Returns:
            Number of active users
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if exclude_id:
                    cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', 
                                 (username, exclude_id))
                else:
                    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Error checking username existence: {e}")
            return True  # Assume exists on error to prevent duplicates