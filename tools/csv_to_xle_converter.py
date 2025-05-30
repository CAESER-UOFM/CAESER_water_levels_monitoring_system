import os
import sys
import re
import csv
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

class CsvToXleConverter:
    """
    Converts CSV format files with water level data to .xle XML format
    """
    
    def __init__(self):
        """Initialize converter"""
        pass
        
    def scan_and_convert(self, root_dir: str, recursive: bool = True) -> List[str]:
        """
        Scans directory for .csv files and converts them to .xle
        
        Args:
            root_dir: Directory to scan
            recursive: Whether to scan subfolders
            
        Returns:
            List of converted file paths
        """
        converted_files = []
        root_path = Path(root_dir)
        
        # Determine the pattern for file discovery
        pattern = "**/*.csv" if recursive else "*.csv"
        
        # Find all .csv files
        for csv_file in root_path.glob(pattern):
            try:
                xle_file = self.convert_file(str(csv_file))
                converted_files.append(xle_file)
                logger.info(f"Converted {csv_file} to {xle_file}")
            except Exception as e:
                logger.error(f"Error converting {csv_file}: {e}")
                
        return converted_files
        
    def convert_file(self, csv_file_path: str) -> str:
        """
        Convert a single .csv file to .xle
        
        Args:
            csv_file_path: Path to .csv file
            
        Returns:
            Path to the created .xle file
        """
        # Parse the .csv file
        parsed_data = self._parse_csv_file(csv_file_path)
        
        # Create XML content
        xml_content = self._create_xle_content(parsed_data)
        
        # Format the XML with proper indentation for readability
        pretty_xml = xml.dom.minidom.parseString(xml_content).toprettyxml(indent="    ")
        
        # Save as .xle file (same name, different extension)
        xle_file_path = str(Path(csv_file_path).with_suffix('.xle'))
        with open(xle_file_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        return xle_file_path
        
    def _parse_csv_file(self, file_path: str) -> Dict:
        """
        Parse CSV file contents into a structured dictionary
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary with parsed data
        """
        metadata = {}
        data_points = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
            # Skip empty lines
            lines = [line.strip() for line in lines if line.strip()]
            
            # A simple approach to extract metadata - look for key rows and get the value below them
            # Initialize metadata with default units
            metadata["Level Unit"] = "ft"
            metadata["Temperature Unit"] = "°C"
            
            # Find key headers and extract values from cells below
            for i in range(len(lines) - 1):  # -1 to ensure we don't go out of bounds
                current_line = lines[i].lower()
                
                # Check for serial number
                if "serial" in current_line and "number" in current_line:
                    metadata["Serial number"] = lines[i+1].strip()
                    
                # Check for Project ID
                if "project" in current_line and "id" in current_line:
                    metadata["Project ID"] = lines[i+1].strip()
                    
                # Check for Location 
                if "location" in current_line:
                    metadata["Location"] = lines[i+1].strip()
                    
                # Check for level unit if specified
                if "level" in current_line and "unit" in current_line:
                    next_line = lines[i+1].lower()
                    if "ft" in next_line:
                        metadata["Level Unit"] = "ft"
                    elif "m" in next_line:
                        metadata["Level Unit"] = "m"
                        
                # Check for temperature unit if specified
                if "temperature" in current_line and "unit" in current_line:
                    next_line = lines[i+1].lower()
                    if "c" in next_line:
                        metadata["Temperature Unit"] = "°C"
                    elif "f" in next_line:
                        metadata["Temperature Unit"] = "°F"
            
            # Now find the data section - look for a line with Date and Time
            data_start_line = -1
            for i, line in enumerate(lines):
                if "Date" in line and "Time" in line:
                    data_start_line = i
                    break
                    
            # If we still couldn't find the data section, try with just Date
            if data_start_line < 0:
                for i, line in enumerate(lines):
                    if "Date" in line:
                        data_start_line = i
                        break
            
            # If we still couldn't find it, raise an error
            if data_start_line < 0:
                raise ValueError("Could not find data section in CSV file")
            
            # Parse the header row to determine column indexes
            header_row = lines[data_start_line]
            
            # Try different delimiters for the header
            if "\t" in header_row:
                header_parts = header_row.split("\t")
            elif "," in header_row:
                header_parts = header_row.split(",")
            else:
                header_parts = header_row.split()
                
            header_parts = [h.strip() for h in header_parts if h.strip()]
            
            # Find column indexes
            date_idx = -1
            time_idx = -1
            ms_idx = -1
            level_idx = -1
            temp_idx = -1
            
            for i, header in enumerate(header_parts):
                header_lower = header.lower()
                if "date" in header_lower:
                    date_idx = i
                elif "time" in header_lower:
                    time_idx = i
                elif "ms" == header_lower:
                    ms_idx = i
                elif "level" in header_lower:
                    level_idx = i
                elif any(term in header_lower for term in ["temperature", "temp", "tempera"]):
                    temp_idx = i
            
            # If we couldn't find critical columns, try to infer them by position
            if date_idx == -1 and len(header_parts) > 0:
                date_idx = 0
            if time_idx == -1 and len(header_parts) > 1:
                time_idx = 1
            if level_idx == -1 and len(header_parts) > 3:
                level_idx = 3
            if temp_idx == -1 and len(header_parts) > 4:
                temp_idx = 4
            
            # Parse data rows - start from the line after the header
            data_id = 1
            
            for line in lines[data_start_line+1:]:
                if not line.strip():
                    continue
                
                # Try different delimiters (tabs, commas, or whitespace)
                if "\t" in line:
                    parts = line.split("\t")
                elif "," in line:
                    parts = line.split(",")
                else:
                    parts = line.split()
                
                parts = [p.strip() for p in parts]
                
                # Check if enough parts for a valid data row
                if len(parts) < max(date_idx, time_idx, level_idx, temp_idx) + 1:
                    continue
                
                try:
                    date_val = parts[date_idx] if date_idx >= 0 and date_idx < len(parts) else ""
                    time_val = parts[time_idx] if time_idx >= 0 and time_idx < len(parts) else ""
                    ms_val = parts[ms_idx] if ms_idx >= 0 and ms_idx < len(parts) else "0"
                    level_val = parts[level_idx] if level_idx >= 0 and level_idx < len(parts) else ""
                    temp_val = parts[temp_idx] if temp_idx >= 0 and temp_idx < len(parts) else ""
                    
                    # Validate and clean up data
                    if not ms_val or not ms_val.isdigit():
                        ms_val = "0"
                    
                    data_point = {
                        'id': data_id,
                        'date': date_val,
                        'time': time_val,
                        'ms': ms_val,
                        'level': level_val,
                        'temperature': temp_val
                    }
                    
                    data_points.append(data_point)
                    data_id += 1
                    
                except Exception as e:
                    logger.warning(f"Error parsing data row: {e}")
            
            # Check if we found any data points
            if not data_points:
                raise ValueError("No valid data points found in CSV file")
            
            # Return the parsed data
            return {
                'metadata': metadata,
                'data_points': data_points
            }
            
        except Exception as e:
            logger.error(f"Error parsing CSV file {file_path}: {e}")
            raise
        
    def _create_xle_content(self, parsed_data: Dict) -> str:
        """
        Create XML content for .xle file from parsed data
        
        Args:
            parsed_data: Dictionary with parsed CSV data
            
        Returns:
            XML content as string
        """
        # Create root element
        root = ET.Element("Body_xle")
        
        # Add File_info section
        file_info = ET.SubElement(root, "File_info")
        ET.SubElement(file_info, "Company").text = ""
        ET.SubElement(file_info, "LICENCE").text = ""
        
        # Get current date/time for file creation
        now = datetime.now()
        current_date = now.strftime("%Y/%m/%d")
        current_time = now.strftime("%H:%M:%S")
        
        ET.SubElement(file_info, "Date").text = current_date
        ET.SubElement(file_info, "Time").text = current_time
        ET.SubElement(file_info, "FileName").text = ""
        ET.SubElement(file_info, "Created_by").text = "CSV to XLE Converter"
        ET.SubElement(file_info, "Downloaded_by").text = ""
        
        # Add Instrument_info section
        instrument_info = ET.SubElement(root, "Instrument_info")
        
        # Get metadata from parsed data
        metadata = parsed_data.get('metadata', {})
        print(f"Using metadata for XML creation: {metadata}")
        
        # Get serial number from metadata if available
        serial_number = metadata.get('Serial number', '')
        print(f"Serial number: {serial_number}")
        
        ET.SubElement(instrument_info, "Instrument_type").text = "L5_LT"
        ET.SubElement(instrument_info, "Model_number").text = "M10"
        ET.SubElement(instrument_info, "Instrument_state").text = "Stopped"
        ET.SubElement(instrument_info, "Serial_number").text = serial_number
        ET.SubElement(instrument_info, "Battery_level").text = "97"
        ET.SubElement(instrument_info, "Channel").text = "2"
        ET.SubElement(instrument_info, "Firmware").text = "1.003"
        
        # Add Instrument_info_data_header section
        data_header = ET.SubElement(root, "Instrument_info_data_header")
        
        # Get project ID and location from metadata
        project_id = metadata.get('Project ID', '')
        location = metadata.get('Location', '')
        print(f"Project ID: {project_id}, Location: {location}")
        
        ET.SubElement(data_header, "Project_ID").text = project_id
        ET.SubElement(data_header, "Location").text = location
        ET.SubElement(data_header, "Latitude").text = "0.000"
        ET.SubElement(data_header, "Longtitude").text = "0.000"
        ET.SubElement(data_header, "Sample_rate").text = "90000"
        ET.SubElement(data_header, "Sample_mode").text = "0"
        ET.SubElement(data_header, "Event_ch").text = "1"
        ET.SubElement(data_header, "Event_threshold").text = "0.000000"
        ET.SubElement(data_header, "Schedule").text = ""
        
        # Use default start and stop time based on the data
        data_points = parsed_data.get('data_points', [])
        
        start_date = ""
        start_time = ""
        stop_date = ""
        stop_time = ""
        
        if data_points:
            first_point = data_points[0]
            last_point = data_points[-1]
            
            # Parse and convert date/time to proper format
            try:
                # Get the date and time strings
                start_date_str = first_point.get('date', '')
                start_time_str = first_point.get('time', '')
                stop_date_str = last_point.get('date', '')
                stop_time_str = last_point.get('time', '')
                
                # Parse dates to proper format (YYYY/MM/DD)
                if start_date_str:
                    # Handle M/D/YYYY format
                    if '/' in start_date_str:
                        date_parts = start_date_str.split('/')
                        if len(date_parts) == 3:
                            # Convert MM/DD/YYYY to YYYY/MM/DD
                            month, day, year = date_parts
                            start_date = f"{year}/{month}/{day}"
                    else:
                        start_date = start_date_str
                
                if stop_date_str:
                    # Handle M/D/YYYY format
                    if '/' in stop_date_str:
                        date_parts = stop_date_str.split('/')
                        if len(date_parts) == 3:
                            # Convert MM/DD/YYYY to YYYY/MM/DD
                            month, day, year = date_parts
                            stop_date = f"{year}/{month}/{day}"
                    else:
                        stop_date = stop_date_str
                
                # Format times (remove AM/PM and ensure 24-hour format)
                if start_time_str:
                    # Remove AM/PM and convert to 24-hour if needed
                    start_time = self._format_time(start_time_str)
                
                if stop_time_str:
                    # Remove AM/PM and convert to 24-hour if needed
                    stop_time = self._format_time(stop_time_str)
                    
            except Exception as e:
                logger.warning(f"Error formatting date/time: {e}")
                # Use original values if parsing fails
                start_date = first_point.get('date', '')
                start_time = first_point.get('time', '')
                stop_date = last_point.get('date', '')
                stop_time = last_point.get('time', '')
        
        # Format start and stop times in YYYY/MM/DD HH:MM:SS format
        start_time_str = f"{start_date} {start_time}"
        stop_time_str = f"{stop_date} {stop_time}"
        
        ET.SubElement(data_header, "Start_time").text = start_time_str
        ET.SubElement(data_header, "Stop_time").text = stop_time_str
        ET.SubElement(data_header, "Num_log").text = str(len(data_points))
        
        # Add Ch1_data_header section for level/pressure
        ch1_header = ET.SubElement(root, "Ch1_data_header")
        
        ET.SubElement(ch1_header, "Identification").text = "LEVEL"
        
        # Use hard-coded value for level unit
        level_unit = "ft"
        ET.SubElement(ch1_header, "Unit").text = level_unit
        
        # Add Parameters with Offset
        parameters = ET.SubElement(ch1_header, "Parameters")
        offset = ET.SubElement(parameters, "Offset")
        offset.set("Val", "0.0000")
        offset.set("Unit", level_unit)
        
        # Add Ch2_data_header section for temperature
        ch2_header = ET.SubElement(root, "Ch2_data_header")
        
        ET.SubElement(ch2_header, "Identification").text = "TEMPERATURE"
        
        # Use hard-coded value for temperature unit
        temp_unit = "°C"
        ET.SubElement(ch2_header, "Unit").text = temp_unit
        ET.SubElement(ch2_header, "Parameters")
        
        # Add Data section
        data_elem = ET.SubElement(root, "Data")
        
        # Add Log entries
        for point in data_points:
            log_entry = ET.SubElement(data_elem, "Log")
            log_entry.set("id", str(point['id']))
            
            # Parse and format date
            date_str = point.get('date', '')
            time_str = point.get('time', '')
            
            # Convert date format from M/D/YYYY to YYYY/MM/DD if needed
            formatted_date = date_str
            try:
                if '/' in date_str:
                    date_parts = date_str.split('/')
                    if len(date_parts) == 3:
                        month, day, year = date_parts
                        formatted_date = f"{year}/{month}/{day}"
            except Exception as e:
                logger.warning(f"Error formatting date: {e}")
                formatted_date = date_str
            
            # Format time (remove AM/PM and ensure 24-hour format)
            formatted_time = self._format_time(time_str)
            
            # Add date and time as separate elements
            ET.SubElement(log_entry, "Date").text = formatted_date
            ET.SubElement(log_entry, "Time").text = formatted_time
            ET.SubElement(log_entry, "ms").text = point['ms']
            
            # Level data (ch1) - ensure it's populated
            ET.SubElement(log_entry, "ch1").text = point['level']
            
            # Temperature data (ch2) - ensure it's populated
            ET.SubElement(log_entry, "ch2").text = point['temperature']
        
        # Convert ElementTree to string
        return ET.tostring(root, encoding='unicode')
    
    def _format_time(self, time_str: str) -> str:
        """
        Format time string to 24-hour format without AM/PM
        
        Args:
            time_str: The time string to format
            
        Returns:
            Formatted time string
        """
        try:
            # Return empty string for empty input
            if not time_str:
                return ""
                
            # Check if the time has AM/PM
            if ' PM' in time_str.upper():
                # Extract HH:MM:SS part
                t = time_str.upper().split(' PM')[0].strip()
                
                # Parse time
                if ':' in t:
                    parts = t.split(':')
                    if len(parts) >= 2:
                        hour = int(parts[0])
                        minute = parts[1]
                        
                        # Convert to 24-hour format (if not already 12)
                        if hour < 12:
                            hour += 12
                            
                        # Format hour with leading zero if needed
                        hour_str = f"{hour:02d}"
                        
                        # Handle seconds if present
                        if len(parts) > 2:
                            seconds = parts[2]
                            return f"{hour_str}:{minute}:{seconds}"
                        else:
                            return f"{hour_str}:{minute}:00"
                    
            elif ' AM' in time_str.upper():
                # Extract HH:MM:SS part
                t = time_str.upper().split(' AM')[0].strip()
                
                # Parse time
                if ':' in t:
                    parts = t.split(':')
                    if len(parts) >= 2:
                        hour = int(parts[0])
                        minute = parts[1]
                        
                        # Convert 12 AM to 00 hours
                        if hour == 12:
                            hour = 0
                            
                        # Format hour with leading zero if needed
                        hour_str = f"{hour:02d}"
                        
                        # Handle seconds if present
                        if len(parts) > 2:
                            seconds = parts[2]
                            return f"{hour_str}:{minute}:{seconds}"
                        else:
                            return f"{hour_str}:{minute}:00"
            
            # Handle case without AM/PM - assume it's already in correct format or just HH:MM
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:  # Only HH:MM
                    return f"{time_str}:00"
                    
            # Return as is if we couldn't parse it
            return time_str
                    
        except Exception as e:
            logger.warning(f"Error formatting time {time_str}: {e}")
            return time_str


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
        self.converter = CsvToXleConverter()
        
    def run(self):
        try:
            # Update status about starting the scan
            self.file_progress.emit("Scanning for CSV files...")
            
            # First count the total number of files to process
            self.file_progress.emit("Counting files in directory...")
            total_files = 0
            pattern = "**/*.csv" if self.recursive else "*.csv"
            
            # Show progress while counting
            scan_count = 0
            scan_dirs = set()
            for csv_file in Path(self.folder_path).glob(pattern):
                total_files += 1
                # Update status every 10 files found
                if total_files % 10 == 0:
                    self.file_progress.emit(f"Found {total_files} CSV files so far...")
                
                # Keep track of unique directories
                parent_dir = str(csv_file.parent)
                if parent_dir not in scan_dirs:
                    scan_dirs.add(parent_dir)
                    scan_count += 1
                    if scan_count % 5 == 0:  # Every 5 directories
                        self.file_progress.emit(f"Scanning directory {scan_count}: {os.path.basename(parent_dir)}")
            
            # Finished counting
            self.status_update.emit(f"Found {total_files} CSV files in {len(scan_dirs)} directories", total_files)
                
            if total_files == 0:
                self.finished.emit([])
                return
                
            # Modified converter method to support progress updates
            converted_files = []
            current_count = 0
            
            for csv_file in Path(self.folder_path).glob(pattern):
                try:
                    # Update progress information
                    self.file_progress.emit(f"Converting: {csv_file.name}")
                    
                    # Convert the file
                    xle_file = self.converter.convert_file(str(csv_file))
                    converted_files.append(xle_file)
                    
                    # Update progress percentage
                    current_count += 1
                    progress_percent = int((current_count / total_files) * 100)
                    self.progress.emit(progress_percent)
                    
                except Exception as e:
                    self.error.emit(f"Error converting {csv_file}: {str(e)}")
            
            self.finished.emit(converted_files)
            
        except Exception as e:
            self.error.emit(f"Conversion error: {str(e)}")


class CsvToXleConverterApp(QMainWindow):
    """Main application window for the CSV to XLE converter"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("CSV to XLE Converter")
        self.setMinimumSize(550, 250)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Remove the metadata explanation label completely
        
        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)
        select_folder_btn = QPushButton("Select Folder")
        select_folder_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(select_folder_btn)
        main_layout.addLayout(folder_layout)
        
        # Recursive option
        recursive_layout = QHBoxLayout()
        self.recursive_checkbox = QCheckBox("Include subfolders")
        self.recursive_checkbox.setChecked(True)
        recursive_layout.addWidget(self.recursive_checkbox)
        recursive_layout.addStretch()
        main_layout.addLayout(recursive_layout)
        
        # Progress information
        self.file_label = QLabel("Ready")
        main_layout.addWidget(self.file_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Convert button
        convert_btn = QPushButton("Convert Files")
        convert_btn.clicked.connect(self.start_conversion)
        main_layout.addWidget(convert_btn)
        
        # Status area
        self.status_label = QLabel("Select a folder containing CSV files to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Store the selected folder path
        self.folder_path = None
        
        # Worker thread for conversion
        self.worker = None
        
    def select_folder(self):
        """Open dialog to select folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with CSV Files")
        if folder:
            self.folder_path = folder
            self.folder_label.setText(folder)
            self.status_label.setText(f"Ready to convert CSV files in {os.path.basename(folder)}")
            self.progress_bar.setValue(0)
    
    def start_conversion(self):
        """Start the conversion process"""
        if not self.folder_path:
            QMessageBox.warning(self, "No Folder Selected", 
                               "Please select a folder containing CSV files first.")
            return
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting conversion...")
        
        # Create and start worker thread
        recursive = self.recursive_checkbox.isChecked()
        self.worker = ConverterWorker(self.folder_path, recursive)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.file_progress.connect(self.update_file_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(self.show_error)
        self.worker.status_update.connect(self.update_status)
        
        # Start conversion
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_file_progress(self, file_info):
        """Update the current file being processed"""
        self.file_label.setText(file_info)
    
    def update_status(self, status_message, total_files):
        """Update status information"""
        self.status_label.setText(status_message)
        
    def conversion_finished(self, converted_files):
        """Handle completion of conversion"""
        count = len(converted_files)
        
        if count == 0:
            self.status_label.setText("No CSV files found in the selected folder.")
        else:
            self.status_label.setText(f"Conversion complete. Converted {count} files.")
            
        self.progress_bar.setValue(100)
        
        # Simplify the success message - remove redundant information
        success_message = f"Successfully converted {count} files to XLE format."
        
        QMessageBox.information(
            self, 
            "Conversion Complete",
            success_message if count > 0 else "No files were converted."
        )
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Conversion Error", error_message)
        self.status_label.setText("Conversion failed. See error message.")


def process_command_line():
    """Process command line arguments for batch processing"""
    if len(sys.argv) > 1 and sys.argv[1] == '--batch':
        # Check if we have a folder specified
        if len(sys.argv) > 2:
            folder = sys.argv[2]
            recursive = True  # Default to recursive
            
            # Check for recursive flag
            if len(sys.argv) > 3 and sys.argv[3].lower() == 'false':
                recursive = False
                
            # Process the folder
            print(f"Batch processing folder: {folder} (recursive={recursive})")
            converter = CsvToXleConverter()
            try:
                converted = converter.scan_and_convert(folder, recursive)
                print(f"Successfully converted {len(converted)} files")
                return True
            except Exception as e:
                print(f"Error during batch conversion: {e}")
                return True
        else:
            print("Error: No folder specified for batch conversion")
            print("Usage: csv_to_xle_converter.py --batch <folder> [recursive]")
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
        window = CsvToXleConverterApp()
        window.show()
        sys.exit(app.exec_()) 