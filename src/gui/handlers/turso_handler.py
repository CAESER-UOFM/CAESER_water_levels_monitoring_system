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
from PyQt5.QtCore import Qt
import requests

logger = logging.getLogger(__name__)

class TursoHandler:
    """Handles synchronization of databases to Turso cloud service"""
    
    def __init__(self, db_manager, settings_handler):
        self.db_manager = db_manager
        self.settings_handler = settings_handler
        self.temp_files = []
        
    def sync_to_turso(self, project_name: str, parent=None) -> bool:
        """
        Sync the current database to Turso for the specified project.
        
        Args:
            project_name: Name of the project (CAESER_GENERAL, MEGASITE, SANDY_CREEK)
            parent: Parent widget for dialogs
            
        Returns:
            bool: True if sync was successful
        """
        # Create progress dialog
        progress_dialog = QProgressDialog("Initializing Turso sync...", None, 0, 100, parent)
        progress_dialog.setWindowTitle("Turso Database Sync")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setFixedSize(450, 120)
        progress_dialog.show()
        
        try:
            # Step 1: Validate project and credentials
            progress_dialog.setLabelText("Validating credentials...")
            progress_dialog.setValue(10)
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
                
            # Step 2: Create reduced database
            progress_dialog.setLabelText("Creating optimized database...")
            progress_dialog.setValue(25)
            QApplication.processEvents()
            
            # Import mobile db reducer
            from ...database.mobile_db_reducer_optimized import MobileDatabaseReducer
            
            # Create temporary file for reduced database
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                reduced_db_path = tmp_file.name
                self.temp_files.append(reduced_db_path)
                
            # Get current database path
            current_db_path = Path(str(self.db_manager.current_db))
            reduced_db_path = Path(reduced_db_path)
            
            # Create optimized database
            reducer = MobileDatabaseReducer(current_db_path, reduced_db_path)
            try:
                reducer.create_reduced_database()
                stats = reducer.get_database_size_info()
                
                # Convert the stats to the expected format
                stats = {
                    'original_size': int(stats.get('source_size_mb', 0) * 1024 * 1024),
                    'reduced_size': int(stats.get('target_size_mb', 0) * 1024 * 1024),
                    'total_records': (stats.get('target_water_level_count', 0) + 
                                    stats.get('target_manual_count', 0) + 
                                    stats.get('target_telemetry_count', 0) +
                                    stats.get('target_master_baro_count', 0)),
                    'tables': {
                        'water_level_readings': stats.get('target_water_level_count', 0),
                        'manual_level_readings': stats.get('target_manual_count', 0),
                        'telemetry_level_readings': stats.get('target_telemetry_count', 0),
                        'rise_calculations': stats.get('target_rise_calculations_count', 0),
                        'wells': stats.get('target_wells_count', 0),
                        'master_baro_readings': stats.get('target_master_baro_count', 0)
                    }
                }
                
                logger.info(f"Created reduced database: {stats}")
                
            except Exception as e:
                progress_dialog.close()
                QMessageBox.critical(parent, "Reduction Failed",
                                   f"Failed to create optimized database:\n{str(e)}")
                self._cleanup_temp_files()
                return False
            
            # Step 3: Upload to Turso
            progress_dialog.setLabelText("Uploading to Turso...")
            progress_dialog.setValue(50)
            QApplication.processEvents()
            
            # Read the reduced database
            with open(str(reduced_db_path), 'rb') as f:
                db_content = f.read()
                
            # Get table structure from reduced database
            tables = self._get_table_structure(str(reduced_db_path))
            
            # Step 4: Clear existing data and upload new data
            progress_dialog.setLabelText("Updating Turso database...")
            progress_dialog.setValue(75)
            QApplication.processEvents()
            
            success = self._upload_to_turso(turso_url, turso_token, str(reduced_db_path), tables, progress_dialog)
            
            if not success:
                progress_dialog.close()
                QMessageBox.critical(parent, "Upload Failed",
                                   "Failed to upload database to Turso.")
                self._cleanup_temp_files()
                return False
                
            # Step 5: Log the sync
            progress_dialog.setLabelText("Logging sync operation...")
            progress_dialog.setValue(90)
            QApplication.processEvents()
            
            self._log_turso_sync(project_name, stats)
            
            # Cleanup
            self._cleanup_temp_files()
            
            progress_dialog.setValue(100)
            progress_dialog.close()
            
            # Show success message
            size_reduction = (1 - stats['reduced_size'] / stats['original_size']) * 100
            QMessageBox.information(
                parent,
                "Sync Complete",
                f"Successfully synced {project_name} to Turso!\n\n"
                f"Original size: {self._format_size(stats['original_size'])}\n"
                f"Reduced size: {self._format_size(stats['reduced_size'])}\n"
                f"Size reduction: {size_reduction:.1f}%\n"
                f"Records synced: {stats['total_records']:,}"
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
            
    def test_connection(self, url: str, token: str) -> Tuple[bool, str]:
        """
        Test connection to a Turso database.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Parse the database name from URL
            # Format: libsql://database-name-org.turso.io
            import re
            match = re.match(r'libsql://([^.]+)', url)
            if not match:
                return False, "Invalid URL format"
                
            # Test with a simple query
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Turso HTTP API endpoint
            api_url = url.replace('libsql://', 'https://').replace('.turso.io', '.turso.io/v2/pipeline')
            
            # Test query
            data = {
                'requests': [
                    {'type': 'execute', 'stmt': {'sql': 'SELECT 1'}}
                ]
            }
            
            response = requests.post(api_url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
            
    def _get_table_structure(self, db_path: str) -> Dict:
        """Get table structure from the reduced database"""
        tables = {}
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [row[0] for row in cursor.fetchall()]

                for table_name in table_names:
                    # Get table schema
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    create_sql = cursor.fetchone()[0]

                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]

                    # LOG THE SQL BEING SENT TO TURSO
                    if table_name == 'wells':
                        logger.warning(f"🔍 TURSO SQL for wells table: {create_sql}")
                        print(f"🔍 TURSO SQL for wells table: {create_sql}")
                        if 'current_transducer_serial' in create_sql:
                            logger.warning("✅ current_transducer_serial column found in SQL being sent to Turso!")
                            print("✅ current_transducer_serial column found in SQL being sent to Turso!")
                        else:
                            logger.warning("❌ current_transducer_serial column NOT found in SQL being sent to Turso!")
                            print("❌ current_transducer_serial column NOT found in SQL being sent to Turso!")

                    tables[table_name] = {
                        'create_sql': create_sql,
                        'row_count': row_count
                    }
                    
        except Exception as e:
            logger.error(f"Error getting table structure: {e}")
            
        return tables
        
    def _upload_to_turso(self, url: str, token: str, db_path: str, tables: Dict, progress_dialog) -> bool:
        """Upload database to Turso using multi-value INSERT for much better performance"""
        try:
            # Convert libsql URL to HTTP API endpoint
            api_url = url.replace('libsql://', 'https://').replace('.turso.io', '.turso.io/v2/pipeline')
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Step 1: Drop existing tables
            progress_dialog.setLabelText("Clearing existing data...")
            drop_requests = []
            for table_name in tables.keys():
                drop_requests.append({
                    'type': 'execute',
                    'stmt': {'sql': f'DROP TABLE IF EXISTS {table_name}'}
                })
                
            if drop_requests:
                response = requests.post(api_url, json={'requests': drop_requests}, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Failed to drop tables: {response.text}")
                    return False
                    
            # Step 2: Create tables
            progress_dialog.setLabelText("Creating tables...")
            create_requests = []
            for table_name, info in tables.items():
                create_requests.append({
                    'type': 'execute',
                    'stmt': {'sql': info['create_sql']}
                })
                
            if create_requests:
                response = requests.post(api_url, json={'requests': create_requests}, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Failed to create tables: {response.text}")
                    return False
                    
            # Step 3: Upload data using multi-value INSERT for much better performance
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                total_rows_uploaded = 0
                
                for table_name, info in tables.items():
                    if info['row_count'] == 0:
                        continue
                        
                    progress_dialog.setLabelText(f"Uploading {table_name} ({info['row_count']} rows)...")
                    
                    # Get all data from table
                    cursor.execute(f"SELECT * FROM {table_name}")
                    columns = [col[0] for col in cursor.description]
                    col_names = ','.join(columns)
                    
                    # Process in larger batches with multi-value INSERT
                    batch_size = 1000  # Increased batch size
                    batch_values = []
                    row_count = 0
                    
                    for row in cursor:
                        values = [row[col] for col in columns]
                        
                        # Format values for SQL
                        formatted_values = []
                        for val in values:
                            if val is None:
                                formatted_values.append('NULL')
                            elif isinstance(val, (int, float)):
                                formatted_values.append(str(val))
                            else:
                                # Escape single quotes and wrap in quotes
                                escaped_val = str(val).replace("'", "''")
                                formatted_values.append(f"'{escaped_val}'")
                                
                        values_str = f"({','.join(formatted_values)})"
                        batch_values.append(values_str)
                        row_count += 1
                        
                        # Send batch when full using multi-value INSERT
                        if len(batch_values) >= batch_size:
                            # Create a single INSERT with multiple value sets
                            multi_insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES {','.join(batch_values)}"
                            
                            request = {
                                'requests': [{
                                    'type': 'execute',
                                    'stmt': {'sql': multi_insert_sql}
                                }]
                            }
                            
                            response = requests.post(api_url, json=request, headers=headers)
                            if response.status_code != 200:
                                logger.error(f"Failed to insert batch: {response.text}")
                                # If multi-value INSERT fails, try smaller batch
                                logger.info("Retrying with smaller batch size...")
                                # Split into smaller chunks
                                for i in range(0, len(batch_values), 100):
                                    chunk = batch_values[i:i+100]
                                    chunk_sql = f"INSERT INTO {table_name} ({col_names}) VALUES {','.join(chunk)}"
                                    retry_request = {
                                        'requests': [{
                                            'type': 'execute',
                                            'stmt': {'sql': chunk_sql}
                                        }]
                                    }
                                    retry_response = requests.post(api_url, json=retry_request, headers=headers)
                                    if retry_response.status_code != 200:
                                        logger.error(f"Failed to insert chunk: {retry_response.text}")
                                        return False
                                        
                            batch_values = []
                            total_rows_uploaded += row_count
                            
                            # Update progress more frequently
                            progress_dialog.setLabelText(f"Uploading {table_name}: {row_count}/{info['row_count']} rows")
                            QApplication.processEvents()
                            
                    # Send remaining rows
                    if batch_values:
                        multi_insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES {','.join(batch_values)}"
                        request = {
                            'requests': [{
                                'type': 'execute',
                                'stmt': {'sql': multi_insert_sql}
                            }]
                        }
                        response = requests.post(api_url, json=request, headers=headers)
                        if response.status_code != 200:
                            logger.error(f"Failed to insert final batch: {response.text}")
                            # Try smaller chunks
                            for i in range(0, len(batch_values), 100):
                                chunk = batch_values[i:i+100]
                                chunk_sql = f"INSERT INTO {table_name} ({col_names}) VALUES {','.join(chunk)}"
                                retry_request = {
                                    'requests': [{
                                        'type': 'execute',
                                        'stmt': {'sql': chunk_sql}
                                    }]
                                }
                                retry_response = requests.post(api_url, json=retry_request, headers=headers)
                                if retry_response.status_code != 200:
                                    logger.error(f"Failed to insert chunk: {retry_response.text}")
                                    return False
                            
                    logger.info(f"Uploaded {row_count} rows to {table_name}")
                    
            logger.info(f"Total rows uploaded: {total_rows_uploaded}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to Turso: {e}")
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
                "stats": {
                    "original_size": stats['original_size'],
                    "reduced_size": stats['reduced_size'],
                    "size_reduction_percent": (1 - stats['reduced_size'] / stats['original_size']) * 100,
                    "total_records": stats['total_records'],
                    "tables": stats.get('tables', {})
                },
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
            
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
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