# -*- coding: utf-8 -*-
"""
Auto Update Handler for Water Level Monitoring System

Handles automatic synchronization with Google Drive using the consolidated folder structure
and service account authentication.

@author: Updated for consolidated architecture
"""

import os
import logging
import sqlite3
import tempfile
from datetime import datetime
from PyQt5.QtWidgets import QProgressDialog, QMessageBox, QApplication
from PyQt5.QtCore import Qt
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

class AutoUpdateHandler:
    """Handles automatic updates and synchronization with Google Drive using consolidated folder structure"""
    
    def __init__(self, parent, db_manager, drive_service, settings_handler, tabs):
        """
        Initialize AutoUpdateHandler
        
        Args:
            parent: Parent window for displaying dialogs
            db_manager: Database manager instance
            drive_service: Google Drive service instance
            settings_handler: Settings handler instance
            tabs: Dictionary of tabs from the main window
        """
        self.parent = parent
        self.db_manager = db_manager
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        self.tabs = tabs
        
        # Initialize consolidated folder monitor for both barologger and water level sync
        self.runs_monitor = None
        
    def auto_sync_barologgers(self):
        """Run automatic sync for barologger XLE files using consolidated folder structure"""
        try:
            # Create progress dialog
            progress_dialog = QProgressDialog("Initializing barologger sync...", None, 0, 100, self.parent)
            progress_dialog.setWindowTitle("Barologger Auto Sync")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setCancelButton(None)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setFixedSize(450, 120)
            progress_dialog.show()
            
            # Step 1: Check Google Drive authentication
            progress_dialog.setLabelText("Verifying Google Drive connection...")
            progress_dialog.setValue(5)
            QApplication.processEvents()
            
            if not self.drive_service.get_service():
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Authentication Required", 
                                  "Google Drive authentication required. Please check your service account configuration.")
                return
            
            # Step 2: Initialize consolidated folder monitor
            progress_dialog.setLabelText("Accessing consolidated field data folder...")
            progress_dialog.setValue(15)
            QApplication.processEvents()
            
            consolidated_folder_id = self.settings_handler.get_setting("consolidated_field_data_folder", "")
            if not consolidated_folder_id:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Configuration Missing", 
                                  "Consolidated field data folder not configured. Please run field data consolidation first.")
                return
            
            # Initialize runs monitor for consolidated folder
            from ..handlers.runs_folder_monitor import RunsFolderMonitor
            if not self.runs_monitor:
                self.runs_monitor = RunsFolderMonitor(consolidated_folder_id, self.db_manager.current_db)
                self.runs_monitor.set_authenticated_service(self.drive_service.get_service())
            
            # Step 3: Get barologger tab for processing
            progress_dialog.setLabelText("Initializing barologger processor...")
            progress_dialog.setValue(25)
            QApplication.processEvents()
            
            baro_tab = self.tabs.get("barologger")
            if not baro_tab:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Tab Error", "Barologger tab not initialized.")
                return
            
            # Step 4: Get active barologgers from database
            progress_dialog.setLabelText("Checking for active barologgers...")
            progress_dialog.setValue(35)
            QApplication.processEvents()
            
            active_barologgers = self._get_active_barologgers()
            if not active_barologgers:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No Active Barologgers", 
                                      "No active barologgers found in the database.")
                return
            
            logger.info(f"Found {len(active_barologgers)} active barologgers to sync")
            
            # Step 5: Check for new files in current and next month folders
            progress_dialog.setLabelText("Scanning consolidated folder for new barologger files...")
            progress_dialog.setValue(45)
            QApplication.processEvents()
            
            current_month = datetime.now().strftime("%Y-%m")
            files_found = self._scan_for_barologger_files(current_month, active_barologgers)
            
            if not files_found:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No New Files", 
                                      "No new barologger files found for processing.")
                return
            
            # Step 6: Process found files
            progress_dialog.setLabelText(f"Processing {len(files_found)} new barologger files...")
            progress_dialog.setValue(60)
            QApplication.processEvents()
            
            processed_count = self._process_barologger_files(files_found, baro_tab, progress_dialog)
            
            progress_dialog.setValue(100)
            progress_dialog.close()
            
            # Show completion message
            if processed_count > 0:
                QMessageBox.information(
                    self.parent, 
                    "Sync Complete", 
                    f"Successfully processed {processed_count} barologger files.\n\n"
                    f"Files imported from consolidated folder: {current_month}"
                )
                
                # Refresh barologger tab if it exists
                if hasattr(baro_tab, 'refresh_data'):
                    baro_tab.refresh_data()
            else:
                QMessageBox.information(self.parent, "Sync Complete", 
                                      "No new files were processed during this sync.")
                
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            logger.error(f"Error in auto_sync_barologgers: {e}")
            QMessageBox.critical(self.parent, "Sync Error", 
                               f"An error occurred during barologger sync:\n{str(e)}")
    
    def auto_sync_water_levels(self):
        """Run automatic sync for water level XLE files using consolidated folder structure"""
        try:
            # Create progress dialog
            progress_dialog = QProgressDialog("Initializing water level sync...", None, 0, 100, self.parent)
            progress_dialog.setWindowTitle("Water Level Auto Sync")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setCancelButton(None)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setFixedSize(450, 120)
            progress_dialog.show()
            
            # Step 1: Check Google Drive authentication
            progress_dialog.setLabelText("Verifying Google Drive connection...")
            progress_dialog.setValue(5)
            QApplication.processEvents()
            
            if not self.drive_service.get_service():
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Authentication Required", 
                                  "Google Drive authentication required. Please check your service account configuration.")
                return
            
            # Step 2: Initialize consolidated folder monitor
            progress_dialog.setLabelText("Accessing consolidated field data folder...")
            progress_dialog.setValue(15)
            QApplication.processEvents()
            
            consolidated_folder_id = self.settings_handler.get_setting("consolidated_field_data_folder", "")
            if not consolidated_folder_id:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Configuration Missing", 
                                  "Consolidated field data folder not configured. Please run field data consolidation first.")
                return
            
            # Initialize runs monitor for consolidated folder
            from ..handlers.runs_folder_monitor import RunsFolderMonitor
            if not self.runs_monitor:
                self.runs_monitor = RunsFolderMonitor(consolidated_folder_id, self.db_manager.current_db)
                self.runs_monitor.set_authenticated_service(self.drive_service.get_service())
            
            # Step 3: Get water level tab for processing
            progress_dialog.setLabelText("Initializing water level processor...")
            progress_dialog.setValue(25)
            QApplication.processEvents()
            
            water_tab = self.tabs.get("water_level")
            if not water_tab:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Tab Error", "Water level tab not initialized.")
                return
            
            # Step 4: Get active wells from database
            progress_dialog.setLabelText("Checking for active wells...")
            progress_dialog.setValue(35)
            QApplication.processEvents()
            
            active_wells = self._get_active_wells()
            if not active_wells:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No Active Wells", 
                                      "No active wells found in the database.")
                return
            
            logger.info(f"Found {len(active_wells)} active wells to sync")
            
            # Step 5: Check for new files in current and next month folders
            progress_dialog.setLabelText("Scanning consolidated folder for new water level files...")
            progress_dialog.setValue(45)
            QApplication.processEvents()
            
            current_month = datetime.now().strftime("%Y-%m")
            files_found = self._scan_for_water_level_files(current_month, active_wells)
            
            if not files_found:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No New Files", 
                                      "No new water level files found for processing.")
                return
            
            # Step 6: Process found files
            progress_dialog.setLabelText(f"Processing {len(files_found)} new water level files...")
            progress_dialog.setValue(60)
            QApplication.processEvents()
            
            processed_count = self._process_water_level_files(files_found, water_tab, progress_dialog)
            
            progress_dialog.setValue(100)
            progress_dialog.close()
            
            # Show completion message
            if processed_count > 0:
                QMessageBox.information(
                    self.parent, 
                    "Sync Complete", 
                    f"Successfully processed {processed_count} water level files.\n\n"
                    f"Files imported from consolidated folder: {current_month}"
                )
                
                # Refresh water level tab if it exists
                if hasattr(water_tab, 'refresh_data'):
                    water_tab.refresh_data()
            else:
                QMessageBox.information(self.parent, "Sync Complete", 
                                      "No new files were processed during this sync.")
                
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            logger.error(f"Error in auto_sync_water_levels: {e}")
            QMessageBox.critical(self.parent, "Sync Error", 
                               f"An error occurred during water level sync:\n{str(e)}")
    
    def _get_active_barologgers(self):
        """Get list of active barologgers from database"""
        active_barologgers = []
        if self.db_manager.current_db:
            try:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT serial_number FROM barologgers WHERE status = 'active'")
                    active_barologgers = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error getting active barologgers: {e}")
        return active_barologgers
    
    def _get_active_wells(self):
        """Get list of active wells from database"""
        active_wells = []
        if self.db_manager.current_db:
            try:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT cae_number FROM wells WHERE cae_number IS NOT NULL AND cae_number != ''")
                    active_wells = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error getting active wells: {e}")
        return active_wells
    
    def _scan_for_barologger_files(self, current_month, active_barologgers):
        """Scan consolidated folder for new barologger files"""
        files_found = []
        try:
            # Get month folders to scan
            folders = self.runs_monitor.get_month_folders(current_month)
            
            service = self.drive_service.get_service()
            if not service:
                return files_found
            
            # Scan each available folder
            for folder_name, folder_id in folders.items():
                if folder_id:
                    # Look for XLE files containing barologger serial numbers
                    for serial_number in active_barologgers:
                        query = f"'{folder_id}' in parents and name contains '{serial_number}' and fileExtension = 'xle' and trashed = false"
                        
                        try:
                            results = service.files().list(
                                q=query,
                                fields="files(id, name, modifiedTime)",
                                spaces='drive'
                            ).execute()
                            
                            for file in results.get('files', []):
                                # Check if this file is newer than our last import
                                if self._is_newer_barologger_file(file, serial_number):
                                    files_found.append({
                                        'file_id': file['id'],
                                        'name': file['name'],
                                        'serial_number': serial_number,
                                        'folder_name': folder_name
                                    })
                                    
                        except Exception as e:
                            logger.error(f"Error scanning folder {folder_name} for barologger {serial_number}: {e}")
                            
        except Exception as e:
            logger.error(f"Error scanning for barologger files: {e}")
            
        return files_found
    
    def _scan_for_water_level_files(self, current_month, active_wells):
        """Scan consolidated folder for new water level files"""
        files_found = []
        try:
            # Get month folders to scan
            folders = self.runs_monitor.get_month_folders(current_month)
            
            service = self.drive_service.get_service()
            if not service:
                return files_found
            
            # Scan each available folder
            for folder_name, folder_id in folders.items():
                if folder_id:
                    # Look for XLE files containing well CAE numbers
                    for cae_number in active_wells:
                        query = f"'{folder_id}' in parents and name contains '{cae_number}' and fileExtension = 'xle' and trashed = false"
                        
                        try:
                            results = service.files().list(
                                q=query,
                                fields="files(id, name, modifiedTime)",
                                spaces='drive'
                            ).execute()
                            
                            for file in results.get('files', []):
                                # Check if this file is newer than our last import
                                if self._is_newer_water_level_file(file, cae_number):
                                    files_found.append({
                                        'file_id': file['id'],
                                        'name': file['name'],
                                        'cae_number': cae_number,
                                        'folder_name': folder_name
                                    })
                                    
                        except Exception as e:
                            logger.error(f"Error scanning folder {folder_name} for well {cae_number}: {e}")
                            
        except Exception as e:
            logger.error(f"Error scanning for water level files: {e}")
            
        return files_found
    
    def _is_newer_barologger_file(self, file, serial_number):
        """Check if barologger file is newer than last import"""
        try:
            # Get last import date for this barologger
            if self.db_manager.current_db:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT MAX(end_date) FROM barologger_imported_files WHERE serial_number = ?", 
                        (serial_number,)
                    )
                    result = cursor.fetchone()
                    if result and result[0]:
                        last_import = datetime.fromisoformat(result[0])
                        
                        # Extract end date from filename
                        file_end_date = self.runs_monitor.extract_date_from_filename(file['name'])
                        if file_end_date and file_end_date > last_import:
                            return True
                        return False
            return True  # No previous import, process the file
        except Exception as e:
            logger.error(f"Error checking if barologger file is newer: {e}")
            return True  # When in doubt, process the file
    
    def _is_newer_water_level_file(self, file, cae_number):
        """Check if water level file is newer than last import"""
        try:
            # Get last import date for this well
            if self.db_manager.current_db:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT MAX(date_time) FROM water_levels WHERE well_number IN (SELECT well_number FROM wells WHERE cae_number = ?)", 
                        (cae_number,)
                    )
                    result = cursor.fetchone()
                    if result and result[0]:
                        last_reading = datetime.fromisoformat(result[0])
                        
                        # Extract end date from filename
                        file_end_date = self.runs_monitor.extract_date_from_filename(file['name'])
                        if file_end_date and file_end_date > last_reading:
                            return True
                        return False
            return True  # No previous readings, process the file
        except Exception as e:
            logger.error(f"Error checking if water level file is newer: {e}")
            return True  # When in doubt, process the file
    
    def _process_barologger_files(self, files_found, baro_tab, progress_dialog):
        """Process found barologger files"""
        processed_count = 0
        total_files = len(files_found)
        
        for i, file_info in enumerate(files_found):
            try:
                # Update progress
                progress = 60 + (i / total_files) * 35  # 60-95% of total progress
                progress_dialog.setValue(int(progress))
                progress_dialog.setLabelText(f"Processing {file_info['name']} ({i+1}/{total_files})...")
                QApplication.processEvents()
                
                # Download file to temporary location
                temp_file = self._download_file_to_temp(file_info['file_id'], file_info['name'])
                if temp_file:
                    # Process with the barologger tab
                    if hasattr(baro_tab, 'process_single_file'):
                        success = baro_tab.process_single_file(temp_file)
                        if success:
                            processed_count += 1
                            logger.info(f"Successfully processed barologger file: {file_info['name']}")
                            
                            # Track the change if we have a change tracker
                            if self.db_manager.change_tracker:
                                from ..handlers.change_tracker import ChangeType, ChangeAction
                                self.db_manager.change_tracker.track_change(
                                    change_type=ChangeType.AUTOMATIC,
                                    action=ChangeAction.INSERT,
                                    table_name="barologger_data",
                                    record_id=file_info['serial_number'],
                                    description=f"Auto-imported barologger file: {file_info['name']}",
                                    context={
                                        "file_name": file_info['name'],
                                        "folder": file_info['folder_name'],
                                        "import_method": "auto_sync"
                                    }
                                )
                        else:
                            logger.warning(f"Failed to process barologger file: {file_info['name']}")
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                else:
                    logger.error(f"Failed to download barologger file: {file_info['name']}")
                    
            except Exception as e:
                logger.error(f"Error processing barologger file {file_info['name']}: {e}")
                
        return processed_count
    
    def _process_water_level_files(self, files_found, water_tab, progress_dialog):
        """Process found water level files"""
        processed_count = 0
        total_files = len(files_found)
        
        for i, file_info in enumerate(files_found):
            try:
                # Update progress
                progress = 60 + (i / total_files) * 35  # 60-95% of total progress
                progress_dialog.setValue(int(progress))
                progress_dialog.setLabelText(f"Processing {file_info['name']} ({i+1}/{total_files})...")
                QApplication.processEvents()
                
                # Download file to temporary location
                temp_file = self._download_file_to_temp(file_info['file_id'], file_info['name'])
                if temp_file:
                    # Process with the water level tab
                    if hasattr(water_tab, 'process_single_file'):
                        success = water_tab.process_single_file(temp_file)
                        if success:
                            processed_count += 1
                            logger.info(f"Successfully processed water level file: {file_info['name']}")
                            
                            # Track the change if we have a change tracker
                            if self.db_manager.change_tracker:
                                from ..handlers.change_tracker import ChangeType, ChangeAction
                                self.db_manager.change_tracker.track_change(
                                    change_type=ChangeType.AUTOMATIC,
                                    action=ChangeAction.INSERT,
                                    table_name="water_levels",
                                    record_id=file_info['cae_number'],
                                    description=f"Auto-imported water level file: {file_info['name']}",
                                    context={
                                        "file_name": file_info['name'],
                                        "folder": file_info['folder_name'],
                                        "import_method": "auto_sync"
                                    }
                                )
                        else:
                            logger.warning(f"Failed to process water level file: {file_info['name']}")
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                else:
                    logger.error(f"Failed to download water level file: {file_info['name']}")
                    
            except Exception as e:
                logger.error(f"Error processing water level file {file_info['name']}: {e}")
                
        return processed_count
    
    def _download_file_to_temp(self, file_id, filename):
        """Download a file from Google Drive to a temporary location"""
        try:
            service = self.drive_service.get_service()
            if not service:
                return None
                
            # Create temp file
            temp_dir = tempfile.gettempdir()
            safe_filename = filename.replace('/', '_').replace('\\', '_')
            temp_path = os.path.join(temp_dir, f"auto_sync_{safe_filename}")
            
            # Download file
            request = service.files().get_media(fileId=file_id)
            with open(temp_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading file {filename}: {e}")
            return None