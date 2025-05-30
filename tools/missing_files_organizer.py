import os
import sys
import csv
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import argparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QProgressBar, QMessageBox, QLineEdit, QTextEdit,
                           QRadioButton, QButtonGroup, QGroupBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import the SolinstReader and XleMapper from their locations
sys.path.append(str(Path(__file__).parent.parent / "src" / "gui" / "handlers"))
from solinst_reader import SolinstReader
from solinst_xle_mapper import XleMapper
from style_handler import StyleHandler

# Set up logging
logger = logging.getLogger(__name__)

class FileComparisonWorker(QThread):
    """Worker thread for comparing files and finding missing ones"""
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(list, list, list)  # new_files, duplicate_files, orphaned_files
    error = pyqtSignal(str)
    
    def __init__(self, input_csv: Path, existing_csv: Path, transducer_locations: List[Dict[str, Any]]):
        super().__init__()
        self.input_csv = input_csv
        self.existing_csv = existing_csv
        self.transducer_locations = transducer_locations
        
    def run(self):
        try:
            # Read both CSV maps
            self.status_update.emit("Reading input CSV map...")
            input_map = self._read_csv(str(self.input_csv))
            
            self.status_update.emit("Reading existing CSV map...")
            existing_map = self._read_csv(str(self.existing_csv))
            
            # Compare maps to find missing files
            self.status_update.emit("Comparing maps to find missing files...")
            new_files, duplicate_files, orphaned_files = self._compare_maps(input_map, existing_map)
            
            self.finished.emit(new_files, duplicate_files, orphaned_files)
            
        except Exception as e:
            logger.error(f"Error in file comparison: {e}")
            self.error.emit(str(e))
    
    def _read_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Read data from a CSV file"""
        data = []
        logger.info(f"\nReading CSV file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            # Debug: Print the fieldnames
            logger.info(f"CSV fieldnames: {reader.fieldnames}")
            
            # Read first few rows to check structure
            for i, row in enumerate(reader):
                if i < 3:  # Print first 3 rows
                    logger.info(f"Row {i}: {row}")
                data.append(row)
                
            logger.info(f"Total rows read: {len(data)}")
            if data:
                logger.info(f"Keys in first row: {list(data[0].keys())}")
                logger.info(f"Values in first row: {list(data[0].values())}")
        return data
    
    def _compare_maps(self, input_map: List[Dict[str, Any]], existing_map: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Compare input and existing maps to find missing files"""
        new_files = []
        duplicate_files = []
        orphaned_files = []
        
        # Create lookup dictionary for existing files
        existing_lookup = {}
        for file in existing_map:
            key = (file['Serial_number'], file['Start_time'], file['Stop_time'])
            existing_lookup[key] = file
        
        # Process each input file
        for file in input_map:
            key = (file['Serial_number'], file['Start_time'], file['Stop_time'])
            
            if key in existing_lookup:
                duplicate_files.append(file)
            else:
                # Check if it's a transducer file and find well number
                if file['Logger_type'] != 'Barologger':
                    well_number = self._find_well_for_time_range(
                        file['Serial_number'],
                        file['Start_time'],
                        file['Stop_time']
                    )
                    if well_number:
                        new_files.append(file)
                    else:
                        orphaned_files.append(file)
                else:
                    new_files.append(file)
        
        return new_files, duplicate_files, orphaned_files

    def _find_well_for_time_range(self, serial_number: str, start_time: str, stop_time: str) -> Optional[str]:
        """Find the well number for a transducer based on time range"""
        if not start_time or not stop_time or not serial_number:
            logger.warning("Missing required time range or serial number data")
            return None
            
        try:
            file_start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            file_end = datetime.strptime(stop_time, '%Y-%m-%d %H:%M:%S')
            
            logger.info(f"\nLooking for well for transducer {serial_number}")
            logger.info(f"File time range: {file_start} to {file_end}")
            
            # Find all locations for this serial number
            locations = []
            for loc in self.transducer_locations:
                try:
                    # Use lowercase keys from the CSV
                    loc_serial = loc.get('serial_number', '')
                    if loc_serial == serial_number:
                        locations.append(loc)
                except Exception as e:
                    logger.error(f"Error processing location: {e}")
                    continue
            
            logger.info(f"Found {len(locations)} locations for this transducer")
            
            for location in locations:
                try:
                    # Use lowercase keys from the CSV
                    start_date = location.get('start_date', '')
                    end_date = location.get('end_date', '')
                    
                    if not start_date:
                        logger.error("Missing start date in location")
                        continue
                                
                    loc_start = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    # Handle NULL end_date (transducer still in well)
                    loc_end = (datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S') 
                              if end_date else datetime.max)
                    
                    # Check if file time range overlaps with location period
                    if (file_start <= loc_end and file_end >= loc_start):
                        # Use lowercase key from the CSV
                        well_number = location.get('well_number', '')
                        logger.info(f"Found matching well: {well_number}")
                        return well_number
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing location dates: {e}")
                    continue
            
            logger.info("No matching well found")
            return None
        except Exception as e:
            logger.error(f"Error in _find_well_for_time_range: {e}")
            return None

