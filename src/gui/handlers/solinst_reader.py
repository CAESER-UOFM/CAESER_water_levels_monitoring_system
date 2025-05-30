import xml.etree.ElementTree as ET
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Tuple, Dict
from io import StringIO

logger = logging.getLogger(__name__)

@dataclass
class SolinstMetadata:
    """Class to store Solinst logger metadata"""
    instrument_type: str
    model_number: str
    serial_number: str
    project_id: str
    location: str
    start_time: datetime
    stop_time: datetime
    sample_rate: int
    num_log: int
    level_unit: str         # Original unit in the file
    temperature_unit: str   # Original unit in the file
    firmware: str
    battery_voltage: float
    original_level_unit: str = ""  # Added to track original unit before conversion
    original_temp_unit: str = ""   # Added to track original unit before conversion

class SolinstReader:
    
    # Conversion factors
    M_TO_FT = 3.28084     # Meters to Feet
    KPA_TO_PSI = 0.145038 # Kilopascals to PSI
    
    # Known instrument type and model combinations for barologgers
    BAROLOGGER_TYPES = {
        'L5_LT': ['M1.5'],      # Levelogger 5 Baro
        'LT_EDGE': ['M1.5'],    # Barologger Edge
        'L5_EDGE': ['M1.5']     # Another possible variant
    }
    
    # Unit mappings for identification
    PRESSURE_UNITS = {'kpa', 'kilopascal', 'kilopascals', 'psi', 'bar'}
    LEVEL_UNITS = {'m', 'meter', 'meters', 'ft', 'foot', 'feet'}
    TEMP_UNITS = {'c', 'celsius', 'f', 'fahrenheit'}
    
    def __init__(self):
        self.required_elements = {
            'instrument': ['Instrument_type', 'Model_number', 'Serial_number', 'Firmware'],
            'header': ['Project_ID', 'Location', 'Sample_rate', 'Start_time', 
                      'Stop_time', 'Num_log'],
            'channels': ['ch1', 'ch2']
        }
        
    def _normalize_unit(self, unit_str: str) -> str:
        """Normalize unit string for comparison"""
        if unit_str is None:
            return ""
        # Clean and lowercase the unit string
        unit = unit_str.strip().lower()
        return unit

    def _detect_unit_type(self, unit: str) -> Dict[str, str]:
        """
        Detect the type and standard form of a unit
        
        Returns:
            Dictionary with unit_type and standard_unit
        """
        unit = self._normalize_unit(unit)
        
        # Detect temperature units
        if unit in {'c', 'celsius', '°c', 'c°', 'deg c', 'degrees c'}:
            return {'unit_type': 'temperature', 'standard_unit': 'C'}
        elif unit in {'f', 'fahrenheit', '°f', 'f°', 'deg f', 'degrees f'}:
            return {'unit_type': 'temperature', 'standard_unit': 'F'}
            
        # Detect pressure units
        elif unit in {'kpa', 'kilopascal', 'kilopascals'}:
            return {'unit_type': 'pressure', 'standard_unit': 'kPa'}
        elif unit in {'psi', 'pounds per square inch', 'lb/in²', 'lb/in2'}:
            return {'unit_type': 'pressure', 'standard_unit': 'psi'}
            
        # Detect level units
        elif unit in {'m', 'meter', 'meters', 'metres'}:
            return {'unit_type': 'level', 'standard_unit': 'm'}
        elif unit in {'ft', 'foot', 'feet'}:
            return {'unit_type': 'level', 'standard_unit': 'ft'}
            
        # Unknown unit
        return {'unit_type': 'unknown', 'standard_unit': unit}

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str = 'C') -> float:
        """Convert temperature between units"""
        if from_unit == to_unit:
            return value
            
        if from_unit == 'F' and to_unit == 'C':
            # F to C conversion: (F - 32) * 5/9
            return (value - 32) * 5/9
            
        if from_unit == 'C' and to_unit == 'F':
            # C to F conversion: (C * 9/5) + 32
            return (value * 9/5) + 32
            
        return value  # Default case if units aren't recognized
        
    def _convert_pressure(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert pressure between units"""
        if from_unit == to_unit:
            return value
            
        if from_unit == 'kPa' and to_unit == 'psi':
            # kPa to psi conversion
            return value * self.KPA_TO_PSI
            
        if from_unit == 'psi' and to_unit == 'kPa':
            # psi to kPa conversion
            return value / self.KPA_TO_PSI
            
        return value  # Default case if units aren't recognized
        
    def _convert_level(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert level between units"""
        if from_unit == to_unit:
            return value
            
        if from_unit == 'm' and to_unit == 'ft':
            # m to ft conversion
            return value * self.M_TO_FT
            
        if from_unit == 'ft' and to_unit == 'm':
            # ft to m conversion
            return value / self.M_TO_FT
            
        return value  # Default case if units aren't recognized

    def _get_utc_offset(self, local_time: datetime) -> int:
        """
        Get UTC offset in hours for a given local time
        Returns +6 for CST (standard time)
        Returns +5 for CDT (during daylight savings)
        """
        spring_dst, fall_dst = self._get_dst_dates(local_time.year)
        return 5 if spring_dst <= local_time < fall_dst else 6

    def read_xle(self, file_path: Path) -> Tuple[pd.DataFrame, SolinstMetadata]:
        """Read XLE file and convert timestamps to naive UTC"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252']
            last_error = None
            
            for encoding in encodings:
                try:
                    # Read file with specific encoding
                    with open(file_path, 'r', encoding=encoding) as f:
                        xml_content = f.read()
                    context = ET.iterparse(StringIO(xml_content), events=("start", "end"))
                    _, root = next(context)  # Get root element
                    break
                except Exception as e:
                    last_error = e
                    continue
            else:
                # If we get here, none of the encodings worked
                raise last_error or ValueError("Could not read file with any supported encoding")
    
            # Get metadata first
            metadata = self._extract_metadata(root)
            
            # Determine UTC offset based on logger start time only
            start_time_offset = self._get_utc_offset(metadata.start_time)
            
            # Convert metadata timestamps to UTC
            metadata.start_time = metadata.start_time + timedelta(hours=start_time_offset)
            metadata.stop_time = metadata.stop_time + timedelta(hours=start_time_offset)
    
            # Process logs efficiently - and skip "END OF" entries
            log_entries = []
            for event, elem in context:
                if event == "end" and elem.tag == "Log":
                    date_str = elem.findtext('Date', '')
                    time_str = elem.findtext('Time', '')
                    
                    # Skip entries with "END OF" text in Date or Time fields
                    if "END OF" in date_str or "END OF" in time_str:
                        continue
                        
                    log_entries.append((
                        f"{date_str} {time_str}",
                        elem.findtext('ch1'),
                        elem.findtext('ch2')
                    ))
    
            # Convert to DataFrame in one batch
            df = pd.DataFrame(log_entries, columns=['timestamp', 'pressure', 'temperature'])
            
            # Skip empty dataframes
            if df.empty:
                return df, metadata
                
            # Convert timestamps to datetime - use standard parsing without deprecated parameters
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y/%m/%d %H:%M:%S")
            except ValueError:
                # If strict parsing fails, try with a more lenient approach
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # Drop rows where timestamp couldn't be parsed
                df = df.dropna(subset=['timestamp'])
            
            # Apply the same offset to all timestamps based on start time
            df['timestamp_utc'] = df['timestamp'] + pd.Timedelta(hours=start_time_offset)
            
            # Convert values in bulk
            df['pressure'] = pd.to_numeric(df['pressure'], errors='coerce')
            df['temperature'] = pd.to_numeric(df['temperature'], errors='coerce')
            
            # Determine unit types and perform conversions if needed
            level_unit_info = self._detect_unit_type(metadata.level_unit)
            temp_unit_info = self._detect_unit_type(metadata.temperature_unit)
            
            # Store original units in metadata
            metadata.original_level_unit = level_unit_info['standard_unit']
            metadata.original_temp_unit = temp_unit_info['standard_unit']
            
            # Convert level/pressure to standardized units (ft for level, psi for pressure)
            if level_unit_info['unit_type'] == 'level' and level_unit_info['standard_unit'] == 'm':
                # Convert from meters to feet
                df['pressure'] = df['pressure'].apply(lambda x: self._convert_level(x, 'm', 'ft'))
                metadata.level_unit = 'ft'  # Update metadata unit
                logger.info(f"Converted level from meters to feet for {file_path}")
                
            elif level_unit_info['unit_type'] == 'pressure' and level_unit_info['standard_unit'] == 'kPa':
                # Convert from kPa to psi
                df['pressure'] = df['pressure'].apply(lambda x: self._convert_pressure(x, 'kPa', 'psi'))
                metadata.level_unit = 'psi'  # Update metadata unit
                logger.info(f"Converted pressure from kPa to psi for {file_path}")
                
            # Convert temperature if needed (to Celsius)
            if temp_unit_info['standard_unit'] == 'F':
                df['temperature'] = df['temperature'].apply(lambda x: self._convert_temperature(x, 'F', 'C'))
                metadata.temperature_unit = 'C'  # Update metadata unit
                logger.info(f"Converted temperature from F to C for {file_path}")
    
            return df, metadata
    
        except Exception as e:
            logger.error(f"Error reading XLE file {file_path}: {e}")
            raise
            
    def _get_dst_dates(self, year: int) -> Tuple[datetime, datetime]:
        """Get DST transition dates for a year"""
        # Spring forward (second Sunday in March)
        spring_date = datetime(year, 3, 8)  # Start with 8th
        while spring_date.weekday() != 6:  # Find second Sunday
            spring_date += timedelta(days=1)
        spring_date = spring_date.replace(hour=2)
        
        # Fall back (first Sunday in November)
        fall_date = datetime(year, 11, 1)  # Start with 1st
        while fall_date.weekday() != 6:  # Find first Sunday
            fall_date += timedelta(days=1)
        fall_date = fall_date.replace(hour=2)
        
        return spring_date, fall_date
    
    def _extract_metadata(self, root: ET.Element) -> SolinstMetadata:
        """Extract and validate metadata from XML structure"""
        try:
            instrument_info = root.find('.//Instrument_info')
            header_info = root.find('.//Instrument_info_data_header')
            ch1_info = root.find('.//Ch1_data_header')
            ch2_info = root.find('.//Ch2_data_header')
            
            self._validate_required_elements(instrument_info, header_info)
            
            # Parse dates
            start_time = datetime.strptime(
                header_info.findtext('Start_time'),
                '%Y/%m/%d %H:%M:%S'
            )
            
            stop_time = datetime.strptime(
                header_info.findtext('Stop_time'),
                '%Y/%m/%d %H:%M:%S'
            )
            
            return SolinstMetadata(
                instrument_type=instrument_info.findtext('Instrument_type'),
                model_number=instrument_info.findtext('Model_number'),
                serial_number=instrument_info.findtext('Serial_number'),
                project_id=header_info.findtext('Project_ID'),
                location=header_info.findtext('Location'),
                start_time=start_time,
                stop_time=stop_time,
                sample_rate=int(header_info.findtext('Sample_rate')),
                num_log=int(header_info.findtext('Num_log')),
                level_unit=ch1_info.findtext('Unit'),
                temperature_unit=ch2_info.findtext('Unit'),
                firmware=instrument_info.findtext('Firmware'),
                battery_voltage=float(instrument_info.findtext('Battery_voltage', '0'))
            )
            
        except (AttributeError, ValueError) as e:
            logger.error(f"Error extracting metadata: {e}")
            raise ValueError(f"Invalid metadata structure: {e}")

    def _validate_required_elements(self, instrument_info: ET.Element, 
                                    header_info: ET.Element):
        """Validate presence of required XML elements"""
        if any(element is None for element in [instrument_info, header_info]):
            raise ValueError("Missing required XML sections")

        for section, elements in self.required_elements.items():
            for element in elements:
                if section == 'instrument' and instrument_info.findtext(element) is None:
                    raise ValueError(f"Missing required instrument element: {element}")
                elif section == 'header' and header_info.findtext(element) is None:
                    raise ValueError(f"Missing required header element: {element}")

    def is_barologger(self, metadata: SolinstMetadata) -> bool:
        """
        Check if the file is from a barologger based on metadata
        
        Now also considers the level/pressure unit:
        - Files with pressure units (kPa, psi) are considered barologgers
        - Files with level units (m, ft) are considered leveloggers
        """
        instrument_type = metadata.instrument_type
        model_number = metadata.model_number.strip() if metadata.model_number else ""
        level_unit = self._normalize_unit(metadata.level_unit)
        
        # Check if unit indicates pressure measurement (barologger)
        unit_info = self._detect_unit_type(level_unit)
        if unit_info['unit_type'] == 'pressure':
            return True
        
        # Also check the model number as before
        if instrument_type in self.BAROLOGGER_TYPES:
            valid_models = self.BAROLOGGER_TYPES[instrument_type]
            if any(model_number.startswith(valid_model) for valid_model in valid_models):
                return True
            
        return False

    def get_file_metadata(self, file_path: Path) -> Tuple[SolinstMetadata, pd.DataFrame]:
        """
        Get file metadata without loading full dataset.
        Returns metadata and a small preview DataFrame with first/last few readings
        """
        try:
            # First attempt - try parsing directly
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except ET.ParseError as xml_error:
                # If parsing fails, try to fix temperature unit issues
                logger.info(f"XML parsing failed on first attempt, trying to fix temperature unit: {xml_error}")
                
                # Read the file content
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                # Look for temperature unit with potential special character before 'C'
                # Using a regex that looks for <Unit> followed by any character and then C</Unit>
                import re
                modified_content = re.sub(r'<Unit>([^<]*?)C</Unit>', r'<Unit>C</Unit>', content)
                
                # Parse the modified content
                try:
                    root = ET.fromstring(modified_content)
                except ET.ParseError as retry_error:
                    # If it still fails, log and re-raise the original error
                    logger.error(f"Failed to parse XML even after attempting fix: {retry_error}")
                    raise xml_error
                
            metadata = self._extract_metadata(root)
            
            # Get first and last few readings for preview
            log_entries = []
            # Use iterparse on the file or on the modified content if we had to fix it
            if 'modified_content' in locals():
                # If we had to modify the content, use StringIO to parse it
                from io import StringIO
                context = ET.iterparse(StringIO(modified_content), events=("end",))
            else:
                # Otherwise use the original file
                context = ET.iterparse(file_path, events=("end",))
                
            for event, elem in context:
                if elem.tag == "Log":
                    entry = {
                        'timestamp': f"{elem.findtext('Date')} {elem.findtext('Time')}",
                        'pressure': elem.findtext('ch1'),
                        'temperature': elem.findtext('ch2')
                    }
                    log_entries.append(entry)
                    
                    # Only get first and last few readings
                    if len(log_entries) >= 5:
                        break

            # Create preview DataFrame
            preview_df = pd.DataFrame(log_entries)
            if not preview_df.empty:
                # Use standard datetime parsing without the deprecated parameter
                preview_df['timestamp'] = pd.to_datetime(preview_df['timestamp'])
                preview_df['pressure'] = pd.to_numeric(preview_df['pressure'], errors='coerce')
                preview_df['temperature'] = pd.to_numeric(preview_df['temperature'], errors='coerce')

            return metadata, preview_df

        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            raise