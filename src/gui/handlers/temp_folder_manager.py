#!/usr/bin/env python3
"""
Temp Folder Manager for Enhanced Field Data Processing

Implements robust temporary folder management for the field data workflow:
1. Download files from Google Drive to temp location
2. Process files with metadata extraction and organization
3. Move to final SMOO consolidated location with intelligent naming
4. Clean up temp folder automatically
5. Handle errors and ensure no temp files are left behind

Cross-platform compatible (Mac development, Windows deployment)
Thread-safe and atomic operations

@author: Professional field data workflow implementation
"""

import os
import shutil
import tempfile
import logging
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Callable, Tuple
from contextlib import contextmanager
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class TempFolderManager:
    """
    Professional temporary folder management for field data processing
    """
    
    def __init__(self, base_temp_dir: Optional[str] = None):
        """
        Initialize temp folder manager
        
        Args:
            base_temp_dir: Base directory for temp folders (optional)
        """
        self.base_temp_dir = base_temp_dir or tempfile.gettempdir()
        self.current_session_dir: Optional[Path] = None
        self.session_lock = threading.Lock()
        self.cleanup_registry: List[Path] = []
        
        # Track active downloads and processing
        self.active_files: Dict[str, Dict] = {}
        self.files_lock = threading.Lock()
        
        logger.debug(f"TempFolderManager initialized with base: {self.base_temp_dir}")
    
    @contextmanager
    def create_session_folder(self, session_name: str = "field_data_sync"):
        """
        Create a temporary session folder with automatic cleanup
        
        Args:
            session_name: Name prefix for the session folder
            
        Yields:
            Path to the session directory
        """
        session_dir = None
        try:
            with self.session_lock:
                # Create unique session folder
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                session_dir = Path(tempfile.mkdtemp(
                    prefix=f"{session_name}_{timestamp}_",
                    dir=self.base_temp_dir
                ))
                
                self.current_session_dir = session_dir
                self.cleanup_registry.append(session_dir)
                
                logger.info(f"Created session folder: {session_dir}")
            
            # Create subdirectories for organization
            downloads_dir = session_dir / "downloads"
            processing_dir = session_dir / "processing"
            
            downloads_dir.mkdir(exist_ok=True)
            processing_dir.mkdir(exist_ok=True)
            
            # Create session info file
            session_info = {
                'session_name': session_name,
                'created_at': datetime.now().isoformat(),
                'pid': os.getpid(),
                'status': 'active'
            }
            
            with open(session_dir / '.session_info.json', 'w') as f:
                json.dump(session_info, f, indent=2)
            
            yield session_dir
            
        except Exception as e:
            logger.error(f"Error in session folder management: {e}")
            raise
        finally:
            # Cleanup session folder
            if session_dir and session_dir.exists():
                self._cleanup_session_folder(session_dir)
    
    def download_file_to_temp(self, google_service, file_info: Dict, 
                             session_dir: Path, progress_callback: Optional[Callable] = None) -> Optional[Path]:
        """
        Download a file from Google Drive to temp location
        
        Args:
            google_service: Google Drive service instance
            file_info: Google Drive file information
            session_dir: Session directory path
            progress_callback: Progress callback function
            
        Returns:
            Path to downloaded file or None if failed
        """
        file_id = file_info['id']
        filename = file_info['name']
        
        try:
            with self.files_lock:
                # Track active download
                self.active_files[file_id] = {
                    'filename': filename,
                    'status': 'downloading',
                    'start_time': datetime.now().isoformat(),
                    'temp_path': None
                }
            
            if progress_callback:
                progress_callback(f"Downloading {filename}...", 0)
            
            # Create temp file in downloads directory
            downloads_dir = session_dir / "downloads"
            temp_file = downloads_dir / f"{file_id}_{filename}"
            
            # Download using Google Drive service
            downloaded_path = google_service.download_file(file_id, str(temp_file))
            
            if not downloaded_path or not os.path.exists(downloaded_path):
                raise Exception(f"Download failed - file not found at {downloaded_path}")
            
            # Verify file size
            expected_size = int(file_info.get('size', 0))
            actual_size = os.path.getsize(downloaded_path)
            
            if expected_size > 0 and abs(expected_size - actual_size) > 1024:  # Allow 1KB tolerance
                logger.warning(f"Size mismatch: expected {expected_size}, got {actual_size}")
            
            # Update tracking
            with self.files_lock:
                self.active_files[file_id].update({
                    'status': 'downloaded',
                    'temp_path': temp_file,
                    'size': actual_size,
                    'download_time': datetime.now().isoformat()
                })
            
            if progress_callback:
                progress_callback(f"Downloaded {filename}", 100)
            
            logger.info(f"Downloaded to temp: {filename} → {temp_file}")
            return Path(downloaded_path)
            
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            
            # Update tracking
            with self.files_lock:
                if file_id in self.active_files:
                    self.active_files[file_id].update({
                        'status': 'error',
                        'error': str(e),
                        'error_time': datetime.now().isoformat()
                    })
            
            if progress_callback:
                progress_callback(f"Error downloading {filename}", 100)
            
            return None
    
    def move_to_processing(self, temp_file_path: Path, session_dir: Path) -> Path:
        """
        Move file from downloads to processing directory
        
        Args:
            temp_file_path: Current temp file path
            session_dir: Session directory
            
        Returns:
            New path in processing directory
        """
        try:
            processing_dir = session_dir / "processing"
            processing_path = processing_dir / temp_file_path.name
            
            # Move file atomically
            shutil.move(str(temp_file_path), str(processing_path))
            
            logger.debug(f"Moved to processing: {temp_file_path.name}")
            return processing_path
            
        except Exception as e:
            logger.error(f"Error moving to processing: {e}")
            raise
    
    def atomic_move_to_final(self, temp_file_path: Path, final_path: Path) -> bool:
        """
        Atomically move file from temp to final location
        
        Args:
            temp_file_path: Temporary file path
            final_path: Final destination path
            
        Returns:
            True if successful
        """
        try:
            # Ensure target directory exists
            final_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if target already exists
            if final_path.exists():
                # Create backup name
                timestamp = datetime.now().strftime("%H%M%S")
                backup_name = f"{final_path.stem}_CONFLICT_{timestamp}{final_path.suffix}"
                final_path = final_path.parent / backup_name
                logger.warning(f"Target exists, using backup name: {backup_name}")
            
            # Atomic move
            shutil.move(str(temp_file_path), str(final_path))
            
            logger.info(f"Moved to final location: {final_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving to final location: {e}")
            return False
    
    def cleanup_file(self, file_path: Path) -> bool:
        """
        Safely cleanup a temp file
        
        Args:
            file_path: Path to file to cleanup
            
        Returns:
            True if successful
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temp file: {file_path}")
                return True
            return True  # Already gone
            
        except Exception as e:
            logger.error(f"Error cleaning up {file_path}: {e}")
            return False
    
    def _cleanup_session_folder(self, session_dir: Path):
        """Clean up session folder and all contents"""
        try:
            # Update session info
            session_info_file = session_dir / '.session_info.json'
            if session_info_file.exists():
                try:
                    with open(session_info_file, 'r') as f:
                        session_info = json.load(f)
                    
                    session_info.update({
                        'status': 'cleanup',
                        'cleanup_time': datetime.now().isoformat()
                    })
                    
                    with open(session_info_file, 'w') as f:
                        json.dump(session_info, f, indent=2)
                except:
                    pass  # Non-critical
            
            # Remove all contents
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
                logger.info(f"Cleaned up session folder: {session_dir}")
            
            # Remove from cleanup registry
            with self.session_lock:
                if session_dir in self.cleanup_registry:
                    self.cleanup_registry.remove(session_dir)
                    
                if self.current_session_dir == session_dir:
                    self.current_session_dir = None
                    
        except Exception as e:
            logger.error(f"Error cleaning up session folder {session_dir}: {e}")
    
    def get_session_statistics(self) -> Dict:
        """Get statistics about current session"""
        try:
            stats = {
                'active_session': str(self.current_session_dir) if self.current_session_dir else None,
                'active_files_count': len(self.active_files),
                'files_by_status': {},
                'cleanup_registry_size': len(self.cleanup_registry)
            }
            
            # Analyze file statuses
            with self.files_lock:
                for file_info in self.active_files.values():
                    status = file_info.get('status', 'unknown')
                    stats['files_by_status'][status] = stats['files_by_status'].get(status, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_orphaned_temp_folders(self, max_age_hours: int = 24) -> int:
        """
        Clean up orphaned temp folders older than specified age
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of folders cleaned up
        """
        cleaned_count = 0
        
        try:
            base_path = Path(self.base_temp_dir)
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            # Look for temp folders with our naming pattern
            for item in base_path.glob("field_data_sync_*"):
                if not item.is_dir():
                    continue
                
                try:
                    # Check age
                    folder_age = current_time - item.stat().st_mtime
                    
                    if folder_age > max_age_seconds:
                        # Check if it's from a dead process
                        session_info_file = item / '.session_info.json'
                        is_orphaned = True
                        
                        if session_info_file.exists():
                            try:
                                with open(session_info_file, 'r') as f:
                                    session_info = json.load(f)
                                
                                # Check if process is still running
                                pid = session_info.get('pid')
                                if pid and self._is_process_running(pid):
                                    is_orphaned = False
                                    
                            except:
                                pass  # Treat as orphaned if can't read
                        
                        if is_orphaned:
                            shutil.rmtree(item, ignore_errors=True)
                            logger.info(f"Cleaned up orphaned temp folder: {item}")
                            cleaned_count += 1
                            
                except Exception as e:
                    logger.debug(f"Error checking temp folder {item}: {e}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} orphaned temp folders")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned temp folders: {e}")
            return 0
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running"""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            # Fallback for systems without psutil
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    
    def emergency_cleanup_all(self):
        """Emergency cleanup of all managed temp folders"""
        try:
            logger.warning("Emergency cleanup initiated")
            
            # Clear active files tracking
            with self.files_lock:
                self.active_files.clear()
            
            # Cleanup all registered folders
            with self.session_lock:
                for session_dir in self.cleanup_registry.copy():
                    try:
                        if session_dir.exists():
                            shutil.rmtree(session_dir, ignore_errors=True)
                            logger.info(f"Emergency cleanup: {session_dir}")
                    except:
                        pass
                
                self.cleanup_registry.clear()
                self.current_session_dir = None
            
            logger.info("Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in emergency cleanup: {e}")

class SafeTempFileHandler:
    """
    Safe temporary file handler with automatic cleanup
    """
    
    def __init__(self, temp_manager: TempFolderManager):
        self.temp_manager = temp_manager
        self.managed_files: List[Path] = []
    
    @contextmanager
    def temp_file(self, suffix: str = '.tmp', prefix: str = 'safe_'):
        """
        Create a temporary file with automatic cleanup
        
        Args:
            suffix: File suffix
            prefix: File prefix
            
        Yields:
            Path to temporary file
        """
        temp_file = None
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(fd)  # Close file descriptor
            
            temp_file = Path(temp_path)
            self.managed_files.append(temp_file)
            
            yield temp_file
            
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    if temp_file in self.managed_files:
                        self.managed_files.remove(temp_file)
                except:
                    pass
    
    def cleanup_all(self):
        """Cleanup all managed temp files"""
        for temp_file in self.managed_files.copy():
            try:
                if temp_file.exists():
                    temp_file.unlink()
                self.managed_files.remove(temp_file)
            except:
                pass