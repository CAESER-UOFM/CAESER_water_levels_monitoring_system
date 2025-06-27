"""
Settings Persistence System for Recharge Analysis.
Provides database-backed storage for user settings, preferences, and method configurations.
"""

import logging
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import os
import numpy as np

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy data types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class SettingsPersistence:
    """
    Database-backed settings persistence for recharge analysis system.
    Stores user preferences, method settings, and application configuration.
    """
    
    def __init__(self, db_path=None):
        """
        Initialize settings persistence.
        
        Args:
            db_path: Path to settings database. If None, uses default location.
        """
        if db_path is None:
            # Use default location relative to current directory
            current_dir = Path(__file__).parent
            db_path = current_dir / "recharge_settings.db"
            
        self.db_path = str(db_path)
        self.connection = None
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize the settings database with required tables."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            
            cursor = self.connection.cursor()
            
            # Create user preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, preference_key)
                )
            """)
            
            # Create unified settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unified_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    settings_name TEXT DEFAULT 'default',
                    settings_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, settings_name)
                )
            """)
            
            # Create method configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS method_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    method_name TEXT NOT NULL,
                    config_name TEXT NOT NULL,
                    config_data TEXT NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, method_name, config_name)
                )
            """)
            
            # Create session history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    session_data TEXT NOT NULL,
                    session_type TEXT DEFAULT 'recharge_analysis',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.connection.commit()
            logger.info("Settings database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing settings database: {e}")
            raise
            
    def save_user_preference(self, key, value, user_id='default'):
        """
        Save a user preference.
        
        Args:
            key: Preference key (e.g., 'interface_mode', 'default_method')
            value: Preference value
            user_id: User identifier
        """
        try:
            cursor = self.connection.cursor()
            
            # Convert value to JSON string if not already string
            if not isinstance(value, str):
                value = json.dumps(value, cls=NumpyEncoder)
                
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (user_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, key, value))
            
            self.connection.commit()
            logger.debug(f"Saved user preference: {key} = {value}")
            
        except Exception as e:
            logger.error(f"Error saving user preference {key}: {e}")
            raise
            
    def get_user_preference(self, key, default=None, user_id='default'):
        """
        Get a user preference.
        
        Args:
            key: Preference key
            default: Default value if preference not found
            user_id: User identifier
            
        Returns:
            Preference value or default
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT preference_value FROM user_preferences
                WHERE user_id = ? AND preference_key = ?
            """, (user_id, key))
            
            result = cursor.fetchone()
            
            if result:
                value = result['preference_value']
                # Try to parse as JSON, fall back to string
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                return default
                
        except Exception as e:
            logger.error(f"Error getting user preference {key}: {e}")
            return default
            
    def save_unified_settings(self, settings, name='default', user_id='default'):
        """
        Save unified settings configuration.
        
        Args:
            settings: Dictionary of settings
            name: Settings configuration name
            user_id: User identifier
        """
        try:
            cursor = self.connection.cursor()
            
            settings_json = json.dumps(settings, indent=2, cls=NumpyEncoder)
            
            cursor.execute("""
                INSERT OR REPLACE INTO unified_settings
                (user_id, settings_name, settings_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, name, settings_json))
            
            self.connection.commit()
            logger.info(f"Saved unified settings configuration: {name}")
            
        except Exception as e:
            logger.error(f"Error saving unified settings {name}: {e}")
            raise
            
    def get_unified_settings(self, name='default', user_id='default'):
        """
        Get unified settings configuration.
        
        Args:
            name: Settings configuration name
            user_id: User identifier
            
        Returns:
            Dictionary of settings or None if not found
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT settings_data FROM unified_settings
                WHERE user_id = ? AND settings_name = ?
            """, (user_id, name))
            
            result = cursor.fetchone()
            
            if result:
                return json.loads(result['settings_data'])
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting unified settings {name}: {e}")
            return None
            
    def list_unified_settings(self, user_id='default'):
        """
        List all unified settings configurations for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of setting configuration names
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT settings_name, updated_at FROM unified_settings
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
            
            return [{'name': row['settings_name'], 'updated_at': row['updated_at']} 
                   for row in cursor.fetchall()]
                   
        except Exception as e:
            logger.error(f"Error listing unified settings: {e}")
            return []
            
    def save_method_configuration(self, method_name, config_name, config_data, 
                                 is_default=False, user_id='default'):
        """
        Save method-specific configuration.
        
        Args:
            method_name: Name of the method (RISE, MRC, ERC)
            config_name: Configuration name
            config_data: Configuration dictionary
            is_default: Whether this is the default configuration
            user_id: User identifier
        """
        try:
            cursor = self.connection.cursor()
            
            # If setting as default, unset other defaults first
            if is_default:
                cursor.execute("""
                    UPDATE method_configurations 
                    SET is_default = FALSE
                    WHERE user_id = ? AND method_name = ?
                """, (user_id, method_name))
            
            config_json = json.dumps(config_data, indent=2, cls=NumpyEncoder)
            
            cursor.execute("""
                INSERT OR REPLACE INTO method_configurations
                (user_id, method_name, config_name, config_data, is_default, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, method_name, config_name, config_json, is_default))
            
            self.connection.commit()
            logger.info(f"Saved {method_name} configuration: {config_name}")
            
        except Exception as e:
            logger.error(f"Error saving method configuration {method_name}/{config_name}: {e}")
            raise
            
    def get_method_configuration(self, method_name, config_name=None, user_id='default'):
        """
        Get method-specific configuration.
        
        Args:
            method_name: Name of the method
            config_name: Configuration name (if None, gets default)
            user_id: User identifier
            
        Returns:
            Configuration dictionary or None if not found
        """
        try:
            cursor = self.connection.cursor()
            
            if config_name:
                cursor.execute("""
                    SELECT config_data FROM method_configurations
                    WHERE user_id = ? AND method_name = ? AND config_name = ?
                """, (user_id, method_name, config_name))
            else:
                # Get default configuration
                cursor.execute("""
                    SELECT config_data FROM method_configurations
                    WHERE user_id = ? AND method_name = ? AND is_default = TRUE
                """, (user_id, method_name))
            
            result = cursor.fetchone()
            
            if result:
                return json.loads(result['config_data'])
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting method configuration {method_name}/{config_name}: {e}")
            return None
            
    def list_method_configurations(self, method_name, user_id='default'):
        """
        List all configurations for a method.
        
        Args:
            method_name: Name of the method
            user_id: User identifier
            
        Returns:
            List of configuration info dictionaries
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT config_name, is_default, updated_at FROM method_configurations
                WHERE user_id = ? AND method_name = ?
                ORDER BY is_default DESC, updated_at DESC
            """, (user_id, method_name))
            
            return [{'name': row['config_name'], 
                    'is_default': bool(row['is_default']),
                    'updated_at': row['updated_at']} 
                   for row in cursor.fetchall()]
                   
        except Exception as e:
            logger.error(f"Error listing method configurations for {method_name}: {e}")
            return []
            
    def save_session_history(self, session_data, session_type='recharge_analysis', user_id='default'):
        """
        Save session history for analysis recovery.
        
        Args:
            session_data: Dictionary containing session information
            session_type: Type of session
            user_id: User identifier
        """
        try:
            cursor = self.connection.cursor()
            
            session_json = json.dumps(session_data, indent=2, cls=NumpyEncoder)
            
            cursor.execute("""
                INSERT INTO session_history
                (user_id, session_data, session_type)
                VALUES (?, ?, ?)
            """, (user_id, session_json, session_type))
            
            self.connection.commit()
            
            # Clean up old sessions (keep last 50)
            cursor.execute("""
                DELETE FROM session_history
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM session_history
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT 50
                )
            """, (user_id, user_id))
            
            self.connection.commit()
            logger.debug(f"Saved session history: {session_type}")
            
        except Exception as e:
            logger.error(f"Error saving session history: {e}")
            
    def get_recent_sessions(self, limit=10, user_id='default'):
        """
        Get recent session history.
        
        Args:
            limit: Maximum number of sessions to return
            user_id: User identifier
            
        Returns:
            List of recent session dictionaries
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT session_data, session_type, created_at FROM session_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            sessions = []
            for row in cursor.fetchall():
                try:
                    session_data = json.loads(row['session_data'])
                    sessions.append({
                        'data': session_data,
                        'type': row['session_type'],
                        'created_at': row['created_at']
                    })
                except json.JSONDecodeError:
                    continue
                    
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return []
            
    def export_user_settings(self, user_id='default'):
        """
        Export all user settings to a dictionary.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing all user settings
        """
        try:
            export_data = {
                'user_id': user_id,
                'exported_at': datetime.now().isoformat(),
                'preferences': {},
                'unified_settings': {},
                'method_configurations': {}
            }
            
            cursor = self.connection.cursor()
            
            # Export preferences
            cursor.execute("""
                SELECT preference_key, preference_value FROM user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                try:
                    value = json.loads(row['preference_value'])
                except (json.JSONDecodeError, TypeError):
                    value = row['preference_value']
                export_data['preferences'][row['preference_key']] = value
                
            # Export unified settings
            cursor.execute("""
                SELECT settings_name, settings_data FROM unified_settings
                WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                export_data['unified_settings'][row['settings_name']] = json.loads(row['settings_data'])
                
            # Export method configurations
            cursor.execute("""
                SELECT method_name, config_name, config_data, is_default FROM method_configurations
                WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                method = row['method_name']
                if method not in export_data['method_configurations']:
                    export_data['method_configurations'][method] = {}
                    
                export_data['method_configurations'][method][row['config_name']] = {
                    'config': json.loads(row['config_data']),
                    'is_default': bool(row['is_default'])
                }
                
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting user settings: {e}")
            return None
            
    def import_user_settings(self, settings_data, user_id='default', overwrite=False):
        """
        Import user settings from a dictionary.
        
        Args:
            settings_data: Dictionary containing settings to import
            user_id: User identifier
            overwrite: Whether to overwrite existing settings
        """
        try:
            # Import preferences
            if 'preferences' in settings_data:
                for key, value in settings_data['preferences'].items():
                    if overwrite or self.get_user_preference(key, user_id=user_id) is None:
                        self.save_user_preference(key, value, user_id)
                        
            # Import unified settings
            if 'unified_settings' in settings_data:
                for name, settings in settings_data['unified_settings'].items():
                    if overwrite or self.get_unified_settings(name, user_id) is None:
                        self.save_unified_settings(settings, name, user_id)
                        
            # Import method configurations
            if 'method_configurations' in settings_data:
                for method_name, configs in settings_data['method_configurations'].items():
                    for config_name, config_info in configs.items():
                        existing = self.get_method_configuration(method_name, config_name, user_id)
                        if overwrite or existing is None:
                            self.save_method_configuration(
                                method_name, config_name, config_info['config'],
                                config_info.get('is_default', False), user_id
                            )
                            
            logger.info(f"Imported user settings for {user_id}")
            
        except Exception as e:
            logger.error(f"Error importing user settings: {e}")
            raise
            
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()