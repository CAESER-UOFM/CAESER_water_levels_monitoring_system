import os
import logging
from pathlib import Path
import json
from datetime import datetime, timedelta
import tempfile
from ..handlers.solinst_reader import SolinstReader
from .google_service_account import GoogleServiceAccountHandler
import pandas as pd

logger = logging.getLogger(__name__)

class GoogleDriveMonitor:
    """
    Monitors SOLINST folder using service account for XLE files and processes them to SMOO.
    Replaces OAuth-based GoogleDriveService with service account authentication.
    """
    
    def __init__(self, service_account_handler=None, settings_handler=None):
        """Initialize the SOLINST folder monitor with service account."""
        self.service_account_handler = service_account_handler
        self.settings_handler = settings_handler
        self.solinst_reader = SolinstReader()
        self.processed_files = set()  # Keep track of processed files
        
        # SMOO destination configuration
        self.smoo_destination_path = settings_handler.get_setting("shared_drive_field_data", "") if settings_handler else ""
        
        logger.info("GoogleDriveMonitor initialized - Service Account → SMOO mode")
        if self.smoo_destination_path:
            logger.info(f"SMOO destination: {self.smoo_destination_path}")
        
    def authenticate(self, service_account_key_path=None):
        """Authenticate using service account credentials."""
        if not self.service_account_handler:
            logger.error("Service account handler not provided")
            return False
            
        if self.service_account_handler.authenticate(service_account_key_path):
            logger.info("Service account authentication successful for SOLINST folder monitoring")
            return True
        else:
            logger.error("Service account authentication failed")
            return False
    
    def set_smoo_destination(self, smoo_path):
        """Set the SMOO destination path."""
        self.smoo_destination_path = smoo_path
        if self.settings_handler:
            self.settings_handler.set_setting("shared_drive_field_data", smoo_path)
        logger.info(f"SMOO destination set to: {smoo_path}")
        
    def initialize_smoo_folders(self):
        """Initialize or create the required folders in SMOO destination."""
        if not self.smoo_destination_path:
            logger.error("SMOO destination path not configured")
            return False
            
        try:
            # Create base folder structure in SMOO
            all_folder_path = os.path.join(self.smoo_destination_path, "all")
            runs_folder_path = os.path.join(self.smoo_destination_path, "runs")
            
            os.makedirs(all_folder_path, exist_ok=True)
            os.makedirs(runs_folder_path, exist_ok=True)
            
            logger.info(f"Initialized SMOO folders: {all_folder_path}, {runs_folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing SMOO folders: {e}")
            return False
    
    def check_for_new_files(self, well_runs=None):
        """Check for new XLE files in SOLINST folder and process them to SMOO."""
        if not self.service_account_handler or not self.service_account_handler.is_authenticated():
            logger.error("Service account handler not available or not authenticated")
            return None
            
        if not self.smoo_destination_path:
            logger.error("SMOO destination path not configured")
            return None
        
        try:
            # Initialize SMOO folders if needed
            if not self.initialize_smoo_folders():
                return None
            
            # Get all XLE files from SOLINST folder
            files = self.service_account_handler.list_xle_files()
            
            if not files:
                logger.info("No new XLE files found in SOLINST folder")
                return {}
            
            logger.info(f"Found {len(files)} XLE files to process")
            
            processed_files_dict = {}
            
            for file in files:
                if file['id'] in self.processed_files:
                    continue
                
                # Download file using service account
                temp_file = self.service_account_handler.download_file(file['id'])
                if not temp_file:
                    continue
                
                try:
                    # Read XLE file metadata and data
                    df, metadata = self.solinst_reader.read_xle(temp_file)
                    
                    # Get actual start and end dates from the timestamp_utc column
                    if not df.empty:
                        actual_start = df['timestamp_utc'].min()
                        actual_end = df['timestamp_utc'].max()
                        logger.debug(f"File {file['name']}: Start: {actual_start}, End: {actual_end}")
                    else:
                        logger.warning(f"No data found in file {file['id']}")
                        continue
                    
                    # Generate new file name using actual dates
                    new_name = self._generate_file_name(metadata, actual_start, actual_end)
                    
                    # Save to SMOO 'all' folder with new name
                    all_folder_path = os.path.join(self.smoo_destination_path, "all")
                    all_file_path = os.path.join(all_folder_path, new_name)
                    
                    import shutil
                    shutil.copy2(temp_file, all_file_path)
                    logger.info(f"Saved {new_name} to SMOO 'all' folder")
                    
                    # Create monthly run folder using actual end date
                    start_month = actual_end.strftime("%Y_%m")
                    runs_folder_path = os.path.join(self.smoo_destination_path, "runs")
                    monthly_folder_path = os.path.join(runs_folder_path, start_month)
                    
                    os.makedirs(monthly_folder_path, exist_ok=True)
                    
                    # Copy file to monthly run folder
                    monthly_file_path = os.path.join(monthly_folder_path, new_name)
                    shutil.copy2(temp_file, monthly_file_path)
                    logger.info(f"Copied {new_name} to SMOO monthly folder {start_month}")
                    
                    # Track processed file
                    location = metadata.location.strip().upper()
                    if location not in processed_files_dict:
                        processed_files_dict[location] = []
                    
                    processed_files_dict[location].append({
                        'file_name': new_name,
                        'start_date': actual_start,
                        'end_date': actual_end,
                        'file_id': file['id'],
                        'smoo_all_path': all_file_path,
                        'smoo_monthly_path': monthly_file_path
                    })
                    
                    self.processed_files.add(file['id'])
                    
                finally:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                    
            return processed_files_dict
            
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
            return None
    
    # NOTE: _download_file method removed - now using service_account_handler.download_file()
    
    def _generate_file_name(self, metadata, actual_start, actual_end):
        """Generate a standardized file name based on metadata and actual data dates."""
        # Format: SERIALNUMBER_LOCATION_YYYY_MM_DD_To_YYYY_MM_DD.xle
        location = metadata.location.strip().upper()
        serial_number = metadata.serial_number.strip().upper()
        
        # Format start date from actual data
        start_year = actual_start.strftime("%Y")
        start_month = actual_start.strftime("%m")
        start_day = actual_start.strftime("%d")
        
        # Format end date from actual data
        end_year = actual_end.strftime("%Y")
        end_month = actual_end.strftime("%m")
        end_day = actual_end.strftime("%d")
        
        # If years are the same, only include year once
        if start_year == end_year:
            return f"{serial_number}_{location}_{start_year}_{start_month}_{start_day}_To_{end_month}_{end_day}.xle"
        else:
            return f"{serial_number}_{location}_{start_year}_{start_month}_{start_day}_To_{end_year}_{end_month}_{end_day}.xle"
    
    def create_smoo_run_folder(self, folder_name):
        """Get or create a folder in the SMOO runs directory"""
        try:
            if not self.smoo_destination_path:
                logger.error("SMOO destination path not configured")
                return None
                
            runs_folder_path = os.path.join(self.smoo_destination_path, "runs")
            monthly_folder_path = os.path.join(runs_folder_path, folder_name)
            
            # Create folder if it doesn't exist
            os.makedirs(monthly_folder_path, exist_ok=True)
            logger.info(f"Created/verified SMOO run folder: {monthly_folder_path}")
            
            return monthly_folder_path
            
        except Exception as e:
            logger.error(f"Error creating SMOO run folder '{folder_name}': {e}")
            return None