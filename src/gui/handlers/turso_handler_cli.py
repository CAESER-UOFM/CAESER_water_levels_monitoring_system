import os
import json
import logging
import tempfile
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict
from PyQt5.QtWidgets import QProgressDialog, QMessageBox, QApplication
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import requests

logger = logging.getLogger(__name__)

class TursoUploadThread(QThread):
    """Thread for running Turso CLI commands without blocking UI"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, db_path, db_name, org_name):
        super().__init__()
        self.db_path = db_path
        self.db_name = db_name
        self.org_name = org_name
        self.process = None
        
    def run(self):
        """Run the Turso upload process"""
        try:
            # Check if turso CLI is installed
            result = subprocess.run(['turso', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.finished.emit(False, "Turso CLI not installed. Please install it first:\ncurl -sSfL https://get.tur.so/install.sh | bash")
                return
                
            self.progress.emit("Checking Turso authentication...")
            
            # Upload the database using turso db shell with .restore command
            self.progress.emit(f"Uploading database to {self.db_name}...")
            
            # Create a SQL script that restores the database
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
                # First drop all tables
                f.write(".mode box\n")
                f.write(".tables\n")  # List tables to verify connection
                f.write(f".restore {self.db_path}\n")  # Restore from our reduced database
                restore_script = f.name
                
            try:
                # Run the restore command
                cmd = ['turso', 'db', 'shell', self.db_name, '--org', self.org_name, '-f', restore_script]
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Monitor the process
                stdout, stderr = self.process.communicate()
                
                if self.process.returncode == 0:
                    self.progress.emit("Upload completed successfully!")
                    self.finished.emit(True, "Database uploaded successfully to Turso!")
                else:
                    error_msg = stderr or stdout or "Unknown error"
                    self.finished.emit(False, f"Upload failed: {error_msg}")
                    
            finally:
                # Clean up
                if os.path.exists(restore_script):
                    os.remove(restore_script)
                    
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

class TursoHandlerCLI:
    """Handles synchronization of databases to Turso using CLI for better performance"""
    
    def __init__(self, db_manager, settings_handler):
        self.db_manager = db_manager
        self.settings_handler = settings_handler
        self.temp_files = []
        
    def check_cli_installed(self) -> Tuple[bool, str]:
        """Check if Turso CLI is installed"""
        try:
            result = subprocess.run(['turso', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, "Turso CLI not found"
        except FileNotFoundError:
            return False, "Turso CLI not installed"
            
    def sync_to_turso(self, project_name: str, parent=None) -> bool:
        """
        Sync the current database to Turso using CLI for much faster uploads.
        
        Args:
            project_name: Name of the project (CAESER_GENERAL, MEGASITE, SANDY_CREEK)
            parent: Parent widget for dialogs
            
        Returns:
            bool: True if sync was successful
        """
        # First check if CLI is available
        cli_available, cli_info = self.check_cli_installed()
        if not cli_available:
            # Ask user if they want to install it
            reply = QMessageBox.question(
                parent,
                "Turso CLI Required",
                "The Turso CLI is required for fast database uploads.\n\n"
                "Would you like to install it now?\n\n"
                "Installation command:\n"
                "curl -sSfL https://get.tur.so/install.sh | bash",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Show installation instructions
                QMessageBox.information(
                    parent,
                    "Installation Instructions",
                    "To install Turso CLI:\n\n"
                    "1. Open Terminal\n"
                    "2. Run: curl -sSfL https://get.tur.so/install.sh | bash\n"
                    "3. Follow the installation prompts\n"
                    "4. Run: turso auth login\n"
                    "5. Try the sync again\n\n"
                    "For more info: https://docs.turso.tech/cli/installation"
                )
            return False
            
        # Create progress dialog
        progress_dialog = QProgressDialog("Initializing Turso sync...", "Cancel", 0, 100, parent)
        progress_dialog.setWindowTitle("Turso Database Sync (CLI)")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setFixedSize(500, 150)
        progress_dialog.show()
        
        try:
            # Step 1: Validate project
            progress_dialog.setLabelText("Validating project...")
            progress_dialog.setValue(10)
            QApplication.processEvents()
            
            if project_name not in ["CAESER_GENERAL", "MEGASITE", "SANDY_CREEK"]:
                progress_dialog.close()
                QMessageBox.warning(parent, "Invalid Project", 
                                  f"Project '{project_name}' is not supported for Turso sync.")
                return False
                
            # Get database name mapping
            db_name_map = {
                "CAESER_GENERAL": "caeser-general",
                "MEGASITE": "megasite", 
                "SANDY_CREEK": "sandy-creek"
            }
            turso_db_name = db_name_map[project_name]
            
            # Get organization from settings
            auth_token = self.settings_handler.get_setting("turso_auth_token", "")
            if not auth_token:
                progress_dialog.close()
                QMessageBox.warning(parent, "Missing Credentials",
                                  "Turso auth token not configured.\n"
                                  "Please configure it in Settings → Turso Database Settings.")
                return False
                
            # Extract org name from token or use default
            org_name = "benjaled"  # Your organization name
            
            # Step 2: Create reduced database
            progress_dialog.setLabelText("Creating optimized database...")
            progress_dialog.setValue(25)
            QApplication.processEvents()
            
            # Import mobile db reducer
            from ...database.mobile_db_reducer import MobileDatabaseReducer
            
            # Create temporary file for reduced database
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                reduced_db_path = tmp_file.name
                self.temp_files.append(reduced_db_path)
                
            # Get current database path
            current_db_path = Path(str(self.db_manager.current_db))
            reduced_db_path = Path(reduced_db_path)
            
            # Create reduced database
            reducer = MobileDatabaseReducer(current_db_path, reduced_db_path)
            try:
                reducer.create_reduced_database()
                stats = reducer.get_database_size_info()
                
                size_mb = stats.get('target_size_mb', 0)
                logger.info(f"Created reduced database: {size_mb:.1f} MB")
                
            except Exception as e:
                progress_dialog.close()
                QMessageBox.critical(parent, "Reduction Failed",
                                   f"Failed to create optimized database:\n{str(e)}")
                self._cleanup_temp_files()
                return False
                
            # Step 3: Upload using CLI in a separate thread
            progress_dialog.setLabelText(f"Uploading {size_mb:.1f} MB to Turso (using CLI for speed)...")
            progress_dialog.setValue(50)
            
            # Create and start upload thread
            self.upload_thread = TursoUploadThread(str(reduced_db_path), turso_db_name, org_name)
            
            # Track if upload is complete
            upload_complete = False
            upload_success = False
            upload_message = ""
            
            def on_progress(msg):
                progress_dialog.setLabelText(msg)
                
            def on_finished(success, message):
                nonlocal upload_complete, upload_success, upload_message
                upload_complete = True
                upload_success = success
                upload_message = message
                
            self.upload_thread.progress.connect(on_progress)
            self.upload_thread.finished.connect(on_finished)
            self.upload_thread.start()
            
            # Wait for upload to complete with cancel support
            while not upload_complete:
                QApplication.processEvents()
                if progress_dialog.wasCanceled():
                    if self.upload_thread.process:
                        self.upload_thread.process.terminate()
                    self.upload_thread.quit()
                    self.upload_thread.wait()
                    self._cleanup_temp_files()
                    return False
                self.upload_thread.wait(100)  # Check every 100ms
                
            # Clean up thread
            self.upload_thread.quit()
            self.upload_thread.wait()
            
            # Check result
            if not upload_success:
                progress_dialog.close()
                QMessageBox.critical(parent, "Upload Failed", upload_message)
                self._cleanup_temp_files()
                return False
                
            # Step 4: Log the sync
            progress_dialog.setLabelText("Logging sync operation...")
            progress_dialog.setValue(90)
            QApplication.processEvents()
            
            # Format stats for logging
            log_stats = {
                'original_size': int(stats.get('source_size_mb', 0) * 1024 * 1024),
                'reduced_size': int(stats.get('target_size_mb', 0) * 1024 * 1024),
                'total_records': stats.get('target_water_level_count', 0) + stats.get('target_manual_count', 0),
                'upload_method': 'turso_cli',
                'tables': {
                    'water_level_readings': stats.get('target_water_level_count', 0),
                    'manual_level_readings': stats.get('target_manual_count', 0)
                }
            }
            
            self._log_turso_sync(project_name, log_stats)
            
            # Cleanup
            self._cleanup_temp_files()
            
            progress_dialog.setValue(100)
            progress_dialog.close()
            
            # Show success message
            size_reduction = (1 - stats.get('target_size_mb', 0) / stats.get('source_size_mb', 1)) * 100
            QMessageBox.information(
                parent,
                "Sync Complete",
                f"Successfully synced {project_name} to Turso using CLI!\n\n"
                f"Original size: {stats.get('source_size_mb', 0):.1f} MB\n"
                f"Reduced size: {stats.get('target_size_mb', 0):.1f} MB\n"
                f"Size reduction: {size_reduction:.1f}%\n"
                f"Upload method: Turso CLI (fast)\n\n"
                f"The database is now available in Turso!"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing to Turso: {e}")
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QMessageBox.critical(parent, "Sync Error",
                               f"Failed to sync to Turso:\n{str(e)}")
            self._cleanup_temp_files()
            return False
            
    def _log_turso_sync(self, project_name: str, stats: Dict):
        """Log the Turso sync operation to Google Drive"""
        try:
            # Import Google Drive data handler
            from .google_drive_data_handler import GoogleDriveDataHandler
            
            # Get drive service
            drive_service = getattr(self.db_manager, 'drive_service', None)
            if not drive_service:
                logger.warning("Google Drive service not available for logging")
                return
                
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "turso_sync",
                "project": project_name,
                "user": os.environ.get('USERNAME', os.environ.get('USER', 'unknown')),
                "stats": stats,
                "success": True
            }
            
            # Use existing feedback logging mechanism
            data_handler = GoogleDriveDataHandler(drive_service, self.settings_handler)
            folder_id = self.settings_handler.get_setting("user_feedback_folder_id")
            
            if folder_id:
                # Create or append to turso_sync_log.json
                filename = "turso_sync_log.json"
                success = data_handler._append_to_json_file(folder_id, filename, log_entry)
                if success:
                    logger.info(f"Logged Turso sync for {project_name}")
                else:
                    logger.warning("Failed to log Turso sync to Google Drive")
            else:
                logger.warning("User feedback folder not configured for logging")
                
        except Exception as e:
            logger.error(f"Error logging Turso sync: {e}")
            
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files = []