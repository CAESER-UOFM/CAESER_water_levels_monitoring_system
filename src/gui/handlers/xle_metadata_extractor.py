#!/usr/bin/env python3
"""
Enhanced XLE Metadata Extractor

This module implements professional field data processing following the user's requirements:
- Never trust filenames (field conditions create unreliable names)
- Extract actual data timestamps (avoid Solinst firmware bugs in metadata)
- Use data units for reliable device type detection
- Extract comprehensive metadata for intelligent file organization

@author: Enhanced for professional field data workflows
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class XLEMetadata:
    """Comprehensive XLE file metadata"""
    serial_number: str
    location: str
    instrument_model: str
    actual_start_date: str
    actual_end_date: str
    data_units: str
    device_type: str  # 'BAROLOGGERS' or 'WATER_LEVELS'
    total_data_points: int
    extraction_errors: List[str]

class EnhancedXLEMetadataExtractor:
    """
    Professional XLE metadata extractor that prioritizes actual data over unreliable metadata
    """
    
    # Define unit categories for device type detection
    PRESSURE_UNITS = [
        'psi', 'kpa', 'bar', 'mbar', 'pa', 'mmhg', 'inhg', 
        'psig', 'psia', 'atm', 'torr'
    ]
    
    WATER_LEVEL_UNITS = [
        'ft', 'fth20', 'm', 'cm', 'mm', 'inches', 'in', 
        'meter', 'feet', 'centimeter', 'millimeter'
    ]
    
    def __init__(self):
        self.extraction_errors = []
    
    def extract_comprehensive_metadata(self, file_path: str) -> XLEMetadata:
        """
        Extract comprehensive metadata from XLE file using professional field data approach
        
        Args:
            file_path: Path to XLE file
            
        Returns:
            XLEMetadata object with all extracted information
        """
        self.extraction_errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract basic metadata from header
            serial_number = self._extract_serial_number(content)
            location = self._extract_location(content)
            instrument_model = self._extract_instrument_model(content)
            
            # Extract data units for device type detection
            data_units = self._extract_data_units(content)
            device_type = self._determine_device_type_by_units(data_units)
            
            # Extract actual data timestamps (most reliable)
            start_date, end_date, data_points = self._extract_actual_date_range(content)
            
            return XLEMetadata(
                serial_number=serial_number,
                location=location,
                instrument_model=instrument_model,
                actual_start_date=start_date,
                actual_end_date=end_date,
                data_units=data_units,
                device_type=device_type,
                total_data_points=data_points,
                extraction_errors=self.extraction_errors.copy()
            )
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            self.extraction_errors.append(f"Critical extraction failure: {str(e)}")
            
            # Return minimal metadata for error cases
            return XLEMetadata(
                serial_number='UNKNOWN',
                location='UNKNOWN',
                instrument_model='UNKNOWN',
                actual_start_date='',
                actual_end_date='',
                data_units='',
                device_type='UNKNOWN_TYPE',
                total_data_points=0,
                extraction_errors=self.extraction_errors.copy()
            )
    
    def _extract_serial_number(self, content: str) -> str:
        """Extract instrument serial number from XLE content"""
        try:
            # Common XLE patterns for serial number
            patterns = [
                r'Logger serial number\s*[:=]\s*(\d+)',  # Full format first
                r'Serial_number\s*[:=]\s*(\d+)',
                r'Serial\s*number\s*[:=]\s*(\d+)',
                r'Serial\s*[:=]\s*(\d+)',
                r'S/N\s*[:=]\s*(\d+)',
                r'Instrument\s*#\s*[:=]\s*(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    serial = match.group(1).strip()
                    logger.debug(f"Extracted serial number: {serial}")
                    return serial
            
            self.extraction_errors.append("Serial number not found in standard locations")
            return 'UNKNOWN'
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting serial number: {str(e)}")
            return 'UNKNOWN'
    
    def _extract_location(self, content: str) -> str:
        """Extract location from XLE content"""
        try:
            # Common XLE patterns for location
            patterns = [
                r'Location\s*[:=]\s*([^\n\r]+)',
                r'Site\s*[:=]\s*([^\n\r]+)',
                r'Well\s*[:=]\s*([^\n\r]+)',
                r'Station\s*[:=]\s*([^\n\r]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    # Clean up location string
                    location = re.sub(r'[<>:"/\\|?*]', '_', location)  # Remove forbidden chars
                    logger.debug(f"Extracted location: {location}")
                    return location
            
            self.extraction_errors.append("Location not found in standard locations")
            return 'UNKNOWN_LOCATION'
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting location: {str(e)}")
            return 'UNKNOWN_LOCATION'
    
    def _extract_instrument_model(self, content: str) -> str:
        """Extract instrument model from XLE content"""
        try:
            # Common XLE patterns for instrument model
            patterns = [
                r'Instrument\s*[:=]\s*([^\n\r]+)',
                r'Model\s*[:=]\s*([^\n\r]+)',
                r'Device\s*[:=]\s*([^\n\r]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    model = match.group(1).strip()
                    logger.debug(f"Extracted instrument model: {model}")
                    return model
            
            self.extraction_errors.append("Instrument model not found")
            return 'UNKNOWN_MODEL'
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting instrument model: {str(e)}")
            return 'UNKNOWN_MODEL'
    
    def _extract_data_units(self, content: str) -> str:
        """
        Extract data units from XLE content for reliable device type detection
        This is the most reliable way to determine if device is barologger or water level
        """
        try:
            # Look for units in various XLE formats
            unit_patterns = [
                r'LEVEL\s+TEMPERATURE.*?\n.*?(\w+)',  # Common table header format
                r'Unit\s*[:=]\s*(\w+)',               # Direct unit specification
                r'\[Data\]\s*\n.*?(\w+)',             # Units after data header
                r'Level.*?[\(\[](\w+)[\)\]]',         # Units in parentheses
                r'Pressure.*?[\(\[](\w+)[\)\]]',      # Pressure units
                r'Head.*?[\(\[](\w+)[\)\]]'           # Head/level units
            ]
            
            units_found = []
            for pattern in unit_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                units_found.extend(matches)
            
            # Return first valid unit found
            for unit in units_found:
                unit_clean = unit.lower().strip()
                if unit_clean and len(unit_clean) <= 10:  # Reasonable unit length
                    logger.debug(f"Extracted data units: {unit_clean}")
                    return unit_clean
            
            # Fallback: analyze first few data lines
            return self._extract_units_from_data_lines(content)
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting data units: {str(e)}")
            return ''
    
    def _extract_units_from_data_lines(self, content: str) -> str:
        """Fallback method: extract units by analyzing data values"""
        try:
            # Find data section
            data_section_start = None
            for marker in ['[Level data]', '[Data]', 'DATE', 'Time']:
                if marker in content:
                    data_section_start = content.find(marker)
                    break
            
            if data_section_start is None:
                return ''
            
            # Get a few data lines
            data_section = content[data_section_start:data_section_start + 1000]
            lines = data_section.split('\n')
            
            # Look for numeric data patterns
            for line in lines[1:6]:  # Skip header, check first few data lines
                # Look for pressure-like values (typically 10+ for psi)
                if re.search(r'\d{2,3}\.\d+', line):  # Values like 14.7, 101.3
                    return 'psi'  # Likely pressure
                # Look for smaller values (typically water levels)
                elif re.search(r'\d{1,2}\.\d+', line):  # Values like 5.2, 12.1
                    return 'ft'   # Likely water level
            
            return ''
            
        except Exception as e:
            logger.debug(f"Error in fallback unit extraction: {e}")
            return ''
    
    def _determine_device_type_by_units(self, units: str) -> str:
        """
        Determine device type based on data units - most reliable method
        
        Args:
            units: Data units extracted from file
            
        Returns:
            'BAROLOGGERS' or 'WATER_LEVELS' or 'UNKNOWN_TYPE'
        """
        if not units:
            return 'UNKNOWN_TYPE'
        
        units_lower = units.lower().strip()
        
        # Check for pressure units (barologgers)
        for pressure_unit in self.PRESSURE_UNITS:
            if pressure_unit in units_lower:
                logger.debug(f"Device categorized as BAROLOGGER based on units: {units}")
                return 'BAROLOGGERS'
        
        # Check for water level units
        for water_unit in self.WATER_LEVEL_UNITS:
            if water_unit in units_lower:
                logger.debug(f"Device categorized as WATER_LEVELS based on units: {units}")
                return 'WATER_LEVELS'
        
        # Unknown units - log for investigation
        logger.warning(f"Unknown units detected, defaulting to WATER_LEVELS: {units}")
        return 'WATER_LEVELS'  # Default to most common type
    
    def _extract_actual_date_range(self, content: str) -> Tuple[str, str, int]:
        """
        Extract actual start/end dates from data rows (not metadata)
        This avoids Solinst firmware bugs in metadata end dates
        
        Returns:
            Tuple of (start_date, end_date, data_point_count)
        """
        try:
            # Find data section
            data_markers = ['[Level data]', '[Data]', 'DATE', 'Time']
            data_start_pos = None
            
            for marker in data_markers:
                pos = content.find(marker)
                if pos != -1:
                    data_start_pos = pos
                    break
            
            if data_start_pos is None:
                self.extraction_errors.append("No data section found")
                return '', '', 0
            
            # Extract data section
            data_section = content[data_start_pos:]
            lines = data_section.split('\n')
            
            # Find actual data lines (skip headers)
            data_lines = []
            for line in lines:
                line = line.strip()
                if self._is_data_line(line):
                    data_lines.append(line)
            
            if not data_lines:
                self.extraction_errors.append("No data lines found")
                return '', '', 0
            
            # Extract timestamps from first and last data lines
            first_timestamp = self._extract_timestamp_from_line(data_lines[0])
            last_timestamp = self._extract_timestamp_from_line(data_lines[-1])
            
            if not first_timestamp or not last_timestamp:
                self.extraction_errors.append("Could not extract timestamps from data")
                return '', '', 0
            
            logger.debug(f"Extracted actual date range: {first_timestamp} to {last_timestamp}")
            return first_timestamp, last_timestamp, len(data_lines)
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting actual date range: {str(e)}")
            return '', '', 0
    
    def _is_data_line(self, line: str) -> bool:
        """Check if line contains actual data (not header or metadata)"""
        if not line or len(line) < 10:
            return False
        
        # Look for date/time patterns in various formats
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',     # MM/dd/yyyy
            r'\d{2,4}-\d{1,2}-\d{1,2}',     # yyyy-mm-dd
            r'\d{1,2}\.\d{1,2}\.\d{2,4}',   # dd.mm.yyyy
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, line):
                # Also check for numeric data (levels/pressure)
                if re.search(r'\d+\.\d+', line):
                    return True
        
        return False
    
    def _extract_timestamp_from_line(self, line: str) -> str:
        """Extract timestamp from data line and convert to standard format"""
        try:
            # Common XLE timestamp patterns
            timestamp_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2}:\d{2})',  # MM/dd/yyyy HH:mm:ss
                r'(\d{2,4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2}:\d{2})',  # yyyy-mm-dd HH:mm:ss
                r'(\d{1,2}\.\d{1,2}\.\d{2,4})\s+(\d{1,2}:\d{2}:\d{2})', # dd.mm.yyyy HH:mm:ss
            ]
            
            for pattern in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    date_part = match.group(1)
                    time_part = match.group(2)
                    
                    # Convert to standard format: YYYY-MM-DD
                    return self._normalize_date_format(date_part)
            
            return ''
            
        except Exception as e:
            logger.debug(f"Error extracting timestamp from line: {e}")
            return ''
    
    def _normalize_date_format(self, date_str: str) -> str:
        """Convert various date formats to YYYY-MM-DD"""
        try:
            # Try different date formats
            date_formats = [
                '%m/%d/%Y', '%m/%d/%y',    # MM/dd/yyyy, MM/dd/yy
                '%Y-%m-%d',                # yyyy-mm-dd
                '%d.%m.%Y', '%d.%m.%y',    # dd.mm.yyyy, dd.mm.yy
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date format: {date_str}")
            return date_str  # Return as-is if can't parse
            
        except Exception as e:
            logger.debug(f"Error normalizing date format: {e}")
            return date_str

    def get_duplicate_key(self, metadata: XLEMetadata) -> str:
        """
        Generate unique key for duplicate detection
        Format: serial_start_end for reliable duplicate identification
        """
        return f"{metadata.serial_number}_{metadata.actual_start_date}_{metadata.actual_end_date}"
    
    def validate_metadata(self, metadata: XLEMetadata) -> bool:
        """
        Validate extracted metadata for completeness
        
        Returns:
            True if metadata is sufficient for file processing
        """
        required_fields = [
            metadata.serial_number != 'UNKNOWN',
            metadata.actual_start_date != '',
            metadata.actual_end_date != '',
            metadata.device_type != 'UNKNOWN_TYPE'
        ]
        
        is_valid = all(required_fields)
        
        if not is_valid:
            logger.warning(f"Incomplete metadata validation: {metadata}")
        
        return is_valid