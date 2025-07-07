import os
import sys
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Set up logging
logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Indexes PDF and TXT files in a directory structure and creates a CSV index"""
    
    def __init__(self):
        """Initialize document indexer"""
        pass
    
    def index_files(self, source_dir: str) -> List[Dict[str, str]]:
        """
        Find PDF and TXT files in source directory and create index entries
        
        Args:
            source_dir: Source directory to scan (including subfolders)
            
        Returns:
            List of dictionaries with file information
        """
        source_path = Path(source_dir)
        file_entries = []
        
        # Find and process PDF files
        for pdf_file in source_path.glob("**/*.pdf"):
            try:
                entry = self._create_file_entry(pdf_file, source_path)
                file_entries.append(entry)
            except Exception as e:
                logger.error(f"Error indexing {pdf_file}: {e}")
        
        # Find and process TXT files
        for txt_file in source_path.glob("**/*.txt"):
            try:
                entry = self._create_file_entry(txt_file, source_path)
                file_entries.append(entry)
            except Exception as e:
                logger.error(f"Error indexing {txt_file}: {e}")
        
        # Sort entries by folder path and then by filename
        file_entries.sort(key=lambda x: (x['folder_path'], x['file_name']))
        
        return file_entries
    
    def _create_file_entry(self, file_path: Path, root_path: Path) -> Dict[str, str]:
        """
        Create an index entry for a file
        
        Args:
            file_path: Path to the file
            root_path: Root path of the scan
            
        Returns:
            Dictionary with file information
        """
        # Get file stats
        file_stat = file_path.stat()
        
        # Calculate relative folder path from root
        rel_path = file_path.parent.relative_to(root_path)
        folder_path = str(rel_path) if rel_path.parts else '.'
        
        # Create Windows-style file:// URL for clickable link
        file_url = f"file:///{file_path.absolute().as_posix()}"
        
        # Create entry
        entry = {
            'file_name': file_path.name,
            'file_type': file_path.suffix.lower().replace('.', ''),
            'folder_path': folder_path,
            'file_url': file_url,
            'size_kb': f"{file_stat.st_size / 1024:.2f}",
            'modified_date': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'full_path': str(file_path)
        }
        
        return entry
    
    def export_to_csv(self, entries: List[Dict[str, str]], output_file: str) -> str:
        """
        Export file index to CSV
        
        Args:
            entries: List of file entry dictionaries
            output_file: Path to save CSV file
            
        Returns:
            Path to the saved CSV file
        """
        if not entries:
            logger.warning("No entries to export")
            return None
            
        # Define column order for the CSV
        columns = [
            'file_name', 'file_type', 'folder_path', 
            'size_kb', 'modified_date', 'file_url', 'full_path'
        ]
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for entry in entries:
                writer.writerow(entry)
                
        logger.info(f"Exported {len(entries)} entries to {output_file}")
        return output_file


class IndexerWorker(QThread):
    """Worker thread for document indexing"""
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(str, int, int)  # Output file, PDF count, TXT count
    error = pyqtSignal(str)
    
    def __init__(self, source_dir, output_file):
        super().__init__()
        self.source_dir = source_dir
        self.output_file = output_file
        self.indexer = DocumentIndexer()
        
    def run(self):
        try:
            source_path = Path(self.source_dir)
            
            # Emit progress status
            self.status_update.emit("Scanning for PDF and TXT files...")
            self.progress.emit(10)  # Initial progress
            
            # First scan to count files for better progress reporting
            pdf_files = list(source_path.glob("**/*.pdf"))
            pdf_count = len(pdf_files)
            self.status_update.emit(f"Found {pdf_count} PDF files")
            
            txt_files = list(source_path.glob("**/*.txt"))
            txt_count = len(txt_files)
            self.status_update.emit(f"Found {txt_count} TXT files")
            
            total_files = pdf_count + txt_count
            
            if total_files == 0:
                self.error.emit("No PDF or TXT files found in the selected folder")
                return
                
            self.status_update.emit(f"Indexing {total_files} files...")
            self.progress.emit(20)  # Update progress
            
            # Custom indexing with progress tracking
            file_entries = []
            processed = 0
            
            # Process PDF files
            self.status_update.emit("Processing PDF files...")
            for pdf_file in pdf_files:
                try:
                    entry = self.indexer._create_file_entry(pdf_file, source_path)
                    file_entries.append(entry)
                    
                    # Update progress
                    processed += 1
                    if processed % 10 == 0 or processed == total_files:
                        progress_value = 20 + int(60 * (processed / total_files))
                        self.progress.emit(progress_value)
                        self.status_update.emit(f"Processed {processed}/{total_files} files")
                        
                except Exception as e:
                    logger.error(f"Error indexing {pdf_file}: {e}")
            
            # Process TXT files
            self.status_update.emit("Processing TXT files...")
            for txt_file in txt_files:
                try:
                    entry = self.indexer._create_file_entry(txt_file, source_path)
                    file_entries.append(entry)
                    
                    # Update progress
                    processed += 1
                    if processed % 10 == 0 or processed == total_files:
                        progress_value = 20 + int(60 * (processed / total_files))
                        self.progress.emit(progress_value)
                        self.status_update.emit(f"Processed {processed}/{total_files} files")
                        
                except Exception as e:
                    logger.error(f"Error indexing {txt_file}: {e}")
            
            # Sort entries
            self.status_update.emit("Sorting entries...")
            file_entries.sort(key=lambda x: (x['folder_path'], x['file_name']))
            self.progress.emit(85)  # Update progress
            
            # Export to CSV
            self.status_update.emit(f"Exporting {len(file_entries)} entries to CSV...")
            output_file = self.indexer.export_to_csv(file_entries, self.output_file)
            self.progress.emit(100)  # Final progress
            
            # Signal completion
            self.finished.emit(output_file, pdf_count, txt_count)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Indexing error: {e}\n{error_details}")
            self.error.emit(f"Error indexing files: {str(e)}")


class DocumentIndexerApp(QMainWindow):
    """GUI Application for indexing PDF and TXT files"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Document File Indexer")
        self.setMinimumSize(600, 300)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Source folder selection
        source_layout = QHBoxLayout()
        self.source_label = QLabel("No folder selected")
        self.source_label.setWordWrap(True)
        select_source_btn = QPushButton("Select Source Folder")
        select_source_btn.clicked.connect(self.select_source_folder)
        
        source_layout.addWidget(QLabel("Source:"))
        source_layout.addWidget(self.source_label, 1)  # 1 = stretch factor
        source_layout.addWidget(select_source_btn)
        main_layout.addLayout(source_layout)
        
        # Output file selection
        output_layout = QHBoxLayout()
        self.output_label = QLabel("No output file selected")
        self.output_label.setWordWrap(True)
        select_output_btn = QPushButton("Select Output CSV")
        select_output_btn.clicked.connect(self.select_output_file)
        
        output_layout.addWidget(QLabel("Output:"))
        output_layout.addWidget(self.output_label, 1)  # 1 = stretch factor
        output_layout.addWidget(select_output_btn)
        main_layout.addLayout(output_layout)
        
        # Progress information
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Index button
        index_btn = QPushButton("Create File Index")
        index_btn.clicked.connect(self.start_indexing)
        main_layout.addWidget(index_btn)
        
        # Result area
        self.result_label = QLabel("Select source folder and output file to begin")
        self.result_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.result_label)
        
        # Store paths
        self.source_folder = None
        self.output_file = None
        
        # Worker thread
        self.worker = None
        
    def select_source_folder(self):
        """Open dialog to select source folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Index")
        if folder:
            self.source_folder = folder
            self.source_label.setText(folder)
            
            # Suggest default output file if none selected yet
            if not self.output_file:
                default_output = os.path.join(folder, "document_index.csv")
                self.output_file = default_output
                self.output_label.setText(default_output)
                
            self.update_status()
    
    def select_output_file(self):
        """Open dialog to select output file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Index File", "", "CSV Files (*.csv)")
        if file_path:
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            self.output_file = file_path
            self.output_label.setText(file_path)
            self.update_status()
    
    def update_status(self):
        """Update the status message based on selections"""
        if self.source_folder and self.output_file:
            self.result_label.setText("Ready to create document index")
        else:
            missing = []
            if not self.source_folder:
                missing.append("source folder")
            if not self.output_file:
                missing.append("output file")
            self.result_label.setText(f"Please select {' and '.join(missing)} to continue")
    
    def start_indexing(self):
        """Start the indexing process"""
        if not self.source_folder:
            QMessageBox.warning(self, "No Folder Selected", 
                               "Please select a source folder first.")
            return
            
        if not self.output_file:
            QMessageBox.warning(self, "No Output File Selected", 
                               "Please select an output CSV file first.")
            return
            
        # Reset progress
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting document indexing...")
        self.result_label.setText("Indexing files...")
        
        # Create and start worker thread
        self.worker = IndexerWorker(self.source_folder, self.output_file)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status_label)
        self.worker.finished.connect(self.indexing_finished)
        self.worker.error.connect(self.show_error)
        
        # Start indexing
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_status_label(self, status_text):
        """Update the status label"""
        self.status_label.setText(status_text)
        
    def indexing_finished(self, output_file, pdf_count, txt_count):
        """Handle completion of indexing"""
        total = pdf_count + txt_count
        
        status_text = f"Indexing complete. Indexed {total} files."
        self.result_label.setText(status_text)
        self.progress_bar.setValue(100)
        
        # Show message box with results
        message = f"Successfully indexed {total} files:\n\n" + \
                  f"- {pdf_count} PDF files\n" + \
                  f"- {txt_count} TXT files\n\n" + \
                  f"Index saved to:\n{output_file}\n\n" + \
                  f"Open the CSV file in Excel to view and use the clickable links."
        
        QMessageBox.information(
            self, 
            "Indexing Complete",
            message
        )
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Indexing Error", error_message)
        self.result_label.setText("Indexing failed. See error message.")


def process_command_line():
    """Process command line arguments if script is run directly"""
    parser = argparse.ArgumentParser(description='Create index of PDF and TXT files with clickable links.')
    parser.add_argument('source_dir', help='Source directory to scan')
    parser.add_argument('--output', '-o', help='Output CSV file path', default='document_index.csv')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        indexer = DocumentIndexer()
        
        try:
            print(f"Scanning {args.source_dir} for PDF and TXT files...")
            entries = indexer.index_files(args.source_dir)
            
            if entries:
                output_file = indexer.export_to_csv(entries, args.output)
                
                pdf_count = sum(1 for e in entries if e['file_type'] == 'pdf')
                txt_count = sum(1 for e in entries if e['file_type'] == 'txt')
                total = len(entries)
                
                print(f"Successfully indexed {total} files:")
                print(f"- {pdf_count} PDF files")
                print(f"- {txt_count} TXT files")
                print(f"Index saved to: {output_file}")
                print("Open the CSV file in Excel to view and use the clickable links.")
            else:
                print("No PDF or TXT files found in the specified directory.")
                
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
        window = DocumentIndexerApp()
        window.show()
        sys.exit(app.exec_())