class FileCopyWorker(QThread):
    """Worker thread for copying new files to their destination"""
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, new_files: List[Dict[str, Any]], 
                 source_folder: Path,
                 transducer_locations: List[Dict[str, Any]]):
        super().__init__()
        self.new_files = new_files
        self.source_folder = source_folder
        self.transducer_locations = transducer_locations
        
    def run(self):
        try:
            # Create missing_xle_files folder in the main directory
            main_dir = Path.cwd()
            missing_files_dir = main_dir / 'missing_xle_files'
            missing_files_dir.mkdir(exist_ok=True)
            
            total_files = len(self.new_files)
            skipped_files = []
            copied_files = []
            
            for i, file in enumerate(self.new_files):
                self.status_update.emit(f"Processing {file['file_name']}...")
                
                # Determine destination path
                if file['Logger_type'] == 'Barologger':
                    dest_path = missing_files_dir / 'barologger' / file['Serial_number']
                else:
                    # For transducers, find the well based on time range
                    well_number = self._find_well_for_time_range(
                        file['Serial_number'],
                        file['Start_time'],
                        file['Stop_time']
                    )
                    
                    if not well_number:
                        skipped_files.append((file, "No matching well found for time range"))
                        continue
                    
                    dest_path = missing_files_dir / 'transducer' / well_number
                
                # Create destination directory if it doesn't exist
                dest_path.mkdir(parents=True, exist_ok=True)
                
                # Copy the file
                source_file = self.source_folder / file['file_path'] / file['file_name']
                if source_file.exists():
                    dest_file = dest_path / file['file_name']
                    shutil.copy2(source_file, dest_file)
                    copied_files.append(file)
                else:
                    skipped_files.append((file, "Source file not found"))
                
                # Update progress
                progress = int((i + 1) / total_files * 100)
                self.progress.emit(progress)
            
            # Log results
            logger.info(f"Copy operation complete:")
            logger.info(f"- Copied: {len(copied_files)} files")
            logger.info(f"- Skipped: {len(skipped_files)} files")
            if skipped_files:
                logger.info("Skipped files:")
                for file, reason in skipped_files:
                    logger.info(f"  {file['file_name']}: {reason}")
            
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"Error copying files: {e}")
            self.error.emit(str(e))
    
    def _find_well_for_time_range(self, serial_number: str, start_time: str, stop_time: str) -> Optional[str]:
        """Find the well number for a transducer based on time range"""
        if not start_time or not stop_time or not serial_number:
            logger.warning("Missing required time range or serial number data")
            return None
            
        try:
            file_start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            file_end = datetime.strptime(stop_time, '%Y-%m-%d %H:%M:%S')
            
            logger.info(f"\nLooking for well for transducer {serial_number}")
            logger.info(f"File time range: {file_start} to {file_end}")
            
            # Find all locations for this serial number
            locations = []
            for loc in self.transducer_locations:
                try:
                    # Use lowercase keys from the CSV
                    loc_serial = loc.get('serial_number', '')
                    if loc_serial == serial_number:
                        locations.append(loc)
                except Exception as e:
                    logger.error(f"Error processing location: {e}")
                    continue
            
            logger.info(f"Found {len(locations)} locations for this transducer")
            
            for location in locations:
                try:
                    # Use lowercase keys from the CSV
                    start_date = location.get('start_date', '')
                    end_date = location.get('end_date', '')
                    
                    if not start_date:
                        logger.error("Missing start date in location")
                        continue
                                
                    loc_start = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    # Handle NULL end_date (transducer still in well)
                    loc_end = (datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S') 
                              if end_date else datetime.max)
                    
                    # Check if file time range overlaps with location period
                    if (file_start <= loc_end and file_end >= loc_start):
                        # Use lowercase key from the CSV
                        well_number = location.get('well_number', '')
                        logger.info(f"Found matching well: {well_number}")
                        return well_number
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing location dates: {e}")
                    continue
            
            logger.info("No matching well found")
            return None
        except Exception as e:
            logger.error(f"Error in _find_well_for_time_range: {e}")
            return None

