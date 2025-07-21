#!/usr/bin/env python3
"""
Find Files by Date Range Tool

This tool searches for XLE and CSV files that contain data within a specified date range.
It's designed to work with the CAESER Water Levels Monitoring System.

Author: CAESER-UOFM
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QRadioButton, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QMessageBox,
    QFileDialog, QButtonGroup, QGroupBox, QDateEdit, QGridLayout, QFrame,
    QSplitter, QTextEdit, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate, QDateTime
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import shutil

# Import SolinstReader from parent directory
sys.path.append(str(Path(__file__).parent.parent))
from src.gui.handlers.solinst_reader import SolinstReader

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DateRangeSearchThread(QThread):
    """Thread for searching files by date range"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    search_completed = pyqtSignal(list)
    
    def __init__(self, folder_path: str, start_date: datetime, end_date: datetime, 
                 file_types: List[str], include_subfolders: bool = True, search_mode: str = "date_range"):
        super().__init__()
        self.folder_path = Path(folder_path)
        self.start_date = start_date
        self.end_date = end_date
        self.file_types = file_types
        self.include_subfolders = include_subfolders
        self.search_mode = search_mode
        self.solinst_reader = SolinstReader()
        self.found_files = []
        
    def run(self):
        """Execute the date range search"""
        try:
            self.search_files()
            self.search_completed.emit(self.found_files)
        except Exception as e:
            logger.error(f"Search thread error: {e}")
            self.search_completed.emit([])
    
    def search_files(self):
        """Search for files containing data within the specified date range"""
        if self.search_mode == "single_date":
            search_date_str = self.start_date.strftime('%Y-%m-%d')
            self.status_updated.emit(f"Searching for files containing data for {search_date_str}...")
        else:
            start_str = self.start_date.strftime('%Y-%m-%d')
            end_str = self.end_date.strftime('%Y-%m-%d')
            self.status_updated.emit(f"Searching for files with data between {start_str} and {end_str}...")
        
        # Get list of files to search
        files_to_search = []
        
        if self.include_subfolders:
            for file_type in self.file_types:
                pattern = f"**/*{file_type}"
                files_to_search.extend(self.folder_path.glob(pattern))
        else:
            for file_type in self.file_types:
                pattern = f"*{file_type}"
                files_to_search.extend(self.folder_path.glob(pattern))
        
        total_files = len(files_to_search)
        if total_files == 0:
            self.status_updated.emit("No files found to search")
            return
        
        self.status_updated.emit(f"Found {total_files} files to search")
        
        # Search through each file
        for i, file_path in enumerate(files_to_search):
            progress = int((i / total_files) * 100)
            self.progress_updated.emit(progress)
            self.status_updated.emit(f"Searching: {file_path.name}")
            
            try:
                if file_path.suffix.lower() == '.xle':
                    self.process_xle_file(file_path)
                elif file_path.suffix.lower() == '.csv':
                    self.process_csv_file(file_path)
                    
            except Exception as e:
                logger.debug(f"Error processing {file_path}: {e}")
                continue
        
        self.progress_updated.emit(100)
        self.status_updated.emit(f"Search completed. Found {len(self.found_files)} matching files")
    
    def process_xle_file(self, file_path: Path):
        """Process an XLE file to check if it contains data in the date range"""
        try:
            data, metadata = self.solinst_reader.read_xle(file_path)
            
            # Check if file has date information
            if not (hasattr(metadata, 'start_time') and hasattr(metadata, 'stop_time')):
                return
                
            if not (metadata.start_time and metadata.stop_time):
                return
            
            # Check if date range overlaps with search range
            if self.date_ranges_overlap(metadata.start_time, metadata.stop_time, 
                                       self.start_date, self.end_date):
                
                # Calculate relative path
                try:
                    relative_path = str(file_path.relative_to(self.folder_path))
                except ValueError:
                    relative_path = str(file_path)
                
                # Create file data record
                file_data = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'location': metadata.location or "",
                    'serial_number': metadata.serial_number or "",
                    'start_date': metadata.start_time.strftime('%Y-%m-%d') if metadata.start_time else "Not available",
                    'end_date': metadata.stop_time.strftime('%Y-%m-%d') if metadata.stop_time else "Not available",
                    'start_time': metadata.start_time.strftime('%Y-%m-%d %H:%M:%S') if metadata.start_time else "Not available",
                    'end_time': metadata.stop_time.strftime('%Y-%m-%d %H:%M:%S') if metadata.stop_time else "Not available",
                    'reading_count': metadata.num_log if hasattr(metadata, 'num_log') else len(data),
                    'relative_path': relative_path,
                    'model': metadata.instrument_type or "",
                    'file_type': 'XLE',
                    'overlap_type': self.get_overlap_type(metadata.start_time, metadata.stop_time, 
                                                        self.start_date, self.end_date)
                }
                
                self.found_files.append(file_data)
                
        except Exception as e:
            logger.debug(f"Error processing XLE file {file_path}: {e}")
    
    def process_csv_file(self, file_path: Path):
        """Process a CSV file to check if it contains data in the date range"""
        try:
            data, metadata_dict = self.read_csv_file(file_path)
            
            # Check if file has date information
            start_time = metadata_dict.get('start_time')
            stop_time = metadata_dict.get('stop_time')
            
            if not (start_time and stop_time):
                return
            
            # Check if date range overlaps with search range
            if self.date_ranges_overlap(start_time, stop_time, self.start_date, self.end_date):
                
                # Calculate relative path
                try:
                    relative_path = str(file_path.relative_to(self.folder_path))
                except ValueError:
                    relative_path = str(file_path)
                
                # Create file data record
                file_data = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'location': metadata_dict.get('location', ''),
                    'serial_number': metadata_dict.get('serial_number', ''),
                    'start_date': start_time.strftime('%Y-%m-%d') if start_time else "Not available",
                    'end_date': stop_time.strftime('%Y-%m-%d') if stop_time else "Not available",
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else "Not available",
                    'end_time': stop_time.strftime('%Y-%m-%d %H:%M:%S') if stop_time else "Not available",
                    'reading_count': metadata_dict.get('num_log', 0),
                    'relative_path': relative_path,
                    'model': metadata_dict.get('instrument_type', ''),
                    'file_type': 'CSV',
                    'overlap_type': self.get_overlap_type(start_time, stop_time, 
                                                        self.start_date, self.end_date)
                }
                
                self.found_files.append(file_data)
                
        except Exception as e:
            logger.debug(f"Error processing CSV file {file_path}: {e}")
    
    def date_ranges_overlap(self, file_start: datetime, file_end: datetime, 
                           search_start: datetime, search_end: datetime) -> bool:
        """Check if two date ranges overlap"""
        return not (file_end < search_start or file_start > search_end)
    
    def get_overlap_type(self, file_start: datetime, file_end: datetime, 
                        search_start: datetime, search_end: datetime) -> str:
        """Determine the type of overlap between file and search date ranges"""
        if self.search_mode == "single_date":
            # For single date searches, just indicate that the file contains the date
            return "Contains Date"
        
        # For date range searches
        if file_start >= search_start and file_end <= search_end:
            return "Complete"
        elif file_start < search_start and file_end > search_end:
            return "Contains"
        elif file_start < search_start:
            return "Starts Before"
        elif file_end > search_end:
            return "Ends After"
        else:
            return "Partial"
    
    def read_csv_file(self, file_path: Path) -> Tuple[Optional[pd.DataFrame], dict]:
        """Read a CSV file and extract metadata including date information"""
        metadata = {
            'serial_number': '',
            'location': '',
            'project_id': '',
            'level_unit': '',
            'temperature_unit': '',
            'offset': '',
            'start_time': None,
            'stop_time': None,
            'instrument_type': 'Levelogger',
            'num_log': 0
        }
        
        # Try different encodings
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        
        for encoding in encodings:
            try:
                # Read header lines to extract metadata
                header_lines = []
                with open(file_path, 'r', encoding=encoding) as f:
                    for i in range(20):  # Read more lines for date info
                        try:
                            line = f.readline().strip()
                            header_lines.append(line)
                            if not line:
                                continue
                            
                            # Extract serial number
                            if any(x in line.upper() for x in ['SERIAL', 'SERIAL_NUMBER', 'SERIAL NUMBER']):
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        serial_candidate = parts[1].strip()
                                        if serial_candidate and any(c.isdigit() for c in serial_candidate):
                                            metadata['serial_number'] = serial_candidate
                            
                            # Extract location
                            elif 'LOCATION' in line.upper():
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['location'] = parts[1].strip()
                            
                            # Extract project ID
                            elif any(x in line.upper() for x in ['PROJECT ID', 'PROJECT_ID', 'PROJECTID']):
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['project_id'] = parts[1].strip()
                        
                        except Exception:
                            continue
                
                # Try to read the data to get start and end times
                try:
                    # Skip header lines and read data
                    data_start_line = 0
                    for i, line in enumerate(header_lines):
                        if any(x in line.upper() for x in ['DATE', 'TIME']) and ',' in line:
                            data_start_line = i
                            break
                    
                    if data_start_line > 0:
                        # Read the CSV data
                        df = pd.read_csv(file_path, skiprows=data_start_line, encoding=encoding)
                        
                        if len(df) > 0:
                            # Try to find date/time columns
                            date_col = None
                            time_col = None
                            datetime_col = None
                            
                            for col in df.columns:
                                col_upper = col.upper()
                                if 'DATE' in col_upper and 'TIME' in col_upper:
                                    datetime_col = col
                                    break
                                elif 'DATE' in col_upper:
                                    date_col = col
                                elif 'TIME' in col_upper:
                                    time_col = col
                            
                            # Extract start and end times
                            if datetime_col:
                                try:
                                    df[datetime_col] = pd.to_datetime(df[datetime_col])
                                    metadata['start_time'] = df[datetime_col].min()
                                    metadata['stop_time'] = df[datetime_col].max()
                                except Exception:
                                    pass
                            elif date_col and time_col:
                                try:
                                    df['datetime'] = pd.to_datetime(df[date_col] + ' ' + df[time_col])
                                    metadata['start_time'] = df['datetime'].min()
                                    metadata['stop_time'] = df['datetime'].max()
                                except Exception:
                                    pass
                            elif date_col:
                                try:
                                    df[date_col] = pd.to_datetime(df[date_col])
                                    metadata['start_time'] = df[date_col].min()
                                    metadata['stop_time'] = df[date_col].max()
                                except Exception:
                                    pass
                            
                            metadata['num_log'] = len(df)
                            
                        return df, metadata
                
                except Exception as e:
                    logger.debug(f"Error reading CSV data: {e}")
                    return None, metadata
                    
            except Exception as e:
                logger.debug(f"Error with encoding {encoding}: {e}")
                continue
        
        return None, metadata


