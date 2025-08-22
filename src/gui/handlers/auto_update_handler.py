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
import shutil
import json
from datetime import datetime
from pathlib import Path
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
            logger.info("AUTO_SYNC_DEBUG: Starting barologger auto-sync...")
            
            # Create progress dialog
            progress_dialog = QProgressDialog("Initializing barologger sync...", None, 0, 100, self.parent)
            progress_dialog.setWindowTitle("Barologger Auto Sync")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setCancelButton(None)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setFixedSize(450, 120)
            progress_dialog.show()
            
            # Step 1: Run field data file sync to ensure all files are organized in SMOO
            progress_dialog.setLabelText("Syncing field data files to SMOO...")
            progress_dialog.setValue(5)
            QApplication.processEvents()
            
            logger.info("AUTO_SYNC_DEBUG: Running field data sync to organize new files in SMOO...")
            
            # Call the working sync_field_data_files_only method
            try:
                # This method handles Google Drive → SMOO file organization
                # It's the same process as the "Sync Field Data Files Only" button
                self.parent.sync_field_data_files_only()
                logger.info("AUTO_SYNC_DEBUG: Field data sync completed successfully")
                
                # Update progress after sync completion
                progress_dialog.setLabelText("Field data sync completed")
                progress_dialog.setValue(15)
                QApplication.processEvents()
                
            except Exception as sync_error:
                logger.error(f"AUTO_SYNC_DEBUG: Field data sync failed: {sync_error}")
                progress_dialog.close()
                QMessageBox.warning(
                    self.parent, 
                    "Field Data Sync Failed", 
                    f"Failed to sync field data files from Google Drive to SMOO:\n\n{str(sync_error)}\n\n"
                    "Auto-sync requires organized field data to function properly."
                )
                return
            
            # Step 2: Initialize SMOO folder scanner for database import
            progress_dialog.setLabelText("Accessing SMOO consolidated data folder...")
            progress_dialog.setValue(20)
            QApplication.processEvents()
            
            logger.info("AUTO_SYNC_DEBUG: Initializing SMOO folder scanner for database import...")
            
            try:
                # Initialize SMOO scanner (replaces Google Drive API scanning)
                from ..handlers.smoo_folder_scanner import SMOOFolderScanner
                self.smoo_scanner = SMOOFolderScanner(self.db_manager.current_db)
                logger.info("AUTO_SYNC_DEBUG: SMOO folder scanner initialized successfully")
                
            except Exception as scanner_error:
                logger.error(f"AUTO_SYNC_DEBUG: Failed to initialize SMOO scanner: {scanner_error}")
                progress_dialog.close()
                QMessageBox.warning(
                    self.parent, 
                    "SMOO Access Error", 
                    f"Could not access SMOO consolidated folder:\n\n{str(scanner_error)}\n\n"
                    "Please ensure:\n"
                    "1. VPN connection is active\n"
                    "2. SMOO drive is mounted\n"
                    "3. Field data files have been synced to SMOO"
                )
                return
            
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
            
            # Step 3: Scan SMOO for new barologger files
            progress_dialog.setLabelText("Scanning SMOO for new barologger files...")
            progress_dialog.setValue(45)
            QApplication.processEvents()
            
            current_month = datetime.now().strftime("%Y-%m")
            logger.info(f"AUTO_SYNC_DEBUG: Starting barologger scan in current month: {current_month}")
            logger.info(f"AUTO_SYNC_DEBUG: Active barologgers to check: {active_barologgers}")
            files_found = self._scan_smoo_for_barologger_files(current_month, active_barologgers)
            
            logger.info(f"AUTO_SYNC_DEBUG: Files found during scan: {len(files_found)}")
            if files_found:
                for f in files_found:
                    logger.info(f"  - Found file: {f['name']} (Serial: {f['serial_number']}, Folder: {f['folder_name']})")
            
            if not files_found:
                progress_dialog.close()
                QMessageBox.information(self.parent, "No New Files", 
                                      "No new barologger files found for processing.\n\n"
                                      "Check the logs for detailed scanning information.")
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
            
            # Step 1: Run field data file sync to ensure all files are organized in SMOO
            progress_dialog.setLabelText("Syncing field data files to SMOO...")
            progress_dialog.setValue(5)
            QApplication.processEvents()
            
            logger.info("Running field data sync to organize new files in SMOO...")
            
            # Call the working sync_field_data_files_only method
            try:
                # This method handles Google Drive → SMOO file organization
                # It's the same process as the "Sync Field Data Files Only" button
                self.parent.sync_field_data_files_only()
                logger.info("Field data sync completed successfully")
                
                # Update progress after sync completion
                progress_dialog.setLabelText("Field data sync completed")
                progress_dialog.setValue(15)
                QApplication.processEvents()
                
            except Exception as sync_error:
                logger.error(f"Field data sync failed: {sync_error}")
                progress_dialog.close()
                QMessageBox.warning(
                    self.parent, 
                    "Field Data Sync Failed", 
                    f"Failed to sync field data files from Google Drive to SMOO:\n\n{str(sync_error)}\n\n"
                    "Auto-sync requires organized field data to function properly."
                )
                return
            
            # Step 2: Initialize SMOO folder scanner for database import
            progress_dialog.setLabelText("Accessing SMOO consolidated data folder...")
            progress_dialog.setValue(20)
            QApplication.processEvents()
            
            logger.info("Initializing SMOO folder scanner for database import...")
            
            try:
                # Initialize SMOO scanner (replaces Google Drive API scanning)
                from ..handlers.smoo_folder_scanner import SMOOFolderScanner
                self.smoo_scanner = SMOOFolderScanner(self.db_manager.current_db)
                logger.info("SMOO folder scanner initialized successfully")
                
            except Exception as scanner_error:
                logger.error(f"Failed to initialize SMOO scanner: {scanner_error}")
                progress_dialog.close()
                QMessageBox.warning(
                    self.parent, 
                    "SMOO Access Error", 
                    f"Could not access SMOO consolidated folder:\n\n{str(scanner_error)}\n\n"
                    "Please ensure:\n"
                    "1. VPN connection is active\n"
                    "2. SMOO drive is mounted\n"
                    "3. Field data files have been synced to SMOO"
                )
                return
            
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
            
            # Step 3: Scan SMOO for new water level files
            progress_dialog.setLabelText("Scanning SMOO for new water level files...")
            progress_dialog.setValue(45)
            QApplication.processEvents()
            
            current_month = datetime.now().strftime("%Y-%m")
            files_found = self._scan_smoo_for_water_level_files(current_month, active_wells)
            
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
            
            # Show completion message and check for Turso sync
            if processed_count > 0:
                # Check if Turso auto-sync is enabled and this is a supported project
                turso_auto_sync = self.settings_handler.get_setting("turso_auto_sync_enabled", False)
                current_project = self.db_manager.cloud_project_name if self.db_manager.is_cloud_database else None
                supported_projects = ["CAESER_GENERAL", "MEGASITE", "SANDY_CREEK"]
                
                if turso_auto_sync and current_project in supported_projects:
                    # Ask user if they want to sync to Turso
                    reply = QMessageBox.question(
                        self.parent,
                        "Sync to Turso",
                        f"Successfully processed {processed_count} water level files.\n\n"
                        f"Do you want to sync the updated {current_project} database to Turso?\n\n"
                        f"This will create an optimized version and upload it to Turso.",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # Use optimized handler that works on all platforms
                        from .turso_handler_optimized import TursoHandlerOptimized
                        turso_handler = TursoHandlerOptimized(self.db_manager, self.settings_handler)
                        turso_handler.sync_to_turso(current_project, self.parent)
                else:
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
        """Scan consolidated folder for new barologger files using metadata.json files"""
        files_found = []
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.error("AUTO_SYNC_DEBUG: Google Drive service not available")
                return files_found
            
            logger.info("AUTO_SYNC_DEBUG: Starting barologger file scan...")
            
            # Get smart month range for each barologger based on last record
            barologger_month_ranges = self._get_barologger_search_ranges(active_barologgers)
            logger.info(f"AUTO_SYNC_DEBUG: Barologger month ranges: {barologger_month_ranges}")
            
            # Check if any barologgers need "ALL_AVAILABLE" search
            needs_all_months = any(
                month_range == "ALL_AVAILABLE" 
                for month_range in barologger_month_ranges.values()
            )
            
            if needs_all_months:
                logger.info("AUTO_SYNC_DEBUG: Some barologgers need ALL_AVAILABLE search, getting all month folders...")
                # Get all available month folders first
                all_available_months = self._get_all_available_month_folders()
                logger.info(f"AUTO_SYNC_DEBUG: Found {len(all_available_months)} available month folders: {sorted(all_available_months.keys())}")
            else:
                all_available_months = {}
            
            # Get all month folders that we need to search
            all_months_needed = set()
            for serial_number in active_barologgers:
                month_range = barologger_month_ranges.get(serial_number, [current_month])
                if month_range == "ALL_AVAILABLE":
                    all_months_needed.update(all_available_months.keys())
                else:
                    all_months_needed.update(month_range)
            
            logger.info(f"AUTO_SYNC_DEBUG: Smart search scope: scanning {len(all_months_needed)} months: {sorted(all_months_needed)}")
            
            # Get folder IDs for all needed months
            if needs_all_months:
                month_folders = all_available_months
            else:
                month_folders = self._get_multiple_month_folders(list(all_months_needed))
            logger.info(f"AUTO_SYNC_DEBUG: Month folder IDs found: {len(month_folders)} folders")
            
            # Scan each barologger in its specific month range using metadata.json
            for serial_number in active_barologgers:
                month_range = barologger_month_ranges.get(serial_number, [current_month])
                if month_range == "ALL_AVAILABLE":
                    month_range = sorted(all_available_months.keys())
                    logger.info(f"AUTO_SYNC_DEBUG: Searching barologger {serial_number} in ALL available months: {month_range}")
                else:
                    logger.info(f"AUTO_SYNC_DEBUG: Searching barologger {serial_number} in specific months: {month_range}")
                
                for month in month_range:
                    folder_id = month_folders.get(month)
                    if folder_id:
                        # Read metadata.json for this month folder
                        metadata_files = self._get_metadata_from_folder(folder_id)
                        logger.info(f"AUTO_SYNC_DEBUG: Found {len(metadata_files)} files in metadata for {month}")
                        
                        for file_metadata in metadata_files:
                            # Check if this file matches our barologger by serial number only
                            if file_metadata.get('serial_number') == serial_number:
                                logger.info(f"  - Checking file: {file_metadata.get('filename', 'UNKNOWN')}")
                                # Check if this file is newer than our last import using metadata dates
                                is_newer = self._is_newer_barologger_file_metadata(file_metadata, serial_number)
                                logger.info(f"    Is newer than last import: {is_newer}")
                                
                                if is_newer:
                                    # Use the correct field name from metadata
                                    file_id_field = file_metadata.get('google_drive_file_id')
                                    if file_id_field:
                                        files_found.append({
                                            'file_id': file_id_field,
                                            'name': file_metadata.get('filename', 'UNKNOWN'),
                                            'serial_number': serial_number,
                                            'folder_name': month,
                                            'metadata': file_metadata
                                        })
                                        logger.info(f"    Added to files_found list")
                                    else:
                                        logger.error(f"AUTO_SYNC_DEBUG: No google_drive_file_id found in metadata: {file_metadata}")
                    else:
                        logger.warning(f"AUTO_SYNC_DEBUG: No folder ID found for month {month}")
                            
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error scanning for barologger files: {e}")
            
        logger.info(f"AUTO_SYNC_DEBUG: Total files found: {len(files_found)}")
        return files_found
    
    def _scan_for_water_level_files(self, current_month, active_wells):
        """Scan consolidated folder for new water level files using metadata.json files"""
        files_found = []
        try:
            service = self.drive_service.get_service()
            if not service:
                return files_found
            
            # Get smart month range for each well based on last record
            well_month_ranges = self._get_water_level_search_ranges(active_wells)
            
            # Check if any wells need "ALL_AVAILABLE" search
            needs_all_months = any(
                month_range == "ALL_AVAILABLE" 
                for month_range in well_month_ranges.values()
            )
            
            if needs_all_months:
                logger.info("Some wells need ALL_AVAILABLE search, getting all month folders...")
                # Get all available month folders first
                all_available_months = self._get_all_available_month_folders()
                logger.info(f"Found {len(all_available_months)} available month folders: {sorted(all_available_months.keys())}")
            else:
                all_available_months = {}
            
            # Get all month folders that we need to search
            all_months_needed = set()
            for cae_number in active_wells:
                month_range = well_month_ranges.get(cae_number, [current_month])
                if month_range == "ALL_AVAILABLE":
                    all_months_needed.update(all_available_months.keys())
                else:
                    all_months_needed.update(month_range)
            
            logger.info(f"Smart search scope for water levels: scanning {len(all_months_needed)} months: {sorted(all_months_needed)}")
            
            # Get folder IDs for all needed months
            if needs_all_months:
                month_folders = all_available_months
            else:
                month_folders = self._get_multiple_month_folders(list(all_months_needed))
            
            # Scan each well in its specific month range using metadata.json
            for cae_number in active_wells:
                month_range = well_month_ranges.get(cae_number, [current_month])
                if month_range == "ALL_AVAILABLE":
                    month_range = sorted(all_available_months.keys())
                    logger.info(f"Searching well {cae_number} in ALL available months: {month_range}")
                else:
                    logger.debug(f"Searching well {cae_number} in specific months: {month_range}")
                
                for month in month_range:
                    folder_id = month_folders.get(month)
                    if folder_id:
                        # Read metadata.json for this month folder
                        metadata_files = self._get_metadata_from_folder(folder_id)
                        logger.debug(f"Found {len(metadata_files)} files in metadata for {month}")
                        
                        for file_metadata in metadata_files:
                            # Check if this file matches our well using location field (original unmodified value)
                            if file_metadata.get('location') == cae_number:
                                logger.debug(f"  - Checking file: {file_metadata['filename']} (location: {file_metadata.get('location')})")
                                # Check if this file is newer than our last import using metadata dates
                                is_newer = self._is_newer_water_level_file_metadata(file_metadata, cae_number)
                                logger.debug(f"    Is newer than last import: {is_newer}")
                                
                                if is_newer:
                                    files_found.append({
                                        'file_id': file_metadata['google_drive_file_id'],
                                        'name': file_metadata['filename'],
                                        'cae_number': cae_number,
                                        'folder_name': month,
                                        'metadata': file_metadata
                                    })
                                    logger.debug(f"    Added to files_found list")
                            
        except Exception as e:
            logger.error(f"Error scanning for water level files: {e}")
            
        return files_found
    
    def _is_newer_barologger_file(self, file, serial_number):
        """Check if barologger file is newer than last actual data"""
        try:
            # Get last actual data timestamp for this barologger (not import metadata)
            if self.db_manager.current_db:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT MAX(timestamp_utc) FROM barometric_readings WHERE serial_number = ?", 
                        (serial_number,)
                    )
                    result = cursor.fetchone()
                    if result and result[0]:
                        last_data_timestamp = datetime.fromisoformat(result[0])
                        
                        # Extract end date from filename
                        file_end_date = self.runs_monitor.extract_date_from_filename(file['name'])
                        if file_end_date and file_end_date > last_data_timestamp:
                            logger.info(f"AUTO_SYNC_DEBUG: File {file['name']} is newer than last data ({last_data_timestamp}) - will process")
                            return True
                        else:
                            logger.info(f"AUTO_SYNC_DEBUG: File {file['name']} is not newer than last data ({last_data_timestamp}) - skipping")
                            return False
            logger.info(f"AUTO_SYNC_DEBUG: No previous data found for {serial_number}, will process file {file['name']}")
            return True  # No previous data, process the file
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error checking if barologger file is newer: {e}")
            return True  # When in doubt, process the file
    
    def _is_newer_water_level_file(self, file, cae_number):
        """Check if water level file is newer than last actual data"""
        try:
            # Get last actual data timestamp for this well
            if self.db_manager.current_db:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    # First get the well_number from cae_number
                    cursor.execute("SELECT well_number FROM wells WHERE cae_number = ?", (cae_number,))
                    well_result = cursor.fetchone()
                    if not well_result:
                        logger.info(f"AUTO_SYNC_DEBUG: No well found for CAE {cae_number}")
                        return True  # No well found, process the file
                    
                    well_number = well_result[0]
                    logger.debug(f"AUTO_SYNC_DEBUG: CAE {cae_number} maps to well_number {well_number}")
                    
                    # Now get the last timestamp from water_level_readings using well_number
                    cursor.execute("SELECT MAX(timestamp_utc) FROM water_level_readings WHERE well_number = ?", (well_number,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        last_data_timestamp = datetime.fromisoformat(result[0])
                        
                        # Extract end date from filename
                        file_end_date = self.runs_monitor.extract_date_from_filename(file['name'])
                        if file_end_date and file_end_date > last_data_timestamp:
                            logger.info(f"AUTO_SYNC_DEBUG: File {file['name']} is newer than last data ({last_data_timestamp}) - will process")
                            return True
                        else:
                            logger.info(f"AUTO_SYNC_DEBUG: File {file['name']} is not newer than last data ({last_data_timestamp}) - skipping")
                            return False
            logger.info(f"AUTO_SYNC_DEBUG: No previous data found for well {cae_number}, will process file {file['name']}")
            return True  # No previous data, process the file
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error checking if water level file is newer: {e}")
            return True  # When in doubt, process the file
    
    def _process_barologger_files(self, files_found, baro_tab, progress_dialog):
        """Process found barologger files using folder-based processing"""
        try:
            total_files = len(files_found)
            logger.info(f"AUTO_SYNC_DEBUG: Starting to process {total_files} barologger files using folder method...")
            
            # Create temporary directory for all files
            temp_dir = tempfile.mkdtemp(prefix="auto_sync_baro_")
            logger.info(f"AUTO_SYNC_DEBUG: Created temp directory: {temp_dir}")
            
            # Copy SMOO files to temp directory for processing
            progress_dialog.setLabelText("Preparing barologger files...")
            progress_dialog.setValue(60)
            QApplication.processEvents()
            
            prepared_files = []
            for i, file_info in enumerate(files_found):
                try:
                    # Update progress for file preparation
                    prep_progress = 60 + (i / total_files) * 20  # 60-80% for file prep
                    progress_dialog.setValue(int(prep_progress))
                    progress_dialog.setLabelText(f"Preparing {file_info['name']} ({i+1}/{total_files})...")
                    QApplication.processEvents()
                    
                    # Copy from SMOO to temp directory for processing
                    source_path = file_info['file_path']
                    temp_file_path = os.path.join(temp_dir, file_info['name'])
                    
                    shutil.copy2(source_path, temp_file_path)
                    
                    prepared_files.append({
                        'path': temp_file_path,
                        'info': file_info
                    })
                    logger.info(f"AUTO_SYNC_DEBUG: Prepared {file_info['name']} from SMOO to {temp_file_path}")
                        
                except Exception as e:
                    logger.error(f"AUTO_SYNC_DEBUG: Error preparing {file_info['name']}: {e}")
            
            if not prepared_files:
                logger.error("AUTO_SYNC_DEBUG: No files prepared successfully")
                return 0
            
            # Process the temp folder using barologger tab's folder processing method
            progress_dialog.setLabelText(f"Processing {len(prepared_files)} barologger files...")
            progress_dialog.setValue(80)
            QApplication.processEvents()
            
            logger.info(f"AUTO_SYNC_DEBUG: Processing temp folder with barologger tab...")
            
            # Use BaroFolderProcessor directly - this is what the import dialog uses
            logger.info("AUTO_SYNC_DEBUG: Using BaroFolderProcessor to process temp folder...")
            
            from ..handlers.baro_folder_processor import BaroFolderProcessor
            from pathlib import Path
            
            # Create processor using the barologger model from the tab
            baro_model = baro_tab.baro_model if hasattr(baro_tab, 'baro_model') else None
            if not baro_model:
                logger.error("AUTO_SYNC_DEBUG: Could not get baro_model from baro_tab")
                return 0
            
            processor = BaroFolderProcessor(baro_model, settings_handler=self.settings_handler)
            
            # Scan the temp folder
            logger.info(f"AUTO_SYNC_DEBUG: Scanning temp folder: {temp_dir}")
            scan_results = processor.scan_folder(Path(temp_dir), include_subfolders=False)
            
            if 'error' in scan_results:
                logger.error(f"AUTO_SYNC_DEBUG: Scan failed: {scan_results['error']}")
                return 0
            
            logger.info(f"AUTO_SYNC_DEBUG: Scan found {scan_results.get('processed_count', 0)} valid files")
            
            # Process each barologger found
            success_count = 0
            for serial_number, file_data in scan_results.get('barologgers', {}).items():
                logger.info(f"AUTO_SYNC_DEBUG: Processing barologger {serial_number} with {len(file_data['files'])} files")
                
                # Process the files for this barologger
                result = processor.process_barologger_files(serial_number, file_data['files'])
                
                if result and result.get('data') is not None:
                    # Import the data using the barologger model directly
                    logger.info(f"AUTO_SYNC_DEBUG: Importing {len(result['data'])} readings for barologger {serial_number}")
                    
                    import_success = baro_model.import_readings(
                        result['data'], 
                        serial_number, 
                        overwrite=False  # Don't overwrite existing data
                    )
                    
                    if import_success:
                        success_count += 1
                        logger.info(f"AUTO_SYNC_DEBUG: Successfully imported data for barologger {serial_number}")
                    else:
                        logger.error(f"AUTO_SYNC_DEBUG: Failed to import data for barologger {serial_number}")
                else:
                    logger.error(f"AUTO_SYNC_DEBUG: No valid data processed for barologger {serial_number}")
            
            success = success_count > 0
            
            if success:
                logger.info(f"AUTO_SYNC_DEBUG: Successfully processed barologger folder with {len(prepared_files)} files")
                
                # Preserve XLE files and track them
                for file_data in prepared_files:
                    file_info = file_data['info']
                    temp_file_path = file_data['path']
                    
                    # Handle XLE file preservation based on database type
                    if self.db_manager.is_cloud_database:
                        # For shared databases: only track files for later push, don't save to SMOO yet
                        self._track_autosync_xle_file(
                            temp_file_path, file_info['serial_number'], file_info['name'], device_type_hint='barologger'
                        )
                        logger.debug("AUTO_SYNC_XLE: Tracked file for push operation (not saved to SMOO yet)")
                    else:
                        # For local databases: save files immediately
                        preserved_file_path = self._preserve_autosync_xle_file(
                            temp_file_path, file_info['name'], file_info['serial_number']
                        )
                        if preserved_file_path:
                            logger.debug("AUTO_SYNC_XLE: Files saved immediately for local database")
                        else:
                            logger.error("AUTO_SYNC_XLE: Failed to preserve XLE file for local database")
                
                # Track the change if we have a change tracker
                if self.db_manager.change_tracker:
                    from ..handlers.change_tracker import ChangeType, ChangeAction
                    self.db_manager.change_tracker.track_change(
                        change_type=ChangeType.AUTOMATIC,
                        action=ChangeAction.INSERT,
                        table_name="barometric_readings",
                        record_id=files_found[0]['serial_number'],  # All files are for same barologger
                        description=f"Auto-imported {len(prepared_files)} barologger files",
                        context={
                            "file_count": len(prepared_files),
                            "import_method": "auto_sync",
                            "temp_folder": temp_dir
                        }
                    )
                
                return len(prepared_files)
            else:
                logger.error("AUTO_SYNC_DEBUG: Barologger folder processing failed")
                return 0
                
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Exception in barologger folder processing: {e}")
            return 0
        finally:
            # Clean up temp directory
            try:
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir)
                    logger.info(f"AUTO_SYNC_DEBUG: Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"AUTO_SYNC_DEBUG: Error cleaning up temp directory: {e}")
    
    def _download_file_to_path(self, file_id, target_path):
        """Download a file from Google Drive to a specific path"""
        try:
            service = self.drive_service.get_service()
            if not service:
                return False
            
            request = service.files().get_media(fileId=file_id)
            
            with open(target_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id} to {target_path}: {e}")
            return False
    
    def _process_water_level_files(self, files_found, water_tab, progress_dialog):
        """Process found water level files using folder-based processing"""
        try:
            total_files = len(files_found)
            logger.info(f"AUTO_SYNC_DEBUG: Starting to process {total_files} water level files using folder method...")
            
            # Create temporary directory for all files
            temp_dir = tempfile.mkdtemp(prefix="auto_sync_water_")
            logger.info(f"AUTO_SYNC_DEBUG: Created temp directory: {temp_dir}")
            
            # Copy SMOO files to temp directory for processing
            progress_dialog.setLabelText("Preparing water level files...")
            progress_dialog.setValue(60)
            QApplication.processEvents()
            
            prepared_files = []
            for i, file_info in enumerate(files_found):
                try:
                    # Update progress for file preparation
                    prep_progress = 60 + (i / total_files) * 20  # 60-80% for file prep
                    progress_dialog.setValue(int(prep_progress))
                    progress_dialog.setLabelText(f"Preparing {file_info['name']} ({i+1}/{total_files})...")
                    QApplication.processEvents()
                    
                    # Copy from SMOO to temp directory for processing
                    source_path = file_info['file_path']
                    temp_file_path = os.path.join(temp_dir, file_info['name'])
                    
                    shutil.copy2(source_path, temp_file_path)
                    
                    prepared_files.append({
                        'path': temp_file_path,
                        'info': file_info
                    })
                    logger.info(f"Prepared {file_info['name']} from SMOO to {temp_file_path}")
                        
                except Exception as e:
                    logger.error(f"Error preparing {file_info['name']}: {e}")
            
            if not prepared_files:
                logger.error("No water level files prepared successfully")
                return 0
            
            # Process the temp folder using water level folder processor
            progress_dialog.setLabelText(f"Processing {len(prepared_files)} water level files...")
            progress_dialog.setValue(80)
            QApplication.processEvents()
            
            logger.info(f"AUTO_SYNC_DEBUG: Processing temp folder with water level dialog...")
            
            # Use WaterLevelFolderDialog directly - SAME as barologger uses BaroFolderProcessor
            from ..dialogs.water_level_folder_dialog import WaterLevelFolderDialog
            from pathlib import Path
            
            # Create dialog (but don't show it) - just use its methods programmatically
            dialog = WaterLevelFolderDialog(
                water_level_model=water_tab.water_level_model,
                parent=None,
                settings_handler=self.settings_handler
            )
            
            # Set the temp folder path and scan it (same as barologger)
            dialog.folder_path = Path(temp_dir)
            
            logger.info(f"AUTO_SYNC_DEBUG: Scanning temp folder: {temp_dir}")
            
            # Add debug: list files in temp folder before scanning
            temp_files = os.listdir(temp_dir)
            logger.info(f"AUTO_SYNC_DEBUG: Files in temp folder before scan: {temp_files}")
            
            # Call processor scan directly with correct parameters
            logger.info(f"AUTO_SYNC_DEBUG: About to call processor.scan_folder with folder_path={dialog.folder_path}")
            logger.info(f"AUTO_SYNC_DEBUG: dialog.processor type: {type(dialog.processor)}")
            logger.info(f"AUTO_SYNC_DEBUG: dialog.processor.scan_folder method: {dialog.processor.scan_folder}")
            
            # Call the scan method and catch any errors
            try:
                scan_result = dialog.processor.scan_folder(
                    dialog.folder_path,
                    False,  # include_subfolders = False
                    None    # progress_dialog = None for auto-sync
                )
                logger.info(f"AUTO_SYNC_DEBUG: scan_folder call completed, result type: {type(scan_result)}")
                dialog.data = scan_result
            except Exception as e:
                logger.error(f"AUTO_SYNC_DEBUG: Exception during scan_folder call: {e}")
                return 0
            
            logger.info(f"AUTO_SYNC_DEBUG: scan_folder returned: {type(dialog.data)} with keys: {list(dialog.data.keys()) if dialog.data and isinstance(dialog.data, dict) else 'Not a dict or None'}")
            
            # Check scan results - handle both formats (defaultdict from handler vs dict from processor)
            if not dialog.data or (isinstance(dialog.data, dict) and 'error' in dialog.data):
                error_msg = dialog.data.get('error', 'No scan results') if dialog.data else 'No scan results'
                logger.error(f"AUTO_SYNC_DEBUG: Water level scan failed: {error_msg}")
                return 0
            
            # Handle different return formats from different processors
            if isinstance(dialog.data, dict) and 'wells' in dialog.data:
                # Format from water_level_folder_processor.py: {'wells': {}, 'processed_count': 0}
                wells_found = dialog.data.get('wells', {})
                processed_count = dialog.data.get('processed_count', 0)
                logger.info(f"AUTO_SYNC_DEBUG: Water level scan found {processed_count} valid files (processor format)")
            else:
                # Format from water_level_folder_handler.py: defaultdict with well numbers as keys
                wells_found = dict(dialog.data) if dialog.data else {}
                processed_count = len(wells_found)
                logger.info(f"AUTO_SYNC_DEBUG: Water level scan found {processed_count} valid files (handler format)")
            
            # Add debug: show what was found in scan results
            logger.info(f"AUTO_SYNC_DEBUG: Full scan data keys: {list(dialog.data.keys())}")
            logger.info(f"AUTO_SYNC_DEBUG: Wells found in scan: {list(wells_found.keys())}")
            
            # Get all wells found
            selected_wells = list(wells_found.keys())
            if not selected_wells:
                logger.error("AUTO_SYNC_DEBUG: No wells found in scan results")
                logger.error(f"AUTO_SYNC_DEBUG: Raw dialog.data = {dialog.data}")
                return 0
            
            logger.info(f"AUTO_SYNC_DEBUG: Processing {len(selected_wells)} wells: {selected_wells}")
            
            # STEP 2: Process the files (level them, put them together) - THE MISSING STEP!
            # Use processor directly since dialog.process_files() requires UI table
            logger.info(f"AUTO_SYNC_DEBUG: Processing files directly using processor...")
            
            # Create mock progress dialog for auto-sync
            class MockProgressDialog:
                def log_message(self, message):
                    logger.info(f"AUTO_SYNC_PROCESSOR: {message}")
                def update_progress(self, current, total):
                    pass
                def update_status(self, message):
                    logger.info(f"AUTO_SYNC_PROCESSOR: {message}")
                def was_canceled(self):
                    return False
                    
            mock_progress = MockProgressDialog()
            
            try:
                # Use the processor's process_files method directly
                logger.info(f"AUTO_SYNC_DEBUG: Calling processor.process_files...")
                processed_data = dialog.processor.process_files(dialog.data, progress_dialog=mock_progress)
                logger.info(f"AUTO_SYNC_DEBUG: processor.process_files completed, returned: {type(processed_data)}")
                
                # Update the wells data with processed results
                if processed_data:
                    for well_number in selected_wells:
                        if well_number in processed_data:
                            wells_found[well_number].update(processed_data[well_number])
                            logger.info(f"AUTO_SYNC_DEBUG: Well {well_number} processing completed")
                        else:
                            logger.warning(f"AUTO_SYNC_DEBUG: Well {well_number} not found in processed results")
                else:
                    logger.warning(f"AUTO_SYNC_DEBUG: No processed data returned")
                
                logger.info(f"AUTO_SYNC_DEBUG: All wells processed")
                
                # Check if processing was successful
                for well_number in selected_wells:
                    well_data = wells_found[well_number]
                    logger.info(f"AUTO_SYNC_DEBUG: After processing - {well_number} has_been_processed = {well_data.get('has_been_processed', 'NOT_SET')}")
                    
            except Exception as e:
                logger.error(f"AUTO_SYNC_DEBUG: Exception in direct processing: {e}")
                return 0
            
            logger.info(f"AUTO_SYNC_DEBUG: Auto-importing {len(selected_wells)} wells after processing")
            
            # STEP 3: Import the processed data directly using the water level model
            logger.info(f"AUTO_SYNC_DEBUG: Importing processed data for {len(selected_wells)} wells...")
            success = True
            total_imported = 0
            
            for well_number in selected_wells:
                try:
                    well_data = wells_found[well_number]
                    logger.info(f"AUTO_SYNC_DEBUG: Checking well {well_number} data keys: {list(well_data.keys())}")
                    logger.info(f"AUTO_SYNC_DEBUG: has_been_processed = {well_data.get('has_been_processed', 'NOT_SET')}")
                    
                    # Check if well was processed
                    if not well_data.get('has_been_processed', False):
                        logger.warning(f"AUTO_SYNC_DEBUG: Well {well_number} was not processed, skipping import")
                        continue
                    
                    # Get processed data
                    processed_data = well_data.get('processed_data')
                    if processed_data is None or processed_data.empty:
                        logger.warning(f"AUTO_SYNC_DEBUG: No processed data for well {well_number}")
                        continue
                    
                    logger.info(f"AUTO_SYNC_DEBUG: Importing {len(processed_data)} readings for well {well_number}")
                    
                    # Import using water level model directly (no overwrite for auto-sync)
                    import_success = water_tab.water_level_model.import_readings(
                        well_number,
                        processed_data,
                        overwrite=False  # Auto-sync doesn't overwrite existing data
                    )
                    
                    if import_success:
                        total_imported += len(processed_data)
                        logger.info(f"AUTO_SYNC_DEBUG: Successfully imported {len(processed_data)} readings for well {well_number}")
                    else:
                        logger.error(f"AUTO_SYNC_DEBUG: Failed to import data for well {well_number}")
                        success = False
                        
                except Exception as e:
                    logger.error(f"AUTO_SYNC_DEBUG: Exception importing well {well_number}: {e}")
                    success = False
            
            logger.info(f"AUTO_SYNC_DEBUG: Import complete - total imported: {total_imported} readings")
            
            if success:
                logger.info(f"AUTO_SYNC_DEBUG: Successfully processed water level folder with {len(prepared_files)} files")
                
                # Preserve XLE files using same method as barologgers (consistent approach)
                for file_data in prepared_files:
                    file_info = file_data['info']
                    temp_file_path = file_data['path']
                    
                    # Find the matching well number for this CAE number
                    matching_well_number = None
                    for well_number in selected_wells:
                        well_data = wells_found[well_number]
                        if (well_data.get('has_been_processed', False) and 
                            'well_info' in well_data and
                            file_info['cae_number'] == well_data['well_info']['cae_number']):
                            matching_well_number = well_number
                            break
                    
                    if matching_well_number:
                        # Handle XLE file preservation based on database type
                        if self.db_manager.is_cloud_database:
                            # For shared databases: only track files for later push, don't save to SMOO yet
                            self._track_autosync_xle_file(
                                temp_file_path, file_info['cae_number'], file_info['name'], device_type_hint='transducer'
                            )
                            logger.info(f"AUTO_SYNC_XLE: Tracked water level file for push operation: {file_info['name']}")
                        else:
                            # For local databases: save files immediately
                            preserved_file_path = self._preserve_autosync_xle_file(
                                temp_file_path, file_info['name'], matching_well_number, file_type="water_level"
                            )
                            if preserved_file_path:
                                logger.info(f"AUTO_SYNC_XLE: Preserved water level file: {preserved_file_path}")
                            else:
                                logger.error(f"AUTO_SYNC_XLE: Failed to preserve water level file: {file_info['name']}")
                    else:
                        logger.warning(f"AUTO_SYNC_XLE: No matching well found for CAE {file_info['cae_number']} in file {file_info['name']}")
                
                return len(prepared_files)
            else:
                logger.error("AUTO_SYNC_DEBUG: Water level folder processing failed")
                return 0
                
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Exception in water level folder processing: {e}")
            return 0
        finally:
            # Clean up temp directory
            try:
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir)
                    logger.info(f"AUTO_SYNC_DEBUG: Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"AUTO_SYNC_DEBUG: Error cleaning up temp directory: {e}")
        # This method now uses folder-based processing (implemented above)
        return 0
    
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
    
    def _preserve_autosync_xle_file(self, temp_file_path, original_filename, identifier, file_type="barologger"):
        """
        Preserve autosync XLE file in the imported_xle_files directory structure.
        For shared databases (S: drive), saves to S: drive imported_xle_files folder.
        For local databases, saves to local imported_xle_files folder.
        
        Args:
            temp_file_path: Path to temporary file
            original_filename: Original filename
            identifier: Serial number (for barologgers) or CAE number (for water levels)
            file_type: "barologger" or "water_level"
            
        Returns the preserved file path or None if failed.
        """
        try:
            # Use database manager's cloud detection instead of path-based detection
            is_shared_database = self.db_manager.is_cloud_database
            if self.db_manager.current_db:
                db_path = Path(self.db_manager.current_db)
                if is_shared_database:
                    logger.info(f"AUTO_SYNC_XLE: Detected shared/cloud database: {db_path}")
                else:
                    logger.info(f"AUTO_SYNC_XLE: Detected local database: {db_path}")
            
            # Get XLE import directory based on database type
            if is_shared_database:
                # For shared databases, use SMOO Projects structure
                shared_drive_projects = self.settings_handler.get_setting("shared_drive_projects", "")
                if shared_drive_projects:
                    # Get project name from database
                    project_name = None
                    if self.db_manager.current_db:
                        db_path = Path(self.db_manager.current_db)
                        if db_path.name.startswith('wlm_'):
                            project_name = db_path.name[4:-3]  # Remove 'wlm_' prefix and '.db' suffix
                        else:
                            project_name = db_path.stem
                    
                    if project_name:
                        xle_import_base = Path(shared_drive_projects) / project_name / "XLE_Files"
                        logger.info(f"AUTO_SYNC_XLE: Using shared drive project XLE path: {xle_import_base}")
                    else:
                        logger.error("AUTO_SYNC_XLE: Could not determine project name for shared database")
                        return None
                else:
                    # Fallback: use SMOO path manager for cross-platform compatibility
                    from config.smoo_paths import get_smoo_path, is_smoo_available
                    
                    if is_smoo_available():
                        smoo_projects = get_smoo_path("projects")
                        # Get project name from database
                        project_name = None
                        if self.db_manager.current_db:
                            db_path = Path(self.db_manager.current_db)
                            if db_path.name.startswith('wlm_'):
                                project_name = db_path.name[4:-3]  # Remove 'wlm_' prefix and '.db' suffix
                            else:
                                project_name = db_path.stem
                        
                        if project_name:
                            xle_import_base = Path(smoo_projects) / project_name / "XLE_Files"
                            logger.info(f"AUTO_SYNC_XLE: Using SMOO project XLE path: {xle_import_base}")
                        else:
                            logger.error("AUTO_SYNC_XLE: Could not determine project name for SMOO path")
                            return None
                    else:
                        logger.error("AUTO_SYNC_XLE: SMOO not available for shared database")
                        return None
            else:
                # For local databases, use local imported_xle_files directory
                app_dir = Path(__file__).parent.parent.parent.parent
                xle_import_base = Path(self.settings_handler.get_setting("xle_import_directory", str(app_dir / "imported_xle_files")))
                logger.info(f"AUTO_SYNC_XLE: Using local XLE import path: {xle_import_base}")
            
            # Get project/database name for organization
            project_name = None
            if self.db_manager.current_db:
                db_path = Path(self.db_manager.current_db)
                if db_path.name.startswith('wlm_'):
                    project_name = db_path.name[4:-3]  # Remove 'wlm_' prefix and '.db' suffix
                else:
                    project_name = db_path.stem
            
            # Sanitize identifier for Windows file system (remove : < > | " * ? \ /)
            safe_identifier = "".join(c for c in identifier if c not in ':*?"<>|\\/')
            
            # Choose folder based on file type
            folder_type = "barologgers" if file_type == "barologger" else "water_levels"
            
            # Create directory structure
            if is_shared_database:
                # For shared databases: Projects/[project]/XLE_Files/[barologgers|water_levels]/[identifier]/
                target_dir = xle_import_base / folder_type / safe_identifier
            else:
                # For local databases: imported_xle_files/[project]/[barologgers|water_levels]/[identifier]/
                if project_name:
                    target_dir = xle_import_base / project_name / folder_type / safe_identifier
                else:
                    target_dir = xle_import_base / folder_type / safe_identifier
            
            # Create directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"AUTO_SYNC_XLE: Created/verified directory: {target_dir}")
            
            # Copy file to target directory
            target_file_path = target_dir / original_filename
            shutil.copy2(temp_file_path, target_file_path)
            
            logger.info(f"AUTO_SYNC_XLE: Preserved XLE file: {target_file_path}")
            logger.info(f"AUTO_SYNC_XLE: File location: {'S: DRIVE (shared)' if is_shared_database else 'LOCAL DRIVE'}")
            return str(target_file_path)
            
        except Exception as e:
            logger.error(f"AUTO_SYNC_XLE: Error preserving XLE file {original_filename}: {e}")
            return None
    
    def _track_autosync_xle_file(self, file_path, serial_or_cae_number, original_filename, device_type_hint=None):
        """
        Track autosync XLE file for shared database upload using SharedDatabaseXLEManager.
        Handles both barologger (serial number) and transducer (CAE number) files.
        
        Args:
            file_path: Path to the XLE file
            serial_or_cae_number: Serial number for barologgers or CAE number for transducers
            original_filename: Original filename of the XLE file
            device_type_hint: Optional hint about device type ('barologger' or 'transducer')
        """
        try:
            if not hasattr(self.parent, 'cloud_db_handler'):
                logger.warning("Cloud database handler not available for XLE tracking")
                return None
            
            cloud_handler = self.parent.cloud_db_handler
            if not cloud_handler:
                logger.warning("Cloud database handler not initialized for XLE tracking")
                return None
            
            # Get project name
            project_name = None
            if self.db_manager.current_db:
                db_path = Path(self.db_manager.current_db)
                if db_path.name.startswith('wlm_'):
                    project_name = db_path.name[4:-3]  # Remove 'wlm_' prefix and '.db' suffix
                else:
                    project_name = db_path.stem
            
            if not project_name:
                logger.warning("Could not determine project name for XLE tracking")
                return None
            
            # Determine device type and identifiers
            if device_type_hint:
                # Use provided hint (more reliable than string pattern matching)
                device_type = device_type_hint
                if device_type == 'transducer':
                    well_number = serial_or_cae_number
                    serial_number = None
                else:  # barologger
                    serial_number = serial_or_cae_number
                    well_number = None
            else:
                # Fallback to pattern matching
                # CAE numbers typically start with 'CAE' but can be other formats like 'HA:A-012'
                # Barologger serial numbers are typically numeric
                if str(serial_or_cae_number).startswith('CAE') or ':' in str(serial_or_cae_number):
                    device_type = 'transducer'
                    well_number = serial_or_cae_number
                    serial_number = None
                else:
                    device_type = 'barologger'
                    serial_number = serial_or_cae_number
                    well_number = None
            
            # Check if this is a shared database - use SharedDatabaseXLEManager
            if hasattr(cloud_handler, 'get_shared_xle_manager'):
                shared_xle_manager = cloud_handler.get_shared_xle_manager()
                if shared_xle_manager:
                    # Extract dates from filename for tracking
                    start_date_str, end_date_str = self._extract_dates_from_filename(original_filename)
                    
                    # Convert to datetime objects for SharedDatabaseXLEManager
                    from datetime import datetime, timedelta
                    try:
                        if end_date_str:
                            end_date = datetime.fromisoformat(end_date_str)
                        else:
                            end_date = datetime.now()
                        
                        if start_date_str:
                            start_date = datetime.fromisoformat(start_date_str)
                        else:
                            # Default to 30 days before end date if not available
                            start_date = end_date - timedelta(days=30)
                    except Exception as e:
                        logger.warning(f"Error parsing dates from {original_filename}: {e}, using defaults")
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=30)
                    
                    # Store XLE file in temporary location for later push to SMOO
                    temp_file_path = shared_xle_manager.store_temp_xle(
                        original_file_path=file_path,
                        project_name=project_name,
                        device_type=device_type,
                        serial_number=serial_number or serial_or_cae_number,
                        location='field-data',
                        start_date=start_date,
                        end_date=end_date,
                        well_number=well_number
                    )
                    
                    logger.info(f"Stored temp {device_type} XLE file for SMOO push: {original_filename} -> {temp_file_path}")
                    return temp_file_path
                else:
                    logger.warning("SharedDatabaseXLEManager not available for XLE tracking")
            
            # Fallback to legacy Google Drive XLE manager (disabled)
            elif hasattr(cloud_handler, 'xle_manager') and cloud_handler.xle_manager:
                logger.warning("Using legacy Google Drive XLE manager (disabled functionality)")
                # Extract dates from filename for tracking
                start_date_str, end_date_str = self._extract_dates_from_filename(original_filename)
                
                # Track the XLE file for upload (Google Drive system, now disabled)
                file_id = cloud_handler.xle_manager.track_xle_file(
                    file_path=file_path,
                    file_type=device_type,
                    serial_number=serial_number or serial_or_cae_number,
                    well_number=well_number,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    project_name=project_name
                )
                
                logger.info(f"Tracked autosync XLE file (legacy): {original_filename} (ID: {file_id})")
                return file_id
            else:
                logger.warning("No XLE manager available for tracking autosync file")
                
        except Exception as e:
            logger.error(f"Error tracking autosync XLE file {original_filename}: {e}")
            
        return None
    
    def _extract_dates_from_filename(self, filename):
        """
        Extract start and end dates from XLE filename for tracking.
        Returns tuple of (start_date_iso, end_date_iso) or (None, None) if not found.
        """
        try:
            # Use the runs monitor's date extraction method
            end_date = self.runs_monitor.extract_date_from_filename(filename)
            if end_date:
                # For now, we only have end date from filename
                # Start date could be extracted if filename pattern supports it
                return None, end_date.isoformat()
        except Exception as e:
            logger.debug(f"Could not extract dates from filename {filename}: {e}")
            
        return None, None
    
    def _get_barologger_search_ranges(self, active_barologgers):
        """
        Get smart month search ranges for each barologger based on their last record.
        Returns dict with serial_number -> list of months to search.
        """
        barologger_ranges = {}
        current_date = datetime.now()
        current_month = current_date.strftime('%Y-%m')
        
        try:
            if not self.db_manager.current_db:
                # No database, search current month only for all barologgers
                for serial in active_barologgers:
                    barologger_ranges[serial] = [current_month]
                return barologger_ranges
            
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                for serial_number in active_barologgers:
                    logger.info(f"AUTO_SYNC_DEBUG: Processing barologger {serial_number}...")
                    
                    # Get the last ACTUAL DATA timestamp for this barologger (not file metadata)
                    # This is the correct approach - look at actual data, not file import records
                    cursor.execute("""
                        SELECT MAX(timestamp_utc) 
                        FROM barometric_readings 
                        WHERE serial_number = ?
                    """, (serial_number,))
                    
                    result = cursor.fetchone()
                    last_data_date = None
                    logger.info(f"AUTO_SYNC_DEBUG: Last actual data query result for {serial_number}: {result}")
                    
                    if result and result[0]:
                        try:
                            last_data_date = datetime.fromisoformat(result[0])
                            logger.info(f"AUTO_SYNC_DEBUG: Found last actual data date: {last_data_date}")
                        except Exception as e:
                            logger.warning(f"AUTO_SYNC_DEBUG: Invalid date format in readings for barologger {serial_number}: {result[0]} - {e}")
                    else:
                        logger.info(f"AUTO_SYNC_DEBUG: No actual data found for barologger {serial_number}")
                    
                    # Generate month range based on actual data (not import metadata)
                    if last_data_date:
                        # Check if last data date is reasonable (not in future)
                        if last_data_date > current_date:
                            logger.warning(f"AUTO_SYNC_DEBUG: Barologger {serial_number}: last data date {last_data_date.strftime('%Y-%m-%d')} is in the future! Using fallback search.")
                            months = "ALL_AVAILABLE"  # Use fallback for bad data
                        else:
                            # Start from the month of the last actual data record
                            start_month = last_data_date.strftime('%Y-%m')
                            months = self._generate_month_range(start_month, current_month)
                            logger.info(f"AUTO_SYNC_DEBUG: Barologger {serial_number}: last actual data {last_data_date.strftime('%Y-%m-%d')}, searching months: {months}")
                            
                            # If we still get empty months (edge case), fall back to ALL_AVAILABLE
                            if not months:
                                logger.warning(f"AUTO_SYNC_DEBUG: Month range generation returned empty for {serial_number}, using ALL_AVAILABLE fallback")
                                months = "ALL_AVAILABLE"
                    else:
                        # No previous data in database, search all available month folders
                        logger.info(f"AUTO_SYNC_DEBUG: No previous data found for {serial_number}, will search all available month folders...")
                        months = "ALL_AVAILABLE"  # Special marker to indicate we should search all month folders
                        logger.info(f"AUTO_SYNC_DEBUG: Barologger {serial_number}: no previous data, will search all available months")
                    
                    barologger_ranges[serial_number] = months
                    logger.info(f"AUTO_SYNC_DEBUG: Final month range for {serial_number}: {months}")
                    
        except Exception as e:
            logger.error(f"Error determining barologger search ranges: {e}")
            # Fallback: search current month for all
            for serial in active_barologgers:
                barologger_ranges[serial] = [current_month]
        
        return barologger_ranges
    
    def _get_water_level_search_ranges(self, active_wells):
        """
        Get smart month search ranges for each well based on their last record.
        Returns dict with cae_number -> list of months to search.
        """
        well_ranges = {}
        current_date = datetime.now()
        current_month = current_date.strftime('%Y-%m')
        
        try:
            if not self.db_manager.current_db:
                # No database, search current month only for all wells
                for cae_number in active_wells:
                    well_ranges[cae_number] = [current_month]
                return well_ranges
            
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                for cae_number in active_wells:
                    logger.info(f"AUTO_SYNC_DEBUG: Processing well {cae_number}...")
                    
                    # Get the well number from CAE number
                    cursor.execute("SELECT well_number FROM wells WHERE cae_number = ?", (cae_number,))
                    well_result = cursor.fetchone()
                    
                    if not well_result:
                        # CAE number not found, search all available months as fallback
                        well_ranges[cae_number] = "ALL_AVAILABLE"
                        logger.warning(f"AUTO_SYNC_DEBUG: CAE number {cae_number} not found in wells table, using ALL_AVAILABLE search")
                        continue
                    
                    well_number = well_result[0]
                    logger.info(f"AUTO_SYNC_DEBUG: CAE {cae_number} maps to well_number {well_number}")
                    
                    # Get the last ACTUAL DATA timestamp for this well (not import metadata)
                    cursor.execute("""
                        SELECT MAX(timestamp_utc) 
                        FROM water_level_readings 
                        WHERE well_number = ?
                    """, (well_number,))
                    
                    result = cursor.fetchone()
                    last_data_date = None
                    logger.info(f"AUTO_SYNC_DEBUG: Last actual data query result for well {well_number}: {result}")
                    
                    if result and result[0]:
                        try:
                            last_data_date = datetime.fromisoformat(result[0])
                            logger.info(f"AUTO_SYNC_DEBUG: Found last actual data date for well {well_number}: {last_data_date}")
                        except Exception as e:
                            logger.warning(f"AUTO_SYNC_DEBUG: Invalid date format in database for well {well_number}: {result[0]} - {e}")
                    else:
                        logger.info(f"AUTO_SYNC_DEBUG: No actual data found for well {well_number}")
                    
                    # Generate month range based on actual data
                    if last_data_date:
                        # Check if last data date is reasonable (not in future)
                        if last_data_date > current_date:
                            logger.warning(f"AUTO_SYNC_DEBUG: Well {cae_number}: last data date {last_data_date.strftime('%Y-%m-%d')} is in the future! Using fallback search.")
                            months = "ALL_AVAILABLE"
                        else:
                            # Start from the month of the last actual data record
                            start_month = last_data_date.strftime('%Y-%m')
                            months = self._generate_month_range(start_month, current_month)
                            logger.info(f"AUTO_SYNC_DEBUG: Well {cae_number}: last actual data {last_data_date.strftime('%Y-%m-%d')}, searching months: {months}")
                            
                            # If we still get empty months, fall back to ALL_AVAILABLE
                            if not months:
                                logger.warning(f"AUTO_SYNC_DEBUG: Month range generation returned empty for well {cae_number}, using ALL_AVAILABLE fallback")
                                months = "ALL_AVAILABLE"
                    else:
                        # No previous data in database, search all available month folders
                        logger.info(f"AUTO_SYNC_DEBUG: Well {cae_number}: no previous data, will search all available months")
                        months = "ALL_AVAILABLE"  # Special marker to indicate we should search all month folders
                    
                    well_ranges[cae_number] = months
                    logger.info(f"AUTO_SYNC_DEBUG: Final month range for well {cae_number}: {months}")
                    
        except Exception as e:
            logger.error(f"Error determining water level search ranges: {e}")
            # Fallback: search current month for all
            for cae_number in active_wells:
                well_ranges[cae_number] = [current_month]
        
        return well_ranges
    
    def _generate_month_range(self, start_month, end_month):
        """
        Generate list of months from start_month to end_month (inclusive).
        Format: YYYY-MM
        """
        months = []
        try:
            logger.info(f"AUTO_SYNC_DEBUG: Generating month range from '{start_month}' to '{end_month}'")
            start_year, start_mon = map(int, start_month.split('-'))
            end_year, end_mon = map(int, end_month.split('-'))
            logger.info(f"AUTO_SYNC_DEBUG: Parsed dates - Start: {start_year}-{start_mon}, End: {end_year}-{end_mon}")
            
            current_year, current_month = start_year, start_mon
            
            while (current_year < end_year) or (current_year == end_year and current_month <= end_mon):
                month_str = f"{current_year}-{current_month:02d}"
                months.append(month_str)
                logger.info(f"AUTO_SYNC_DEBUG: Added month: {month_str}")
                
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                    
                # Safety check to prevent infinite loops
                if len(months) > 24:  # Max 2 years
                    logger.warning(f"AUTO_SYNC_DEBUG: Month range generation stopped at 24 months for safety")
                    break
            
            logger.info(f"AUTO_SYNC_DEBUG: Generated {len(months)} months: {months}")
                    
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error generating month range from {start_month} to {end_month}: {e}")
            # Fallback to end month only
            months = [end_month]
            logger.info(f"AUTO_SYNC_DEBUG: Using fallback month: {months}")
            
        return months
    
    def _get_multiple_month_folders(self, month_list):
        """
        Get folder IDs for multiple months at once.
        Returns dict with month -> folder_id.
        """
        month_folders = {}
        
        try:
            service = self.drive_service.get_service()
            if not service:
                return month_folders
            
            consolidated_folder_id = self.settings_handler.get_setting("consolidated_field_data_folder")
            if not consolidated_folder_id:
                logger.warning("Consolidated field data folder ID not configured")
                return month_folders
            
            # Build query to find all needed month folders at once
            month_conditions = " or ".join([f"name = '{month}'" for month in month_list])
            query = f"'{consolidated_folder_id}' in parents and ({month_conditions}) and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            
            logger.debug(f"Searching for {len(month_list)} month folders with query: {query}")
            
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=50  # Should be enough for month folders
            ).execute()
            
            # Map results
            for folder in results.get('files', []):
                month_folders[folder['name']] = folder['id']
                logger.debug(f"Found month folder: {folder['name']} -> {folder['id']}")
            
            # Log missing folders
            missing_months = set(month_list) - set(month_folders.keys())
            if missing_months:
                logger.info(f"Month folders not found (will be skipped): {sorted(missing_months)}")
                
        except Exception as e:
            logger.error(f"Error getting multiple month folders: {e}")
            
        return month_folders
    
    def _get_all_available_month_folders(self):
        """
        Get all available month folders in the consolidated folder.
        Returns dict with month -> folder_id.
        """
        month_folders = {}
        
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.error("AUTO_SYNC_DEBUG: Google Drive service not available for getting all month folders")
                return month_folders
            
            consolidated_folder_id = self.settings_handler.get_setting("consolidated_field_data_folder")
            if not consolidated_folder_id:
                logger.warning("AUTO_SYNC_DEBUG: Consolidated field data folder ID not configured")
                return month_folders
            
            # Search for all month-like folders (YYYY-MM pattern)
            query = f"'{consolidated_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            
            logger.info(f"AUTO_SYNC_DEBUG: Searching for all month folders with query: {query}")
            
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=100  # Should be enough for all month folders
            ).execute()
            
            # Filter results to only include valid month format (YYYY-MM)
            import re
            month_pattern = re.compile(r'^\d{4}-\d{2}$')
            
            for folder in results.get('files', []):
                folder_name = folder['name']
                if month_pattern.match(folder_name):
                    month_folders[folder_name] = folder['id']
                    logger.info(f"AUTO_SYNC_DEBUG: Found month folder: {folder_name} -> {folder['id']}")
                else:
                    logger.debug(f"AUTO_SYNC_DEBUG: Skipping non-month folder: {folder_name}")
                    
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error getting all available month folders: {e}")
            
        return month_folders
    
    def _get_metadata_from_folder(self, folder_id):
        """
        Read metadata.json file from a month folder and return file metadata.
        Returns list of file metadata dictionaries.
        """
        try:
            service = self.drive_service.get_service()
            if not service:
                return []
            
            # Look for metadata.json in the folder
            query = f"'{folder_id}' in parents and name='metadata.json' and trashed=false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            metadata_files = results.get('files', [])
            
            if not metadata_files:
                logger.debug(f"No metadata.json found in folder {folder_id}")
                return []
            
            # Download and parse metadata.json
            metadata_file = metadata_files[0]
            request = service.files().get_media(fileId=metadata_file['id'])
            
            import io
            from googleapiclient.http import MediaIoBaseDownload
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            metadata_json = json.loads(file_content.read().decode('utf-8'))
            
            logger.info(f"AUTO_SYNC_DEBUG: Metadata JSON structure: {list(metadata_json.keys())}")
            files_list = metadata_json.get('files', [])
            logger.info(f"AUTO_SYNC_DEBUG: Found {len(files_list)} files in metadata JSON")
            if files_list:
                logger.info(f"AUTO_SYNC_DEBUG: First file sample: {files_list[0]}")
            
            return files_list
            
        except Exception as e:
            logger.error(f"Error reading metadata from folder {folder_id}: {e}")
            return []
    
    def _is_newer_barologger_file_metadata(self, file_metadata, serial_number):
        """Check if barologger file is newer than last actual data using metadata"""
        try:
            # Get last actual data timestamp for this barologger
            if self.db_manager.current_db:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT MAX(timestamp_utc) FROM barometric_readings WHERE serial_number = ?", 
                        (serial_number,)
                    )
                    result = cursor.fetchone()
                    if result and result[0]:
                        last_data_timestamp = datetime.fromisoformat(result[0])
                        
                        # Use actual end date from metadata
                        file_end_date = datetime.fromisoformat(file_metadata['actual_end_date'])
                        
                        if file_end_date > last_data_timestamp:
                            logger.info(f"AUTO_SYNC_DEBUG: File {file_metadata['filename']} is newer than last data ({last_data_timestamp}) - will process")
                            return True
                        else:
                            logger.info(f"AUTO_SYNC_DEBUG: File {file_metadata['filename']} is not newer than last data ({last_data_timestamp}) - skipping")
                            return False
            
            logger.info(f"AUTO_SYNC_DEBUG: No previous data found for {serial_number}, will process file {file_metadata['filename']}")
            return True  # No previous data, process the file
            
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error checking if barologger file is newer: {e}")
            return True  # When in doubt, process the file
    
    def _is_newer_water_level_file_metadata(self, file_metadata, cae_number):
        """Check if water level file is newer than last actual data using metadata"""
        try:
            # Get last actual data timestamp for this well using proper well table lookup
            if self.db_manager.current_db:
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    # First get the well_number from cae_number
                    cursor.execute(
                        "SELECT well_number FROM wells WHERE cae_number = ?", 
                        (cae_number,)
                    )
                    well_result = cursor.fetchone()
                    
                    if well_result:
                        well_number = well_result[0]
                        # Then get last data for this well
                        cursor.execute(
                            "SELECT MAX(timestamp_utc) FROM water_level_readings WHERE well_number = ?", 
                            (well_number,)
                        )
                        result = cursor.fetchone()
                        
                        if result and result[0]:
                            last_data_timestamp = datetime.fromisoformat(result[0])
                            
                            # Use actual end date from metadata
                            file_end_date = datetime.fromisoformat(file_metadata['actual_end_date'])
                            
                            if file_end_date > last_data_timestamp:
                                logger.debug(f"File {file_metadata['filename']} is newer than last data ({last_data_timestamp}) - will process")
                                return True
                            else:
                                logger.debug(f"File {file_metadata['filename']} is not newer than last data ({last_data_timestamp}) - skipping")
                                return False
            
            logger.debug(f"No previous data found for {cae_number}, will process file {file_metadata['filename']}")
            return True  # No previous data, process the file
            
        except Exception as e:
            logger.error(f"Error checking if water level file is newer: {e}")
            return True  # When in doubt, process the file
    
    def generate_metadata_files_for_existing_data(self, progress_callback=None):
        """
        Generate metadata.json files for all existing XLE files in consolidated folder structure.
        Reads actual data from each XLE file to get accurate dates and device information.
        """
        try:
            logger.info("METADATA_GEN: Starting metadata generation for existing consolidated files...")
            
            service = self.drive_service.get_service()
            if not service:
                logger.error("METADATA_GEN: Google Drive service not available")
                return False
            
            # Get consolidated folder
            consolidated_folder_id = self.settings_handler.get_setting("consolidated_field_data_folder")
            if not consolidated_folder_id:
                consolidated_folder_id = self._auto_detect_consolidated_folder()
                if not consolidated_folder_id:
                    logger.error("METADATA_GEN: Could not find consolidated folder")
                    return False
            
            # Get all month folders
            all_month_folders = self._get_all_available_month_folders()
            if not all_month_folders:
                logger.warning("METADATA_GEN: No month folders found in consolidated structure")
                return False
            
            logger.info(f"METADATA_GEN: Found {len(all_month_folders)} month folders to process")
            
            total_folders = len(all_month_folders)
            processed_folders = 0
            
            # Process each month folder
            for month, folder_id in sorted(all_month_folders.items()):
                try:
                    if progress_callback:
                        progress = int((processed_folders / total_folders) * 100)
                        progress_callback(f"Processing month folder {month}...", progress)
                    
                    logger.info(f"METADATA_GEN: Processing month folder: {month}")
                    
                    # Get all XLE files in this month folder
                    xle_files = self._get_xle_files_in_folder(folder_id)
                    logger.info(f"METADATA_GEN: Found {len(xle_files)} XLE files in {month}")
                    
                    if not xle_files:
                        logger.info(f"METADATA_GEN: No XLE files in {month}, skipping")
                        processed_folders += 1
                        continue
                    
                    # Generate metadata for all files in this folder
                    metadata = {
                        "folder": month,
                        "generated_date": datetime.now().isoformat(),
                        "files": []
                    }
                    
                    for i, file_info in enumerate(xle_files):
                        try:
                            if progress_callback:
                                file_progress = int((processed_folders / total_folders) * 100 + (i / len(xle_files)) * (100 / total_folders))
                                progress_callback(f"Reading {file_info['name']} in {month}...", file_progress)
                            
                            logger.info(f"METADATA_GEN: Processing file {i+1}/{len(xle_files)}: {file_info['name']}")
                            
                            # Read actual XLE data
                            file_metadata = self._extract_xle_metadata(file_info)
                            if file_metadata:
                                metadata["files"].append(file_metadata)
                                logger.info(f"METADATA_GEN: Successfully processed {file_info['name']}")
                            else:
                                logger.warning(f"METADATA_GEN: Failed to process {file_info['name']}")
                                
                        except Exception as e:
                            logger.error(f"METADATA_GEN: Error processing file {file_info['name']}: {e}")
                            continue
                    
                    # Create metadata.json file in the month folder
                    if metadata["files"]:
                        success = self._create_metadata_json_file(folder_id, metadata)
                        if success:
                            logger.info(f"METADATA_GEN: Created metadata.json for {month} with {len(metadata['files'])} files")
                        else:
                            logger.error(f"METADATA_GEN: Failed to create metadata.json for {month}")
                    else:
                        logger.warning(f"METADATA_GEN: No valid files processed for {month}")
                    
                    processed_folders += 1
                    
                except Exception as e:
                    logger.error(f"METADATA_GEN: Error processing month folder {month}: {e}")
                    processed_folders += 1
                    continue
            
            if progress_callback:
                progress_callback(f"✓ Metadata generation complete! Processed {total_folders} month folders", 100)
            
            logger.info(f"METADATA_GEN: Completed metadata generation for {processed_folders} month folders")
            return True
            
        except Exception as e:
            logger.error(f"METADATA_GEN: Error during metadata generation: {e}")
            return False
    
    def _get_xle_files_in_folder(self, folder_id):
        """Get all XLE files in a specific Google Drive folder"""
        try:
            service = self.drive_service.get_service()
            query = f"'{folder_id}' in parents and name contains '.xle' and trashed = false"
            
            results = service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)",
                pageSize=1000
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            logger.error(f"METADATA_GEN: Error getting XLE files from folder {folder_id}: {e}")
            return []
    
    def _extract_xle_metadata(self, file_info):
        """Download XLE file temporarily and extract actual data metadata"""
        temp_file_path = None
        try:
            # Download file to temporary location
            temp_file_path = self._download_file_to_temp(file_info['id'], file_info['name'])
            if not temp_file_path:
                logger.error(f"METADATA_GEN: Failed to download {file_info['name']}")
                return None
            
            # Read XLE file using SolinstReader
            from .solinst_reader import SolinstReader
            reader = SolinstReader()
            df, metadata = reader.read_xle(temp_file_path)
            
            if df.empty:
                logger.warning(f"METADATA_GEN: No data found in {file_info['name']}")
                return None
            
            # Get actual data dates (not metadata dates)
            first_timestamp = df['timestamp_utc'].min()
            last_timestamp = df['timestamp_utc'].max()
            
            # Get device information
            serial_number = metadata.serial_number
            location = metadata.location.strip()
            
            # Try to extract CAE number from location
            # Location might be like "HA012" or "HA:A-012" etc.
            cae_number = location.replace(':', '').replace('-', '').replace(' ', '')
            
            # Check if this is a barologger or water level device
            device_type = "barologger" if reader.is_barologger(metadata) else "water_level"
            
            file_metadata = {
                "filename": file_info['name'],
                "google_drive_file_id": file_info['id'],
                "serial_number": serial_number,
                "cae_number": cae_number,
                "location": location,
                "device_type": device_type,
                "actual_start_date": first_timestamp.isoformat(),
                "actual_end_date": last_timestamp.isoformat(),
                "file_size": int(file_info.get('size', 0)),
                "drive_modified_time": file_info['modifiedTime'],
                "processed_date": datetime.now().isoformat()
            }
            
            logger.info(f"METADATA_GEN: Extracted metadata for {file_info['name']}: {device_type} {serial_number} ({cae_number}) {first_timestamp} to {last_timestamp}")
            return file_metadata
            
        except Exception as e:
            logger.error(f"METADATA_GEN: Error extracting metadata from {file_info['name']}: {e}")
            return None
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
    
    def _create_metadata_json_file(self, folder_id, metadata):
        """Create metadata.json file in Google Drive folder"""
        try:
            import json
            import tempfile
            
            # Create temporary JSON file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(metadata, tmp_file, indent=2, ensure_ascii=False)
                temp_json_path = tmp_file.name
            
            try:
                # Upload to Google Drive
                service = self.drive_service.get_service()
                
                # Check if metadata.json already exists
                query = f"'{folder_id}' in parents and name='metadata.json' and trashed=false"
                results = service.files().list(q=query, fields="files(id)").execute()
                existing_files = results.get('files', [])
                
                if existing_files:
                    # Update existing file
                    from googleapiclient.http import MediaFileUpload
                    media = MediaFileUpload(temp_json_path, mimetype='application/json')
                    service.files().update(
                        fileId=existing_files[0]['id'],
                        media_body=media
                    ).execute()
                    logger.info(f"METADATA_GEN: Updated existing metadata.json in folder {folder_id}")
                else:
                    # Create new file
                    from googleapiclient.http import MediaFileUpload
                    file_metadata = {
                        'name': 'metadata.json',
                        'parents': [folder_id]
                    }
                    media = MediaFileUpload(temp_json_path, mimetype='application/json')
                    service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    logger.info(f"METADATA_GEN: Created new metadata.json in folder {folder_id}")
                
                return True
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_json_path):
                    os.remove(temp_json_path)
                    
        except Exception as e:
            logger.error(f"METADATA_GEN: Error creating metadata.json file: {e}")
            return False

    def _auto_detect_consolidated_folder(self):
        """Auto-detect the FIELD_DATA_CONSOLIDATED folder in Google Drive"""
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.warning("Google Drive service not available for auto-detection")
                return None
            
            # Get the main water levels monitoring folder ID
            main_folder_id = self.settings_handler.get_setting("google_drive_folder_id")
            if not main_folder_id:
                logger.warning("Main Google Drive folder ID not configured")
                return None
            
            # Search for FIELD_DATA_CONSOLIDATED folder in the main folder
            query = f"'{main_folder_id}' in parents and name = 'FIELD_DATA_CONSOLIDATED' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                spaces='drive'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                consolidated_folder_id = folders[0]['id']
                logger.info(f"Auto-detected FIELD_DATA_CONSOLIDATED folder: {consolidated_folder_id}")
                return consolidated_folder_id
            else:
                logger.warning("FIELD_DATA_CONSOLIDATED folder not found in Google Drive")
                return None
                
        except Exception as e:
            logger.error(f"Error auto-detecting consolidated folder: {e}")
            return None
    
    def _scan_smoo_for_barologger_files(self, current_month, active_barologgers):
        """Scan SMOO consolidated folder for new barologger files using direct file system access"""
        files_found = []
        
        try:
            logger.info(f"AUTO_SYNC_DEBUG: Scanning SMOO for barologger files in {current_month}")
            
            # Get smart month ranges for each barologger
            barologger_month_ranges = self._get_barologger_search_ranges(active_barologgers)
            logger.info(f"AUTO_SYNC_DEBUG: Barologger month ranges: {barologger_month_ranges}")
            
            # Get all available month folders if needed
            needs_all_months = any(month_range == "ALL_AVAILABLE" for month_range in barologger_month_ranges.values())
            
            if needs_all_months:
                logger.info("AUTO_SYNC_DEBUG: Some barologgers need ALL_AVAILABLE search, getting all month folders...")
                month_folders = self.smoo_scanner.get_all_available_month_folders()
            else:
                # Get specific month folders needed
                months_to_scan = set()
                for month_range in barologger_month_ranges.values():
                    if isinstance(month_range, list):
                        months_to_scan.update(month_range)
                    elif month_range != "ALL_AVAILABLE":
                        months_to_scan.add(month_range)
                
                # Add current month as fallback
                months_to_scan.add(current_month)
                logger.info(f"AUTO_SYNC_DEBUG: Scanning specific months: {months_to_scan}")
                
                month_folders = {}
                for month in months_to_scan:
                    folders = self.smoo_scanner.get_month_folders(month)
                    month_folders.update(folders)
            
            logger.info(f"AUTO_SYNC_DEBUG: Found {len(month_folders)} month folders to scan")
            
            # Scan each month folder for files with matching serial numbers
            for month_name, folder_path in month_folders.items():
                logger.info(f"AUTO_SYNC_DEBUG: Scanning month folder: {month_name} at {folder_path}")
                
                # Scan the main month folder for files with serial numbers (no subfolders)
                month_readings = self.smoo_scanner.scan_barologger_files(str(folder_path))
                logger.info(f"AUTO_SYNC_DEBUG: Found {len(month_readings)} readings with serial numbers in {month_name}")
                
                # Check each file against active barologgers
                for serial_number, file_data in month_readings.items():
                    # Check if this is an active barologger
                    if serial_number in active_barologgers:
                        # Check if this file is newer than existing data
                        if self._is_smoo_barologger_file_newer(file_data, serial_number):
                            files_found.append({
                                'name': file_data['filename'],
                                'serial_number': serial_number,
                                'folder_name': month_name,
                                'file_path': file_data['file_path'],
                                'reading_date': file_data['date']
                            })
                            logger.info(f"AUTO_SYNC_DEBUG: Added file with serial {serial_number}: {file_data['filename']}")
                        else:
                            logger.debug(f"AUTO_SYNC_DEBUG: Skipping older file: {file_data['filename']}")
                    else:
                        logger.debug(f"AUTO_SYNC_DEBUG: Skipping inactive serial: {serial_number}")
            
            logger.info(f"AUTO_SYNC_DEBUG: Completed SMOO barologger scan - found {len(files_found)} files")
            return files_found
            
        except Exception as e:
            logger.error(f"AUTO_SYNC_DEBUG: Error scanning SMOO for barologger files: {e}")
            return []
    
    def _scan_smoo_for_water_level_files(self, current_month, active_wells):
        """Scan SMOO consolidated folder for new water level files using direct file system access"""
        files_found = []
        
        try:
            logger.info(f"Scanning SMOO for water level files in {current_month}")
            
            # Get smart month ranges for each well
            well_month_ranges = self._get_water_level_search_ranges(active_wells)
            logger.info(f"Water level month ranges: {well_month_ranges}")
            
            # Get all available month folders if needed
            needs_all_months = any(month_range == "ALL_AVAILABLE" for month_range in well_month_ranges.values())
            
            if needs_all_months:
                logger.info("Some wells need ALL_AVAILABLE search, getting all month folders...")
                month_folders = self.smoo_scanner.get_all_available_month_folders()
            else:
                # Get specific month folders needed
                months_to_scan = set()
                for month_range in well_month_ranges.values():
                    if isinstance(month_range, list):
                        months_to_scan.update(month_range)
                    elif month_range != "ALL_AVAILABLE":
                        months_to_scan.add(month_range)
                
                # Add current month as fallback
                months_to_scan.add(current_month)
                logger.info(f"Scanning specific months: {months_to_scan}")
                
                month_folders = {}
                for month in months_to_scan:
                    folders = self.smoo_scanner.get_month_folders(month)
                    month_folders.update(folders)
            
            logger.info(f"Found {len(month_folders)} month folders to scan")
            
            # Scan each month folder for water level files
            for month_name, folder_path in month_folders.items():
                logger.info(f"Scanning month folder: {month_name} at {folder_path}")
                
                # Scan month folder root for metadata.json and XLE files
                logger.debug(f"Scanning month folder root: {folder_path}")
                
                # Scan for XLE files using metadata.json in month folder root
                month_readings = self.smoo_scanner.scan_xle_files(str(folder_path))
                logger.info(f"Found {len(month_readings)} water level readings in {month_name}")
                
                # Check each file against active wells
                for location, file_data in month_readings.items():
                    try:
                        filename = file_data['filename']
                        
                        # Extract CAE number from filename (location part)
                        cae_number = location
                        
                        # Check if this is an active well
                        if cae_number in active_wells:
                            # Check if this file is newer than existing data
                            if self._is_smoo_water_level_file_newer(file_data, cae_number):
                                files_found.append({
                                    'name': filename,
                                    'cae_number': cae_number,
                                    'folder_name': month_name,
                                    'file_path': file_data['file_path'],
                                    'reading_date': file_data['date']
                                })
                                logger.info(f"Added water level file: {filename} (CAE: {cae_number})")
                            else:
                                logger.debug(f"Skipping older file: {filename}")
                        else:
                            logger.debug(f"Skipping inactive well: {cae_number}")
                            
                    except Exception as file_error:
                        logger.warning(f"Error processing file {file_data}: {file_error}")
                        continue
            
            logger.info(f"Completed SMOO water level scan - found {len(files_found)} files")
            return files_found
            
        except Exception as e:
            logger.error(f"Error scanning SMOO for water level files: {e}")
            return []
    
    def _is_smoo_barologger_file_newer(self, file_data, serial_number):
        """Check if SMOO barologger file is newer than existing database data"""
        try:
            # Get the end date from the filename or file data
            if 'reading_date' in file_data:
                file_end_date = file_data['reading_date']
            else:
                file_end_date = self.smoo_scanner.extract_date_from_filename(file_data['filename'])
            
            if not file_end_date:
                logger.warning(f"Could not determine file date for {file_data['filename']}, processing anyway")
                return True
            
            # Check against database - get last reading for this serial number
            if self.db_manager and self.db_manager.current_db:
                conn = sqlite3.connect(self.db_manager.current_db)
                cursor = conn.cursor()
                
                # Get the latest reading timestamp for this barologger
                cursor.execute("""
                    SELECT MAX(timestamp_utc) 
                    FROM barometric_readings 
                    WHERE serial_number = ?
                """, (serial_number,))
                
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    last_data_timestamp = datetime.fromisoformat(result[0])
                    
                    # Check if file end date is newer than last data
                    if file_end_date > last_data_timestamp:
                        logger.info(f"File {file_data['filename']} is newer ({file_end_date}) than last data ({last_data_timestamp}) - processing")
                        return True
                    else:
                        logger.info(f"File {file_data['filename']} is not newer than last data ({last_data_timestamp}) - skipping")
                        return False
            
            logger.info(f"No previous data found for barologger {serial_number}, will process file {file_data['filename']}")
            return True  # No previous data, process the file
            
        except Exception as e:
            logger.error(f"Error checking if barologger file is newer: {e}")
            return True  # When in doubt, process the file
    
    def _is_smoo_water_level_file_newer(self, file_data, cae_number):
        """Check if SMOO water level file is newer than existing database data"""
        try:
            # Get the end date from the filename or file data
            if 'reading_date' in file_data:
                file_end_date = file_data['reading_date']
            else:
                file_end_date = self.smoo_scanner.extract_date_from_filename(file_data['filename'])
            
            if not file_end_date:
                logger.warning(f"Could not determine file date for {file_data['filename']}, processing anyway")
                return True
            
            # Check against database - get last reading for this well
            if self.db_manager and self.db_manager.current_db:
                conn = sqlite3.connect(self.db_manager.current_db)
                cursor = conn.cursor()
                
                # Get the latest reading timestamp for this well 
                # Convert CAE to well_number first
                cursor.execute("SELECT well_number FROM wells WHERE cae_number = ?", (cae_number,))
                well_result = cursor.fetchone()
                if not well_result:
                    logger.warning(f"Could not find well_number for CAE {cae_number}")
                    return True  # Process the file if we can't determine the well
                
                well_number = well_result[0]
                cursor.execute("""
                    SELECT MAX(timestamp_utc) 
                    FROM water_level_readings 
                    WHERE well_number = ?
                """, (well_number,))
                
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    last_data_timestamp = datetime.fromisoformat(result[0])
                    
                    # Check if file end date is newer than last data
                    if file_end_date > last_data_timestamp:
                        logger.info(f"File {file_data['filename']} is newer ({file_end_date}) than last data ({last_data_timestamp}) - processing")
                        return True
                    else:
                        logger.info(f"File {file_data['filename']} is not newer than last data ({last_data_timestamp}) - skipping")
                        return False
            
            logger.info(f"No previous data found for well {cae_number}, will process file {file_data['filename']}")
            return True  # No previous data, process the file
            
        except Exception as e:
            logger.error(f"Error checking if water level file is newer: {e}")
            return True  # When in doubt, process the file
    
    def test_generate_metadata(self):
        """Test method to generate metadata files - can be called manually for now"""
        def progress_callback(message, percent):
            print(f"[{percent:3d}%] {message}")
        
        print("Starting metadata generation for existing consolidated files...")
        success = self.generate_metadata_files_for_existing_data(progress_callback)
        
        if success:
            print("✓ Metadata generation completed successfully!")
        else:
            print("✗ Metadata generation failed. Check logs for details.")
        
        return success