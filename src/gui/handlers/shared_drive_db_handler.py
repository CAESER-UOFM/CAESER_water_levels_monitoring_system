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
            self.shared_drive_root = self.settings_handler.get_setting(
                "shared_drive_root", "S:/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring/"
            )
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
                        'locked_by': None,  # TODO: Implement locking mechanism
                        'lock_time': None
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
                backup_name = f"{project_name}_backup_{int(time.time())}.db"
                backup_path = os.path.join(db_folder_path, backup_name)
                shutil.copy2(shared_db_path, backup_path)
                logger.info(f"Backup created: {backup_name}")
            
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
        """Check if project has a draft (interface compatibility with CloudDatabaseHandler)"""
        # For shared drive, we can check if draft manager has any drafts
        if hasattr(self, 'draft_manager') and self.draft_manager:
            return self.draft_manager.has_draft(project_name)
        return False
    
    def cleanup_temp_files(self):
        """Clean up any temporary files created during operations"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not clean up temp file {temp_file}: {e}")
        
        self.temp_files.clear()