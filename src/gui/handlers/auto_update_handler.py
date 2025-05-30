# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 12:16:46 2025

@author: bledesma
"""

# src/gui/handlers/auto_update_handler.py

import os
import logging
import sqlite3
import tempfile
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import QProgressDialog, QMessageBox, QApplication
from PyQt5.QtCore import Qt, QTimer
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

class AutoUpdateHandler:
    """Handles automatic updates and synchronization with Google Drive"""
    
    def __init__(self, parent, db_manager, drive_service, drive_monitor, settings_handler, tabs):
        """
        Initialize AutoUpdateHandler
        
        Args:
            parent: Parent window for displaying dialogs
            db_manager: Database manager instance
            drive_service: Google Drive service instance
            drive_monitor: Drive monitor instance (or None)
            settings_handler: Settings handler instance
            tabs: Dictionary of tabs from the main window
        """
        self.parent = parent
        self.db_manager = db_manager
        self.drive_service = drive_service
        self.drive_monitor = drive_monitor
        self.settings_handler = settings_handler
        self.tabs = tabs
        
    def auto_sync_barologgers(self):
        """Run guided or automatic sync for barologger XLE files with Google Drive integration"""
        try:
            # Create progress dialog
            progress_dialog = QProgressDialog("Initializing barologger sync...", None, 0, 100, self.parent)
            progress_dialog.setWindowTitle("Barologger Sync")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setCancelButton(None)  # No cancel button
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setFixedSize(400, 100)
            progress_dialog.show()
            
            # Step 1: Check if we're authenticated with Google Drive
            progress_dialog.setLabelText("Authenticating with Google Drive...")
            progress_dialog.setValue(5)
            
            if not self.drive_service.authenticated:
                if not self._authenticate_google_drive():
                    progress_dialog.close()
                    QMessageBox.warning(self.parent, "Authentication Failed", 
                                      "Failed to authenticate with Google Drive. Sync cannot continue.")
                    return
            
            # Step 2: Initialize Google Drive folders for scanning 'all' directory
            progress_dialog.setLabelText("Checking access to 'all' folder on Google Drive...")
            progress_dialog.setValue(10)
            
            xle_folder_id = self.settings_handler.get_setting("google_drive_xle_folder_id", "")
            if not xle_folder_id:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Folder ID Missing", 
                                  "XLE folder ID not configured. Please set it in Google Drive Settings.")
                return
            
            from ..handlers.google_drive_monitor import GoogleDriveMonitor
            if self.drive_monitor is None:
                self.drive_monitor = GoogleDriveMonitor(xle_folder_id, self.settings_handler)
            else:
                self.drive_monitor.set_folder_id(xle_folder_id)
            
            # Ensure 'all' folder exists and we have access
            if not self.drive_monitor.initialize_folders():
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Folder Error", 
                                  "Failed to access 'all' folder on Google Drive.")
                return
            
            # Step 3: Get barologger tab for processing
            tab = self.tabs.get("barologger")
            if not tab:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Tab Error", "Barologger tab not initialized.")
                return
            
            # Step 4: Initialize folder processor for automatic processing
            progress_dialog.setLabelText("Getting last import dates...")
            progress_dialog.setValue(20)
            
            from ..handlers.baro_folder_processor import BaroFolderProcessor
            processor = BaroFolderProcessor(tab.baro_model if tab else None)
            
            # Step 5: Get last import dates from database
            last_dates = {}
            db = self.db_manager.current_db
            if db:
                with sqlite3.connect(db) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT serial_number, MAX(end_date) FROM barologger_imported_files GROUP BY serial_number")
                    for s, es in cur.fetchall():
                        try:
                            last_dates[s] = datetime.fromisoformat(es)
                        except:
                            pass
            
            progress_dialog.setLabelText("Getting active barologgers...")
            progress_dialog.setValue(25)
            
            # Get list of active barologgers
            active_barologgers = []
            if db:
                with sqlite3.connect(db) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT serial_number FROM barologgers WHERE status = 'active'")
                    active_barologgers = [row[0] for row in cur.fetchall()]
            
            if not active_barologgers:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "No Active Barologgers", 
                                  "No active barologgers found in the database.")
                return
            
            logger.info(f"Found {len(active_barologgers)} active barologgers to check")
            
            # Step 6: Check organized folders for unprocessed files
            progress_dialog.setLabelText("Checking organized folders for new barologger data...")
            progress_dialog.setValue(30)
            
            # Get the 'all' folder ID
            if not hasattr(self.drive_monitor, 'all_folder_id') or not self.drive_monitor.all_folder_id:
                if not self.drive_monitor.initialize_folders():
                    progress_dialog.close()
                    QMessageBox.warning(self.parent, "Folder Error", 
                                      "Failed to initialize organized folder structure in Google Drive.")
                    return
            
            service = self.drive_service.get_service()
            if not service:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Service Error", "Google Drive service not available.")
                return
            
            # This will store files we need to process
            files_to_process = {}
            
            # Get current time for calculating relative dates
            current_time = datetime.now()
            
            # Process each active barologger
            total_barologgers = len(active_barologgers)
            for i, serial_number in enumerate(active_barologgers):
                progress_dialog.setLabelText(f"Checking files for barologger {serial_number} ({i+1}/{total_barologgers})...")
                progress_percent = 30 + (i * 20 // total_barologgers)
                progress_dialog.setValue(progress_percent)
                
                # Get last import date for this barologger
                last_date = last_dates.get(serial_number)
                
                # If we have a last date, only look at files after that date
                if last_date:
                    # Format last date for comparison
                    last_month = last_date.strftime("%Y_%m")
                    
                    # Query for files in all folder matching this barologger that were modified after the last date
                    query = f"name contains '{serial_number.upper()}' and '{self.drive_monitor.all_folder_id}' in parents and trashed = false"
                    
                    try:
                        results = service.files().list(
                            q=query,
                            fields="files(id, name, modifiedTime)",
                            spaces='drive'
                        ).execute()
                        
                        baro_files = results.get('files', [])
                        logger.info(f"Found {len(baro_files)} potential files for barologger {serial_number}")
                        
                        # Filter files by examining their date from filename
                        for file in baro_files:
                            # Extract date range from filename (format: LOCATION_YYYY_MM_DD_To_YYYY_MM_DD.xle)
                            parts = file['name'].split('_')
                            if len(parts) >= 7 and 'To' in parts:
                                try:
                                    # Parse end date from filename (located after "To")
                                    to_index = parts.index('To')
                                    if to_index + 3 <= len(parts):
                                        if parts[-1].endswith('.xle'):
                                            parts[-1] = parts[-1][:-4]  # Remove .xle
                                        
                                        # Extract end date components
                                        if to_index + 3 == len(parts):
                                            # Format: LOCATION_YYYY_MM_DD_To_MM_DD.xle (same year)
                                            end_year = parts[1]
                                            end_month = parts[to_index + 1]
                                            end_day = parts[to_index + 2]
                                        else:
                                            # Format: LOCATION_YYYY_MM_DD_To_YYYY_MM_DD.xle (different years)
                                            end_year = parts[to_index + 1]
                                            end_month = parts[to_index + 2]
                                            end_day = parts[to_index + 3]
                                        
                                        # Construct end date string
                                        end_date_str = f"{end_year}-{end_month}-{end_day}"
                                        file_end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                                        
                                        # Compare with last import date
                                        if file_end_date > last_date:
                                            # This file has data beyond our last import
                                            if serial_number not in files_to_process:
                                                files_to_process[serial_number] = []
                                            
                                            # Store file info for processing
                                            files_to_process[serial_number].append({
                                                'file_id': file['id'],
                                                'name': file['name'],
                                                'end_date': file_end_date
                                            })
                                            logger.info(f"Found new file for {serial_number}: {file['name']} (ends {file_end_date})")
                                except Exception as e:
                                    logger.warning(f"Error parsing date from filename {file['name']}: {e}")
                
                    except Exception as e:
                        logger.error(f"Error querying files for barologger {serial_number}: {e}")
                else:
                    # No previous import, get all files for this barologger
                    query = f"name contains '{serial_number.upper()}' and '{self.drive_monitor.all_folder_id}' in parents and trashed = false"
                    
                    try:
                        results = service.files().list(
                            q=query,
                            fields="files(id, name)",
                            spaces='drive'
                        ).execute()
                        
                        baro_files = results.get('files', [])
                        logger.info(f"Found {len(baro_files)} files for barologger {serial_number} (no previous import)")
                        
                        # Store all files for processing
                        if baro_files:
                            files_to_process[serial_number] = []
                            for file in baro_files:
                                files_to_process[serial_number].append({
                                    'file_id': file['id'],
                                    'name': file['name'],
                                    'end_date': current_time  # Use current time as placeholder
                                })
                    except Exception as e:
                        logger.error(f"Error querying files for barologger {serial_number}: {e}")
            
            # Step 7: If no new files found in either drop folder or organized folders
            if not files_to_process:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No New Data", 
                                      "No new barologger data found that hasn't been imported already.")
                return
            
            # Step 8: Process each new file
            progress_dialog.setLabelText("Processing barologger files...")
            progress_dialog.setValue(50)
            
            total_files = sum(len(files) for files in files_to_process.values())
            logger.info(f"Found {total_files} new files to process for {len(files_to_process)} barologgers")
            
            # This will hold all the data for batch import
            aggregated_data = {}
            temp_files = []
            file_info_map = {}
            
            # Download and prepare data from each file
            processed_count = 0
            for serial_number, file_infos in files_to_process.items():
                aggregated_data[serial_number] = {'data': None, 'overwrite': False}
                all_data_frames = []
                
                for file_info in file_infos:
                    file_id = file_info['file_id']
                    file_name = file_info['name']
                    
                    progress_dialog.setLabelText(f"Downloading {file_name}...")
                    progress_percent = 50 + (processed_count * 20 // total_files)
                    progress_dialog.setValue(progress_percent)
                    
                    # Download file to temp location
                    temp_file = os.path.join(tempfile.gettempdir(), file_name)
                    try:
                        request = service.files().get_media(fileId=file_id)
                        with open(temp_file, 'wb') as f:
                            downloader = MediaIoBaseDownload(f, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                        
                        temp_files.append(temp_file)
                        
                        # Read the file data
                        from ..handlers.solinst_reader import SolinstReader
                        reader = SolinstReader()
                        df, metadata = reader.read_xle(temp_file)
                        
                        if not df.empty:
                            logger.info(f"File {file_name} contains {len(df)} readings from {df['timestamp_utc'].min()} to {df['timestamp_utc'].max()}")
                            all_data_frames.append(df)
                            
                            # Store file info for later database logging
                            file_info_map[temp_file] = {
                                'serial': serial_number,
                                'name': file_name,
                                'metadata': metadata,
                                'start_date': df['timestamp_utc'].min(),
                                'end_date': df['timestamp_utc'].max(),
                                'count': len(df)
                            }
                        else:
                            logger.warning(f"File {file_name} contains no data, skipping")
                    except Exception as e:
                        logger.error(f"Error processing file {file_name}: {e}")
                    
                    processed_count += 1
                
                # Combine all dataframes for this serial number
                if all_data_frames:
                    combined_df = pd.concat(all_data_frames)
                    combined_df = combined_df.sort_values('timestamp_utc')
                    aggregated_data[serial_number]['data'] = combined_df
            
            # Step 9: Batch import all the data
            progress_dialog.setLabelText("Importing data to database...")
            progress_dialog.setValue(70)
            
            # Define progress callback
            def update_import_progress(current, total, message):
                progress_percent = 70 + (current * 20 // total)
                progress_dialog.setValue(progress_percent)
                progress_dialog.setLabelText(message)
            
            # Perform batch import
            success, message = tab.baro_model.batch_import_readings(
                aggregated_data,
                progress_callback=update_import_progress
            )
            
            if success:
                # Step 10: Log imported files to database
                progress_dialog.setLabelText("Logging imported files...")
                progress_dialog.setValue(90)
                
                try:
                    with sqlite3.connect(db) as conn:
                        cursor = conn.cursor()
                        
                        for temp_file, info in file_info_map.items():
                            # Convert timestamps to ISO format strings for SQLite compatibility
                            start_date_str = info['start_date'].strftime('%Y-%m-%d %H:%M:%S')
                            end_date_str = info['end_date'].strftime('%Y-%m-%d %H:%M:%S')
                            
                            # Insert record for this specific file
                            cursor.execute('''
                                INSERT INTO barologger_imported_files
                                (serial_number, starting_date, end_date)
                                VALUES (?, ?, ?)
                            ''', (info['serial'], start_date_str, end_date_str))
                            
                            logger.info(f"Logged file: {info['name']} ({info['start_date']} to {info['end_date']})")
                        
                        conn.commit()
                except Exception as e:
                    logger.error(f"Error logging imported files: {e}")
                
                # Step 11: Clean up temp files
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except Exception as e:
                        logger.error(f"Error removing temp file {temp_file}: {e}")
                
                # Step 12: Refresh only the barologger tab
                if tab and hasattr(tab, 'refresh_data') and callable(tab.refresh_data):
                    logger.info("Refreshing barologger tab")
                    QTimer.singleShot(100, tab.refresh_data)
                
                progress_dialog.setLabelText("Import complete!")
                progress_dialog.setValue(100)
                QTimer.singleShot(500, progress_dialog.close)
                
                # Ask about creating master baro
                reply = QMessageBox.question(self.parent, "Create Master Baro", 
                                          f"Successfully processed {processed_count} new barologger files.\n\n"
                                          "Do you want to compute the master baro series?",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes and tab:
                    tab.create_master_baro()
            else:
                # Import failed
                progress_dialog.close()
                QMessageBox.critical(self.parent, "Import Failed", message)
                
        except Exception as e:
            logger.error(f"Error in auto_sync_barologgers: {e}")
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QMessageBox.critical(self.parent, "Error", f"An error occurred during synchronization: {str(e)}")
    
    def auto_sync_water_levels(self):
        """Run guided or automatic sync for water level XLE files with Google Drive integration"""
        try:
            # Create progress dialog
            progress_dialog = QProgressDialog("Initializing water level sync...", None, 0, 100, self.parent)
            progress_dialog.setWindowTitle("Water Level Sync")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setCancelButton(None)  # No cancel button
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setFixedSize(400, 100)
            progress_dialog.show()
            
            # Step 1: Check if we're authenticated with Google Drive
            progress_dialog.setLabelText("Authenticating with Google Drive...")
            progress_dialog.setValue(5)
            
            if not self.drive_service.authenticated:
                if not self._authenticate_google_drive():
                    progress_dialog.close()
                    QMessageBox.warning(self.parent, "Authentication Failed", 
                                      "Failed to authenticate with Google Drive. Sync cannot continue.")
                    return
            
            # Step 2: Initialize Google Drive folders for scanning 'all' directory
            progress_dialog.setLabelText("Checking access to 'all' folder on Google Drive...")
            progress_dialog.setValue(10)
            
            xle_folder_id = self.settings_handler.get_setting("google_drive_xle_folder_id", "")
            if not xle_folder_id:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Folder ID Missing", 
                                  "XLE folder ID not configured. Please set it in Google Drive Settings.")
                return
            
            from ..handlers.google_drive_monitor import GoogleDriveMonitor
            if self.drive_monitor is None:
                self.drive_monitor = GoogleDriveMonitor(xle_folder_id, self.settings_handler)
            else:
                self.drive_monitor.set_folder_id(xle_folder_id)
            
            # Ensure 'all' folder exists and we have access
            if not self.drive_monitor.initialize_folders():
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Folder Error", 
                                  "Failed to access 'all' folder on Google Drive.")
                return
            
            # Step 3: Get water level tab for processing
            tab = self.tabs.get("water_level")
            if not tab:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Tab Error", "Water Level tab not initialized.")
                return
            
            # Step 4: Initialize folder processor for automatic processing
            progress_dialog.setLabelText("Getting last import dates...")
            progress_dialog.setValue(20)
            
            from ..handlers.water_level_folder_handler import WaterLevelFolderProcessor
            processor = WaterLevelFolderProcessor(tab.water_level_model)
            
            # Step 5: Get last import dates from database
            import sqlite3
            last_dates = {}
            db = self.db_manager.current_db
            if db:
                with sqlite3.connect(db) as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT serial_number, well_number, MAX(end_date) 
                        FROM transducer_imported_files 
                        GROUP BY serial_number, well_number
                    """)
                    for s, w, es in cur.fetchall():
                        try:
                            if s not in last_dates:
                                last_dates[s] = {}
                            last_dates[s][w] = datetime.fromisoformat(es)
                        except:
                            pass
            
            # Step 6: Get active transducers
            progress_dialog.setLabelText("Getting active transducers...")
            progress_dialog.setValue(25)
            
            active_transducers = {}
            if db:
                with sqlite3.connect(db) as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT t.serial_number, t.well_number, w.cae_number  
                        FROM transducers t
                        JOIN wells w ON t.well_number = w.well_number
                        WHERE t.end_date IS NULL
                    """)
                    for row in cur.fetchall():
                        serial, well, cae = row
                        active_transducers[serial] = {
                            'well_number': well,
                            'cae_number': cae
                        }
            
            if not active_transducers:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "No Active Transducers", 
                                  "No active transducers found in the database.")
                return
            
            logger.info(f"Found {len(active_transducers)} active transducers to check")
            
            # Step 7: Check organized folders for unprocessed files
            progress_dialog.setLabelText("Checking for new water level files...")
            progress_dialog.setValue(30)
            
            # Get the 'all' folder ID
            if not hasattr(self.drive_monitor, 'all_folder_id') or not self.drive_monitor.all_folder_id:
                if not self.drive_monitor.initialize_folders():
                    progress_dialog.close()
                    QMessageBox.warning(self.parent, "Folder Error", 
                                      "Failed to initialize organized folder structure in Google Drive.")
                    return
            
            service = self.drive_service.get_service()
            if not service:
                progress_dialog.close()
                QMessageBox.warning(self.parent, "Service Error", "Google Drive service not available.")
                return
            
            # This will store files we need to process
            files_to_process = {}
            
            # Get current time for calculating relative dates
            current_time = datetime.now()
            
            # Process each active transducer
            total_transducers = len(active_transducers)
            for i, (serial_number, info) in enumerate(active_transducers.items()):
                well_number = info['well_number']
                cae_number = info['cae_number']
                
                progress_dialog.setLabelText(f"Checking files for transducer {serial_number} ({i+1}/{total_transducers})...")
                progress_percent = 30 + (i * 20 // total_transducers)
                progress_dialog.setValue(progress_percent)
                
                # Get last import date for this transducer + well combo
                last_date = last_dates.get(serial_number, {}).get(well_number)
                
                # Query for files matching this transducer in the "all" folder
                query = f"name contains '{serial_number.upper()}' and '{self.drive_monitor.all_folder_id}' in parents and trashed = false"
                
                try:
                    results = service.files().list(
                        q=query,
                        fields="files(id, name, modifiedTime)",
                        spaces='drive'
                    ).execute()
                    
                    transducer_files = results.get('files', [])
                    logger.info(f"Found {len(transducer_files)} potential files for transducer {serial_number}")
                    
                    # Filter files by examining both serial number and location in filename 
                    for file in transducer_files:
                        try:
                            if last_date:
                                # Extract date range from filename (format: SERIAL_LOCATION_YYYY_MM_DD_To_YYYY_MM_DD.xle)
                                parts = file['name'].split('_')
                                if len(parts) >= 7 and 'To' in parts:
                                    # Get the end date position (after "To")
                                    to_index = parts.index('To')
                                    if to_index + 3 <= len(parts):
                                        if parts[-1].endswith('.xle'):
                                            parts[-1] = parts[-1][:-4]  # Remove .xle
                                        
                                        # Extract end date components
                                        if to_index + 3 == len(parts):
                                            # Format: SERIAL_LOCATION_YYYY_MM_DD_To_MM_DD.xle (same year)
                                            end_year = parts[2]  # Year should be in the third position
                                            end_month = parts[to_index + 1]
                                            end_day = parts[to_index + 2]
                                        else:
                                            # Format: SERIAL_LOCATION_YYYY_MM_DD_To_YYYY_MM_DD.xle
                                            end_year = parts[to_index + 1]
                                            end_month = parts[to_index + 2]
                                            end_day = parts[to_index + 3]
                                        
                                        # Construct end date string
                                        end_date_str = f"{end_year}-{end_month}-{end_day}"
                                        file_end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                                        
                                        # Compare with last import date
                                        if file_end_date > last_date:
                                            # This file has data beyond our last import
                                            if well_number not in files_to_process:
                                                files_to_process[well_number] = []
                                            
                                            # Store file info for processing
                                            files_to_process[well_number].append({
                                                'file_id': file['id'],
                                                'name': file['name'],
                                                'serial_number': serial_number,
                                                'end_date': file_end_date
                                            })
                                            logger.info(f"Found new file for {serial_number}/{well_number}: {file['name']} (ends {file_end_date})")
                            else:
                                # No previous import date, include file if it matches our active transducer
                                if well_number not in files_to_process:
                                    files_to_process[well_number] = []
                                
                                files_to_process[well_number].append({
                                    'file_id': file['id'],
                                    'name': file['name'],
                                    'serial_number': serial_number,
                                    'end_date': current_time  # Placeholder
                                })
                                logger.info(f"Found file for {serial_number}/{well_number} (no previous import): {file['name']}")
                        except Exception as e:
                            logger.warning(f"Error processing filename {file['name']}: {e}")
                
                except Exception as e:
                    logger.error(f"Error querying files for transducer {serial_number}: {e}")
            
            # Step 8: If no new files found
            if not files_to_process:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No New Data", 
                                      "No new water level data found that hasn't been imported already.")
                return
            
            # Step 9: Process each new file
            progress_dialog.setLabelText("Processing water level files...")
            progress_dialog.setValue(50)
            
            total_files = sum(len(files) for files in files_to_process.values())
            logger.info(f"Found {total_files} new files to process for {len(files_to_process)} wells")
            
            # Download and prepare all files for batch processing
            from ..dialogs.water_level_progress_dialog import WaterLevelProgressDialog
            
            # Initialize file organizer for post-processing file organization
            from ..utils.file_organizer import XLEFileOrganizer
            app_root_dir = Path(db).parent if db else Path.cwd()
            file_organizer = XLEFileOrganizer(app_root_dir)
            
            # Create a temporary directory for downloaded files
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())
            temp_files = []
            
            try:
                # First download all files
                download_progress = 0
                
                for well_number, file_infos in files_to_process.items():
                    for file_info in file_infos:
                        file_id = file_info['file_id']
                        file_name = file_info['name']
                        
                        progress_dialog.setLabelText(f"Downloading {file_name}...")
                        progress_percent = 50 + (download_progress * 10 // total_files)
                        progress_dialog.setValue(progress_percent)
                        
                        # Download file to temp location
                        temp_file = temp_dir / file_name
                        try:
                            request = service.files().get_media(fileId=file_id)
                            with open(temp_file, 'wb') as f:
                                downloader = MediaIoBaseDownload(f, request)
                                done = False
                                while not done:
                                    status, done = downloader.next_chunk()
                            
                            temp_files.append(str(temp_file))
                            file_info['path'] = str(temp_file)
                            logger.info(f"Downloaded {file_name} to {temp_file}")
                        except Exception as e:
                            logger.error(f"Error downloading file {file_name}: {e}")
                        
                        download_progress += 1
                
                # Create a detailed progress dialog for processing
                progress_dialog.close()  # Close the simple progress dialog
                
                process_dialog = WaterLevelProgressDialog(self.parent)
                process_dialog.setWindowTitle("Water Level Sync")
                process_dialog.show()
                process_dialog.log_message("=== Starting Water Level File Processing ===")
                
                # Group files by well
                well_data = {}
                for well_number, file_infos in files_to_process.items():
                    well_data[well_number] = {
                        'files': [Path(file_info['path']) for file_info in file_infos if 'path' in file_info],
                        'serial_number': file_infos[0]['serial_number'] if file_infos else None
                    }
                    process_dialog.log_message(f"Well {well_number}: {len(well_data[well_number]['files'])} files to process")
                
                # Process all files using the WaterLevelFolderProcessor
                scan_results = {}
                for well_number, data in well_data.items():
                    if process_dialog.was_canceled():
                        break
                    
                    process_dialog.log_message(f"\n=== Processing Well {well_number} ===")
                    
                    # Create a folder-like structure for scan_folder
                    folder_path = temp_dir / well_number
                    folder_path.mkdir(exist_ok=True)
                    
                    # Move files to well folder
                    for file_path in data['files']:
                        shutil.copy(file_path, folder_path)
                    
                    # Scan the folder
                    process_dialog.log_message(f"Scanning folder for well {well_number}...")
                    scan_result = processor.scan_folder(folder_path, include_subfolders=False, progress_dialog=process_dialog)
                    
                    if 'error' in scan_result:
                        process_dialog.log_message(f"Error scanning folder: {scan_result['error']}")
                        continue
                    
                    if well_number in scan_result:
                        # Process the files
                        process_dialog.log_message(f"Processing files for well {well_number}...")
                        scan_result = processor.process_files(scan_result, progress_dialog=process_dialog)
                        scan_results[well_number] = scan_result[well_number]
                
                # Step 10: Import data to database
                process_dialog.log_message("\n=== Importing Data to Database ===")
                
                imported_count = 0
                for well_number, well_info in scan_results.items():
                    if process_dialog.was_canceled():
                        break
                    
                    if not well_info.get('has_been_processed', False):
                        process_dialog.log_message(f"Skipping well {well_number} - not processed")
                        continue
                    
                    if 'processed_data' not in well_info:
                        process_dialog.log_message(f"No processed data for well {well_number}")
                        continue
                    
                    process_dialog.log_message(f"Importing data for well {well_number}...")
                    
                    # Get transducer serial number
                    serial_number = well_info.get('metadata', {}).serial_number
                    if not serial_number:
                        for file_info in files_to_process.get(well_number, []):
                            if file_info.get('serial_number'):
                                serial_number = file_info['serial_number']
                                break
                    
                    if not serial_number:
                        process_dialog.log_message(f"Could not determine serial number for well {well_number}")
                        continue
                    
                    # Import the processed data
                    try:
                        overwrite = well_info.get('has_overlap', False)
                        success = tab.water_level_model.import_readings(
                            well_info['processed_data'], 
                            well_number, 
                            serial_number,
                            overwrite=overwrite
                        )
                        
                        if success:
                            imported_count += 1
                            process_dialog.log_message(f"Successfully imported {len(well_info['processed_data'])} readings for well {well_number}")
                            
                            # Log to transducer_imported_files table
                            time_range = well_info.get('time_range')
                            if time_range and db:
                                with sqlite3.connect(db) as conn:
                                    cursor = conn.cursor()
                                    start_date_str = time_range[0].strftime('%Y-%m-%d %H:%M:%S')
                                    end_date_str = time_range[1].strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    cursor.execute('''
                                        INSERT INTO transducer_imported_files
                                        (well_number, serial_number, starting_date, end_date)
                                        VALUES (?, ?, ?, ?)
                                    ''', (well_number, serial_number, start_date_str, end_date_str))
                                    
                                    conn.commit()
                                    
                                process_dialog.log_message(f"Logged import for {well_number} from {start_date_str} to {end_date_str}")
                            
                            # Organize the files
                            for file_path in well_info['files']:
                                if isinstance(file_path, Path) and file_path.exists():
                                    cae_number = None
                                    for t_serial, t_info in active_transducers.items():
                                        if t_serial == serial_number:
                                            cae_number = t_info.get('cae_number')
                                            break
                                    
                                    try:
                                        # Read file metadata
                                        from ..handlers.solinst_reader import SolinstReader
                                        reader = SolinstReader()
                                        _, metadata = reader.get_file_metadata(file_path)
                                        
                                        # Organize file
                                        location = cae_number or metadata.location
                                        organized_path = file_organizer.organize_water_level_file(
                                            file_path,
                                            serial_number,
                                            location,
                                            metadata.start_time,
                                            metadata.stop_time
                                        )
                                        
                                        if organized_path:
                                            process_dialog.log_message(f"Organized file: {organized_path}")
                                    except Exception as e:
                                        logger.error(f"Error organizing file {file_path}: {e}")
                        else:
                            process_dialog.log_message(f"Failed to import data for well {well_number}")
                    except Exception as e:
                        logger.error(f"Error importing data for well {well_number}: {e}")
                        process_dialog.log_message(f"Error importing data: {str(e)}")
                
                # Step 11: Clean up
                process_dialog.log_message("\n=== Cleaning Up ===")
                
                # Clean up temp directory
                try:
                    shutil.rmtree(temp_dir)
                    process_dialog.log_message("Removed temporary directory")
                except Exception as e:
                    logger.error(f"Error removing temp directory: {e}")
                
                # Step 12: Refresh the water level tab
                if imported_count > 0:
                    process_dialog.log_message("\n=== Updating UI ===")
                    if tab and hasattr(tab, 'refresh_data') and callable(tab.refresh_data):
                        QTimer.singleShot(100, tab.refresh_data)
                        process_dialog.log_message("Refreshing water level tab")
                
                # Finish
                process_dialog.log_message("\n=== Import Complete ===")
                process_dialog.log_message(f"Successfully imported data for {imported_count} wells")
                process_dialog.finish_operation()
                
                QMessageBox.information(self.parent, "Import Complete", 
                                      f"Successfully imported water level data for {imported_count} wells.")
                
            except Exception as e:
                logger.error(f"Error processing water level files: {e}")
                QMessageBox.critical(self.parent, "Error", f"An error occurred during processing: {str(e)}")
                # Ensure dialog is closed if error occurred in processing
                if 'process_dialog' in locals() and process_dialog:
                    process_dialog.close()
            
        except Exception as e:
            logger.error(f"Error in auto_sync_water_levels: {e}")
            if 'progress_dialog' in locals() and progress_dialog:
                progress_dialog.close()
            QMessageBox.critical(self.parent, "Error", f"An error occurred during synchronization: {str(e)}")
            
    def _authenticate_google_drive(self):
        """Authenticate with Google Drive"""
        # This would typically call the parent's authenticate_google_drive method
        # Since we don't have direct access, we'll return True for now and rely on drive_service.authenticated check
        return True
