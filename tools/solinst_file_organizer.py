import os
import sys
import csv
import logging
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any, Set
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QCheckBox, QProgressBar, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Set up logging
logger = logging.getLogger(__name__)

class FileOrganizer:
    """Organizes XLE files based on mapper CSV output"""
    
    def __init__(self):
        """Initialize organizer"""
        pass
        
    def organize_files(self, 
                     map_file_path: str, 
                     duplicates_file_path: str, 
                     output_dir: str) -> Dict[str, int]:
        """
        Organize files based on CSV data
        
        Args:
            map_file_path: Path to the main CSV map file
            duplicates_file_path: Path to the duplicates CSV file (optional)
            output_dir: Path where organized files will be created
            
        Returns:
            Statistics about organized files
        """
        # Create output directory structure
        output_path = Path(output_dir)
        barologger_dir = output_path / "Barologgers"
        levelogger_dir = output_path / "Leveloggers"
        
        barologger_dir.mkdir(parents=True, exist_ok=True)
        levelogger_dir.mkdir(parents=True, exist_ok=True)
        
        # Track duplicates - for files in the duplicates.csv with is_duplicate=False
        non_duplicate_files = set()
        if duplicates_file_path and os.path.exists(duplicates_file_path):
            with open(duplicates_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only consider original files (not duplicates)
                    if row.get('is_duplicate', '').lower() == 'false':
                        file_path = os.path.join(row['file_path'], row['file_name'])
                        non_duplicate_files.add(file_path)
        
        # Process main CSV file
        stats = {
            'barologgers': 0,
            'leveloggers': 0,
            'skipped_duplicates': 0,
            'missing_files': 0
        }
        
        with open(map_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Construct source file path
                file_path = os.path.join(row['file_path'], row['file_name'])
                
                # Skip duplicates if not in the non_duplicate_files set and we're using duplicate filtering
                if duplicates_file_path and os.path.exists(duplicates_file_path) and file_path not in non_duplicate_files:
                    if os.path.exists(file_path):  # Only count existing files
                        stats['skipped_duplicates'] += 1
                    continue
                
                # Check if the file exists
                if not os.path.exists(file_path):
                    stats['missing_files'] += 1
                    logger.warning(f"File not found: {file_path}")
                    continue
                
                # Determine destination based on logger type
                logger_type = row.get('Logger_type', '')
                serial_number = row.get('Serial_number', 'unknown')
                
                # Create serial number folder in appropriate location
                if logger_type.lower() == 'barologger':
                    dest_folder = barologger_dir / serial_number
                    stats['barologgers'] += 1
                else:  # Default to levelogger
                    dest_folder = levelogger_dir / serial_number
                    stats['leveloggers'] += 1
                
                # Create directory if it doesn't exist
                dest_folder.mkdir(exist_ok=True)
                
                # Copy file
                dest_file = dest_folder / row['file_name']
                try:
                    shutil.copy2(file_path, dest_file)
                    logger.info(f"Copied {file_path} to {dest_file}")
                except Exception as e:
                    logger.error(f"Error copying {file_path}: {e}")
        
        return stats


class OrganizerWorker(QThread):
    """Worker thread for file organization"""
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Stats dictionary
    error = pyqtSignal(str)
    
    def __init__(self, map_file, duplicates_file, output_dir):
        super().__init__()
        self.map_file = map_file
        self.duplicates_file = duplicates_file
        self.output_dir = output_dir
        self.organizer = FileOrganizer()
        
    def run(self):
        try:
            self.status_update.emit("Reading map file and counting files...")
            
            # Count total files for progress tracking
            total_files = 0
            with open(self.map_file, 'r', encoding='utf-8') as f:
                total_files = sum(1 for _ in csv.DictReader(f))
            
            if total_files == 0:
                self.error.emit("No files found in the map file")
                return
            
            self.status_update.emit(f"Found {total_files} entries in map file")
            
            # Create custom organizer with progress reporting
            processed_files = 0
            
            # Define a custom organize_files method with progress updates
            def organize_with_progress():
                nonlocal processed_files
                
                # Create output directory structure
                output_path = Path(self.output_dir)
                barologger_dir = output_path / "Barologgers"
                levelogger_dir = output_path / "Leveloggers"
                
                barologger_dir.mkdir(parents=True, exist_ok=True)
                levelogger_dir.mkdir(parents=True, exist_ok=True)
                
                # Track duplicates - for files in the duplicates.csv with is_duplicate=False
                non_duplicate_files = set()
                if self.duplicates_file and os.path.exists(self.duplicates_file):
                    self.status_update.emit("Reading duplicates file...")
                    with open(self.duplicates_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Only consider original files (not duplicates)
                            if row.get('is_duplicate', '').lower() == 'false':
                                file_path = os.path.join(row['file_path'], row['file_name'])
                                non_duplicate_files.add(file_path)
                                
                    self.status_update.emit(f"Found {len(non_duplicate_files)} original files in duplicates file")
                
                # Process main CSV file
                stats = {
                    'barologgers': 0,
                    'leveloggers': 0,
                    'skipped_duplicates': 0,
                    'missing_files': 0
                }
                
                self.status_update.emit("Starting file organization...")
                
                with open(self.map_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Construct source file path
                        file_path = os.path.join(row['file_path'], row['file_name'])
                        
                        # Update progress information
                        processed_files += 1
                        progress_percent = int((processed_files / total_files) * 100)
                        self.progress.emit(progress_percent)
                        self.status_update.emit(f"Processing: {row['file_name']}")
                        
                        # Skip duplicates if not in the non_duplicate_files set and we're using duplicate filtering
                        if self.duplicates_file and os.path.exists(self.duplicates_file) and len(non_duplicate_files) > 0 and file_path not in non_duplicate_files:
                            if os.path.exists(file_path):  # Only count existing files
                                stats['skipped_duplicates'] += 1
                            continue
                        
                        # Check if the file exists
                        if not os.path.exists(file_path):
                            stats['missing_files'] += 1
                            logger.warning(f"File not found: {file_path}")
                            continue
                        
                        # Determine destination based on logger type
                        logger_type = row.get('Logger_type', '')
                        serial_number = row.get('Serial_number', 'unknown')
                        
                        # Create serial number folder in appropriate location
                        if logger_type.lower() == 'barologger':
                            dest_folder = barologger_dir / serial_number
                            stats['barologgers'] += 1
                        else:  # Default to levelogger
                            dest_folder = levelogger_dir / serial_number
                            stats['leveloggers'] += 1
                        
                        # Create directory if it doesn't exist
                        dest_folder.mkdir(exist_ok=True)
                        
                        # Copy file
                        dest_file = dest_folder / row['file_name']
                        try:
                            shutil.copy2(file_path, dest_file)
                            logger.info(f"Copied {file_path} to {dest_file}")
                        except Exception as e:
                            logger.error(f"Error copying {file_path}: {e}")
                
                return stats
                
            # Run the organization with progress tracking
            stats = organize_with_progress()
            self.finished.emit(stats)
            
        except Exception as e:
            import traceback
            logger.error(f"Organization error: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Error organizing files: {str(e)}")


class FileOrganizerApp(QMainWindow):
    """GUI Application for organizing XLE files"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Solinst File Organizer")
        self.setMinimumSize(600, 300)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Map file selection
        map_layout = QHBoxLayout()
        self.map_file_label = QLabel("No map file selected")
        self.map_file_label.setWordWrap(True)
        select_map_btn = QPushButton("Select Map File")
        select_map_btn.clicked.connect(self.select_map_file)
        
        map_layout.addWidget(QLabel("Map File:"))
        map_layout.addWidget(self.map_file_label, 1)  # 1 = stretch factor
        map_layout.addWidget(select_map_btn)
        main_layout.addLayout(map_layout)
        
        # Duplicates file selection
        dup_layout = QHBoxLayout()
        self.dup_file_label = QLabel("No duplicates file selected (optional)")
        self.dup_file_label.setWordWrap(True)
        select_dup_btn = QPushButton("Select Duplicates")
        select_dup_btn.clicked.connect(self.select_duplicates_file)
        
        dup_layout.addWidget(QLabel("Duplicates:"))
        dup_layout.addWidget(self.dup_file_label, 1)  # 1 = stretch factor
        dup_layout.addWidget(select_dup_btn)
        main_layout.addLayout(dup_layout)
        
        # Output directory selection
        output_layout = QHBoxLayout()
        self.output_dir_label = QLabel("No output folder selected")
        self.output_dir_label.setWordWrap(True)
        select_output_btn = QPushButton("Select Output Folder")
        select_output_btn.clicked.connect(self.select_output_directory)
        
        output_layout.addWidget(QLabel("Output:"))
        output_layout.addWidget(self.output_dir_label, 1)  # 1 = stretch factor
        output_layout.addWidget(select_output_btn)
        main_layout.addLayout(output_layout)
        
        # Progress information
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Organize button
        organize_btn = QPushButton("Organize Files")
        organize_btn.clicked.connect(self.start_organization)
        main_layout.addWidget(organize_btn)
        
        # Result area
        self.result_label = QLabel("Select files to begin")
        self.result_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.result_label)
        
        # Store paths
        self.map_file = None
        self.duplicates_file = None
        self.output_dir = None
        
        # Worker thread
        self.worker = None
        
    def select_map_file(self):
        """Open dialog to select map file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Map CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.map_file = file_path
            self.map_file_label.setText(file_path)
            self.update_status()
    
    def select_duplicates_file(self):
        """Open dialog to select duplicates file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Duplicates CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.duplicates_file = file_path
            self.dup_file_label.setText(file_path)
            self.update_status()
    
    def select_output_directory(self):
        """Open dialog to select output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir = folder
            self.output_dir_label.setText(folder)
            self.update_status()
    
    def update_status(self):
        """Update the status message based on selected files"""
        if self.map_file and self.output_dir:
            self.result_label.setText("Ready to organize files")
        else:
            missing = []
            if not self.map_file:
                missing.append("map file")
            if not self.output_dir:
                missing.append("output folder")
            self.result_label.setText(f"Please select {' and '.join(missing)} to continue")
    
    def start_organization(self):
        """Start organizing files"""
        if not self.map_file:
            QMessageBox.warning(self, "No Map File Selected", 
                               "Please select a map CSV file first.")
            return
            
        if not self.output_dir:
            QMessageBox.warning(self, "No Output Folder Selected", 
                               "Please select an output folder first.")
            return
            
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting organization...")
        self.result_label.setText("Organizing files...")
        
        # Create and start worker thread
        self.worker = OrganizerWorker(self.map_file, self.duplicates_file, self.output_dir)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status_label)
        self.worker.finished.connect(self.organization_finished)
        self.worker.error.connect(self.show_error)
        
        # Start organization
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_status_label(self, status_text):
        """Update the status label"""
        self.status_label.setText(status_text)
        
    def organization_finished(self, stats):
        """Handle completion of organization"""
        level_count = stats['leveloggers']
        baro_count = stats['barologgers']
        skipped = stats['skipped_duplicates']
        missing = stats['missing_files']
        total = level_count + baro_count
        
        status_text = f"Organization complete. Organized {total} files."
        self.result_label.setText(status_text)
        self.progress_bar.setValue(100)
        
        # Show a message box with the results
        message = f"Successfully organized {total} files:\n\n" + \
                  f"- {level_count} Levelogger files\n" + \
                  f"- {baro_count} Barologger files\n\n"
                  
        if skipped > 0:
            message += f"Skipped {skipped} duplicate files.\n\n"
            
        if missing > 0:
            message += f"Could not find {missing} files referenced in the map.\n\n"
            
        message += f"Files have been organized in:\n{self.output_dir}"
        
        QMessageBox.information(
            self, 
            "Organization Complete",
            message
        )
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Organization Error", error_message)
        self.result_label.setText("Organization failed. See error message.")


def process_command_line():
    """Process command line arguments if script is run directly"""
    parser = argparse.ArgumentParser(description='Organize Solinst XLE files based on mapper output.')
    parser.add_argument('map_file', help='Path to the CSV map file')
    parser.add_argument('output_dir', help='Output directory for organized files')
    parser.add_argument('--duplicates', '-d', help='Path to duplicates CSV file (optional)')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        organizer = FileOrganizer()
        
        try:
            print(f"Organizing files based on {args.map_file}...")
            stats = organizer.organize_files(args.map_file, args.duplicates, args.output_dir)
            
            total = stats['leveloggers'] + stats['barologgers']
            print(f"Successfully organized {total} files:")
            print(f"- {stats['leveloggers']} Levelogger files")
            print(f"- {stats['barologgers']} Barologger files")
            
            if stats['skipped_duplicates'] > 0:
                print(f"Skipped {stats['skipped_duplicates']} duplicate files")
                
            if stats['missing_files'] > 0:
                print(f"Could not find {stats['missing_files']} files referenced in the map")
                
            print(f"Files organized in: {args.output_dir}")
            
        except Exception as e:
            print(f"Error: {e}")
            return False
            
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
        window = FileOrganizerApp()
        window.show()
        sys.exit(app.exec_())
