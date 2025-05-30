from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QCheckBox, 
                           QMessageBox, QHBoxLayout, QGroupBox)
from PyQt5.QtCore import Qt 
from ..handlers.baro_import_handler import BaroFileProcessor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import pandas as pd
import logging
from pathlib import Path
import matplotlib.dates as mdates
from datetime import datetime  # Add this import
from ..utils.file_organizer import XLEFileOrganizer

logger = logging.getLogger(__name__)

class SingleFileImportDialog(QDialog):
    def __init__(self, baro_model, file_path, parent=None, metadata=None):
        super().__init__(parent)
        self.baro_model = baro_model
        self.file_path = file_path
        self.processor = BaroFileProcessor(baro_model)
        self.solinst_reader = self.processor.solinst_reader  # Add reference to solinst_reader
        self.metadata = metadata  # Store metadata from previous validation
        self.registration_warning = QLabel()
        self.registration_warning.setStyleSheet("color: orange;")
        self.registration_warning.setVisible(False)
        
        self.setup_ui()
        if self.metadata:
            self.process_validation_results(use_cached=True)  # Use existing metadata
        else:
            self.process_validation_results()
            
    def setup_ui(self):
        self.setWindowTitle("Import Barologger Data")
        layout = QVBoxLayout(self)
        
        # Logger Info Group
        info_group = QGroupBox("Data Information")
        info_layout = QVBoxLayout()
        
        # Time range info with larger font
        self.time_range_info = QLabel()
        font = self.time_range_info.font()
        font.setPointSize(10)
        font.setBold(True)
        self.time_range_info.setFont(font)
        
        info_layout.addWidget(self.time_range_info)
        info_layout.addWidget(self.registration_warning)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Plot
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        
        # Overlap Warning Group
        overlap_group = QGroupBox("Data Overlap")
        overlap_layout = QVBoxLayout()
        self.overlap_label = QLabel()
        self.overlap_label.setStyleSheet("color: red;")
        overlap_layout.addWidget(self.overlap_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.overwrite_cb = QCheckBox("Overwrite existing records")
        self.overwrite_cb.stateChanged.connect(self.toggle_import_button)
        controls_layout.addWidget(self.overwrite_cb)
        controls_layout.addStretch()
        
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.import_data)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        controls_layout.addWidget(self.import_btn)
        controls_layout.addWidget(self.cancel_btn)
        
        overlap_layout.addLayout(controls_layout)
        overlap_group.setLayout(overlap_layout)
        layout.addWidget(overlap_group)

    def toggle_import_button(self, state):
        """Enable import button only if overlap is acknowledged via checkbox"""
        if self.metadata and self.metadata.get('has_overlap', False):
            self.import_btn.setEnabled(state == Qt.Checked)
        else:
            self.import_btn.setEnabled(True)

    def process_validation_results(self, use_cached=False):
        """Handles UI updates based on file validation results"""
        try:
            if not use_cached:
                # First read the file without validation
                df, metadata = self.solinst_reader.read_xle(self.file_path)
                
                # Then do barologger validation
                if not self.solinst_reader.is_barologger(metadata):
                    QMessageBox.critical(self, "Error", "File is not from a barologger")
                    self.reject()
                    return
                
                # Store validation results
                self.metadata = {
                    'serial_number': metadata.serial_number,
                    'preview_data': df,
                    'metadata': metadata
                }
    
            # Convert timestamps in preview data
            self.metadata['preview_data']['timestamp_utc'] = pd.to_datetime(self.metadata['preview_data']['timestamp_utc'])
            
            # Remove local_timestamp if exists
            if 'local_timestamp' in self.metadata['preview_data']:
                del self.metadata['preview_data']['local_timestamp']
    
            # Display new data range
            new_range = (
                f"New Data Range: {self.metadata['preview_data']['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M')} to "
                f"{self.metadata['preview_data']['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M')}"
            )
    
            # Properly get existing data using the same method used in folder processing
            serial_number = self.metadata['serial_number']
            existing_data = self.processor.get_existing_data(serial_number)
            self.metadata['existing_data'] = existing_data
            
            # Handle existing data range display
            existing_range = ""
            if not existing_data.empty:
                existing_range = (
                    f"\nExisting Data Range: "
                    f"{existing_data['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M')} to "
                    f"{existing_data['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                logger.warning("No existing data found for overlap check.")
    
            # Update UI
            self.time_range_info.setText(f"{new_range}{existing_range}")
    
            # Use the same overlap check method as in folder processor
            has_overlap = self._check_overlap(self.metadata['preview_data'], existing_data)
            if has_overlap:
                self.overlap_label.setText("WARNING: Data overlap detected")
                self.overwrite_cb.setVisible(True)
                self.overwrite_cb.setChecked(False)
                self.import_btn.setEnabled(False)
                self.metadata['has_overlap'] = True
            else:
                self.overlap_label.setText("No data overlap detected")
                self.overwrite_cb.setVisible(False)
                self.import_btn.setEnabled(True)
                self.metadata['has_overlap'] = False

            # Update plot
            self.plot_data()
    
        except Exception as e:
            logger.error(f"Error processing validation results: {e}")
            QMessageBox.critical(self, "Error", f"Failed to validate file: {str(e)}")
            self.reject()

    def plot_data(self):
        """Plot data preview, including new and existing data with overlap detection"""
        try:
            self.figure.clear()
            ax1 = self.figure.add_subplot(111)
    
            # Ensure preview data exists
            df = self.metadata['preview_data']
            if df.empty:
                logger.warning("No new data available to plot.")
                return
    
            # Plot new data with gap handling
            df_sorted = df.sort_values('timestamp_utc')
            time_diff = df_sorted['timestamp_utc'].diff()
            gaps = time_diff > pd.Timedelta(hours=1)
            segment_ids = gaps.cumsum()
    
            for segment_id in segment_ids.unique():
                segment = df_sorted[segment_ids == segment_id]
                ax1.plot(segment['timestamp_utc'], segment['pressure'], 'b-', 
                        label='New Data' if segment_id == 0 else "_nolegend_")
    
            # Handle existing data with gaps
            existing_data = self.metadata.get('existing_data', pd.DataFrame(columns=['timestamp_utc', 'pressure']))
            if not existing_data.empty:
                existing_data = existing_data.sort_values('timestamp_utc')
                existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])
    
                # Handle gaps in existing data
                time_diff = existing_data['timestamp_utc'].diff()
                gaps = time_diff > pd.Timedelta(hours=1)
                segment_ids = gaps.cumsum()
    
                # Plot each segment of existing data
                for segment_id in segment_ids.unique():
                    segment = existing_data[segment_ids == segment_id]
                    ax1.plot(segment['timestamp_utc'], segment['pressure'], 'r--',
                            label='Existing Data' if segment_id == 0 else "_nolegend_",
                            alpha=0.5)
    
                # Identify and highlight overlap region
                overlap_start = max(df['timestamp_utc'].min(), existing_data['timestamp_utc'].min())
                overlap_end = min(df['timestamp_utc'].max(), existing_data['timestamp_utc'].max())
    
                if overlap_start < overlap_end:
                    ax1.axvspan(overlap_start, overlap_end, color='yellow', alpha=0.3, label='Overlap Region')
    
            ax1.set_ylabel('Pressure (PSI)')
            ax1.grid(True)
            ax1.legend()
    
            # Get logger info for title
            location = self.processor.get_logger_location(self.metadata['serial_number'])
            self.figure.suptitle(
                f"Serial Number: {self.metadata['serial_number']} | Location: {location}",
                fontsize=12, y=0.95
            )
    
            # Format date axis
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            ax1.tick_params(axis='x', rotation=45)
            self.figure.tight_layout()
            self.canvas.draw()
    
        except Exception as e:
            logger.error(f"Error in plot_data: {e}")

    def import_data(self):
        """Handle data import"""
        try:
            logger.debug("Import button clicked, starting import process...")
    
            if self.metadata['has_overlap'] and not self.overwrite_cb.isChecked():
                QMessageBox.warning(self, "Warning", "Overlapping data exists. Please check overwrite to import.")
                logger.debug("Import canceled due to unchecked overwrite warning.")
                return

            # Register barologger if needed (will only execute if user accepted in process_validation_results)
            if not self.baro_model.barologger_exists(self.metadata['serial_number']):
                baro_data = {
                    'serial_number': self.metadata['serial_number'],
                    'location_description': self.metadata['metadata'].location,
                    'installation_date': self.metadata['preview_data']['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'active',
                    'notes': f'Auto-registered during import on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                }
                success, message = self.baro_model.add_barologger(baro_data)
                if not success:
                    QMessageBox.critical(self, "Error", f"Failed to register barologger: {message}")
                    return
    
            logger.debug("Calling import_readings()...")
    
            success = self.baro_model.import_readings(
                self.metadata['preview_data'],
                self.metadata['serial_number'],
                self.overwrite_cb.isChecked()
            )
    
            logger.debug(f"Import process finished with status: {success}")
    
            if success:
                # Log the imported file in the database
                try:
                    import sqlite3
                    serial_number = self.metadata['serial_number']
                    start_date = pd.to_datetime(self.metadata['preview_data']['timestamp_utc'].min())
                    end_date = pd.to_datetime(self.metadata['preview_data']['timestamp_utc'].max())
                    
                    with sqlite3.connect(self.baro_model.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO barologger_imported_files
                            (serial_number, starting_date, end_date)
                            VALUES (?, ?, ?)
                        ''', (serial_number, start_date, end_date))
                        conn.commit()
                        logger.info(f"Logged imported file for barologger {serial_number}")
                except Exception as e:
                    logger.error(f"Error logging imported file: {e}")
                
                # Organize the imported file after successful import
                try:
                    # Initialize file organizer
                    file_organizer = XLEFileOrganizer(Path(self.baro_model.db_path).parent, db_name=Path(self.baro_model.db_path).stem)
                    
                    # Get location from database
                    location = self._get_location_description(self.metadata['serial_number'])
                    
                    # Get start and end dates from data
                    start_date = pd.to_datetime(self.metadata['preview_data']['timestamp_utc'].min())
                    end_date = pd.to_datetime(self.metadata['preview_data']['timestamp_utc'].max())
                    
                    # Organize the file
                    organized_path = file_organizer.organize_barologger_file(
                        Path(self.file_path), self.metadata['serial_number'], location, start_date, end_date
                    )
                    
                    if organized_path:
                        logger.info(f"File organized at: {organized_path}")
                except Exception as e:
                    logger.error(f"Error organizing file: {e}")
                    # Continue with success even if file organization fails
                
                QMessageBox.information(self, "Success", "Data imported successfully")
                logger.debug("Closing dialog after successful import.")
                # Refresh parent's barologger table
                if self.parent() and hasattr(self.parent(), 'refresh_barologger_list'):
                    self.parent().refresh_barologger_list()
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Import failed")
                logger.debug("Import failed.")
    
        except Exception as e:
            logger.error(f"Error during import: {e}")
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")

    def _check_overlap(self, new_data: pd.DataFrame, existing_data: pd.DataFrame) -> bool:
        """Check for overlapping data between new and existing data using the same method as folder processor"""
        if existing_data.empty or new_data.empty:
            return False

        new_range = (new_data['timestamp_utc'].min(), new_data['timestamp_utc'].max())
        existing_range = (existing_data['timestamp_utc'].min(), existing_data['timestamp_utc'].max())

        # Check if date ranges overlap, not just exact matches
        return not (new_range[1] < existing_range[0] or new_range[0] > existing_range[1])

    def _get_location_description(self, serial_number: str) -> str:
        """Get location description for a barologger"""
        try:
            import sqlite3
            with sqlite3.connect(self.baro_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT location_description
                    FROM barologgers
                    WHERE serial_number = ?
                ''', (serial_number,))
                result = cursor.fetchone()
                return result[0] if result else "Unknown"
        except Exception as e:
            logger.error(f"Error getting location description: {e}")
            return "Unknown"