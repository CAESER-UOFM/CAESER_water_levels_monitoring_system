"""
Shared Drive Updater for Water Level Monitoring Application
Handles updates from a shared network drive within the organization.
"""

import os
import json
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ...config.paths import DefaultPaths

logger = logging.getLogger(__name__)

class SharedDriveUpdater:
    """Handles updates from a shared network drive"""
    
    def __init__(self, app_root: Path, shared_drive_path: str = None):
        """
        Initialize shared drive updater
        
        Args:
            app_root: Root directory of the application
            shared_drive_path: Path to shared network drive (placeholder for now)
        """
        self.app_root = Path(app_root)
        self.current_version_file = self.app_root / "version.json"
        
        # Use centralized path configuration
        self.shared_drive_path = shared_drive_path or DefaultPaths.SHARED_DRIVE_BASE
        self.shared_version_file = Path(self.shared_drive_path) / "version.json"
        self.shared_src_folder = Path(self.shared_drive_path) / "src"
        
        # Load current version
        self.current_version = self._load_current_version()
        
    def _load_current_version(self) -> str:
        """Load current application version from version.json"""
        try:
            if self.current_version_file.exists():
                with open(self.current_version_file, 'r') as f:
                    version_data = json.load(f)
                    return version_data.get('version', '0.0.0-unknown')
            else:
                logger.warning("No version.json file found")
                return '0.0.0-unknown'
        except Exception as e:
            logger.error(f"Error loading current version: {e}")
            return '0.0.0-unknown'
    
    def check_shared_drive_access(self) -> bool:
        """
        Check if the shared drive is accessible
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            logger.error(f"DEBUG: check_shared_drive_access() called with path: {self.shared_drive_path}")
            shared_path = Path(self.shared_drive_path)
            
            # Check if path exists and is accessible
            if not shared_path.exists():
                logger.error(f"DEBUG: Path does not exist: {self.shared_drive_path}")
                logger.debug(f"Shared drive path does not exist: {self.shared_drive_path}")
                return False
            
            if not shared_path.is_dir():
                logger.error(f"DEBUG: Path is not a directory: {self.shared_drive_path}")
                logger.debug(f"Shared drive path is not a directory: {self.shared_drive_path}")
                return False
            
            # Try to list contents to verify read access
            list(shared_path.iterdir())
            
            # Check if version file exists
            if not self.shared_version_file.exists():
                logger.error(f"DEBUG: Version file missing: {self.shared_version_file}")
                logger.debug(f"Version file not found in shared drive: {self.shared_version_file}")
                return False
            
            logger.error(f"DEBUG: All checks passed for: {self.shared_drive_path}")
            logger.info(f"Shared drive access confirmed: {self.shared_drive_path}")
            return True
            
        except (PermissionError, OSError, IOError) as e:
            logger.debug(f"Shared drive access failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking shared drive access: {e}")
            return False
    
    def get_shared_version_info(self) -> Optional[Dict]:
        """
        Get version information from shared drive
        
        Returns:
            Dictionary with version info or None if error
        """
        try:
            if not self.check_shared_drive_access():
                return None
            
            with open(self.shared_version_file, 'r') as f:
                version_data = json.load(f)
            
            logger.info(f"Shared drive version info loaded: {version_data.get('version')}")
            return version_data
            
        except Exception as e:
            logger.error(f"Error loading shared version info: {e}")
            return None
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings
        
        Args:
            version1: First version string (e.g., "1.0.0")
            version2: Second version string (e.g., "1.1.0")
        
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        try:
            # Handle development versions
            v1_clean = version1.replace('-dev', '').replace('-beta', '').replace('-alpha', '')
            v2_clean = version2.replace('-dev', '').replace('-beta', '').replace('-alpha', '')
            
            # Split into parts and convert to integers
            v1_parts = [int(x) for x in v1_clean.split('.')]
            v2_parts = [int(x) for x in v2_clean.split('.')]
            
            # Pad shorter version with zeros
            max_length = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_length - len(v1_parts)))
            v2_parts.extend([0] * (max_length - len(v2_parts)))
            
            # Compare parts
            for v1_part, v2_part in zip(v1_parts, v2_parts):
                if v1_part < v2_part:
                    return -1
                elif v1_part > v2_part:
                    return 1
            
            return 0
            
        except Exception as e:
            logger.error(f"Error comparing versions {version1} and {version2}: {e}")
            return 0  # Assume equal if comparison fails
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Check if updates are available on shared drive
        
        Returns:
            Dictionary with update info or None if no updates/error
        """
        try:
            # Check shared drive access
            if not self.check_shared_drive_access():
                logger.info("Shared drive not accessible - skipping update check")
                return None
            
            # Get shared version info
            shared_version_info = self.get_shared_version_info()
            if not shared_version_info:
                logger.warning("Could not get shared version info")
                return None
            
            shared_version = shared_version_info.get('version', '0.0.0')
            
            # Compare versions
            comparison = self.compare_versions(self.current_version, shared_version)
            
            if comparison < 0:  # Current version is older
                logger.info(f"Update available: {self.current_version} -> {shared_version}")
                return {
                    'current_version': self.current_version,
                    'new_version': shared_version,
                    'release_date': shared_version_info.get('release_date', 'Unknown'),
                    'description': shared_version_info.get('description', 'No description available'),
                    'shared_path': self.shared_drive_path
                }
            else:
                logger.info(f"No updates available. Current: {self.current_version}, Shared: {shared_version}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None
    
    def prompt_for_update(self, update_info: Dict, parent=None) -> bool:
        """
        Show update prompt to user
        
        Args:
            update_info: Dictionary with update information
            parent: Parent widget for dialog
        
        Returns:
            True if user wants to update, False otherwise
        """
        try:
            current_version = update_info['current_version']
            new_version = update_info['new_version']
            release_date = update_info.get('release_date', 'Unknown')
            description = update_info.get('description', 'No description available')
            
            message = f"""New version available from shared drive!

Current Version: {current_version}
New Version: {new_version}
Release Date: {release_date}

Description:
{description}

⚠️ IMPORTANT: Save your work before updating!
The application will restart to complete the update.

Do you want to update now?"""
            
            reply = QMessageBox.question(
                parent,
                "Update Available",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            return reply == QMessageBox.Yes
            
        except Exception as e:
            logger.error(f"Error showing update prompt: {e}")
            return False
    
    def create_updater_script(self) -> Path:
        """
        Create the external updater script that will replace the src folder
        
        Returns:
            Path to the created updater script
        """
        try:
            script_content = f'''@echo off
echo Starting Water Level App Update...
timeout /t 3 /nobreak > nul

echo Backing up current src folder...
if exist "{self.app_root}\\src_backup" rmdir /s /q "{self.app_root}\\src_backup"
move "{self.app_root}\\src" "{self.app_root}\\src_backup"

echo Copying new src folder from shared drive...
xcopy /s /e /i "{self.shared_src_folder}" "{self.app_root}\\src"

if %errorlevel% equ 0 (
    echo Update completed successfully!
    echo Copying version file...
    copy "{self.shared_version_file}" "{self.current_version_file}"
    
    echo Starting application...
    cd /d "{self.app_root}"
    start "" python main.py
    
    echo Cleaning up backup after successful update...
    timeout /t 5 /nobreak > nul
    if exist "{self.app_root}\\src_backup" rmdir /s /q "{self.app_root}\\src_backup"
) else (
    echo Update failed! Restoring backup...
    if exist "{self.app_root}\\src_backup" (
        rmdir /s /q "{self.app_root}\\src"
        move "{self.app_root}\\src_backup" "{self.app_root}\\src"
        echo Backup restored successfully.
    )
    pause
)

del "%~f0"
'''
            
            script_path = self.app_root / "update_helper.bat"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            logger.info(f"Updater script created: {script_path}")
            return script_path
            
        except Exception as e:
            logger.error(f"Error creating updater script: {e}")
            raise
    
    def apply_update(self, update_info: Dict, parent=None) -> bool:
        """
        Apply the update by launching external script and closing app
        
        Args:
            update_info: Dictionary with update information
            parent: Parent widget for progress dialog
        
        Returns:
            True if update process started successfully
        """
        try:
            # Final confirmation
            reply = QMessageBox.warning(
                parent,
                "Confirm Update",
                "The application will now close and update.\n\n"
                "Make sure you have saved all your work!\n\n"
                "Continue with update?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return False
            
            # Create updater script
            script_path = self.create_updater_script()
            
            # Launch updater script
            logger.info("Launching updater script and closing application")
            subprocess.Popen([str(script_path)], shell=True)
            
            # Give script a moment to start
            QApplication.processEvents()
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying update: {e}")
            QMessageBox.critical(
                parent,
                "Update Error",
                f"Failed to start update process:\n{str(e)}"
            )
            return False
    
    def get_update_status_message(self) -> str:
        """Get status message for display in UI"""
        try:
            logger.error(f"DEBUG: get_update_status_message() called")
            access_result = self.check_shared_drive_access()
            logger.error(f"DEBUG: check_shared_drive_access() returned: {access_result}")
            if not access_result:
                logger.error(f"DEBUG: Returning 'Shared drive not accessible' message")
                return "❌ Shared drive not accessible"
            
            shared_info = self.get_shared_version_info()
            if not shared_info:
                return "⚠️ Cannot read shared version info"
            
            shared_version = shared_info.get('version', 'Unknown')
            comparison = self.compare_versions(self.current_version, shared_version)
            
            if comparison < 0:
                return f"🔄 Update available: {shared_version}"
            elif comparison > 0:
                return f"✅ Development version (newer than shared: {shared_version})"
            else:
                return f"✅ Up to date ({shared_version})"
                
        except Exception as e:
            logger.error(f"Error getting update status: {e}")
            return "❓ Update status unknown"