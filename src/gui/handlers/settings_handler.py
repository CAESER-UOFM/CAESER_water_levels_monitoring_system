import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SettingsHandler:
    """Handler for application settings"""
    
    def __init__(self, settings_file=None):
        """Initialize settings handler"""
        self.settings_file = settings_file or Path.home() / '.water_levels' / 'settings.json'
        self.settings = self._load_settings()
        
        # Set default settings if not already set
        self._set_default_settings()
        
    def _load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            else:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
                return {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}
    
    def _set_default_settings(self):
        """Set default settings if not already set"""
        # Find the default client secret file in the config directory
        default_secret_path = ""
        config_dir = Path.cwd() / "config"
        if config_dir.exists():
            # Look for client_secret*.json files
            secret_files = list(config_dir.glob("client_secret*.json"))
            if secret_files:
                default_secret_path = str(secret_files[0])
                logger.info(f"Found default client secret file: {default_secret_path}")
        
        # Find default service account file
        default_service_account_path = ""
        if config_dir.exists():
            service_account_files = [
                f for f in config_dir.glob("*.json")
                if not f.name.startswith("client_secret")
            ]
            # Check if any are service account files
            for file_path in service_account_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        if data.get('type') == 'service_account':
                            default_service_account_path = str(file_path)
                            logger.info(f"Found default service account file: {default_service_account_path}")
                            break
                except:
                    continue
        
        # Determine default database directory
        # Check if we're in an installation (has databases folder in current dir)
        databases_folder = Path.cwd() / "databases"
        if databases_folder.exists():
            default_db_directory = str(databases_folder)
            logger.info(f"Using installation databases folder: {default_db_directory}")
        else:
            # Fallback to current working directory
            default_db_directory = str(Path.cwd())
            logger.info(f"Using current working directory for databases: {default_db_directory}")
        
        defaults = {
            "local_db_directory": default_db_directory,
            "use_google_drive_db": True,
            "google_drive_auto_check": False,
            "google_drive_folder_id": "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK",  # Default CAESER folder ID for database
            "google_drive_xle_folder_id": "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW",  # Default folder ID for XLE files
            "google_drive_projects_folder_id": "",  # Folder ID for water_levels_monitoring/Projects
            "google_drive_secret_path": default_secret_path,  # Default client secret path (legacy OAuth)
            "service_account_key_path": default_service_account_path,  # Service account key path
            "transducer_watch_folder": str(Path.cwd()),  # Add transducer watch folder default
            "barologger_watch_folder": str(Path.cwd()),  # Add barologger watch folder default
            "water_level_watch_folder": str(Path.cwd()),  # Add water level watch folder default
            "field_data_folders": ["1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"],  # Field laptop Solinst folders (correct folder ID)
            "consolidated_field_data_folder": ""  # Will be set to water_levels_monitoring/FIELD_DATA_CONSOLIDATED
        }
        
        # Force update the folder ID if it's set to the wrong value
        if "google_drive_folder_id" in self.settings and self.settings["google_drive_folder_id"] == "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW":
            logger.warning("Correcting Google Drive folder ID from XLE folder to CAESER folder")
            self.settings["google_drive_folder_id"] = "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"
        
        # Force update local_db_directory if it's still pointing to old hardcoded paths
        if "local_db_directory" in self.settings:
            current_path = self.settings["local_db_directory"]
            # Check for specific old hardcoded path patterns (S: drive or network paths)
            old_path_indicators = ["S:/Water_Projects", "S:\\Water_Projects", "Water_Data_Series"]
            if any(indicator in current_path for indicator in old_path_indicators):
                logger.warning(f"Correcting local_db_directory from old hardcoded path: {current_path} -> {default_db_directory}")
                self.settings["local_db_directory"] = default_db_directory
                # Force save immediately to persist the correction
                self.save_settings()
        
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
                
        # Save settings if any defaults were set
        self.save_settings()
            
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
            
    def get_setting(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
        
    def set_setting(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        return self.save_settings()
        
    def reset_database_directory(self):
        """Reset database directory to installation default"""
        # Determine default database directory
        databases_folder = Path.cwd() / "databases"
        if databases_folder.exists():
            default_db_directory = str(databases_folder)
            logger.info(f"Resetting to installation databases folder: {default_db_directory}")
        else:
            default_db_directory = str(Path.cwd())
            logger.info(f"Resetting to current working directory: {default_db_directory}")
        
        self.settings["local_db_directory"] = default_db_directory
        self.save_settings()
        return default_db_directory 