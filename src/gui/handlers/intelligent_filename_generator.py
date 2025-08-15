#!/usr/bin/env python3
"""
Intelligent Filename Generator for Field Data

Implements professional field data naming convention:
Format: {serial}_{location}_{start_date}_To_{end_date}.xle

Examples:
- 2102759_PIONEER_SPRINGS_2025_06_24_To_2025_08_01.xle
- 2105643_WELL_HA_A012_2025_06_23_To_07_29.xle (same year optimization)

Features:
- Never trust original filenames (field conditions create unreliable names)
- Generate consistent, self-documenting filenames
- Handle Windows path length limitations
- Smart date formatting (same year optimization)
- Character sanitization for cross-platform compatibility

@author: Professional field data workflow implementation
"""

import re
import os
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from .xle_metadata_extractor import XLEMetadata

logger = logging.getLogger(__name__)

class IntelligentFilenameGenerator:
    """
    Generate intelligent, self-documenting filenames based on extracted metadata
    Following professional field data practices
    """
    
    # Windows path limitations
    MAX_FILENAME_LENGTH = 80   # Conservative limit for long folder paths
    MAX_LOCATION_LENGTH = 20   # Prevent extremely long location names
    
    # Characters forbidden in Windows filenames
    FORBIDDEN_CHARS = r'[<>:"/\\|?*]'
    
    # Reserved Windows filenames
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    def __init__(self):
        self.generation_errors = []
    
    def generate_intelligent_filename(self, metadata: XLEMetadata, 
                                    fallback_original: str = None) -> str:
        """
        Generate intelligent filename based on metadata
        
        Format: {serial}_{location}_{start_date}_To_{end_date}.xle
        
        Args:
            metadata: Extracted XLE metadata
            fallback_original: Original filename to use if metadata insufficient
            
        Returns:
            Intelligent filename string
        """
        self.generation_errors = []
        
        try:
            # Check if we have sufficient metadata
            if not self._has_sufficient_metadata(metadata):
                logger.warning("Insufficient metadata for intelligent naming, using fallback")
                return self._get_fallback_filename(fallback_original, metadata)
            
            # Extract and clean components
            serial = self._clean_serial_number(metadata.serial_number)
            location = self._clean_location_name(metadata.location)
            date_part = self._format_date_range(metadata.actual_start_date, metadata.actual_end_date)
            
            # Generate base filename
            base_filename = f"{serial}_{location}_{date_part}"
            
            # Add device type prefix for organization
            device_prefix = self._get_device_prefix(metadata.device_type)
            if device_prefix:
                base_filename = f"{device_prefix}_{base_filename}"
            
            # Add extension
            intelligent_filename = f"{base_filename}.xle"
            
            # Check length and adjust if necessary
            if len(intelligent_filename) > self.MAX_FILENAME_LENGTH:
                intelligent_filename = self._shorten_filename(serial, location, date_part, device_prefix)
            
            # Validate filename
            if self._is_valid_filename(intelligent_filename):
                logger.debug(f"Generated intelligent filename: {intelligent_filename}")
                return intelligent_filename
            else:
                logger.warning("Generated filename failed validation, using fallback")
                return self._get_fallback_filename(fallback_original, metadata)
                
        except Exception as e:
            logger.error(f"Error generating intelligent filename: {e}")
            self.generation_errors.append(f"Filename generation failed: {str(e)}")
            return self._get_fallback_filename(fallback_original, metadata)
    
    def _has_sufficient_metadata(self, metadata: XLEMetadata) -> bool:
        """Check if metadata is sufficient for intelligent filename generation"""
        required_fields = [
            metadata.serial_number and metadata.serial_number != 'UNKNOWN',
            metadata.actual_start_date and metadata.actual_start_date != '',
            metadata.actual_end_date and metadata.actual_end_date != ''
        ]
        
        return all(required_fields)
    
    def _clean_serial_number(self, serial: str) -> str:
        """Clean and validate serial number"""
        if not serial or serial == 'UNKNOWN':
            return 'UNK'
        
        # Keep only alphanumeric characters
        cleaned = re.sub(r'[^\w]', '', str(serial))
        
        # Limit length
        if len(cleaned) > 10:
            cleaned = cleaned[:10]
        
        return cleaned if cleaned else 'UNK'
    
    def _clean_location_name(self, location: str) -> str:
        """Clean location name for filename use"""
        if not location or location in ['UNKNOWN_LOCATION', 'UNKNOWN']:
            return 'UNK_LOC'
        
        # Remove forbidden characters and replace with underscores
        cleaned = re.sub(self.FORBIDDEN_CHARS, '_', location)
        
        # Remove extra spaces and replace with underscores
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        
        # Convert to uppercase for consistency
        cleaned = cleaned.upper()
        
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        # Limit length
        if len(cleaned) > self.MAX_LOCATION_LENGTH:
            cleaned = cleaned[:self.MAX_LOCATION_LENGTH]
        
        # Check for reserved names
        if cleaned.upper() in self.RESERVED_NAMES:
            cleaned = f"{cleaned}_LOC"
        
        return cleaned if cleaned else 'UNK_LOC'
    
    def _format_date_range(self, start_date: str, end_date: str) -> str:
        """
        Format date range with smart optimization
        
        Examples:
        - Same year: 2025_06_24_To_08_01
        - Different years: 2025_06_24_To_2026_01_15
        """
        try:
            # Parse dates
            start_parts = start_date.split('-')  # Expected: ['2025', '06', '24']
            end_parts = end_date.split('-')      # Expected: ['2025', '08', '01']
            
            if len(start_parts) != 3 or len(end_parts) != 3:
                logger.warning(f"Invalid date format: {start_date} or {end_date}")
                return "DATE_RANGE_ERROR"
            
            start_year, start_month, start_day = start_parts
            end_year, end_month, end_day = end_parts
            
            # Smart formatting based on year
            if start_year == end_year:
                # Same year: optimize format
                date_part = f"{start_year}_{start_month}_{start_day}_To_{end_month}_{end_day}"
            else:
                # Different years: full format
                date_part = f"{start_year}_{start_month}_{start_day}_To_{end_year}_{end_month}_{end_day}"
            
            return date_part
            
        except Exception as e:
            logger.error(f"Error formatting date range: {e}")
            return "DATE_ERROR"
    
    def _get_device_prefix(self, device_type: str) -> str:
        """Get device type prefix for filename"""
        device_prefixes = {
            'BAROLOGGERS': 'BARO',
            'WATER_LEVELS': 'WL',
            'UNKNOWN_TYPE': ''
        }
        
        return device_prefixes.get(device_type, '')
    
    def _shorten_filename(self, serial: str, location: str, date_part: str, 
                         device_prefix: str) -> str:
        """Shorten filename to meet length requirements"""
        try:
            # Start with essential components
            shortened_location = location[:10] if len(location) > 10 else location
            
            # Build progressively shorter versions
            versions = [
                f"{device_prefix}_{serial}_{shortened_location}_{date_part}.xle" if device_prefix else f"{serial}_{shortened_location}_{date_part}.xle",
                f"{serial}_{shortened_location[:8]}_{date_part}.xle",
                f"{serial}_{shortened_location[:5]}_{date_part}.xle",
                f"{serial}_{date_part}.xle",
                f"{serial[:8]}_{date_part}.xle",
            ]
            
            # Return first version that fits
            for version in versions:
                if len(version) <= self.MAX_FILENAME_LENGTH:
                    logger.debug(f"Shortened filename to: {version}")
                    return version
            
            # Last resort: use serial and current date
            current_date = datetime.now().strftime("%Y_%m_%d")
            fallback = f"{serial[:10]}_{current_date}.xle"
            logger.warning(f"Using fallback shortened filename: {fallback}")
            return fallback
            
        except Exception as e:
            logger.error(f"Error shortening filename: {e}")
            return f"{serial[:10]}_SHORTENED.xle"
    
    def _is_valid_filename(self, filename: str) -> bool:
        """Validate filename for cross-platform compatibility"""
        try:
            # Check basic requirements
            if not filename or len(filename) == 0:
                return False
            
            # Check length
            if len(filename) > self.MAX_FILENAME_LENGTH:
                return False
            
            # Check for forbidden characters
            if re.search(self.FORBIDDEN_CHARS, filename):
                return False
            
            # Check for reserved names (without extension)
            name_without_ext = Path(filename).stem.upper()
            if name_without_ext in self.RESERVED_NAMES:
                return False
            
            # Check for valid extension
            if not filename.lower().endswith('.xle'):
                return False
            
            # Check for control characters
            if any(ord(char) < 32 for char in filename):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating filename: {e}")
            return False
    
    def _get_fallback_filename(self, original_filename: str, metadata: XLEMetadata) -> str:
        """Generate fallback filename when intelligent generation fails"""
        try:
            # Try to use original filename if available and valid
            if original_filename and self._is_valid_filename(original_filename):
                logger.debug(f"Using original filename as fallback: {original_filename}")
                return original_filename
            
            # Generate basic fallback
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            device_prefix = self._get_device_prefix(metadata.device_type)
            
            if device_prefix:
                fallback = f"{device_prefix}_FIELD_DATA_{timestamp}.xle"
            else:
                fallback = f"FIELD_DATA_{timestamp}.xle"
            
            logger.debug(f"Generated timestamp fallback: {fallback}")
            return fallback
            
        except Exception as e:
            logger.error(f"Error generating fallback filename: {e}")
            # Ultimate fallback
            return f"UNKNOWN_DATA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xle"
    
    def generate_filename_with_validation(self, metadata: XLEMetadata, 
                                        original_filename: str = None,
                                        target_directory: str = None) -> Dict:
        """
        Generate filename with comprehensive validation and conflict checking
        
        Returns:
            Dict with 'filename', 'full_path', 'conflicts', 'warnings'
        """
        result = {
            'filename': '',
            'full_path': '',
            'conflicts': [],
            'warnings': self.generation_errors.copy()
        }
        
        try:
            # Generate intelligent filename
            filename = self.generate_intelligent_filename(metadata, original_filename)
            result['filename'] = filename
            
            # Check for conflicts if target directory provided
            if target_directory:
                full_path = os.path.join(target_directory, filename)
                result['full_path'] = full_path
                
                # Check for existing files
                if os.path.exists(full_path):
                    result['conflicts'].append(f"File already exists: {full_path}")
                    
                    # Generate alternative filename
                    counter = 1
                    name_without_ext = Path(filename).stem
                    ext = Path(filename).suffix
                    
                    while os.path.exists(full_path) and counter < 100:
                        alt_filename = f"{name_without_ext}_{counter:02d}{ext}"
                        full_path = os.path.join(target_directory, alt_filename)
                        counter += 1
                    
                    if counter < 100:
                        result['filename'] = alt_filename
                        result['full_path'] = full_path
                        result['warnings'].append(f"Renamed to avoid conflict: {alt_filename}")
                    else:
                        result['warnings'].append("Could not resolve filename conflict")
            
            return result
            
        except Exception as e:
            result['warnings'].append(f"Filename generation error: {str(e)}")
            result['filename'] = self._get_fallback_filename(original_filename, metadata)
            return result
    
    def batch_generate_filenames(self, metadata_list: list, 
                               target_directory: str = None) -> Dict:
        """
        Generate filenames for multiple files with conflict resolution
        
        Returns:
            Dict with results for each file and overall statistics
        """
        results = {
            'files': [],
            'statistics': {
                'total': len(metadata_list),
                'successful': 0,
                'conflicts': 0,
                'errors': 0
            }
        }
        
        used_filenames = set()
        
        for i, metadata in enumerate(metadata_list):
            try:
                # Generate filename
                file_result = self.generate_filename_with_validation(
                    metadata, 
                    target_directory=target_directory
                )
                
                # Check for duplicates in this batch
                base_filename = file_result['filename']
                if base_filename in used_filenames:
                    # Add index to make unique
                    name_without_ext = Path(base_filename).stem
                    ext = Path(base_filename).suffix
                    unique_filename = f"{name_without_ext}_BATCH_{i:03d}{ext}"
                    file_result['filename'] = unique_filename
                    file_result['warnings'].append(f"Made unique in batch: {unique_filename}")
                
                used_filenames.add(file_result['filename'])
                results['files'].append(file_result)
                
                # Update statistics
                if file_result['conflicts']:
                    results['statistics']['conflicts'] += 1
                if file_result['warnings']:
                    if any('error' in w.lower() for w in file_result['warnings']):
                        results['statistics']['errors'] += 1
                    else:
                        results['statistics']['successful'] += 1
                else:
                    results['statistics']['successful'] += 1
                    
            except Exception as e:
                logger.error(f"Error in batch filename generation: {e}")
                results['statistics']['errors'] += 1
        
        return results