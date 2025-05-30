import os
import sys
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import argparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QCheckBox, QProgressBar, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import the SolinstReader from its location
sys.path.append(str(Path(__file__).parent.parent / "src" / "gui" / "handlers"))
from solinst_reader import SolinstReader

# Set up logging
logger = logging.getLogger(__name__)

class XleMapper:
    """Maps XLE files in a directory structure and extracts metadata"""
    
    def __init__(self):
        """Initialize mapper"""
        self.reader = SolinstReader()
        
    def scan_directory(self, directory: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Scan directory for XLE files and extract metadata
        
        Args:
            directory: Directory to scan
            recursive: Whether to include subdirectories
            
        Returns:
            List of dictionaries with extracted metadata
        """
        directory_path = Path(directory)
        pattern = "**/*.xle" if recursive else "*.xle"
        
        results = []
        
        for xle_file in directory_path.glob(pattern):
            try:
                # Get file metadata using SolinstReader
                metadata, _ = self.reader.get_file_metadata(xle_file)
                
                # Calculate duration in days
                duration_days = (metadata.stop_time - metadata.start_time).total_seconds() / (60 * 60 * 24)
                
                # Determine if it's a barologger or levelogger
                logger_type = "Barologger" if self.reader.is_barologger(metadata) else "Levelogger"
                
                # Create entry with required fields
                entry = {
                    'Serial_number': metadata.serial_number,
                    'Project_ID': metadata.project_id,
                    'Location': metadata.location,
                    'Start_time': metadata.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Stop_time': metadata.stop_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Duration_days': f"{duration_days:.2f}", # Add duration column with 2 decimal places
                    'Logger_type': logger_type,  # Add logger type column
                    'file_name': xle_file.name,
                    'file_path': str(xle_file.parent)  # Store only the directory path, not the full file path
                }
                
                results.append(entry)
                logger.info(f"Processed {xle_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing {xle_file}: {e}")
        
        return results
    
    def export_to_csv(self, results: List[Dict[str, Any]], output_file: str) -> str:
        """
        Export extracted metadata to CSV file
        
        Args:
            results: List of metadata dictionaries
            output_file: Path to save CSV file
            
        Returns:
            Path to the saved CSV file
        """
        if not results:
            logger.warning("No results to export")
            return None
            
        # Define column order for the CSV - add Logger_type after Duration_days
        columns = ['Serial_number', 'Project_ID', 'Location', 
                  'Start_time', 'Stop_time', 'Duration_days', 'Logger_type', 
                  'file_name', 'file_path']
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for entry in results:
                writer.writerow(entry)
                
        logger.info(f"Exported metadata to {output_file}")
        return output_file

    def find_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find duplicate files based on serial number, start time, and stop time
        
        Args:
            results: List of metadata dictionaries
            
        Returns:
            List of dictionaries with duplicate file information
        """
        # Create lookup dictionary for fast duplicate finding
        # Use a tuple of (serial_number, start_time, stop_time) as the key
        file_index = {}
        duplicates = []
        
        for entry in results:
            # Create a key based on the unique identifying fields
            key = (entry['Serial_number'], entry['Start_time'], entry['Stop_time'])
            
            # If we've seen this combination before, it's a duplicate
            if key in file_index:
                # Get the original file
                original = file_index[key]
                
                # Add both files to duplicates list if this is the first duplicate
                if len([d for d in duplicates if d['key'] == key]) == 0:
                    duplicates.append({
                        'key': key,
                        'Serial_number': original['Serial_number'],
                        'Start_time': original['Start_time'], 
                        'Stop_time': original['Stop_time'],
                        'file_name': original['file_name'],
                        'file_path': original['file_path'],
                        'is_duplicate': False  # The original file
                    })
                
                # Add the current duplicate
                duplicates.append({
                    'key': key,
                    'Serial_number': entry['Serial_number'],
                    'Start_time': entry['Start_time'],
                    'Stop_time': entry['Stop_time'],
                    'file_name': entry['file_name'],
                    'file_path': entry['file_path'],
                    'is_duplicate': True  # Marked as duplicate
                })
            else:
                # First time seeing this combination
                file_index[key] = entry
        
        # Remove the temporary 'key' field used for grouping
        for entry in duplicates:
            entry.pop('key', None)
            
        return duplicates
    
    def export_duplicates_to_csv(self, duplicates: List[Dict[str, Any]], output_file: str) -> str:
        """
        Export duplicate files information to CSV
        
        Args:
            duplicates: List of duplicate file dictionaries
            output_file: Path to save CSV file
            
        Returns:
            Path to the saved CSV file
        """
        if not duplicates:
            logger.warning("No duplicates to export")
            return None
            
        # Define column order for the CSV
        columns = ['Serial_number', 'Start_time', 'Stop_time', 
                   'file_name', 'file_path', 'is_duplicate']
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for entry in duplicates:
                writer.writerow(entry)
                
        logger.info(f"Exported {len(duplicates)} duplicate entries to {output_file}")
        return output_file


class MapperWorker(QThread):
    """Worker thread for mapping XLE files"""
    progress = pyqtSignal(int)
    file_progress = pyqtSignal(str)
    finished = pyqtSignal(str, list, str, int)  # Output file path, results, duplicates path, duplicates count
    error = pyqtSignal(str)
    
    def __init__(self, folder_path, output_path, recursive=True):
        super().__init__()
        self.folder_path = folder_path
        self.output_path = output_path
        self.recursive = recursive
        self.mapper = XleMapper()
        
    def run(self):
        try:
            # First count total files to process for progress tracking
            total_files = sum(1 for _ in Path(self.folder_path).glob('**/*.xle' if self.recursive else '*.xle'))
            
            if total_files == 0:
                self.error.emit("No XLE files found in the selected folder")
                return
                
            self.file_progress.emit(f"Found {total_files} XLE files to process")
            
            # Keep track of processed files for manual progress updates
            processed = 0
            
            # Function to update progress during scan
            def progress_callback(file_name):
                nonlocal processed
                processed += 1
                self.file_progress.emit(f"Processing: {file_name}")
                progress_percent = int((processed / total_files) * 100)
                self.progress.emit(progress_percent)
            
            # Patch the scan_directory method to include progress updates
            original_scan = self.mapper.scan_directory
            
            def scan_with_progress(directory, recursive):
                directory_path = Path(directory)
                pattern = "**/*.xle" if recursive else "*.xle"
                
                results = []
                
                for xle_file in directory_path.glob(pattern):
                    try:
                        # Get file metadata
                        metadata, _ = self.mapper.reader.get_file_metadata(xle_file)
                        
                        # Calculate duration in days
                        duration_days = (metadata.stop_time - metadata.start_time).total_seconds() / (60 * 60 * 24)
                        
                        # Determine if it's a barologger or levelogger
                        logger_type = "Barologger" if self.mapper.reader.is_barologger(metadata) else "Levelogger"
                        
                        # Create entry with required fields
                        entry = {
                            'Serial_number': metadata.serial_number,
                            'Project_ID': metadata.project_id,
                            'Location': metadata.location,
                            'Start_time': metadata.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'Stop_time': metadata.stop_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'Duration_days': f"{duration_days:.2f}", # Add duration column with 2 decimal places
                            'Logger_type': logger_type,  # Add logger type column
                            'file_name': xle_file.name,
                            'file_path': str(xle_file.parent)  # Store only the directory path, not the full file path
                        }
                        
                        results.append(entry)
                        
                        # Update progress
                        progress_callback(xle_file.name)
                        
                    except Exception as e:
                        self.error.emit(f"Error processing {xle_file.name}: {str(e)}")
                
                return results
                
            # Replace method temporarily
            self.mapper.scan_directory = scan_with_progress
            
            # Scan directory and get metadata
            results = self.mapper.scan_directory(self.folder_path, self.recursive)
            
            # Restore original method
            self.mapper.scan_directory = original_scan
            
            # Export to CSV
            if results:
                try:
                    self.file_progress.emit("Exporting main results to CSV...")
                    output_file = self.mapper.export_to_csv(results, self.output_path)
                    
                    # Find and export duplicates
                    self.file_progress.emit("Finding duplicates...")
                    duplicates_path = self.output_path.replace('.csv', '_duplicates.csv')
                    
                    try:
                        duplicates = self.mapper.find_duplicates(results)
                        if duplicates:
                            self.file_progress.emit(f"Exporting {len(duplicates)} duplicates to CSV...")
                            self.mapper.export_duplicates_to_csv(duplicates, duplicates_path)
                            self.finished.emit(output_file, results, duplicates_path, len(duplicates))
                        else:
                            self.finished.emit(output_file, results, None, 0)
                    except Exception as dup_error:
                        logger.error(f"Error in duplicate finding/exporting: {dup_error}")
                        # Continue without duplicates if that part fails
                        self.finished.emit(output_file, results, None, 0)
                        
                except Exception as csv_error:
                    logger.error(f"Error exporting CSV: {csv_error}")
                    self.error.emit(f"Error saving CSV file: {str(csv_error)}")
            else:
                self.error.emit("No valid XLE files found or all files had errors")
                
        except Exception as e:
            # Add more context to the error message
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error mapping XLE files: {e}\n{error_details}")
            self.error.emit(f"Error mapping XLE files: {str(e)}")


class XleMapperApp(QMainWindow):
    """GUI Application for mapping XLE files"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Solinst XLE Mapper")
        self.setMinimumSize(600, 300)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Input folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)
        select_folder_btn = QPushButton("Select Input Folder")
        select_folder_btn.clicked.connect(self.select_input_folder)
        
        folder_layout.addWidget(QLabel("Input:"))
        folder_layout.addWidget(self.folder_label, 1)  # 1 = stretch factor
        folder_layout.addWidget(select_folder_btn)
        main_layout.addLayout(folder_layout)
        
        # Output file selection
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Output CSV file path...")
        select_output_btn = QPushButton("Select Output File")
        select_output_btn.clicked.connect(self.select_output_file)
        
        output_layout.addWidget(QLabel("Output:"))
        output_layout.addWidget(self.output_path, 1)  # 1 = stretch factor
        output_layout.addWidget(select_output_btn)
        main_layout.addLayout(output_layout)
        
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
        
        # Generate button
        generate_btn = QPushButton("Generate Map File")
        generate_btn.clicked.connect(self.start_mapping)
        main_layout.addWidget(generate_btn)
        
        # Status area
        self.status_label = QLabel("Select a folder containing XLE files to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Store paths
        self.input_folder = None
        
        # Worker thread
        self.worker = None
        
    def select_input_folder(self):
        """Open dialog to select input folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with XLE Files")
        if folder:
            self.input_folder = folder
            self.folder_label.setText(folder)
            self.status_label.setText(f"Ready to process XLE files in {os.path.basename(folder)}")
            
            # Suggest default output file
            if not self.output_path.text():
                default_output = os.path.join(folder, "xle_map.csv")
                self.output_path.setText(default_output)
    
    def select_output_file(self):
        """Open dialog to select output file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Map File", "", "CSV Files (*.csv)")
        if file_path:
            # Ensure it has .csv extension
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            self.output_path.setText(file_path)
    
    def start_mapping(self):
        """Start the mapping process"""
        if not self.input_folder:
            QMessageBox.warning(self, "No Folder Selected", 
                               "Please select a folder containing XLE files first.")
            return
            
        output_path = self.output_path.text()
        if not output_path:
            QMessageBox.warning(self, "No Output File", 
                               "Please specify an output file path.")
            return
            
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting XLE mapping...")
        
        # Create and start worker thread
        recursive = self.recursive_checkbox.isChecked()
        self.worker = MapperWorker(self.input_folder, output_path, recursive)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.file_progress.connect(self.update_file_progress)
        self.worker.finished.connect(self.mapping_finished)
        self.worker.error.connect(self.show_error)
        
        # Start mapping
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_file_progress(self, file_info):
        """Update the current file being processed"""
        self.file_label.setText(file_info)
        
    def mapping_finished(self, output_file, results, duplicates_file=None, duplicates_count=0):
        """Handle completion of mapping"""
        count = len(results)
        
        if count == 0:
            self.status_label.setText("No XLE files were found or processed.")
        else:
            status_text = f"Mapping complete. Processed {count} files."
            if duplicates_count > 0:
                status_text += f" Found {duplicates_count} duplicates."
            self.status_label.setText(status_text)
            
        self.progress_bar.setValue(100)
        
        # Show a message box with the results
        message = f"Successfully processed {count} XLE files.\n\n"
        message += f"Map file saved to:\n{output_file}"
        
        if duplicates_file and duplicates_count > 0:
            message += f"\n\nFound {duplicates_count} duplicate files.\n"
            message += f"Duplicates list saved to:\n{duplicates_file}"
        
        QMessageBox.information(
            self, 
            "Mapping Complete",
            message
        )
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Mapping Error", error_message)
        self.status_label.setText("Mapping failed. See error message.")


def process_command_line():
    """Process command line arguments if script is run directly"""
    parser = argparse.ArgumentParser(description='Map Solinst XLE files and extract metadata.')
    parser.add_argument('input_dir', help='Directory containing XLE files')
    parser.add_argument('--output', '-o', help='Output CSV file path', default='xle_map.csv')
    parser.add_argument('--recursive', '-r', action='store_true', help='Include subdirectories')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        mapper = XleMapper()
        
        try:
            print(f"Scanning {args.input_dir} for XLE files...")
            results = mapper.scan_directory(args.input_dir, args.recursive)
            
            if results:
                # Export main results
                output_file = mapper.export_to_csv(results, args.output)
                print(f"Successfully processed {len(results)} files")
                print(f"Map file saved to: {output_file}")
                
                # Find and export duplicates
                duplicates_path = args.output.replace('.csv', '_duplicates.csv')
                duplicates = mapper.find_duplicates(results)
                if duplicates:
                    mapper.export_duplicates_to_csv(duplicates, duplicates_path)
                    print(f"Found {len(duplicates)} duplicate entries")
                    print(f"Duplicates saved to: {duplicates_path}")
                else:
                    print("No duplicate files found")
            else:
                print("No XLE files found or all files had errors")
                
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
        window = XleMapperApp()
        window.show()
        sys.exit(app.exec_())
