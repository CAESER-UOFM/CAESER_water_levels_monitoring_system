import os
import json
import logging
import tempfile
import sqlite3
import gzip
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict
from PyQt5.QtWidgets import QProgressDialog, QMessageBox, QApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import requests

logger = logging.getLogger(__name__)

class TursoUploadWorker(QThread):
    """Background worker for Turso uploads"""
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, url, token, db_path, tables):
        super().__init__()
        self.url = url
        self.token = token
        self.db_path = db_path
        self.tables = tables
        self.cancelled = False
        
    def cancel(self):
        self.cancelled = True
        
    def run(self):
        """Run the upload process with optimizations"""
        try:
            api_url = self.url.replace('libsql://', 'https://').replace('.turso.io', '.turso.io/v2/pipeline')
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Drop and recreate tables
            self.progress.emit("Preparing database...", 10)
            if not self._setup_tables(api_url, headers):
                return
                
            # Upload data with maximum efficiency
            if not self._upload_data(api_url, headers):
                return
                
            self.finished.emit(True, "Upload completed successfully!")
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            self.finished.emit(False, str(e))
            
    def _setup_tables(self, api_url, headers):
        """Drop and recreate tables"""
        try:
            # Drop existing tables
            drop_requests = []
            for table_name in self.tables.keys():
                drop_requests.append({
                    'type': 'execute',
                    'stmt': {'sql': f'DROP TABLE IF EXISTS {table_name}'}
                })
                
            if drop_requests:
                response = requests.post(api_url, json={'requests': drop_requests}, headers=headers)
                if response.status_code != 200:
                    self.finished.emit(False, f"Failed to drop tables: {response.text}")
                    return False
                    
            # Create tables
            create_requests = []
            for table_name, info in self.tables.items():
                create_requests.append({
                    'type': 'execute',
                    'stmt': {'sql': info['create_sql']}
                })
                
            if create_requests:
                response = requests.post(api_url, json={'requests': create_requests}, headers=headers)
                if response.status_code != 200:
                    self.finished.emit(False, f"Failed to create tables: {response.text}")
                    return False
                    
            return True
            
        except Exception as e:
            self.finished.emit(False, f"Setup error: {str(e)}")
            return False
            
    def _upload_data(self, api_url, headers):
        """Upload data with maximum batch size and compression"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                total_rows = sum(info['row_count'] for info in self.tables.values())
                uploaded_rows = 0
                
                for table_name, info in self.tables.items():
                    if info['row_count'] == 0:
                        continue
                        
                    if self.cancelled:
                        self.finished.emit(False, "Upload cancelled")
                        return False
                        
                    # Get all data
                    cursor.execute(f"SELECT * FROM {table_name}")
                    columns = [col[0] for col in cursor.description]
                    col_names = ','.join(columns)
                    
                    # Use maximum batch size that Turso can handle
                    # Testing shows ~5000 rows or ~1MB of SQL text works well
                    batch_values = []
                    batch_size_bytes = 0
                    max_batch_bytes = 900000  # ~900KB to stay under 1MB limit
                    max_batch_rows = 5000
                    
                    for row in cursor:
                        if self.cancelled:
                            self.finished.emit(False, "Upload cancelled")
                            return False
                            
                        values = [row[col] for col in columns]
                        
                        # Format values
                        formatted_values = []
                        for val in values:
                            if val is None:
                                formatted_values.append('NULL')
                            elif isinstance(val, (int, float)):
                                formatted_values.append(str(val))
                            else:
                                escaped_val = str(val).replace("'", "''")
                                formatted_values.append(f"'{escaped_val}'")
                                
                        values_str = f"({','.join(formatted_values)})"
                        values_bytes = len(values_str.encode('utf-8'))
                        
                        # Check if adding this row would exceed limits
                        if batch_values and (
                            len(batch_values) >= max_batch_rows or 
                            batch_size_bytes + values_bytes > max_batch_bytes
                        ):
                            # Send current batch
                            if not self._send_batch(api_url, headers, table_name, 
                                                   col_names, batch_values):
                                return False
                                
                            uploaded_rows += len(batch_values)
                            progress = int((uploaded_rows / total_rows) * 80) + 20
                            self.progress.emit(
                                f"Uploading {table_name}: {uploaded_rows}/{total_rows} rows", 
                                progress
                            )
                            
                            batch_values = []
                            batch_size_bytes = 0
                            
                        batch_values.append(values_str)
                        batch_size_bytes += values_bytes
                        
                    # Send remaining batch
                    if batch_values:
                        if not self._send_batch(api_url, headers, table_name, 
                                               col_names, batch_values):
                            return False
                        uploaded_rows += len(batch_values)
                        
                    logger.info(f"Uploaded {info['row_count']} rows to {table_name}")
                    
                self.progress.emit(f"Upload complete: {uploaded_rows} rows", 100)
                return True
                
        except Exception as e:
            self.finished.emit(False, f"Upload error: {str(e)}")
            return False
            
    def _send_batch(self, api_url, headers, table_name, col_names, batch_values):
        """Send a batch of inserts with retry logic"""
        try:
            sql = f"INSERT INTO {table_name} ({col_names}) VALUES {','.join(batch_values)}"
            request = {
                'requests': [{
                    'type': 'execute',
                    'stmt': {'sql': sql}
                }]
            }
            
            # Try up to 3 times with smaller batches if needed
            for attempt in range(3):
                response = requests.post(api_url, json=request, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 413 or "too large" in response.text.lower():
                    # Request too large, split batch
                    if len(batch_values) > 100:
                        mid = len(batch_values) // 2
                        return (self._send_batch(api_url, headers, table_name, 
                                               col_names, batch_values[:mid]) and
                               self._send_batch(api_url, headers, table_name, 
                                               col_names, batch_values[mid:]))
                    else:
                        logger.error(f"Batch too large even at minimum size: {response.text}")
                        return False
                else:
                    logger.error(f"Batch upload failed (attempt {attempt + 1}): {response.text}")
                    
            return False
            
        except Exception as e:
            logger.error(f"Batch send error: {e}")
            return False

class TursoHandlerOptimized:
    """Optimized Turso handler that works on all platforms"""
    
    def __init__(self, db_manager, settings_handler):
        self.db_manager = db_manager
        self.settings_handler = settings_handler
        self.temp_files = []
        self.upload_worker = None
        
    def sync_to_turso(self, project_name: str, parent=None) -> bool:
        """Sync database to Turso with platform-independent optimizations"""
        
        # Create progress dialog
        progress_dialog = QProgressDialog("Initializing Turso sync...", "Cancel", 0, 100, parent)
        progress_dialog.setWindowTitle("Turso Database Sync")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setFixedSize(500, 150)
        progress_dialog.show()
        
        try:
            # Validate project and credentials
            progress_dialog.setLabelText("Validating credentials...")
            progress_dialog.setValue(5)
            QApplication.processEvents()
            
            if project_name not in ["CAESER_GENERAL", "MEGASITE", "SANDY_CREEK"]:
                progress_dialog.close()
                QMessageBox.warning(parent, "Invalid Project", 
                                  f"Project '{project_name}' is not supported for Turso sync.")
                return False
                
            # Get Turso credentials
            url_key = f"turso_{project_name.lower()}_url"
            token_key = f"turso_{project_name.lower()}_token"
            
            turso_url = self.settings_handler.get_setting(url_key, "")
            turso_token = self.settings_handler.get_setting(token_key, "")
            
            if not turso_url or not turso_token:
                progress_dialog.close()
                QMessageBox.warning(parent, "Missing Credentials",
                                  f"Turso credentials for {project_name} are not configured.\n"
                                  f"Please configure them in Settings → Turso Database Settings.")
                return False
                
            # Create reduced database
            progress_dialog.setLabelText("Creating optimized database...")
            progress_dialog.setValue(10)
            QApplication.processEvents()
            
            from ...database.mobile_db_reducer import MobileDatabaseReducer
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                reduced_db_path = tmp_file.name
                self.temp_files.append(reduced_db_path)
                
            current_db_path = Path(str(self.db_manager.current_db))
            reduced_db_path = Path(reduced_db_path)
            
            reducer = MobileDatabaseReducer(current_db_path, reduced_db_path)
            try:
                reducer.create_reduced_database()
                stats = reducer.get_database_size_info()
                
                # Convert stats
                stats_formatted = {
                    'original_size': int(stats.get('source_size_mb', 0) * 1024 * 1024),
                    'reduced_size': int(stats.get('target_size_mb', 0) * 1024 * 1024),
                    'total_records': stats.get('target_water_level_count', 0) + stats.get('target_manual_count', 0),
                    'tables': {
                        'water_level_readings': stats.get('target_water_level_count', 0),
                        'manual_level_readings': stats.get('target_manual_count', 0)
                    }
                }
                
                logger.info(f"Created reduced database: {stats.get('target_size_mb', 0):.1f} MB")
                
            except Exception as e:
                progress_dialog.close()
                QMessageBox.critical(parent, "Reduction Failed",
                                   f"Failed to create optimized database:\n{str(e)}")
                self._cleanup_temp_files()
                return False
                
            # Get table structure
            tables = self._get_table_structure(str(reduced_db_path))
            
            # Start upload in background thread
            self.upload_worker = TursoUploadWorker(turso_url, turso_token, 
                                                  str(reduced_db_path), tables)
            
            # Connect signals
            upload_complete = False
            upload_success = False
            upload_message = ""
            
            def on_progress(msg, percent):
                progress_dialog.setLabelText(msg)
                progress_dialog.setValue(percent)
                QApplication.processEvents()
                
            def on_finished(success, message):
                nonlocal upload_complete, upload_success, upload_message
                upload_complete = True
                upload_success = success
                upload_message = message
                
            self.upload_worker.progress.connect(on_progress)
            self.upload_worker.finished.connect(on_finished)
            
            # Start upload
            self.upload_worker.start()
            
            # Wait for completion
            while not upload_complete:
                QApplication.processEvents()
                if progress_dialog.wasCanceled():
                    self.upload_worker.cancel()
                    self.upload_worker.wait()
                    self._cleanup_temp_files()
                    return False
                self.upload_worker.wait(100)
                
            # Clean up thread
            self.upload_worker.quit()
            self.upload_worker.wait()
            
            if not upload_success:
                progress_dialog.close()
                QMessageBox.critical(parent, "Upload Failed", upload_message)
                self._cleanup_temp_files()
                return False
                
            # Log the sync
            self._log_turso_sync(project_name, stats_formatted)
            
            # Cleanup
            self._cleanup_temp_files()
            progress_dialog.close()
            
            # Show success
            size_reduction = (1 - stats_formatted['reduced_size'] / stats_formatted['original_size']) * 100
            QMessageBox.information(
                parent,
                "Sync Complete",
                f"Successfully synced {project_name} to Turso!\n\n"
                f"Original size: {self._format_size(stats_formatted['original_size'])}\n"
                f"Reduced size: {self._format_size(stats_formatted['reduced_size'])}\n"
                f"Size reduction: {size_reduction:.1f}%\n"
                f"Records synced: {stats_formatted['total_records']:,}\n\n"
                f"Upload method: Optimized HTTP (works on all platforms)"
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
            
    def _get_table_structure(self, db_path: str) -> Dict:
        """Get table structure from the reduced database"""
        tables = {}
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [row[0] for row in cursor.fetchall()]
                
                for table_name in table_names:
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", 
                                 (table_name,))
                    create_sql = cursor.fetchone()[0]
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    tables[table_name] = {
                        'create_sql': create_sql,
                        'row_count': row_count
                    }
                    
        except Exception as e:
            logger.error(f"Error getting table structure: {e}")
            
        return tables
        
    def _log_turso_sync(self, project_name: str, stats: Dict):
        """Log the Turso sync operation"""
        try:
            from .google_drive_data_handler import GoogleDriveDataHandler
            
            drive_service = getattr(self.db_manager, 'drive_service', None)
            if not drive_service:
                logger.warning("Google Drive service not available for logging")
                return
                
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "turso_sync",
                "project": project_name,
                "user": os.environ.get('USERNAME', os.environ.get('USER', 'unknown')),
                "stats": stats,
                "success": True,
                "platform": os.name  # 'nt' for Windows, 'posix' for Mac/Linux
            }
            
            data_handler = GoogleDriveDataHandler(drive_service, self.settings_handler)
            folder_id = self.settings_handler.get_setting("user_feedback_folder_id")
            
            if folder_id:
                filename = "turso_sync_log.json"
                success = data_handler._append_to_json_file(folder_id, filename, log_entry)
                if success:
                    logger.info(f"Logged Turso sync for {project_name}")
                    
        except Exception as e:
            logger.error(f"Error logging Turso sync: {e}")
            
    def _format_size(self, size_bytes: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
        
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files = []