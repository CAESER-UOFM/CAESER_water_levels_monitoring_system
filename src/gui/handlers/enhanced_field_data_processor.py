#!/usr/bin/env python3
"""
Enhanced Field Data Processor - Complete Integration

This is the main processor that integrates all enhanced field data components:
1. Google Drive SOLINST folder monitoring with date filtering
2. Enhanced XML-based metadata extraction
3. Units-based device type detection
4. Intelligent filename generation
5. Duplicate detection with serial+timerange
6. Temp folder management with atomic operations
7. Hierarchical organization (YYYY-MM/DEVICE_TYPE/)

Implements your professional field data approach:
- Never trust filenames (field conditions create unreliable names)
- Use actual data timestamps (avoid Solinst firmware bugs)
- Units-based device categorization (most reliable method)
- Serial + timerange duplicate detection

@author: Complete professional field data workflow
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Callable, Tuple
from datetime import datetime

from .xle_metadata_extractor import EnhancedXLEMetadataExtractor, XLEMetadata
from .intelligent_filename_generator import IntelligentFilenameGenerator
from .duplicate_detection_system import DuplicateDetectionSystem
from .temp_folder_manager import TempFolderManager
from .google_service_account import GoogleServiceAccountHandler
from .enhanced_field_data_config import ConfigurationManager
from .enhanced_error_recovery import EnhancedErrorRecoverySystem

logger = logging.getLogger(__name__)

class EnhancedFieldDataProcessor:
    """
    Complete enhanced field data processing pipeline
    
    Integrates all professional field data components into a single workflow
    """
    
    def __init__(self, settings_handler, google_service: GoogleServiceAccountHandler, 
                 config_manager: Optional[ConfigurationManager] = None):
        """
        Initialize enhanced field data processor
        
        Args:
            settings_handler: Settings handler instance
            google_service: Google Drive service instance
            config_manager: Optional configuration manager (creates new if None)
        """
        self.settings_handler = settings_handler
        self.google_service = google_service
        
        # Initialize configuration and error recovery systems
        self.config_manager = config_manager or ConfigurationManager()
        self.error_recovery = EnhancedErrorRecoverySystem(self.config_manager)
        
        # Initialize all components with configuration
        self.metadata_extractor = EnhancedXLEMetadataExtractor()
        self.filename_generator = IntelligentFilenameGenerator()
        self.temp_manager = TempFolderManager()
        
        # Initialize consolidated folder and duplicate detector
        self.consolidated_folder = self._get_consolidated_folder_path()
        self.duplicate_detector = DuplicateDetectionSystem(self.consolidated_folder)
        
        # Processing statistics
        self.session_stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'duplicates_detected': 0,
            'errors_encountered': 0,
            'start_time': None,
            'end_time': None,
            'recovery_events': 0,
            'config_version': self.config_manager.config.version
        }
        
        # Check for recovery state
        recovery_state = self.error_recovery.load_recovery_state()
        if recovery_state:
            logger.info("Previous incomplete processing detected - recovery state available")
            self.session_stats['recovery_available'] = True
        
        logger.info(f"Enhanced field data processor initialized (v{self.config_manager.config.version})")
        logger.info(f"Consolidated folder: {self.consolidated_folder}")
        logger.info(f"Configuration: {self.config_manager.config_file}")
    
    def _get_consolidated_folder_path(self) -> str:
        """Get the consolidated folder path from settings"""
        smoo_root = self.settings_handler.get_setting("shared_drive_root", "")
        if smoo_root:
            return os.path.join(smoo_root, "FIELD_DATA_CONSOLIDATED")
        else:
            # Fallback for development/testing
            return os.path.join(os.path.expanduser("~"), "FIELD_DATA_CONSOLIDATED_TEST")
    
    def process_field_data(self, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Main processing workflow - implements your complete field data approach
        
        Args:
            progress_callback: Progress callback function (message, percent)
            
        Returns:
            Processing results dictionary
        """
        results = {
            'success': False,
            'files_processed': 0,
            'files_skipped': 0,
            'duplicates_detected': 0,
            'errors': [],
            'processing_time': 0,
            'new_files': []
        }
        
        start_time = datetime.now()
        self.session_stats['start_time'] = start_time.isoformat()
        
        try:
            logger.info("Starting enhanced field data processing")
            
            if progress_callback:
                progress_callback("Initializing enhanced field data processing...", 0)
            
            # Step 1: Check Google Drive and SMOO access
            if not self._check_system_access():
                raise Exception("System access check failed - cannot access Google Drive or SMOO")
            
            if progress_callback:
                progress_callback("Scanning Google Drive for new files...", 10)
            
            # Step 2: Get new files from Google Drive using date filtering
            files_to_process = self._get_files_to_process()
            
            if not files_to_process:
                logger.info("No new files found to process")
                if progress_callback:
                    progress_callback("No new files found", 100)
                results['success'] = True
                return results
            
            logger.info(f"Found {len(files_to_process)} files to process")
            
            # Step 3: Process files with temp folder management
            with self.temp_manager.create_session_folder("enhanced_field_data") as session_dir:
                processed_files = self._process_files_batch(
                    files_to_process, 
                    session_dir, 
                    progress_callback
                )
                
                results.update(processed_files)
            
            # Step 4: Update tracking and cleanup
            if results['files_processed'] > 0:
                self._update_last_sync_timestamp()
            
            # Final statistics
            end_time = datetime.now()
            self.session_stats['end_time'] = end_time.isoformat()
            results['processing_time'] = (end_time - start_time).total_seconds()
            
            logger.info(f"Processing complete: {results['files_processed']} files processed")
            results['success'] = True
            
            if progress_callback:
                progress_callback(f"Complete: {results['files_processed']} files processed", 100)
            
            return results
            
        except Exception as e:
            logger.error(f"Enhanced field data processing failed: {e}")
            results['errors'].append(str(e))
            
            if progress_callback:
                progress_callback(f"Error: {str(e)}", 100)
            
            return results
    
    def process_with_recovery(self, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Process field data with full error recovery and resilience
        
        Args:
            progress_callback: Progress callback function
            
        Returns:
            Processing results with recovery information
        """
        def processing_operation():
            return self.process_field_data(progress_callback)
        
        # Execute with error recovery
        result, success = self.error_recovery.with_retry(
            processing_operation,
            error_context={
                'operation': 'field_data_processing',
                'consolidated_folder': self.consolidated_folder
            }
        )
        
        if success:
            self.error_recovery.clear_recovery_state()
            return result
        else:
            # Save recovery state for manual intervention
            recovery_state = {
                'operation': 'field_data_processing',
                'data': self.session_stats,
                'failed_files': [],
                'completed_files': []
            }
            self.error_recovery.save_recovery_state(recovery_state)
            
            return {
                'success': False,
                'error': 'Processing failed with error recovery',
                'recovery_state_saved': True,
                'error_statistics': self.error_recovery.get_error_statistics()
            }
    
    def _check_system_access(self) -> bool:
        """Check access to Google Drive and SMOO systems"""
        try:
            # Check Google Drive access
            if not self.google_service.is_authenticated():
                logger.error("Google Drive not authenticated")
                return False
            
            if not self.google_service.check_folder_access():
                logger.error("Cannot access SOLINST folder")
                return False
            
            # Check SMOO access (create consolidated folder if needed)
            consolidated_path = Path(self.consolidated_folder)
            consolidated_path.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = consolidated_path / f"access_test_{int(datetime.now().timestamp())}.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                logger.debug("SMOO write access confirmed")
            except Exception as e:
                logger.error(f"No write access to SMOO: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"System access check failed: {e}")
            return False
    
    def _get_files_to_process(self) -> List[Dict]:
        """Get files from Google Drive that need processing using date filtering"""
        try:
            # Get last sync date for optimization
            last_sync = self.duplicate_detector._get_last_sync_date() if hasattr(self.duplicate_detector, '_get_last_sync_date') else None
            
            # Use Google Drive date filtering for efficiency
            if last_sync:
                logger.info(f"Getting files created after: {last_sync}")
                files = self.google_service.list_xle_files(created_after=last_sync)
            else:
                logger.info("No previous sync found - getting all files")
                files = self.google_service.list_xle_files()
            
            logger.info(f"Found {len(files)} files to evaluate")
            return files
            
        except Exception as e:
            logger.error(f"Error getting files to process: {e}")
            return []
    
    def _process_files_batch(self, files_to_process: List[Dict], 
                           session_dir: Path, 
                           progress_callback: Optional[Callable]) -> Dict:
        """Process a batch of files with comprehensive workflow"""
        
        results = {
            'files_processed': 0,
            'files_skipped': 0,
            'duplicates_detected': 0,
            'errors': [],
            'new_files': []
        }
        
        total_files = len(files_to_process)
        
        for i, file_info in enumerate(files_to_process):
            try:
                # Calculate progress (10% for scanning, 80% for processing, 10% for cleanup)
                base_progress = 10 + int((i / total_files) * 80)
                
                def file_progress(message, percent):
                    if progress_callback:
                        overall_progress = base_progress + int(percent * 0.8 / 100)
                        progress_callback(message, min(overall_progress, 89))
                
                # Process single file
                file_result = self._process_single_file(file_info, session_dir, file_progress)
                
                # Update results
                if file_result['success']:
                    if file_result['action'] == 'processed':
                        results['files_processed'] += 1
                        results['new_files'].append(file_result['final_filename'])
                    elif file_result['action'] == 'skipped':
                        results['files_skipped'] += 1
                    elif file_result['action'] == 'duplicate':
                        results['duplicates_detected'] += 1
                else:
                    results['errors'].append(f"{file_info['name']}: {file_result['error']}")
                
            except Exception as e:
                logger.error(f"Error processing file {file_info['name']}: {e}")
                results['errors'].append(f"{file_info['name']}: {str(e)}")
        
        return results
    
    def _process_single_file(self, file_info: Dict, session_dir: Path, 
                           progress_callback: Optional[Callable]) -> Dict:
        """
        Process a single file through the complete workflow
        
        Your professional approach:
        1. Download to temp
        2. Extract metadata (never trust filename)
        3. Check for duplicates (serial + timerange)
        4. Generate intelligent filename
        5. Move to hierarchical location
        6. Register in duplicate detection
        7. Cleanup temp
        """
        
        result = {
            'success': False,
            'action': None,
            'error': None,
            'final_filename': None,
            'final_path': None
        }
        
        temp_file_path = None
        
        try:
            filename = file_info['name']
            file_id = file_info['id']
            
            # Step 1: Download to temp
            if progress_callback:
                progress_callback(f"Downloading {filename}...", 10)
            
            temp_file_path = self.temp_manager.download_file_to_temp(
                self.google_service, file_info, session_dir, 
                lambda msg, pct: progress_callback(msg, 10 + pct * 0.3) if progress_callback else None
            )
            
            if not temp_file_path:
                raise Exception("Failed to download file")
            
            # Step 2: Extract metadata (never trust filename!)
            if progress_callback:
                progress_callback(f"Extracting metadata from {filename}...", 40)
            
            metadata = self.metadata_extractor.extract_comprehensive_metadata(str(temp_file_path))
            
            if not self.metadata_extractor.validate_metadata(metadata):
                logger.warning(f"Incomplete metadata for {filename}, processing anyway")
            
            # Step 3: Check for duplicates (serial + timerange)
            if progress_callback:
                progress_callback(f"Checking for duplicates...", 50)
            
            duplicate_check = self.duplicate_detector.check_for_duplicate(
                metadata, file_id, str(temp_file_path)
            )
            
            if duplicate_check['is_duplicate']:
                logger.info(f"Duplicate detected: {filename} - {duplicate_check['recommendation']}")
                result.update({
                    'success': True,
                    'action': 'duplicate',
                    'final_filename': filename
                })
                return result
            
            # Step 4: Generate intelligent filename (professional naming)
            if progress_callback:
                progress_callback(f"Generating intelligent filename...", 60)
            
            intelligent_filename = self.filename_generator.generate_intelligent_filename(
                metadata, filename
            )
            
            # Step 5: Determine target location (hierarchical organization)
            target_folder = self._get_target_folder(metadata)
            final_path = Path(target_folder) / intelligent_filename
            
            # Step 6: Move to final location atomically
            if progress_callback:
                progress_callback(f"Moving to final location...", 80)
            
            if not self.temp_manager.atomic_move_to_final(temp_file_path, final_path):
                raise Exception("Failed to move file to final location")
            
            # Step 7: Register in duplicate detection system
            if progress_callback:
                progress_callback(f"Registering processed file...", 90)
            
            registration_success = self.duplicate_detector.register_processed_file(
                metadata, file_id, str(final_path), filename, intelligent_filename, 
                int(file_info.get('size', 0)), str(temp_file_path)
            )
            
            if not registration_success:
                logger.warning(f"Failed to register {intelligent_filename} in duplicate detection")
            
            result.update({
                'success': True,
                'action': 'processed',
                'final_filename': intelligent_filename,
                'final_path': str(final_path)
            })
            
            logger.info(f"Successfully processed: {filename} → {intelligent_filename}")
            
            if progress_callback:
                progress_callback(f"Completed: {intelligent_filename}", 100)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {file_info['name']}: {e}")
            result.update({
                'success': False,
                'error': str(e)
            })
            
            # Cleanup temp file on error
            if temp_file_path and temp_file_path.exists():
                self.temp_manager.cleanup_file(temp_file_path)
            
            return result
    
    def _get_target_folder(self, metadata: XLEMetadata) -> str:
        """
        Get target folder for hierarchical organization: YYYY-MM/DEVICE_TYPE/
        
        Args:
            metadata: Extracted metadata
            
        Returns:
            Target folder path
        """
        try:
            # Use end date for organization (when data collection ended)
            if metadata.actual_end_date:
                end_date = datetime.strptime(metadata.actual_end_date, '%Y-%m-%d')
                year_month = end_date.strftime('%Y-%m')
            else:
                # Fallback to current month
                year_month = datetime.now().strftime('%Y-%m')
            
            # Get device category for hierarchical organization
            device_category = metadata.device_type
            if device_category == 'UNKNOWN_TYPE':
                device_category = 'UNKNOWN_TYPE'
            
            target_folder = os.path.join(
                self.consolidated_folder,
                year_month,
                device_category
            )
            
            logger.debug(f"Target folder: {os.path.relpath(target_folder, self.consolidated_folder)}")
            return target_folder
            
        except Exception as e:
            logger.error(f"Error determining target folder: {e}")
            # Fallback to current month/unknown type
            current_month = datetime.now().strftime('%Y-%m')
            return os.path.join(self.consolidated_folder, current_month, 'UNKNOWN_TYPE')
    
    def _update_last_sync_timestamp(self):
        """Update last sync timestamp for future optimizations"""
        try:
            sync_file = os.path.join(self.consolidated_folder, '.last_sync')
            os.makedirs(self.consolidated_folder, exist_ok=True)
            
            current_time = datetime.now().isoformat()
            with open(sync_file, 'w') as f:
                f.write(current_time)
            
            logger.debug(f"Updated last sync timestamp: {current_time}")
            
        except Exception as e:
            logger.error(f"Error updating last sync timestamp: {e}")
    
    def get_processing_statistics(self) -> Dict:
        """Get comprehensive processing statistics"""
        try:
            stats = {
                'session_stats': self.session_stats.copy(),
                'duplicate_detector_stats': self.duplicate_detector.get_processing_statistics(),
                'temp_manager_stats': self.temp_manager.get_session_statistics(),
                'consolidated_folder': self.consolidated_folder
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting processing statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_and_maintenance(self) -> Dict:
        """Perform cleanup and maintenance operations"""
        try:
            maintenance_results = {
                'orphaned_temp_cleaned': 0,
                'invalid_records_cleaned': 0,
                'maintenance_time': datetime.now().isoformat()
            }
            
            # Cleanup orphaned temp folders
            maintenance_results['orphaned_temp_cleaned'] = self.temp_manager.cleanup_orphaned_temp_folders()
            
            # Cleanup invalid registry records
            maintenance_results['invalid_records_cleaned'] = self.duplicate_detector.cleanup_invalid_records()
            
            logger.info(f"Maintenance completed: {maintenance_results}")
            return maintenance_results
            
        except Exception as e:
            logger.error(f"Error during maintenance: {e}")
            return {'error': str(e)}
    
    def emergency_stop(self):
        """Emergency stop and cleanup"""
        try:
            logger.warning("Emergency stop initiated")
            
            # Emergency cleanup of temp manager
            self.temp_manager.emergency_cleanup_all()
            
            # Save duplicate detector state
            self.duplicate_detector.save_registry()
            
            logger.info("Emergency stop completed")
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")

# Backward compatibility wrapper
class HybridFieldDataConsolidator(EnhancedFieldDataProcessor):
    """
    Backward compatibility wrapper to maintain existing interface
    """
    
    def __init__(self, drive_service, settings_handler):
        """Maintain backward compatibility with existing code"""
        super().__init__(settings_handler, drive_service)
        self.drive_service = drive_service  # Maintain old attribute name
    
    def consolidate_field_data(self, progress_callback: Optional[Callable] = None) -> bool:
        """Maintain backward compatibility with existing interface"""
        try:
            results = self.process_field_data(progress_callback)
            return results['success']
        except Exception as e:
            logger.error(f"Error in backward compatibility method: {e}")
            return False