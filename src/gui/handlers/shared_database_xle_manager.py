#!/usr/bin/env python3
"""
Shared Database XLE Manager

Handles temporary XLE file storage during draft phase for shared databases.
Provides proper separation between local and shared database workflows.

Key Features:
1. Temp storage during draft phase: cache/temp_xle_files/{project_name}/
2. Registry tracking of temp files linked to draft database
3. Move temp files to SMOO structure on database push
4. Cleanup temp files on draft discard or app restart

@author: SMOO XLE Workflow Implementation
"""

import os
import json
import shutil
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TempXLEFileRecord:
    """Record for tracking temporary XLE files during draft phase"""
    file_id: str
    original_path: str
    temp_path: str
    project_name: str
    device_type: str  # 'barologger' or 'transducer'
    serial_number: str
    well_number: Optional[str]
    location: str
    start_date: str
    end_date: str
    file_size: int
    file_hash: str
    created_at: str
    status: str  # 'temp', 'moved_to_smoo', 'cleaned_up'

class SharedDatabaseXLEManager:
    """
    Manages temporary XLE files for shared databases during draft phase.
    Handles the workflow: temp storage → SMOO push → cleanup
    """
    
    def __init__(self, cache_dir: str):
        """
        Initialize shared database XLE manager
        
        Args:
            cache_dir: Base cache directory for temp files
        """
        self.cache_dir = cache_dir
        self.temp_xle_base = os.path.join(cache_dir, 'temp_xle_files')
        self.registry_file = os.path.join(self.temp_xle_base, 'temp_xle_registry.json')
        
        # Ensure temp directory exists
        os.makedirs(self.temp_xle_base, exist_ok=True)
        
        logger.info(f"SharedDatabaseXLEManager initialized: {self.temp_xle_base}")
    
    def store_temp_xle(self, original_file_path: str, project_name: str, 
                      device_type: str, serial_number: str, location: str,
                      start_date: datetime, end_date: datetime, 
                      well_number: Optional[str] = None) -> str:
        """
        Store XLE file in temporary location during draft phase
        
        Args:
            original_file_path: Path to original XLE file
            project_name: Name of the project
            device_type: 'barologger' or 'transducer'
            serial_number: Device serial number
            location: Location description
            start_date: Start date of data
            end_date: End date of data
            well_number: Well number for transducers
            
        Returns:
            Path to stored temp file
        """
        try:
            if not os.path.exists(original_file_path):
                raise FileNotFoundError(f"Original XLE file not found: {original_file_path}")
            
            # Create project temp directory
            project_temp_dir = os.path.join(self.temp_xle_base, project_name)
            device_temp_dir = os.path.join(project_temp_dir, device_type)
            os.makedirs(device_temp_dir, exist_ok=True)
            
            # Generate temp filename with metadata
            identifier = well_number if well_number else serial_number
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            temp_filename = f"{device_type}_{identifier}_{location}_{start_str}_to_{end_str}.xle"
            
            # Clean filename for filesystem compatibility
            temp_filename = self._sanitize_filename(temp_filename)
            temp_file_path = os.path.join(device_temp_dir, temp_filename)
            
            # Copy file to temp location
            shutil.copy2(original_file_path, temp_file_path)
            
            # Calculate file metadata
            file_size = os.path.getsize(temp_file_path)
            file_hash = self._calculate_file_hash(temp_file_path)
            
            # Create registry record
            file_id = self._generate_file_id(project_name, device_type, serial_number, start_date)
            record = TempXLEFileRecord(
                file_id=file_id,
                original_path=original_file_path,
                temp_path=temp_file_path,
                project_name=project_name,
                device_type=device_type,
                serial_number=serial_number,
                well_number=well_number,
                location=location,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                file_size=file_size,
                file_hash=file_hash,
                created_at=datetime.now().isoformat(),
                status='temp'
            )
            
            # Add to registry
            self._add_to_registry(record)
            
            logger.info(f"Stored temp XLE file: {temp_filename} (ID: {file_id})")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Error storing temp XLE file: {e}")
            raise
    
    def list_temp_xle_files(self, project_name: str) -> List[Dict]:
        """
        List all temp XLE files for a project
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of temp file records
        """
        try:
            registry = self._load_registry()
            project_files = []
            
            for record in registry.values():
                if record['project_name'] == project_name and record['status'] == 'temp':
                    # Verify file still exists
                    if os.path.exists(record['temp_path']):
                        project_files.append(record)
                    else:
                        # Mark as cleaned up if file missing
                        self._update_record_status(record['file_id'], 'cleaned_up')
            
            logger.debug(f"Found {len(project_files)} temp XLE files for project: {project_name}")
            return project_files
            
        except Exception as e:
            logger.error(f"Error listing temp XLE files: {e}")
            return []
    
    def move_to_smoo(self, project_name: str, smoo_base_path: str) -> bool:
        """
        Move temp XLE files to SMOO structure on database push
        
        Args:
            project_name: Name of the project
            smoo_base_path: Base path for SMOO storage (will create Projects/{project}/XLE_Files/)
            
        Returns:
            True if successful
        """
        try:
            temp_files = self.list_temp_xle_files(project_name)
            if not temp_files:
                logger.info(f"No temp XLE files to move for project: {project_name}")
                return True
            
            # Create SMOO XLE structure
            smoo_project_dir = os.path.join(smoo_base_path, 'Projects', project_name)
            smoo_xle_dir = os.path.join(smoo_project_dir, 'XLE_Files')
            
            moved_count = 0
            failed_count = 0
            
            for file_record in temp_files:
                try:
                    # Determine target directory in SMOO
                    device_type = file_record['device_type']
                    identifier = file_record.get('well_number') or file_record['serial_number']
                    
                    target_dir = os.path.join(smoo_xle_dir, f"{device_type}s", identifier)
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Generate final filename for SMOO
                    original_filename = os.path.basename(file_record['temp_path'])
                    target_path = os.path.join(target_dir, original_filename)
                    
                    # Move file to SMOO (use copy + remove for cross-filesystem compatibility)
                    shutil.copy2(file_record['temp_path'], target_path)
                    os.remove(file_record['temp_path'])
                    
                    # Update registry
                    self._update_record_status(file_record['file_id'], 'moved_to_smoo')
                    
                    moved_count += 1
                    logger.info(f"Moved temp XLE to SMOO: {original_filename}")
                    
                except Exception as e:
                    logger.error(f"Error moving temp XLE file {file_record['file_id']}: {e}")
                    failed_count += 1
            
            logger.info(f"SMOO move complete: {moved_count} moved, {failed_count} failed")
            return failed_count == 0
            
        except Exception as e:
            logger.error(f"Error moving temp XLE files to SMOO: {e}")
            return False
    
    def cleanup_temp_files(self, project_name: str) -> bool:
        """
        Clean up temp XLE files for a project (on draft discard)
        
        Args:
            project_name: Name of the project
            
        Returns:
            True if successful
        """
        try:
            temp_files = self.list_temp_xle_files(project_name)
            if not temp_files:
                logger.info(f"No temp XLE files to clean up for project: {project_name}")
                return True
            
            cleaned_count = 0
            failed_count = 0
            
            for file_record in temp_files:
                try:
                    # Remove temp file
                    if os.path.exists(file_record['temp_path']):
                        os.remove(file_record['temp_path'])
                    
                    # Update registry
                    self._update_record_status(file_record['file_id'], 'cleaned_up')
                    
                    cleaned_count += 1
                    logger.info(f"Cleaned up temp XLE: {os.path.basename(file_record['temp_path'])}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up temp XLE file {file_record['file_id']}: {e}")
                    failed_count += 1
            
            # Remove empty project directory
            project_temp_dir = os.path.join(self.temp_xle_base, project_name)
            if os.path.exists(project_temp_dir):
                try:
                    # Remove if empty (rmdir only removes empty directories)
                    for device_dir in ['barologgers', 'transducers']:
                        device_path = os.path.join(project_temp_dir, device_dir)
                        if os.path.exists(device_path) and not os.listdir(device_path):
                            os.rmdir(device_path)
                    
                    if not os.listdir(project_temp_dir):
                        os.rmdir(project_temp_dir)
                        logger.info(f"Removed empty project temp directory: {project_name}")
                except OSError:
                    # Directory not empty, leave it
                    pass
            
            logger.info(f"Cleanup complete: {cleaned_count} cleaned, {failed_count} failed")
            return failed_count == 0
            
        except Exception as e:
            logger.error(f"Error cleaning up temp XLE files: {e}")
            return False
    
    def cleanup_orphaned_files(self) -> int:
        """
        Clean up orphaned temp files on app startup
        
        Returns:
            Number of files cleaned up
        """
        try:
            registry = self._load_registry()
            cleaned_count = 0
            
            # Check each registry entry
            for file_id, record in list(registry.items()):
                if record['status'] == 'temp':
                    # Check if temp file still exists
                    if not os.path.exists(record['temp_path']):
                        # File is missing, update registry
                        self._update_record_status(file_id, 'cleaned_up')
                        cleaned_count += 1
                    else:
                        # Check if file is old (> 7 days)
                        try:
                            created_at = datetime.fromisoformat(record['created_at'])
                            age_days = (datetime.now() - created_at).days
                            
                            if age_days > 7:
                                # Remove old temp file
                                os.remove(record['temp_path'])
                                self._update_record_status(file_id, 'cleaned_up')
                                cleaned_count += 1
                                logger.info(f"Cleaned up old temp XLE file: {record['temp_path']}")
                        except Exception:
                            # Invalid date, clean it up
                            if os.path.exists(record['temp_path']):
                                os.remove(record['temp_path'])
                            self._update_record_status(file_id, 'cleaned_up')
                            cleaned_count += 1
            
            # Clean up empty directories
            self._cleanup_empty_directories()
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} orphaned temp XLE files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files: {e}")
            return 0
    
    def get_temp_storage_info(self) -> Dict:
        """Get information about temp storage usage"""
        try:
            registry = self._load_registry()
            
            total_files = len(registry)
            temp_files = sum(1 for r in registry.values() if r['status'] == 'temp')
            moved_files = sum(1 for r in registry.values() if r['status'] == 'moved_to_smoo')
            cleaned_files = sum(1 for r in registry.values() if r['status'] == 'cleaned_up')
            
            # Calculate total size of temp files
            total_size = 0
            for record in registry.values():
                if record['status'] == 'temp' and os.path.exists(record['temp_path']):
                    total_size += record['file_size']
            
            return {
                'total_records': total_files,
                'temp_files': temp_files,
                'moved_files': moved_files,
                'cleaned_files': cleaned_files,
                'total_temp_size_mb': round(total_size / (1024 * 1024), 2),
                'temp_base_path': self.temp_xle_base,
                'registry_file': self.registry_file
            }
            
        except Exception as e:
            logger.error(f"Error getting temp storage info: {e}")
            return {'error': str(e)}
    
    def _load_registry(self) -> Dict:
        """Load temp XLE file registry"""
        try:
            if os.path.exists(self.registry_file):
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading temp XLE registry: {e}")
            return {}
    
    def _save_registry(self, registry: Dict) -> bool:
        """Save temp XLE file registry"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            
            # Save atomically
            temp_file = f"{self.registry_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            
            os.replace(temp_file, self.registry_file)
            return True
            
        except Exception as e:
            logger.error(f"Error saving temp XLE registry: {e}")
            return False
    
    def _add_to_registry(self, record: TempXLEFileRecord) -> bool:
        """Add record to registry"""
        try:
            registry = self._load_registry()
            registry[record.file_id] = asdict(record)
            return self._save_registry(registry)
        except Exception as e:
            logger.error(f"Error adding to registry: {e}")
            return False
    
    def _update_record_status(self, file_id: str, new_status: str) -> bool:
        """Update record status in registry"""
        try:
            registry = self._load_registry()
            if file_id in registry:
                registry[file_id]['status'] = new_status
                registry[file_id]['updated_at'] = datetime.now().isoformat()
                return self._save_registry(registry)
            return False
        except Exception as e:
            logger.error(f"Error updating record status: {e}")
            return False
    
    def _generate_file_id(self, project_name: str, device_type: str, 
                         serial_number: str, start_date: datetime) -> str:
        """Generate unique file ID"""
        content = f"{project_name}_{device_type}_{serial_number}_{start_date.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:96] + ext
        
        return filename
    
    def _cleanup_empty_directories(self):
        """Clean up empty directories in temp structure"""
        try:
            for root, dirs, files in os.walk(self.temp_xle_base, topdown=False):
                # Skip the base directory
                if root == self.temp_xle_base:
                    continue
                
                # Try to remove empty directories
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                        logger.debug(f"Removed empty directory: {root}")
                except OSError:
                    # Directory not empty or permission issue
                    pass
        except Exception as e:
            logger.debug(f"Error cleaning up empty directories: {e}")