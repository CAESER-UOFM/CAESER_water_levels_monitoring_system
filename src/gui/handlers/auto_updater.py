"""
Auto Updater for Water Level Monitoring Application
Handles automatic updates by downloading and replacing the src folder.
"""

import os
import shutil
import tempfile
import zipfile
import requests
import logging
from pathlib import Path
from typing import Optional, Callable
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from .version_checker import VersionChecker

logger = logging.getLogger(__name__)

class UpdateDownloader(QThread):
    """Thread for downloading updates"""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, download_url: str, temp_dir: Path):
        super().__init__()
        self.download_url = download_url
        self.temp_dir = temp_dir
        
    def run(self):
        """Download the update"""
        try:
            self.status.emit("Downloading update...")
            
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            zip_path = self.temp_dir / "update.zip"
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)
                            
            self.status.emit("Download complete!")
            self.finished.emit(True, str(zip_path))
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.finished.emit(False, str(e))

class AutoUpdater:
    """Handles automatic updates for the application"""
    
    def __init__(self, app_root: Path, github_repo: str = "benjaled/water_levels_monitoring_-for_external_edits-"):
        """
        Initialize auto updater
        
        Args:
            app_root: Root directory of the application
            github_repo: GitHub repository in format "owner/repo"
        """
        self.app_root = Path(app_root)
        self.github_repo = github_repo
        self.src_dir = self.app_root / "src"
        self.backup_dir = self.app_root / "backups"
        self.version_file = self.app_root / "version.json"
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load current version
        self.current_version = self._load_current_version()
        self.version_checker = VersionChecker(self.current_version, github_repo)
        
    def _load_current_version(self) -> str:
        """Load current version from file or default"""
        try:
            import json
            if self.version_file.exists():
                with open(self.version_file, 'r') as f:
                    data = json.load(f)
                return data.get('version', '1.0.0')
        except Exception as e:
            logger.error(f"Failed to load version: {e}")
        return '1.0.0'
        
    def _save_current_version(self, version: str):
        """Save current version to file"""
        try:
            import json
            from datetime import datetime
            data = {
                'version': version,
                'last_update': datetime.now().isoformat(),
                'app_root': str(self.app_root)
            }
            with open(self.version_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save version: {e}")
            
    def check_for_updates(self) -> Optional[dict]:
        """
        Check if updates are available
        
        Returns:
            Update info dict or None if no updates
        """
        try:
            return self.version_checker.get_update_info()
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return None
            
    def create_backup(self, version: str) -> bool:
        """
        Create backup of current src directory
        
        Args:
            version: Version string for backup naming
            
        Returns:
            True if successful
        """
        try:
            backup_path = self.backup_dir / f"v{version}"
            
            # Remove old backup if exists
            if backup_path.exists():
                shutil.rmtree(backup_path)
                
            # Create new backup
            shutil.copytree(self.src_dir, backup_path)
            logger.info(f"Backup created at {backup_path}")
            
            # Keep only last 3 backups
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
            
    def _cleanup_old_backups(self):
        """Keep only the last 3 backups"""
        try:
            backups = [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith('v')]
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove old backups (keep only 3 most recent)
            for backup in backups[3:]:
                shutil.rmtree(backup)
                logger.info(f"Removed old backup: {backup}")
                
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            
    def apply_update(self, update_info: dict, parent=None) -> bool:
        """
        Apply the update
        
        Args:
            update_info: Update information from check_for_updates
            parent: Parent widget for progress dialog
            
        Returns:
            True if successful
        """
        try:
            # Create backup first
            if not self.create_backup(self.current_version):
                QMessageBox.critical(parent, "Update Failed", "Failed to create backup. Update cancelled.")
                return False
                
            # Download update
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Show progress dialog
                progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100, parent)
                progress_dialog.setWindowTitle("Updating Application")
                progress_dialog.setWindowModality(Qt.WindowModal)
                progress_dialog.show()
                
                # Download in thread
                downloader = UpdateDownloader(update_info['download_url'], temp_path)
                
                def on_progress(value):
                    progress_dialog.setValue(value)
                    
                def on_status(status):
                    progress_dialog.setLabelText(status)
                    
                def on_finished(success, result):
                    progress_dialog.close()
                    if success:
                        zip_path = Path(result)
                        if self._extract_and_replace(zip_path, update_info['version']):
                            QMessageBox.information(parent, "Update Complete", 
                                                  f"Application updated to version {update_info['version']}.\n"
                                                  "Please restart the application.")
                            return True
                        else:
                            self._rollback_update()
                            QMessageBox.critical(parent, "Update Failed", "Failed to apply update. Rolled back to previous version.")
                            return False
                    else:
                        QMessageBox.critical(parent, "Update Failed", f"Download failed: {result}")
                        return False
                        
                downloader.progress.connect(on_progress)
                downloader.status.connect(on_status)
                downloader.finished.connect(on_finished)
                
                downloader.start()
                
                # Wait for download to complete
                while downloader.isRunning():
                    QApplication.processEvents()
                    
                return True
                
        except Exception as e:
            logger.error(f"Update failed: {e}")
            self._rollback_update()
            QMessageBox.critical(parent, "Update Failed", f"Update failed: {str(e)}")
            return False
            
    def _extract_and_replace(self, zip_path: Path, new_version: str) -> bool:
        """Extract update and replace src directory"""
        try:
            with tempfile.TemporaryDirectory() as extract_dir:
                extract_path = Path(extract_dir)
                
                # Extract zip
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    
                # Find src directory in extracted files
                src_found = None
                for root, dirs, files in os.walk(extract_path):
                    if 'src' in dirs:
                        src_found = Path(root) / 'src'
                        break
                        
                if not src_found or not src_found.exists():
                    logger.error("No src directory found in update")
                    return False
                    
                # Replace src directory
                if self.src_dir.exists():
                    shutil.rmtree(self.src_dir)
                    
                shutil.copytree(src_found, self.src_dir)
                
                # Update version
                self._save_current_version(new_version)
                
                logger.info(f"Update applied successfully to version {new_version}")
                return True
                
        except Exception as e:
            logger.error(f"Extract and replace failed: {e}")
            return False
            
    def _rollback_update(self):
        """Rollback to previous version"""
        try:
            # Find most recent backup
            backups = [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith('v')]
            if not backups:
                logger.error("No backups available for rollback")
                return False
                
            latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
            
            # Restore from backup
            if self.src_dir.exists():
                shutil.rmtree(self.src_dir)
                
            shutil.copytree(latest_backup, self.src_dir)
            
            logger.info(f"Rolled back to backup: {latest_backup}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
            
    def prompt_for_update(self, update_info: dict, parent=None) -> bool:
        """
        Show update prompt to user
        
        Args:
            update_info: Update information
            parent: Parent widget
            
        Returns:
            True if user wants to update
        """
        message = f"""A new version is available!

Current Version: {update_info['current_version']}
New Version: {update_info['version']}

Release Notes:
{update_info.get('release_notes', 'No release notes available.')[:500]}

Would you like to update now?

Note: The application will need to be restarted after the update."""

        reply = QMessageBox.question(parent, "Update Available", message,
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        return reply == QMessageBox.Yes