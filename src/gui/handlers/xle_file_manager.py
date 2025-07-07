"""
XLE File Manager for Google Drive Integration
Handles XLE file tracking, organization, and upload to Google Drive project folders.
"""

import os
import json
import logging
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class XLEFileManager:
    """Manages XLE files and their synchronization with Google Drive."""
    
    def __init__(self, database_manager, drive_service, settings_handler):
        """
        Initialize the XLE File Manager.
        
        Args:
            database_manager: DatabaseManager instance
            drive_service: GoogleDriveService instance  
            settings_handler: SettingsHandler instance
        """
        self.db_manager = database_manager
        self.drive_service = drive_service
        self.settings_handler = settings_handler
        
    def track_xle_file(self, file_path: str, file_type: str, serial_number: str, 
                      well_number: str = None, start_date: str = None, 
                      end_date: str = None, project_name: str = None) -> int:
        """
        Track an XLE file in the database for future upload.
        
        Args:
            file_path: Local path to the XLE file
            file_type: 'transducer' or 'barologger'
            serial_number: Serial number of the device
            well_number: Well number (for transducers)
            start_date: Start date of data in file
            end_date: End date of data in file
            project_name: Name of the project
            
        Returns:
            ID of the tracked file record
        """
        logger.info(f"XLE_TRACK: Attempting to track XLE file: {file_path}")
        logger.info(f"XLE_TRACK: File type: {file_type}, Serial: {serial_number}, Well: {well_number}, Project: {project_name}")
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"XLE file not found: {file_path}")
            
            # Calculate file metadata
            file_size = os.path.getsize(file_path)
            file_hash = self._calculate_file_hash(file_path)
            file_name = os.path.basename(file_path)
            
            # Insert into database
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if file already tracked
                cursor.execute("""
                    SELECT id FROM xle_files 
                    WHERE file_hash = ? OR (file_path = ? AND file_size = ?)
                """, (file_hash, file_path, file_size))
                
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"XLE file already tracked: {file_name}")
                    return existing[0]
                
                # Insert new tracking record
                cursor.execute("""
                    INSERT INTO xle_files 
                    (file_path, file_name, file_type, serial_number, well_number,
                     start_date, end_date, file_size, file_hash, project_name,
                     upload_status, local_import_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                """, (
                    file_path, file_name, file_type, serial_number, well_number,
                    start_date, end_date, file_size, file_hash, project_name
                ))
                
                file_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Tracked XLE file: {file_name} (ID: {file_id})")
                return file_id
                
        except Exception as e:
            logger.error(f"Error tracking XLE file {file_path}: {e}")
            raise
    
    def update_water_level_xle_source(self, file_path: str, serial_number: str, 
                                    start_time: str, end_time: str):
        """
        Update water level readings with their source XLE file.
        
        Args:
            file_path: Path to the XLE file
            serial_number: Serial number of transducer
            start_time: Start time of data import
            end_time: End time of data import
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update water level readings with source file
                cursor.execute("""
                    UPDATE water_level_readings 
                    SET source_xle_file = ?
                    WHERE serial_number = ? 
                    AND timestamp_utc BETWEEN ? AND ?
                    AND source_xle_file IS NULL
                """, (file_path, serial_number, start_time, end_time))
                
                updated_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Updated {updated_count} water level readings with XLE source: {os.path.basename(file_path)}")
                
        except Exception as e:
            logger.error(f"Error updating water level XLE source: {e}")
            raise
    
    def get_pending_uploads(self, project_name: str = None) -> List[Dict]:
        """
        Get list of XLE files pending upload to Google Drive.
        
        Args:
            project_name: Filter by project name (optional)
            
        Returns:
            List of file records pending upload
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if project_name:
                    cursor.execute("""
                        SELECT * FROM xle_files 
                        WHERE upload_status = 'pending' AND project_name = ?
                        ORDER BY local_import_time
                    """, (project_name,))
                else:
                    cursor.execute("""
                        SELECT * FROM xle_files 
                        WHERE upload_status = 'pending'
                        ORDER BY local_import_time
                    """)
                
                columns = [desc[0] for desc in cursor.description]
                files = []
                
                for row in cursor.fetchall():
                    files.append(dict(zip(columns, row)))
                
                return files
                
        except Exception as e:
            logger.error(f"Error getting pending uploads: {e}")
            return []
    
    def create_project_xle_folders(self, project_name: str) -> Dict[str, str]:
        """
        Create XLE file folder structure in Google Drive for a project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dictionary with folder IDs for different XLE file types
        """
        try:
            service = self.drive_service.get_service()
            if not service:
                raise Exception("Google Drive service not available")
            
            # Get projects folder ID
            projects_folder_id = self.settings_handler.get_setting(
                "google_drive_projects_folder_id", 
                "1JjiXRblLAf6rdhiOzrAaYik8bjNpBc9s"
            )
            
            # Find or create project folder
            project_folder_id = self._find_or_create_folder(
                service, project_name, projects_folder_id
            )
            
            # Create XLE_Files folder in project
            xle_main_folder_id = self._find_or_create_folder(
                service, "XLE_Files", project_folder_id
            )
            
            # Create subfolders for different file types
            transducers_folder_id = self._find_or_create_folder(
                service, "transducers", xle_main_folder_id
            )
            
            barologgers_folder_id = self._find_or_create_folder(
                service, "barologgers", xle_main_folder_id
            )
            
            folder_structure = {
                'project': project_folder_id,
                'xle_main': xle_main_folder_id,
                'transducers': transducers_folder_id,
                'barologgers': barologgers_folder_id
            }
            
            logger.info(f"Created XLE folder structure for project: {project_name}")
            return folder_structure
            
        except Exception as e:
            logger.error(f"Error creating project XLE folders: {e}")
            raise
    
    def upload_xle_file(self, file_record: Dict, progress_callback=None) -> bool:
        """
        Upload an XLE file to Google Drive.
        
        Args:
            file_record: File record from database
            progress_callback: Progress callback function
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            file_path = file_record['file_path']
            project_name = file_record['project_name']
            file_type = file_record['file_type']
            file_id = file_record['id']
            
            if not os.path.exists(file_path):
                logger.error(f"XLE file not found for upload: {file_path}")
                self._update_upload_status(file_id, 'failed', 'File not found')
                return False
            
            # Update status to uploading
            self._update_upload_status(file_id, 'uploading')
            
            if progress_callback:
                progress_callback(10, "Creating folder structure...")
            
            # Create folder structure
            folders = self.create_project_xle_folders(project_name)
            
            # Determine target folder
            if file_type == 'transducer':
                target_folder_id = folders['transducers']
                # Create well-specific subfolder
                well_number = file_record.get('well_number')
                if well_number:
                    service = self.drive_service.get_service()
                    target_folder_id = self._find_or_create_folder(
                        service, well_number, target_folder_id
                    )
            else:  # barologger
                target_folder_id = folders['barologgers']
                # Create serial-specific subfolder  
                serial_number = file_record.get('serial_number')
                if serial_number:
                    service = self.drive_service.get_service()
                    target_folder_id = self._find_or_create_folder(
                        service, serial_number, target_folder_id
                    )
            
            if progress_callback:
                progress_callback(30, "Uploading file...")
            
            # Upload the file
            cloud_file_id = self._upload_file_to_drive(
                file_path, target_folder_id, progress_callback
            )
            
            if cloud_file_id:
                # Update database with successful upload
                self._update_upload_status(
                    file_id, 'uploaded', None, cloud_file_id, target_folder_id
                )
                
                if progress_callback:
                    progress_callback(100, "Upload completed successfully")
                
                logger.info(f"Successfully uploaded XLE file: {file_record['file_name']}")
                return True
            else:
                self._update_upload_status(file_id, 'failed', 'Upload failed')
                return False
                
        except Exception as e:
            logger.error(f"Error uploading XLE file: {e}")
            if 'file_id' in locals():
                self._update_upload_status(file_id, 'failed', str(e))
            return False
    
    def upload_project_xle_files(self, project_name: str, progress_callback=None) -> Dict:
        """
        Upload all pending XLE files for a project.
        
        Args:
            project_name: Name of the project
            progress_callback: Progress callback function
            
        Returns:
            Summary of upload results
        """
        try:
            pending_files = self.get_pending_uploads(project_name)
            
            if not pending_files:
                logger.info(f"No pending XLE files for project: {project_name}")
                return {'success': 0, 'failed': 0, 'total': 0}
            
            logger.info(f"Uploading {len(pending_files)} XLE files for project: {project_name}")
            
            success_count = 0
            failed_count = 0
            
            for i, file_record in enumerate(pending_files):
                if progress_callback:
                    overall_progress = int((i / len(pending_files)) * 100)
                    progress_callback(overall_progress, f"Uploading file {i+1}/{len(pending_files)}")
                
                success = self.upload_xle_file(file_record)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            
            results = {
                'success': success_count,
                'failed': failed_count,
                'total': len(pending_files)
            }
            
            if progress_callback:
                progress_callback(100, f"Upload complete: {success_count} success, {failed_count} failed")
            
            logger.info(f"XLE upload summary for {project_name}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error uploading project XLE files: {e}")
            return {'success': 0, 'failed': 0, 'total': 0, 'error': str(e)}
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for duplicate detection."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _find_or_create_folder(self, service, folder_name: str, parent_id: str) -> str:
        """Find existing folder or create new one in Google Drive."""
        try:
            # Search for existing folder
            query = f"name = '{folder_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created Google Drive folder: {folder_name}")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error finding/creating folder {folder_name}: {e}")
            raise
    
    def _upload_file_to_drive(self, file_path: str, folder_id: str, progress_callback=None) -> Optional[str]:
        """Upload file to Google Drive folder."""
        try:
            service = self.drive_service.get_service()
            file_name = os.path.basename(file_path)
            
            # Check if file already exists
            query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            
            existing_files = results.get('files', [])
            if existing_files:
                logger.info(f"File already exists in Google Drive: {file_name}")
                return existing_files[0]['id']
            
            # Upload new file
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            request = service.files().create(body=file_metadata, media_body=media, fields='id')
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress = int(status.progress() * 70) + 30  # 30-100% range
                    progress_callback(progress, f"Uploading {file_name}...")
            
            return response.get('id')
            
        except HttpError as e:
            logger.error(f"HTTP error uploading file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return None
    
    def _update_upload_status(self, file_id: int, status: str, error: str = None, 
                            cloud_file_id: str = None, cloud_folder_id: str = None):
        """Update upload status in database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if status == 'uploaded':
                    cursor.execute("""
                        UPDATE xle_files 
                        SET upload_status = ?, cloud_file_id = ?, cloud_folder_id = ?,
                            upload_timestamp = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, cloud_file_id, cloud_folder_id, file_id))
                else:
                    cursor.execute("""
                        UPDATE xle_files 
                        SET upload_status = ?, upload_error = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, error, file_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating upload status: {e}")
    
    def get_upload_summary(self, project_name: str = None) -> Dict:
        """Get summary of XLE file upload status."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if project_name:
                    cursor.execute("""
                        SELECT upload_status, COUNT(*) as count
                        FROM xle_files 
                        WHERE project_name = ?
                        GROUP BY upload_status
                    """, (project_name,))
                else:
                    cursor.execute("""
                        SELECT upload_status, COUNT(*) as count
                        FROM xle_files 
                        GROUP BY upload_status
                    """)
                
                summary = {}
                for status, count in cursor.fetchall():
                    summary[status] = count
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting upload summary: {e}")
            return {}
    
    def rebuild_tracking_from_database(self, project_name: str = None) -> int:
        """
        Rebuild XLE file tracking from database after loading a draft.
        Validates file paths and updates tracking for files that still exist.
        
        Args:
            project_name: Optional project name to rebuild tracking for
            
        Returns:
            Number of files successfully rebuilt
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Enhanced logging to debug project name issues
                logger.info(f"XLE_REBUILD: Starting rebuild for project_name='{project_name}'")
                
                # First, let's see what projects we have in the database
                cursor.execute("SELECT DISTINCT project_name FROM xle_files")
                projects_in_db = [row[0] for row in cursor.fetchall()]
                logger.info(f"XLE_REBUILD: Projects found in xle_files table: {projects_in_db}")
                
                # Get all tracked XLE files from database
                if project_name:
                    # Try exact match first
                    cursor.execute("""
                        SELECT id, file_path, file_type, serial_number, well_number, 
                               start_date, end_date, project_name, upload_status
                        FROM xle_files 
                        WHERE project_name = ? AND upload_status != 'uploaded'
                        ORDER BY created_at
                    """, (project_name,))
                    tracked_files = cursor.fetchall()
                    logger.info(f"XLE_REBUILD: Found {len(tracked_files)} files for exact project match: '{project_name}'")
                    
                    # If no exact match, try case-insensitive search
                    if not tracked_files:
                        cursor.execute("""
                            SELECT id, file_path, file_type, serial_number, well_number, 
                                   start_date, end_date, project_name, upload_status
                            FROM xle_files 
                            WHERE LOWER(project_name) = LOWER(?) AND upload_status != 'uploaded'
                            ORDER BY created_at
                        """, (project_name,))
                        tracked_files = cursor.fetchall()
                        logger.info(f"XLE_REBUILD: Found {len(tracked_files)} files for case-insensitive project match: '{project_name}'")
                    
                    # If still no match, try partial match (maybe project name has extra characters)
                    if not tracked_files:
                        cursor.execute("""
                            SELECT id, file_path, file_type, serial_number, well_number, 
                                   start_date, end_date, project_name, upload_status
                            FROM xle_files 
                            WHERE project_name LIKE ? AND upload_status != 'uploaded'
                            ORDER BY created_at
                        """, (f"%{project_name}%",))
                        tracked_files = cursor.fetchall()
                        logger.info(f"XLE_REBUILD: Found {len(tracked_files)} files for partial project match: '{project_name}'")
                        
                        if tracked_files:
                            found_projects = set(row[7] for row in tracked_files)
                            logger.info(f"XLE_REBUILD: Partial matches found in projects: {found_projects}")
                else:
                    cursor.execute("""
                        SELECT id, file_path, file_type, serial_number, well_number, 
                               start_date, end_date, project_name, upload_status
                        FROM xle_files 
                        WHERE upload_status != 'uploaded'
                        ORDER BY created_at
                    """)
                    tracked_files = cursor.fetchall()
                    logger.info(f"XLE_REBUILD: Found {len(tracked_files)} tracked XLE files (all projects)")
                
                logger.info(f"XLE_REBUILD: Total tracked files found: {len(tracked_files)}")
                
                # Debug: Show what we found
                if tracked_files:
                    for file_record in tracked_files:
                        file_id, file_path, file_type, serial_number, well_number, start_date, end_date, proj_name, upload_status = file_record
                        logger.debug(f"  - ID {file_id}: {file_type} {serial_number}, path: {file_path}, status: {upload_status}")
                else:
                    logger.warning(f"No tracked XLE files found in database for project: {project_name}")
                    # Let's also check if there are ANY xle_files records at all
                    cursor.execute("SELECT COUNT(*) FROM xle_files")
                    total_count = cursor.fetchone()[0]
                    logger.info(f"Total XLE file records in database: {total_count}")
                    
                    if total_count > 0:
                        # Show what we have
                        cursor.execute("""
                            SELECT project_name, upload_status, COUNT(*) 
                            FROM xle_files 
                            GROUP BY project_name, upload_status
                        """)
                        breakdown = cursor.fetchall()
                        logger.info("XLE files breakdown by project and status:")
                        for proj, status, count in breakdown:
                            logger.info(f"  - Project: {proj}, Status: {status}, Count: {count}")
                
                if not tracked_files:
                    return 0
                
                rebuilt_count = 0
                missing_files = []
                
                for file_record in tracked_files:
                    file_id, file_path, file_type, serial_number, well_number, start_date, end_date, proj_name, upload_status = file_record
                    
                    # Check if file still exists at original path
                    if os.path.exists(file_path):
                        logger.debug(f"✓ XLE file exists: {file_path}")
                        rebuilt_count += 1
                        continue
                    
                    # Try to find file in project's import directory structure
                    potential_paths = self._find_potential_file_paths(
                        file_path, file_type, serial_number, proj_name
                    )
                    
                    found_path = None
                    for potential_path in potential_paths:
                        if os.path.exists(potential_path):
                            found_path = potential_path
                            break
                    
                    if found_path:
                        # Update database with new path
                        cursor.execute("""
                            UPDATE xle_files 
                            SET file_path = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (found_path, file_id))
                        logger.info(f"✓ Updated XLE file path: {os.path.basename(file_path)} -> {found_path}")
                        rebuilt_count += 1
                    else:
                        missing_files.append({
                            'id': file_id,
                            'original_path': file_path,
                            'serial_number': serial_number,
                            'file_type': file_type
                        })
                        logger.warning(f"✗ XLE file not found: {file_path}")
                
                # Commit any path updates
                conn.commit()
                
                if missing_files:
                    logger.warning(f"Could not locate {len(missing_files)} XLE files. They may need to be re-imported:")
                    for missing in missing_files:
                        logger.warning(f"  - {missing['file_type']} {missing['serial_number']}: {os.path.basename(missing['original_path'])}")
                
                logger.info(f"Rebuilt tracking for {rebuilt_count}/{len(tracked_files)} XLE files")
                return rebuilt_count
                
        except Exception as e:
            logger.error(f"Error rebuilding XLE tracking from database: {e}")
            return 0
    
    def _find_potential_file_paths(self, original_path: str, file_type: str, serial_number: str, project_name: str) -> List[str]:
        """
        Find potential paths where an XLE file might be located based on the import directory structure.
        
        Args:
            original_path: Original file path from database
            file_type: 'transducer' or 'barologger'
            serial_number: Device serial number
            project_name: Project name
            
        Returns:
            List of potential file paths to check
        """
        potential_paths = []
        
        try:
            # Get XLE import directory from settings
            app_dir = Path(__file__).parent.parent.parent.parent
            xle_import_base = Path(self.settings_handler.get_setting("xle_import_directory", str(app_dir / "imported_xle_files")))
            
            # Original filename
            original_filename = os.path.basename(original_path)
            
            # Path 1: Project-specific import directory structure
            if project_name:
                if file_type == 'barologger':
                    potential_path = xle_import_base / project_name / "barologgers" / serial_number / original_filename
                else:  # transducer
                    potential_path = xle_import_base / project_name / "transducers" / serial_number / original_filename
                potential_paths.append(str(potential_path))
            
            # Path 2: Base import directory structure (no project name)
            if file_type == 'barologger':
                potential_path = xle_import_base / "barologgers" / serial_number / original_filename
            else:  # transducer  
                potential_path = xle_import_base / "transducers" / serial_number / original_filename
            potential_paths.append(str(potential_path))
            
            # Path 3: Check if file exists in any subdirectory with matching filename
            if xle_import_base.exists():
                for file_path in xle_import_base.rglob(original_filename):
                    if str(file_path) not in potential_paths:
                        potential_paths.append(str(file_path))
            
        except Exception as e:
            logger.error(f"Error finding potential file paths: {e}")
        
        return potential_paths