import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime
from pathlib import Path
import json
import sqlite3  # Add import for SQLite

logger = logging.getLogger(__name__)

class RunsFolderMonitor:
    def __init__(self, folder_id="1FhCJH6KuvHcdFSpn0PxY8k9_-62vjmKj", db_path=None):
        self.folder_id = folder_id
        self.service = None
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.db_path = db_path
        self.latest_readings = {}
        self.logger = logger  # Use the module's logger
        # Initialize mapping
        self.location_to_well_mapping = {}
        
    def set_authenticated_service(self, service):
        """Set an already authenticated Google Drive service."""
        self.service = service
        return True
        
    def authenticate(self, client_secret_path=None):
        """Authenticate with Google Drive."""
        # Skip authentication if service is already set
        if self.service is not None:
            logger.debug("Using existing authenticated service")
            return True
            
        try:
            token_path = 'token_runs_monitor.pickle'
            creds = None
            
            # Check if token file exists
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh token if expired, or create new one if invalid
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.error(f"Authentication error: {e}")
                        # Token refresh failed, need to get a new one
                        creds = None
                
                if not creds:
                    if not client_secret_path or not os.path.exists(client_secret_path):
                        logger.error("Client secret file not found")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secret_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    # Save the credentials for next run
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
            
            # Build the service
            self.service = build('drive', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_month_folders(self, year_month):
        """Get folders for current and next month"""
        try:
            # Convert year_month (2025-02) to folder format (2025_02)
            current_folder = year_month.replace('-', '_')
            
            # Calculate next month folder name
            year = int(year_month[:4])
            month = int(year_month[5:7])
            if month == 12:
                next_month = f"{year + 1}_01"
            else:
                next_month = f"{year}_{month + 1:02d}"

            # Search for exact folder names
            folders = {}
            query = f"'{self.folder_id}' in parents and (name = '{current_folder}' or name = '{next_month}') and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            
            logger.debug(f"Searching for folders: {current_folder} and {next_month} in parent folder {self.folder_id}")
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            # Store folder IDs by name
            for folder in results.get('files', []):
                logger.debug(f"Found folder: {folder['name']} with ID: {folder['id']}")
                folders[folder['name']] = folder['id']

            if not folders:
                logger.warning(f"No folders found matching {current_folder} or {next_month}")
            
            return {
                current_folder: folders.get(current_folder),
                next_month: folders.get(next_month)
            }

        except Exception as e:
            logger.error(f"Error getting month folders: {e}")
            return {}

    def scan_xle_files(self, folder_id):
        """Scan XLE files in a folder and return dict mapping CAE -> latest reading date"""
        try:
            readings = {}
            logger.debug(f"Scanning folder {folder_id} for XLE files")
            
            query = f"'{folder_id}' in parents and fileExtension = 'xle' and trashed = false"
            logger.debug(f"Using query: {query}")
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, description, modifiedTime)',
                pageSize=1000
            ).execute()

            files = results.get('files', [])
            logger.debug(f"Found {len(files)} XLE files in folder {folder_id}")
            
            for file in files:
                try:
                    filename = file['name']
                    logger.debug(f"Processing file: {filename}")
                    
                    # Extract location from filename
                    location = filename.split('_')[0]  
                    logger.debug(f"Extracted location from filename: {location}")
                    
                    # Extract date from filename instead of using modified time
                    reading_date = self.extract_date_from_filename(filename)
                    if reading_date is None:
                        # Fallback to modified time if we can't extract date from filename
                        logger.debug(f"Could not extract date from filename, using modified time")
                        reading_date = datetime.fromisoformat(
                            file['modifiedTime'].replace('Z', '+00:00')
                        )
                    else:
                        logger.debug(f"Extracted date from filename: {reading_date}")
                    
                    # Keep the latest reading for each location
                    if location not in readings or reading_date > readings[location]['date']:
                        readings[location] = {
                            'date': reading_date,
                            'file_name': filename
                        }

                except Exception as e:
                    logger.warning(f"Error processing file {file['name']}: {e}")
                    continue

            logger.debug(f"Found readings for locations: {list(readings.keys())}")
            return readings

        except Exception as e:
            logger.error(f"Error scanning XLE files: {e}")
            return {}
            
    def extract_date_from_filename(self, filename):
        """Extract the end date from an XLE filename.
        
        Handles two formats:
        - Full date: J140_2022_12_3_To_2023_01_02.xle
        - Abbreviated: J140_2022_12_3_To_12_22.xle (reuses year from start date)
        
        Returns a datetime object representing the end date.
        """
        try:
            # Split on '_To_' to get the end date part
            if '_To_' not in filename:
                logger.warning(f"Could not find '_To_' in filename: {filename}")
                return None
                
            # Get the parts before and after '_To_'
            start_part, end_part = filename.split('_To_')
            
            # Remove file extension from end part
            end_part = end_part.split('.')[0]
            
            # Split start and end parts into components
            start_components = start_part.split('_')
            end_components = end_part.split('_')
            
            # Find the position where the year appears in start_components
            year_pos = -1
            for i, part in enumerate(start_components):
                if len(part) == 4 and part.isdigit():  # Year is 4 digits
                    year_pos = i
                    break
                    
            if year_pos == -1:
                logger.warning(f"Could not find year in start part: {start_part}")
                return None
            
            start_year = start_components[year_pos]
            
            # Check if end part is a full or abbreviated date
            if len(end_components) >= 3 and len(end_components[0]) == 4 and end_components[0].isdigit():
                # Full date format: 2023_01_02
                year = end_components[0]
                month = end_components[1]
                day = end_components[2]
            else:
                # Abbreviated format: 12_22 - reuse year from start
                year = start_year
                month = end_components[0]
                day = end_components[1]
            
            # Padding day and month with zeros if needed
            month = month.zfill(2)
            day = day.zfill(2)
            
            # Create date string and convert to datetime
            date_str = f"{year}-{month}-{day}"
            logger.debug(f"Created date string from filename: {date_str}")
            
            # Make a datetime object at the END of the day (23:59:59)
            dt = datetime.strptime(f"{date_str} 23:59:59", "%Y-%m-%d %H:%M:%S")
            return dt
            
        except Exception as e:
            logger.error(f"Error extracting date from filename {filename}: {e}")
            return None

    def get_latest_readings(self, year_month):
        """Get latest readings for all wells for given month"""
        if not self.service:
            logger.error("Not authenticated with Google Drive")
            return {}
            
        try:
            # Get relevant folders
            folders = self.get_month_folders(year_month)
            
            # Combine readings from both folders
            all_readings = {}
            for folder_id in folders.values():
                if folder_id is not None:  # Only scan folders that exist
                    readings = self.scan_xle_files(folder_id)
                    for location, data in readings.items():
                        if location not in all_readings or data['date'] > all_readings[location]['date']:
                            all_readings[location] = data

            return all_readings

        except Exception as e:
            logger.error(f"Error getting latest readings: {e}")
            return {}

    def get_folder_for_file(self, filename):
        """Get the correct folder ID for a file based on its end date in filename"""
        try:
            # P-210_2024_08_12_To_2025_02_10.xle -> 2025_02
            end_date = filename.split('_To_')[1].split('.')[0]  # Gets 2025_02_10
            folder_name = '_'.join(end_date.split('_')[:2])    # Gets 2025_02
            
            # Check if folder exists
            query = f"'{self.folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            
            if results.get('files'):
                return results['files'][0]['id']
            
            # Create folder if it doesn't exist
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.folder_id]
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder['id']
            
        except Exception as e:
            logger.error(f"Error getting folder for file {filename}: {e}")
            return None 

    def get_or_create_month_folder(self, folder_name):
        """Get or create a single folder for a month (no suffixes)"""
        try:
            # First try to find existing folder
            query = f"'{self.folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            
            if results.get('files'):
                logger.debug(f"Found existing folder {folder_name}")
                return results['files'][0]['id']
            
            # If folder doesn't exist, create it (exactly once)
            logger.debug(f"Creating new folder {folder_name}")
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.folder_id]
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder['id']
            
        except Exception as e:
            logger.error(f"Error with folder {folder_name}: {e}")
            return None

    def move_file_to_month_folder(self, file_id, filename):
        """Move a file to its correct month folder"""
        try:
            # Get month from filename end date
            end_date = filename.split('_To_')[1].split('.')[0]  # Gets 2025_02_10
            folder_name = '_'.join(end_date.split('_')[:2])    # Gets 2025_02
            
            folder_id = self.get_or_create_month_folder(folder_name)
            if not folder_id:
                return False
            
            # Move file to folder
            self.service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=self.folder_id,
                fields='id, parents'
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error moving file {filename}: {e}")
            return False

    def extract_location_from_filename(self, filename):
        """Extract the location code from a filename."""
        try:
            # Get just the filename part without path
            base_filename = os.path.basename(filename)
            # Location is typically before the first underscore
            location = base_filename.split('_')[0]
            self.logger.debug(f"Extracted location from filename: {location}")
            return location
        except Exception as e:
            self.logger.error(f"Error extracting location from filename {filename}: {e}")
            return None

    def process_files(self, files_list, db_path=None):
        """Process a list of files to extract locations and readings"""
        # Set up database path if provided
        if db_path:
            self.db_path = db_path
            
        self.latest_readings = {}
        locations = []
        for file_path in files_list:
            location = self.extract_location_from_filename(file_path)
            date = self.extract_date_from_filename(file_path)
            
            # Add both the location and file path to track which file corresponds to which location
            if location:
                locations.append(location)
                # Store the file information for later processing
                if location not in self.latest_readings:
                    self.latest_readings[location] = {'date': date, 'file_path': file_path}
                elif date and date > self.latest_readings[location]['date']:
                    self.latest_readings[location] = {'date': date, 'file_path': file_path}
        
        self.logger.debug(f"Found readings for locations: {locations}")
        
        # Get mapping from location codes to well numbers
        self.location_to_well_mapping = self.get_location_to_well_mapping()
        
        return self.latest_readings

    def get_location_to_well_mapping(self):
        """Query the database to get mapping between location codes and well numbers"""
        mapping = {}
        try:
            if not self.db_path:
                self.logger.error("Database path not set")
                return {}
                
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query the table that contains the mapping
            cursor.execute("SELECT cae_number, well_number FROM wells WHERE cae_number IS NOT NULL")
            
            # Build the mapping dictionary
            for row in cursor.fetchall():
                cae, well_number = row
                if cae:  # Only add if cae is not empty
                    mapping[cae] = well_number
                    
            conn.close()
            self.logger.debug(f"Created location to well mapping with {len(mapping)} entries")
            return mapping
        except Exception as e:
            self.logger.error(f"Error getting location to well mapping: {str(e)}")
            return {}