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
        
        defaults = {
            "local_db_directory": str(Path.cwd()),
            "use_google_drive_db": True,
            "default_db_name": "CAESER_GENERAL.db",
            "google_drive_auto_check": False,
            "google_drive_folder_id": "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK",  # Default CAESER folder ID for database
            "google_drive_xle_folder_id": "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW",  # Default folder ID for XLE files
            "google_drive_secret_path": default_secret_path,  # Default client secret path
            "transducer_watch_folder": str(Path.cwd()),  # Add transducer watch folder default
            "barologger_watch_folder": str(Path.cwd()),  # Add barologger watch folder default
            "water_level_watch_folder": str(Path.cwd())  # Add water level watch folder default
        }
        
        # Force update the folder ID if it's set to the wrong value
        if "google_drive_folder_id" in self.settings and self.settings["google_drive_folder_id"] == "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW":
            logger.warning("Correcting Google Drive folder ID from XLE folder to CAESER folder")
            self.settings["google_drive_folder_id"] = "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"
        
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