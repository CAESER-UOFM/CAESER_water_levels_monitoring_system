import os
import json
import logging
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
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
        
    def get_projects_folder_id(self):
        """Get the projects folder ID from settings"""
        if not self.projects_folder_id:
            self.projects_folder_id = self.settings_handler.get_setting(
                "google_drive_projects_folder_id", ""
            )
        return self.projects_folder_id
    
    def _get_cache_directory(self) -> str:
        """Get or create the cache directory for storing downloaded databases"""
        cache_dir = os.path.join(tempfile.gettempdir(), "wlm_cloud_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    def _get_cached_db_path(self, project_name: str) -> str:
        """Get the path for cached database file"""
        return os.path.join(self.cache_dir, f"{project_name}.db")
    
    def _get_cached_metadata_path(self, project_name: str) -> str:
        """Get the path for cached metadata file"""
        return os.path.join(self.cache_dir, f"{project_name}_metadata.json")
    
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
                logger.error("Projects folder ID not configured")
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
            
    def download_database(self, project_name: str, project_info: Dict, progress_callback=None) -> Optional[str]:
        """
        Download a database to a temporary location, using cache if available.
        
        Args:
            project_name: Name of the project
            project_info: Project information dictionary
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Path to the temporary database file
        """
        try:
            # Check if we have a valid cached version
            cloud_modified_time = project_info.get('modified_time', '')
            if self._is_cache_valid(project_name, cloud_modified_time):
                logger.info(f"Using cached database for {project_name} (up to date)")
                if progress_callback:
                    progress_callback(100, "Using cached database (up to date)")
                
                # Copy cached file to temp location
                cached_path = self._get_cached_db_path(project_name)
                temp_dir = tempfile.gettempdir()
                temp_filename = f"wlm_{project_name}_{uuid.uuid4().hex[:8]}.db"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                shutil.copy2(cached_path, temp_path)
                self.temp_files.append(temp_path)
                logger.info(f"Copied cached database to: {temp_path}")
                return temp_path
            
            # Need to download from cloud
            service = self.drive_service.get_service()
            if not service:
                return None
            
            logger.info(f"Downloading {project_name} from cloud (cache outdated or missing)")
            if progress_callback:
                progress_callback(0, f"Downloading {project_info['database_name']} from cloud...")
                
            # Use cached path as destination
            cached_path = self._get_cached_db_path(project_name)
            
            # Create temp file with unique name for final result
            temp_dir = tempfile.gettempdir()
            temp_filename = f"wlm_{project_name}_{uuid.uuid4().hex[:8]}.db"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Try alternative download method for better performance
            start_time = time.time()
            
            try:
                # Alternative 1: Try to get file metadata first
                file_metadata = service.files().get(fileId=project_info['database_id'], fields="size").execute()
                file_size = int(file_metadata.get('size', 0))
                logger.info(f"Database file size: {file_size / (1024*1024):.1f} MB")
                
                # Download to cached location first
                request = service.files().get_media(fileId=project_info['database_id'])
                with open(cached_path, 'wb') as f:
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
            
            # Save cache metadata
            self._save_cache_metadata(project_name, project_info)
            
            # Copy cached file to temp location
            shutil.copy2(cached_path, temp_path)
            
            # Track temp file for cleanup
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
                     change_tracker=None) -> bool:
        """
        Save database to cloud with backup and change tracking.
        
        Args:
            project_name: Name of the project
            project_info: Project information dictionary
            temp_db_path: Path to the temporary database to upload
            user_name: Name of the user making changes
            changes_desc: Description of changes
            change_tracker: Optional ChangeTracker instance for detailed change logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self.drive_service.get_service()
            if not service:
                return False
                
            # 1. Create backup of current database
            if not self._create_backup(service, project_info, user_name):
                logger.warning("Failed to create backup, continuing anyway")
                
            # 2. Upload new database
            if not self._upload_database(service, project_info, temp_db_path):
                logger.error("Failed to upload database")
                return False
                
            # 3. Update change log
            self._update_change_log(service, project_info, user_name, changes_desc)
            
            # 4. Save detailed change tracking if available
            if change_tracker and change_tracker.changes:
                self._save_detailed_changes(service, project_info, change_tracker)
            
            # 5. Clean old backups
            self._cleanup_backups(service, project_info)
            
            # 6. Release lock
            self._release_lock(service, project_info)
            
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
            
    def _upload_database(self, service, project_info: Dict, temp_db_path: str) -> bool:
        """Upload the database file"""
        try:
            media = MediaFileUpload(
                temp_db_path,
                mimetype='application/x-sqlite3',
                resumable=True
            )
            
            # Update existing file
            service.files().update(
                fileId=project_info['database_id'],
                media_body=media
            ).execute()
            
            logger.info("Database uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database: {e}")
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
            media = MediaFileUpload(
                io.BytesIO(json.dumps(changes_data, indent=2).encode('utf-8')),
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
            media = MediaFileUpload(
                io.BytesIO(json.dumps(changes_data, indent=2).encode('utf-8')),
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
            
    def cleanup_temp_files(self):
        """Clean up any temporary files created"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.error(f"Error cleaning up temp file {temp_file}: {e}")
                
        self.temp_files.clear()