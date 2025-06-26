# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 10:14:18 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                           QPushButton, QLabel, QGroupBox, QTableWidget,
                           QTableWidgetItem, QMessageBox, QComboBox, QDialog, QFileDialog, QApplication, QDateTimeEdit, QDoubleSpinBox, QLineEdit, QTextEdit, QDialogButtonBox, QCheckBox, QHeaderView, QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QDateTime, QSize, QPoint
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import pandas as pd
import logging
from pathlib import Path
import io  # Add this missing import for StringIO
import requests  # Make sure requests is imported for telemetry data fetching
from ..dialogs.water_level_import_dialog import WaterLevelImportDialog
#from ...database.models.water_level import WaterLevelModel
#from ..dialogs.transducer_dialog import TransducerDialoglImportDialog
from ...database.models.water_level import WaterLevelModel
from ..dialogs.transducer_dialog import TransducerDialog
from ..handlers.solinst_reader import SolinstReader
import sqlite3
from ..handlers.fetch_monet import fetch_monet_data
from ..dialogs.manual_reading_dialog import AddManualReadingDialog
from ..dialogs.manual_readings_preview_dialog import ManualReadingsPreviewDialog
from ..handlers.water_level_plot_handler import WaterLevelPlotHandler
from ..handlers.well_data_handler import WellDataHandler
from ..handlers.transducer_handler import TransducerHandler
from ..handlers.manual_readings_handler import ManualReadingsHandler
from ..handlers.progress_dialog_handler import progress_dialog  # Import the standardized progress dialog handler

logger = logging.getLogger(__name__)
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.backend_bases import MouseButton
from matplotlib.widgets import Cursor
import matplotlib.dates as mdates
import time
from typing import Dict, Optional, List
import matplotlib.pyplot as plt
from ..handlers.csv_handler import ManualReadingsCSVHandler
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QStyleOptionViewItem
from datetime import datetime, timedelta

