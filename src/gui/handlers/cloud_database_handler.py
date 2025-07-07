import os
import json
import logging
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from .draft_manager import DraftManager
from .version_manager import VersionManager
from .xle_file_manager import XLEFileManager
from googleapiclient.errors import HttpError
import io
import uuid

logger = logging.getLogger(__name__)

class CloudDatabaseHandler:
    """Handles cloud database operations for project-based databases in Google Drive"""
    
    def __init__(self, drive_service, settings_handler):
        """
        Initialize the cloud database handler.
        
        Args:
            drive_service: GoogleDriveService instance
            settings_handler: SettingsHandler instance
        """
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        self.projects_folder_id = None
        self.temp_files = []  # Track temp files for cleanup
        self.cache_dir = self._get_cache_directory()
        self.draft_manager = DraftManager(self.cache_dir)  # Initialize draft manager
        self.version_manager = VersionManager(self.cache_dir)  # Initialize version manager
        self.xle_manager = None  # Initialize when database manager available
        
        # Session state tracking for enhanced draft management
        self.session_backups = {}  # {project_name: {"original": path, "last_uploaded": path}}
        
    def get_projects_folder_id(self):
        """Get the projects folder ID from settings"""
        if not self.projects_folder_id:
            self.projects_folder_id = self.settings_handler.get_setting(
                "google_drive_projects_folder_id", "1JjiXRblLAf6rdhiOzrAaYik8bjNpBc9s"
            )
            logger.info(f"CloudDatabaseHandler projects folder ID: '{self.projects_folder_id}'")
        return self.projects_folder_id
    
    def _get_cache_directory(self) -> str:
        """Get or create the cache directory for storing downloaded databases"""
        # Use databases/temp folder instead of system temp
        # Use app directory instead of current working directory
        app_dir = Path(__file__).parent.parent.parent.parent
        local_db_directory = self.settings_handler.get_setting("local_db_directory", str(app_dir))
        cache_dir = os.path.join(local_db_directory, "temp")
        
        # Ensure the directory exists and is writable
        try:
            os.makedirs(cache_dir, exist_ok=True)
            # Test write permissions
            test_file = os.path.join(cache_dir, f"test_write_{int(time.time())}.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.debug(f"Cache directory confirmed: {cache_dir}")
        except Exception as e:
            logger.error(f"Error creating or accessing cache directory {cache_dir}: {e}")
            # Fallback to system temp if databases/temp fails
            import tempfile
            cache_dir = tempfile.mkdtemp(prefix="wlm_cache_")
            logger.warning(f"Using fallback cache directory: {cache_dir}")
            
        return cache_dir
    
    def _get_cached_db_path(self, project_name: str) -> str:
        """Get the path for cached database file"""
        return os.path.join(self.cache_dir, f"{project_name}.db")
    
    def _get_cached_metadata_path(self, project_name: str) -> str:
        """Get the path for cached metadata file"""
        return os.path.join(self.cache_dir, f"{project_name}_metadata.json")
    
    def _get_working_metadata_path(self, project_name: str) -> str:
        """Get the path for working database metadata file"""
        return os.path.join(self.cache_dir, f"{project_name}_working_metadata.json")
    
    def _is_cache_valid(self, project_name: str, cloud_modified_time: str) -> bool:
        """Check if cached database is still valid (up to date)"""
        try:
            metadata_path = self._get_cached_metadata_path(project_name)
            cached_db_path = self._get_cached_db_path(project_name)
            
            # Check if both metadata and database files exist
            if not (os.path.exists(metadata_path) and os.path.exists(cached_db_path)):
                return False
            
            # Read cached metadata
            with open(metadata_path, 'r') as f:
                cached_metadata = json.load(f)
            
            # Compare modification times
            cached_time = cached_metadata.get('modifiedTime', '')
            return cached_time == cloud_modified_time
            
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def _is_working_database_valid(self, project_name: str, cloud_modified_time: str) -> bool:
        """Check if working database is still valid (up to date with cloud)"""
        try:
            working_metadata_path = self._get_working_metadata_path(project_name)
            working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
            
            # Check if both metadata and database files exist
            if not (os.path.exists(working_metadata_path) and os.path.exists(working_db_path)):
                return False
            
            # Read working database metadata
            with open(working_metadata_path, 'r') as f:
                working_metadata = json.load(f)
            
            # Compare modification times
            working_time = working_metadata.get('modifiedTime', '')
            is_valid = working_time == cloud_modified_time
            
            if not is_valid:
                logger.warning(f"Working database for {project_name} is outdated. "
                             f"Local: {working_time}, Cloud: {cloud_modified_time}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error checking working database validity: {e}")
            return False
    
    def _save_cache_metadata(self, project_name: str, project_info: Dict):
        """Save metadata for cached database"""
        try:
            metadata_path = self._get_cached_metadata_path(project_name)
            metadata = {
                'project_name': project_name,
                'database_name': project_info['database_name'],
                'modifiedTime': project_info['modified_time'],
                'cached_at': datetime.now().isoformat(),
                'database_id': project_info['database_id']
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")
    
    def _save_working_metadata(self, project_name: str, project_info: Dict):
        """Save metadata for working database"""
        try:
            metadata_path = self._get_working_metadata_path(project_name)
            metadata = {
                'project_name': project_name,
                'database_name': project_info['database_name'],
                'modifiedTime': project_info['modified_time'],
                'preserved_at': datetime.now().isoformat(),
                'database_id': project_info['database_id'],
                'is_working_copy': True
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving working database metadata: {e}")
        
    def list_projects(self) -> List[Dict]:
        """
        List all available projects in the cloud.
        
        Returns:
            List of project dictionaries with name and metadata
        """
        projects = []
        
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.error("No Google Drive service available")
                return projects
                
            folder_id = self.get_projects_folder_id()
            if not folder_id:
                logger.info("Projects folder ID not configured - no cloud projects available")
                return projects
                
            # Query for folders in the Projects folder
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            response = service.files().list(
                q=query,
                fields="files(id, name, modifiedTime)",
                orderBy="name"
            ).execute()
            
            for folder in response.get('files', []):
                # Check if this project has a databases folder
                db_folder_id = self._find_databases_folder(service, folder['id'])
                if db_folder_id:
                    # Check for database files
                    db_info = self._get_project_database_info(service, db_folder_id)
                    if db_info:
                        projects.append({
                            'name': folder['name'],
                            'project_id': folder['id'],
                            'db_folder_id': db_folder_id,
                            'database_name': db_info['name'],
                            'database_id': db_info['id'],
                            'modified_time': db_info.get('modifiedTime', ''),
                            'locked_by': db_info.get('locked_by'),
                            'lock_time': db_info.get('lock_time')
                        })
                        
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            
        return projects
        
    def _find_databases_folder(self, service, project_id: str) -> Optional[str]:
        """Find the databases folder within a project"""
        try:
            query = f"'{project_id}' in parents and name='databases' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = service.files().list(q=query, fields="files(id)").execute()
            files = response.get('files', [])
            return files[0]['id'] if files else None
        except Exception as e:
            logger.error(f"Error finding databases folder: {e}")
            return None
            
    def _get_project_database_info(self, service, db_folder_id: str) -> Optional[Dict]:
        """Get information about the main database file in a project"""
        try:
            # Look for .db files in the databases folder
            query = f"'{db_folder_id}' in parents and name contains '.db' and trashed=false"
            response = service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, properties)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = response.get('files', [])
            if not files:
                return None
                
            # Get the most recent database file
            db_file = files[0]
            
            # Check for lock properties
            properties = db_file.get('properties', {})
            lock_info = {}
            if 'locked_by' in properties:
                lock_info['locked_by'] = properties['locked_by']
                lock_info['lock_time'] = properties.get('lock_time', '')
                
            return {
                'id': db_file['id'],
                'name': db_file['name'],
                'modifiedTime': db_file['modifiedTime'],
                **lock_info
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return None
            
    def download_database(self, project_name: str, project_info: Dict, progress_callback=None, prefer_draft=False, force_download=False) -> Optional[str]:
        """
        Download a database to a temporary location, using cache if available.
        
        Args:
            project_name: Name of the project
            project_info: Project information dictionary
            progress_callback: Optional callback function for progress updates
            prefer_draft: If True, prefer loading draft over cloud download
            force_download: If True, skip automatic cache usage (for version choice dialog)
            
        Returns:
            Path to the temporary database file
        """
        try:
            # Check for existing draft first if requested
            if prefer_draft and self.has_draft(project_name):
                logger.info(f"Loading existing draft for {project_name}")
                if progress_callback:
                    progress_callback(50, "Loading existing draft...")
                
                draft_path = self.load_draft(project_name)
                if draft_path:
                    if progress_callback:
                        progress_callback(100, "Draft loaded successfully")
                    return draft_path
            
            # Check for valid working database first (unless forced to download)
            working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
            cloud_modified_time = project_info.get('modified_time', '')
            
            if (not force_download and os.path.exists(working_db_path) and 
                self._is_working_database_valid(project_name, cloud_modified_time)):
                logger.info(f"Using existing working database for {project_name} (up to date)")
                if progress_callback:
                    progress_callback(100, "Using existing working database (up to date)")
                return working_db_path
            
            # OPTIMIZATION: Check if we have a valid working database (unless forced to download)
            # Single file system - the working database IS the cache
            working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
            if (not force_download and os.path.exists(working_db_path) and 
                self._is_working_database_valid(project_name, cloud_modified_time)):
                logger.info(f"Using existing working database for {project_name} (up to date)")
                if progress_callback:
                    progress_callback(100, "Using existing working database (up to date)")
                
                # No copying needed - just return the working file path
                if working_db_path not in self.temp_files:
                    self.temp_files.append(working_db_path)
                logger.info(f"Using existing working database: {working_db_path}")
                return working_db_path
            
            # Need to download from cloud
            service = self.drive_service.get_service()
            if not service:
                return None
            
            logger.info(f"Downloading {project_name} from cloud (cache outdated or missing)")
            if progress_callback:
                progress_callback(0, f"Downloading {project_info['database_name']} from cloud...")
                
            # OPTIMIZATION: Download directly to working file - single file system!
            temp_dir = self.cache_dir  # Use databases/temp folder
            temp_filename = f"wlm_{project_name}.db"  # Use consistent naming
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Remove old working file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Removed existing working file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Could not remove existing working file {temp_path}: {e}")
            
            # Also clean up any legacy cache files
            legacy_cache_path = self._get_cached_db_path(project_name)
            if os.path.exists(legacy_cache_path):
                try:
                    os.remove(legacy_cache_path)
                    logger.debug(f"Removed legacy cache file: {legacy_cache_path}")
                except Exception as e:
                    logger.warning(f"Could not remove legacy cache file {legacy_cache_path}: {e}")
            
            # Try alternative download method for better performance
            start_time = time.time()
            
            try:
                # Alternative 1: Try to get file metadata first
                file_metadata = service.files().get(fileId=project_info['database_id'], fields="size").execute()
                file_size = int(file_metadata.get('size', 0))
                logger.info(f"Database file size: {file_size / (1024*1024):.1f} MB")
                
                # OPTIMIZATION: Download directly to working file (no cache duplication)
                request = service.files().get_media(fileId=project_info['database_id'])
                with open(temp_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request, chunksize=8*1024*1024)  # 8MB chunks
                    done = False
                    downloaded_bytes = 0
                    last_log_time = start_time
                    last_progress = -1
                    
                    while not done:
                        status, done = downloader.next_chunk()
                        current_time = time.time()
                        
                        if status:
                            downloaded_bytes = int(status.resumable_progress)
                            progress = int(status.progress() * 100)
                            elapsed = current_time - start_time
                            speed_mbps = (downloaded_bytes / (1024*1024)) / elapsed if elapsed > 0 else 0
                            
                            # Update progress callback every 5% and log every 10% or 30 seconds
                            if progress_callback and progress != last_progress and progress % 5 == 0:
                                progress_callback(progress, f"Downloading: {progress}% ({downloaded_bytes/(1024*1024):.1f}/{file_size/(1024*1024):.1f} MB) - {speed_mbps:.1f} MB/s")
                                
                            if (progress % 10 == 0 and progress > 0) or (current_time - last_log_time > 30):
                                logger.info(f"Download: {progress}% ({downloaded_bytes/(1024*1024):.1f}/{file_size/(1024*1024):.1f} MB) - Speed: {speed_mbps:.1f} MB/s")
                                last_log_time = current_time
                                last_progress = progress
                                
            except Exception as download_error:
                logger.error(f"Error during optimized download: {download_error}")
                # Fallback to original method
                request = service.files().get_media(fileId=project_info['database_id'])
                with open(temp_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request, chunksize=4*1024*1024)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            logger.info(f"Download progress: {progress}% (fallback method)")
                            
            elapsed_total = time.time() - start_time
            logger.info(f"Download completed in {elapsed_total:.1f} seconds")
            
            # OPTIMIZATION: No cache file needed - work directly with downloaded file!
            # Save cache metadata for version checking compatibility (but no physical cache file)
            self._save_cache_metadata(project_name, project_info)
            
            # Track temp file for cleanup (only if not already tracked)
            if temp_path not in self.temp_files:
                self.temp_files.append(temp_path)
            
            if progress_callback:
                progress_callback(100, "Download completed, loading database...")
            
            logger.info(f"Downloaded database to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading database: {e}")
            return None
            
    def save_database(self, project_name: str, project_info: Dict, 
                     temp_db_path: str, user_name: str, changes_desc: str, 
                     change_tracker=None, progress_callback=None) -> bool:
        """
        Save database to cloud with backup and change tracking.
        
        Args:
            project_name: Name of the project
            project_info: Project information dictionary
            temp_db_path: Path to the temporary database to upload
            user_name: Name of the user making changes
            changes_desc: Description of changes
            change_tracker: Optional ChangeTracker instance for detailed change logging
            progress_callback: Optional callback for progress updates (progress_percent, message)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self.drive_service.get_service()
            if not service:
                return False
                
            # 1. Create backup of current database
            if progress_callback:
                progress_callback(10, "Creating backup...")
            if not self._create_backup(service, project_info, user_name):
                logger.warning("Failed to create backup, continuing anyway")
                
            # 2. Upload new database (this is the main time-consuming operation)
            if progress_callback:
                progress_callback(20, "Starting database upload...")
            if not self._upload_database(service, project_info, temp_db_path, progress_callback):
                logger.error("Failed to upload database")
                return False
                
            # 2.5. Upload associated XLE files
            if progress_callback:
                progress_callback(70, "Uploading associated XLE files...")
            self._upload_project_xle_files(project_name, progress_callback)
                
            # 3. Update change log
            if progress_callback:
                progress_callback(90, "Updating change log...")
            self._update_change_log(service, project_info, user_name, changes_desc)
            
            # 4. Save detailed change tracking if available
            if progress_callback:
                progress_callback(95, "Saving change details...")
            if change_tracker and change_tracker.changes:
                self._save_detailed_changes(service, project_info, change_tracker)
            
            # 5. Clean old backups
            if progress_callback:
                progress_callback(98, "Cleaning up old backups...")
            self._cleanup_backups(service, project_info)
            
            # 6. Release lock
            self._release_lock(service, project_info)
            
            # 7. Get updated project info after upload to get current modified time
            updated_project_info = self._get_updated_project_info(service, project_info)
            
            # 8. Preserve uploaded database as working copy
            self._preserve_working_database(temp_db_path, project_name, updated_project_info or project_info)
            
            if progress_callback:
                progress_callback(100, "Save completed successfully!")
            logger.info(f"Successfully saved database for project: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            return False
            
    def _create_backup(self, service, project_info: Dict, user_name: str) -> bool:
        """Create a backup of the current database"""
        try:
            # Find or create backup folder
            backup_folder_id = self._get_or_create_backup_folder(service, project_info['db_folder_id'])
            if not backup_folder_id:
                return False
                
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            safe_username = user_name.replace(' ', '_').replace('@', '_')
            backup_name = f"{project_info['database_name'].replace('.db', '')}_{timestamp}_{safe_username}.db"
            
            # Copy current database to backup folder
            body = {
                'name': backup_name,
                'parents': [backup_folder_id]
            }
            
            service.files().copy(
                fileId=project_info['database_id'],
                body=body
            ).execute()
            
            logger.info(f"Created backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
            
    def _get_or_create_backup_folder(self, service, db_folder_id: str) -> Optional[str]:
        """Get or create the backup folder"""
        try:
            # Check if backup folder exists
            query = f"'{db_folder_id}' in parents and name='backup' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = service.files().list(q=query, fields="files(id)").execute()
            files = response.get('files', [])
            
            if files:
                return files[0]['id']
                
            # Create backup folder
            folder_metadata = {
                'name': 'backup',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [db_folder_id]
            }
            
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error creating backup folder: {e}")
            return None
            
    def _get_or_create_proposals_folder(self, service, project_id: str) -> Optional[str]:
        """Get or create the proposed_changes folder for a project"""
        try:
            # Check if proposed_changes folder exists
            query = f"'{project_id}' in parents and name='proposed_changes' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = service.files().list(q=query, fields="files(id)").execute()
            files = response.get('files', [])
            
            if files:
                return files[0]['id']
                
            # Create proposed_changes folder
            folder_metadata = {
                'name': 'proposed_changes',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [project_id]
            }
            
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created proposed_changes folder with ID: {folder.get('id')}")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error creating proposed_changes folder: {e}")
            return None
            
    def _upload_database(self, service, project_info: Dict, temp_db_path: str, progress_callback=None) -> bool:
        """Upload the database file"""
        try:
            import os
            file_size = os.path.getsize(temp_db_path)
            logger.info(f"Starting database upload: {file_size} bytes")
            
            media = MediaFileUpload(
                temp_db_path,
                mimetype='application/x-sqlite3',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks for better progress
            )
            
            # Update existing file with timeout
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(300)  # 5 minute timeout
            
            try:
                request = service.files().update(
                    fileId=project_info['database_id'],
                    media_body=media
                )
                
                response = None
                retries = 0
                max_retries = 3
                
                while response is None and retries < max_retries:
                    try:
                        status, response = request.next_chunk()
                        if status:
                            # Map upload progress (0-100%) to overall save progress (20-85%)
                            upload_progress = int(status.progress() * 100)
                            overall_progress = 20 + int(upload_progress * 0.65)  # 65% of total for upload
                            logger.info(f"Upload progress: {upload_progress}%")
                            
                            # Call progress callback with real upload progress
                            if progress_callback:
                                progress_callback(overall_progress, f"Uploading database... {upload_progress}%")
                    except Exception as chunk_error:
                        retries += 1
                        logger.warning(f"Upload chunk error (attempt {retries}): {chunk_error}")
                        if retries >= max_retries:
                            raise chunk_error
                
            finally:
                socket.setdefaulttimeout(original_timeout)
            
            logger.info("Database uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database: {e}")
            import traceback
            logger.error(f"Upload error details: {traceback.format_exc()}")
            return False
            
    def _update_change_log(self, service, project_info: Dict, user_name: str, changes_desc: str):
        """Update the change log file"""
        try:
            # Find or create changes.json
            query = f"'{project_info['db_folder_id']}' in parents and name='changes.json' and trashed=false"
            response = service.files().list(q=query, fields="files(id)").execute()
            files = response.get('files', [])
            
            # Load existing changes or create new
            changes_data = {'project': project_info['name'], 'changes': []}
            
            if files:
                # Download existing file
                request = service.files().get_media(fileId=files[0]['id'])
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                    
                file_content.seek(0)
                changes_data = json.loads(file_content.read().decode('utf-8'))
                
            # Add new change entry
            change_entry = {
                'timestamp': datetime.now().isoformat(),
                'user': user_name,
                'description': changes_desc,
                'app_version': '2.1.0'  # You might want to get this dynamically
            }
            
            changes_data['changes'].insert(0, change_entry)
            
            # Keep only last 50 changes
            changes_data['changes'] = changes_data['changes'][:50]
            
            # Upload updated file
            json_content = io.BytesIO(json.dumps(changes_data, indent=2).encode('utf-8'))
            media = MediaIoBaseUpload(
                json_content,
                mimetype='application/json',
                resumable=True
            )
            
            if files:
                # Update existing
                service.files().update(
                    fileId=files[0]['id'],
                    media_body=media
                ).execute()
            else:
                # Create new
                file_metadata = {
                    'name': 'changes.json',
                    'parents': [project_info['db_folder_id']]
                }
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
        except Exception as e:
            logger.error(f"Error updating change log: {e}")
            
    def _cleanup_backups(self, service, project_info: Dict):
        """Clean up old backups, keeping only the 2 most recent"""
        try:
            # Find backup folder
            backup_folder_id = self._get_or_create_backup_folder(service, project_info['db_folder_id'])
            if not backup_folder_id:
                return
                
            # List all backups
            query = f"'{backup_folder_id}' in parents and name contains '.db' and trashed=false"
            response = service.files().list(
                q=query,
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc"
            ).execute()
            
            backups = response.get('files', [])
            
            # Keep only 2 most recent
            if len(backups) > 2:
                for backup in backups[2:]:
                    service.files().delete(fileId=backup['id']).execute()
                    logger.info(f"Deleted old backup: {backup['name']}")
                    
        except Exception as e:
            logger.error(f"Error cleaning backups: {e}")
            
    def check_lock(self, project_info: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if database is locked by another user.
        
        Returns:
            Tuple of (is_locked, user_name, lock_time)
        """
        try:
            if 'locked_by' not in project_info:
                return False, None, None
                
            # Check if lock is expired (5 minutes)
            lock_time_str = project_info.get('lock_time', '')
            if lock_time_str:
                lock_time = datetime.fromisoformat(lock_time_str)
                if (datetime.now() - lock_time).total_seconds() > 300:
                    # Lock expired
                    return False, None, None
                    
            return True, project_info['locked_by'], lock_time_str
            
        except Exception as e:
            logger.error(f"Error checking lock: {e}")
            return False, None, None
            
    def acquire_lock(self, project_info: Dict, user_name: str) -> bool:
        """Try to acquire lock on database"""
        try:
            service = self.drive_service.get_service()
            if not service:
                return False
                
            # Set custom properties for lock
            properties = {
                'locked_by': user_name,
                'lock_time': datetime.now().isoformat()
            }
            
            service.files().update(
                fileId=project_info['database_id'],
                body={'properties': properties}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            return False
            
    def _release_lock(self, service, project_info: Dict):
        """Release lock on database"""
        try:
            # Clear lock properties
            service.files().update(
                fileId=project_info['database_id'],
                body={'properties': {}}
            ).execute()
            
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
            
    def _save_detailed_changes(self, service, project_info: Dict, change_tracker):
        """Save detailed change tracking data to cloud"""
        try:
            # Get change data
            changes_data = change_tracker.get_changes_for_save()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"changes_{timestamp}.json"
            
            # Create or find changes folder
            changes_folder_id = self._get_or_create_changes_folder(service, project_info['db_folder_id'])
            if not changes_folder_id:
                logger.warning("Could not create changes folder, skipping detailed change tracking")
                return
            
            # Upload changes file
            json_content = io.BytesIO(json.dumps(changes_data, indent=2).encode('utf-8'))
            media = MediaIoBaseUpload(
                json_content,
                mimetype='application/json',
                resumable=True
            )
            
            file_metadata = {
                'name': filename,
                'parents': [changes_folder_id]
            }
            
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.info(f"Detailed changes saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving detailed changes: {e}")
    
    def _get_or_create_changes_folder(self, service, db_folder_id: str) -> Optional[str]:
        """Get or create the changes folder for detailed change tracking"""
        try:
            # Check if changes folder exists
            query = f"'{db_folder_id}' in parents and name='changes' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = service.files().list(q=query, fields="files(id)").execute()
            files = response.get('files', [])
            
            if files:
                return files[0]['id']
                
            # Create changes folder
            folder_metadata = {
                'name': 'changes',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [db_folder_id]
            }
            
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error creating changes folder: {e}")
            return None
    
    def _get_updated_project_info(self, service, project_info: Dict) -> Optional[Dict]:
        """Get updated project info after upload to get current modified time"""
        try:
            # Get fresh file metadata
            file_metadata = service.files().get(
                fileId=project_info['database_id'], 
                fields="modifiedTime"
            ).execute()
            
            # Update project info with new modified time
            updated_info = project_info.copy()
            updated_info['modified_time'] = file_metadata.get('modifiedTime', '')
            logger.debug(f"Updated project info with new modified time: {updated_info['modified_time']}")
            return updated_info
            
        except Exception as e:
            logger.error(f"Error getting updated project info: {e}")
            return None
            
    def _preserve_working_database(self, uploaded_db_path: str, project_name: str, project_info: Dict):
        """
        Preserve the uploaded database as the working copy and remove it from temp cleanup.
        This ensures the uploaded database remains available after app closure and tracks version info.
        """
        try:
            # Remove the uploaded database from temp files cleanup list
            if uploaded_db_path in self.temp_files:
                self.temp_files.remove(uploaded_db_path)
                logger.info(f"Preserved working database: {uploaded_db_path}")
                
            # OPTIMIZATION: No cache file needed - we work directly with uploaded file
            # The working database IS the cache now (single file system)
            logger.debug(f"Working with single database file: {uploaded_db_path}")
                
            # CRITICAL: Save working database metadata with current cloud version
            # This ensures we can detect when the cloud version is newer
            self._save_working_metadata(project_name, project_info)
            logger.info(f"Saved working database metadata for version tracking")
                
        except Exception as e:
            logger.error(f"Error preserving working database: {e}")
    
    def cleanup_temp_files(self):
        """Clean up any temporary files created"""
        files_to_remove = []
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    # Check if file is in use by checking if we can open it
                    try:
                        with open(temp_file, 'r+b'):
                            pass  # File is not locked
                        os.remove(temp_file)
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                        files_to_remove.append(temp_file)
                    except (PermissionError, OSError) as lock_error:
                        # File is locked/in use - skip cleanup for now
                        logger.warning(f"Temp file {temp_file} is in use, skipping cleanup: {lock_error}")
                else:
                    # File doesn't exist anymore, remove from list
                    files_to_remove.append(temp_file)
            except Exception as e:
                logger.error(f"Error cleaning up temp file {temp_file}: {e}")
                
        # Only remove successfully cleaned files from the list
        for removed_file in files_to_remove:
            if removed_file in self.temp_files:
                self.temp_files.remove(removed_file)
    
    # Draft Management Methods
    def has_draft(self, project_name: str) -> bool:
        """Check if a draft exists for the project."""
        return self.draft_manager.has_draft(project_name)
    
    def get_draft_info(self, project_name: str) -> Optional[Dict]:
        """Get draft information."""
        return self.draft_manager.get_draft_info(project_name)
    
    def save_as_draft(self, project_name: str, temp_db_path: str, 
                      original_download_time: str, changes_description: str = None) -> bool:
        """Save current state as a local draft."""
        return self.draft_manager.save_draft(
            project_name, temp_db_path, original_download_time, changes_description
        )
    
    def load_draft(self, project_name: str) -> Optional[str]:
        """Load a draft database."""
        return self.draft_manager.load_draft(project_name, self.cache_dir)
    
    def clear_draft(self, project_name: str) -> bool:
        """Clear a draft after successful upload."""
        return self.draft_manager.clear_draft(project_name)
    
    def check_draft_version_changes(self, project_name: str) -> Dict:
        """Check if cloud version changed since draft was created."""
        try:
            # Get current cloud version
            projects = self.list_projects()
            project_info = next((p for p in projects if p['name'] == project_name), None)
            
            if not project_info:
                return {'changed': False, 'info': None}
            
            current_cloud_time = project_info.get('modified_time')
            return self.draft_manager.check_version_changes(project_name, current_cloud_time)
            
        except Exception as e:
            logger.error(f"Error checking draft version changes: {e}")
            return {'changed': False, 'info': None}
    
    def check_for_outdated_working_databases(self) -> List[Dict]:
        """
        Check all working databases for version conflicts.
        Returns list of outdated databases with details.
        """
        outdated_databases = []
        
        try:
            # Get all available projects
            projects = self.list_projects()
            
            for project in projects:
                project_name = project['name']
                working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
                
                # Check if working database exists
                if os.path.exists(working_db_path):
                    cloud_modified_time = project.get('modified_time', '')
                    
                    # Check if working database is outdated
                    if not self._is_working_database_valid(project_name, cloud_modified_time):
                        outdated_info = {
                            'project_name': project_name,
                            'working_db_path': working_db_path,
                            'cloud_modified_time': cloud_modified_time,
                            'database_name': project.get('database_name', 'Unknown')
                        }
                        
                        # Get local modified time for comparison
                        try:
                            working_metadata_path = self._get_working_metadata_path(project_name)
                            if os.path.exists(working_metadata_path):
                                with open(working_metadata_path, 'r') as f:
                                    metadata = json.load(f)
                                    outdated_info['local_modified_time'] = metadata.get('modifiedTime', 'Unknown')
                        except Exception as e:
                            logger.warning(f"Could not read local metadata for {project_name}: {e}")
                            outdated_info['local_modified_time'] = 'Unknown'
                        
                        outdated_databases.append(outdated_info)
                        logger.warning(f"Found outdated working database: {project_name}")
            
        except Exception as e:
            logger.error(f"Error checking for outdated working databases: {e}")
        
        return outdated_databases
    
    # Version Manager Methods
    def check_version_status(self, project_name: str, cloud_version_time: str) -> Dict:
        """
        Check version status between local databases (working + cache) and cloud.
        Now includes working database checking with priority over cache.
        """
        # First check if we have a working database and if it's valid
        working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
        
        if os.path.exists(working_db_path):
            # Check working database version first (highest priority)
            if self._is_working_database_valid(project_name, cloud_version_time):
                # Working database is up to date - recommend using it
                try:
                    working_metadata_path = self._get_working_metadata_path(project_name)
                    file_size = os.path.getsize(working_db_path) / (1024 * 1024)
                    
                    working_metadata = {}
                    if os.path.exists(working_metadata_path):
                        with open(working_metadata_path, 'r') as f:
                            working_metadata = json.load(f)
                    
                    return {
                        'status': 'current',
                        'local_time': working_metadata.get('modifiedTime', cloud_version_time),
                        'cloud_time': cloud_version_time,
                        'time_diff': 0,
                        'needs_download': False,
                        'message': '✅ Working with latest version (preserved working copy)',
                        'local_db_exists': True,
                        'file_size_mb': round(file_size, 2),
                        'db_type': 'working',
                        'working_db_path': working_db_path
                    }
                except Exception as e:
                    logger.error(f"Error checking working database metadata: {e}")
            else:
                # Working database is outdated - needs attention
                try:
                    working_metadata_path = self._get_working_metadata_path(project_name)
                    file_size = os.path.getsize(working_db_path) / (1024 * 1024)
                    
                    local_time = cloud_version_time  # Default
                    if os.path.exists(working_metadata_path):
                        with open(working_metadata_path, 'r') as f:
                            working_metadata = json.load(f)
                            local_time = working_metadata.get('modifiedTime', cloud_version_time)
                    
                    # Calculate time difference
                    try:
                        local_dt = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
                        cloud_dt = datetime.fromisoformat(cloud_version_time.replace('Z', '+00:00'))
                        diff_minutes = int((cloud_dt - local_dt).total_seconds() / 60)
                    except:
                        diff_minutes = 0
                    
                    return {
                        'status': 'outdated',
                        'local_time': local_time,
                        'cloud_time': cloud_version_time,
                        'time_diff': max(diff_minutes, 1),  # At least 1 minute difference
                        'needs_download': True,
                        'message': '⚠️ Your working copy is outdated - cloud version is newer',
                        'local_db_exists': True,
                        'file_size_mb': round(file_size, 2),
                        'db_type': 'working_outdated',
                        'working_db_path': working_db_path
                    }
                except Exception as e:
                    logger.error(f"Error checking outdated working database: {e}")
        
        # No working database or error checking it - fall back to original cache checking
        return self.version_manager.compare_versions(project_name, cloud_version_time)
    
    def update_local_version_tracking(self, project_name: str, cloud_version_time: str, 
                                    local_db_path: str, operation: str = "download"):
        """Update version tracking after download/upload"""
        self.version_manager.update_local_version(project_name, cloud_version_time, 
                                                local_db_path, operation)
    
    def get_cached_database_path(self, project_name: str) -> Optional[str]:
        """Get path to cached database if it exists and is valid"""
        version_info = self.version_manager.get_local_version_info(project_name)
        if version_info:
            local_path = version_info.get('local_db_path')
            if local_path and os.path.exists(local_path):
                return local_path
        return None
    
    # Proposal Management Methods
    def upload_proposal(self, project_name: str, proposal_db_path: str, user_name: str, 
                       description: str, progress_callback=None) -> bool:
        """
        Upload a reduced database proposal to Google Drive
        
        Args:
            project_name: Name of the project
            proposal_db_path: Path to the reduced proposal database
            user_name: Name of the user making the proposal
            description: Description of the proposed changes
            progress_callback: Optional callback for progress updates
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            if progress_callback:
                progress_callback(10, "Initializing proposal upload...")
            
            service = self.drive_service.get_service()
            if not service:
                logger.error("No Google Drive service available")
                return False
            
            # Find project
            projects = self.list_projects()
            project_info = next((p for p in projects if p['name'] == project_name), None)
            if not project_info:
                logger.error(f"Project '{project_name}' not found")
                return False
            
            if progress_callback:
                progress_callback(30, "Creating proposals folder...")
            
            # Get or create proposals folder
            proposals_folder_id = self._get_or_create_proposals_folder(service, project_info['project_id'])
            if not proposals_folder_id:
                logger.error("Failed to create proposals folder")
                return False
            
            if progress_callback:
                progress_callback(50, "Uploading proposal database...")
            
            # Generate proposal filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            safe_username = user_name.replace(' ', '_').replace('@', '_')
            proposal_name = f"{project_name}_{timestamp}_{safe_username}.db"
            
            # Upload proposal database
            media = MediaFileUpload(
                proposal_db_path,
                mimetype='application/x-sqlite3',
                resumable=True
            )
            
            file_metadata = {
                'name': proposal_name,
                'parents': [proposals_folder_id],
                'description': description
            }
            
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            if progress_callback:
                progress_callback(80, "Creating proposal metadata...")
            
            # Create metadata file
            metadata = {
                'proposal_id': uploaded_file.get('id'),
                'project_name': project_name,
                'author': user_name,
                'timestamp': datetime.now().isoformat(),
                'description': description,
                'filename': proposal_name
            }
            
            # Upload metadata
            metadata_json = json.dumps(metadata, indent=2)
            metadata_media = MediaIoBaseUpload(
                io.BytesIO(metadata_json.encode()),
                mimetype='application/json'
            )
            
            metadata_file = {
                'name': f"{proposal_name.replace('.db', '_metadata.json')}",
                'parents': [proposals_folder_id]
            }
            
            service.files().create(
                body=metadata_file,
                media_body=metadata_media
            ).execute()
            
            if progress_callback:
                progress_callback(100, "Proposal upload completed!")
            
            logger.info(f"Successfully uploaded proposal: {proposal_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading proposal: {e}")
            return False
    
    def list_proposals(self, project_name: str) -> List[Dict]:
        """
        List all available proposals for a project
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of proposal dictionaries with metadata
        """
        proposals = []
        
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.error("No Google Drive service available")
                return proposals
            
            # Find project
            projects = self.list_projects()
            project_info = next((p for p in projects if p['name'] == project_name), None)
            if not project_info:
                logger.error(f"Project '{project_name}' not found")
                return proposals
            
            # Check if proposals folder exists
            proposals_folder_id = self._get_or_create_proposals_folder(service, project_info['project_id'])
            if not proposals_folder_id:
                return proposals
            
            # Query for proposal database files
            query = f"'{proposals_folder_id}' in parents and name contains '.db' and trashed=false"
            response = service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, description)",
                orderBy="modifiedTime desc"
            ).execute()
            
            for file in response.get('files', []):
                # Try to find corresponding metadata file
                metadata_name = file['name'].replace('.db', '_metadata.json')
                metadata_query = f"'{proposals_folder_id}' in parents and name='{metadata_name}' and trashed=false"
                metadata_response = service.files().list(q=metadata_query, fields="files(id)").execute()
                
                proposal_data = {
                    'id': file['id'],
                    'filename': file['name'],
                    'modified_time': file.get('modifiedTime', ''),
                    'description': file.get('description', ''),
                    'metadata_id': None
                }
                
                # Get metadata if available
                metadata_files = metadata_response.get('files', [])
                if metadata_files:
                    proposal_data['metadata_id'] = metadata_files[0]['id']
                    # Download and parse metadata
                    try:
                        metadata_content = service.files().get_media(fileId=metadata_files[0]['id']).execute()
                        metadata = json.loads(metadata_content.decode())
                        proposal_data.update({
                            'author': metadata.get('author', 'Unknown'),
                            'timestamp': metadata.get('timestamp', ''),
                            'description': metadata.get('description', proposal_data['description'])
                        })
                    except Exception as e:
                        logger.warning(f"Could not parse metadata for {file['name']}: {e}")
                
                proposals.append(proposal_data)
            
        except Exception as e:
            logger.error(f"Error listing proposals: {e}")
        
        return proposals
    
    def download_proposal(self, proposal_id: str, project_name: str) -> Optional[str]:
        """
        Download a proposal database to temporary location
        
        Args:
            proposal_id: Google Drive file ID of the proposal
            project_name: Name of the project
            
        Returns:
            Optional[str]: Path to downloaded proposal database, or None if failed
        """
        try:
            service = self.drive_service.get_service()
            if not service:
                logger.error("No Google Drive service available")
                return None
            
            # Create temporary file path
            temp_filename = f"proposal_{proposal_id}_{int(time.time())}.db"
            temp_path = os.path.join(self.cache_dir, temp_filename)
            
            # Download the proposal file
            request = service.files().get_media(fileId=proposal_id)
            with open(temp_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            logger.info(f"Downloaded proposal to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading proposal: {e}")
            return None
    
    def set_database_manager(self, database_manager):
        """Set the database manager for XLE file operations."""
        if database_manager and not self.xle_manager:
            self.xle_manager = XLEFileManager(
                database_manager, self.drive_service, self.settings_handler
            )
            logger.info("XLE file manager initialized for cloud database operations")
        elif self.xle_manager:
            logger.info("XLE file manager already initialized")
        else:
            logger.warning("Cannot initialize XLE file manager - no database manager provided")
    
    def rebuild_xle_tracking_after_database_load(self, project_name: str = None):
        """
        Rebuild XLE file tracking after a database is loaded.
        Call this after database is opened/loaded to restore XLE tracking.
        """
        logger.info(f"XLE_REBUILD: rebuild_xle_tracking_after_database_load called for project: '{project_name}'")
        
        if not self.xle_manager:
            logger.warning("XLE_REBUILD: Cannot rebuild XLE tracking - XLE manager not initialized")
            return
            
        try:
            rebuilt_count = self.xle_manager.rebuild_tracking_from_database(project_name)
            if rebuilt_count > 0:
                logger.info(f"XLE_REBUILD: Successfully rebuilt tracking for {rebuilt_count} XLE files from database")
            else:
                logger.info(f"XLE_REBUILD: No XLE files needed tracking rebuild for project '{project_name}'")
        except Exception as e:
            logger.error(f"XLE_REBUILD: Error rebuilding XLE tracking from database: {e}")
    
    def _upload_project_xle_files(self, project_name: str, progress_callback=None):
        """Upload pending XLE files for a project."""
        try:
            logger.info(f"XLE_UPLOAD: Starting XLE upload for project: '{project_name}'")
            
            if not self.xle_manager:
                logger.warning("XLE_UPLOAD: XLE file manager not initialized - skipping XLE upload")
                return
            
            # Check what pending files we have before upload
            pending_files = self.xle_manager.get_pending_uploads(project_name)
            logger.info(f"XLE_UPLOAD: Found {len(pending_files)} pending XLE files for project '{project_name}'")
            
            if pending_files:
                for i, file_record in enumerate(pending_files):
                    logger.info(f"XLE_UPLOAD: Pending file {i+1}: {file_record.get('file_name', 'unknown')} "
                              f"(type: {file_record.get('file_type', 'unknown')}, "
                              f"serial: {file_record.get('serial_number', 'unknown')}, "
                              f"status: {file_record.get('upload_status', 'unknown')})")
            
            # Create progress wrapper for XLE uploads
            def xle_progress_callback(progress, message):
                if progress_callback:
                    # Map XLE progress to 70-89% range (20% allocation for XLE upload)
                    adjusted_progress = 70 + int(progress * 0.19)
                    progress_callback(adjusted_progress, f"XLE: {message}")
            
            # Upload XLE files for this project
            results = self.xle_manager.upload_project_xle_files(
                project_name, xle_progress_callback
            )
            
            if results['total'] > 0:
                logger.info(f"XLE_UPLOAD: Upload results for {project_name}: {results['success']} success, {results['failed']} failed")
            else:
                logger.info(f"XLE_UPLOAD: No pending XLE files to upload for project: {project_name}")
                
        except Exception as e:
            logger.error(f"XLE_UPLOAD: Error uploading XLE files for project {project_name}: {e}")
            # Don't fail the entire database upload if XLE upload fails
            if progress_callback:
                progress_callback(89, "XLE upload encountered issues, continuing...")
    
    def create_session_backup(self, project_name: str, database_path: str, backup_type: str):
        """
        Create a session backup of the database.
        
        Args:
            project_name: Name of the project
            database_path: Path to the database to backup
            backup_type: 'original' (just downloaded) or 'last_uploaded' (after successful upload)
        """
        try:
            import uuid
            backup_filename = f"{project_name}_{backup_type}_{uuid.uuid4().hex[:8]}.db"
            backup_path = os.path.join(self.cache_dir, "session_backups", backup_filename)
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Create backup copy
            shutil.copy2(database_path, backup_path)
            
            # Track in session backups
            if project_name not in self.session_backups:
                self.session_backups[project_name] = {}
            
            self.session_backups[project_name][backup_type] = backup_path
            
            logger.info(f"Created {backup_type} session backup for {project_name}: {backup_path}")
            
        except Exception as e:
            logger.error(f"Error creating session backup: {e}")
    
    def get_session_backup_path(self, project_name: str, backup_type: str) -> Optional[str]:
        """Get the path to a session backup."""
        try:
            backup_path = self.session_backups.get(project_name, {}).get(backup_type)
            if backup_path and os.path.exists(backup_path):
                return backup_path
            return None
        except Exception as e:
            logger.error(f"Error getting session backup path: {e}")
            return None
    
    def cleanup_session_backups(self, project_name: str = None):
        """Clean up session backups for a project or all projects."""
        try:
            if project_name:
                # Clean up specific project backups
                if project_name in self.session_backups:
                    for backup_type, backup_path in self.session_backups[project_name].items():
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                            logger.info(f"Removed session backup: {backup_path}")
                    del self.session_backups[project_name]
            else:
                # Clean up all session backups
                for proj_name, backups in self.session_backups.items():
                    for backup_type, backup_path in backups.items():
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                            logger.info(f"Removed session backup: {backup_path}")
                self.session_backups.clear()
                
                # Also clean up session backups directory
                backups_dir = os.path.join(self.cache_dir, "session_backups")
                if os.path.exists(backups_dir):
                    shutil.rmtree(backups_dir)
                    logger.info("Cleaned up session backups directory")
                    
        except Exception as e:
            logger.error(f"Error cleaning up session backups: {e}")
    
    def has_session_changes_since_upload(self, project_name: str, current_db_path: str) -> bool:
        """
        Check if there are changes since the last upload by comparing with the last_uploaded backup.
        """
        try:
            last_uploaded_path = self.get_session_backup_path(project_name, 'last_uploaded')
            if not last_uploaded_path:
                # No upload has happened this session, check against original
                return self.has_session_changes_since_download(project_name, current_db_path)
            
            # Compare file sizes and modification times as a quick check
            current_size = os.path.getsize(current_db_path)
            last_uploaded_size = os.path.getsize(last_uploaded_path)
            
            if current_size != last_uploaded_size:
                return True
            
            # If sizes are same, compare modification times
            current_mtime = os.path.getmtime(current_db_path)
            last_uploaded_mtime = os.path.getmtime(last_uploaded_path)
            
            return current_mtime > last_uploaded_mtime
            
        except Exception as e:
            logger.error(f"Error checking session changes since upload: {e}")
            return True  # Assume there are changes if we can't determine
    
    def has_session_changes_since_download(self, project_name: str, current_db_path: str) -> bool:
        """
        Check if there are changes since the original download by comparing with the original backup.
        """
        try:
            original_path = self.get_session_backup_path(project_name, 'original')
            if not original_path:
                return True  # No original backup means we can't determine, assume changes exist
            
            # Compare file sizes as a quick check
            current_size = os.path.getsize(current_db_path)
            original_size = os.path.getsize(original_path)
            
            return current_size != original_size
            
        except Exception as e:
            logger.error(f"Error checking session changes since download: {e}")
            return True  # Assume there are changes if we can't determine