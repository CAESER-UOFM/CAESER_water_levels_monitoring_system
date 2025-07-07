"""
Version Manager

Handles persistent version tracking for cloud databases.
Tracks local cache versions vs cloud versions to enable smart caching.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages version tracking for cloud database caching"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.metadata_file = os.path.join(cache_dir, 'version_metadata.json')
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing metadata
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load version metadata from file"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading version metadata: {e}")
            return {}
    
    def _save_metadata(self):
        """Save version metadata to file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.debug(f"Version metadata saved to {self.metadata_file}")
        except Exception as e:
            logger.error(f"Error saving version metadata: {e}")
    
    def get_local_version_info(self, project_name: str) -> Optional[Dict]:
        """Get local version information for a project"""
        return self.metadata.get(project_name)
    
    def update_local_version(self, project_name: str, cloud_version_time: str, 
                           local_db_path: str, operation: str = "download"):
        """
        Update local version tracking information
        
        Args:
            project_name: Name of the cloud project
            cloud_version_time: Timestamp of the cloud version we're based on
            local_db_path: Path to the local database file (temp UUID path)
            operation: Type of operation ('download', 'upload', 'draft_load')
        """
        try:
            # Use stable cache path instead of temporary UUID path
            # This matches what _is_cache_valid() in cloud_database_handler uses
            stable_cache_path = os.path.join(self.cache_dir, f"{project_name}.db")
            
            # Get file info from the temp path (which actually exists)
            file_size = os.path.getsize(local_db_path) if os.path.exists(local_db_path) else 0
            
            # Update metadata with stable cache path
            self.metadata[project_name] = {
                'local_version_time': cloud_version_time,
                'last_sync_time': datetime.now(timezone.utc).isoformat(),
                'local_db_path': stable_cache_path,  # Use stable path for consistency
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'operation': operation,
                'is_current': True  # Assume current until proven otherwise
            }
            
            self._save_metadata()
            logger.info(f"Updated local version tracking for {project_name}: {operation} (using stable cache path)")
            
        except Exception as e:
            logger.error(f"Error updating local version: {e}")
    
    def compare_versions(self, project_name: str, cloud_version_time: str) -> Dict:
        """
        Compare local version with cloud version
        
        Returns:
            Dict with comparison results:
            - status: 'current', 'outdated', 'newer', 'no_local'
            - local_time: Local version timestamp
            - cloud_time: Cloud version timestamp  
            - time_diff: Difference in minutes
            - needs_download: Boolean
            - message: Human readable status
        """
        try:
            local_info = self.get_local_version_info(project_name)
            
            if not local_info:
                return {
                    'status': 'no_local',
                    'local_time': None,
                    'cloud_time': cloud_version_time,
                    'time_diff': None,
                    'needs_download': True,
                    'message': 'No local cache available',
                    'local_db_exists': False
                }
            
            # Check if local DB file still exists
            local_db_path = local_info.get('local_db_path', '')
            local_db_exists = os.path.exists(local_db_path)
            
            if not local_db_exists:
                return {
                    'status': 'no_local',
                    'local_time': local_info.get('local_version_time'),
                    'cloud_time': cloud_version_time,
                    'time_diff': None,
                    'needs_download': True,
                    'message': 'Local cache file missing',
                    'local_db_exists': False
                }
            
            local_time = local_info.get('local_version_time')
            
            # Parse timestamps
            try:
                local_dt = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
                cloud_dt = datetime.fromisoformat(cloud_version_time.replace('Z', '+00:00'))
                
                # Calculate difference in minutes
                diff_seconds = (cloud_dt - local_dt).total_seconds()
                diff_minutes = int(diff_seconds / 60)
                
                if abs(diff_seconds) < 60:  # Within 1 minute = same version
                    status = 'current'
                    message = '✅ Working with latest version'
                    needs_download = False
                elif local_dt < cloud_dt:
                    status = 'outdated'
                    if diff_minutes < 60:
                        message = f'⚠️ Cloud updated {diff_minutes} minutes ago'
                    elif diff_minutes < 1440:  # < 24 hours
                        hours = diff_minutes // 60
                        message = f'⚠️ Cloud updated {hours} hour{"s" if hours > 1 else ""} ago'
                    else:
                        days = diff_minutes // 1440
                        message = f'⚠️ Cloud updated {days} day{"s" if days > 1 else ""} ago'
                    needs_download = True
                else:
                    status = 'newer'
                    message = '🤔 Local is newer than cloud (unusual)'
                    needs_download = False
                
                return {
                    'status': status,
                    'local_time': local_time,
                    'cloud_time': cloud_version_time,
                    'time_diff': diff_minutes,
                    'needs_download': needs_download,
                    'message': message,
                    'local_db_exists': True,
                    'local_db_path': local_db_path,
                    'file_size_mb': local_info.get('file_size_mb', 0)
                }
                
            except ValueError as e:
                logger.error(f"Error parsing timestamps: {e}")
                return {
                    'status': 'error',
                    'local_time': local_time,
                    'cloud_time': cloud_version_time,
                    'time_diff': None,
                    'needs_download': True,
                    'message': 'Error comparing versions',
                    'local_db_exists': local_db_exists
                }
                
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")
            return {
                'status': 'error',
                'local_time': None,
                'cloud_time': cloud_version_time,
                'time_diff': None,
                'needs_download': True,
                'message': f'Version check error: {e}',
                'local_db_exists': False
            }
    
    def mark_as_outdated(self, project_name: str):
        """Mark a local version as outdated (when cloud is updated by others)"""
        if project_name in self.metadata:
            self.metadata[project_name]['is_current'] = False
            self._save_metadata()
            logger.info(f"Marked {project_name} as outdated")
    
    def cleanup_old_versions(self, project_name: str, keep_current: bool = True):
        """Clean up old version metadata"""
        if not keep_current and project_name in self.metadata:
            # Remove local DB file if it exists
            local_info = self.metadata[project_name]
            local_db_path = local_info.get('local_db_path')
            if local_db_path and os.path.exists(local_db_path):
                try:
                    os.remove(local_db_path)
                    logger.info(f"Removed old local DB: {local_db_path}")
                except Exception as e:
                    logger.warning(f"Could not remove old DB file: {e}")
            
            # Remove metadata
            del self.metadata[project_name]
            self._save_metadata()
            logger.info(f"Cleaned up version metadata for {project_name}")
    
    def get_all_projects_status(self) -> Dict:
        """Get version status for all tracked projects"""
        return self.metadata.copy()
    
    def get_cache_summary(self) -> Dict:
        """Get summary of cache usage"""
        total_size = 0
        project_count = 0
        
        for project_name, info in self.metadata.items():
            if info.get('local_db_exists', True):  # Assume exists if not checked
                total_size += info.get('file_size_mb', 0)
                project_count += 1
        
        return {
            'total_projects': project_count,
            'total_size_mb': round(total_size, 2),
            'total_size_gb': round(total_size / 1024, 2)
        }