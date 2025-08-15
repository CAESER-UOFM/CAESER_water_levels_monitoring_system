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
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from io import StringIO

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
        Extract comprehensive metadata from XML-format XLE file using professional field data approach
        
        Args:
            file_path: Path to XLE file
            
        Returns:
            XLEMetadata object with all extracted information
        """
        self.extraction_errors = []
        
        try:
            # Parse XML content (real XLE files are XML format)
            root = self._parse_xle_xml(file_path)
            
            # Extract metadata from XML structure
            serial_number = self._extract_serial_from_xml(root)
            location = self._extract_location_from_xml(root)
            instrument_model = self._extract_instrument_model_from_xml(root)
            
            # Extract data units for device type detection
            data_units = self._extract_data_units_from_xml(root)
            device_type = self._determine_device_type_by_units(data_units)
            
            # Extract actual data timestamps from XML data logs
            start_date, end_date, data_points = self._extract_date_range_from_xml(root)
            
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
    
    def _parse_xle_xml(self, file_path: str) -> ET.Element:
        """Parse XLE XML file and return root element"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    # Fix common XML issues in XLE files
                    # Fix temperature unit issues (special characters before 'C')
                    import re
                    content = re.sub(r'<Unit>([^<]*?)C</Unit>', r'<Unit>C</Unit>', content)
                    
                    # Parse XML
                    root = ET.fromstring(content)
                    logger.debug(f"Successfully parsed XML with encoding: {encoding}")
                    return root
                    
                except Exception as e:
                    logger.debug(f"Failed with encoding {encoding}: {e}")
                    continue
            
            raise ValueError("Could not parse XLE file with any supported encoding")
            
        except Exception as e:
            logger.error(f"Error parsing XLE XML: {e}")
            raise
    
    def _extract_serial_from_xml(self, root: ET.Element) -> str:
        """Extract instrument serial number from XML"""
        try:
            # Look for serial number in XML structure
            instrument_info = root.find('.//Instrument_info')
            if instrument_info is not None:
                serial_element = instrument_info.find('Serial_number')
                if serial_element is not None and serial_element.text:
                    serial = serial_element.text.strip()
                    logger.debug(f"Extracted serial number from XML: {serial}")
                    return serial
            
            self.extraction_errors.append("Serial number not found in XML structure")
            return 'UNKNOWN'
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting serial number: {str(e)}")
            return 'UNKNOWN'
    
    def _extract_location_from_xml(self, root: ET.Element) -> str:
        """Extract location from XML"""
        try:
            # Look for location in XML structure  
            header_info = root.find('.//Instrument_info_data_header')
            if header_info is not None:
                location_element = header_info.find('Location')
                if location_element is not None and location_element.text:
                    location = location_element.text.strip()
                    # Clean up location string
                    location = re.sub(r'[<>:"/\\|?*]', '_', location)  # Remove forbidden chars
                    logger.debug(f"Extracted location from XML: {location}")
                    return location
            
            self.extraction_errors.append("Location not found in XML structure")
            return 'UNKNOWN_LOCATION'
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting location: {str(e)}")
            return 'UNKNOWN_LOCATION'
    
    def _extract_instrument_model_from_xml(self, root: ET.Element) -> str:
        """Extract instrument model from XML"""
        try:
            # Look for instrument info in XML structure
            instrument_info = root.find('.//Instrument_info')
            if instrument_info is not None:
                # Try instrument type first
                type_element = instrument_info.find('Instrument_type')
                model_element = instrument_info.find('Model_number')
                
                instrument_type = type_element.text.strip() if type_element is not None and type_element.text else ''
                model_number = model_element.text.strip() if model_element is not None and model_element.text else ''
                
                if instrument_type and model_number:
                    model = f"{instrument_type} {model_number}"
                elif instrument_type:
                    model = instrument_type
                elif model_number:
                    model = model_number
                else:
                    model = 'UNKNOWN_MODEL'
                
                logger.debug(f"Extracted instrument model from XML: {model}")
                return model
            
            self.extraction_errors.append("Instrument model not found in XML structure")
            return 'UNKNOWN_MODEL'
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting instrument model: {str(e)}")
            return 'UNKNOWN_MODEL'
    
    def _extract_data_units_from_xml(self, root: ET.Element) -> str:
        """
        Extract data units from XML for reliable device type detection
        This is the most reliable way to determine if device is barologger or water level
        """
        try:
            # Look for Ch1 (primary channel) unit in XML structure
            ch1_info = root.find('.//Ch1_data_header')
            if ch1_info is not None:
                unit_element = ch1_info.find('Unit')
                if unit_element is not None and unit_element.text:
                    unit = unit_element.text.strip().lower()
                    logger.debug(f"Extracted data units from XML: {unit}")
                    return unit
            
            # Fallback: look in other possible locations
            for element in root.iter('Unit'):
                if element.text:
                    unit = element.text.strip().lower()
                    if unit in self.PRESSURE_UNITS + self.WATER_LEVEL_UNITS:
                        logger.debug(f"Found valid unit in XML: {unit}")
                        return unit
            
            self.extraction_errors.append("Data units not found in XML structure")
            return ''
            
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
    
    def _extract_date_range_from_xml(self, root: ET.Element) -> Tuple[str, str, int]:
        """
        Extract actual start/end dates from XML data logs (not metadata)
        This avoids Solinst firmware bugs in metadata end dates
        
        Returns:
            Tuple of (start_date, end_date, data_point_count)
        """
        try:
            # Find all Log entries in XML
            log_entries = root.findall('.//Log')
            
            if not log_entries:
                self.extraction_errors.append("No data log entries found in XML")
                return '', '', 0
            
            # Extract timestamps from first and last entries
            valid_entries = []
            
            for log in log_entries:
                date_elem = log.find('Date')
                time_elem = log.find('Time')
                
                if (date_elem is not None and date_elem.text and 
                    time_elem is not None and time_elem.text):
                    
                    date_str = date_elem.text.strip()
                    time_str = time_elem.text.strip()
                    
                    # Skip "END OF" entries
                    if "END OF" not in date_str and "END OF" not in time_str:
                        timestamp_str = f"{date_str} {time_str}"
                        try:
                            # Parse to validate and normalize
                            timestamp = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                            valid_entries.append(timestamp)
                        except ValueError:
                            logger.debug(f"Could not parse timestamp: {timestamp_str}")
                            continue
            
            if not valid_entries:
                self.extraction_errors.append("No valid timestamps found in data logs")
                return '', '', 0
            
            # Sort to get actual first and last
            valid_entries.sort()
            first_timestamp = valid_entries[0].strftime('%Y-%m-%d')
            last_timestamp = valid_entries[-1].strftime('%Y-%m-%d')
            
            logger.debug(f"Extracted actual date range from XML: {first_timestamp} to {last_timestamp}")
            return first_timestamp, last_timestamp, len(valid_entries)
            
        except Exception as e:
            self.extraction_errors.append(f"Error extracting date range from XML: {str(e)}")
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