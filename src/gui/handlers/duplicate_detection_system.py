#!/usr/bin/env python3
"""
Duplicate Detection System for Field Data

Implements professional duplicate detection logic:
- Use serial number + time range for unique identification
- Handle Google Drive re-uploads (different file IDs, same content)
- Track processed files to avoid re-processing
- Support overlapping time ranges detection
- Cross-platform persistent storage

Key principle: Metadata is truth, not filename or Google Drive file ID

@author: Professional field data workflow implementation
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from .xle_metadata_extractor import XLEMetadata

logger = logging.getLogger(__name__)

@dataclass
class ProcessedFileRecord:
    """Record of a processed file for duplicate detection"""
    duplicate_key: str          # serial_start_end unique identifier
    google_drive_id: str        # Google Drive file ID
    processed_date: str         # When we processed it
    consolidated_path: str      # Where we stored it in SMOO
    original_filename: str      # Original Google Drive filename
    intelligent_filename: str  # Our generated filename
    file_size: int             # File size for verification
    content_hash: str          # Content hash for duplicate detection
    device_type: str           # BAROLOGGERS or WATER_LEVELS
    metadata_summary: Dict     # Key metadata for reference

class DuplicateDetectionSystem:
    """
    Professional duplicate detection system for field data processing
    """
    
    def __init__(self, consolidated_folder: str):
        """
        Initialize duplicate detection system
        
        Args:
            consolidated_folder: Path to SMOO consolidated folder
        """
        self.consolidated_folder = Path(consolidated_folder)
        self.registry_file = self.consolidated_folder / '.processed_files_registry.json'
        self.processed_files: Dict[str, ProcessedFileRecord] = {}
        self.load_registry()
    
    def load_registry(self):
        """Load processed files registry from disk"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    registry_data = json.load(f)
                
                # Convert dict data back to ProcessedFileRecord objects
                for key, record_data in registry_data.items():
                    self.processed_files[key] = ProcessedFileRecord(**record_data)
                
                logger.info(f"Loaded {len(self.processed_files)} processed file records")
            else:
                logger.info("No existing registry found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading processed files registry: {e}")
            self.processed_files = {}
    
    def save_registry(self):
        """Save processed files registry to disk"""
        try:
            # Ensure directory exists
            self.consolidated_folder.mkdir(parents=True, exist_ok=True)
            
            # Convert ProcessedFileRecord objects to dict for JSON serialization
            registry_data = {}
            for key, record in self.processed_files.items():
                registry_data[key] = asdict(record)
            
            # Write atomically (write to temp file, then rename)
            temp_file = self.registry_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.registry_file)
            
            logger.debug(f"Saved {len(self.processed_files)} processed file records")
            
        except Exception as e:
            logger.error(f"Error saving processed files registry: {e}")
    
    def generate_duplicate_key(self, metadata: XLEMetadata) -> str:
        """
        Generate unique key for duplicate detection
        Format: serial_start_end
        
        Args:
            metadata: Extracted XLE metadata
            
        Returns:
            Unique key string for duplicate detection
        """
        try:
            serial = metadata.serial_number if metadata.serial_number != 'UNKNOWN' else 'UNK'
            start = metadata.actual_start_date.replace('-', '') if metadata.actual_start_date else 'NOSTART'
            end = metadata.actual_end_date.replace('-', '') if metadata.actual_end_date else 'NOEND'
            
            duplicate_key = f"{serial}_{start}_{end}"
            logger.debug(f"Generated duplicate key: {duplicate_key}")
            return duplicate_key
            
        except Exception as e:
            logger.error(f"Error generating duplicate key: {e}")
            # Fallback key
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"ERROR_{timestamp}"
    
    def calculate_content_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file content for duplicate detection"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            content_hash = sha256_hash.hexdigest()[:16]  # Use first 16 chars
            logger.debug(f"Calculated content hash: {content_hash}")
            return content_hash
            
        except Exception as e:
            logger.error(f"Error calculating content hash: {e}")
            return "HASH_ERROR"
    
    def check_for_duplicate(self, metadata: XLEMetadata, 
                          google_drive_id: str,
                          file_path: str = None) -> Dict:
        """
        Check if file is a duplicate of already processed data
        
        Args:
            metadata: Extracted XLE metadata
            google_drive_id: Google Drive file ID
            file_path: Local file path for content hash (optional)
            
        Returns:
            Dict with duplicate status and details
        """
        result = {
            'is_duplicate': False,
            'duplicate_type': None,
            'existing_record': None,
            'overlapping_files': [],
            'recommendation': 'process'
        }
        
        try:
            duplicate_key = self.generate_duplicate_key(metadata)
            
            # Check for exact duplicate
            if duplicate_key in self.processed_files:
                existing_record = self.processed_files[duplicate_key]
                result['is_duplicate'] = True
                result['duplicate_type'] = 'exact_match'
                result['existing_record'] = existing_record
                
                # Check if it's the same Google Drive file (re-download)
                if existing_record.google_drive_id == google_drive_id:
                    result['recommendation'] = 'skip_same_file'
                    logger.info(f"Exact duplicate (same Google Drive ID): {duplicate_key}")
                else:
                    # Different Google Drive ID but same metadata - possible re-upload
                    if file_path:
                        current_hash = self.calculate_content_hash(file_path)
                        if current_hash == existing_record.content_hash:
                            result['recommendation'] = 'skip_same_content'
                            logger.info(f"Same content, different Google Drive ID: {duplicate_key}")
                        else:
                            result['recommendation'] = 'investigate_content_change'
                            logger.warning(f"Same metadata, different content: {duplicate_key}")
                    else:
                        result['recommendation'] = 'investigate_possible_reupload'
                        logger.warning(f"Possible re-upload detected: {duplicate_key}")
                
                return result
            
            # Check for overlapping time ranges (potential duplicates)
            overlapping = self.find_overlapping_time_ranges(metadata)
            if overlapping:
                result['overlapping_files'] = overlapping
                result['recommendation'] = 'check_overlap'
                logger.warning(f"Found {len(overlapping)} files with overlapping time ranges")
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            result['recommendation'] = 'process_with_caution'
            return result
    
    def find_overlapping_time_ranges(self, metadata: XLEMetadata, 
                                   tolerance_hours: int = 1) -> List[ProcessedFileRecord]:
        """
        Find files with overlapping time ranges from same serial number
        
        Args:
            metadata: Metadata to check for overlaps
            tolerance_hours: Tolerance for overlap detection
            
        Returns:
            List of overlapping ProcessedFileRecord objects
        """
        overlapping = []
        
        try:
            if not metadata.actual_start_date or not metadata.actual_end_date:
                return overlapping
            
            # Parse target date range
            target_start = datetime.strptime(metadata.actual_start_date, '%Y-%m-%d')
            target_end = datetime.strptime(metadata.actual_end_date, '%Y-%m-%d')
            
            # Check all processed files for same serial number
            for record in self.processed_files.values():
                try:
                    # Skip if different serial number
                    if not record.metadata_summary.get('serial_number') == metadata.serial_number:
                        continue
                    
                    # Parse existing date range
                    existing_start_str = record.metadata_summary.get('actual_start_date', '')
                    existing_end_str = record.metadata_summary.get('actual_end_date', '')
                    
                    if not existing_start_str or not existing_end_str:
                        continue
                    
                    existing_start = datetime.strptime(existing_start_str, '%Y-%m-%d')
                    existing_end = datetime.strptime(existing_end_str, '%Y-%m-%d')
                    
                    # Check for overlap with tolerance
                    tolerance = timedelta(hours=tolerance_hours)
                    
                    if (target_start <= existing_end + tolerance and 
                        target_end + tolerance >= existing_start):
                        overlapping.append(record)
                        logger.debug(f"Found overlap: {record.duplicate_key}")
                
                except Exception as e:
                    logger.debug(f"Error checking overlap for record: {e}")
                    continue
            
            return overlapping
            
        except Exception as e:
            logger.error(f"Error finding overlapping time ranges: {e}")
            return overlapping
    
    def register_processed_file(self, metadata: XLEMetadata,
                              google_drive_id: str,
                              consolidated_path: str,
                              original_filename: str,
                              intelligent_filename: str,
                              file_size: int,
                              file_path: str = None) -> bool:
        """
        Register a successfully processed file in the duplicate detection system
        
        Args:
            metadata: Extracted XLE metadata
            google_drive_id: Google Drive file ID
            consolidated_path: Path where file was stored in SMOO
            original_filename: Original Google Drive filename
            intelligent_filename: Generated intelligent filename
            file_size: File size in bytes
            file_path: Temporary file path for content hash calculation
            
        Returns:
            True if registration successful
        """
        try:
            duplicate_key = self.generate_duplicate_key(metadata)
            
            # Calculate content hash if file path provided
            content_hash = ""
            if file_path and os.path.exists(file_path):
                content_hash = self.calculate_content_hash(file_path)
            
            # Create record
            record = ProcessedFileRecord(
                duplicate_key=duplicate_key,
                google_drive_id=google_drive_id,
                processed_date=datetime.now().isoformat(),
                consolidated_path=consolidated_path,
                original_filename=original_filename,
                intelligent_filename=intelligent_filename,
                file_size=file_size,
                content_hash=content_hash,
                device_type=metadata.device_type,
                metadata_summary={
                    'serial_number': metadata.serial_number,
                    'location': metadata.location,
                    'actual_start_date': metadata.actual_start_date,
                    'actual_end_date': metadata.actual_end_date,
                    'data_units': metadata.data_units,
                    'total_data_points': metadata.total_data_points
                }
            )
            
            # Register in memory
            self.processed_files[duplicate_key] = record
            
            # Save to disk
            self.save_registry()
            
            logger.info(f"Registered processed file: {duplicate_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering processed file: {e}")
            return False
    
    def get_processing_statistics(self) -> Dict:
        """Get statistics about processed files"""
        try:
            stats = {
                'total_processed': len(self.processed_files),
                'by_device_type': {},
                'by_year': {},
                'duplicate_keys_with_multiple_files': 0,
                'oldest_processed': None,
                'newest_processed': None
            }
            
            # Analyze records
            processed_dates = []
            
            for record in self.processed_files.values():
                # Count by device type
                device_type = record.device_type
                stats['by_device_type'][device_type] = stats['by_device_type'].get(device_type, 0) + 1
                
                # Count by year
                try:
                    if record.metadata_summary.get('actual_start_date'):
                        year = record.metadata_summary['actual_start_date'][:4]
                        stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
                except:
                    pass
                
                # Track processing dates
                if record.processed_date:
                    processed_dates.append(record.processed_date)
            
            # Calculate date range
            if processed_dates:
                processed_dates.sort()
                stats['oldest_processed'] = processed_dates[0]
                stats['newest_processed'] = processed_dates[-1]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_invalid_records(self) -> int:
        """
        Clean up registry records for files that no longer exist
        
        Returns:
            Number of records cleaned up
        """
        cleanup_count = 0
        
        try:
            records_to_remove = []
            
            for key, record in self.processed_files.items():
                # Check if consolidated file still exists
                if not os.path.exists(record.consolidated_path):
                    records_to_remove.append(key)
                    logger.debug(f"Marking for cleanup (file not found): {key}")
            
            # Remove invalid records
            for key in records_to_remove:
                del self.processed_files[key]
                cleanup_count += 1
            
            if cleanup_count > 0:
                self.save_registry()
                logger.info(f"Cleaned up {cleanup_count} invalid registry records")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error during registry cleanup: {e}")
            return 0
    
    def export_registry_report(self, output_path: str) -> bool:
        """Export detailed registry report for analysis"""
        try:
            report = {
                'export_date': datetime.now().isoformat(),
                'statistics': self.get_processing_statistics(),
                'processed_files': {}
            }
            
            # Add detailed file information
            for key, record in self.processed_files.items():
                report['processed_files'][key] = asdict(record)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported registry report to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting registry report: {e}")
            return False
    
    def reset_registry(self, backup: bool = True) -> bool:
        """
        Reset the processed files registry (with optional backup)
        
        Args:
            backup: Whether to create backup before reset
            
        Returns:
            True if reset successful
        """
        try:
            if backup and self.registry_file.exists():
                backup_path = self.registry_file.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                self.registry_file.rename(backup_path)
                logger.info(f"Created registry backup: {backup_path}")
            
            # Clear in-memory registry
            self.processed_files = {}
            
            # Remove registry file
            if self.registry_file.exists():
                self.registry_file.unlink()
            
            logger.info("Registry reset completed")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting registry: {e}")
            return False