# -*- coding: utf-8 -*-
"""
User migration script to convert users.json to database format.

This module provides functions to migrate user data from JSON file format
to the new database-based user management system.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .user_repository import UserRepository
from .password_manager import PasswordManager

logger = logging.getLogger(__name__)

class UserMigration:
    """
    Handles migration of user data from JSON to database format
    """
    
    def __init__(self, config_path: Path, db_path: Path):
        """
        Initialize the migration
        
        Args:
            config_path: Path to the config directory containing users.json
            db_path: Path to the database file
        """
        self.config_path = config_path
        self.db_path = db_path
        self.users_json_path = config_path / "users.json"
        self.backup_json_path = config_path / "users.json.backup"
        self.user_repository = UserRepository(db_path)
    
    def needs_migration(self) -> bool:
        """
        Check if migration is needed
        
        Returns:
            True if users.json exists and migration is needed
        """
        try:
            # Check if users.json exists
            if not self.users_json_path.exists():
                logger.info("No users.json found, migration not needed")
                return False
            
            # Check if users already exist in database
            user_count = self.user_repository.get_user_count()
            if user_count > 0:
                logger.info(f"Database already has {user_count} users, migration not needed")
                return False
            
            logger.info("Migration needed: users.json exists and database is empty")
            return True
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False
    
    def load_users_from_json(self) -> Optional[List[Dict]]:
        """
        Load users from the JSON file
        
        Returns:
            List of user dictionaries or None if error
        """
        try:
            with open(self.users_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', [])
            logger.info(f"Loaded {len(users)} users from {self.users_json_path}")
            return users
            
        except Exception as e:
            logger.error(f"Error loading users from JSON: {e}")
            return None
    
    def validate_user_data(self, users: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate user data before migration
        
        Args:
            users: List of user dictionaries
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        try:
            if not users:
                errors.append("No users found in JSON file")
                return False, errors
            
            usernames_seen = set()
            
            for i, user in enumerate(users):
                user_errors = []
                
                # Check required fields
                required_fields = ['username', 'password', 'display_name']
                for field in required_fields:
                    if field not in user or not user[field]:
                        user_errors.append(f"Missing or empty '{field}'")
                
                # Check for duplicate usernames
                username = user.get('username', '')
                if username in usernames_seen:
                    user_errors.append(f"Duplicate username '{username}'")
                else:
                    usernames_seen.add(username)
                
                # Add user-specific errors
                if user_errors:
                    errors.append(f"User {i+1} ({username}): {', '.join(user_errors)}")
            
            is_valid = len(errors) == 0
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"Error validating user data: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    def migrate_users_to_database(self, users: List[Dict]) -> Tuple[bool, str]:
        """
        Migrate users to database with password hashing
        
        Args:
            users: List of user dictionaries from JSON
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            migrated_count = 0
            errors = []
            
            for user in users:
                try:
                    # Hash the plain text password
                    password_hash, salt = PasswordManager.hash_password(user['password'])
                    
                    # Determine role (default to 'user' if not specified)
                    role = user.get('role', 'user')
                    
                    # Create user in database
                    success, message = self.user_repository.create_user(
                        username=user['username'],
                        password_hash=password_hash,
                        salt=salt,
                        display_name=user['display_name'],
                        role=role
                    )
                    
                    if success:
                        migrated_count += 1
                        logger.info(f"Migrated user: {user['username']}")
                    else:
                        errors.append(f"Failed to migrate {user['username']}: {message}")
                        
                except Exception as e:
                    errors.append(f"Error migrating user {user.get('username', 'unknown')}: {str(e)}")
            
            if errors:
                error_summary = f"Migration completed with errors. {migrated_count} users migrated successfully. Errors: {'; '.join(errors)}"
                logger.warning(error_summary)
                return migrated_count > 0, error_summary
            else:
                success_message = f"Successfully migrated {migrated_count} users to database"
                logger.info(success_message)
                return True, success_message
                
        except Exception as e:
            logger.error(f"Error during user migration: {e}")
            return False, f"Migration failed: {str(e)}"
    
    def backup_users_json(self) -> bool:
        """
        Create a backup of the users.json file
        
        Returns:
            True if backup successful, False otherwise
        """
        try:
            if self.users_json_path.exists():
                shutil.copy2(self.users_json_path, self.backup_json_path)
                logger.info(f"Created backup: {self.backup_json_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def remove_users_json(self) -> bool:
        """
        Remove the original users.json file after successful migration
        
        Returns:
            True if removal successful, False otherwise
        """
        try:
            if self.users_json_path.exists():
                self.users_json_path.unlink()
                logger.info(f"Removed original users.json file")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing users.json: {e}")
            return False
    
    def ensure_admin_user(self) -> bool:
        """
        Ensure there's at least one admin user in the system
        
        Returns:
            True if admin user exists or was created, False otherwise
        """
        try:
            # Check if admin user already exists
            if self.user_repository.has_admin_user():
                logger.info("Admin user already exists")
                return True
            
            # Create default admin user
            password_hash, salt = PasswordManager.hash_password("admin")
            
            success, message = self.user_repository.create_user(
                username="admin",
                password_hash=password_hash,
                salt=salt,
                display_name="Administrator",
                role="admin"
            )
            
            if success:
                logger.info("Created default admin user (username: admin, password: admin)")
                return True
            else:
                logger.error(f"Failed to create admin user: {message}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring admin user: {e}")
            return False
    
    def perform_migration(self) -> Tuple[bool, str]:
        """
        Perform the complete migration process
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info("Starting user migration process")
            
            # Check if migration is needed
            if not self.needs_migration():
                return True, "Migration not needed"
            
            # Load users from JSON
            users = self.load_users_from_json()
            if users is None:
                return False, "Failed to load users from JSON file"
            
            # Validate user data
            is_valid, validation_errors = self.validate_user_data(users)
            if not is_valid:
                error_message = f"User data validation failed: {'; '.join(validation_errors)}"
                logger.error(error_message)
                return False, error_message
            
            # Create backup
            if not self.backup_users_json():
                logger.warning("Failed to create backup, continuing anyway")
            
            # Migrate users to database
            success, message = self.migrate_users_to_database(users)
            if not success:
                return False, message
            
            # Ensure admin user exists
            if not self.ensure_admin_user():
                logger.warning("Failed to ensure admin user exists")
            
            # Remove original JSON file
            if not self.remove_users_json():
                logger.warning("Failed to remove original users.json file")
            
            final_message = f"Migration completed successfully. {message}"
            logger.info(final_message)
            return True, final_message
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False, f"Migration failed: {str(e)}"

def migrate_users(config_path: Path, db_path: Path) -> Tuple[bool, str]:
    """
    Convenience function to perform user migration
    
    Args:
        config_path: Path to config directory with users.json
        db_path: Path to database file
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    migration = UserMigration(config_path, db_path)
    return migration.perform_migration()