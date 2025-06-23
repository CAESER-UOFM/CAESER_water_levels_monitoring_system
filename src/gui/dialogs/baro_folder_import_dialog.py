from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QCheckBox, QMessageBox, QGroupBox,
                           QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication  # Add this import
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import pandas as pd
import logging
from pathlib import Path
import matplotlib.dates as mdates
from datetime import datetime
from ..handlers.baro_folder_processor import BaroFolderProcessor
from .baro_progress_dialog import BaroProgressDialog

logger = logging.getLogger(__name__)

class BaroFolderImportDialog(QDialog):
    def __init__(self, baro_model, parent=None):
        super().__init__(parent)
        self.baro_model = baro_model
        self.folder_path = None
        self.processor = BaroFolderProcessor(baro_model)
        self.current_serial = None
        self.scan_results = None
        
        self.setup_ui()

    def set_button_width_with_padding(self, button, padding=20):
        """Set button width based on content plus padding"""
        hint = button.sizeHint()
        button.setFixedWidth(hint.width() + padding)

    def setup_ui(self):
        self.setWindowTitle("Import Barologger Files")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)
        main_layout = QVBoxLayout(self)

        # Folder selection group
        folder_group = QGroupBox("Folder Selection")
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(4)  # Reduce spacing between elements
        
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setMinimumWidth(200)
        self.folder_label.setMaximumWidth(400)
        self.folder_label.setWordWrap(True)
        self.folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        # Create a sub-layout for the buttons to keep them together
        button_layout = QHBoxLayout()
        button_layout.setSpacing(2)  # Very tight spacing between controls
        button_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        self.subfolder_cb = QCheckBox("Include Subfolders")
        
        self.scan_btn = QPushButton("Scan Folder")
        self.scan_btn.clicked.connect(self.scan_folder)
        self.scan_btn.setEnabled(False)
        
        # Set dynamic widths with padding
        self.set_button_width_with_padding(self.select_folder_btn, 30)
        self.set_button_width_with_padding(self.subfolder_cb, 30)
        self.set_button_width_with_padding(self.scan_btn, 30)
        
        # Add buttons to the button layout
        button_layout.addWidget(self.select_folder_btn)
        button_layout.addWidget(self.subfolder_cb)
        button_layout.addWidget(self.scan_btn)
        
        folder_layout.addWidget(self.folder_label, 1)
        folder_layout.addStretch()  # Add stretch to push buttons to the right
        folder_layout.addLayout(button_layout)  # Add the button layout
        folder_layout.setContentsMargins(4, 4, 12, 4)  # Add right margin to match bottom buttons
        folder_group.setLayout(folder_layout)
        main_layout.addWidget(folder_group)

        # Summary section
        summary_group = QGroupBox("Import Summary")
        summary_layout = QVBoxLayout()
        self.summary_label = QLabel()
        summary_layout.addWidget(self.summary_label)
        summary_group.setLayout(summary_layout)
        main_layout.addWidget(summary_group)

        # Split view for table and plot
        content_layout = QHBoxLayout()

        # Barologger list table
        table_group = QGroupBox("Barologger Files")
        table_layout = QVBoxLayout()
        self.baro_table = QTableWidget()
        self.baro_table.setColumnCount(6)
        self.baro_table.setHorizontalHeaderLabels([
            "Include", "Overwrite", "Serial Number", "Location", "Files", "Time Range"
        ])
        self.baro_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.baro_table.itemSelectionChanged.connect(self.on_selection_changed)
        table_layout.addWidget(self.baro_table)
        table_group.setLayout(table_layout)
        content_layout.addWidget(table_group)

        # Plot area
        plot_group = QGroupBox("Data Preview")
        plot_layout = QVBoxLayout()
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)
        content_layout.addWidget(plot_group)

        main_layout.addLayout(content_layout)

        # Import controls
        controls_group = QGroupBox("Import Controls")
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        self.import_btn = QPushButton("Import Selected")
        self.import_btn.clicked.connect(self.import_selected)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        controls_layout.addWidget(self.import_btn)
        controls_layout.addWidget(self.cancel_btn)
        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

    def select_folder(self):
        """Handle folder selection"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with XLE Files",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder_path:
            self.folder_path = Path(folder_path)
            self.folder_label.setText(str(self.folder_path))
            self.scan_btn.setEnabled(True)
            # Clear previous results
            self.scan_results = None
            self.baro_table.setRowCount(0)
            self.summary_label.clear()
            self.figure.clear()
            self.canvas.draw()

    def scan_folder(self):
        """Scan folder for barologger files"""
        if not self.folder_path:
            QMessageBox.warning(self, "Warning", "Please select a folder first")
            return

        try:
            # Create and show progress dialog
            progress_dialog = BaroProgressDialog(self)
            progress_dialog.show()
            QApplication.processEvents()  # Force UI update
            
            include_subfolders = self.subfolder_cb.isChecked()
            
            # Process files
            self.scan_results = self.processor.scan_folder(
                self.folder_path, 
                include_subfolders,
                progress_dialog
            )
            
            # Only close if not canceled
            if not progress_dialog.was_canceled():
                progress_dialog.close()
            
            if progress_dialog.was_canceled():
                self.scan_results = None
                return
                
            if 'error' in self.scan_results:
                QMessageBox.warning(self, "Warning", self.scan_results['error'])
                return

            self.update_summary()
            self.populate_table()
            
        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to scan folder: {str(e)}")

    def update_summary(self):
        """Update the summary section with scan results"""
        if not self.scan_results or 'error' in self.scan_results:
            return

        summary_text = (
            f"Total XLE files found: {self.scan_results['file_count']}\n"
            f"Valid barologger files: {self.scan_results['processed_count']}\n"
            f"Number of barologgers: {len(self.scan_results['barologgers'])}"
        )
        self.summary_label.setText(summary_text)

    def populate_table(self):
        """Populate the barologger table with scan results"""
        self.baro_table.setRowCount(0)
        if not self.scan_results or 'error' in self.scan_results:
            return

        for serial, data in self.scan_results['barologgers'].items():
            row = self.baro_table.rowCount()
            self.baro_table.insertRow(row)
            
            # Include checkbox (column 0)
            include_cb = QCheckBox()
            include_cb.setChecked(True)
            include_cb.stateChanged.connect(lambda state, r=row: self.on_include_changed(state, r))
            self.baro_table.setCellWidget(row, 0, include_cb)

            # Overwrite checkbox (column 1)
            overwrite_cb = QCheckBox()
            # Check for overlap immediately and enable if needed
            result = self.processor.process_barologger_files(
                serial, data['files']
            )
            has_overlap = result.get('has_overlap', False) if result else False
            overwrite_cb.setEnabled(has_overlap)
            self.baro_table.setCellWidget(row, 1, overwrite_cb)
            
            # Regular cells (shifted one column right)
            self.baro_table.setItem(row, 2, QTableWidgetItem(serial))
            self.baro_table.setItem(row, 3, QTableWidgetItem(
                self.processor.processor.get_logger_location(serial)))
            self.baro_table.setItem(row, 4, QTableWidgetItem(str(len(data['files']))))
            self.baro_table.setItem(row, 5, QTableWidgetItem(
                f"{data['time_ranges'][0][0].strftime('%Y-%m-%d')} to "
                f"{data['time_ranges'][-1][1].strftime('%Y-%m-%d')}")
            )

    def on_selection_changed(self):
        """Handle barologger selection change"""
        selected_items = self.baro_table.selectedItems()
        if not selected_items:
            return

        serial = self.baro_table.item(selected_items[0].row(), 2).text()
        self.current_serial = serial
        self.preview_data(serial)

    def on_include_changed(self, state: int, row: int):
        """Handle include checkbox state change"""
        overwrite_cb = self.baro_table.cellWidget(row, 1)  # Changed column index to 1
        if not overwrite_cb:
            return
            
        if not state == Qt.Checked:
            # Disable and uncheck overwrite when unchecking include
            overwrite_cb.setChecked(False)

    def has_overlap(self, serial_number: str) -> bool:
        """Check if logger has overlapping data"""
        if not self.scan_results or serial_number not in self.scan_results['barologgers']:
            return False
            
        result = self.processor.process_barologger_files(
            serial_number,
            self.scan_results['barologgers'][serial_number]['files']
        )
        
        return result.get('has_overlap', False) if result else False

    def get_selected_loggers(self) -> list:
        """Get list of selected loggers and their overwrite status"""
        selected = []
        for row in range(self.baro_table.rowCount()):
            include_cb = self.baro_table.cellWidget(row, 0)
            if include_cb and include_cb.isChecked():
                serial = self.baro_table.item(row, 2).text()  # Changed column index to 2
                overwrite_cb = self.baro_table.cellWidget(row, 1)  # Changed column index to 1
                overwrite = overwrite_cb.isChecked() if overwrite_cb else False
                selected.append((serial, overwrite))
        return selected

    def preview_data(self, serial_number: str):
        """Preview data for selected barologger"""
        if not self.scan_results or serial_number not in self.scan_results['barologgers']:
            return

        try:
            # Process files for preview
            result = self.processor.process_barologger_files(
                serial_number, 
                self.scan_results['barologgers'][serial_number]['files']
            )
            
            if not result:
                return

            self.plot_preview(result['data'], result['existing_data'])
            
        except Exception as e:
            logger.error(f"Error previewing data: {e}")

    def plot_preview(self, new_data: pd.DataFrame, existing_data: pd.DataFrame):
        """Plot preview of new and existing data"""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)

            # Plot new data with gap handling
            if not new_data.empty:
                new_data = new_data.sort_values('timestamp_utc')
                time_diff = new_data['timestamp_utc'].diff()
                gaps = time_diff > pd.Timedelta(hours=1)
                segment_ids = gaps.cumsum()

                for segment_id in segment_ids.unique():
                    segment = new_data[segment_ids == segment_id]
                    ax.plot(segment['timestamp_utc'], segment['pressure'], 'b-',
                           label='New Data' if segment_id == 0 else "_nolegend_")

            # Plot existing data with gap handling
            if not existing_data.empty:
                existing_data = existing_data.sort_values('timestamp_utc')
                time_diff = existing_data['timestamp_utc'].diff()
                gaps = time_diff > pd.Timedelta(hours=1)
                segment_ids = gaps.cumsum()

                for segment_id in segment_ids.unique():
                    segment = existing_data[segment_ids == segment_id]
                    ax.plot(segment['timestamp_utc'], segment['pressure'], 'r--',
                           label='Existing Data' if segment_id == 0 else "_nolegend_",
                           alpha=0.5)

                # Find actual overlapping regions
                if not new_data.empty:
                    # Convert timestamps to datetime if they aren't already
                    new_data['timestamp_utc'] = pd.to_datetime(new_data['timestamp_utc'])
                    existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])

                    # Create timestamp sets for efficient lookup
                    existing_timestamps = set(existing_data['timestamp_utc'])
                    new_timestamps = set(new_data['timestamp_utc'])
                    
                    # Find overlapping timestamps
                    overlap_timestamps = sorted(list(existing_timestamps.intersection(new_timestamps)))
                    
                    if overlap_timestamps:
                        # Group consecutive timestamps into ranges
                        overlap_ranges = []
                        range_start = overlap_timestamps[0]
                        prev_time = overlap_timestamps[0]
                        
                        for curr_time in overlap_timestamps[1:]:
                            if (curr_time - prev_time) > pd.Timedelta(hours=1):
                                # Gap found, end current range and start new one
                                overlap_ranges.append((range_start, prev_time))
                                range_start = curr_time
                            prev_time = curr_time
                        
                        # Add the last range
                        overlap_ranges.append((range_start, prev_time))
                        
                        # Highlight each overlap range separately
                        for start, end in overlap_ranges:
                            ax.axvspan(start, end, color='yellow', alpha=0.3, 
                                     label='Overlap Region' if start == overlap_ranges[0][0] else "_nolegend_")

            ax.set_ylabel('Pressure (PSI)')
            ax.grid(True)
            ax.legend()

            # Format date axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            ax.tick_params(axis='x', rotation=45)

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            logger.error(f"Error plotting preview: {e}")

    def import_selected(self):
        """Import data for selected barologgers"""
        selected_loggers = self.get_selected_loggers()
        if not selected_loggers:
            QMessageBox.warning(self, "Warning", "No loggers selected for import")
            return

        try:
            # Create and show progress dialog
            progress_dialog = BaroProgressDialog(self)
            progress_dialog.show()
            progress_dialog.log_message("=== Starting Import Process ===")
            QApplication.processEvents()
            
            # Prepare aggregated data dictionary
            aggregated_data = {}
            
            # Process each selected logger
            progress_dialog.log_message(f"\nPreparing data for {len(selected_loggers)} loggers...")
            progress_dialog.update_progress(0, len(selected_loggers))
            
            for i, (serial, overwrite) in enumerate(selected_loggers, 1):
                if progress_dialog.was_canceled():
                    progress_dialog.close()
                    return
                    
                progress_dialog.update_status(f"Processing logger {serial} ({i}/{len(selected_loggers)})")
                progress_dialog.update_progress(i, len(selected_loggers))
                
                # Process the files for this logger
                result = self.processor.process_barologger_files(
                    serial,
                    self.scan_results['barologgers'][serial]['files']
                )
                
                if result:
                    # Store the processed data and overwrite flag
                    aggregated_data[serial] = {
                        'data': result['data'],
                        'overwrite': overwrite
                    }
                    progress_dialog.log_message(f"Prepared {len(result['data'])} readings for {serial}")
            
            if not aggregated_data:
                progress_dialog.close()
                QMessageBox.warning(self, "Warning", "No valid data to import")
                return
            
            # Define progress callback for batch import
            def update_import_progress(current, total, message):
                if progress_dialog.was_canceled():
                    return
                progress_dialog.update_progress(current, total)
                progress_dialog.update_status(message)
                progress_dialog.log_message(message)
                QApplication.processEvents()
            
            progress_dialog.log_message("\n=== Starting Database Import ===")
            # Perform batch import with progress tracking
            success, message = self.baro_model.batch_import_readings(
                aggregated_data,
                progress_callback=update_import_progress
            )
            
            if success:
                # Log imported files to the database
                try:
                    import sqlite3
                    progress_dialog.log_message("\n=== Logging Imported Files ===")
                    
                    with sqlite3.connect(self.baro_model.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # Log each file individually instead of aggregating by serial number
                        for serial in aggregated_data.keys():
                            # Get each file for this barologger
                            files = self.scan_results['barologgers'][serial]['files']
                            progress_dialog.log_message(f"Logging {len(files)} files for barologger {serial}")
                            
                            for file_idx, file_path in enumerate(files, 1):
                                try:
                                    # Get exact time range for this specific file directly from processor
                                    file_data = self.processor._scanned_data.get(file_path)
                                    if not file_data:
                                        # Read the file if not in cache
                                        df, metadata = self.processor.solinst_reader.read_xle(file_path)
                                        start_date = pd.to_datetime(df['timestamp_utc'].min())
                                        end_date = pd.to_datetime(df['timestamp_utc'].max())
                                    else:
                                        # Use cached data
                                        start_date = pd.to_datetime(file_data['time_range'][0])
                                        end_date = pd.to_datetime(file_data['time_range'][1])
                                    
                                    # Convert timestamps to ISO format strings for SQLite compatibility
                                    start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
                                    end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    # Insert record for this specific file
                                    cursor.execute('''
                                        INSERT INTO barologger_imported_files
                                        (serial_number, starting_date, end_date)
                                        VALUES (?, ?, ?)
                                    ''', (serial, start_date_str, end_date_str))
                                    
                                    progress_dialog.log_message(f"  File {file_idx}: {file_path.name} - {start_date} to {end_date}")
                                except Exception as e:
                                    logger.error(f"Error logging file {file_path}: {e}")
                                    progress_dialog.log_message(f"  Error with file {file_path.name}: {str(e)}")
                            
                        conn.commit()
                except Exception as e:
                    logger.error(f"Error logging imported files: {e}")
                    progress_dialog.log_message(f"Warning: Failed to log imported files: {str(e)}")
                
                # After successfully logging to DB, organize the actual imported files
                try:
                    for serial in aggregated_data.keys():
                        files = self.scan_results['barologgers'][serial]['files']
                        for file_path in files:
                            file_data = self.processor._scanned_data.get(file_path)
                            if file_data:
                                start_date, end_date = file_data['time_range']
                                location = file_data['metadata'].location
                            else:
                                # Fallback to reading file metadata
                                df, metadata = self.processor.solinst_reader.read_xle(file_path)
                                start_date = pd.to_datetime(df['timestamp_utc'].min())
                                end_date = pd.to_datetime(df['timestamp_utc'].max())
                                location = metadata.location
                            organized_path = self.processor.file_organizer.organize_barologger_file(
                                file_path, serial, location, start_date, end_date
                            )
                            if organized_path:
                                progress_dialog.log_message(f"File organized at: {organized_path}")
                except Exception as e:
                    logger.error(f"Error organizing files after import: {e}")
                    progress_dialog.log_message(f"Warning: Failed to organize files: {str(e)}")
                
                progress_dialog.log_message("\n=== Import Complete ===")
                progress_dialog.log_message(message)
                progress_dialog.update_status("Import complete")
                progress_dialog.finish_operation()
                QMessageBox.information(self, "Success", message)
                
                # Do a single refresh cycle in the parent
                parent = self.parent()
                if parent:
                    parent.refresh_data()  # This will do list and plot refresh efficiently
                self.accept()
            else:
                progress_dialog.close()
                QMessageBox.critical(self, "Error", f"Failed to import data: {message}")
                
        except Exception as e:
            logger.error(f"Error in import process: {e}")
            if progress_dialog:
                progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to import data: {str(e)}")
            return

    def _import_data(self):
        # No changes needed if already using BaroFolderProcessor which we've updated
        # Just add a log line to confirm file organization is happening
        logger.info("Files will be organized in the imported_xle_files directory")