class CenteredIconTable(QTableWidget):
    """Custom table widget that centers icons in cells"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.current_tooltip_item = None
        
    def viewOptions(self) -> QStyleOptionViewItem:
        option = super().viewOptions()
        option.decorationAlignment = Qt.AlignHCenter | Qt.AlignVCenter
        option.decorationPosition = QStyleOptionViewItem.Top
        option.displayAlignment = Qt.AlignCenter
        return option

    def mouseMoveEvent(self, event):
        try:
            item = self.itemAt(event.pos())
            if item and item.column() < 2:  # Only for flag columns
                if item != self.current_tooltip_item:
                    self.current_tooltip_item = item
                    flag_type = "Baro" if item.column() == 0 else "Level"
                    flag_value = item.data(Qt.UserRole)
                    
                    # More descriptive tooltips based on flag type
                    if flag_type == "Baro":
                        description = "Master" if flag_value == "master" else "Standard"
                        tooltip = f"""
                        <div style='background-color: white; padding: 5px;'>
                            <b>Barometric Flag</b><br>
                            <span style='color: #666;'>Type: {description}</span><br>
                            <span style='color: #666;'>Used for: Atmospheric pressure compensation</span>
                        </div>
                        """
                    else:  # Level flag
                        if flag_value in ("manual_reading", "predicted"):
                            description = "Manual/Predicted Reading"
                        elif flag_value == "default_level":
                            description = "Default Level"
                        else:
                            description = "Standard Reading"
                            
                        tooltip = f"""
                        <div style='background-color: white; padding: 5px;'>
                            <b>Water Level Flag</b><br>
                            <span style='color: #666;'>Type: {description}</span><br>
                            <span style='color: #666;'>Source: {flag_value}</span>
                        </div>
                        """
                    
                    self.setToolTip(tooltip)
            else:
                self.current_tooltip_item = None
                self.setToolTip("")
            super().mouseMoveEvent(event)
        except Exception as e:
            logger.error(f"Error in mouseMoveEvent: {e}")

class WaterLevelTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        # Initialize core attributes first
        self.db_manager = db_manager
        self.current_dir = Path(__file__).parent.parent.parent.parent
        self.water_level_model = None
        self.show_temperature = False
        
        # Initialize handlers
        self.well_handler = WellDataHandler(self.db_manager.current_db if self.db_manager else None)
        self.transducer_handler = TransducerHandler(self.db_manager.current_db if self.db_manager else None)
        self.transducer_handler.parent = self  # Set the parent reference
        self.manual_readings_handler = ManualReadingsHandler(self.db_manager.current_db if self.db_manager else None)
        
        # Initialize plot components
        self.figure = Figure(figsize=(10, 6))  # Increased from (8, 4)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.plot_handler = WaterLevelPlotHandler(self.figure, self.canvas)
        
        # Initialize tables
        self.wells_table = CenteredIconTable()
        self.wells_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.wells_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.wells_table.itemSelectionChanged.connect(self.on_well_selection_changed)
        
        self.transducers_table = QTableWidget()
        self.transducers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transducers_table.setSelectionMode(QTableWidget.SingleSelection)

        # Connect signals after initializing attributes
        self.db_manager.database_changed.connect(self.sync_database_selection)
        
        # Setup UI and tables
        self.setup_wells_table()
        self.setup_transducers_table()
        self.setup_ui()

        # Load initial data if database is already open
        if db_manager and hasattr(db_manager, 'current_db'):
            self.load_initial_data()

    def load_initial_data(self):
        """Load initial data after UI setup"""
        if self.db_manager.current_db:
            self.water_level_model = WaterLevelModel(self.db_manager.current_db)
            self.refresh_wells_table()
            self.refresh_transducers_table()
    
    def sync_database_selection(self, db_name: str):
        """Handle database selection changes."""
        logger.debug(f"Syncing database selection to {db_name}")
        if (db_name and db_name != "No databases found"):
            start_sync_time = time.time() # Start timing
            db_path = self.db_manager.current_db
            logger.debug(f"Using database path: {db_path}")

            # Update handlers with new database path
            handler_start_time = time.time() # Timing handlers
            self.well_handler.update_db_path(db_path)
            self.transducer_handler.update_db_path(db_path)
            self.manual_readings_handler.update_db_path(db_path)
            logger.debug(f"Updated handlers in {time.time() - handler_start_time:.4f} seconds") # Log handler time

            # Create new water level model with current database
            # No need to recalculate flags as this will use the cached values in the wells table
            model_start_time = time.time() # Timing model creation
            self.water_level_model = WaterLevelModel(db_path)
            logger.debug(f"Initialized WaterLevelModel in {time.time() - model_start_time:.4f} seconds") # Log model time

            # Refresh tables
            wells_refresh_start_time = time.time() # Timing wells refresh
            self.refresh_wells_table()
            logger.debug(f"Refreshed wells table in {time.time() - wells_refresh_start_time:.4f} seconds") # Log wells refresh time

            transducers_refresh_start_time = time.time() # Timing transducers refresh
            self.refresh_transducers_table()
            logger.debug(f"Refreshed transducers table in {time.time() - transducers_refresh_start_time:.4f} seconds") # Log transducers refresh time

            logger.debug(f"Finished sync_database_selection for {db_name} in {time.time() - start_sync_time:.4f} seconds") # Log total sync time
    
    def refresh_data(self):
        """Refresh all water level data."""
        logger.debug("Refreshing water level data")
        try:
            # Refresh wells table
            self.refresh_wells_table()
            
            # Refresh transducers table
            self.refresh_transducers_table()
            
            # Update the plot if wells are selected
            if self.wells_table.selectedItems():
                self.update_plot()
                
            return True
        except Exception as e:
            logger.error(f"Error refreshing water level data: {e}")
            return False

    def on_database_changed(self, db_name):
        """Handle database changes by resetting state and refreshing data"""
        if not db_name or db_name == "No databases found":
            return
            
        try:
            # Clear caches and reset state
            self.show_temperature = False
            
            # Clear existing plot
            self.figure.clear()
            self.canvas.draw()
            
            # Reset model and use the existing database connection
            # Database is already opened by MainWindow
            self.water_level_model = None
            self.water_level_model = WaterLevelModel(self.db_manager.current_db)
            
            # Update handlers
            self.well_handler.update_db_path(self.db_manager.current_db)
            self.transducer_handler.update_db_path(self.db_manager.current_db)
            self.manual_readings_handler.update_db_path(self.db_manager.current_db)
            
            # Clear existing data
            self.wells_table.clearContents()
            self.wells_table.setRowCount(0)
            self.transducers_table.clearContents()
            self.transducers_table.setRowCount(0)
            
            # Refresh data
            self.refresh_wells_table()
            self.refresh_transducers_table()
            
            # Clear selection
            self.wells_table.clearSelection()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {str(e)}")
    
    def setup_ui(self):
        """Setup the main UI layout"""
        main_layout = QGridLayout(self)
        main_layout.setSpacing(5)  # Reduced from 10
        
        # Add sections
        main_layout.addWidget(self.create_well_list_section(), 0, 0)
        
        # Create right side layout
        right_side = QVBoxLayout()
        right_side.setSpacing(2)  # Reduced spacing
        
        # Add plot section at top with more vertical space
        plot_section = QVBoxLayout()
        plot_section.setSpacing(2)  # Reduced spacing
        
        # Add control buttons in horizontal layout
        plot_controls = QHBoxLayout()
        plot_controls.setSpacing(8)  # Better spacing
        
        self.edit_data_btn = QPushButton("Edit Data")
        self.edit_data_btn.setFixedHeight(32)  # Reduced from 40
        self.edit_data_btn.clicked.connect(self.open_edit_dialog)
        self.edit_data_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-weight: 500;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
                border-color: #8d9499;
            }
        """)
        plot_controls.addWidget(self.edit_data_btn)
        
        self.refresh_btn = QPushButton("Refresh Tab")
        self.refresh_btn.setFixedHeight(32)  # Reduced from 40
        self.refresh_btn.clicked.connect(self.refresh_all_data)
        self.refresh_btn.setIcon(QIcon(str(Path(__file__).parent.parent / "icons" / "refresh.png")))
        self.refresh_btn.setToolTip("Refresh all data in this tab")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-weight: 500;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
                border-color: #8d9499;
            }
        """)
        plot_controls.addWidget(self.refresh_btn)
        
        plot_controls.addStretch()
        
        # Add gap highlighting checkbox
        self.show_gaps_cb = QCheckBox("Show Data Gaps")
        self.show_gaps_cb.setChecked(True)  # Enabled by default
        self.show_gaps_cb.setToolTip("Show colored background for data gaps")
        self.show_gaps_cb.stateChanged.connect(self.toggle_gap_highlighting)
        plot_controls.addWidget(self.show_gaps_cb)
        
        self.show_temp_btn = QPushButton("Show Temperature")
        self.show_temp_btn.setFixedHeight(32)  # Added fixed height
        self.show_temp_btn.setCheckable(True)
        self.show_temp_btn.clicked.connect(self.toggle_plot_type)
        self.show_temp_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-weight: 500;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:checked {
                background-color: #28a745;
                border-color: #1e7e34;
                color: white;
            }
            QPushButton:checked:hover {
                background-color: #218838;
                border-color: #1c7430;
            }
        """)
        plot_controls.addWidget(self.show_temp_btn)
        plot_section.addLayout(plot_controls)
        
        # Plot container with maximized plot space
        plot_container = QWidget()
        plot_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        
        # Add toolbar and canvas
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setStyleSheet("""
            QToolBar { 
                spacing: 2px; 
                padding: 2px;
                margin: 0px;
            }
            QToolButton { 
                max-width: 24px; 
                max-height: 24px;
                min-width: 24px;
                min-height: 24px;
            }
        """)
        self.toolbar.setFixedHeight(28)  # Reduced from 32
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        plot_section.addWidget(plot_container)
        right_side.addLayout(plot_section, stretch=5)  # Increased stretch from 4 to 5 for taller plot

        # Bottom grid layout with reduced spacing
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(2)  # Reduced spacing further
        bottom_grid.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        
        # Add panels with reduced spacing
        telemetry_group = self.create_compact_telemetry_panel()
        transducer_group = self.create_compact_transducer_panel()
        manual_group = self.create_compact_manual_panel()
        
        # Create app logo with reduced size
        self.logo_area = self.create_logo_area()
        
        # Add components to bottom grid
        bottom_grid.addWidget(telemetry_group, 0, 0)
        bottom_grid.addWidget(transducer_group, 1, 0)
        bottom_grid.addWidget(manual_group, 2, 0)
        bottom_grid.addWidget(self.logo_area, 0, 1, 3, 1)  # Span all rows
        
        # Adjust column stretches
        bottom_grid.setColumnStretch(0, 6)  # Increased to push logo more to the right
        bottom_grid.setColumnStretch(1, 1)
        
        right_side.addLayout(bottom_grid, stretch=1)

        # Create widget to hold right side layout
        right_widget = QWidget()
        right_widget.setLayout(right_side)
        main_layout.addWidget(right_widget, 0, 1)
        
        # Set stretch factors
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 2)

    def update_telemetry_data(self):
        """Fetch and update telemetry data from URLs"""
        try:
            # Check if database is selected
            if not self.db_manager.current_db:
                QMessageBox.warning(self, "Warning", "Please select a database first")
                return
            
            # Show progress dialog using the handler
            progress_dialog.show("Fetching telemetry data...", "Updating Telemetry")
            progress_dialog.update(10)
            
            # Get wells with telemetry data source
            progress_dialog.update(20, "Finding wells with telemetry data...")
            telemetry_wells = self._get_telemetry_wells()
            
            if not telemetry_wells:
                progress_dialog.close()
                QMessageBox.information(self, "No Telemetry Wells", 
                                      "No wells with telemetry data source and URL found.")
                return
            
            progress_dialog.update(30, f"Found {len(telemetry_wells)} telemetry wells")
            
            # Initialize counters
            total_readings = 0
            wells_updated = {}
            errors = []
            
            # Process each well
            step_size = 60 / len(telemetry_wells)
            current_progress = 30
            
            for i, well in enumerate(telemetry_wells):
                try:
                    progress_dialog.update(int(current_progress), 
                                          f"Processing well {well['well_number']} ({i+1}/{len(telemetry_wells)})...")
                    
                    # Download and process data
                    readings_count = self._process_telemetry_well(well)
                    
                    if readings_count > 0:
                        wells_updated[well['well_number']] = readings_count
                        total_readings += readings_count
                    
                    current_progress += step_size
                    
                except Exception as e:
                    error_msg = f"Error processing well {well['well_number']}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            progress_dialog.update(95, "Finalizing...")
            
            # Create result message
            result_message = []
            
            if wells_updated:
                result_message.append("Successfully updated telemetry data:")
                for well_number, count in wells_updated.items():
                    result_message.append(f"- {well_number}: {count} new readings")
                result_message.append(f"\nTotal new readings: {total_readings}")
            else:
                result_message.append("No new telemetry readings found.")
            
            if errors:
                result_message.append("\nErrors encountered:")
                for error in errors[:5]:  # Limit to first 5 errors
                    result_message.append(f"- {error}")
                if len(errors) > 5:
                    result_message.append(f"... and {len(errors) - 5} more errors.")
            
            progress_dialog.close()
            
            # Show results
            QMessageBox.information(self, "Telemetry Update Complete", "\n".join(result_message))
            
            # Update plot if we have new data
            if total_readings > 0:
                self.update_plot()
            
        except Exception as e:
            logger.error(f"Error updating telemetry data: {e}")
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to update telemetry data: {str(e)}")
    
    def _get_telemetry_wells(self):
        """Get wells with telemetry data source and URL"""
        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT well_number, url, top_of_casing 
                    FROM wells 
                    WHERE data_source = 'telemetry' AND url IS NOT NULL AND url != ''
                ''')
                
                wells = []
                for row in cursor.fetchall():
                    wells.append({
                        'well_number': row[0],
                        'url': row[1],
                        'top_of_casing': row[2]
                    })
                
                return wells
                
        except Exception as e:
            logger.error(f"Error getting telemetry wells: {e}")
            raise
    
    def _process_telemetry_well(self, well):
        """Process telemetry data for a single well"""
        import requests
        import pandas as pd
        import io
        
        try:
            # Validate URL
            url = well['url'].strip()
            if not url or not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: '{url}'. URL must start with http:// or https://")
                
            # Get latest reading timestamp
            latest_timestamp = self._get_latest_telemetry_timestamp(well['well_number'])
            
            logger.debug(f"Downloading data from {url}")
                # Fix: Check if the URL contains 'results_id=' and replace with 'result_ids='andling
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()  # Raise exception for HTTP errors
            except requests.exceptions.RequestException as req_err:
                logger.error(f"HTTP request error for well {well['well_number']}: {req_err}")
                raise ValueError(f"Failed to download data: {str(req_err)}")
                
            content = response.text
            
            # Process the CSV with metadata headers
            df = self._parse_csv_with_metadata(content)
            
            if df.empty:
                logger.debug(f"No data found in CSV for well {well['well_number']}")
                return 0
                
            # Map columns to our expected format
            df = self._map_csv_columns(df)
            
            # Convert timestamp to datetime
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
            
            # Remove rows with invalid timestamps
            df = df.dropna(subset=['timestamp_utc'])
            
            # Filter to only get new readings
            if latest_timestamp:
                latest_dt = pd.to_datetime(latest_timestamp)
                df = df[df['timestamp_utc'] > latest_dt]
            
            if df.empty:
                logger.debug(f"No new telemetry readings for well {well['well_number']}")
                return 0
            
            # Convert DTW from mm to ft (1mm = 0.00328084ft)
            df['dtw'] = df['dtw_mm'] * 0.00328084
            
            # Calculate water level (TOC - DTW)
            df['water_level'] = float(well['top_of_casing']) - df['dtw']
            
            # Insert into database
            readings_added = self._insert_telemetry_readings(well['well_number'], df)
            logger.info(f"Added {readings_added} telemetry readings for well {well['well_number']}")
            return readings_added
            
        except ValueError as ve:
            # Re-raise ValueErrors as they're already formatted properly
            raise ve
        except Exception as e:
            logger.error(f"Error processing telemetry for well {well['well_number']}: {e}")
            raise ValueError(f"Error processing data: {str(e)}")

    def _parse_csv_with_metadata(self, content: str) -> pd.DataFrame:
        """Parse CSV with metadata headers"""
        try:
            # Split content by lines
            lines = content.strip().split('\n')
            
            # Find the actual CSV header line (starts with "DateTimeUTC" or similar)
            header_index = -1
            for i, line in enumerate(lines):
                if ('DateTimeUTC' in line or 'DateTime' in line or 
                    'Date' in line or 'Timestamp' in line):
                    header_index = i
                    break
            
            if header_index == -1:
                logger.warning("Could not find header row in CSV")
                return pd.DataFrame()  # Return empty DataFrame
                
            # Extract the actual CSV data (header + data rows)
            csv_data = '\n'.join(lines[header_index:])
            
            # Read into DataFrame
            df = pd.read_csv(io.StringIO(csv_data), sep='\t' if '\t' in lines[header_index] else ',')
            
            return df
        except Exception as e:
            logger.error(f"Error parsing CSV with metadata: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def _map_csv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map CSV columns to our expected format"""
        # Make a copy to avoid modifying the original
        result_df = df.copy()
        
        # Identify timestamp column - look for DateTimeUTC, DateTime, Date, or Timestamp
        timestamp_col = None
        for col in df.columns:
            if any(time_str in col.lower() for time_str in ['datetime', 'date', 'timestamp']):
                timestamp_col = col
                break
        
        if timestamp_col is None:
            logger.error("No timestamp column found in CSV")
            return pd.DataFrame()  # Return empty DataFrame
            
        # Rename timestamp column
        result_df.rename(columns={timestamp_col: 'timestamp_utc'}, inplace=True)
        
        # Identify depth/level column - look for Depth, Level, DTW, Water_Depth
        depth_col = None
        for col in df.columns:
            if any(depth_str in col.lower() for depth_str in ['depth', 'level', 'dtw', 'meter_hydros21_depth']):
                depth_col = col
                break
                
        if depth_col is None:
            logger.error("No depth/level column found in CSV")
            return pd.DataFrame()  # Return empty DataFrame
            
        # Rename depth column
        result_df.rename(columns={depth_col: 'dtw_mm'}, inplace=True)
        
        # Identify temperature column - look for Temp, Temperature
        temp_col = None
        for col in df.columns:
            if any(temp_str in col.lower() for temp_str in ['temp', 'temperature', 'meter_hydros21_temp']):
                temp_col = col
                break
                
        if temp_col is None:
            # Temperature is optional, create a default column
            logger.warning("No temperature column found in CSV, using default value")
            result_df['temperature_c'] = None
        else:
            # Rename temperature column
            result_df.rename(columns={temp_col: 'temperature_c'}, inplace=True)
            
        # Select only the columns we need
        needed_columns = ['timestamp_utc', 'dtw_mm', 'temperature_c']
        available_columns = [col for col in needed_columns if col in result_df.columns]
        result_df = result_df[available_columns]
        
        # Handle missing columns
        for col in needed_columns:
            if col not in result_df.columns:
                result_df[col] = None
        
        return result_df

    def _get_latest_telemetry_timestamp(self, well_number):
        """Get the latest telemetry reading timestamp for a well"""
        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT MAX(timestamp_utc) 
                    FROM telemetry_level_readings 
                    WHERE well_number = ?
                ''', (well_number,))
                
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
                
        except Exception as e:
            logger.error(f"Error getting latest telemetry timestamp: {e}")
            raise
    
    def _insert_telemetry_readings(self, well_number, df):
        """Insert telemetry readings into database"""
        try:
            readings_count = 0
            
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    try:
                        # Calculate Julian timestamp
                        timestamp = row['timestamp_utc']
                        julian_timestamp = timestamp.to_julian_date()
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO telemetry_level_readings 
                            (well_number, timestamp_utc, julian_timestamp, water_level, temperature, dtw)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            well_number,
                            timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            julian_timestamp,
                            float(row['water_level']),
                            float(row['temperature_c']),
                            float(row['dtw'])
                        ))
                        
                        if cursor.rowcount > 0:
                            readings_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error inserting telemetry row: {e}")
                
                # Mark database as modified if we added readings
                if readings_count > 0:
                    self.db_manager.mark_as_modified()
                
                conn.commit()
                return readings_count
                
        except Exception as e:
            logger.error(f"Error inserting telemetry readings: {e}")
            raise
    
    def create_well_list_section(self) -> QGroupBox:
        """Create well management section with wells and transducers."""
        group = QGroupBox("Well Management")
        layout = QVBoxLayout()
        layout.setSpacing(2)  # Reduce spacing between sections
        
        # Well Management Buttons
        btn_layout = QHBoxLayout()
    
        add_well_btn = QPushButton("Add Well")
        add_well_btn.clicked.connect(self.add_well)
    
        self.edit_well_btn = QPushButton("Edit Well")  # Make it instance variable
        self.edit_well_btn.clicked.connect(self.edit_well)
        self.edit_well_btn.setEnabled(False)  # Initially disabled
        
        self.delete_well_btn = QPushButton("Delete Well")  # Add delete button
        self.delete_well_btn.clicked.connect(self.delete_well)
        self.delete_well_btn.setEnabled(False)  # Initially disabled
    
        import_well_btn = QPushButton("Import CSV")  # Changed from "Import Wells" to "Import CSV"
        import_well_btn.clicked.connect(self.import_wells)
    
        btn_layout.addWidget(add_well_btn)
        btn_layout.addWidget(self.edit_well_btn)
        btn_layout.addWidget(self.delete_well_btn)
        btn_layout.addWidget(import_well_btn)
        btn_layout.addStretch()
    
        layout.addLayout(btn_layout)
    
        # Wells section (70%)
        wells_layout = QVBoxLayout()
        wells_layout.setSpacing(2)
        label = QLabel("Wells:")
        label.setMaximumHeight(20)
        wells_layout.addWidget(label)
        wells_layout.addWidget(self.wells_table)
        wells_widget = QWidget()
        wells_widget.setLayout(wells_layout)
        layout.addWidget(wells_widget, stretch=70)  # 70% of space
    
        # Transducers section (30%)
        transducer_layout = QVBoxLayout()
        transducer_layout.setSpacing(2)
        transducer_layout.addWidget(QLabel("Transducers:"))

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Transducer")
        edit_btn = QPushButton("Edit")
        # Removed the location_btn = QPushButton("Update Location")
        delete_btn = QPushButton("Delete")

        add_btn.clicked.connect(self.add_transducer)
        edit_btn.clicked.connect(self.edit_transducer) 
        # Removed location_btn.clicked.connect(self.update_transducer_location)
        delete_btn.clicked.connect(self.delete_transducer)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        # Rem        oved         btn_layout.addWidget(location_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
    
        transducer_layout.addLayout(btn_layout)
    
        self.transducers_table = QTableWidget()
        self.transducers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transducers_table.setSelectionMode(QTableWidget.SingleSelection)
        self.setup_transducers_table()
        transducer_layout.addWidget(self.transducers_table)
    
        transducer_widget = QWidget()
        transducer_widget.setLayout(transducer_layout)
        layout.addWidget(transducer_widget, stretch=30)  # 30% of space
    
        group.setLayout(layout)
        return group

    def add_well(self):
        """Open dialog to add a new well."""
        if not self.db_manager.well_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
    
        from ..dialogs.well_dialog import WellDialog
        dialog = WellDialog(self.db_manager.well_model, parent=self)
    
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_wells_table()
    
    def edit_well(self):
        """Open dialog to edit the selected well."""
        if not self.db_manager.well_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
    
        current_row = self.wells_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a well to edit")
            return
    
        well_number = self.wells_table.item(current_row, 3).text()  # Well Number is in column 3
        well_data = self.db_manager.well_model.get_well(well_number)
    
        from ..dialogs.well_dialog import WellDialog
        dialog = WellDialog(self.db_manager.well_model, well_data, parent=self)
    
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_wells_table()
    
    def import_wells(self):
        """Import wells from a CSV file."""
        if not self.db_manager.well_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
    
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            str(self.current_dir),
            "CSV files (*.csv)"
        )
    
        if (file_path):
            from ..dialogs.well_import_dialog import WellImportDialog
            dialog = WellImportDialog(self.db_manager.well_model, file_path, self)
            
            if dialog.exec_() == QDialog.Accepted:
                self.refresh_wells_table()
    
    def refresh_wells_table(self):
        """Refresh the wells table contents"""
        if not self.db_manager.well_model:
            return
            
        try:
            # Temporarily disable sorting while populating the table
            self.wells_table.setSortingEnabled(False)
            
            # Get all well data directly from database to ensure we get all fields
            with sqlite3.connect(self.db_manager.current_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM wells")
                wells = [dict(row) for row in cursor.fetchall()]
            
            # Flags stored in wells table; no need to recalculate from readings
            
            # Create default flag values for wells that might not have readings yet
            default_flags = {'baro_status': 'no_data', 'level_status': 'no_data'}
                
            # Proceed with normal table population
            self.wells_table.setRowCount(len(wells))
            self.wells_table.setIconSize(QSize(10, 10))
            
            # Start time for the row population loop
            loop_start_time = time.time()
            
            for row, well in enumerate(wells):
                # User flag
                user_flag_item = QTableWidgetItem()
                user_flag_status = well.get('user_flag', 'unchecked')
                user_flag_item.setIcon(self.create_user_flag_icon(user_flag_status))
                user_flag_item.setData(Qt.UserRole, user_flag_status)
                tooltips = {
                    'unchecked': 'Not checked yet',
                    'error': 'Error found by user',
                    'approved': 'Approved by user'
                }
                user_flag_item.setToolTip(tooltips.get(user_flag_status, ''))
                self.wells_table.setItem(row, 0, user_flag_item)

                # Flags for this well from wells table
                well_number = well['well_number']
                well_flags = {
                    'baro_status': well.get('baro_status', 'no_data'),
                    'level_status': well.get('level_status', 'no_data')
                }
                # Debug: log the loaded flag statuses for this well
                logger.debug(f"Refresh: Well {well_number} loaded flags -> baro: {well_flags['baro_status']}, level: {well_flags['level_status']}")

                # Check if well is telemetry first
                is_telemetry = well.get('data_source') == 'telemetry'

                # Baro Flag
                baro_item = QTableWidgetItem()
                if is_telemetry:
                    baro_color = '#0000FF'  # Blue for telemetry
                else:
                    baro_color = "#808080"  # Default to gray
                    if well_flags['baro_status'] == 'all_master':
                        baro_color = "#28a745"  # Previous green shade
                    elif well_flags['baro_status'] == 'has_non_master':
                        baro_color = "#FF0000"  # Red
                baro_item.setIcon(self.create_flag_icon(baro_color))
                baro_item.setTextAlignment(Qt.AlignCenter)
                baro_item.setData(Qt.UserRole, baro_color)
                self.wells_table.setItem(row, 1, baro_item)

                # Level Flag
                level_item = QTableWidgetItem()
                if is_telemetry:
                    level_color = '#0000FF'  # Blue for telemetry
                else:
                    level_color = "#808080"  # Default to gray
                    if well_flags['level_status'] == 'default_level':
                        level_color = "#FF0000"  # Red
                    elif well_flags['level_status'] == 'no_default':
                        level_color = "#28a745"  # Previous green shade
                level_item.setIcon(self.create_flag_icon(level_color))
                level_item.setTextAlignment(Qt.AlignCenter)
                level_item.setData(Qt.UserRole, level_color)
                self.wells_table.setItem(row, 2, level_item)

                # Other columns
                self.wells_table.setItem(row, 3, QTableWidgetItem(well['well_number']))
                self.wells_table.setItem(row, 4, QTableWidgetItem(well.get('cae_number', '')))
                self.wells_table.setItem(row, 5, QTableWidgetItem(well.get('aquifer', '')))
                self.wells_table.setItem(row, 6, QTableWidgetItem(well.get('well_field', '')))
                self.wells_table.setItem(row, 7, QTableWidgetItem(well.get('county', '')))
            
            # Log the time for the loop
            logger.debug(f"Populated {len(wells)} table rows in {time.time() - loop_start_time:.4f} seconds")
            
            # Re-enable sorting
            self.wells_table.setSortingEnabled(True)
            
        except Exception as e:
            logger.error(f"Error refreshing wells table: {e}", exc_info=True)

    def create_user_flag_icon(self, status):
        """Create an icon for user flag status"""
        colors = {
            'unchecked': '#808080',  # Gray
            'error': '#FF0000',      # Red
            'approved': '#28a745'    # Green - Updated to match baro/level flags
        }
        return self.create_flag_icon(colors.get(status, '#808080'))

    def on_cell_clicked(self, row, col):
        """Handle cell clicks in the table"""
        if col == 0:  # User flag column
            # Temporarily block the selection change signal
            self.wells_table.blockSignals(True)
            
            # Remember current selection
            current_selection = self.wells_table.selectedItems()
            selection_rows = set()
            for item in current_selection:
                selection_rows.add(item.row())
            
            item = self.wells_table.item(row, col)
            if item:
                current_status = item.data(Qt.UserRole)
                # Cycle through statuses: unchecked -> error -> approved -> unchecked
                status_cycle = {'unchecked': 'error', 'error': 'approved', 'approved': 'unchecked'}
                new_status = status_cycle.get(current_status, 'unchecked')
                
                # Update the icon and status
                item.setIcon(self.create_user_flag_icon(new_status))
                item.setData(Qt.UserRole, new_status)
                
                # Set tooltip based on status
                tooltips = {
                    'unchecked': 'Not checked yet',
                    'error': 'Error found by user',
                    'approved': 'Approved by user'
                }
                item.setToolTip(tooltips.get(new_status, ''))
                
                # Update the database
                well_number = self.wells_table.item(row, 3).text()  # Well Number is in column 3
                self.update_user_flag(well_number, current_status, new_status)
            
            # Restore selection
            self.wells_table.clearSelection()
            for row_idx in selection_rows:
                self.wells_table.selectRow(row_idx)
            
            # Unblock signals
            self.wells_table.blockSignals(False)

    def update_user_flag(self, well_number, old_status, new_status):
        """Update user flag in the database"""
        try:
            # Track the change if this is a cloud database
            if self.db_manager.change_tracker:
                self.db_manager.change_tracker.track_user_flag_change(
                    well_number, old_status, new_status
                )
            
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE wells 
                    SET user_flag = ? 
                    WHERE well_number = ?
                """, (new_status, well_number))
                conn.commit()
                
            # Mark database as modified
            self.db_manager.mark_as_modified()
        except Exception as e:
            logger.error(f"Error updating user flag: {e}")

    def create_flag_icon_from_qcolor(self, color: QColor, diameter: int = 10):
        """Create an icon with a filled circle of the given QColor."""
        padding = 2  # Reduced padding
        total_size = diameter + (padding * 2)
        pixmap = QPixmap(total_size, total_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        
        # Draw circle in center of pixmap
        painter.drawEllipse(padding, padding, diameter, diameter)
        painter.end()
        return QIcon(pixmap)

    def create_flag_icon(self, color_name: str, diameter: int = 10):
        """Create an icon with a filled circle of the given color."""
        # Check if color_name is already a QColor
        if isinstance(color_name, QColor):
            return self.create_flag_icon_from_qcolor(color_name, diameter)
            
        # Make pixmap slightly larger than circle to allow for padding
        padding = 2  # Reduced padding
        total_size = diameter + (padding * 2)
        pixmap = QPixmap(total_size, total_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Use explicit color values for common colors to avoid issues
        if color_name.lower() == "red":
            painter.setBrush(QColor(255, 0, 0))
        elif color_name.lower() == "green":
            painter.setBrush(QColor(0, 180, 0))
        elif color_name.lower() == "gray":
            painter.setBrush(QColor(180, 180, 180))
        else:
            painter.setBrush(QColor(color_name))
        
        painter.setPen(Qt.NoPen)
        
        # Draw circle in center of pixmap
        painter.drawEllipse(padding, padding, diameter, diameter)
        painter.end()
        return QIcon(pixmap)

    def setup_transducers_table(self):
        """Setup the transducers table structure"""
        headers = ["Serial Number", "Current Location", "CAE", "Last Installation", "Location Count"]
        self.transducers_table.setColumnCount(len(headers))
        self.transducers_table.setHorizontalHeaderLabels(headers)
        
        # Configure all columns to resize to content
        header = self.transducers_table.horizontalHeader()
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.transducers_table.setStyleSheet("""
            QTableWidget { font-size: 8pt; }
            QHeaderView::section { font-size: 8pt; height: 25px; padding: 2px; }
        """)
        self.transducers_table.verticalHeader().setDefaultSectionSize(20)  # Set row height
        self.transducers_table.setMinimumSize(350, 150)  # Set minimum size
    
    def setup_wells_table(self):
        """Setup the wells table structure"""
        # Use two-line headers for flag columns
        headers = ["User\nFlag", "Baro\nFlag", "Level\nFlag", "Well Number", "CAE", "Aquifer", "Well Field", "County"]
        self.wells_table.setColumnCount(len(headers))
        self.wells_table.setHorizontalHeaderLabels(headers)
        
        # Set smaller icon size
        self.wells_table.setIconSize(QSize(10, 10))
        
        # Make all columns resizable
        header = self.wells_table.horizontalHeader()
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        # Set initial widths for flag columns only
        font_metrics = self.wells_table.fontMetrics()
        for i in range(3):  # First three columns (user flag + flags)
            text_width = font_metrics.boundingRect(headers[i].replace('\n', ' ')).width()
            self.wells_table.setColumnWidth(i, text_width + 8)  # text width + minimal padding
        
        # Let other columns auto-adjust
        self.wells_table.resizeColumnsToContents()
        
        # Enable sorting
        self.wells_table.setSortingEnabled(True)
        self.wells_table.sortByColumn(3, Qt.AscendingOrder)  # Sort by Well Number
        
        # Style settings to match transducers table
        self.wells_table.setStyleSheet("""
            QTableWidget { font-size: 8pt; }
            QHeaderView::section { font-size: 8pt; height: 25px; padding: 2px; }
        """)
        
        # Set row height
        self.wells_table.verticalHeader().setDefaultSectionSize(20)
        self.wells_table.setMinimumSize(350, 250)
        
        # Enable cell clicking for user flag column
        self.wells_table.cellClicked.connect(self.on_cell_clicked)
        
        # Make the table read-only
        self.wells_table.setEditTriggers(QTableWidget.NoEditTriggers)

    def toggle_plot_type(self):
        """Toggle between water level and temperature plots"""
        if self.show_temp_btn.isChecked():
            self.show_temp_btn.setText("Show Water Levels")
            self.plot_handler.toggle_temperature(True)
        else:
            self.show_temp_btn.setText("Show Temperature")
            self.plot_handler.toggle_temperature(False)
        self.update_plot()
    
    def on_well_selection_changed(self):
        """Handle well selection changes"""
        selected_wells = self.get_selected_wells()
        
        # Enable/disable edit and delete buttons based on selection
        has_selection = len(selected_wells) == 1
        self.edit_well_btn.setEnabled(has_selection)
        self.delete_well_btn.setEnabled(has_selection)
        
        # Update plot
        self.update_plot()
        
        # Update temperature button state
        self.show_temp_btn.setEnabled(len(selected_wells) <= 1)
        if len(selected_wells) > 1:
            self.show_temp_btn.setChecked(False)
            self.plot_handler.toggle_temperature(False)

    def get_selected_wells(self):
        """Return a list of well numbers for the selected rows"""
        selected_rows = self.wells_table.selectionModel().selectedRows()
        wells = []
        for index in selected_rows:
            well_item = self.wells_table.item(index.row(), 3)  # column 3 contains well number
            if well_item:
                wells.append(well_item.text())
        return wells

    def update_plot(self):
        """Update the plot with current selection"""
        selected_wells = self.get_selected_wells()
        if self.water_level_model and self.db_manager.current_db:
            # Show loading indicator
            loading_dialog = QDialog(self)
            loading_dialog.setWindowTitle("Loading")
            loading_dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            loading_layout = QVBoxLayout(loading_dialog)
            loading_label = QLabel("Loading plot data...\nPlease wait.")
            loading_label.setAlignment(Qt.AlignCenter)
            loading_label.setStyleSheet("font-size: 12pt; padding: 20px; background-color: white; color: #333;")
            loading_layout.addWidget(loading_label)
            loading_dialog.setStyleSheet("background-color: white; border: 1px solid #ccc;")
            loading_dialog.setFixedSize(250, 80)
            
            # Position in center of the plot area
            loading_dialog.move(self.canvas.mapToGlobal(
                QPoint(self.canvas.width() // 2 - 125, self.canvas.height() // 2 - 40)))
            
            loading_dialog.show()
            QApplication.processEvents()  # Ensure dialog is displayed
            
            try:
                # Update the plot
                self.plot_handler.update_plot(
                    selected_wells,
                    self.water_level_model,
                    self.db_manager.current_db
                )
            finally:
                # Hide loading dialog
                loading_dialog.close()

    def import_single_file(self):
        """Handle import of single XLE file"""
        if not self.water_level_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return

        # Show progress dialog using the standardized handler
        progress_dialog.show("Select a file to import...", "Processing File")
        
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select XLE File",
                "",
                "XLE files (*.xle)"
            )
                
            if not file_path:
                progress_dialog.close()
                return

            # Read file metadata
            progress_dialog.update(10, f"Reading file: {Path(file_path).name}")
            
            reader = SolinstReader()
            df, metadata = reader.read_xle(Path(file_path))
            
            # Match well location
            progress_dialog.update(30, "Matching well location...")
            
            well_mapping = self.well_handler.get_well_mapping()
            well_number = self.well_handler.match_well_location(metadata.location, well_mapping)
            
            if not well_number:
                progress_dialog.close()
                well_number = self._show_well_selection_dialog(metadata.location, well_mapping)
                if not well_number:
                    QMessageBox.warning(
                        self,
                        "Well Not Found",
                        f"Could not match file location '{metadata.location}' to any well.\n"
                        "Please verify the file or well information."
                    )
                    return

            # Check transducer status
            progress_dialog.update(50, "Checking transducer status...")
            
            transducer_status = self.well_handler.check_transducer_status(
                metadata.serial_number, 
                well_number
            )
            
            if transducer_status['status'] == 'error':
                progress_dialog.close()
                QMessageBox.critical(self, "Error", transducer_status['message'])
                return
            
            if transducer_status['status'] == 'warning':
                progress_dialog.close()
                response = QMessageBox.warning(
                    self,
                    "Transducer Mismatch",
                    f"{transducer_status['message']}\n\nDo you want to continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if response == QMessageBox.No:
                    return
            
            # Show import dialog
            progress_dialog.update(90, "Preparing import dialog...")
            
            dialog = WaterLevelImportDialog(
                water_level_model=self.water_level_model,
                file_path=file_path,
                well_number=well_number,
                parent=self,
                transducer_status=transducer_status
            )
            
            progress_dialog.close()
            
            if dialog.exec_() == QDialog.Accepted:
                self.update_plot()
                # Refresh the wells table to show updated data
                self.refresh_wells_table()
                # Select the well in the table
                self.select_well_in_table(well_number)
                
        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")
    
    def _show_well_selection_dialog(self, file_location: str, 
                                  well_mapping: Dict[str, str]) -> Optional[str]:
        """Show dialog for manual well selection"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Well")
        layout = QVBoxLayout()
        
        # Add information label
        layout.addWidget(QLabel(
            f"File location '{file_location}' could not be automatically matched.\n"
            "Please select the correct well:"
        ))
        
        # Add well selection combo
        combo = QComboBox()
        combo.addItem("-- Select Well --", None)
        for cae, wn in well_mapping.items():
            combo.addItem(f"{wn} ({cae})", wn)
        
        layout.addWidget(combo)
        
        # Add buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        
        # Connect buttons
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec_() == QDialog.Accepted:
            return combo.currentData()
        return None        
        
        
    def import_folder(self):
        """Handle folder import for water level data"""
        logger.debug("Starting water level folder import...")
        if not self.water_level_model:
            logger.debug("No water level model available")
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
                
        try:
            logger.debug("Creating WaterLevelFolderDialog...")
            from ..dialogs.water_level_folder_dialog import WaterLevelFolderDialog
            dialog = WaterLevelFolderDialog(
                water_level_model=self.water_level_model,
                parent=self
            )
            logger.debug("WaterLevelFolderDialog created")
            
            if dialog.exec_() == QDialog.Accepted:
                logger.debug("Dialog accepted, updating plot and table")
                self.update_plot()
                # Refresh the wells table to show updated data
                self.refresh_wells_table()
            else:
                logger.debug("Dialog cancelled or closed")
        except Exception as e:
            logger.error(f"Error creating folder dialog: {e}", exc_info=True)
        
    def refresh_transducers_table(self):
        """Refresh the transducers table contents"""
        if not self.db_manager.well_model:
            return
            
        try:
            transducers = self.transducer_handler.get_all_transducers()
            self.transducers_table.setRowCount(len(transducers))

            for row, transducer in enumerate(transducers):
                # Create items with center alignment
                for col, value in enumerate([
                    transducer['serial_number'],
                    transducer['well_number'] or "NO_MATCH",
                    transducer['cae_number'] or "",
                    str(transducer['installation_date']),
                    str(transducer['location_count'])
                ]):
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignCenter)  # Center align text
                    self.transducers_table.setItem(row, col, item)

        except Exception as e:
            logger.error(f"Error refreshing transducers table: e")

    
    def add_transducer(self):
        """Open dialog to add new transducer"""
        if not self.db_manager.well_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
            
        from ..dialogs.transducer_dialog import TransducerDialog
        dialog = TransducerDialog(self.db_manager.well_model, None, self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                success, message, additional_data = self.transducer_handler.add_transducer(dialog.get_data())
                if success:
                    self.refresh_transducers_table()
                elif message == "needs_confirmation":
                    # Show confirmation dialog
                    from ..dialogs.transducer_location_dialog import TransducerLocationDialog
                    confirm_dialog = TransducerLocationDialog(
                        additional_data['current_location'],
                        additional_data['new_location'],
                        parent=self
                    )
                    if confirm_dialog.exec_() == QDialog.Accepted:
                        self.refresh_transducers_table()
                else:
                    QMessageBox.critical(self, "Error", message)
            except Exception as e:
                logger.error(f"Error adding transducer: {e}")
                QMessageBox.critical(self, "Error", str(e))
    
    def edit_transducer(self):
        """Open dialog to edit selected transducer"""
        current_row = self.transducers_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a transducer to edit")
            return
            
        serial_number = self.transducers_table.item(current_row, 0).text()
        transducer = self.transducer_handler.get_transducer(serial_number)
        
        if not transducer:
            QMessageBox.critical(self, "Error", "Failed to get transducer data")
            return
        
        from ..dialogs.transducer_dialog import TransducerDialog
        dialog = TransducerDialog(self.db_manager.well_model, transducer, self)
        if dialog.exec_() == QDialog.Accepted:
            success, message = self.transducer_handler.update_transducer(dialog.get_data())
            if success:
                self.refresh_transducers_table()
            else:
                QMessageBox.critical(self, "Error", message)
    
    def delete_transducer(self):
        """Delete selected transducer"""
        current_row = self.transducers_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a transducer")
            return
            
        serial_number = self.transducers_table.item(current_row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                   f"Delete transducer {serial_number}?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.transducer_handler.delete_transducer(serial_number)
            if success:
                self.refresh_transducers_table()
            else:
                QMessageBox.critical(self, "Error", message)
    
    def update_monet_data(self):
        """Fetch and update Monet data, converting to UTC storage"""
        try:
            # Get credentials from settings
            if hasattr(self.db_manager, 'settings_handler') and self.db_manager.settings_handler:
                settings_handler = self.db_manager.settings_handler
            else:
                # Fallback to get settings handler from main window
                main_window = self.window()
                if main_window and hasattr(main_window, 'settings_handler'):
                    settings_handler = main_window.settings_handler
                else:
                    QMessageBox.critical(self, "Error", "Settings handler not found. Please restart the application.")
                    return
                    
            username = settings_handler.get_setting("monet_username", "")
            password = settings_handler.get_setting("monet_password", "")
            url = settings_handler.get_setting("monet_api_url", 
                "https://services1.arcgis.com/EX9Lx0EdFAxE7zvX/arcgis/rest/services/MONET/FeatureServer/2/query")
            
            # Check if credentials are configured
            if not username or not password:
                # Show dialog prompting user to configure credentials
                QMessageBox.warning(
                    self, 
                    "Monet API Settings Required", 
                    "Please configure your Monet API credentials in Settings → Monet API Settings before using this feature."
                )
                return
                
            # Update status in main window if possible
            main_window = self.window()
            if main_window and hasattr(main_window, 'monet_status_label'):
                main_window.monet_status_label.setText(f"Connecting as {username}...")
                main_window.monet_status_label.setStyleSheet("color: #0077ff;")
                QApplication.processEvents()  # Update UI
            
            # Show progress dialog using the standardized handler
            progress_dialog.show("Fetching Monet data...", "Updating Monet Data")
            
            monet_data = fetch_monet_data(username, password, url, verbose=False)
            progress_dialog.update(25)
            
            # Update status in main window to show successful connection
            if main_window and hasattr(main_window, 'monet_status_label'):
                main_window.monet_status_label.setText(f"Connected as {username}")
                main_window.monet_status_label.setStyleSheet("color: #007700; font-weight: bold;")
            
            if not monet_data:
                progress_dialog.close()
                QMessageBox.warning(self, "Warning", "No Monet data retrieved")
                return
            
            progress_dialog.update(50, "Saving to database...")
                
            records_added, unmatched, well_updates = self.manual_readings_handler.update_monet_data(monet_data)
            
            progress_dialog.update(75, "Finalizing...")
            
            # Build result message
            message = []
            updated_wells = [well for well, count in well_updates.items() if count > 0]
            
            if updated_wells:
                message.append("New measurements added for wells:")
                for well in updated_wells:
                    message.append(f"- {well}: {well_updates[well]} new readings")
                message.append(f"\nTotal new measurements: {records_added}")
            else:
                message.append("No new measurements found")
                
            if unmatched:
                message.append("\nUnmatched well IDs:")
                message.append(", ".join(unmatched))
                
            progress_dialog.update(100)
            progress_dialog.close()
            
            QMessageBox.information(self, "Update Complete", "\n".join(message))
            
            self.update_plot()
            
        except Exception as e:
            # Update status in main window to show connection failure
            main_window = self.window()
            if main_window and hasattr(main_window, 'monet_status_label'):
                main_window.monet_status_label.setText("Connection failed")
                main_window.monet_status_label.setStyleSheet("color: #ff0000;")
            
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to update Monet data: {str(e)}")
    
    def create_manual_readings_section(self) -> QGroupBox:
        """Create manual readings section with updated buttons"""
        group = QGroupBox("Manual Readings")
        layout = QHBoxLayout()
        
        # Update Monet Data button
        update_monet_btn = QPushButton("Update Monet Data")
        update_monet_btn.clicked.connect(self.update_monet_data)
        
        # Add Manual Reading button
        add_manual_btn = QPushButton("Add Manual Reading")
        add_manual_btn.clicked.connect(self.add_manual_reading)
        
        # Import Manual Readings button
        import_manual_btn = QPushButton("Import CSV File")
        import_manual_btn.clicked.connect(self.import_csv_file)
        
        layout.addWidget(update_monet_btn)
        layout.addWidget(add_manual_btn)
        layout.addWidget(import_manual_btn)
        layout.addStretch()
        
        group.setLayout(layout)
        return group

    def add_manual_reading(self):
        """Open dialog to add a single manual reading"""
        dialog = AddManualReadingDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                data = dialog.get_data()
                
                # Get well's top of casing from cache
                well_info = self.well_handler.get_well_info(data['well_number'])
                if not well_info:
                    raise ValueError(f"Well {data['well_number']} not found")
                
                # Add top of casing to data for water level calculation
                data['top_of_casing'] = well_info['top_of_casing']
                
                success, message = self.manual_readings_handler.add_reading(data)
                if success:
                    self.update_plot()
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.critical(self, "Error", message)
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add manual reading: {str(e)}")

    def import_csv_file(self):
        """Import water level readings from a CSV file"""
        if not self.water_level_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV files (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            # Process CSV using the handler
            df = ManualReadingsCSVHandler.validate_and_process(file_path)
            
            # Show preview dialog
            preview_dialog = ManualReadingsPreviewDialog(df, self.db_manager, self)
            if preview_dialog.exec_() != QDialog.Accepted:
                return
            
            # Get selected wells and import
            selected_wells = preview_dialog.get_selected_wells()
            if not selected_wells:
                QMessageBox.warning(self, "Warning", "No wells selected for import")
                return
            
            # Import data using the handler
            records_added, errors = self.manual_readings_handler.import_readings(df, selected_wells)
            
            # Show results
            message_parts = []
            if records_added > 0:
                message_parts.append(f"Successfully added {records_added} measurements.")
            else:
                message_parts.append("No measurements were added.")
                
            if errors:
                message_parts.append("\nErrors encountered:")
                message_parts.extend(errors)
            
            message = "\n".join(message_parts)
            
            if records_added > 0:
                QMessageBox.information(self, "Import Complete", message)
                self.update_plot()
            else:
                QMessageBox.warning(self, "Import Failed", message)
            
        except Exception as e:
            error_msg = f"Failed to import readings: {str(e)}"
            print(f"Critical error: {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
                
    def cleanup(self):
        """Clean up resources before closing"""
        try:
            # Close database connection
            if self.water_level_model:
                self.water_level_model = None
                
            # Clear matplotlib figure
            if hasattr(self, 'figure'):
                self.figure.clear()
                plt.close(self.figure)
                
            # Remove canvas
            if hasattr(self, 'canvas'):
                self.canvas.close()
                
            # Clear tables
            if hasattr(self, 'wells_table'):
                self.wells_table.clearContents()
                self.wells_table.setRowCount(0)
            if hasattr(self, 'transducers_table'):
                self.transducers_table.clearContents()
                self.transducers_table.setRowCount(0)
                
            # Delete widgets
            self.deleteLater()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    def select_well_in_table(self, well_number: str):
        """Selects the well in the table after import."""
        for row in range(self.wells_table.rowCount()):
            item = self.wells_table.item(row, 3)  # Assuming 'Well Number' is column 3
            if item and item.text() == well_number:
                self.wells_table.selectRow(row)
                self.on_well_selection_changed()  # Ensure plot updates
                break
            
    def showEvent(self, event):
        """Ensure the transducers table is loaded when the tab is first displayed."""
        super().showEvent(event)
        
        # Refresh transducers when the tab is shown
        self.refresh_transducers_table()
        
        # Remove auto-selection of first well
        # self.select_first_well()
    
    def select_first_well(self):
        """Automatically select the first well in the table when the tab is opened."""
        if self.wells_table.rowCount() > 0:
            self.wells_table.selectRow(0)  # Select the first row
            self.on_well_selection_changed()  # Ensure plot updates

    def load_databases(self):
        """Load existing database files"""
        self.db_combo.clear()
        db_files = list(self.current_dir.glob("*.db"))
        
        if not db_files:
            self.db_combo.addItem("No databases found")
            self.db_combo.setEnabled(False)
        else:
            self.db_combo.setEnabled(True)
            for db_file in db_files:
                self.db_combo.addItem(db_file.name)
    
    def delete_well(self):
        """Delete the selected well"""
        current_row = self.wells_table.currentRow()
        if current_row < 0:
            return
        
        well_number = self.wells_table.item(current_row, 3).text()  # Well Number is in column 3
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete well {well_number}?\n"
            "This will remove the well and ALL associated data.\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success, message = self.db_manager.well_model.delete_well(well_number)
                if success:
                    self.refresh_wells_table()
                    self.refresh_transducers_table()
                    QMessageBox.information(self, "Success", "Well deleted successfully")
                else:
                    QMessageBox.critical(self, "Error", message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete well: {str(e)}")

    def edit_trace(self, well_number: str, flag_type: str):
        logger.debug(f"Editing {flag_type} trace for well {well_number}")
        # TODO: Implement trace editing dialog
        QMessageBox.information(
            self,
            "Edit Trace",
            f"Trace editor for {well_number} ({flag_type}) will be implemented soon!"
        )
        
    def open_edit_dialog(self):
        """Open the water level edit dialog"""
        selected_wells = self.get_selected_wells()
        if not selected_wells:
            QMessageBox.warning(self, "Warning", "Please select a well")
            return
        
        # Only select first well if multiple selected
        if len(selected_wells) > 1:
            QMessageBox.information(self, "Information", 
                                 "Multiple wells selected. Only the first well will be edited.")
            selected_wells = [selected_wells[0]]
            
        try:
            # Get the plot data for the selected well, including master baro data
            plot_data_dict = self.plot_handler.get_plot_data(
                selected_wells,
                self.water_level_model,
                self.db_manager.current_db,
                self.well_handler,
                include_master_baro=True  # Explicitly request master baro data for editing
            )
            
            if plot_data_dict is None:
                QMessageBox.warning(self, "Warning", "Error retrieving data")
                return
                
            # Check if we have any transducer data
            if plot_data_dict['transducer_data'].empty:
                QMessageBox.warning(self, "Warning", "No transducer data available for selected well")
                return
                
            from ..dialogs.water_level_edit_dialog import WaterLevelEditDialog
            
            # Pass the separate DataFrames and current database path to the dialog
            dialog = WaterLevelEditDialog(
                transducer_data=plot_data_dict['transducer_data'],
                manual_data=plot_data_dict['manual_data'], 
                master_baro_data=plot_data_dict['master_baro_data'],  # Updated name
                parent=self, 
                db_path=self.db_manager.current_db
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Handle the edited data here
                self.update_plot()
                # Refresh wells table to show updated flag status
                self.refresh_wells_table()
                
        except Exception as e:
            logger.error(f"Error opening edit dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open edit dialog: {str(e)}")
    
    def update_for_screen(self, screen):
        """Update layout for the current screen"""
        try:
            logger.debug(f"Updating WaterLevelTab layout for screen: {screen.name()}")
            
            # Get screen dimensions
            available_size = screen.availableGeometry().size()
            dpi_factor = screen.devicePixelRatio()
            
            # Update figure size based on screen dimensions
            if hasattr(self, 'figure'):
                # Calculate new figure size in inches (divide pixel size by DPI)
                width_inches = (available_size.width() * 0.5) / (self.figure.dpi * dpi_factor)
                height_inches = (available_size.height() * 0.3) / (self.figure.dpi * dpi_factor)
                self.figure.set_size_inches(width_inches, height_inches)
                
                # Update canvas minimum size
                if hasattr(self, 'canvas'):
                    self.canvas.setMinimumSize(int(available_size.width() * 0.4), int(available_size.height() * 0.25))
            
            # Update tables dimensions
            if hasattr(self, 'wells_table'):
                self.wells_table.setMinimumSize(int(available_size.width() * 0.25), int(available_size.height() * 0.25))
                
            if hasattr(self, 'transducers_table'):
                self.transducers_table.setMinimumSize(int(available_size.width() * 0.25), int(available_size.height() * 0.15))
                
            # Update toolbar sizing if it exists
            if hasattr(self, 'toolbar'):
                # Calculate appropriate icon size based on DPI
                icon_size = max(24, int(24 * dpi_factor * 0.8))  # Scale icon but not too much
                self.toolbar.setIconSize(QSize(icon_size, icon_size))
                
            # Force layout update
            if self.layout():
                self.layout().update()
                self.layout().activate()
                
            # Redraw the plot
            self.update_plot()
            
        except Exception as e:
            logger.error(f"Error updating WaterLevelTab for screen change: {e}")

    def refresh_all_data(self):
        """Refresh all data in the water level tab with progress indication"""
        # Show progress dialog
        progress_dialog.show("Refreshing water level data...", "Refreshing Tab")
        
        try:
            # Step 1: Refresh wells table
            progress_dialog.update(20, "Refreshing wells data...")
            self.refresh_wells_table()
            
            # Step 2: Refresh transducers table
            progress_dialog.update(40, "Refreshing transducers data...")
            self.refresh_transducers_table()
            
            # Step 3: Refresh plot if wells are selected
            progress_dialog.update(60, "Updating plot...")
            selected_wells = self.get_selected_wells()
            if selected_wells and self.water_level_model and self.db_manager.current_db:
                self.plot_handler.update_plot(
                    selected_wells,
                    self.water_level_model,
                    self.db_manager.current_db
                )
            
            # Step 4: Recreate water level model to ensure fresh data
            progress_dialog.update(80, "Reinitializing data model...")
            if self.db_manager.current_db:
                self.water_level_model = WaterLevelModel(self.db_manager.current_db)
            
            # Done
            progress_dialog.update(100, "Refresh complete!")
            progress_dialog.close()
            
            # Show success message
            QMessageBox.information(self, "Refresh Complete", "Water level data has been refreshed successfully.")
            
        except Exception as e:
            logger.error(f"Error refreshing water level data: {e}")
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {str(e)}")

    def create_animation_area(self):
        """Create an area for water animation in the bottom left corner"""
        from PyQt5.QtCore import QTimer, Qt
        
        # Create a group box with a title
        group = QGroupBox("Water Level Animation")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 9pt;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
                background-color: #f8f8f8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(5)
        
        # Create animation canvas (using QLabel for now)
        self.animation_label = QLabel()
        self.animation_label.setAlignment(Qt.AlignCenter)
        self.animation_label.setMinimumSize(180, 120)
        self.animation_label.setStyleSheet("background-color: #e0f7fa; border-radius: 5px;")
        
        # Add a placeholder text
        self.animation_label.setText("Water Level Animation\nComing Soon")
        
        # Add the animation label to the layout
        layout.addWidget(self.animation_label)
        
        # Initialize animation frames
        self.animation_frames = self.initialize_animation_frames()
        self.current_frame = 0
        
        # Create timer for animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(100)  # Update every 100 ms
        
        return group
        
    def initialize_animation_frames(self):
        """Initialize the animation frames"""
        try:
            # This is a placeholder - in a real implementation you would load actual animation frames
            frames = []
            
            # Create a simple animation with rising water level
            water_levels = [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25]
            
            for water_level in water_levels:
                # Create a pixmap for this frame
                pixmap = QPixmap(180, 120)
                pixmap.fill(Qt.transparent)
                
                # Create painter
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Draw well casing
                painter.setPen(Qt.black)
                painter.setBrush(Qt.lightGray)
                painter.drawRect(50, 20, 80, 80)
                
                # Draw water level
                water_height = int(80 * water_level / 100)
                painter.setBrush(QColor(0, 120, 215))  # Blue water
                painter.drawRect(50, 100 - water_height, 80, water_height)
                
                # Add text
                painter.setPen(Qt.black)
                painter.drawText(pixmap.rect(), Qt.AlignBottom | Qt.AlignHCenter, f"Water Level: {water_level}%")
                
                painter.end()
                frames.append(pixmap)
            
            return frames
            
        except Exception as e:
            logger.error(f"Error initializing animation frames: {e}")
            return []
            
    def update_animation(self):
        """Update the animation frame"""
        if not self.animation_frames:
            return
            
        try:
            # Set the current frame
            self.animation_label.setPixmap(self.animation_frames[self.current_frame])
            
            # Update the frame index
            self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
            
        except Exception as e:
            logger.error(f"Error updating animation: {e}")
            
    def create_compact_transducer_panel(self):
        """Create a compact transducer data panel with buttons in a single row"""
        group = QGroupBox("Transducer Data")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                border-radius: 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #495057;
                font-size: 10pt;
            }
        """)
        
        # Create a horizontal layout for a single row of buttons
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 15, 8, 8)
        layout.setSpacing(6)
        
        # Create buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        # Create buttons with icons
        import_file_btn = QPushButton("Import Single File")
        import_file_btn.clicked.connect(self.import_single_file)
        import_file_btn.setMinimumWidth(120)
        import_file_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: 1px solid #0056b3;
                border-radius: 8px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                font-size: 9pt;
                min-height: 36px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #002752;
            }
        """)
        
        import_folder_btn = QPushButton("Import Folder")
        import_folder_btn.clicked.connect(self.import_folder)
        import_folder_btn.setMinimumWidth(120)
        import_folder_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: 1px solid #0056b3;
                border-radius: 8px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                font-size: 9pt;
                min-height: 36px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #002752;
            }
        """)
        
        # Add buttons to the horizontal layout
        btn_layout.addWidget(import_file_btn)
        btn_layout.addWidget(import_folder_btn)
        btn_layout.addStretch()
        
        # Add button layout to main layout
        layout.addLayout(btn_layout)
        
        # Set a reasonable maximum height for better appearance
        group.setMaximumHeight(85)
        
        return group
    
    def create_compact_telemetry_panel(self):
        """Create a compact telemetry data panel with buttons in a single row"""
        group = QGroupBox("Telemetry Data")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                border-radius: 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #495057;
                font-size: 10pt;
            }
        """)
        
        # Create a layout
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 15, 8, 8)
        layout.setSpacing(6)
        
        # Create button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        # Create button 
        update_telemetry_btn = QPushButton("Update Telemetry")
        update_telemetry_btn.clicked.connect(self.update_telemetry_data)
        update_telemetry_btn.setMinimumWidth(120)
        update_telemetry_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: 1px solid #0056b3;
                border-radius: 8px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                font-size: 9pt;
                min-height: 36px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #002752;
            }
        """)
        
        # Add button to layout
        btn_layout.addWidget(update_telemetry_btn)
        btn_layout.addStretch()
        
        # Add button layout to main layout
        layout.addLayout(btn_layout)
        
        # Set a reasonable maximum height for better appearance
        group.setMaximumHeight(85)
        
        return group
    
    def create_compact_manual_panel(self):
        """Create a compact manual readings panel with buttons in a single row"""
        group = QGroupBox("Manual Readings")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                border-radius: 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #495057;
                font-size: 10pt;
            }
        """)
        
        # Create a vertical layout with a single row of buttons
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 15, 8, 8)
        layout.setSpacing(6)
        
        # Create button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        # Create buttons
        update_monet_btn = QPushButton("Update Monet Data")
        update_monet_btn.clicked.connect(self.update_monet_data)
        update_monet_btn.setMinimumWidth(120)
        update_monet_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: 1px solid #0056b3;
                border-radius: 8px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                font-size: 9pt;
                min-height: 36px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #002752;
            }
        """)
        
        add_manual_btn = QPushButton("Add Manual Reading")
        add_manual_btn.clicked.connect(self.add_manual_reading)
        add_manual_btn.setMinimumWidth(120)
        add_manual_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: 1px solid #0056b3;
                border-radius: 8px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                font-size: 9pt;
                min-height: 36px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #002752;
            }
        """)
        
        import_manual_btn = QPushButton("Import CSV File")
        import_manual_btn.clicked.connect(self.import_csv_file)
        import_manual_btn.setMinimumWidth(120)
        import_manual_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: 1px solid #0056b3;
                border-radius: 8px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                font-size: 9pt;
                min-height: 36px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #002752;
            }
        """)
        
        # Add buttons to the horizontal layout
        btn_layout.addWidget(update_monet_btn)
        btn_layout.addWidget(add_manual_btn)
        btn_layout.addWidget(import_manual_btn)
        btn_layout.addStretch()
        
        # Add button layout to main layout
        layout.addLayout(btn_layout)
        
        # Set a reasonable maximum height for better appearance
        group.setMaximumHeight(85)
        
        return group
    
    def create_logo_area(self):
        """Create an area for app logo in the bottom right corner"""
        # Create a group box without a title
        group = QWidget()
        group.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)
        
        # Create layout
        layout = QVBoxLayout(group)
        layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)
        
        # Create logo label
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setMinimumSize(150, 100)  # Reduced size
        self.logo_label.setMaximumSize(150, 100)  # Reduced size
        self.logo_label.setScaledContents(True)
        
        # Load the water level tab icon
        icon_path = Path(__file__).parent.parent / "icons" / "Water_level_tab_icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            self.logo_label.setPixmap(pixmap)
            logger.debug(f"Loaded water level tab icon from {icon_path}")
        else:
            self.logo_label.setText("CAESER\nWater Levels")
            self.logo_label.setStyleSheet("""
                font-size: 16pt;
                font-weight: bold;
                color: #2c3e50;
                background-color: #ecf0f1;
                border-radius: 10px;
                padding: 20px;
            """)
            logger.warning(f"Water level tab icon not found at {icon_path}, using text fallback")
        
        # Add the logo label to the layout
        layout.addWidget(self.logo_label)
        
        return group

    def toggle_gap_highlighting(self, state):
        """Toggle gap highlighting in the plot based on checkbox state"""
        # Convert state to boolean (state=2 is checked, state=0 is unchecked)
        show_gaps = (state == 2)
        # Update the plot handler setting
        self.plot_handler.toggle_gap_highlighting(show_gaps)
        # Update the plot to apply the change
        self.update_plot()