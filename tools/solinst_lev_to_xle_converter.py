import os
import sys
import re
import xml.dom.minidom
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# GUI imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                            QCheckBox, QProgressBar, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Set up logging
logger = logging.getLogger(__name__)

class LevToXleConverter:
    """
    Converts Solinst .lev format files to .xle XML format
    """
    
    def __init__(self):
        """Initialize converter"""
        # Patterns for extracting sections from .lev files
        self.section_patterns = {
            'instrument_info': r'\[Instrument info\](.*?)(?=\[|\[Instrument info from data header\])',
            'channel_1': r'\[Channel 1\](.*?)(?=\[)',
            'channel_2': r'\[Channel 2\](.*?)(?=\[)',
            'instrument_data_header': r'\[Instrument info from data header\](.*?)(?=\[)',
            'channel_1_data_header': r'\[CHANNEL 1 from data header\](.*?)(?=\[)',
            'channel_2_data_header': r'\[CHANNEL 2 from data header\](.*?)(?=\[)',
            'data': r'\[Data\](.*?)(?=$)',
        }
        
        # Patterns for extracting key-value pairs
        self.kv_pattern = re.compile(r'^\s*([^=]+)=(.*)$', re.MULTILINE)
        
    def scan_and_convert(self, root_dir: str, recursive: bool = True) -> List[str]:
        """
        Scans directory for .lev files and converts them to .xle
        
        Args:
            root_dir: Directory to scan
            recursive: Whether to scan subfolders
            
        Returns:
            List of converted file paths
        """
        converted_files = []
        root_path = Path(root_dir)
        
        # Determine the pattern for file discovery
        pattern = "**/*.lev" if recursive else "*.lev"
        
        # Find all .lev files
        for lev_file in root_path.glob(pattern):
            try:
                xle_file = self.convert_file(str(lev_file))
                converted_files.append(xle_file)
                logger.info(f"Converted {lev_file} to {xle_file}")
            except Exception as e:
                logger.error(f"Error converting {lev_file}: {e}")
                
        return converted_files
        
    def convert_file(self, lev_file_path: str) -> str:
        """
        Convert a single .lev file to .xle
        
        Args:
            lev_file_path: Path to .lev file
            
        Returns:
            Path to the created .xle file
        """
        # Parse the .lev file
        parsed_data = self._parse_lev_file(lev_file_path)
        
        # Create XML content
        xml_content = self._create_xle_content(parsed_data)
        
        # Format the XML with proper indentation for readability
        pretty_xml = xml.dom.minidom.parseString(xml_content).toprettyxml(indent="    ")
        
        # Save as .xle file (same name, different extension)
        xle_file_path = str(Path(lev_file_path).with_suffix('.xle'))
        with open(xle_file_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        return xle_file_path
        
    def _parse_lev_file(self, file_path: str) -> Dict:
        """
        Parse .lev file contents into a structured dictionary
        
        Args:
            file_path: Path to .lev file
            
        Returns:
            Dictionary with parsed data
        """
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Extract file header info (before BEGINNING OF DATA)
        header_match = re.search(r'Data file for DataLogger\..*?==+\s+BEGINNING OF DATA\s+==+', 
                               content, re.DOTALL)
        header_text = header_match.group(0) if header_match else ""
        
        # Parse header
        file_info = {}
        for line in header_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                file_info[key.strip()] = value.strip()
        
        # Extract sections using regex
        sections = {}
        for section_name, pattern in self.section_patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()
        
        # Parse key-value pairs in each section
        parsed_sections = {}
        for section_name, section_content in sections.items():
            if section_name == 'data':
                # Special handling for data section
                data_lines = section_content.strip().split('\n')
                # First line might contain the number of data points
                num_points = int(data_lines[0]) if data_lines and data_lines[0].strip().isdigit() else 0
                
                # Parse data rows
                data_points = []
                for i, line in enumerate(data_lines[1:], 1):  # Skip the first line with count
                    if not line.strip():
                        continue
                        
                    # Skip lines containing "END OF DATA FILE OF DATALOGGER"
                    if "END OF DATA FILE OF DATALOGGER" in line:
                        continue
                        
                    parts = line.split()
                    if len(parts) >= 3:  # Make sure we have date, time, and at least one value
                        date_str = parts[0]
                        time_str = parts[1]
                        ch1_val = parts[2]
                        ch2_val = parts[3] if len(parts) > 3 else ""
                        
                        data_point = {
                            'id': i,
                            'date': date_str,
                            'time': time_str,
                            'ch1': ch1_val,
                            'ch2': ch2_val
                        }
                        data_points.append(data_point)
                
                parsed_sections[section_name] = {
                    'count': num_points,
                    'points': data_points
                }
            else:
                # Regular key-value parsing
                pairs = {}
                for match in self.kv_pattern.finditer(section_content):
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    pairs[key] = value
                parsed_sections[section_name] = pairs
        
        return {
            'file_info': file_info,
            'sections': parsed_sections
        }
        
    def _create_xle_content(self, parsed_data: Dict) -> str:
        """
        Create XML content for .xle file from parsed data
        
        Args:
            parsed_data: Dictionary with parsed .lev data
            
        Returns:
            XML content as string
        """
        # Create root element
        root = ET.Element("Body_xle")
        
        # Add File_info section
        file_info = ET.SubElement(root, "File_info")
        ET.SubElement(file_info, "Company").text = parsed_data['file_info'].get('COMPANY', '')
        ET.SubElement(file_info, "LICENCE").text = parsed_data['file_info'].get('LICENSE', '')
        
        # Parse and format date/time
        date_str = parsed_data['file_info'].get('DATE', '')
        time_str = parsed_data['file_info'].get('TIME', '')
        
        # Convert date format from MM/DD/YY to YYYY/MM/DD if needed
        if date_str and '/' in date_str:
            try:
                date_parts = date_str.split('/')
                if len(date_parts) == 3:
                    if len(date_parts[2]) == 2:  # YY format
                        year = f"20{date_parts[2]}" if int(date_parts[2]) < 50 else f"19{date_parts[2]}"
                    else:
                        year = date_parts[2]
                    date_str = f"{year}/{date_parts[0]}/{date_parts[1]}"
            except:
                # If parsing fails, leave as is
                pass
                
        ET.SubElement(file_info, "Date").text = date_str
        ET.SubElement(file_info, "Time").text = time_str
        ET.SubElement(file_info, "FileName").text = parsed_data['file_info'].get('FILENAME', '')
        ET.SubElement(file_info, "Created_by").text = parsed_data['file_info'].get('CREATED BY', '')
        
        # Add Instrument_info section
        sections = parsed_data['sections']
        instrument_info = ET.SubElement(root, "Instrument_info")
        instr_section = sections.get('instrument_info', {})
        
        ET.SubElement(instrument_info, "Instrument_type").text = instr_section.get('Instrument type', '')
        
        # Determine model number based on units from Channel 1
        ch1_section = sections.get('channel_1_data_header', {})
        ch1_unit = ch1_section.get('Unit', '').lower().strip()
        
        # Determine if it's a barologger (pressure) or levelogger (level) based on unit
        if ch1_unit in ['kpa', 'psi', 'bar']:
            # Barologger - uses pressure units
            model_number = "M1.5"
            logger.info(f"Detected pressure unit '{ch1_unit}', setting model to M1.5 (Barologger)")
        elif ch1_unit in ['m', 'ft', 'meter', 'meters', 'feet']:
            # Levelogger - uses level units
            model_number = "M10"
            logger.info(f"Detected level unit '{ch1_unit}', setting model to M10 (Levelogger)")
        else:
            # Default case - can't determine from unit
            model_number = "M1.5"  # Default to M1.5
            logger.warning(f"Could not determine logger type from unit '{ch1_unit}', defaulting to M1.5")
        
        ET.SubElement(instrument_info, "Model_number").text = model_number
        
        ET.SubElement(instrument_info, "Instrument_state").text = instr_section.get('Instrument state', '').split('=')[0].strip()
        
        # Standardize the serial number format
        serial_number = instr_section.get('Serial number', '')
        
        # Use a more robust regex approach to extract just the numeric part
        # This will handle formats like "100-2079142 2", "0-2079143 2", etc.
        import re
        match = re.search(r'(\d+-)?(\d+)(?:\s|$)', serial_number)
        if match and match.group(2):
            serial_number = match.group(2)  # Get just the numeric part
        elif '..' in serial_number:  # Keep the original handling for ".." format
            serial_number = serial_number.split('..')[1].strip()
        
        ET.SubElement(instrument_info, "Serial_number").text = serial_number
        
        ET.SubElement(instrument_info, "Battery_level").text = "100"  # Default value
        ET.SubElement(instrument_info, "Channel").text = instr_section.get('Channel', '')
        ET.SubElement(instrument_info, "Firmware").text = instr_section.get('FW', '')
        
        # Add Instrument_info_data_header section
        data_header = ET.SubElement(root, "Instrument_info_data_header")
        header_section = sections.get('instrument_data_header', {})
        
        # Use location as Project_ID if available
        location = header_section.get('Location', '')
        ET.SubElement(data_header, "Project_ID").text = location
        ET.SubElement(data_header, "Location").text = location
        ET.SubElement(data_header, "Latitude").text = "0.000"  # Default
        ET.SubElement(data_header, "Longtitude").text = "0.000"  # Default
        ET.SubElement(data_header, "Sample_rate").text = header_section.get('Sample Rate', '')
        ET.SubElement(data_header, "Sample_mode").text = header_section.get('Sample Mode', '0')
        ET.SubElement(data_header, "Event_ch").text = "0"  # Default
        ET.SubElement(data_header, "Event_threshold").text = "0.000000"  # Default
        ET.SubElement(data_header, "Schedule")
        
        # Parse and format start/stop times
        start_time = header_section.get('Start Time', '')
        stop_time = header_section.get('Stop Time', '')
        
        # Convert date format if needed (MM/DD/YYYY to YYYY/MM/DD)
        for time_field, value in [('Start Time', start_time), ('Stop Time', stop_time)]:
            if value and '/' in value:
                try:
                    parts = value.split()
                    if len(parts) == 2:  # Has date and time
                        date_parts = parts[0].split('/')
                        if len(date_parts) == 3:
                            new_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
                            if time_field == 'Start Time':
                                start_time = f"{new_date} {parts[1]}"
                            else:
                                stop_time = f"{new_date} {parts[1]}"
                except:
                    # If parsing fails, leave as is
                    pass
        
        ET.SubElement(data_header, "Start_time").text = start_time
        ET.SubElement(data_header, "Stop_time").text = stop_time
        
        # Get number of data points
        data_section = sections.get('data', {})
        num_log = str(data_section.get('count', 0)) if isinstance(data_section, dict) else "0"
        ET.SubElement(data_header, "Num_log").text = num_log
        
        # Add Ch1_data_header section
        ch1_header = ET.SubElement(root, "Ch1_data_header")
        ch1_section = sections.get('channel_1_data_header', {})
        
        ET.SubElement(ch1_header, "Identification").text = ch1_section.get('Identification', 'LEVEL')
        
        # Standardize units - convert to ft for level or psi for pressure
        original_unit = ch1_section.get('Unit', '')
        standard_unit = original_unit  # Default to keeping original
        
        # Convert units if needed
        if original_unit.lower().strip() == 'm':
            standard_unit = 'ft'
        elif original_unit.lower().strip() == 'kpa':
            standard_unit = 'psi'
            
        ET.SubElement(ch1_header, "Unit").text = standard_unit
        ET.SubElement(ch1_header, "Parameters")
        
        # Add Ch2_data_header section
        ch2_header = ET.SubElement(root, "Ch2_data_header")
        ch2_section = sections.get('channel_2_data_header', {})
        
        ET.SubElement(ch2_header, "Identification").text = ch2_section.get('Identification', 'TEMPERATURE')
        
        # Fix temperature unit - ensure there's no unrecognized character before 'C'
        temp_unit = ch2_section.get('Unit', '')
        if temp_unit and 'C' in temp_unit:
            # Replace with clean 'C' - no space or unusual character
            temp_unit = 'C'
        ET.SubElement(ch2_header, "Unit").text = temp_unit
        
        ET.SubElement(ch2_header, "Parameters")
        
        # Add Data section
        data_elem = ET.SubElement(root, "Data")
        
        # Add Log entries
        if isinstance(data_section, dict) and 'points' in data_section:
            for point in data_section['points']:
                log_entry = ET.SubElement(data_elem, "Log")
                log_entry.set("id", str(point['id']))
                
                ET.SubElement(log_entry, "Date").text = point['date']
                ET.SubElement(log_entry, "Time").text = point['time']
                ET.SubElement(log_entry, "ms").text = "0"
                
                # Convert units if needed
                pressure_value = point['ch1']
                if ch1_unit == 'm':
                    # Convert meters to feet
                    try:
                        value_m = float(pressure_value)
                        value_ft = value_m * 3.28084  # Meters to feet conversion
                        pressure_value = f"{value_ft:.6f}"  # Format with 6 decimal places
                    except (ValueError, TypeError):
                        # If conversion fails, keep original value
                        pass
                elif ch1_unit == 'kpa':
                    # Convert kPa to psi
                    try:
                        value_kpa = float(pressure_value)
                        value_psi = value_kpa * 0.145038  # kPa to PSI conversion
                        pressure_value = f"{value_psi:.6f}"  # Format with 6 decimal places
                    except (ValueError, TypeError):
                        # If conversion fails, keep original value
                        pass
                        
                ET.SubElement(log_entry, "ch1").text = pressure_value
                
                # Always keep temperature in Celsius - no conversion in LEV files
                ET.SubElement(log_entry, "ch2").text = point['ch2']
        
        # Convert ElementTree to string
        return ET.tostring(root, encoding='unicode')


class ConverterWorker(QThread):
    """Worker thread to handle the conversion process without freezing UI"""
    progress = pyqtSignal(int)
    file_progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str, int)  # Message, total files found
    
    def __init__(self, folder_path, recursive=True):
        super().__init__()
        self.folder_path = folder_path
        self.recursive = recursive
        self.converter = LevToXleConverter()
        
    def run(self):
        try:
            # Update status about starting the scan
            self.file_progress.emit("Scanning for LEV files...")
            
            # First count the total number of files to process
            self.file_progress.emit("Counting files in directory...")
            total_files = 0
            pattern = "**/*.lev" if self.recursive else "*.lev"
            
            # Show progress while counting
            scan_count = 0
            scan_dirs = set()
            for lev_file in Path(self.folder_path).glob(pattern):
                total_files += 1
                # Update status every 10 files found
                if total_files % 10 == 0:
                    self.file_progress.emit(f"Found {total_files} LEV files so far...")
                
                # Keep track of unique directories
                parent_dir = str(lev_file.parent)
                if parent_dir not in scan_dirs:
                    scan_dirs.add(parent_dir)
                    scan_count += 1
                    if scan_count % 5 == 0:  # Every 5 directories
                        self.file_progress.emit(f"Scanning directory {scan_count}: {os.path.basename(parent_dir)}")
            
            # Finished counting
            self.status_update.emit(f"Found {total_files} LEV files in {len(scan_dirs)} directories", total_files)
                
            if total_files == 0:
                self.file_progress.emit("No LEV files found.")
                self.finished.emit([])
                return
                
            # Modified converter method to support progress updates
            converted_files = []
            current_count = 0
            
            for lev_file in Path(self.folder_path).glob(pattern):
                try:
                    # Update progress information
                    self.file_progress.emit(f"Converting ({current_count+1}/{total_files}): {lev_file.name}")
                    
                    # Convert the file
                    xle_file = self.converter.convert_file(str(lev_file))
                    converted_files.append(xle_file)
                    
                    # Update progress percentage
                    current_count += 1
                    progress_percent = int((current_count / total_files) * 100)
                    self.progress.emit(progress_percent)
                    
                except Exception as e:
                    self.error.emit(f"Error converting {lev_file}: {str(e)}")
            
            self.finished.emit(converted_files)
            
        except Exception as e:
            import traceback
            self.error.emit(f"Conversion error: {str(e)}\n{traceback.format_exc()}")


