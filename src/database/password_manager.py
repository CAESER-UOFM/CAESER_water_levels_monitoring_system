# -*- coding: utf-8 -*-
"""
Password management utility for secure password hashing and verification.

This module provides the PasswordManager class for handling password security
operations using bcrypt hashing.
"""

import bcrypt
import secrets
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class PasswordManager:
    """
    Utility class for secure password management.
    
    Provides methods for hashing passwords with bcrypt, verifying passwords,
    and generating secure salts.
    """
    
    # Default bcrypt rounds (can be adjusted based on security requirements)
    DEFAULT_ROUNDS = 12
    
    @staticmethod
    def generate_salt() -> str:
        """
        Generate a cryptographically secure random salt
        
        Returns:
            Base64 encoded salt string
        """
        try:
            # Generate 32 bytes of random data
            salt_bytes = secrets.token_bytes(32)
            # Encode as base64 for storage
            import base64
            return base64.b64encode(salt_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating salt: {e}")
            raise
    
    @staticmethod
    def hash_password(password: str, salt: str = None, rounds: int = DEFAULT_ROUNDS) -> Tuple[str, str]:
        """
        Hash a password using bcrypt with optional salt
        
        Args:
            password: Plain text password to hash
            salt: Optional salt (if None, a new one will be generated)
            rounds: Number of bcrypt rounds (default: 12)
            
        Returns:
            Tuple of (password_hash, salt) both as strings
        """
        try:
            if not password:
                raise ValueError("Password cannot be empty")
            
            # Generate salt if not provided
            if salt is None:
                salt = PasswordManager.generate_salt()
            
            # Convert password to bytes
            password_bytes = password.encode('utf-8')
            
            # Decode salt from base64
            import base64
            salt_bytes = base64.b64decode(salt.encode('utf-8'))
            
            # Combine password and salt
            salted_password = password_bytes + salt_bytes
            
            # Generate bcrypt hash
            bcrypt_hash = bcrypt.hashpw(salted_password, bcrypt.gensalt(rounds=rounds))
            
            # Encode hash as base64 for storage
            password_hash = base64.b64encode(bcrypt_hash).decode('utf-8')
            
            return password_hash, salt
            
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """
        Verify a password against its hash and salt
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            salt: Stored salt
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            if not password or not password_hash or not salt:
                return False
            
            # Convert password to bytes
            password_bytes = password.encode('utf-8')
            
            # Decode salt and hash from base64
            import base64
            salt_bytes = base64.b64decode(salt.encode('utf-8'))
            stored_hash = base64.b64decode(password_hash.encode('utf-8'))
            
            # Combine password and salt
            salted_password = password_bytes + salt_bytes
            
            # Verify using bcrypt
            return bcrypt.checkpw(salted_password, stored_hash)
            
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def is_strong_password(password: str) -> Tuple[bool, str]:
        """
        Check if a password meets strength requirements
        
        Args:
            password: Password to check
            
        Returns:
            Tuple of (is_strong: bool, message: str)
        """
        try:
            if not password:
                return False, "Password cannot be empty"
            
            # Minimum length requirement
            if len(password) < 8:
                return False, "Password must be at least 8 characters long"
            
            # Check for different character types
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
            
            # Count character types present
            char_types = sum([has_upper, has_lower, has_digit, has_special])
            
            # Require at least 3 of 4 character types for strong password
            if char_types < 3:
                missing = []
                if not has_upper:
                    missing.append("uppercase letters")
                if not has_lower:
                    missing.append("lowercase letters")
                if not has_digit:
                    missing.append("numbers")
                if not has_special:
                    missing.append("special characters")
                
                return False, f"Password should include at least 3 of: {', '.join(missing)}"
            
            # Check for common weak patterns
            if password.lower() in ['password', '123456', 'qwerty', 'admin', 'user']:
                return False, "Password is too common"
            
            # Check for sequential patterns
            if any(password.lower().find(seq) != -1 for seq in ['123', 'abc', 'qwe']):
                return False, "Password contains sequential patterns"
            
            return True, "Password meets strength requirements"
            
        except Exception as e:
            logger.error(f"Error checking password strength: {e}")
            return False, "Error validating password"
    
    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """
        Generate a cryptographically secure random password
        
        Args:
            length: Length of password to generate (minimum 8)
            
        Returns:
            Generated password string
        """
        try:
            if length < 8:
                length = 8
            
            # Character sets for password generation
            uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            lowercase = "abcdefghijklmnopqrstuvwxyz"
            digits = "0123456789"
            special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            
            # Ensure at least one character from each set
            password_chars = [
                secrets.choice(uppercase),
                secrets.choice(lowercase),
                secrets.choice(digits),
                secrets.choice(special)
            ]
            
            # Fill remaining length with random characters from all sets
            all_chars = uppercase + lowercase + digits + special
            for _ in range(length - 4):
                password_chars.append(secrets.choice(all_chars))
            
            # Shuffle the password characters
            secrets.SystemRandom().shuffle(password_chars)
            
            return ''.join(password_chars)
            
        except Exception as e:
            logger.error(f"Error generating secure password: {e}")
            raise
    
    @staticmethod
    def hash_existing_password(plain_password: str) -> Tuple[str, str]:
        """
        Convenience method to hash an existing plain text password
        
        Args:
            plain_password: Plain text password
            
        Returns:
            Tuple of (password_hash, salt)
        """
        return PasswordManager.hash_password(plain_password)
    
    @staticmethod
    def migrate_plain_passwords(users_data: list) -> list:
        """
        Migrate a list of users with plain text passwords to hashed passwords
        
        Args:
            users_data: List of user dictionaries with 'password' field
            
        Returns:
            List of user dictionaries with 'password_hash' and 'salt' fields
        """
        try:
            migrated_users = []
            
            for user in users_data:
                if 'password' in user:
                    # Hash the plain text password
                    password_hash, salt = PasswordManager.hash_password(user['password'])
                    
                    # Create new user dict with hashed password
                    migrated_user = user.copy()
                    migrated_user['password_hash'] = password_hash
                    migrated_user['salt'] = salt
                    
                    # Remove plain text password
                    if 'password' in migrated_user:
                        del migrated_user['password']
                    
                    migrated_users.append(migrated_user)
                else:
                    # User already has hashed password
                    migrated_users.append(user)
            
            return migrated_users
            
        except Exception as e:
            logger.error(f"Error migrating plain passwords: {e}")
            raise