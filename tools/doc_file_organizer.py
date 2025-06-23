import os
import sys
import shutil
import logging
import argparse
from pathlib import Path
from typing import Dict, Set
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QCheckBox, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Set up logging
logger = logging.getLogger(__name__)

class DocumentOrganizer:
    """Organizes PDF and TXT files from source folder to target folder"""
    
    def __init__(self):
        """Initialize document organizer"""
        pass
    
    def organize_files(self, source_dir: str, target_dir: str) -> Dict[str, int]:
        """
        Find PDF and TXT files in source directory and copy to organized structure
        
        Args:
            source_dir: Source directory to scan (including subfolders)
            target_dir: Target directory for organized files
            
        Returns:
            Statistics about organized files
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        # Create target directory structure
        pdf_dir = target_path / "PDFs"
        txt_dir = target_path / "TXTs"
        
        pdf_dir.mkdir(parents=True, exist_ok=True)
        txt_dir.mkdir(parents=True, exist_ok=True)
        
        # Track statistics
        stats = {
            'pdfs_found': 0,
            'txts_found': 0,
            'pdfs_copied': 0,
            'txts_copied': 0,
            'errors': 0
        }
        
        # Track processed files to avoid duplicates
        processed_files = {
            'pdf': set(),
            'txt': set()
        }
        
        # Find PDF files
        for pdf_file in source_path.glob("**/*.pdf"):
            stats['pdfs_found'] += 1
            
            # Create a unique name based on the path if needed
            target_file = self._get_unique_filename(pdf_file, pdf_dir, processed_files['pdf'])
            processed_files['pdf'].add(target_file.name)
            
            try:
                shutil.copy2(pdf_file, target_file)
                stats['pdfs_copied'] += 1
                logger.info(f"Copied PDF: {pdf_file} -> {target_file}")
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error copying {pdf_file}: {e}")
        
        # Find TXT files
        for txt_file in source_path.glob("**/*.txt"):
            stats['txts_found'] += 1
            
            # Create a unique name based on the path if needed
            target_file = self._get_unique_filename(txt_file, txt_dir, processed_files['txt'])
            processed_files['txt'].add(target_file.name)
            
            try:
                shutil.copy2(txt_file, target_file)
                stats['txts_copied'] += 1
                logger.info(f"Copied TXT: {txt_file} -> {target_file}")
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error copying {txt_file}: {e}")
        
        return stats
    
    def _get_unique_filename(self, source_file: Path, target_dir: Path, used_names: Set[str]) -> Path:
        """
        Create a unique filename to avoid overwriting files
        
        Args:
            source_file: Original file path
            target_dir: Target directory
            used_names: Set of already used filenames
            
        Returns:
            Path object for the target file
        """
        base_name = source_file.name
        
        # If the name is already used, add parent directory names until unique
        if base_name in used_names:
            # Create a unique name by prepending parent directory names
            parts = list(source_file.parts)
            
            # Start with just filename
            unique_name = parts[-1]
            index = 2
            
            # Keep adding parent directory names until the name is unique
            while unique_name in used_names and index <= len(parts):
                # Add another parent directory name
                parent_dir = parts[-index].replace(" ", "_")
                unique_name = f"{parent_dir}-{unique_name}"
                index += 1
                
            # If still not unique, add a number
            counter = 1
            original_name = unique_name
            while unique_name in used_names:
                unique_name = f"{original_name}_{counter}"
                counter += 1
                
            return target_dir / unique_name
        
        # Name is unique, use it
        return target_dir / base_name


class OrganizerWorker(QThread):
    """Worker thread for document organization"""
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Stats dictionary
    error = pyqtSignal(str)
    
    def __init__(self, source_dir, target_dir):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.organizer = DocumentOrganizer()
        
    def run(self):
        try:
            source_path = Path(self.source_dir)
            
            # First count total files for progress tracking
            self.status_update.emit("Scanning for PDF and TXT files...")
            
            # Count PDF files
            pdf_files = list(source_path.glob("**/*.pdf"))
            pdf_count = len(pdf_files)
            self.status_update.emit(f"Found {pdf_count} PDF files")
            
            # Count TXT files
            txt_files = list(source_path.glob("**/*.txt"))
            txt_count = len(txt_files)
            self.status_update.emit(f"Found {txt_count} TXT files")
            
            total_files = pdf_count + txt_count
            
            if total_files == 0:
                self.status_update.emit("No PDF or TXT files found")
                self.finished.emit({"pdfs_copied": 0, "txts_copied": 0, "errors": 0})
                return
                
            self.status_update.emit(f"Total files to process: {total_files}")
            
            # Custom implementation with progress reporting
            target_path = Path(self.target_dir)
            
            # Create target directory structure
            pdf_dir = target_path / "PDFs"
            txt_dir = target_path / "TXTs"
            
            pdf_dir.mkdir(parents=True, exist_ok=True)
            txt_dir.mkdir(parents=True, exist_ok=True)
            
            # Track statistics
            stats = {
                'pdfs_found': pdf_count,
                'txts_found': txt_count,
                'pdfs_copied': 0,
                'txts_copied': 0,
                'errors': 0
            }
            
            # Track processed files to avoid duplicates
            processed_files = {
                'pdf': set(),
                'txt': set()
            }
            
            # Track progress
            processed = 0
            
            # Copy PDF files
            self.status_update.emit("Copying PDF files...")
            for pdf_file in pdf_files:
                try:
                    # Create a unique name based on the path if needed
                    target_file = self.organizer._get_unique_filename(pdf_file, pdf_dir, processed_files['pdf'])
                    processed_files['pdf'].add(target_file.name)
                    
                    # Copy file with metadata
                    shutil.copy2(pdf_file, target_file)
                    stats['pdfs_copied'] += 1
                    
                    # Update progress
                    processed += 1
                    progress_percent = int((processed / total_files) * 100)
                    self.progress.emit(progress_percent)
                    self.status_update.emit(f"Copied PDF ({processed}/{total_files}): {pdf_file.name}")
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error copying {pdf_file}: {e}")
                    self.status_update.emit(f"Error copying: {pdf_file.name}")
            
            # Copy TXT files
            self.status_update.emit("Copying TXT files...")
            for txt_file in txt_files:
                try:
                    # Create a unique name based on the path if needed
                    target_file = self.organizer._get_unique_filename(txt_file, txt_dir, processed_files['txt'])
                    processed_files['txt'].add(target_file.name)
                    
                    # Copy file with metadata
                    shutil.copy2(txt_file, target_file)
                    stats['txts_copied'] += 1
                    
                    # Update progress
                    processed += 1
                    progress_percent = int((processed / total_files) * 100)
                    self.progress.emit(progress_percent)
                    self.status_update.emit(f"Copied TXT ({processed}/{total_files}): {txt_file.name}")
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error copying {txt_file}: {e}")
                    self.status_update.emit(f"Error copying: {txt_file.name}")
            
            self.finished.emit(stats)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Document organization error: {e}\n{error_details}")
            self.error.emit(f"Error organizing documents: {str(e)}")


class DocumentOrganizerApp(QMainWindow):
    """GUI Application for organizing PDF and TXT files"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Document File Organizer")
        self.setMinimumSize(600, 300)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Source folder selection
        source_layout = QHBoxLayout()
        self.source_label = QLabel("No source folder selected")
        self.source_label.setWordWrap(True)
        select_source_btn = QPushButton("Select Source Folder")
        select_source_btn.clicked.connect(self.select_source_folder)
        
        source_layout.addWidget(QLabel("Source:"))
        source_layout.addWidget(self.source_label, 1)  # 1 = stretch factor
        source_layout.addWidget(select_source_btn)
        main_layout.addLayout(source_layout)
        
        # Target folder selection
        target_layout = QHBoxLayout()
        self.target_label = QLabel("No target folder selected")
        self.target_label.setWordWrap(True)
        select_target_btn = QPushButton("Select Target Folder")
        select_target_btn.clicked.connect(self.select_target_folder)
        
        target_layout.addWidget(QLabel("Target:"))
        target_layout.addWidget(self.target_label, 1)  # 1 = stretch factor
        target_layout.addWidget(select_target_btn)
        main_layout.addLayout(target_layout)
        
        # Progress information
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
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
        self.result_label = QLabel("Select source and target folders to begin")
        self.result_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.result_label)
        
        # Store paths
        self.source_folder = None
        self.target_folder = None
        
        # Worker thread
        self.worker = None
        
    def select_source_folder(self):
        """Open dialog to select source folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder with Documents")
        if folder:
            self.source_folder = folder
            self.source_label.setText(folder)
            self.update_status()
    
    def select_target_folder(self):
        """Open dialog to select target folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Target Folder for Organized Files")
        if folder:
            self.target_folder = folder
            self.target_label.setText(folder)
            self.update_status()
    
    def update_status(self):
        """Update the status message based on selected folders"""
        if self.source_folder and self.target_folder:
            self.result_label.setText("Ready to organize files")
        else:
            missing = []
            if not self.source_folder:
                missing.append("source folder")
            if not self.target_folder:
                missing.append("target folder")
            self.result_label.setText(f"Please select {' and '.join(missing)} to continue")
    
    def start_organization(self):
        """Start organizing files"""
        if not self.source_folder:
            QMessageBox.warning(self, "No Source Folder Selected", 
                               "Please select a source folder first.")
            return
            
        if not self.target_folder:
            QMessageBox.warning(self, "No Target Folder Selected", 
                               "Please select a target folder first.")
            return
            
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting file organization...")
        self.result_label.setText("Organizing files...")
        
        # Create and start worker thread
        self.worker = OrganizerWorker(self.source_folder, self.target_folder)
        
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
        pdf_count = stats['pdfs_copied']
        txt_count = stats['txts_copied']
        error_count = stats.get('errors', 0)
        total = pdf_count + txt_count
        
        status_text = f"Organization complete. Organized {total} files."
        self.result_label.setText(status_text)
        self.progress_bar.setValue(100)
        
        # Show a message box with the results
        message = f"Successfully organized {total} files:\n\n" + \
                  f"- {pdf_count} PDF files\n" + \
                  f"- {txt_count} TXT files\n\n" + \
                  f"Files have been organized in:\n{self.target_folder}"
                  
        if error_count > 0:
            message += f"\n\nEncountered {error_count} errors during processing."
        
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
    parser = argparse.ArgumentParser(description='Organize PDF and TXT files from source to target folder.')
    parser.add_argument('source_dir', help='Source directory containing PDF and TXT files')
    parser.add_argument('target_dir', help='Target directory for organized files')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        organizer = DocumentOrganizer()
        
        try:
            print(f"Scanning {args.source_dir} for PDF and TXT files...")
            stats = organizer.organize_files(args.source_dir, args.target_dir)
            
            total = stats['pdfs_copied'] + stats['txts_copied']
            print(f"Successfully organized {total} files:")
            print(f"- {stats['pdfs_copied']} PDF files")
            print(f"- {stats['txts_copied']} TXT files")
            
            if stats['errors'] > 0:
                print(f"Encountered {stats['errors']} errors during processing.")
                
            print(f"Files organized in: {args.target_dir}")
            
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
        window = DocumentOrganizerApp()
        window.show()
        sys.exit(app.exec_())
