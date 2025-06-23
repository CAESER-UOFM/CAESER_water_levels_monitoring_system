import os
import sys
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QCheckBox, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import the SolinstReader from its location
sys.path.append(str(Path(__file__).parent.parent / "src" / "gui" / "handlers"))
from solinst_reader import SolinstReader

# Set up logging
logger = logging.getLogger(__name__)

class UnitConverter:
    """Converts XLE files from meters to feet"""
    
    # Conversion factor from meters to feet
    M_TO_FT = 3.28084
    
    def __init__(self):
        """Initialize unit converter"""
        self.reader = SolinstReader()
    
    def convert_directory(self, directory: str, recursive: bool = True) -> Dict[str, int]:
        """
        Scan directory for XLE files and convert units where needed
        
        Args:
            directory: Directory to scan
            recursive: Whether to include subdirectories
            
        Returns:
            Statistics about converted files
        """
        directory_path = Path(directory)
        pattern = "**/*.xle" if recursive else "*.xle"
        
        stats = {
            'total': 0,
            'converted': 0,
            'already_ft': 0,
            'errors': 0
        }
        
        for xle_file in directory_path.glob(pattern):
            stats['total'] += 1
            try:
                was_converted = self.convert_file(xle_file)
                if was_converted:
                    stats['converted'] += 1
                else:
                    stats['already_ft'] += 1
            except Exception as e:
                logger.error(f"Error converting {xle_file}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def convert_file(self, file_path: Path) -> bool:
        """
        Convert a single XLE file from meters to feet
        
        Args:
            file_path: Path to the XLE file
            
        Returns:
            True if file was converted, False if already in feet
        """
        # Check if file needs conversion by parsing XML
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find the Ch1_data_header element and check unit
        ch1_header = root.find('.//Ch1_data_header')
        if not ch1_header:
            raise ValueError(f"Invalid XLE file structure: missing Ch1_data_header")
        
        unit_elem = ch1_header.find('Unit')
        if not unit_elem:
            raise ValueError(f"Invalid XLE file structure: missing Unit element")
        
        # Check if already in feet (case insensitive)
        current_unit = unit_elem.text.strip().lower() if unit_elem.text else ""
        if 'ft' in current_unit or 'feet' in current_unit:
            logger.info(f"File {file_path.name} already using feet units")
            return False
        
        if not ('m' in current_unit or 'meter' in current_unit):
            logger.warning(f"Unknown unit '{current_unit}' - assuming meters")
        
        # Convert data
        data_elem = root.find('.//Data')
        if not data_elem:
            raise ValueError(f"Invalid XLE file structure: missing Data element")
        
        # Update the unit to feet
        unit_elem.text = "ft"
        
        # Convert all pressure values from meters to feet
        for log_entry in data_elem.findall('Log'):
            ch1_elem = log_entry.find('ch1')
            if ch1_elem is not None and ch1_elem.text:
                try:
                    value_m = float(ch1_elem.text)
                    value_ft = value_m * self.M_TO_FT
                    ch1_elem.text = f"{value_ft:.6f}"  # Keep 6 decimal places
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert value '{ch1_elem.text}' to float")
        
        # Write back the modified XML
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        logger.info(f"Converted {file_path.name} from meters to feet")
        return True


class ConverterWorker(QThread):
    """Worker thread for unit conversion"""
    progress = pyqtSignal(int)
    file_progress = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Stats dictionary
    error = pyqtSignal(str)
    
    def __init__(self, folder_path, recursive=True):
        super().__init__()
        self.folder_path = folder_path
        self.recursive = recursive
        self.converter = UnitConverter()
        
    def run(self):
        try:
            # First count total files to process for progress tracking
            self.file_progress.emit("Scanning for XLE files...")
            total_files = sum(1 for _ in Path(self.folder_path).glob('**/*.xle' if self.recursive else '*.xle'))
            
            if total_files == 0:
                self.error.emit("No XLE files found in the selected folder")
                return
                
            self.file_progress.emit(f"Found {total_files} XLE files to process")
            
            # Keep track of processed files for manual progress updates
            processed = 0
            stats = {
                'total': 0,
                'converted': 0,
                'already_ft': 0,
                'errors': 0
            }
            
            # Process files with progress tracking
            pattern = "**/*.xle" if self.recursive else "*.xle"
            for xle_file in Path(self.folder_path).glob(pattern):
                try:
                    # Update progress info
                    processed += 1
                    self.file_progress.emit(f"Processing {processed}/{total_files}: {xle_file.name}")
                    progress_percent = int((processed / total_files) * 100)
                    self.progress.emit(progress_percent)
                    
                    # Perform conversion
                    stats['total'] += 1
                    try:
                        was_converted = self.converter.convert_file(xle_file)
                        if was_converted:
                            stats['converted'] += 1
                            self.file_progress.emit(f"Converted {xle_file.name} from meters to feet")
                        else:
                            stats['already_ft'] += 1
                            self.file_progress.emit(f"Skipped {xle_file.name} - already in feet")
                    except Exception as e:
                        logger.error(f"Error converting {xle_file}: {e}")
                        stats['errors'] += 1
                        self.file_progress.emit(f"Error processing {xle_file.name}: {str(e)}")
                        
                except Exception as e:
                    self.error.emit(f"Error processing {xle_file.name}: {str(e)}")
            
            self.finished.emit(stats)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error converting units: {e}\n{error_details}")
            self.error.emit(f"Error converting units: {str(e)}")


class UnitConverterApp(QMainWindow):
    """GUI Application for converting units in XLE files"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Solinst XLE Unit Converter (m→ft)")
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
        
        # Warning label
        warning_layout = QHBoxLayout()
        warning_label = QLabel("⚠️ WARNING: Original files will be modified. Make sure you have backups!")
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        warning_label.setAlignment(Qt.AlignCenter)
        warning_layout.addWidget(warning_label)
        main_layout.addLayout(warning_layout)
        
        # Recursive option
        recursive_layout = QHBoxLayout()
        self.recursive_checkbox = QCheckBox("Include subfolders")
        self.recursive_checkbox.setChecked(True)
        recursive_layout.addWidget(self.recursive_checkbox)
        recursive_layout.addStretch()
        main_layout.addLayout(recursive_layout)
        
        # Progress information
        self.file_label = QLabel("Ready")
        self.file_label.setWordWrap(True)
        main_layout.addWidget(self.file_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Convert button
        convert_btn = QPushButton("Convert Units (m → ft)")
        convert_btn.clicked.connect(self.start_conversion)
        main_layout.addWidget(convert_btn)
        
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
            
    def start_conversion(self):
        """Start the unit conversion process"""
        if not self.input_folder:
            QMessageBox.warning(self, "No Folder Selected", 
                               "Please select a folder containing XLE files first.")
            return
            
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            "Confirm Unit Conversion",
            "This will modify the original files, converting water levels from meters to feet.\n\n"
            "Make sure you have a backup of your data before proceeding.\n\n"
            "Do you want to continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
            
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting unit conversion...")
        
        # Create and start worker thread
        recursive = self.recursive_checkbox.isChecked()
        self.worker = ConverterWorker(self.input_folder, recursive)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.file_progress.connect(self.update_file_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(self.show_error)
        
        # Start conversion
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_file_progress(self, file_info):
        """Update the current file being processed"""
        self.file_label.setText(file_info)
        
    def conversion_finished(self, stats):
        """Handle completion of conversion"""
        total = stats['total']
        converted = stats['converted']
        already_ft = stats['already_ft']
        errors = stats['errors']
        
        status_text = f"Conversion complete. Processed {total} files."
        self.status_label.setText(status_text)
        self.progress_bar.setValue(100)
        
        # Show a message box with the results
        message = f"Processed {total} XLE files:\n\n" + \
                  f"- {converted} files converted from meters to feet\n" + \
                  f"- {already_ft} files already in feet (not modified)\n" + \
                  f"- {errors} files with errors\n\n"
        
        QMessageBox.information(self, "Unit Conversion Complete", message)
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Conversion Error", error_message)
        self.status_label.setText("Conversion failed. See error message.")


def process_command_line():
    """Process command line arguments if script is run directly"""
    parser = argparse.ArgumentParser(description='Convert XLE water level units from meters to feet.')
    parser.add_argument('input_dir', help='Directory containing XLE files')
    parser.add_argument('--recursive', '-r', action='store_true', help='Include subdirectories')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        converter = UnitConverter()
        
        try:
            print(f"Scanning {args.input_dir} for XLE files...")
            stats = converter.convert_directory(args.input_dir, args.recursive)
            
            print(f"Processed {stats['total']} XLE files:")
            print(f"- {stats['converted']} files converted from meters to feet")
            print(f"- {stats['already_ft']} files already in feet (not modified)")
            print(f"- {stats['errors']} files with errors")
            
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
        window = UnitConverterApp()
        window.show()
        sys.exit(app.exec_())