class LevToXleConverterApp(QMainWindow):
    """Main application window for the LEV to XLE converter"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Solinst LEV to XLE Converter")
        self.setMinimumSize(650, 350)  # Increased size for more information
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)
        select_folder_btn = QPushButton("Select Folder")
        select_folder_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(QLabel("Input:"))
        folder_layout.addWidget(self.folder_label, 1) # Stretch factor
        folder_layout.addWidget(select_folder_btn)
        main_layout.addLayout(folder_layout)
        
        # Recursive option
        recursive_layout = QHBoxLayout()
        self.recursive_checkbox = QCheckBox("Include subfolders")
        self.recursive_checkbox.setChecked(True)
        recursive_layout.addWidget(self.recursive_checkbox)
        recursive_layout.addStretch()
        main_layout.addLayout(recursive_layout)
        
        # Status area - added detailed section
        status_frame = QGroupBox("Status")
        status_layout = QVBoxLayout()
        status_frame.setLayout(status_layout)
        
        self.status_label = QLabel("Select a folder containing .lev files to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        self.file_count_label = QLabel("No files found yet")
        
        # File list progress with more details
        self.file_label = QLabel("Ready")
        self.file_label.setWordWrap(True)
        self.file_label.setMinimumHeight(50)  # Make it taller to fit multiple lines
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.file_count_label)
        status_layout.addWidget(self.file_label)
        
        main_layout.addWidget(status_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Convert button
        convert_btn = QPushButton("Convert Files")
        convert_btn.clicked.connect(self.start_conversion)
        main_layout.addWidget(convert_btn)
        
        # Store the selected folder path
        self.folder_path = None
        
        # Worker thread for conversion
        self.worker = None
        
    def select_folder(self):
        """Open dialog to select folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with LEV Files")
        if folder:
            self.folder_path = folder
            self.folder_label.setText(folder)
            self.status_label.setText(f"Ready to convert .lev files in {os.path.basename(folder)}")
            self.progress_bar.setValue(0)
    
    def start_conversion(self):
        """Start the conversion process"""
        if not self.folder_path:
            QMessageBox.warning(self, "No Folder Selected", 
                               "Please select a folder containing .lev files first.")
            return
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting conversion...")
        self.file_count_label.setText("Scanning for files...")
        self.file_label.setText("Preparing to scan directory...")
        
        # Create and start worker thread
        recursive = self.recursive_checkbox.isChecked()
        self.worker = ConverterWorker(self.folder_path, recursive)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.file_progress.connect(self.update_file_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(self.show_error)
        self.worker.status_update.connect(self.update_file_count)
        
        # Start conversion
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_file_progress(self, file_info):
        """Update the current file being processed"""
        self.file_label.setText(file_info)
    
    def update_file_count(self, message, total_files):
        """Update the file count label and status"""
        self.file_count_label.setText(message)
        if total_files > 0:
            self.status_label.setText(f"Converting {total_files} LEV files...")
        else:
            self.status_label.setText("No LEV files found in the selected folder.")
        
    def conversion_finished(self, converted_files):
        """Handle completion of conversion"""
        count = len(converted_files)
        
        if count == 0:
            self.status_label.setText("No .lev files found in the selected folder.")
        else:
            self.status_label.setText(f"Conversion complete. Converted {count} files.")
            
        self.progress_bar.setValue(100)
        
        # Show a message box with the results
        QMessageBox.information(
            self, 
            "Conversion Complete",
            f"Successfully converted {count} files.\n\n" + 
            ("No files were converted." if count == 0 else 
             f"The files have been saved to the same folder(s) as the original .lev files, with .xle extension.")
        )
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Conversion Error", error_message)
        self.status_label.setText("Conversion failed. See error message.")


# Command-line interface handling
def process_command_line():
    """Process command line arguments if script is run directly"""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        recursive = True if len(sys.argv) <= 2 or sys.argv[2].lower() == 'true' else False
        
        converter = LevToXleConverter()
        converted = converter.scan_and_convert(directory, recursive)
        print(f"Converted {len(converted)} files:")
        for file in converted:
            print(f" - {file}")
        return True
    return False


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Check if we should run command line mode
    if not process_command_line():
        # No command line arguments, start GUI
        app = QApplication(sys.argv)
        window = LevToXleConverterApp()
        window.show()
        sys.exit(app.exec_())