class MissingFilesOrganizerApp(QMainWindow):
    """GUI Application for organizing missing XLE files"""
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Missing Files Organizer")
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(25)  # Increased spacing between groups
        main_layout.setContentsMargins(25, 25, 25, 25)  # Increased main margins
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Input CSV Group
        input_group = QGroupBox("Input CSV Map")
        input_layout = QVBoxLayout()
        input_layout.setSpacing(15)
        input_layout.setContentsMargins(20, 30, 20, 20)  # Increased top margin for title
        input_group.setLayout(input_layout)
        
        # Input CSV selection
        input_csv_layout = QHBoxLayout()
        input_csv_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins from inner layout
        self.input_csv_path = QLineEdit()
        self.input_csv_path.setPlaceholderText("Select input XLE Map CSV file...")
        input_csv_select_btn = QPushButton("Browse")
        input_csv_select_btn.setStyleSheet(StyleHandler.get_secondary_button_style())
        input_csv_select_btn.clicked.connect(lambda: self.select_file(self.input_csv_path, "CSV Files (*.csv)"))
        
        input_csv_layout.addWidget(self.input_csv_path, 1)
        input_csv_layout.addWidget(input_csv_select_btn)
        input_layout.addLayout(input_csv_layout)
        
        main_layout.addWidget(input_group)
        
        # Required Files Group
        files_group = QGroupBox("Required Files")
        files_layout = QVBoxLayout()
        files_layout.setSpacing(15)
        files_layout.setContentsMargins(20, 30, 20, 20)  # Increased top margin for title
        files_group.setLayout(files_layout)
        
        # Existing CSV map
        existing_csv_layout = QHBoxLayout()
        existing_csv_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins from inner layout
        existing_csv_label = QLabel("Existing CSV Map:")
        self.existing_csv_path = QLineEdit()
        self.existing_csv_path.setPlaceholderText("Select existing XLE Map CSV file...")
        existing_csv_select_btn = QPushButton("Browse")
        existing_csv_select_btn.setStyleSheet(StyleHandler.get_secondary_button_style())
        existing_csv_select_btn.clicked.connect(lambda: self.select_file(self.existing_csv_path, "CSV Files (*.csv)"))
        
        existing_csv_layout.addWidget(existing_csv_label)
        existing_csv_layout.addWidget(self.existing_csv_path, 1)
        existing_csv_layout.addWidget(existing_csv_select_btn)
        files_layout.addLayout(existing_csv_layout)
        
        # Transducer locations CSV
        locations_layout = QHBoxLayout()
        locations_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins from inner layout
        locations_label = QLabel("Transducer Locations CSV:")
        self.locations_path = QLineEdit()
        self.locations_path.setPlaceholderText("Select transducer locations CSV file...")
        locations_select_btn = QPushButton("Browse")
        locations_select_btn.setStyleSheet(StyleHandler.get_secondary_button_style())
        locations_select_btn.clicked.connect(lambda: self.select_file(self.locations_path, "CSV Files (*.csv)"))
        
        locations_layout.addWidget(locations_label)
        locations_layout.addWidget(self.locations_path, 1)
        locations_layout.addWidget(locations_select_btn)
        files_layout.addLayout(locations_layout)
        
        main_layout.addWidget(files_group)
        
        # Progress Group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(15)
        progress_layout.setContentsMargins(20, 30, 20, 20)  # Increased top margin for title
        progress_group.setLayout(progress_layout)
        
        # Progress information
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_group)
        
        # Results Group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(20, 30, 20, 20)  # Increased top margin for title
        results_group.setLayout(results_layout)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(200)
        results_layout.addWidget(self.results_text)
        
        main_layout.addWidget(results_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 15, 0, 0)  # Increased top margin for buttons
        button_layout.addStretch()
        
        self.compare_btn = QPushButton("Compare Files")
        self.compare_btn.setStyleSheet(StyleHandler.get_action_button_style())
        self.compare_btn.clicked.connect(self.start_comparison)
        button_layout.addWidget(self.compare_btn)
        
        self.copy_btn = QPushButton("Copy New Files")
        self.copy_btn.setStyleSheet(StyleHandler.get_action_button_style())
        self.copy_btn.clicked.connect(self.start_copying)
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        main_layout.addLayout(button_layout)
        
        # Store data
        self.new_files = None
        self.duplicate_files = None
        self.orphaned_files = None
        self.transducer_locations = None
        
        # Worker threads
        self.comparison_worker = None
        self.copy_worker = None
    
    def select_file(self, line_edit: QLineEdit, file_filter: str):
        """Open dialog to select a file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            line_edit.setText(file_path)
    
    def start_comparison(self):
        """Start the file comparison process"""
        # Validate inputs
        if not self.input_csv_path.text():
            QMessageBox.warning(self, "Missing Input", "Please select an input XLE Map CSV file.")
            return
            
        if not self.existing_csv_path.text():
            QMessageBox.warning(self, "Missing Input", "Please select an existing XLE Map CSV file.")
            return
            
        if not self.locations_path.text():
            QMessageBox.warning(self, "Missing Input", "Please select a transducer locations CSV file.")
            return
        
        # Read transducer locations data
        self.transducer_locations = self._read_csv(self.locations_path.text())
        
        # Reset UI
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting file comparison...")
        self.results_text.clear()
        
        # Create and start worker thread
        self.comparison_worker = FileComparisonWorker(
            Path(self.input_csv_path.text()),
            Path(self.existing_csv_path.text()),
            self.transducer_locations
        )
        
        # Connect signals
        self.comparison_worker.progress.connect(self.update_progress)
        self.comparison_worker.status_update.connect(self.update_status)
        self.comparison_worker.finished.connect(self.comparison_finished)
        self.comparison_worker.error.connect(self.show_error)
        
        # Start comparison
        self.comparison_worker.start()
    
    def start_copying(self):
        """Start copying new files to their destination"""
        if not self.new_files:
            QMessageBox.warning(self, "No Files", "No new files to copy.")
            return
            
        # Get source folder from input CSV path
        source_folder = Path(self.input_csv_path.text()).parent
        
        # Reset UI
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting file copy...")
        
        # Create and start worker thread
        self.copy_worker = FileCopyWorker(
            self.new_files,
            source_folder,
            self.transducer_locations
        )
        
        # Connect signals
        self.copy_worker.progress.connect(self.update_progress)
        self.copy_worker.status_update.connect(self.update_status)
        self.copy_worker.finished.connect(self.copy_finished)
        self.copy_worker.error.connect(self.show_error)
        
        # Start copying
        self.copy_worker.start()
    
    def _read_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Read data from a CSV file"""
        data = []
        logger.info(f"\nReading CSV file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            # Debug: Print the fieldnames
            logger.info(f"CSV fieldnames: {reader.fieldnames}")
            
            # Read first few rows to check structure
            for i, row in enumerate(reader):
                if i < 3:  # Print first 3 rows
                    logger.info(f"Row {i}: {row}")
                data.append(row)
                
            logger.info(f"Total rows read: {len(data)}")
            if data:
                logger.info(f"Keys in first row: {list(data[0].keys())}")
                logger.info(f"Values in first row: {list(data[0].values())}")
        return data
    
    def update_progress(self, value: int):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message: str):
        """Update the status label"""
        self.status_label.setText(message)
    
    def comparison_finished(self, new_files: List[Dict[str, Any]], 
                          duplicate_files: List[Dict[str, Any]],
                          orphaned_files: List[Dict[str, Any]]):
        """Handle completion of file comparison"""
        self.new_files = new_files
        self.duplicate_files = duplicate_files
        self.orphaned_files = orphaned_files
        
        # Update results display
        results_text = f"Found {len(new_files)} new files, {len(duplicate_files)} duplicate files, "
        results_text += f"and {len(orphaned_files)} orphaned files.\n\n"
        
        if new_files:
            results_text += "New Files:\n"
            for file in new_files:
                results_text += f"- {file['file_name']} ({file['Logger_type']} {file['Serial_number']})\n"
        
        if duplicate_files:
            results_text += "\nDuplicate Files:\n"
            for file in duplicate_files:
                results_text += f"- {file['file_name']} ({file['Logger_type']} {file['Serial_number']})\n"
        
        if orphaned_files:
            results_text += "\nOrphaned Files (No matching well found):\n"
            for file in orphaned_files:
                results_text += f"- {file['file_name']} ({file['Logger_type']} {file['Serial_number']})\n"
                results_text += f"  Time range: {file['Start_time']} to {file['Stop_time']}\n"
        
        self.results_text.setText(results_text)
        
        # Enable copy button if there are new files
        self.copy_btn.setEnabled(len(new_files) > 0)
        
        self.status_label.setText("Comparison complete")
        self.progress_bar.setValue(100)
    
    def copy_finished(self):
        """Handle completion of file copying"""
        self.status_label.setText("File copying complete")
        self.progress_bar.setValue(100)
        
        QMessageBox.information(
            self,
            "Copy Complete",
            f"Successfully copied {len(self.new_files)} new files to the missing_xle_files folder."
        )
    
    def show_error(self, error_message: str):
        """Display error message"""
        QMessageBox.critical(self, "Error", error_message)
        self.status_label.setText("Error occurred. See error message.")

def process_command_line():
    """Process command line arguments if script is run directly"""
    parser = argparse.ArgumentParser(description='Organize missing XLE files.')
    parser.add_argument('--csv', help='XLE Map CSV file path')
    parser.add_argument('--folder', help='Folder containing XLE files')
    parser.add_argument('--locations', required=True, help='Transducer locations CSV file path')
    parser.add_argument('--db-folder', required=True, help='Existing database folder path')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        # Create and run the application
        app = QApplication(sys.argv)
        StyleHandler.apply_application_style(app)
        window = MissingFilesOrganizerApp()
        
        # Set initial values if provided
        if args.csv:
            window.input_csv_path.setText(args.csv)
        if args.folder:
            window.folder_path.setText(args.folder)
            window.folder_radio.setChecked(True)
        if args.locations:
            window.locations_path.setText(args.locations)
        if args.db_folder:
            window.existing_csv_path.setText(args.db_folder)
        
        window.show()
        sys.exit(app.exec_())
    
    return False

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Check if we should run command line mode
    if not process_command_line():
        # No command line arguments, start GUI
        app = QApplication(sys.argv)
        StyleHandler.apply_application_style(app)
        window = MissingFilesOrganizerApp()
        window.show()
        sys.exit(app.exec_())