import os
import json
import logging
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from .draft_manager import DraftManager
from .version_manager import VersionManager
from .xle_file_manager import XLEFileManager
import uuid

logger = logging.getLogger(__name__)

class SharedDriveDbHandler:
    """Handles shared drive database operations for project-based databases"""
    
    def __init__(self, settings_handler):
        """
        Initialize the shared drive database handler.
        
        Args:
            settings_handler: SettingsHandler instance
        """
        self.settings_handler = settings_handler
        self.shared_drive_root = None
        self.projects_folder_path = None
        self.temp_files = []  # Track temp files for cleanup
        self.cache_dir = self._get_cache_directory()
        self.draft_manager = DraftManager(self.cache_dir)  # Initialize draft manager
        self.version_manager = VersionManager(self.cache_dir)  # Initialize version manager
        self.xle_manager = None  # Initialize when database manager available
        
        # Session state tracking for enhanced draft management
        self.session_backups = {}  # {project_name: {"original": path, "last_uploaded": path}}
        
    def get_shared_drive_root(self):
        """Get the shared drive root path from settings"""
        if not self.shared_drive_root:
            self.shared_drive_root = self.settings_handler.get_setting("shared_drive_root")
            if not self.shared_drive_root:
                raise ValueError("shared_drive_root not configured in settings.json. Please configure shared drive paths.")
            logger.info(f"SharedDriveDbHandler root path: '{self.shared_drive_root}'")
        return self.shared_drive_root
    
    def get_projects_folder_path(self):
        """Get the projects folder path from shared drive root"""
        if not self.projects_folder_path:
            root = self.get_shared_drive_root()
            self.projects_folder_path = os.path.join(root, "Projects")
            logger.info(f"SharedDriveDbHandler projects path: '{self.projects_folder_path}'")
        return self.projects_folder_path
    
    def _get_cache_directory(self) -> str:
        """Get or create the cache directory for storing downloaded databases"""
        # Use databases/temp folder instead of system temp
        # Use app directory instead of current working directory
        app_dir = Path(__file__).parent.parent.parent.parent
        local_db_directory = self.settings_handler.get_setting("local_db_directory", str(app_dir))
        
        # Fix double "databases" folder issue - check if local_db_directory already ends with "databases"
        if local_db_directory.endswith("databases") or local_db_directory.endswith("databases\\"):
            cache_dir = os.path.join(local_db_directory, "temp")
        else:
            cache_dir = os.path.join(local_db_directory, "databases", "temp")
        
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
    
    def _get_shared_drive_project_path(self, project_name: str) -> str:
        """Get the shared drive path for a specific project"""
        projects_path = self.get_projects_folder_path()
        return os.path.join(projects_path, project_name)
    
    def _get_shared_drive_db_path(self, project_name: str) -> str:
        """Get the shared drive database file path for a project"""
        project_path = self._get_shared_drive_project_path(project_name)
        return os.path.join(project_path, "DATABASES", f"{project_name}.db")
    
    def _get_shared_drive_db_folder_path(self, project_name: str) -> str:
        """Get the shared drive databases folder path for a project"""
        project_path = self._get_shared_drive_project_path(project_name)
        return os.path.join(project_path, "DATABASES")
    
    def _get_shared_drive_backup_folder_path(self, project_name: str) -> str:
        """Get the shared drive backup folder path for a project"""
        db_folder_path = self._get_shared_drive_db_folder_path(project_name)
        return os.path.join(db_folder_path, "backup")
    
    def _check_shared_drive_access(self) -> bool:
        """Check if shared drive is accessible"""
        try:
            root_path = self.get_shared_drive_root()
            projects_path = self.get_projects_folder_path()
            
            # Check if paths exist and are accessible
            if not os.path.exists(root_path):
                logger.error(f"Shared drive root path not accessible: {root_path}")
                return False
            
            if not os.path.exists(projects_path):
                logger.error(f"Projects folder not found: {projects_path}")
                return False
            
            # Test write permissions
            test_file = os.path.join(root_path, f"test_access_{int(time.time())}.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.debug("Shared drive write access confirmed")
                return True
            except Exception as e:
                logger.error(f"No write access to shared drive: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking shared drive access: {e}")
            return False
    
    def _is_cache_valid(self, project_name: str, shared_drive_modified_time: str) -> bool:
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
            return cached_time == shared_drive_modified_time
            
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def _is_working_database_valid(self, project_name: str, shared_drive_modified_time: str) -> bool:
        """Check if working database is still valid (up to date with shared drive)"""
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
            is_valid = working_time == shared_drive_modified_time
            
            if not is_valid:
                logger.warning(f"Working database for {project_name} is outdated. "
                             f"Local: {working_time}, Shared Drive: {shared_drive_modified_time}")
            
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
                'source': 'shared_drive'
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.debug(f"Cache metadata saved for {project_name}")
            
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
                'working_copy_created': datetime.now().isoformat(),
                'source': 'shared_drive'
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.debug(f"Working metadata saved for {project_name}")
            
        except Exception as e:
            logger.error(f"Error saving working metadata: {e}")
    
    def _get_file_modified_time(self, file_path: str) -> str:
        """Get file modification time as ISO string"""
        try:
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                return datetime.fromtimestamp(mtime).isoformat()
            return ""
        except Exception as e:
            logger.error(f"Error getting file modification time: {e}")
            return ""
    
    def list_projects(self) -> List[Dict]:
        """
        List all available projects in shared drive.
        
        Returns:
            List of project dictionaries with name, path, database info, etc.
        """
        projects = []
        
        if not self._check_shared_drive_access():
            logger.error("Cannot access shared drive")
            return projects
            
        try:
            projects_path = self.get_projects_folder_path()
            
            # List all directories in projects folder
            for item in os.listdir(projects_path):
                project_path = os.path.join(projects_path, item)
                
                # Skip if not a directory
                if not os.path.isdir(project_path):
                    continue
                    
                # Check if project has a DATABASES folder
                databases_folder = os.path.join(project_path, "DATABASES")
                if not os.path.exists(databases_folder):
                    continue
                    
                # Look for database file
                db_file_path = os.path.join(databases_folder, f"{item}.db")
                if os.path.exists(db_file_path):
                    modified_time = self._get_file_modified_time(db_file_path)
                    
                    projects.append({
                        'name': item,
                        'project_path': project_path,
                        'db_folder_path': databases_folder,
                        'database_name': f"{item}.db",
                        'database_path': db_file_path,
                        'modified_time': modified_time,
                        'locked_by': None,  # No locking for shared drive (users work on local copies)
                        'lock_time': None   # No locking for shared drive (users work on local copies)
                    })
                    
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            
        logger.info(f"Found {len(projects)} projects in shared drive")
        return projects
    
    def download_project_database(self, project_name: str, force_download: bool = False) -> Optional[str]:
        """
        Download project database from shared drive to local cache.
        
        Args:
            project_name: Name of the project
            force_download: Force download even if cache is valid
            
        Returns:
            Path to downloaded database file or None if failed
        """
        try:
            if not self._check_shared_drive_access():
                logger.error("Cannot access shared drive")
                return None
            
            # Get shared drive database path
            shared_db_path = self._get_shared_drive_db_path(project_name)
            
            if not os.path.exists(shared_db_path):
                logger.error(f"Database not found in shared drive: {shared_db_path}")
                return None
            
            # Get modification time
            modified_time = self._get_file_modified_time(shared_db_path)
            
            # Check if cache is valid (unless forcing download)
            cached_db_path = self._get_cached_db_path(project_name)
            if not force_download and self._is_cache_valid(project_name, modified_time):
                logger.info(f"Using cached database for {project_name}")
                return cached_db_path
            
            # Download database
            logger.info(f"Downloading database for {project_name} from shared drive")
            shutil.copy2(shared_db_path, cached_db_path)
            
            # Save metadata
            project_info = {
                'database_name': f"{project_name}.db",
                'modified_time': modified_time
            }
            self._save_cache_metadata(project_name, project_info)
            
            logger.info(f"Database downloaded successfully for {project_name}")
            return cached_db_path
            
        except Exception as e:
            logger.error(f"Error downloading database for {project_name}: {e}")
            return None
    
    def get_working_database_path(self, project_name: str, force_download: bool = False) -> Optional[str]:
        """
        Get path to working database (wlm_PROJECT.db) for local operations.
        
        Args:
            project_name: Name of the project
            force_download: Force download from shared drive
            
        Returns:
            Path to working database file or None if failed
        """
        try:
            working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
            
            if not self._check_shared_drive_access():
                logger.error("Cannot access shared drive")
                return None
            
            # Get shared drive database info
            shared_db_path = self._get_shared_drive_db_path(project_name)
            
            if not os.path.exists(shared_db_path):
                logger.error(f"Database not found in shared drive: {shared_db_path}")
                return None
            
            modified_time = self._get_file_modified_time(shared_db_path)
            
            # Check if working database is valid (unless forcing download)
            if not force_download and self._is_working_database_valid(project_name, modified_time):
                logger.info(f"Using existing working database for {project_name}")
                return working_db_path
            
            # Copy from shared drive to working database
            logger.info(f"Creating working database for {project_name}")
            shutil.copy2(shared_db_path, working_db_path)
            
            # Save working metadata
            project_info = {
                'database_name': f"{project_name}.db",
                'modified_time': modified_time
            }
            self._save_working_metadata(project_name, project_info)
            
            logger.info(f"Working database ready for {project_name}")
            return working_db_path
            
        except Exception as e:
            logger.error(f"Error getting working database for {project_name}: {e}")
            return None
    
    def upload_database(self, project_name: str, local_db_path: str, 
                       create_backup: bool = True) -> bool:
        """
        Upload database from local path to shared drive.
        
        Args:
            project_name: Name of the project
            local_db_path: Path to local database file
            create_backup: Whether to create backup before upload
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            if not self._check_shared_drive_access():
                logger.error("Cannot access shared drive")
                return False
            
            if not os.path.exists(local_db_path):
                logger.error(f"Local database file not found: {local_db_path}")
                return False
            
            # Ensure databases folder exists
            db_folder_path = self._get_shared_drive_db_folder_path(project_name)
            os.makedirs(db_folder_path, exist_ok=True)
            
            shared_db_path = self._get_shared_drive_db_path(project_name)
            
            # Create backup if requested and file exists
            if create_backup and os.path.exists(shared_db_path):
                # Create backup folder (matching Google Drive structure)
                backup_folder_path = self._get_shared_drive_backup_folder_path(project_name)
                os.makedirs(backup_folder_path, exist_ok=True)
                
                # Generate backup filename using source file's modification time
                source_mtime = os.path.getmtime(shared_db_path)
                source_datetime = datetime.fromtimestamp(source_mtime)
                timestamp = source_datetime.strftime("%Y-%m-%d_%H-%M")
                backup_name = f"{project_name}_backup_{timestamp}.db"
                backup_path = os.path.join(backup_folder_path, backup_name)
                
                shutil.copy2(shared_db_path, backup_path)
                logger.info(f"Backup created in backup/ folder: {backup_name}")
                
                # Clean up old backups (keep only last 5 backups)
                self._cleanup_old_backups(backup_folder_path, project_name)
            
            # Upload database
            logger.info(f"Uploading database for {project_name} to shared drive")
            shutil.copy2(local_db_path, shared_db_path)
            
            # Update metadata
            modified_time = self._get_file_modified_time(shared_db_path)
            project_info = {
                'database_name': f"{project_name}.db",
                'modified_time': modified_time
            }
            
            # Update both cache and working metadata if they exist
            if os.path.exists(self._get_cached_metadata_path(project_name)):
                self._save_cache_metadata(project_name, project_info)
            
            if os.path.exists(self._get_working_metadata_path(project_name)):
                self._save_working_metadata(project_name, project_info)
            
            logger.info(f"Database uploaded successfully for {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database for {project_name}: {e}")
            return False
    
    def set_database_manager(self, database_manager):
        """Set the database manager for operations (interface compatibility)"""
        self.database_manager = database_manager
        logger.debug("Database manager set for SharedDriveDbHandler")
    
    def has_draft(self, project_name: str) -> bool:
        """Check if project has a draft (single draft per project system)"""
        try:
            # SINGLE DRAFT SYSTEM: Simple check for draft_PROJECTNAME.db
            drafts_folder_path = os.path.join(self.cache_dir, "drafts")
            
            if not os.path.exists(drafts_folder_path):
                logger.debug(f"No drafts folder exists: {drafts_folder_path}")
                return False
            
            draft_file_path = os.path.join(drafts_folder_path, f"draft_{project_name}.db")
            has_draft = os.path.exists(draft_file_path)
            logger.debug(f"Checking for single draft: {draft_file_path} -> {has_draft}")
            
            return has_draft
            
        except Exception as e:
            logger.error(f"Error checking for drafts: {e}")
            return False
    
    def check_version_status(self, project_name: str, cloud_version_time: str = None) -> Dict:
        """Check version status of project (interface compatibility with CloudDatabaseHandler)"""
        try:
            # Get shared drive database info
            shared_db_path = self._get_shared_drive_db_path(project_name)
            
            if not os.path.exists(shared_db_path):
                return {
                    'status': 'not_found',
                    'message': f'Database not found in shared drive: {project_name}',
                    'local_db_exists': False,
                    'needs_download': True
                }
            
            # Get modification time (use provided cloud_version_time if available)
            if cloud_version_time:
                modified_time = cloud_version_time
            else:
                modified_time = self._get_file_modified_time(shared_db_path)
            
            working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
            cached_db_path = os.path.join(self.cache_dir, f"{project_name}.db")
            
            # Check for both working database and cached database
            working_db_exists = os.path.exists(working_db_path)
            cached_db_exists = os.path.exists(cached_db_path)
            local_db_exists = working_db_exists or cached_db_exists
            
            # Determine which database to use for operations
            if working_db_exists:
                primary_db_path = working_db_path
                db_type_prefix = "working"
            elif cached_db_exists:
                primary_db_path = cached_db_path
                db_type_prefix = "cached"
            else:
                primary_db_path = working_db_path  # Default for error messages
            
            # Get file size if local database exists
            file_size_mb = 0
            if local_db_exists:
                try:
                    file_size_mb = round(os.path.getsize(primary_db_path) / (1024 * 1024), 2)
                except:
                    file_size_mb = 0
            
            # Check if we have a local database copy
            if local_db_exists:
                # For cached databases, we can't validate like working databases, so assume they're valid
                # For working databases, check validation
                is_valid = True
                if working_db_exists:
                    is_valid = self._is_working_database_valid(project_name, modified_time)
                
                if is_valid:
                    return {
                        'status': 'current',
                        'local_time': modified_time,
                        'cloud_time': modified_time,
                        'time_diff': 0,
                        'needs_download': False,
                        'message': f'✅ Working with latest version ({db_type_prefix} database)',
                        'local_db_exists': True,
                        'file_size_mb': file_size_mb,
                        'db_type': db_type_prefix,
                        'working_db_path': primary_db_path
                    }
                else:
                    # Calculate time difference for outdated database
                    time_diff = 60  # Default to 60 minutes if we can't calculate exact difference
                    try:
                        local_metadata_path = self._get_working_metadata_path(project_name)
                        if os.path.exists(local_metadata_path):
                            with open(local_metadata_path, 'r') as f:
                                local_metadata = json.load(f)
                                local_time = local_metadata.get('modifiedTime', modified_time)
                                
                            # Parse timestamps to calculate difference
                            from datetime import datetime
                            local_dt = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
                            cloud_dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                            time_diff = max(int((cloud_dt - local_dt).total_seconds() / 60), 1)
                        else:
                            local_time = modified_time
                    except Exception as e:
                        logger.warning(f"Could not calculate time difference for {project_name}: {e}")
                        local_time = modified_time
                    
                    return {
                        'status': 'outdated',
                        'local_time': local_time,
                        'cloud_time': modified_time,
                        'time_diff': time_diff,
                        'needs_download': True,
                        'message': f'⚠️ Your {db_type_prefix} copy is outdated - shared drive has newer version',
                        'local_db_exists': True,
                        'file_size_mb': file_size_mb,
                        'db_type': f'{db_type_prefix}_outdated',
                        'working_db_path': primary_db_path
                    }
            else:
                return {
                    'status': 'no_local',
                    'local_time': None,
                    'cloud_time': modified_time,
                    'time_diff': None,
                    'needs_download': True,
                    'message': 'Database not cached locally, will download from shared drive',
                    'local_db_exists': False,
                    'file_size_mb': 0
                }
                
        except Exception as e:
            logger.error(f"Error checking version status for {project_name}: {e}")
            return {
                'status': 'error',
                'message': f'Error checking version status: {str(e)}',
                'local_db_exists': False,
                'needs_download': True
            }
    
    # === COMPATIBILITY METHODS (adapted from CloudDatabaseHandler) ===
    
    def get_projects_folder_id(self):
        """Get projects folder ID (interface compatibility - returns shared drive path)"""
        return self.get_projects_folder_path()
    
    def get_cached_database_path(self, project_name: str) -> str:
        """Get cached database path (interface compatibility)"""
        return self._get_cached_db_path(project_name)
    
    def download_database(self, project_name: str, project_info: Dict, progress_callback=None, prefer_draft=False, force_download=False) -> Optional[str]:
        """Download database (interface compatibility - maps to download_project_database)"""
        logger.debug(f"SharedDriveDbHandler.download_database called with prefer_draft={prefer_draft}")
        
        # FIXED: Handle prefer_draft parameter properly
        if prefer_draft:
            logger.info(f"DRAFT: Checking for draft for {project_name}")
            has_draft = self.has_draft(project_name)
            logger.info(f"DRAFT: has_draft({project_name}) = {has_draft}")
            
            # Enhanced debugging - check what files exist
            drafts_folder_path = os.path.join(self.cache_dir, "drafts")
            logger.info(f"DRAFT: Drafts folder path: {drafts_folder_path}")
            logger.info(f"DRAFT: Drafts folder exists: {os.path.exists(drafts_folder_path)}")
            
            if os.path.exists(drafts_folder_path):
                try:
                    draft_files = os.listdir(drafts_folder_path)
                    logger.info(f"DRAFT: Files in drafts folder: {draft_files}")
                    
                    # Check for specific files
                    expected_db = f"draft_{project_name}.db"
                    expected_meta = f"draft_{project_name}_metadata.json"
                    logger.info(f"DRAFT: Looking for: {expected_db}, {expected_meta}")
                    logger.info(f"DRAFT: DB file exists: {expected_db in draft_files}")
                    logger.info(f"DRAFT: Metadata file exists: {expected_meta in draft_files}")
                except Exception as e:
                    logger.error(f"DRAFT: Error listing drafts folder: {e}")
            
            if has_draft:
                logger.info(f"DRAFT: Loading existing draft for {project_name} instead of downloading from shared drive")
                if progress_callback:
                    progress_callback(50, "Loading existing draft...")
                
                # Load the draft instead of downloading from shared drive
                draft_info = self.get_draft_info(project_name)
                logger.debug(f"DRAFT: get_draft_info({project_name}) returned: {draft_info}")
                
                if draft_info:
                    # Calculate draft path from draft_name (metadata doesn't store 'path')
                    draft_name = draft_info.get('draft_name')
                    logger.debug(f"DRAFT: draft_name from info: {repr(draft_name)}")
                    
                    if draft_name:
                        drafts_folder_path = os.path.join(self.cache_dir, "drafts")
                        draft_path = os.path.join(drafts_folder_path, f"{draft_name}.db")
                        logger.debug(f"DRAFT: calculated draft_path: {repr(draft_path)}")
                        
                        if os.path.exists(draft_path):
                            logger.info(f"DRAFT: Found draft at {draft_path}")
                            
                            # Copy draft to cache directory with expected name (no nested temp needed)
                            temp_draft_path = os.path.join(self.cache_dir, f"{project_name}.db")
                            
                            logger.debug(f"DRAFT: Copying draft from {draft_path} to {temp_draft_path}")
                            shutil.copy2(draft_path, temp_draft_path)
                            
                            if progress_callback:
                                progress_callback(100, "Draft loaded successfully")
                                
                            logger.info(f"DRAFT: Successfully loaded draft to {temp_draft_path}")
                            return temp_draft_path
                        else:
                            logger.warning(f"DRAFT: Draft file not found at {draft_path}, falling back to shared drive download")
                    else:
                        logger.warning(f"DRAFT: No draft_name found in draft info, falling back to shared drive download")
                else:
                    logger.warning(f"DRAFT: No draft info found for {project_name}, falling back to shared drive download")
            else:
                logger.info(f"DRAFT: No draft found for {project_name}, falling back to shared drive download")
        
        # Fallback to shared drive download (original behavior)
        logger.info(f"SHARED_DRIVE: Downloading {project_name} from shared drive (prefer_draft={prefer_draft})")
        if progress_callback:
            progress_callback(20, "Downloading from shared drive...")
            
        cached_db_path = self.download_project_database(project_name, force_download)
        
        if progress_callback:
            progress_callback(100, "Download complete")
            
        return cached_db_path
    
    def save_database(self, project_name: str, project_info: Dict, 
                     temp_db_path: str, user_name: str, changes_desc: str, 
                     change_tracker=None, progress_callback=None) -> bool:
        """Save database to shared drive (interface compatibility with CloudDatabaseHandler)"""
        try:
            logger.info(f"Saving database for {project_name} to shared drive")
            logger.info(f"User: {user_name}, Changes: {changes_desc}")
            
            # Report progress if callback provided
            if progress_callback:
                progress_callback(10, "Starting upload to shared drive...")
            
            # Use existing upload_database method
            success = self.upload_database(project_name, temp_db_path, create_backup=True)
            
            if progress_callback:
                progress_callback(70, "Upload complete, saving change tracking...")
            
            if success and change_tracker:
                # Save change tracking info to shared drive changes folder
                self._save_detailed_changes(project_name, change_tracker)
                
            if progress_callback:
                progress_callback(100, "Upload completed successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving database for {project_name}: {e}")
            return False
    
    def _save_detailed_changes(self, project_name: str, change_tracker):
        """Save detailed change tracking data to shared drive"""
        try:
            # Get change data
            changes_data = change_tracker.get_changes_for_save()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"changes_{timestamp}.json"
            
            # Create changes folder in project databases folder
            db_folder_path = self._get_shared_drive_db_folder_path(project_name)
            changes_folder_path = os.path.join(db_folder_path, "changes")
            os.makedirs(changes_folder_path, exist_ok=True)
            
            # Save changes file
            changes_file_path = os.path.join(changes_folder_path, filename)
            with open(changes_file_path, 'w') as f:
                json.dump(changes_data, f, indent=2)
            
            logger.info(f"Detailed changes saved to: {changes_file_path}")
            
        except Exception as e:
            logger.error(f"Error saving detailed changes: {e}")
    
    # === LOCKING SYSTEM (stub methods for interface compatibility) ===
    
    def check_lock(self, project_info: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check if database is locked - no locking for shared drive (users work on local copies)"""
        # Always return not locked since each user works on their own local copy
        return False, None, None
    
    def acquire_lock(self, project_info: Dict, user_name: str) -> bool:
        """Acquire lock - no locking needed for shared drive (users work on local copies)"""
        # Always successful since no actual locking needed
        return True
    
    def _release_lock(self, project_info: Dict):
        """Release lock - no-op for shared drive (no locks created)"""
        # Nothing to release since no locks are created
        pass
    
    # === DRAFT MANAGEMENT SYSTEM (adapted for shared drive) ===
    
    def save_as_draft(self, project_name: str, local_db_path: str, 
                     original_download_time: str, changes_description: str = None) -> bool:
        """Save database as draft (single draft per project system)"""
        try:
            # SINGLE DRAFT SYSTEM: Simple naming without timestamps
            draft_name = f"draft_{project_name}"
            
            # FIXED: Create drafts folder in LOCAL cache directory, not shared drive
            # Shared drive may not be writable or accessible for draft storage
            drafts_folder_path = os.path.join(self.cache_dir, "drafts")
            os.makedirs(drafts_folder_path, exist_ok=True)
            logger.info(f"Creating draft in local cache directory: {drafts_folder_path}")
            
            # ENHANCED: Define all draft file paths (including WAL/SHM)
            draft_file_path = os.path.join(drafts_folder_path, f"{draft_name}.db")
            draft_wal_path = os.path.join(drafts_folder_path, f"{draft_name}.db-wal")
            draft_shm_path = os.path.join(drafts_folder_path, f"{draft_name}.db-shm")
            metadata_path = os.path.join(drafts_folder_path, f"{draft_name}_metadata.json")
            
            # Check if we're updating existing draft
            is_updating_existing = os.path.exists(draft_file_path)
            
            if is_updating_existing:
                logger.info(f"Updating existing draft for {project_name}")
                # Remove old files (including WAL/SHM)
                try:
                    for file_path in [draft_file_path, draft_wal_path, draft_shm_path, metadata_path]:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.debug(f"Removed old draft file: {os.path.basename(file_path)}")
                    logger.debug(f"Removed old draft files for {project_name}")
                except Exception as e:
                    logger.warning(f"Error removing old draft files: {e}")
            else:
                logger.info(f"Creating new draft for {project_name}")
            
            # ENHANCED: Add detailed logging for draft saving process
            logger.info(f"=== SAVING DRAFT: {draft_name} ===")
            logger.info(f"Project: {project_name}")
            logger.info(f"Source database: {local_db_path}")
            logger.info(f"Target draft path: {draft_file_path}")
            
            if not os.path.exists(local_db_path):
                raise FileNotFoundError(f"Source database file not found: {local_db_path}")
            
            source_size = os.path.getsize(local_db_path)
            logger.info(f"Source database size: {source_size} bytes")
            logger.info(f"Source database basename: {os.path.basename(local_db_path)}")
            
            # Verify this is the working database (should be wlm_PROJECT.db)
            if not os.path.basename(local_db_path).startswith(f"wlm_{project_name}"):
                logger.warning(f"WARNING: Source database doesn't appear to be working copy for {project_name}")
                logger.warning(f"Expected: wlm_{project_name}.db, Got: {os.path.basename(local_db_path)}")
            
            # Copy main database file
            shutil.copy2(local_db_path, draft_file_path)
            draft_size = os.path.getsize(draft_file_path)
            logger.info(f"Draft database saved, size: {draft_size} bytes")
            
            # Copy WAL file if it exists (essential for change tracking)
            wal_source = f"{local_db_path}-wal"
            has_wal = False
            if os.path.exists(wal_source):
                shutil.copy2(wal_source, draft_wal_path)
                wal_size = os.path.getsize(draft_wal_path)
                logger.info(f"Draft WAL file saved, size: {wal_size} bytes")
                has_wal = True
            else:
                logger.debug(f"No WAL file found at: {wal_source}")
            
            # Copy SHM file if it exists (essential for change tracking)
            shm_source = f"{local_db_path}-shm"
            has_shm = False
            if os.path.exists(shm_source):
                shutil.copy2(shm_source, draft_shm_path)
                shm_size = os.path.getsize(draft_shm_path)
                logger.info(f"Draft SHM file saved, size: {shm_size} bytes")
                has_shm = True
            else:
                logger.debug(f"No SHM file found at: {shm_source}")
            
            logger.info(f"Draft structure saved: DB=✓, WAL={'✓' if has_wal else '✗'}, SHM={'✓' if has_shm else '✗'}")
            logger.info(f"Size verification: source={source_size}, draft={draft_size}, match={source_size == draft_size}")
            
            # Save draft metadata (enhanced with WAL/SHM tracking)
            draft_metadata = {
                'draft_name': draft_name,
                'created_at': datetime.now().isoformat(),
                'project_name': project_name,
                'original_size': os.path.getsize(local_db_path),
                'original_download_time': original_download_time,
                'changes_description': changes_description or "No description provided",
                'draft_type': 'shared_drive',
                'has_wal': has_wal,
                'has_shm': has_shm,
                'wal_size': os.path.getsize(draft_wal_path) if has_wal else 0,
                'shm_size': os.path.getsize(draft_shm_path) if has_shm else 0
            }
            
            logger.info(f"Saving metadata to: {metadata_path}")
            with open(metadata_path, 'w') as f:
                json.dump(draft_metadata, f, indent=2)
            
            if is_updating_existing:
                logger.info(f"Draft updated successfully: {draft_name} for {project_name}")
            else:
                logger.info(f"Draft created successfully: {draft_name} for {project_name}")
            logger.info(f"Draft files: {draft_file_path}, {metadata_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving draft: {e}")
            return False
    
    def load_draft(self, project_name: str) -> Optional[str]:
        """Load draft database (adapted for shared drive from local cache, compatible signature)"""
        try:
            # FIXED: Get the latest draft info to determine which draft to load
            draft_info = self.get_draft_info(project_name)
            if not draft_info:
                logger.warning(f"No draft found for {project_name}")
                return None
            
            draft_name = draft_info.get('draft_name')
            if not draft_name:
                logger.error(f"Draft info missing draft_name for {project_name}")
                return None
            
            # Look for drafts in local cache directory
            drafts_folder_path = os.path.join(self.cache_dir, "drafts")
            draft_file_path = os.path.join(drafts_folder_path, f"{draft_name}.db")
            
            if not os.path.exists(draft_file_path):
                logger.warning(f"Draft database file not found: {draft_file_path}")
                return None
            
            # ENHANCED: Copy complete draft structure to working location
            working_db_path = os.path.join(self.cache_dir, f"wlm_{project_name}.db")
            working_wal_path = f"{working_db_path}-wal"
            working_shm_path = f"{working_db_path}-shm"
            
            # Define draft file paths
            draft_wal_source = os.path.join(drafts_folder_path, f"{draft_name}.db-wal")
            draft_shm_source = os.path.join(drafts_folder_path, f"{draft_name}.db-shm")
            
            # ENHANCED: Add detailed logging for draft loading process
            draft_size = os.path.getsize(draft_file_path)
            logger.info(f"Loading draft: {draft_name}")
            logger.info(f"Draft source: {draft_file_path} (size: {draft_size} bytes)")
            logger.info(f"Working target: {working_db_path}")
            
            # Check if working database already exists and remove all working files
            if os.path.exists(working_db_path):
                existing_size = os.path.getsize(working_db_path)
                logger.info(f"Removing existing working database (size: {existing_size} bytes)")
                # Remove all working files to ensure clean state
                for working_file in [working_db_path, working_wal_path, working_shm_path]:
                    if os.path.exists(working_file):
                        os.remove(working_file)
                        logger.debug(f"Removed existing file: {os.path.basename(working_file)}")
            
            # Copy main database file
            shutil.copy2(draft_file_path, working_db_path)
            final_size = os.path.getsize(working_db_path)
            logger.info(f"Working database copied, size: {final_size} bytes")
            
            # Copy WAL file if it exists in draft
            has_wal = False
            if os.path.exists(draft_wal_source):
                shutil.copy2(draft_wal_source, working_wal_path)
                wal_size = os.path.getsize(working_wal_path)
                logger.info(f"Working WAL file restored, size: {wal_size} bytes")
                has_wal = True
            else:
                logger.debug(f"No WAL file in draft: {draft_wal_source}")
            
            # Copy SHM file if it exists in draft
            has_shm = False
            if os.path.exists(draft_shm_source):
                shutil.copy2(draft_shm_source, working_shm_path)
                shm_size = os.path.getsize(working_shm_path)
                logger.info(f"Working SHM file restored, size: {shm_size} bytes")
                has_shm = True
            else:
                logger.debug(f"No SHM file in draft: {draft_shm_source}")
            
            logger.info(f"Draft loaded successfully: {draft_name} for {project_name}")
            logger.info(f"Working structure restored: DB=✓, WAL={'✓' if has_wal else '✗'}, SHM={'✓' if has_shm else '✗'}")
            logger.info(f"Working database path: {working_db_path}")
            
            # CRITICAL: If no WAL/SHM files exist, we need to ensure SQLite creates them
            # by opening the database in WAL mode
            if not has_wal or not has_shm:
                logger.info("Creating WAL/SHM files for change tracking by opening database in WAL mode")
                try:
                    import sqlite3
                    with sqlite3.connect(working_db_path) as conn:
                        conn.execute('PRAGMA journal_mode = WAL')
                        conn.execute('PRAGMA synchronous = OFF')
                        # Force creation of WAL/SHM files
                        conn.execute('SELECT COUNT(*) FROM sqlite_master')
                        conn.commit()
                    logger.info("WAL/SHM files created for change tracking")
                except Exception as e:
                    logger.warning(f"Error creating WAL/SHM files: {e}")
            
            return working_db_path
            
        except Exception as e:
            logger.error(f"Error loading draft for {project_name}: {e}")
            return None
    
    def clear_draft(self, project_name: str) -> bool:
        """Clear/delete the single draft for a project (single draft per project system)"""
        try:
            # SINGLE DRAFT SYSTEM: Simple deletion of specific files
            drafts_folder_path = os.path.join(self.cache_dir, "drafts")
            
            if not os.path.exists(drafts_folder_path):
                return True  # No drafts to clear
            
            # Define file paths for complete draft structure
            draft_file_path = os.path.join(drafts_folder_path, f"draft_{project_name}.db")
            draft_wal_path = os.path.join(drafts_folder_path, f"draft_{project_name}.db-wal")
            draft_shm_path = os.path.join(drafts_folder_path, f"draft_{project_name}.db-shm")
            metadata_path = os.path.join(drafts_folder_path, f"draft_{project_name}_metadata.json")
            
            draft_existed = False
            
            # Delete all draft files if they exist
            for file_path, file_type in [
                (draft_file_path, "database"),
                (draft_wal_path, "WAL"),
                (draft_shm_path, "SHM"),
                (metadata_path, "metadata")
            ]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed draft {file_type}: {os.path.basename(file_path)}")
                    draft_existed = True
            
            if draft_existed:
                logger.info(f"Cleared draft for project {project_name}")
            else:
                logger.debug(f"No draft found to clear for project {project_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing drafts for {project_name}: {e}")
            return False
    
    def get_draft_info(self, project_name: str) -> Optional[Dict]:
        """Get draft information (single draft per project system)"""
        try:
            # SINGLE DRAFT SYSTEM: Look for specific draft file
            drafts_folder_path = os.path.join(self.cache_dir, "drafts")
            
            if not os.path.exists(drafts_folder_path):
                logger.debug(f"DRAFT: No drafts folder exists at {drafts_folder_path}")
                return None
            
            # Check for the single draft file for this project
            metadata_path = os.path.join(drafts_folder_path, f"draft_{project_name}_metadata.json")
            
            if not os.path.exists(metadata_path):
                logger.debug(f"DRAFT: No draft metadata found at {metadata_path}")
                return None
            
            # Load draft metadata
            with open(metadata_path, 'r') as f:
                draft_info = json.load(f)
            
            logger.info(f"Found single draft for project {project_name}: {draft_info.get('draft_name')}")
            return draft_info
            
        except Exception as e:
            logger.error(f"Error getting draft info: {e}")
            return None
    
    # === SESSION MANAGEMENT (adapted for shared drive) ===
    
    def create_session_backup(self, project_name: str, database_path: str, backup_type: str) -> bool:
        """
        OPTIMIZED: Skip session backup creation for shared drive.
        We use the cached database as our reference instead.
        """
        logger.info(f"Skipping session backup creation for {project_name} - using cached database as reference")
        return True  # Always return True to maintain compatibility
    
    def get_session_backup_path(self, project_name: str, backup_type: str) -> Optional[str]:
        """
        OPTIMIZED: Return cached database path as backup reference.
        This eliminates the need for separate session backup files.
        """
        if backup_type == 'original':
            # Return cached database path as "original" backup
            cached_path = self._get_cached_db_path(project_name)
            if os.path.exists(cached_path):
                logger.debug(f"Using cached database as original backup: {cached_path}")
                return cached_path
        elif backup_type == 'last_uploaded':
            # For "last_uploaded", also use cached database since it represents the latest known state
            cached_path = self._get_cached_db_path(project_name)
            if os.path.exists(cached_path):
                logger.debug(f"Using cached database as last_uploaded backup: {cached_path}")
                return cached_path
        
        return None
    
    def cleanup_session_backups(self):
        """OPTIMIZED: No session backups to clean up for shared drive"""
        # Session backups are no longer created, so nothing to clean up
        logger.debug("No session backups to clean up - using cached database as reference")
        self.session_backups.clear()  # Clear any legacy references
    
    # === STUB METHODS (for interface compatibility) ===
    
    def check_draft_version_changes(self, project_name: str) -> Dict:
        """Check draft version changes (stub for interface compatibility)"""
        return {'has_changes': False, 'message': 'Not implemented for shared drive'}
    
    def check_for_outdated_working_databases(self) -> List[str]:
        """Check for outdated working databases (stub)"""
        return []
    
    def ensure_working_database_preserved(self, project_name: str):
        """Ensure working database preserved (stub)"""
        pass
    
    def has_session_changes_since_download(self, project_name: str, current_db_path: str) -> bool:
        """
        Check if session has changes since download by comparing working database with cached.
        This is the same as has_session_changes_since_upload for shared drive.
        
        Args:
            project_name: Name of the project
            current_db_path: Path to current working database
            
        Returns:
            True if working database differs from cached database
        """
        # For shared drive, changes since download = changes since upload
        # Both compare working copy against cached copy
        return self.has_session_changes_since_upload(project_name, current_db_path)
    
    def has_session_changes_since_upload(self, project_name: str, current_db_path: str) -> bool:
        """
        Check if session has changes since upload by comparing working database with cached.
        OPTIMIZED: Uses cached database as reference instead of session backup.
        
        Args:
            project_name: Name of the project
            current_db_path: Path to current working database
            
        Returns:
            True if working database differs from cached database
        """
        try:
            import os
            
            # Get cached database path (this is our "original" reference)
            cached_db_path = self._get_cached_db_path(project_name)
            
            if not os.path.exists(cached_db_path) or not os.path.exists(current_db_path):
                logger.debug(f"Missing database files for comparison: cached={os.path.exists(cached_db_path)}, current={os.path.exists(current_db_path)}")
                return False
            
            # Compare file sizes as quick check
            cached_size = os.path.getsize(cached_db_path)
            current_size = os.path.getsize(current_db_path)
            
            if cached_size != current_size:
                logger.info(f"Database size changed: cached={cached_size}, current={current_size}")
                return True
            
            # Compare modification times
            cached_mtime = os.path.getmtime(cached_db_path)
            current_mtime = os.path.getmtime(current_db_path)
            
            if current_mtime > cached_mtime:
                logger.info(f"Working database modified after cached version")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking session changes: {e}")
            return False
    
    def list_proposals(self) -> List[Dict]:
        """List proposals (stub - not implemented for shared drive)"""
        return []
    
    def download_proposal(self, proposal_id: str) -> Optional[str]:
        """Download proposal (stub - not implemented for shared drive)"""
        return None
    
    def upload_proposal(self, proposal_data: Dict) -> bool:
        """Upload proposal (stub - not implemented for shared drive)"""
        return False
    
    def rebuild_xle_tracking_after_database_load(self, project_name: str):
        """Rebuild XLE tracking after database load (stub)"""
        pass
    
    def restore_original_database(self, project_name: str) -> bool:
        """Restore original database (stub)"""
        return False
    
    def _cleanup_old_backups(self, backup_folder_path: str, project_name: str, keep_count: int = 5):
        """Clean up old backup files, keeping only the most recent ones"""
        try:
            if not os.path.exists(backup_folder_path):
                return
            
            # Get all backup files for this project
            backup_files = []
            for file in os.listdir(backup_folder_path):
                if file.startswith(f"{project_name}_backup_") and file.endswith(".db"):
                    file_path = os.path.join(backup_folder_path, file)
                    if os.path.isfile(file_path):
                        backup_files.append((file_path, os.path.getmtime(file_path)))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups beyond keep_count
            files_to_remove = backup_files[keep_count:]
            for file_path, _ in files_to_remove:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed old backup: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.warning(f"Could not remove old backup {file_path}: {e}")
            
            if files_to_remove:
                logger.info(f"Cleaned up {len(files_to_remove)} old backup files, keeping {keep_count} most recent")
                
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def update_local_version_tracking(self, project_name: str, cloud_version_time: str, 
                                    local_db_path: str, operation: str = "download"):
        """Update local version tracking (adapted for shared drive)"""
        # For shared drive, we update version tracking using our version manager
        if hasattr(self, 'version_manager') and self.version_manager:
            self.version_manager.update_local_version(project_name, cloud_version_time, 
                                                    local_db_path, operation)
        else:
            logger.debug(f"Version tracking updated for {project_name}: {operation}")
    
    def cleanup_temp_files(self, force_cleanup_working_dbs=False):
        """Clean up any temporary files created during operations"""
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not clean up temp file {temp_file}: {e}")
        
        self.temp_files.clear()
        
        # If force cleanup is requested, attempt to clean up all working database files
        if force_cleanup_working_dbs:
            self._cleanup_working_database_files()
    
    def _cleanup_working_database_files(self):
        """
        Safely clean up working database files (wlm_*.db and related files).
        This method handles the Windows file locking issue by waiting and retrying.
        ENHANCED: Also cleans up legacy session backup files.
        """
        import glob
        
        try:
            # Find all working database files in cache directory
            working_db_pattern = os.path.join(self.cache_dir, "wlm_*.db*")
            working_files = glob.glob(working_db_pattern)
            
            # Also find legacy session backup files to clean up
            session_backup_pattern = os.path.join(self.cache_dir, "*session_backup*.db")
            session_backup_files = glob.glob(session_backup_pattern)
            
            all_files = working_files + session_backup_files
            
            if not all_files:
                logger.debug("No working database or session backup files found to clean up")
                return
            
            logger.info(f"Found {len(working_files)} working database files and {len(session_backup_files)} legacy session backup files to clean up")
            
            # Group working database files by base database name
            db_groups = {}
            for file_path in working_files:
                basename = os.path.basename(file_path)
                if basename.endswith('.db'):
                    base_name = basename
                elif basename.endswith('.db-shm'):
                    base_name = basename[:-4]  # Remove '-shm'
                elif basename.endswith('.db-wal'):
                    base_name = basename[:-4]  # Remove '-wal'
                else:
                    base_name = basename
                
                if base_name not in db_groups:
                    db_groups[base_name] = []
                db_groups[base_name].append(file_path)
            
            # Clean up each database group
            for db_name, file_list in db_groups.items():
                self._cleanup_database_file_group(db_name, file_list)
            
            # Clean up legacy session backup files (simple deletion)
            for backup_file in session_backup_files:
                try:
                    os.remove(backup_file)
                    logger.info(f"Removed legacy session backup: {backup_file}")
                except Exception as e:
                    logger.warning(f"Could not remove legacy session backup {backup_file}: {e}")
                
        except Exception as e:
            logger.error(f"Error during working database cleanup: {e}")
    
    def _cleanup_database_file_group(self, db_name, file_list):
        """Clean up a group of database files (main, shm, wal) with retry logic"""
        
        logger.info(f"Cleaning up database files for: {db_name}")
        
        # Sort files to delete main database last (SQLite might recreate shm/wal)
        file_list.sort(key=lambda x: (
            0 if x.endswith('.db-shm') else 
            1 if x.endswith('.db-wal') else 
            2  # .db file last
        ))
        
        for file_path in file_list:
            if not os.path.exists(file_path):
                continue
                
            success = False
            max_retries = 5
            
            for attempt in range(max_retries):
                try:
                    os.remove(file_path)
                    logger.info(f"Successfully removed: {file_path}")
                    success = True
                    break
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                        logger.debug(f"File locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        logger.warning(f"Could not remove {file_path} after {max_retries} attempts: {e} - file may still be in use")
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")
                    break
            
            if success:
                # Small delay between files to let Windows release handles
                time.sleep(0.05)