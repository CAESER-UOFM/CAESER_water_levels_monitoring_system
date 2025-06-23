# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 10:40:57 2025

@author: bledesma
"""

# In water_level_import_dialog.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QCheckBox,
                           QMessageBox, QHBoxLayout, QGroupBox, QTabWidget,
                           QTableWidget, QTableWidgetItem,QWidget, QApplication)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg,
                                              NavigationToolbar2QT)  # Add NavigationToolbar
from PyQt5.QtCore import Qt 
from matplotlib.figure import Figure
import logging
from pathlib import Path
from ..handlers.water_level_single_handler import WaterLevelHandler
from ..dialogs.transducer_dialog import TransducerDialog  # Add this import
from ...database.models.well_model import WellModel  # Add this import
import pandas as pd
from typing import Dict
from datetime import  timedelta
import matplotlib.dates as mdates
import time
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

class WaterLevelImportDialog(QDialog):
    def __init__(self, water_level_model, file_path, well_number, parent=None, transducer_status=None):
        logger.info("Initializing WaterLevelImportDialog")
        super().__init__(parent)
        self.water_level_model = water_level_model
        self.file_path = file_path
        self.well_number = well_number
        logger.info("Creating WaterLevelHandler")
        self.handler = WaterLevelHandler(water_level_model)
        self.metadata = None
        self.transducer_status = transducer_status or {'status': 'unknown'}
        
        # Add transducer warning label
        self.transducer_warning = QLabel()
        self.transducer_warning.setStyleSheet("color: orange;")
        if self.transducer_status.get('status') == 'warning':
            self.transducer_warning.setText(self.transducer_status.get('message', ''))
            self.transducer_warning.setVisible(True)
        else:
            self.transducer_warning.setVisible(False)
            
        logger.info("Setting up UI")
        self.setup_ui()
        logger.info("Starting file validation")
        self.validate_file()
        logger.info("Dialog initialization complete")
        
    def setup_ui(self):
        self.setWindowTitle("Import Water Level Data")
        self.resize(1000, 800)
        layout = QVBoxLayout(self)
        
        # Data Information Group
        info_group = QGroupBox("Data Information")
        info_layout = QVBoxLayout()
        self.time_range_info = QLabel()
        self.time_range_info.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.time_range_info)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Tab widget for different views
        tab_widget = QTabWidget()
        
        # Data Preview Tab
        preview_tab = QWidget()
        preview_layout = QVBoxLayout()
        
        # Summary information
        self.summary_info = QLabel()
        preview_layout.addWidget(self.summary_info)
        
        # Data preview table
        self.preview_table = QTableWidget()
        preview_layout.addWidget(self.preview_table)
        preview_tab.setLayout(preview_layout)
        tab_widget.addTab(preview_tab, "Data Preview")
        
        # Plot Tab
        plot_tab = QWidget()
        plot_layout = QVBoxLayout()
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)  # Add toolbar
        plot_layout.addWidget(self.toolbar)  # Add toolbar above plot
        plot_layout.addWidget(self.canvas)
        plot_tab.setLayout(plot_layout)
        tab_widget.addTab(plot_tab, "Visualization")
        
        layout.addWidget(tab_widget)
        
        # Processing Information
        process_group = QGroupBox("Processing Information")
        process_layout = QVBoxLayout()
        
        # Barometric info
        self.baro_info = QLabel()
        process_layout.addWidget(self.baro_info)
        
        # Insertion level info
        self.insertion_info = QLabel()
        process_layout.addWidget(self.insertion_info)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        # Controls at bottom
        controls_layout = QHBoxLayout()
        self.overlap_warning = QLabel()
        self.overlap_warning.setStyleSheet("color: red; font-weight: bold;")
        self.overlap_warning.setVisible(False)  # Hidden by default
        
        self.overwrite_cb = QCheckBox("Overwrite existing records")
        self.overwrite_cb.stateChanged.connect(self.toggle_import_button)
        self.overwrite_cb.setVisible(False)  # Hidden by default
        
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.import_data)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        # Layout changes
        controls_layout.addWidget(self.overlap_warning)
        controls_layout.addWidget(self.overwrite_cb)
        controls_layout.addStretch()
        controls_layout.addWidget(self.import_btn)
        controls_layout.addWidget(self.cancel_btn)
        layout.addLayout(controls_layout)

    # def toggle_import_button(self, state):
    #     """Enable import button based on overlap status"""
    #     if hasattr(self, 'metadata') and self.metadata.get('has_overlap', False):
    #         self.import_btn.setEnabled(state == Qt.Checked)
    #     else:
    #         self.import_btn.setEnabled(True)


    def toggle_import_button(self, state):
        """Enable import button only if overlap is acknowledged via checkbox"""
        if self.metadata and self.metadata.get('has_overlap', False):
            self.import_btn.setEnabled(state == Qt.Checked)
        else:
            self.import_btn.setEnabled(True)


    def validate_file(self):
        logger.info("Starting validate_file")
        try:
            # First validate the file using the handler
            valid, status, details = self.handler.validate_file(self.file_path, self.well_number)
            logger.debug(f"Initial validation result: {valid}, {status}")
            
            if status == "needs_registration":
                logger.info("Transducer needs registration - showing registration dialog")
                
                # First read the file to get transducer info
                df, metadata = self.handler.processor.solinst_reader.read_xle(self.file_path)
                
                transducer_data = {
                    'serial_number': metadata.serial_number,
                    'well_number': self.well_number,
                    'installation_date': pd.to_datetime(df['timestamp_utc'].min()).strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Create WellModel directly
                well_model = WellModel(self.water_level_model.db_path)
                dialog = TransducerDialog(well_model, transducer_data=transducer_data, parent=self)
                
                if (dialog.exec_() != QDialog.Accepted):
                    logger.info("Transducer registration cancelled by user")
                    self.reject()
                    return
                    
                logger.info("Transducer dialog accepted, handling potential confirmation")
                
                # Use transducer_handler to properly handle the registration/relocation
                from ..handlers.transducer_handler import TransducerHandler
                handler = TransducerHandler(self.water_level_model.db_path)
                
                # Process the registration with proper confirmation handling
                success, message, additional_data = handler.add_transducer(dialog.get_data())
                
                if success:
                    logger.info("Transducer registered successfully")
                    # Re-validate after successful registration
                    valid, status, details = self.handler.validate_file(self.file_path, self.well_number)
                elif message == "needs_confirmation":
                    # Show confirmation dialog for transducer relocation
                    from ..dialogs.transducer_location_dialog import TransducerLocationDialog
                    logger.info("Showing transducer relocation confirmation dialog")
                    
                    confirm_dialog = TransducerLocationDialog(
                        additional_data['current_location'],
                        additional_data['new_location'],
                        parent=self
                    )
                    
                    if confirm_dialog.exec_() == QDialog.Accepted:
                        # Update transducer location and re-validate
                        result = handler.update_transducer(dialog.get_data())
                        if isinstance(result, tuple) and len(result) >= 2 and result[0]:
                            logger.info("Transducer relocation confirmed")
                            valid, status, details = self.handler.validate_file(self.file_path, self.well_number)
                        else:
                            logger.error("Failed to update transducer location")
                            self.reject()
                            return
                    else:
                        logger.info("Transducer relocation cancelled")
                        self.reject()
                        return
                else:
                    logger.error(f"Transducer registration failed: {message}")
                    QMessageBox.critical(self, "Error", f"Failed to register transducer: {message}")
                    self.reject()
                    return
            
            elif status == "needs_relocation":
                # Show confirmation dialog for relocation
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"Transducer {details['serial_number']} is currently assigned to well {details['current_well']}.")
                msg.setInformativeText("Would you like to relocate this transducer to the new well?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                
                if msg.exec_() == QMessageBox.Yes:
                    try:
                        # Import the TransducerHandler to use our fixed implementation
                        from ..handlers.transducer_handler import TransducerHandler
                        
                        # Create data for the update
                        relocation_data = {
                            'serial_number': details['serial_number'],
                            'well_number': self.well_number,
                            'installation_date': pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S'),
                            'notes': f"Relocated during data import to well {self.well_number}"
                        }
                        
                        # Use our fixed TransducerHandler directly
                        handler = TransducerHandler(self.water_level_model.db_path)
                        success, message = handler.update_transducer(relocation_data)
                        relocation_details = None  # Adding a third return value to match expected unpacking
                        
                        if success:
                            valid, status, details = self.handler.validate_file(self.file_path, self.well_number)
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to relocate transducer: {message}")
                            self.reject()
                            return
                    except Exception as e:
                        logger.error(f"Error relocating transducer: {e}", exc_info=True)
                        QMessageBox.critical(self, "Error", f"Error relocating transducer: {str(e)}")
                        self.reject()
                        return
                else:
                    self.reject()
                    return
                
            elif status == "invalid_well":
                QMessageBox.critical(self, "Error", 
                    f"Well {self.well_number} does not exist in the database. Please register the well first.")
                self.reject()
                return

            if not valid and status != "needs_registration":
                logger.error(f"Validation failed: {status}")
                QMessageBox.critical(self, "Error", status)
                self.reject()
                return

            # Get data from validation
            df = details['preview_data']
            metadata = details['metadata']
            well_info = details['well_info']

            # Get time range for reference data
            time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
            
            # Get reference data
            manual_readings = self.handler.processor._get_manual_readings(self.well_number, time_range)
            existing_data = self.handler.processor._get_existing_data(self.well_number, time_range)
            baro_coverage = self.handler.processor._check_baro_coverage(time_range)

            # Store all metadata
            self.metadata = {
                'metadata': metadata,
                'preview_data': df,
                'well_info': well_info,
                'manual_readings': manual_readings,
                'existing_data': existing_data,
                'start_date': time_range[0],
                'end_date': time_range[1],
                'baro_coverage': baro_coverage
            }
            
            # Add safety check for manual_readings
            if 'manual_readings' not in self.metadata or self.metadata['manual_readings'] is None:
                logger.warning("Manual readings not found in metadata or is None")
                self.metadata['manual_readings'] = pd.DataFrame()  # Initialize empty DataFrame
            
            if not self.metadata['manual_readings'].empty:
                logger.debug("Manual readings found:")
                logger.debug(f"Columns: {self.metadata['manual_readings'].columns.tolist()}")
                logger.debug(f"Number of readings: {len(self.metadata['manual_readings'])}")
                logger.debug(f"Time range: {self.metadata['manual_readings']['measurement_date_utc'].min()} to {self.metadata['manual_readings']['measurement_date_utc'].max()}")
                logger.debug(f"Water level range: {self.metadata['manual_readings']['water_level'].min():.2f} to {self.metadata['manual_readings']['water_level'].max():.2f}")
            
            # Ensure all timestamps are in UTC
            logger.debug("Converting timestamps to UTC")
            logger.debug(f"Preview data timestamp before conversion (first row): {self.metadata['preview_data']['timestamp_utc'].iloc[0]}")
            
            # Convert all timestamps to naive UTC
            self.metadata['start_date'] = pd.to_datetime(self.metadata['start_date']).replace(tzinfo=None)
            self.metadata['end_date'] = pd.to_datetime(self.metadata['end_date']).replace(tzinfo=None)
            
            if not self.metadata['manual_readings'].empty:
                logger.debug("Converting manual readings timestamps to UTC")
                logger.debug(f"Manual readings timestamp before conversion (first row): {self.metadata['manual_readings']['measurement_date_utc'].iloc[0]}")
                self.metadata['manual_readings']['measurement_date_utc'] = pd.to_datetime(
                    self.metadata['manual_readings']['measurement_date_utc']
                ).dt.tz_localize(None)
                logger.debug(f"Manual readings timestamp after conversion (first row): {self.metadata['manual_readings']['measurement_date_utc'].iloc[0]}")
            
            logger.debug(f"Existing data empty? {self.metadata['existing_data'].empty}")
            logger.debug(f"Preview data empty? {self.metadata['preview_data'].empty}")

            if not self.metadata['existing_data'].empty:
                logger.debug("Processing existing data timestamps")
                self.metadata['existing_data']['timestamp_utc'] = pd.to_datetime(
                    self.metadata['existing_data']['timestamp_utc']
                ).dt.tz_localize(None)
                
                # Check if new data is completely within existing data range
                new_start = self.metadata['start_date']
                new_end = self.metadata['end_date']
                existing_start = self.metadata['existing_data']['timestamp_utc'].min()
                existing_end = self.metadata['existing_data']['timestamp_utc'].max()
                
                logger.debug(f"New data range: {new_start} to {new_end}")
                logger.debug(f"Existing data range: {existing_start} to {existing_end}")
                
                complete_overlap = (new_start >= existing_start) and (new_end <= existing_end)
                has_overlap = (
                    (new_start <= existing_end and new_end >= existing_start) or
                    (existing_start <= new_end and existing_end >= new_start)
                )
                
                logger.debug(f"Complete overlap: {complete_overlap}")
                logger.debug(f"Has overlap: {has_overlap}")
                
                self.metadata['has_overlap'] = has_overlap
                self.metadata['complete_overlap'] = complete_overlap

                # Update UI elements based on overlap status
                if complete_overlap:
                    logger.debug("Complete overlap detected - updating UI")
                    self.overlap_warning.setText("Warning: New data falls entirely within existing data range")
                    self.overlap_warning.setVisible(True)
                    self.overwrite_cb.setVisible(True)
                    self.overwrite_cb.setChecked(False)
                    self.import_btn.setEnabled(False)
                elif has_overlap:
                    logger.debug("Partial overlap detected - updating UI")
                    self.overlap_warning.setText("Warning: Overlapping data detected")
                    self.overlap_warning.setVisible(True)
                    self.overwrite_cb.setVisible(True)
                    self.overwrite_cb.setChecked(False)
                else:
                    logger.debug("No overlap detected")
                    self.overlap_warning.setVisible(False)
                    self.overwrite_cb.setVisible(False)
                    self.import_btn.setEnabled(True)
                
            logger.info("Updating UI with metadata")
            self.update_ui_with_metadata()
            self.update_preview_table()
            logger.info("Plotting data")
            self.plot_data()
            logger.info("Validation complete")
            
        except Exception as e:
            logger.error(f"Error in validate_file: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to validate file: {str(e)}")
            self.reject()
            
    def update_ui_with_metadata(self):
        t0 = time.time()
        logger.debug("Starting UI metadata update")

        # Well information
        well_info = (
            f"Well: {self.metadata['well_info']['well_number']} "
            f"(CAE: {self.metadata['well_info'].get('cae_number', 'N/A')})"
        )
        
        # Time range info including existing data range
        time_ranges = [f"Well Information: {well_info}"]
        
        time_ranges.append(
            f"New Data Range: {self.metadata['start_date'].strftime('%Y-%m-%d %H:%M')} to "
            f"{self.metadata['end_date'].strftime('%Y-%m-%d %H:%M')} (UTC)"
        )
        
        if not self.metadata['existing_data'].empty:
            existing_start = self.metadata['existing_data']['timestamp_utc'].min()
            existing_end = self.metadata['existing_data']['timestamp_utc'].max()
            time_ranges.append(
                f"Existing Data Range: {existing_start.strftime('%Y-%m-%d %H:%M')} to "
                f"{existing_end.strftime('%Y-%m-%d %H:%M')} (UTC)"
            )
        
        self.time_range_info.setText("\n".join(time_ranges))
        
        # Restore barometric info code
        baro_info = []
        if self.metadata['baro_coverage']['type'] == 'master':
            if self.metadata['baro_coverage']['complete']:
                baro_info.append("✓ Master barometric data available")
                baro_style = "color: green;"
            else:
                baro_info.append("⚠ Partial barometric data coverage")
                baro_style = "color: orange;"
        else:
            baro_info.append("⚠ Using standard atmospheric pressure")
            baro_style = "color: orange;"
            
        baro_info.append(self.metadata['baro_coverage']['message'])
        self.baro_info.setText("\n".join(baro_info))
        self.baro_info.setStyleSheet(baro_style)
        
        # Update insertion level info based on UTC timestamps
        t0 = time.time()
        has_recent = (not self.metadata['existing_data'].empty and 
                     self._check_data_gap() < 2)
        logger.debug(f"Checking data gap took: {time.time() - t0:.3f} seconds")
       
        has_manual = not self.metadata['manual_readings'].empty
        
        if has_manual:
            level_text = "Insertion level will be set from manual readings"
            level_style = "color: blue;"
        elif has_recent:
            level_text = "Insertion level will be predicted from existing data"
            level_style = "color: green;"
        else:
            level_text = f"Default insertion level will be used (TOC - 30ft)"
            level_style = "color: orange;"
        
        self.insertion_info.setText(level_text)
        self.insertion_info.setStyleSheet(level_style)
        
        # ...rest of existing code...

    def update_preview_table(self):
        try:
            if 'preview_data' in self.metadata:
                if 'processed_data' not in self.metadata:
                    # Use the handler's process_file method instead of direct processing
                    success, status, details = self.handler.process_file(self.file_path, self.well_number)
                    
                    if success:
                        preview_df = details['processed_data']
                        self.metadata['processed_data'] = preview_df
                        
                        # Populate the table
                        self.preview_table.clear()
                        self.preview_table.setRowCount(min(1000, len(preview_df)))  # Limit to 1000 rows for performance
                        self.preview_table.setColumnCount(len(preview_df.columns))
                        self.preview_table.setHorizontalHeaderLabels(preview_df.columns)
                        
                        # Populate table with data
                        for i, (_, row) in enumerate(preview_df.head(1000).iterrows()):
                            for j, value in enumerate(row):
                                item = QTableWidgetItem(str(value))
                                self.preview_table.setItem(i, j, item)
                        
                        # Adjust column widths
                        self.preview_table.resizeColumnsToContents()
                    else:
                        logger.error(f"Failed to process file: {status}")
                        
        except Exception as e:
            logger.error(f"Error updating preview table: {e}", exc_info=True)
        
    def _determine_insertion_level(self, df: pd.DataFrame) -> Dict:
        """Determine insertion level for preview data"""
        try:
            logger.debug(f"_determine_insertion_level: Starting with data shape: {df.shape}")
            
            # Add water_pressure to df before calling determine_insertion_level
            df = df.copy()
            baro_coverage = self.metadata['baro_coverage']
            if baro_coverage['type'] == 'master' and baro_coverage['complete']:
                baro_times = baro_coverage['data']['timestamp_utc'].values.astype('datetime64[ns]')
                baro_pressures = baro_coverage['data']['pressure'].values
                df['water_pressure'] = df['pressure'] - np.interp(
                    df['timestamp_utc'].values.astype('datetime64[ns]').astype(float),
                    baro_times.astype(float),
                    baro_pressures
                )
            else:
                df['water_pressure'] = df['pressure'] - self.handler.processor.STANDARD_ATMOS_PRESSURE
            
            logger.debug(f"_determine_insertion_level: Calling processor.determine_insertion_level") # Log the call
            result = self.handler.processor.determine_insertion_level(
                df,
                self.metadata['well_info'],
                self.metadata['manual_readings'],
                self.metadata['existing_data'],
                is_folder_import=False  # This is single file import
            )
            
            logger.debug(f"_determine_insertion_level: processor.determine_insertion_level returned: {result}") # Log the result
            return result
                
        except Exception as e:
            logger.error(f"Error determining insertion level: {e}")
            return None
    
    def plot_data(self):
        """Plot water level data with naive UTC timestamps"""
        try:
            logger.info("Starting plot_data")
            # Get full history for context
            full_history = self.water_level_model.get_readings(self.metadata['well_info']['well_number'])
            logger.debug(f"Full history empty? {full_history.empty}")
            
            if not full_history.empty:
                full_history['timestamp_utc'] = pd.to_datetime(full_history['timestamp_utc'])
                logger.debug(f"Full history range: {full_history['timestamp_utc'].min()} to {full_history['timestamp_utc'].max()}")
                
            df = self.metadata['processed_data']  # Use pre-calculated data
            existing_data = self.metadata['existing_data']
            manual_readings = self.metadata['manual_readings']
            logger.debug(f"Preview data empty? {df.empty}")
            logger.debug(f"Existing data empty? {existing_data.empty}")
            logger.debug(f"Manual readings empty? {manual_readings.empty}")
            
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.grid(True, which='both', linestyle='--', alpha=0.6)
    
            if not df.empty:
                # First plot the overlap region if it exists
                if not existing_data.empty:
                    mask = (existing_data['timestamp_utc'] >= df['timestamp_utc'].min()) & \
                           (existing_data['timestamp_utc'] <= df['timestamp_utc'].max())
                    logger.debug(f"Overlap mask has True values? {mask.any()}")
                    if mask.any():
                        overlap_data = existing_data[mask]
                        logger.debug(f"Overlap data range: {overlap_data['timestamp_utc'].min()} to {overlap_data['timestamp_utc'].max()}")
                        ax.axvspan(overlap_data['timestamp_utc'].min(),
                                  overlap_data['timestamp_utc'].max(),
                                  color='yellow', alpha=0.3,
                                  label='Overlap',
                                  zorder=1)
                
                # Then plot full history
                if not full_history.empty:
                    ax.plot(full_history['timestamp_utc'], 
                            full_history['water_level'],
                            'gray', label='Existing', 
                            alpha=0.3, linewidth=0.5, zorder=2)

                # Plot manual readings within ±1 hour of imported data timeframe
                if not manual_readings.empty:
                    # Define the time range: ±1 hour from the imported data
                    min_time = df['timestamp_utc'].min() - timedelta(hours=1)
                    max_time = df['timestamp_utc'].max() + timedelta(hours=1)  # Fixed: missing closing parenthesis
                    
                    # Filter manual readings within this range
                    mask = (manual_readings['measurement_date_utc'] >= min_time) & \
                           (manual_readings['measurement_date_utc'] <= max_time)
                    
                    if mask.any():
                        filtered_manual = manual_readings[mask]
                        ax.scatter(filtered_manual['measurement_date_utc'], 
                                  filtered_manual['water_level'],
                                  marker='o', color='red', s=50, label='Manual Reading', 
                                  zorder=4)
                        logger.debug(f"Plotting {len(filtered_manual)} manual readings")
    
                # Plot new water levels using pre-calculated data
                if 'level_flag' in df.columns:
                    label = 'New Data'  # Simplified label without the level_flag
                else:
                    label = 'New Data'
                    
                ax.plot(df['timestamp_utc'], df['water_level'], 'b-', 
                        label=label, linewidth=1.5, zorder=3)
    
                ax.set_ylabel('Water Level (ft)')
                ax.legend(loc='upper right')
                ax.grid(True, linestyle='--', alpha=0.6)
                ax.tick_params(axis='x', rotation=45)
                ax.margins(x=0.01)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                
                self.figure.tight_layout(rect=[0.05, 0.05, 0.95, 0.95])
                self.canvas.draw()
    
        except Exception as e:
            logger.error(f"Error plotting data: {e}", exc_info=True)
            # Show error in plot area
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Error loading plot:\n{str(e)}", 
                   ha='center', va='center', 
                   transform=ax.transAxes,
                   color='red', fontsize=10)
            self.canvas.draw()
            
    def _check_data_gap(self) -> float:
        """Calculate minimum gap with existing data in hours"""
        try:
            logger.debug("Starting data gap check")
            
            if self.metadata['existing_data'].empty:
                logger.debug("No existing data found - returning infinite gap")
                return float('inf')
                
            start_time = time.time()
            
            # Get time range from new data
            new_data_min = self.metadata['preview_data']['timestamp_utc'].min()
            new_data_max = self.metadata['preview_data']['timestamp_utc'].max()
            
            # Connect to database
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                # First find closest readings before and after our data range
                query = """
                    WITH TimeGaps AS (
                        SELECT 
                            timestamp_utc,
                            ABS(JULIANDAY(timestamp_utc) - JULIANDAY(?)) * 24 as hours_diff
                        FROM water_level_readings 
                        WHERE well_number = ?
                        AND timestamp_utc BETWEEN DATETIME(?, '-2 hours') AND DATETIME(?, '+2 hours')
                    )
                    SELECT MIN(hours_diff) as min_gap
                    FROM TimeGaps;
                """
                
                cursor = conn.cursor()
                # Check gap at start of data
                cursor.execute(query, (
                    new_data_min.strftime('%Y-%m-%d %H:%M:%S'),
                    self.metadata['well_info']['well_number'],
                    new_data_min.strftime('%Y-%m-%d %H:%M:%S'),
                    new_data_max.strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                min_gap = cursor.fetchone()[0]
                if min_gap is None:
                    min_gap = float('inf')
                    
            logger.debug(f"Data gap check completed in {time.time() - start_time:.3f} seconds")
            return float(min_gap)
    
        except Exception as e:
            logger.error(f"Error checking data gap: {e}")
            return float('inf')
        
    def import_data(self):
        """Handle data import with transducer registration and well selection in the UI."""
        try:
            logger.info("Starting data import")
            
            # Use pre-calculated data
            df = self.metadata['processed_data']
            logger.debug(f"import_data: Using pre-calculated data with {len(df)} rows")
    
            # Check if transducer exists and register if missing
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM transducers WHERE serial_number = ?
                """, (self.metadata['metadata'].serial_number,))
                
                if cursor.fetchone()[0] == 0:
                    logger.info(f"Registering new transducer {self.metadata['metadata'].serial_number}")
                    
                    # Use TransducerHandler instead of direct SQL to properly update both tables
                    from ..handlers.transducer_handler import TransducerHandler
                    handler = TransducerHandler(self.water_level_model.db_path)
                    
                    transducer_data = {
                        'serial_number': self.metadata['metadata'].serial_number, 
                        'well_number': self.well_number,
                        'installation_date': df['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M:%S'),
                        'notes': f"Auto-registered during data import"
                    }
                    
                    success, message, _ = handler.add_transducer(transducer_data)
                    if not success:
                        logger.warning(f"Issue registering transducer: {message}")
    
            success = self.water_level_model.import_readings(
                self.well_number,
                df,
                self.overwrite_cb.isChecked()
            )
    
            if success:
                # Log the imported file in the transducer_imported_files table
                try:
                    logger.info("Logging imported file to transducer_imported_files table")
                    well_number = self.well_number
                    serial_number = self.metadata['metadata'].serial_number
                    start_date = pd.to_datetime(df['timestamp_utc'].min())
                    end_date = pd.to_datetime(df['timestamp_utc'].max())
                    
                    with sqlite3.connect(self.water_level_model.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO transducer_imported_files
                            (well_number, serial_number, starting_date, end_date)
                            VALUES (?, ?, ?, ?)
                        ''', (well_number, serial_number, start_date, end_date))
                        conn.commit()
                        logger.info(f"Logged imported file for well {well_number}, serial {serial_number}")
                except Exception as e:
                    logger.error(f"Error logging imported file: {e}")
                    # Continue even if logging fails
                
                QMessageBox.information(self, "Success", "Data imported successfully")
                self.accept()
    
                # After import, select the well in the table and update the UI
                if self.parent():  # Ensure parent exists
                    if hasattr(self.parent(), "select_well_in_table"):
                        self.parent().select_well_in_table(self.well_number)
                    if hasattr(self.parent(), "refresh_transducers_table"):
                        self.parent().refresh_transducers_table()
            else:
                QMessageBox.critical(self, "Error", "Failed to import data")
    
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")

    def preview_data(self, well_number: str):
        """Preview data for selected well in the plot area"""
        try:
            # Show loading state in the plot area
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Loading plot...", 
                   ha='center', va='center', 
                   transform=ax.transAxes,
                   fontsize=12)
            self.canvas.draw()
            QApplication.processEvents()  # Update UI to show loading text
            
            # Clear for actual plot
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            well_data = self.data[well_number]
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

            if well_data.get('has_been_processed'):
                # After processing - show water levels
                # Get existing data first for context
                existing_data = self.water_level_model.get_readings(well_number)
                if not existing_data.empty:
                    existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])
                    # Downsample existing data for preview
                    if len(existing_data) > 1000:
                        existing_data = existing_data.iloc[::len(existing_data)//1000]
                    
                    # Replace data_source filtering with a single plot
                    ax.plot(existing_data['timestamp_utc'], 
                          existing_data['water_level'],
                          color='gray', alpha=0.3, linewidth=0.5, 
                          label='Existing Data',
                          zorder=1)

                # Plot processed segments
                df = well_data['processed_data']
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                
                # Downsample data for preview if too many points
                if len(df) > 1000:
                    df = df.iloc[::len(df)//1000]
                
                # Plot by level method
                ax.plot(df['timestamp_utc'], df['water_level'], 
                       color='blue', label=f'New ({df["level_flag"].iloc[0]})', 
                       linewidth=1.5, zorder=2)

                ax.set_ylabel('Water Level (ft)')
                title = f"Well {well_number} - Processed Water Levels"
                if well_data.get('has_overlap'):
                    title += " (Has Overlaps)"
                ax.set_title(title)
            else:
                # Before processing - show raw pressure with simplified labels
                for idx, file_path in enumerate(well_data['files']):
                    df, metadata = self.processor.solinst_reader.read_xle(file_path)
                    color = colors[idx % len(colors)]
                    
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    # Downsample data for preview if too many points
                    if len(df) > 1000:
                        df = df.iloc[::len(df)//1000]
                    # Simplified label for preview
                    label = f"File {idx+1}"
                    ax.plot(df['timestamp_utc'], df['pressure'], 
                           color=color, label=label, linewidth=1.5)

                ax.set_ylabel('Pressure (PSI)')
                ax.set_title(f"Well {well_number} - Raw Pressure Data")

            # Show overlap regions in both cases
            if well_data.get('has_overlap'):
                overlap_start, overlap_end = well_data['overlap_range']
                ax.axvspan(overlap_start, overlap_end,
                         color='yellow', alpha=0.2,
                         label='Overlap Region')

            # Common formatting
            ax.set_xlabel('Time (UTC)')
            ax.grid(True, which='major', linestyle='--', alpha=0.6)
            ax.grid(True, which='minor', linestyle=':', alpha=0.3)
            
            # Format x-axis to show dates nicely
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # Rotate and align the tick labels so they look better
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Add legend
            ax.legend(loc='best', fontsize=8)
            
            # Add note about downsampling if applied
            if well_data.get('has_been_processed'):
                if len(well_data['processed_data']) > 1000:
                    ax.text(0.02, 0.98, "Note: Plot shows downsampled data for preview",
                           transform=ax.transAxes, fontsize=8, alpha=0.7,
                           verticalalignment='top')
            
            # Adjust layout to prevent label cutoff
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error plotting preview data: {e}")
            # Show error in plot area
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Error loading plot:\n{str(e)}", 
                   ha='center', va='center', 
                   transform=ax.transAxes,
                   color='red', fontsize=10)
            self.canvas.draw()