class FindFilesByDateRange(QMainWindow):
    """Main window for the Find Files by Date Range tool"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Find Files by Date Range")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize data
        self.found_files = []
        self.search_thread = None
        
        # Setup UI
        self.setup_ui()
        
        # Set default dates (last 30 days)
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-30)
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
        self.single_date_edit.setDate(end_date)
        
        # Apply styling
        self.apply_styling()
    
    def setup_ui(self):
        """Set up the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Find Files by Date Range")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Search parameters
        search_group = QGroupBox("Search Parameters")
        search_layout = QGridLayout(search_group)
        
        # Folder selection
        search_layout.addWidget(QLabel("Folder:"), 0, 0)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select folder containing XLE/CSV files")
        search_layout.addWidget(self.folder_edit, 0, 1)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        search_layout.addWidget(self.browse_button, 0, 2)
        
        # Subfolder inclusion
        self.include_subfolders_check = QCheckBox("Include subfolders")
        self.include_subfolders_check.setChecked(True)
        search_layout.addWidget(self.include_subfolders_check, 1, 0, 1, 3)
        
        # Search mode selection
        search_mode_group = QGroupBox("Search Mode")
        search_mode_layout = QHBoxLayout(search_mode_group)
        
        self.date_range_radio = QRadioButton("Date Range")
        self.single_date_radio = QRadioButton("Single Date")
        self.date_range_radio.setChecked(True)
        
        search_mode_layout.addWidget(self.date_range_radio)
        search_mode_layout.addWidget(self.single_date_radio)
        
        # Connect radio buttons to update UI
        self.date_range_radio.toggled.connect(self.update_date_controls)
        self.single_date_radio.toggled.connect(self.update_date_controls)
        
        search_layout.addWidget(search_mode_group, 2, 0, 1, 3)
        
        # Date selection controls
        search_layout.addWidget(QLabel("Start Date:"), 3, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        search_layout.addWidget(self.start_date_edit, 3, 1)
        
        self.end_date_label = QLabel("End Date:")
        search_layout.addWidget(self.end_date_label, 4, 0)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        search_layout.addWidget(self.end_date_edit, 4, 1)
        
        # Single date control (initially hidden)
        self.single_date_label = QLabel("Search Date:")
        self.single_date_edit = QDateEdit()
        self.single_date_edit.setCalendarPopup(True)
        search_layout.addWidget(self.single_date_label, 3, 0)
        search_layout.addWidget(self.single_date_edit, 3, 1)
        
        # Initially hide single date controls
        self.single_date_label.hide()
        self.single_date_edit.hide()
        
        # File type selection
        file_type_group = QGroupBox("File Types")
        file_type_layout = QHBoxLayout(file_type_group)
        
        self.xle_radio = QRadioButton("XLE only")
        self.csv_radio = QRadioButton("CSV only")
        self.both_radio = QRadioButton("Both XLE and CSV")
        self.both_radio.setChecked(True)
        
        file_type_layout.addWidget(self.xle_radio)
        file_type_layout.addWidget(self.csv_radio)
        file_type_layout.addWidget(self.both_radio)
        
        search_layout.addWidget(file_type_group, 5, 0, 1, 3)
        
        # Search button
        self.search_button = QPushButton("Search Files")
        self.search_button.clicked.connect(self.start_search)
        search_layout.addWidget(self.search_button, 6, 0, 1, 3)
        
        layout.addWidget(search_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to search")
        layout.addWidget(self.status_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.setup_results_table()
        layout.addWidget(self.results_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.open_file_button = QPushButton("Open Selected File")
        self.open_file_button.clicked.connect(self.open_selected_file)
        self.open_file_button.setEnabled(False)
        button_layout.addWidget(self.open_file_button)
        
        self.open_folder_button = QPushButton("Open File Location")
        self.open_folder_button.clicked.connect(self.open_file_location)
        self.open_folder_button.setEnabled(False)
        button_layout.addWidget(self.open_folder_button)
        
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Connect table selection
        self.results_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
    
    def setup_results_table(self):
        """Set up the results table"""
        headers = [
            "File Name", "File Type", "Location", "Serial Number", 
            "Start Date", "End Date", "Overlap Type", "Reading Count", "Relative Path"
        ]
        
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(headers) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Set selection behavior
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
    
    def apply_styling(self):
        """Apply styling to the interface"""
        # Set a modern color scheme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit, QDateEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QTableWidget {
                gridline-color: #cccccc;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
    
    def update_date_controls(self):
        """Update date control visibility based on search mode"""
        if self.date_range_radio.isChecked():
            # Show date range controls
            self.start_date_edit.show()
            self.end_date_edit.show()
            self.end_date_label.show()
            # Hide single date controls
            self.single_date_label.hide()
            self.single_date_edit.hide()
        else:
            # Hide date range controls
            self.start_date_edit.hide()
            self.end_date_edit.hide()
            self.end_date_label.hide()
            # Show single date controls
            self.single_date_label.show()
            self.single_date_edit.show()
    
    def browse_folder(self):
        """Browse for folder containing files"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", "", QFileDialog.ShowDirsOnly
        )
        if folder_path:
            self.folder_edit.setText(folder_path)
    
    def start_search(self):
        """Start the search process"""
        # Validate inputs
        folder_path = self.folder_edit.text().strip()
        if not folder_path:
            QMessageBox.warning(self, "Error", "Please select a folder to search.")
            return
        
        if not Path(folder_path).exists():
            QMessageBox.warning(self, "Error", "Selected folder does not exist.")
            return
        
        # Get date range based on search mode
        if self.single_date_radio.isChecked():
            # Single date mode - search for files containing this specific date
            search_date = self.single_date_edit.date().toPyDate()
            start_datetime = datetime.combine(search_date, datetime.min.time())
            end_datetime = datetime.combine(search_date, datetime.max.time())
            search_mode = "single_date"
        else:
            # Date range mode
            start_date = self.start_date_edit.date().toPyDate()
            end_date = self.end_date_edit.date().toPyDate()
            
            # Convert to datetime objects
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            if start_datetime > end_datetime:
                QMessageBox.warning(self, "Error", "Start date must be before end date.")
                return
            
            search_mode = "date_range"
        
        # Determine file types to search
        file_types = []
        if self.xle_radio.isChecked():
            file_types = ['.xle']
        elif self.csv_radio.isChecked():
            file_types = ['.csv']
        else:  # both_radio
            file_types = ['.xle', '.csv']
        
        # Clear previous results
        self.found_files.clear()
        self.results_table.setRowCount(0)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Disable search button
        self.search_button.setEnabled(False)
        
        # Start search thread
        self.search_thread = DateRangeSearchThread(
            folder_path, start_datetime, end_datetime, file_types, 
            self.include_subfolders_check.isChecked(), search_mode
        )
        self.search_thread.progress_updated.connect(self.progress_bar.setValue)
        self.search_thread.status_updated.connect(self.status_label.setText)
        self.search_thread.search_completed.connect(self.search_completed)
        self.search_thread.start()
    
    def search_completed(self, found_files: List[Dict[str, Any]]):
        """Handle search completion"""
        self.found_files = found_files
        self.populate_results_table()
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Re-enable search button
        self.search_button.setEnabled(True)
        
        # Update status
        self.status_label.setText(f"Found {len(found_files)} files matching criteria")
        
        # Enable export button if results found
        self.export_button.setEnabled(len(found_files) > 0)
    
    def populate_results_table(self):
        """Populate the results table with found files"""
        self.results_table.setRowCount(len(self.found_files))
        
        for row, file_data in enumerate(self.found_files):
            self.results_table.setItem(row, 0, QTableWidgetItem(file_data['file_name']))
            self.results_table.setItem(row, 1, QTableWidgetItem(file_data['file_type']))
            self.results_table.setItem(row, 2, QTableWidgetItem(file_data['location']))
            self.results_table.setItem(row, 3, QTableWidgetItem(file_data['serial_number']))
            self.results_table.setItem(row, 4, QTableWidgetItem(file_data['start_date']))
            self.results_table.setItem(row, 5, QTableWidgetItem(file_data['end_date']))
            self.results_table.setItem(row, 6, QTableWidgetItem(file_data['overlap_type']))
            self.results_table.setItem(row, 7, QTableWidgetItem(str(file_data['reading_count'])))
            self.results_table.setItem(row, 8, QTableWidgetItem(file_data['relative_path']))
    
    def on_selection_changed(self):
        """Handle table selection changes"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        self.open_file_button.setEnabled(has_selection)
        self.open_folder_button.setEnabled(has_selection)
    
    def open_selected_file(self):
        """Open the selected file"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        file_path = self.found_files[row]['file_path']
        
        try:
            os.startfile(file_path)  # Windows
        except AttributeError:
            try:
                os.system(f'open "{file_path}"')  # macOS
            except:
                os.system(f'xdg-open "{file_path}"')  # Linux
    
    def open_file_location(self):
        """Open the location of the selected file"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        file_path = Path(self.found_files[row]['file_path'])
        folder_path = file_path.parent
        
        try:
            os.startfile(folder_path)  # Windows
        except AttributeError:
            try:
                os.system(f'open "{folder_path}"')  # macOS
            except:
                os.system(f'xdg-open "{folder_path}"')  # Linux
    
    def export_results(self):
        """Export search results to CSV"""
        if not self.found_files:
            QMessageBox.warning(self, "Warning", "No results to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "date_range_search_results.csv", 
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # Create DataFrame from results
            df = pd.DataFrame(self.found_files)
            
            # Select columns to export
            columns_to_export = [
                'file_name', 'file_type', 'location', 'serial_number',
                'start_date', 'end_date', 'start_time', 'end_time',
                'overlap_type', 'reading_count', 'relative_path', 'model'
            ]
            
            # Filter to only include available columns
            available_columns = [col for col in columns_to_export if col in df.columns]
            export_df = df[available_columns]
            
            # Export to CSV
            export_df.to_csv(file_path, index=False)
            
            QMessageBox.information(self, "Success", f"Results exported to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export results: {str(e)}")


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Find Files by Date Range")
    app.setOrganizationName("CAESER-UOFM")
    
    window = FindFilesByDateRange()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()