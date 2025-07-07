import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                            QCheckBox, QProgressBar, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import the converter from the assumed location
# Adjust the import based on where the lev_to_xle_converter.py file has been moved
sys.path.append(str(Path(__file__).parent))
from lev_to_xle_converter import LevToXleConverter

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
                self.finished.emit([])
                return
                
            # Modified converter method to support progress updates
            converted_files = []
            current_count = 0
            
            for lev_file in Path(self.folder_path).glob(pattern):
                try:
                    # Update progress information
                    self.file_progress.emit(f"Converting: {lev_file.name}")
                    
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
            self.error.emit(f"Conversion error: {str(e)}")


class LevToXleConverterApp(QMainWindow):
    """Main application window for the LEV to XLE converter"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Solinst LEV to XLE Converter")
        self.setMinimumSize(550, 250)
        
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
        self.status_label = QLabel("Select a folder containing .lev files to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
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
        
        # Create and start worker thread
        recursive = self.recursive_checkbox.isChecked()
        self.worker = ConverterWorker(self.folder_path, recursive)
        
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LevToXleConverterApp()
    window.show()
    sys.exit(app.exec_())
