import os
import logging
import tempfile
import shutil
import zipfile
from pathlib import Path
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
from .google_drive_service import GoogleDriveService
import json  # Added for pretty-printing API responses

logger = logging.getLogger(__name__)

class GoogleDriveDataHandler:
    """
    Handles data folder operations with Google Drive.
    Allows downloading and uploading data folders from/to Google Drive.
    """
    
    def __init__(self, settings_handler):
        """Initialize the Google Drive data handler."""
        self.settings_handler = settings_handler
        self.drive_service = GoogleDriveService.get_instance(settings_handler)
        self.local_data_path = None
        self.drive_data_id = None
        self.folder_id = None
        # Remove hardcoded runs folder ID - we'll find it dynamically based on project context
        
    def authenticate(self):
        """Authenticate with Google Drive."""
        if self.drive_service.authenticate():
            # Use the main folder ID for general data operations
            self.folder_id = self.settings_handler.get_setting("google_drive_folder_id", "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK")
            if not self.folder_id:
                logger.error("Google Drive folder ID not set")
                return False
            logger.info(f"Using Google Drive folder ID for data: {self.folder_id}")
            return True
        return False
    
    def find_data_folder(self, folder_name="data"):
        """Find a data folder in the Google Drive folder."""
        logger.warning(f"STARTING find_data_folder for '{folder_name}'")
        
        service = self.drive_service.get_service()
        if not service or not self.folder_id:
            logger.warning("Not authenticated or folder ID not set")
            return None
            
        try:
            # Only look for folder, ignore zip files
            query = f"name = '{folder_name}' and '{self.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            logger.warning(f"Drive API query: {query}")
            
            # Execute the query with additional debugging
            logger.warning("Executing Google Drive API list request...")
            results = service.files().list(
                q=query,
                fields="files(id, name, modifiedTime)",
                spaces='drive'
            ).execute()
            
            # Log the raw response for debugging
            logger.warning(f"Drive API response folders count: {len(results.get('files', []))}")
            
            folders = results.get('files', [])
            if not folders:
                logger.warning(f"No folders named '{folder_name}' found in {self.folder_id}")
                return None
                
            # Use the first folder found
            self.drive_data_id = folders[0]['id']
            logger.warning(f"Using folder: {folders[0]['name']} ({folders[0]['id']})")
            return folders[0]
            
        except Exception as e:
            logger.warning(f"Error finding data folder: {e}", exc_info=True)
            return None
    
    def download_data_folder(self, folder_name="data", local_dir=None):
        """
        Download a data folder from Google Drive.
        
        Args:
            folder_name: Name of the data folder
            local_dir: Local directory to save the folder (defaults to app directory)
            
        Returns:
            Path to the downloaded folder or None if failed
        """
        # Add explicit warning at the beginning to confirm method is called
        logger.warning(f"STARTING download_data_folder for '{folder_name}' - FOLDER_ID={self.folder_id}")
        
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.warning("No Drive service available, attempting to authenticate")
                if not self.authenticate():
                    logger.error("Authentication failed, cannot download folder")
                    return None
                service = self.drive_service.get_service()
                    
            try:
                logger.warning(f"Searching for data folder '{folder_name}' in Drive folder: {self.folder_id}")
                
                # Find the data folder
                logger.warning("About to call find_data_folder()")
                data_folder = self.find_data_folder(folder_name)
                
                if not data_folder:
                    logger.warning(f"No data folder named '{folder_name}' found in Drive folder {self.folder_id}")
                    # List all folders at the root level to see what's available
                    all_items_query = f"'{self.folder_id}' in parents and trashed = false"
                    all_items = service.files().list(
                        q=all_items_query,
                        fields="files(id, name, mimeType)",
                        spaces='drive'
                    ).execute()
                    
                    items = all_items.get('files', [])
                    logger.warning(f"Contents of parent folder {self.folder_id}:")
                    for item in items:
                        logger.warning(f"  - {item.get('name')} ({item.get('mimeType')})")
                    
                    return None
                
                logger.warning(f"Found data folder: {data_folder['name']} with ID {data_folder['id']}")
                
                # Determine local path
                if not local_dir:
                    local_dir = self.settings_handler.get_setting("local_db_directory", str(Path.cwd()))
                
                logger.warning(f"Using local directory: {local_dir}")    
                local_path = Path(local_dir) / folder_name
                logger.warning(f"Local data path will be: {local_path}")
                
                # Force delete the existing folder if it exists
                if local_path.exists():
                    logger.warning(f"Existing data folder found at {local_path}, deleting...")
                    import subprocess
                    try:
                        result = subprocess.run(['cmd', '/c', f'rmdir /s /q "{local_path}"'], 
                                              check=True, capture_output=True, text=True)
                        logger.warning(f"Delete command result: {result.returncode}")
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Error deleting existing folder: {e}")
                        # Continue anyway
                
                # Create the directory
                logger.warning(f"Creating directory at {local_path}")
                os.makedirs(local_path, exist_ok=True)
                
                # Download folder contents recursively
                logger.warning(f"Starting download of folder contents from {data_folder['id']} to {local_path}")
                self._download_folder_contents(service, data_folder['id'], local_path)
                
                self.local_data_path = local_path
                logger.warning(f"Download COMPLETED. Data folder saved to {local_path}")
                
                # Verify contents were downloaded
                if local_path.exists():
                    file_count = sum(1 for _ in local_path.glob('**/*') if _.is_file())
                    dir_count = sum(1 for _ in local_path.glob('**/*') if _.is_dir())
                    logger.warning(f"Downloaded {file_count} files in {dir_count} directories")
                    
                    # List first few files to confirm content
                    files = list(local_path.glob('**/*'))[:10]
                    logger.warning("Sample of downloaded files:")
                    for f in files:
                        logger.warning(f"  - {f.relative_to(local_path)}")
                
                return local_path
                
            except Exception as e:
                logger.warning(f"Error in download_data_folder inner try block: {e}", exc_info=True)
                return None
                
        except Exception as e:
            logger.warning(f"Error in download_data_folder outer try block: {e}", exc_info=True)
            return None
            
    def _download_folder_contents(self, service, folder_id, local_path):
        """
        Recursively download contents of a folder.
        """
        try:
            # List all files and folders in current folder
            logger.warning(f"Listing contents of folder ID: {folder_id} to download to {local_path}")
            query = f"'{folder_id}' in parents and trashed = false"
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)",
                pageSize=1000
            ).execute()
            
            items = results.get('files', [])
            logger.warning(f"Found {len(items)} items in folder {folder_id}")
            
            for i, item in enumerate(items):
                item_path = local_path / item['name']
                logger.warning(f"Processing item {i+1}/{len(items)}: {item['name']} ({item['mimeType']})")
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Create folder and download its contents
                    logger.warning(f"Creating directory: {item_path}")
                    os.makedirs(item_path, exist_ok=True)
                    self._download_folder_contents(service, item['id'], item_path)
                else:
                    # Download file
                    logger.warning(f"Downloading file: {item['name']} (ID: {item['id']}) to {item_path}")
                    request = service.files().get_media(fileId=item['id'])
                    
                    with open(item_path, 'wb') as f:
                        downloader = MediaIoBaseDownload(f, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                    
                    # Verify file was downloaded correctly
                    if item_path.exists():
                        file_size = item_path.stat().st_size
                        logger.warning(f"Downloaded file: {item_path} ({file_size} bytes)")
                    else:
                        logger.warning(f"File appears to be missing after download: {item_path}")
        except Exception as e:
            logger.warning(f"Error downloading folder contents: {e}", exc_info=True)
            raise  # Re-raise to ensure parent method knows about the failure
    
    def upload_data_folder(self, local_path=None, as_zip=True):
        """
        Upload a data folder to Google Drive.
        
        Args:
            local_path: Path to the local data folder
            as_zip: Whether to upload as a zip file (recommended)
            
        Returns:
            True if successful, False otherwise
        """
        service = self.drive_service.get_service()
        if not service:
            if not self.authenticate():
                return False
            service = self.drive_service.get_service()
                
        try:
            if not local_path and self.local_data_path:
                local_path = self.local_data_path
                
            if not local_path or not os.path.exists(local_path):
                logger.error("Local data folder not found")
                return False
            
            local_path = Path(local_path)
            folder_name = local_path.name
            
            if as_zip:
                # Create a temporary zip file
                fd, temp_zip_path = tempfile.mkstemp(suffix='.zip')
                os.close(fd)
                
                try:
                    # Create a zip file of the data folder
                    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(local_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.path.dirname(local_path))
                                zipf.write(file_path, arcname)
                    
                    # Check if zip file exists in Drive
                    zip_name = f"{folder_name}.zip"
                    data_item = self.find_data_folder(zip_name)
                    
                    if data_item:
                        # Update existing file
                        media = MediaFileUpload(temp_zip_path, resumable=True)
                        service.files().update(
                            fileId=self.drive_data_id,
                            media_body=media
                        ).execute()
                        logger.info(f"Updated data folder zip {zip_name} in Google Drive")
                    else:
                        # Create new file
                        file_metadata = {
                            'name': zip_name,
                            'parents': [self.folder_id]
                        }
                        media = MediaFileUpload(temp_zip_path, resumable=True)
                        file = service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields='id'
                        ).execute()
                        self.drive_data_id = file.get('id')
                        logger.info(f"Created data folder zip {zip_name} in Google Drive")
                finally:
                    # Clean up the temporary zip file
                    if os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
            else:
                # Upload as a folder (not implemented yet)
                logger.error("Uploading as a folder is not implemented yet")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error uploading data folder: {e}")
            return False
    
    def create_data_folder(self, folder_name="data", local_dir=None):
        """
        Create a new empty data folder and upload it to Google Drive.
        
        Args:
            folder_name: Name of the data folder
            local_dir: Local directory to save the folder (defaults to app directory)
            
        Returns:
            Path to the created folder or None if failed
        """
        try:
            # Determine local path
            if not local_dir:
                local_dir = self.settings_handler.get_setting("local_db_directory", str(Path.cwd()))
                
            local_path = Path(local_dir) / folder_name
            
            # Create empty data folder with runs subfolder
            os.makedirs(local_path / "runs", exist_ok=True)
            
            # Create a README file
            with open(local_path / "README.txt", 'w') as f:
                f.write("This folder contains data for the Water Level Monitoring System.\n")
                f.write("The 'runs' subfolder contains water level run data.\n")
                
            # Upload to Google Drive
            self.local_data_path = local_path
            if self.upload_data_folder(local_path):
                return local_path
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error creating data folder: {e}")
            return None
    
    def _find_project_runs_folder(self, service, project_name):
        """
        Find the WATER_LEVEL_RUNS folder for a specific project.
        
        Args:
            service: Google Drive service instance
            project_name: Name of the project
            
        Returns:
            Folder ID of the WATER_LEVEL_RUNS folder, or None if not found
        """
        try:
            # Get main water_levels_monitoring folder
            main_folder_id = self.settings_handler.get_setting("google_drive_folder_id")
            if not main_folder_id:
                logger.error("Google Drive folder ID not set")
                return None
            
            # Find Projects folder
            query = f"'{main_folder_id}' in parents and name='Projects' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            projects_folders = results.get('files', [])
            
            if not projects_folders:
                logger.error("Projects folder not found")
                return None
            
            projects_folder_id = projects_folders[0]['id']
            
            # Find specific project folder
            query = f"'{projects_folder_id}' in parents and name='{project_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            project_folders = results.get('files', [])
            
            if not project_folders:
                logger.error(f"Project folder '{project_name}' not found")
                return None
            
            project_folder_id = project_folders[0]['id']
            
            # Find WATER_LEVEL_RUNS folder
            query = f"'{project_folder_id}' in parents and name='WATER_LEVEL_RUNS' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            runs_folders = results.get('files', [])
            
            if not runs_folders:
                logger.info(f"WATER_LEVEL_RUNS folder not found for project {project_name}, creating it...")
                # Create WATER_LEVEL_RUNS folder
                folder_metadata = {
                    'name': 'WATER_LEVEL_RUNS',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [project_folder_id]
                }
                runs_folder = service.files().create(body=folder_metadata, fields='id').execute()
                return runs_folder.get('id')
            
            return runs_folders[0]['id']
            
        except Exception as e:
            logger.error(f"Error finding project runs folder: {e}")
            return None
    
    def upload_run_folder(self, run_id, project_name=None):
        """
        Upload a specific run folder to Google Drive using proper cloud project structure.
        Structure: water_levels_monitoring/Projects/[PROJECT]/WATER_LEVEL_RUNS/[YEAR-MONTH]/
        
        Args:
            run_id: ID of the run folder to upload (e.g., "2025-06")
            project_name: Name of the project (if None, will try to get from current context)
            
        Returns:
            True if successful, False otherwise
        """
        service = self.drive_service.get_service()
        if not service:
            if not self.authenticate():
                return False
            service = self.drive_service.get_service()
                
        try:
            # Construct the run folder path
            run_folder_path = Path('data/runs') / run_id
            if not run_folder_path.exists():
                logger.error(f"Run folder not found: {run_folder_path}")
                return False
            
            # Get project name from current context if not provided
            if not project_name:
                # Try to get from database manager context (via main window)
                try:
                    # This is a bit of a hack, but we need to get the main window reference
                    from PyQt5.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        for widget in app.topLevelWidgets():
                            if hasattr(widget, 'db_manager') and hasattr(widget.db_manager, 'cloud_project_name'):
                                project_name = widget.db_manager.cloud_project_name
                                break
                except Exception as e:
                    logger.debug(f"Could not get project name from context: {e}")
                
                if not project_name:
                    logger.error("No project name provided and could not determine from context")
                    return False
            
            logger.info(f"Uploading run {run_id} to project {project_name}")
            
            # Find the project's WATER_LEVEL_RUNS folder
            runs_folder_id = self._find_project_runs_folder(service, project_name)
            if not runs_folder_id:
                logger.error(f"Could not find or create WATER_LEVEL_RUNS folder for project {project_name}")
                return False
            
            # Check if run folder already exists
            query = f"name = '{run_id}' and '{runs_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, fields="files(id)").execute()
            existing_folder = results.get('files', [])
            
            if existing_folder:
                run_folder_id = existing_folder[0]['id']
                logger.info(f"Found existing run folder: {run_id}")
            else:
                # Create run folder
                folder_metadata = {
                    'name': run_id,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [runs_folder_id]
                }
                run_folder = service.files().create(body=folder_metadata, fields='id').execute()
                run_folder_id = run_folder.get('id')
                logger.info(f"Created new run folder: {run_id}")
            
            # Upload each JSON file in the run folder
            uploaded_files = []
            for file_path in run_folder_path.glob('*.json'):
                file_metadata = {
                    'name': file_path.name,
                    'parents': [run_folder_id]
                }
                
                # Check if file already exists
                query = f"name = '{file_path.name}' and '{run_folder_id}' in parents and trashed = false"
                results = service.files().list(q=query, fields="files(id)").execute()
                existing_file = results.get('files', [])
                
                media = MediaFileUpload(str(file_path), resumable=True)
                
                if existing_file:
                    # Update existing file
                    service.files().update(
                        fileId=existing_file[0]['id'],
                        media_body=media
                    ).execute()
                    logger.debug(f"Updated existing file: {file_path.name}")
                else:
                    # Create new file
                    service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    logger.debug(f"Created new file: {file_path.name}")
                
                uploaded_files.append(file_path.name)
            
            logger.info(f"Successfully uploaded run folder: {run_id} with files: {uploaded_files}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading run folder: {e}")
            return False