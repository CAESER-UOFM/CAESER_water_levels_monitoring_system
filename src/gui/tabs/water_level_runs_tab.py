from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QLabel, QComboBox, 
                             QDialog, QDialogButtonBox, QDateEdit, QFrame,
                             QHeaderView, QSizePolicy, QTabWidget, QFileDialog,
                             QInputDialog, QProgressDialog, QMessageBox, QAction, 
                             QApplication, QMainWindow)

from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QDate, QUrl, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPainter, QIcon, QColor
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import pytz
import os
import tempfile
import json
import folium
from folium import plugins
import branca
from ..handlers.google_drive_monitor import GoogleDriveMonitor
from ..handlers.field_data_consolidator import FieldDataConsolidator
from pathlib import Path
import traceback
from ..handlers.runs_folder_monitor import RunsFolderMonitor
import base64

logger = logging.getLogger(__name__)

class WellSelectionDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_wells = []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Select Wells for Run")
        self.setMinimumWidth(1200)
        layout = QVBoxLayout(self)
        
        # Add button container above table
        button_container = QHBoxLayout()
        
        # Select/Deselect All button
        self.select_all_btn = QPushButton("Deselect All")
        self.select_all_btn.clicked.connect(self.toggle_all_wells)
        self.select_all_btn.setFont(QFont("Arial", 10))
        button_container.addWidget(self.select_all_btn)
        
        button_container.addStretch()
        layout.addLayout(button_container)
        
        # Wells table with updated columns
        self.wells_table = QTableWidget(0, 9)  # Changed to 9 columns
        self.wells_table.setHorizontalHeaderLabels([
            "Include", "Transducer", "Manual", "Well Number", "CAE", "Well Field", 
            "Last WL Reading", "Last Manual Reading", "Notes"
        ])
        
        # Set column widths
        header = self.wells_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Include checkbox
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Transducer
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Manual
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Well Number
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # CAE
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Well Field
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Last WL Reading
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Last Manual Reading
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # Notes
        
        self.wells_table.setColumnWidth(0, 50)  # Include checkbox
        self.wells_table.setColumnWidth(1, 50)  # Transducer
        self.wells_table.setColumnWidth(2, 50)  # Manual
        
        layout.addWidget(self.wells_table, 1)
        
        # Load wells from database
        self.load_wells()
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_wells(self):
        try:
            logger.debug(f"Attempting to connect to database: {self.db_manager.current_db}")
            with sqlite3.connect(self.db_manager.current_db) as conn:
                # Get all wells with their basic information
                wells_query = """
                    SELECT 
                        w.well_number,
                        w.cae_number,
                        w.well_field,
                        w.cluster,
                        w.top_of_casing,
                        w.data_source
                    FROM wells w
                    ORDER BY w.well_number
                """
                logger.debug(f"Executing wells query: {wells_query}")
                wells_df = pd.read_sql(wells_query, conn)
                logger.debug(f"Found {len(wells_df)} wells in database")
                
                if wells_df.empty:
                    logger.warning("No wells found in database!")
                    return
                
                # Get last water level readings with more details - MODIFIED to remove data_source
                wl_query = """
                    SELECT 
                        wl.well_number,
                        wl.timestamp_utc,
                        wl.water_level,
                        wl.temperature,
                        wl.serial_number
                    FROM water_level_readings wl
                    WHERE (wl.well_number, wl.timestamp_utc) IN (
                        SELECT well_number, MAX(timestamp_utc)
                        FROM water_level_readings
                        GROUP BY well_number
                    )
                """
                logger.debug("Executing water level readings query")
                wl_df = pd.read_sql(wl_query, conn, parse_dates=['timestamp_utc'])
                logger.debug(f"Found {len(wl_df)} water level readings")
                
                # Get last manual readings with more details
                manual_query = """
                    SELECT 
                        m.well_number,
                        m.measurement_date_utc,
                        m.water_level,
                        m.dtw_avg,
                        m.comments,
                        m.collected_by
                    FROM manual_level_readings m
                    WHERE (m.well_number, m.measurement_date_utc) IN (
                        SELECT well_number, MAX(measurement_date_utc)
                        FROM manual_level_readings
                        GROUP BY well_number
                    )
                """
                logger.debug("Executing manual readings query")
                manual_df = pd.read_sql(manual_query, conn, parse_dates=['measurement_date_utc'])
                logger.debug(f"Found {len(manual_df)} manual readings")
                
                # Debug print the dataframes
                logger.debug(f"Wells count: {len(wells_df)}")
                logger.debug(f"Water Level readings count: {len(wl_df)}")
                logger.debug(f"Manual readings count: {len(manual_df)}")
                
                # Merge all data, add suffix '_manual' for manual readings columns
                logger.debug("Merging dataframes...")
                wells = wells_df.merge(wl_df, on='well_number', how='left')
                wells = wells.merge(manual_df, on='well_number', how='left', suffixes=('', '_manual'))
                logger.debug(f"Final merged dataframe has {len(wells)} rows")
                
                # Populate table
                self.wells_table.setRowCount(len(wells))
                logger.debug(f"Setting table to {len(wells)} rows")
                
                for row, well in wells.iterrows():
                    try:
                        # Checkbox
                        chk_item = QTableWidgetItem()
                        chk_item.setCheckState(Qt.Checked)
                        self.wells_table.setItem(row, 0, chk_item)
                        
                        # Well Number
                        well_num = str(well.get('well_number'))
                        self.wells_table.setItem(row, 3, QTableWidgetItem(well_num))
                        
                        # CAE
                        cae = str(well.get('cae_number')) if pd.notnull(well.get('cae_number')) else "N/A"
                        self.wells_table.setItem(row, 4, QTableWidgetItem(cae))
                        
                        # Well Field
                        well_field = str(well.get('well_field')) if pd.notnull(well.get('well_field')) else "N/A"
                        self.wells_table.setItem(row, 5, QTableWidgetItem(well_field))
                        
                        # Last WL Reading - Now getting data_source from wells table
                        if pd.notnull(well.get('timestamp_utc')) and pd.notnull(well.get('water_level')):
                            utc_dt = pd.to_datetime(well.get('timestamp_utc'))
                            local_dt = utc_dt.tz_localize('UTC').tz_convert('America/Chicago').tz_localize(None)
                            # Get data_source from the wells table (not from water_level_readings)
                            data_source = well.get('data_source') if pd.notnull(well.get('data_source')) else "unknown"
                            # Safely format numeric values
                            try:
                                water_level = float(well.get('water_level', 0))
                            except (ValueError, TypeError):
                                water_level = 0.0
                            
                            try:
                                temperature = float(well.get('temperature', 0))
                            except (ValueError, TypeError):
                                temperature = 0.0
                            
                            wl_text = (f"{local_dt.strftime('%Y-%m-%d %I:%M %p')} | "
                                     f"{water_level:.2f} ft | "
                                     f"T: {temperature:.1f}°C | {data_source}")
                        else:
                            wl_text = "No data"
                        self.wells_table.setItem(row, 6, QTableWidgetItem(wl_text))
                        
                        # Last Manual Reading
                        if pd.notnull(well.get('measurement_date_utc')) and pd.notnull(well.get('water_level_manual')):
                            utc_dt = pd.to_datetime(well.get('measurement_date_utc'))
                            local_dt = utc_dt.tz_localize('UTC').tz_convert('America/Chicago').tz_localize(None)
                            # Safely format numeric values for manual readings
                            try:
                                water_level_manual = float(well.get('water_level_manual', 0))
                            except (ValueError, TypeError):
                                water_level_manual = 0.0
                            
                            try:
                                dtw_avg = float(well.get('dtw_avg', 0))
                            except (ValueError, TypeError):
                                dtw_avg = 0.0
                            
                            manual_text = (f"{local_dt.strftime('%Y-%m-%d %I:%M %p')} | "
                                         f"{water_level_manual:.2f} ft | "
                                         f"DTW: {dtw_avg:.2f} ft | By: {well.get('collected_by')}")
                        else:
                            manual_text = "No data"
                        self.wells_table.setItem(row, 7, QTableWidgetItem(manual_text))
                        
                        # Notes
                        notes = []
                        if pd.notnull(well.get('top_of_casing')):
                            try:
                                toc = float(well.get('top_of_casing', 0))
                                notes.append(f"TOC: {toc:.2f} ft")
                            except (ValueError, TypeError):
                                notes.append(f"TOC: {well.get('top_of_casing')} ft")
                        if pd.notnull(well.get('comments')):
                            notes.append(f"Last note: {well.get('comments')}")
                        notes_text = " | ".join(notes) if notes else "No notes"
                        self.wells_table.setItem(row, 8, QTableWidgetItem(notes_text))
                        
                    except Exception as e:
                        logger.error(f"Error processing row {row} for well {well.get('well_number', 'unknown')}: {e}")
                        
        except Exception as e:
            logger.error(f"Error loading wells: {e}", exc_info=True)
            raise
            
    def create_flag_icon(self, color_name: str, diameter: int = 16):
        """Create an icon with a filled circle of the given color."""
        padding = 4
        total_size = diameter + (padding * 2)
        pixmap = QPixmap(total_size, total_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color_name))
        painter.setPen(Qt.NoPen)
        
        # Draw circle in center of pixmap
        painter.drawEllipse(padding, padding, diameter, diameter)
        painter.end()
        return QIcon(pixmap)

    def accept_selection(self):
        self.selected_wells = []
        for row in range(self.wells_table.rowCount()):
            if self.wells_table.item(row, 0).checkState() == Qt.Checked:
                # Make sure all required items exist before accessing them
                well_number = self.wells_table.item(row, 3)
                cae = self.wells_table.item(row, 4)
                well_field = self.wells_table.item(row, 5)
                last_wl = self.wells_table.item(row, 6)
                last_manual = self.wells_table.item(row, 7)
                notes = self.wells_table.item(row, 8)

                well_data = {
                    'well_number': well_number.text() if well_number else "N/A",
                    'cae': cae.text() if cae else "N/A",
                    'well_field': well_field.text() if well_field else "N/A",
                    'cluster': "N/A",  # Not shown in selection dialog
                    'last_wl': last_wl.text() if last_wl else "No data",
                    'last_manual': last_manual.text() if last_manual else "No data",
                    'notes': notes.text() if notes else "No notes"
                }
                self.selected_wells.append(well_data)
        self.accept()

    def toggle_all_wells(self):
        """Toggle selection state of all wells"""
        # Get current state from button text
        is_selecting = self.select_all_btn.text() == "Deselect All"
        
        # Update all checkboxes
        for row in range(self.wells_table.rowCount()):
            item = self.wells_table.item(row, 0)  # Get checkbox item
            if item:
                item.setCheckState(Qt.Checked if is_selecting else Qt.Unchecked)
        
        # Update button text
        self.select_all_btn.setText("Select All" if is_selecting else "Deselect All")

class WaterLevelRunsTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.runs = {}  # Dictionary to store run data {run_id: wells_list}
        self.cloud_runs = {}  # Dictionary to track which runs are from cloud {run_id: temp_path}
        self.current_run_id = None  # Track the currently selected run
        
        # Initialize the runs folder monitor with consolidated folder if available
        consolidated_folder_id = None
        main_window = self.window()
        
        if main_window and hasattr(main_window, 'settings_handler'):
            consolidated_folder_id = main_window.settings_handler.get_setting("consolidated_field_data_folder")
            logger.info(f"WaterLevelRunsTab initialization - consolidated_folder_id from settings: {consolidated_folder_id}")
            if not consolidated_folder_id:
                logger.warning("WaterLevelRunsTab initialization - consolidated_field_data_folder setting is empty")
        else:
            logger.warning(f"WaterLevelRunsTab initialization - main_window: {main_window}, has settings_handler: {hasattr(main_window, 'settings_handler') if main_window else False}")
        
        logger.info(f"WaterLevelRunsTab initialization - using folder_id: {consolidated_folder_id}")
        self.runs_monitor = RunsFolderMonitor(folder_id=consolidated_folder_id)
        
        # Connect to database change signals
        if hasattr(self.db_manager, 'database_changed'):
            self.db_manager.database_changed.connect(self.on_database_changed)
            logger.debug("Connected to database_changed signal")
        
        self.setup_ui()
        self.load_existing_runs()

    def on_database_changed(self, db_name):
        """Handle database changes by reloading runs"""
        logger.info(f"Runs tab: Database changed to {db_name}")
        
        # Clear current selection
        self.current_run_id = None
        
        # Reload runs from both local and cloud sources
        self.load_existing_runs()
        
        # Clear the wells table since no run is selected
        if hasattr(self, 'wells_table'):
            self.wells_table.setRowCount(0)
            self.wells_table.hide()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Header Section ---
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("Water Level Monitoring Runs")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #495057;")
        
        header_layout.addWidget(title_label)
        
        layout.addWidget(header_frame)
        
        # Form layout for run creation and selection with improved styling
        form_container = QFrame()
        form_container.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        form_container.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 5px;
                padding: 10px;
            }
            QComboBox {
                min-width: 200px;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        form_layout = QHBoxLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        
        # Label for the dropdown
        run_label = QLabel("Select Run:")
        run_label.setFont(QFont("Arial", 10, QFont.Bold))
        form_layout.addWidget(run_label)
        
        # Dropdown to select an existing run
        self.runs_dropdown = QComboBox()
        self.runs_dropdown.addItem("Select Run")
        self.runs_dropdown.currentTextChanged.connect(self.on_run_selected)
        form_layout.addWidget(self.runs_dropdown)
        
        # Add reload button right after the dropdown
        self.reload_run_btn = QPushButton("Reload Run")
        self.reload_run_btn.setFont(QFont("Arial", 10))
        self.reload_run_btn.clicked.connect(self.reload_current_run)
        form_layout.addWidget(self.reload_run_btn)
        
        form_layout.addStretch()
        
        # Button to create a new run
        self.create_run_btn = QPushButton("Create New Run")
        self.create_run_btn.setFont(QFont("Arial", 10))
        self.create_run_btn.clicked.connect(self.create_run)
        form_layout.addWidget(self.create_run_btn)
        
        # Button to sync Google Drive data
        self.google_drive_btn = QPushButton("Sync Google Drive")
        self.google_drive_btn.setFont(QFont("Arial", 10))
        self.google_drive_btn.clicked.connect(self.sync_google_drive)
        form_layout.addWidget(self.google_drive_btn)
        
        # Add Update Monet Data button
        self.update_monet_btn = QPushButton("Update Monet Data")
        self.update_monet_btn.setFont(QFont("Arial", 10))
        self.update_monet_btn.clicked.connect(self.update_monet_data)
        form_layout.addWidget(self.update_monet_btn)
        
        layout.addWidget(form_container)
        
        # Table for listing wells in the selected run
        self.wells_table = QTableWidget(0, 8)  # Changed from 9 to 8 columns (removed Cluster)
        self.wells_table.setHorizontalHeaderLabels([
            "Transducer", "Manual", "Well Number", "CAE", "Well Field",  
            "Last WL Reading", "Last Manual Reading", "Notes"
        ])
        
        # Set size policy to expand
        self.wells_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set column widths
        header = self.wells_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Transducer column
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Manual column
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Well Number
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # CAE
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Well Field
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Last WL Reading
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Last Manual Reading
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Notes
        
        self.wells_table.setColumnWidth(0, 50)  # Transducer column width
        self.wells_table.setColumnWidth(1, 50)  # Manual column width
        self.wells_table.hide()  # Initially hidden until a run is selected
        
        # Create a tab widget to hold the table and the map view
        self.tab_widget = QTabWidget()
        
        # Create table tab and add the wells table
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        table_layout.addWidget(self.wells_table)
        self.tab_widget.addTab(table_tab, "Wells Table")
        
        # Create map tab with folium map
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)
        
        # Create QWebEngineView for the map
        self.map_view = QWebEngineView()
        self.map_view.setMinimumHeight(400)
        map_layout.addWidget(self.map_view)
        
        # Initialize the map centered on Memphis
        self.init_map()
        
        self.tab_widget.addTab(map_tab, "Map")
        
        # Add the tab widget to the main layout so it fills available vertical space
        layout.addWidget(self.tab_widget, 1)
        
        # Add stretch to push everything to the top
        layout.addStretch()


    def create_run(self):
        """Create a new run with selected wells."""
        # Add debugging info at the beginning of the method
        logger.info("Starting create_run method")

        # First get the start date
        date_dialog = QDialog(self)
        date_dialog.setWindowTitle("Select Run Start Date")
        date_layout = QVBoxLayout(date_dialog)
        
        date_form = QHBoxLayout()
        date_label = QLabel("Starting Date:")
        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_form.addWidget(date_label)
        date_form.addWidget(date_edit)
        date_layout.addLayout(date_form)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(date_dialog.accept)
        button_box.rejected.connect(date_dialog.reject)
        date_layout.addWidget(button_box)
        
        if date_dialog.exec_() == QDialog.Accepted:
            start_date = date_edit.date()
            base_run_id = start_date.toString("yyyy-MM")
            run_id = base_run_id
            count = 2
            while run_id in self.runs:
                run_id = f"{base_run_id} ({count})"
                count += 1
            
            # Now show well selection dialog
            well_dialog = WellSelectionDialog(self.db_manager, self)
            if well_dialog.exec_() == QDialog.Accepted and well_dialog.selected_wells:
                try:
                    # Create directory for the run in temp directory
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', run_id)
                    os.makedirs(run_dir, exist_ok=True)
                    logger.info(f"Created run directory: {run_dir}")
                    
                    # Create run data
                    run_data = {
                        "runs": [{
                            "id": run_id,
                            "start_date": start_date.toString("yyyy-MM-dd"),
                            "end_date": (start_date.addMonths(1).addDays(-1)).toString("yyyy-MM-dd"),
                            "well_status": {}
                        }]
                    }
                    
                    # Create wells_data
                    wells_data = {}
                    for well in well_dialog.selected_wells:
                        # Add well to run status with new structure
                        run_data["runs"][0]["well_status"][well['well_number']] = {
                            "visited": False,
                            "tranducer_data_date": None,
                            "tranducer_record": None,
                            "manual_data_date": None,
                            "manual_record": None
                        }
                        
                        # Parse last readings for wells_data
                        last_wl = "No data"
                        last_manual = "No data"
                        
                        if well['last_wl'] != "No data":
                            last_wl = {
                                "date": well['last_wl'].split(" | ")[0],
                                "level": float(well['last_wl'].split(" | ")[1].replace(" ft", "")),
                                "temperature": float(well['last_wl'].split(" | ")[2].replace("T: ", "").replace("°C", "")),
                                "source": well['last_wl'].split(" | ")[3]
                            }
                        
                        if well['last_manual'] != "No data":
                            last_manual = {
                                "date": well['last_manual'].split(" | ")[0],
                                "level": float(well['last_manual'].split(" | ")[1].replace(" ft", "")),
                                "dtw": float(well['last_manual'].split(" | ")[2].replace("DTW: ", "").replace(" ft", "")),
                                "collector": well['last_manual'].split(" | ")[3].replace("By: ", "")
                            }
                        
                        # Add well to wells_data
                        wells_data[well['well_number']] = {
                            "cae_number": well['cae'],
                            "well_field": well['well_field'],
                            "cluster": well['cluster'],
                            "parking_instructions": "Park in gravel lot north of well",
                            "access_requirements": "Key #123 required",
                            "safety_notes": "Beware of snakes in summer",
                            "special_instructions": "Contact property owner 24h before visit",
                            "last_visit": None,
                            "last_measured_level": None,
                            "last_wl_reading": last_wl,
                            "last_manual_reading": last_manual
                        }
                    
                    # Save the JSON files
                    with open(os.path.join(run_dir, 'water_level_run.json'), 'w') as f:
                        json.dump(run_data, f, indent=4)
                    
                    with open(os.path.join(run_dir, 'wells_data.json'), 'w') as f:
                        json.dump(wells_data, f, indent=4)

                    # Update local UI first
                    self.runs[run_id] = well_dialog.selected_wells
                    if run_id not in [self.runs_dropdown.itemText(i) for i in range(self.runs_dropdown.count())]:
                        self.runs_dropdown.addItem(run_id)
                    self.runs_dropdown.setCurrentText(run_id)
                    
                    # Now that files exist, update display
                    self.display_run_wells(run_id)
                    self.update_map_markers(run_id)

                    # After creating files but before uploading
                    try:
                        # Debug print to confirm we're getting here
                        logger.info(f"About to call upload_run_to_drive for {run_id}")
                        success = self.upload_run_to_drive(run_id)
                        logger.info(f"upload_run_to_drive returned {success}")
                        if not success:
                            QMessageBox.warning(
                                self,
                                "Upload Warning",
                                f"The run was created locally but could not be uploaded to Google Drive.\n"
                                f"Please check your connection and try syncing later."
                            )
                    except Exception as e:
                        # More detailed error logging
                        logger.error(f"Exception during upload: {e}")
                        logger.error(f"Traceback: {traceback.format_exc()}")

                    logger.info(f"Created new run {run_id} and saved data files")

                except Exception as e:
                    logger.error(f"Error creating run: {e}")
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to create run: {str(e)}"
                    )

    def on_run_selected(self, run_id):
        if (run_id and run_id != "Select Run"):
            self.current_run_id = run_id
            
            # Create a single progress dialog for the entire process
            main_window = self.window()
            progress_handler = None
            if hasattr(main_window, 'progress_dialog_handler'):
                progress_handler = main_window.progress_dialog_handler
                progress_handler.start_progress("Processing Run Data", "Initializing...", 0, 100)
            
            # Process the run data with the single progress handler
            self.process_run_data(run_id, progress_handler)
            
            # Now display the run data (this will use the updated JSON files)
            self.display_run_wells(run_id)
            self.update_map_markers(run_id)
            
            # Close the progress dialog if it was created
            if progress_handler:
                progress_handler.finish()
        else:
            self.current_run_id = None
            self.wells_table.hide()
            self.wells_table.setRowCount(0)
            self.init_map()  # Reset map to initial state

    def process_run_data(self, run_id, progress_handler=None):
        """Process the run data for the selected run: check for XLE files, update manual readings, and upload changes."""
        try:
            # Create a progress dialog if we don't have an external handler
            progress_dialog = None
            if not progress_handler:
                progress_dialog = QProgressDialog("Updating run data...", None, 0, 100, self)
                progress_dialog.setWindowModality(Qt.WindowModal)
                progress_dialog.setMinimumDuration(500)
                progress_dialog.setValue(10)
            else:
                # Use the provided progress handler
                progress_handler.update_progress(10, "Processing run data...")
            
            # Step 1: Check for transducer data in Google Drive
            if progress_handler:
                progress_handler.update_progress(20, "Checking Google Drive for transducer data...")
            elif progress_dialog:
                progress_dialog.setLabelText("Checking Google Drive for transducer data...")
                progress_dialog.setValue(20)
            
            # Call the Google Drive check method with the progress handler/dialog
            self.check_google_drive_silent(run_id, progress_handler, progress_dialog)
            
            # Step 2: Check for manual readings in database
            if progress_handler:
                progress_handler.update_progress(60, "Checking database for manual readings...")
            elif progress_dialog:
                progress_dialog.setLabelText("Checking database for manual readings...")
                progress_dialog.setValue(60)
            
            # Call the existing manual readings update method
            self.update_manual_readings_status(run_id)
            
            # Step 3: Upload updated JSON to Google Drive
            if progress_handler:
                progress_handler.update_progress(80, "Uploading updated run data to Google Drive...")
            elif progress_dialog:
                progress_dialog.setLabelText("Uploading updated run data to Google Drive...")
                progress_dialog.setValue(80)
            
            # Upload the run data to Google Drive
            success = self.upload_run_to_drive(run_id)
            if not success:
                logger.warning(f"Failed to upload updated run data for {run_id} to Google Drive")
            
            # Complete the progress
            if progress_handler:
                progress_handler.update_progress(100, "Processing complete")
            elif progress_dialog:
                progress_dialog.setValue(100)
                progress_dialog.close()
            
        except Exception as e:
            logger.error(f"Error processing run data: {e}", exc_info=True)
            if 'progress_dialog' in locals() and progress_dialog:
                progress_dialog.close()
            if progress_handler:
                progress_handler.finish()
            QMessageBox.warning(self, "Error", f"Error processing run data: {str(e)}")

    def check_google_drive_silent(self, run_id, progress_handler=None, progress_dialog=None):
        """Silent version of check_google_drive that doesn't show UI progress or dialogs."""
        try:
            # Get settings from main window
            main_window = self.window()
            
            # Get the existing authenticated drive service from main window
            if hasattr(main_window, 'drive_service') and main_window.drive_service.authenticated:
                # Use the already authenticated service
                service = main_window.drive_service.get_service()
                
                # Set the authenticated service in the runs_monitor
                self.runs_monitor.set_authenticated_service(service)
                
                logger.debug("Using existing authenticated Google Drive service")
            else:
                # Fall back to separate authentication if needed
                if not hasattr(main_window, 'settings_handler'):
                    logger.warning("Settings handler not found")
                    return False
                
                settings_handler = main_window.settings_handler
                client_secret_path = settings_handler.get_setting("google_drive_secret_path")
                
                # Authenticate (this is the part that's failing)
                if not self.runs_monitor.authenticate(client_secret_path):
                    logger.warning("Failed to authenticate with Google Drive")
                    return False
            
            # Update progress to show we're retrieving data
            if progress_handler:
                progress_handler.update_progress(30, "Retrieving data from Google Drive...")
            elif progress_dialog:
                progress_dialog.setLabelText("Retrieving data from Google Drive...")
                progress_dialog.setValue(30)
            
            # Get year and month from run ID (e.g., "2025-02")
            year_month = run_id.split()[0]  # Gets "2025-02"
            
            # Get latest readings from drive
            latest_readings = self.runs_monitor.get_latest_readings(year_month)
            
            # Update progress to show we're processing the data
            if progress_handler:
                progress_handler.update_progress(40, "Processing transducer data...")
            elif progress_dialog:
                progress_dialog.setLabelText("Processing transducer data...")
                progress_dialog.setValue(40)
            
            # Update with the new data
            self.update_table_with_readings(latest_readings)
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking Google Drive silently: {e}", exc_info=True)
            return False

    def display_run_wells(self, run_id):
        if run_id in self.runs:
            wells = self.runs[run_id]
            self.wells_table.setRowCount(len(wells))
            
            # Try to load the JSON file to get status information from temp directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', run_id)
            run_json_path = os.path.join(run_dir, 'water_level_run.json')
            
            try:
                if os.path.exists(run_json_path):
                    with open(run_json_path, 'r') as f:
                        run_data = json.load(f)
                else:
                    # JSON file doesn't exist, continue with basic display (cloud-only mode)
                    logger.info(f"Run JSON file not found: {run_json_path} - using cloud-only mode")
                    run_data = None
                    
                for row, well in enumerate(wells):
                    well_number = well['well_number']
                    
                    # Handle cloud-only mode where run_data is None
                    if run_data:
                        well_status = run_data['runs'][0]['well_status'].get(well_number, {})
                    else:
                        # Default empty status for cloud-only mode
                        well_status = {}
                    
                    # Determine transducer status color based on JSON data
                    transducer_color = "red"  # Default color
                    if well_status.get('tranducer_data_date') is not None:
                        transducer_color = "green"
                        
                    # Create and set transducer status icon
                    transducer_item = QTableWidgetItem()
                    transducer_item.setIcon(self.create_flag_icon(transducer_color))
                    transducer_item.setTextAlignment(Qt.AlignCenter)
                    transducer_item.setData(Qt.UserRole, transducer_color)
                    self.wells_table.setItem(row, 0, transducer_item)
                    
                    # Determine manual reading status color based on JSON data
                    manual_color = "red"  # Default color
                    if well_status.get('manual_data_date') is not None:
                        manual_color = "green"
                        
                    # Create and set manual reading status icon
                    manual_item = QTableWidgetItem()
                    manual_item.setIcon(self.create_flag_icon(manual_color))
                    manual_item.setTextAlignment(Qt.AlignCenter)
                    manual_item.setData(Qt.UserRole, manual_color)
                    self.wells_table.setItem(row, 1, manual_item)
                    
                    # Set well information
                    self.wells_table.setItem(row, 2, QTableWidgetItem(well_number))  # Well Number
                    self.wells_table.setItem(row, 3, QTableWidgetItem(well['cae']))  # CAE
                    self.wells_table.setItem(row, 4, QTableWidgetItem(well['well_field']))  # Well Field
                    # Removed cluster column (was at index 5)

                    # Update WL reading display if transducer data is present in JSON
                    if well_status.get('tranducer_data_date') is not None:
                        # Format date more nicely for display
                        date_str = well_status.get('tranducer_data_date')
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            local_dt = date_obj.strftime('%Y-%m-%d %I:%M %p')
                            wl_text = f"{local_dt} | From XLE file"
                            self.wells_table.setItem(row, 5, QTableWidgetItem(wl_text))  # Column index adjusted
                        except Exception as e:
                            logger.error(f"Error formatting date {date_str}: {e}")
                            self.wells_table.setItem(row, 5, QTableWidgetItem(well['last_wl']))  # Column index adjusted
                    else:
                        # Use default text if no transducer data
                        self.wells_table.setItem(row, 5, QTableWidgetItem(well['last_wl']))  # Column index adjusted
                    
                    # Update Manual reading display if manual data is present in JSON
                    if well_status.get('manual_data_date') is not None and well_status.get('manual_record') is not None:
                        # Format date more nicely for display
                        date_str = well_status.get('manual_data_date')
                        manual_record = well_status.get('manual_record', {})
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            local_dt = date_obj.strftime('%Y-%m-%d %I:%M %p')
                            
                            # Safely convert values to float, defaulting to 0 if conversion fails
                            try:
                                water_level = float(manual_record.get('water_level', 0))
                            except (ValueError, TypeError):
                                water_level = 0.0
                                
                            try:
                                dtw_avg = float(manual_record.get('dtw_avg', 0))
                            except (ValueError, TypeError):
                                dtw_avg = 0.0
                            
                            manual_text = (f"{local_dt} | "
                                         f"{water_level:.2f} ft | "
                                         f"DTW: {dtw_avg:.2f} ft | By: {manual_record.get('collected_by', 'Unknown')}")
                            self.wells_table.setItem(row, 6, QTableWidgetItem(manual_text))  # Column index adjusted
                        except Exception as e:
                            logger.error(f"Error formatting manual data for {well_number}: {e}")
                            self.wells_table.setItem(row, 6, QTableWidgetItem(well['last_manual']))  # Column index adjusted
                    else:
                        # Use default text if no manual data
                        self.wells_table.setItem(row, 6, QTableWidgetItem(well['last_manual']))  # Column index adjusted
                    
                    # Set notes column
                    self.wells_table.setItem(row, 7, QTableWidgetItem(well['notes']))  # Column index adjusted
                    
                self.wells_table.show()
                
                # After populating table, resize columns to content
                self.wells_table.resizeColumnsToContents()
                
                # Then ensure minimum widths for fixed columns
                if self.wells_table.columnWidth(0) < 50:
                    self.wells_table.setColumnWidth(0, 50)  # Min width for transducer column
                if self.wells_table.columnWidth(1) < 50:
                    self.wells_table.setColumnWidth(1, 50)  # Min width for manual column
                    
            except Exception as e:
                logger.error(f"Error loading run data from JSON: {e}", exc_info=True)
                
                # Fall back to the old display method if JSON read fails
                for row, well in enumerate(wells):
                    # Transducer status (red for now)
                    transducer_item = QTableWidgetItem()
                    transducer_item.setIcon(self.create_flag_icon("red"))
                    transducer_item.setTextAlignment(Qt.AlignCenter)
                    transducer_item.setData(Qt.UserRole, "red")
                    self.wells_table.setItem(row, 0, transducer_item)
                    
                    # Manual reading status (red for now)
                    manual_item = QTableWidgetItem()
                    manual_item.setIcon(self.create_flag_icon("red"))
                    manual_item.setTextAlignment(Qt.AlignCenter)
                    manual_item.setData(Qt.UserRole, "red")
                    self.wells_table.setItem(row, 1, manual_item)
                    
                    # Set the rest of the columns - with adjusted indices due to removed cluster column
                    self.wells_table.setItem(row, 2, QTableWidgetItem(well['well_number']))  # Well Number
                    self.wells_table.setItem(row, 3, QTableWidgetItem(well['cae']))         # CAE
                    self.wells_table.setItem(row, 4, QTableWidgetItem(well['well_field']))  # Well Field
                    # Removed cluster column
                    self.wells_table.setItem(row, 5, QTableWidgetItem(well['last_wl']))     # Last WL Reading
                    self.wells_table.setItem(row, 6, QTableWidgetItem(well['last_manual'])) # Last Manual Reading
                    self.wells_table.setItem(row, 7, QTableWidgetItem(well['notes']))       # Notes
                
                self.wells_table.show()
                self.wells_table.resizeColumnsToContents()
                
                # Skip manual readings status update in fallback mode to avoid recursive errors
                # when local storage is unavailable
                logger.info("Skipping manual readings status update in fallback mode")

    def load_existing_runs(self):
        """Load existing runs from both local storage and cloud storage"""
        logger.info("Loading existing runs from local and cloud sources...")
        
        # Clear existing runs first
        self.runs.clear()
        self.cloud_runs.clear()
        self.runs_dropdown.clear()
        self.runs_dropdown.addItem("Select Run")
        
        # Load local runs first
        self._load_local_runs()
        
        # Load cloud runs if available
        self._load_cloud_runs()
        
        logger.info(f"Loaded {len(self.runs)} total runs")
    
    def _load_local_runs(self):
        """Load runs from local data/runs/ directory"""
        base_dir = os.path.join('data', 'runs')
        if not os.path.exists(base_dir):
            logger.debug("Local runs directory does not exist")
            return

        logger.debug(f"Loading local runs from: {base_dir}")
        
        # Iterate over all run directories (each folder name corresponds to a run ID)
        for run_id in os.listdir(base_dir):
            run_dir = os.path.join(base_dir, run_id)
            if os.path.isdir(run_dir):
                self._load_run_from_local_directory(run_id, run_dir)
    
    def _load_cloud_runs(self):
        """Load runs from cloud WATER_LEVEL_RUNS structure"""
        try:
            # Check if we have Google Drive access and a current project
            main_window = self.window()
            if not (hasattr(main_window, 'drive_service') and main_window.drive_service.authenticated):
                logger.debug("Google Drive not available for cloud runs loading")
                return
            
            # Get current project context from database manager
            if not (hasattr(main_window, 'db_manager') and main_window.db_manager.is_cloud_database):
                logger.debug("No cloud database selected, skipping cloud runs loading")
                return
            
            project_name = getattr(main_window.db_manager, 'cloud_project_name', None)
            if not project_name:
                logger.debug("No project name available for cloud runs loading")
                return
            
            logger.info(f"Loading cloud runs for project: {project_name}")
            
            # Get Google Drive service
            service = main_window.drive_service.get_service()
            
            # Find the project's WATER_LEVEL_RUNS folder
            runs_folder_id = self._find_project_runs_folder(service, project_name)
            if not runs_folder_id:
                logger.info(f"No WATER_LEVEL_RUNS folder found for project {project_name}")
                return
            
            # Load runs from the cloud folder
            self._load_runs_from_cloud_folder(service, runs_folder_id)
            
        except Exception as e:
            logger.error(f"Error loading cloud runs: {e}")
    
    def _find_project_runs_folder(self, service, project_name):
        """Find the WATER_LEVEL_RUNS folder for a specific project"""
        try:
            # Get main water_levels_monitoring folder
            main_folder_id = self.window().settings_handler.get_setting("google_drive_folder_id")
            if not main_folder_id:
                return None
            
            # Find Projects folder
            query = f"'{main_folder_id}' in parents and name='Projects' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            projects_folders = results.get('files', [])
            
            if not projects_folders:
                logger.debug("Projects folder not found")
                return None
            
            projects_folder_id = projects_folders[0]['id']
            
            # Find specific project folder
            query = f"'{projects_folder_id}' in parents and name='{project_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            project_folders = results.get('files', [])
            
            if not project_folders:
                logger.debug(f"Project folder '{project_name}' not found")
                return None
            
            project_folder_id = project_folders[0]['id']
            
            # Find WATER_LEVEL_RUNS folder
            query = f"'{project_folder_id}' in parents and name='WATER_LEVEL_RUNS' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            runs_folders = results.get('files', [])
            
            if not runs_folders:
                logger.debug(f"WATER_LEVEL_RUNS folder not found in project {project_name}")
                return None
            
            runs_folder_id = runs_folders[0]['id']
            logger.info(f"Found WATER_LEVEL_RUNS folder for {project_name}: {runs_folder_id}")
            return runs_folder_id
            
        except Exception as e:
            logger.error(f"Error finding project runs folder: {e}")
            return None
    
    def _load_runs_from_cloud_folder(self, service, runs_folder_id):
        """Load individual run folders from the cloud WATER_LEVEL_RUNS folder"""
        try:
            # Get all run folders (should be named like 2025-01, 2025-02, etc.)
            query = f"'{runs_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id, name)", orderBy="name").execute()
            run_folders = results.get('files', [])
            
            logger.info(f"Found {len(run_folders)} run folders in cloud")
            
            for folder in run_folders:
                run_id = folder['name']
                folder_id = folder['id']
                
                # Download and process the run
                self._load_run_from_cloud_folder(service, run_id, folder_id)
                
        except Exception as e:
            logger.error(f"Error loading runs from cloud folder: {e}")
    
    def _load_run_from_cloud_folder(self, service, run_id, folder_id):
        """Load a specific run from a cloud folder and cache it locally"""
        try:
            # Create local temp directory for the run (using same structure as update methods)
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_runs_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs')
            os.makedirs(temp_runs_dir, exist_ok=True)
            
            temp_run_dir = os.path.join(temp_runs_dir, run_id)
            os.makedirs(temp_run_dir, exist_ok=True)
            
            # Download and save JSON files from the cloud folder
            water_level_run_data = self._download_json_from_folder(service, folder_id, 'water_level_run.json')
            wells_data = self._download_json_from_folder(service, folder_id, 'wells_data.json')
            
            if water_level_run_data and wells_data:
                # Save to temp directory for local caching
                temp_run_file = os.path.join(temp_run_dir, 'water_level_run.json')
                temp_wells_file = os.path.join(temp_run_dir, 'wells_data.json')
                
                with open(temp_run_file, 'w') as f:
                    json.dump(water_level_run_data, f, indent=4)
                with open(temp_wells_file, 'w') as f:
                    json.dump(wells_data, f, indent=4)
                
                # Mark as cloud run with temp path
                self._process_run_data(run_id, water_level_run_data, wells_data, source="cloud", temp_path=temp_run_dir)
                logger.debug(f"Loaded and cached cloud run: {run_id}")
            else:
                logger.warning(f"Could not load complete data for cloud run: {run_id}")
                
        except Exception as e:
            logger.error(f"Error loading cloud run {run_id}: {e}")
    
    def _download_json_from_folder(self, service, folder_id, filename):
        """Download and parse a JSON file from a Google Drive folder"""
        try:
            # Find the file in the folder
            query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if not files:
                logger.debug(f"File {filename} not found in folder {folder_id}")
                return None
            
            file_id = files[0]['id']
            
            # Download the file content
            file_content = service.files().get_media(fileId=file_id).execute()
            
            # Parse JSON
            return json.loads(file_content.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error downloading {filename} from folder {folder_id}: {e}")
            return None
    
    def _load_run_from_local_directory(self, run_id, run_dir):
        """Load a run from a local directory"""
        water_level_run_file = os.path.join(run_dir, 'water_level_run.json')
        wells_data_file = os.path.join(run_dir, 'wells_data.json')
        
        if os.path.exists(water_level_run_file) and os.path.exists(wells_data_file):
            try:
                with open(water_level_run_file, 'r') as f:
                    run_data = json.load(f)
                with open(wells_data_file, 'r') as f:
                    wells_data = json.load(f)
                
                self._process_run_data(run_id, run_data, wells_data, source="local")
                logger.debug(f"Loaded local run: {run_id}")
                
            except Exception as e:
                logger.error(f"Error loading local run {run_id}: {e}")
    
    def _process_run_data(self, run_id, run_data, wells_data, source="unknown", temp_path=None):
        """Process run data and add to runs dictionary"""
        try:
            # Extract well IDs from the run JSON
            run_details = run_data["runs"][0]
            well_list = []
            
            for well_number in run_details["well_status"]:
                if well_number in wells_data:
                    data = wells_data[well_number]

                    if isinstance(data.get("last_wl_reading"), dict):
                        last_wl = f"{data['last_wl_reading'].get('date', '')} | {data['last_wl_reading'].get('level', 0):.2f} ft | T: {data['last_wl_reading'].get('temperature', 0):.1f}°C | {data['last_wl_reading'].get('source', '')}"
                    else:
                        last_wl = "No data"

                    if isinstance(data.get("last_manual_reading"), dict):
                        last_manual = f"{data['last_manual_reading'].get('date', '')} | {data['last_manual_reading'].get('level', 0):.2f} ft | DTW: {data['last_manual_reading'].get('dtw', 0):.2f} ft | By: {data['last_manual_reading'].get('collector', '')}"
                    else:
                        last_manual = "No data"

                    well_dict = {
                        "well_number": well_number,
                        "cae": data.get("cae_number", "N/A"),
                        "well_field": data.get("well_field", "N/A"),
                        "cluster": data.get("cluster", "N/A"),
                        "last_wl": last_wl,
                        "last_manual": last_manual,
                        "notes": f"Source: {source}"
                    }
                    well_list.append(well_dict)

            # Store the well list in the runs dictionary and add to dropdown if not already present
            self.runs[run_id] = well_list
            
            # Track cloud runs with their temp paths
            if source == "cloud" and temp_path:
                self.cloud_runs[run_id] = temp_path
            
            if run_id not in [self.runs_dropdown.itemText(i) for i in range(self.runs_dropdown.count())]:
                self.runs_dropdown.addItem(run_id)
                
        except Exception as e:
            logger.error(f"Error processing run data for {run_id}: {e}") 

    def sync_run_to_cloud(self, run_id):
        """Sync a run's changes back to cloud storage if it's a cloud run"""
        try:
            # Check if this is a cloud run
            if run_id not in self.cloud_runs:
                logger.debug(f"Run {run_id} is not a cloud run, skipping cloud sync")
                return True
            
            temp_path = self.cloud_runs[run_id]
            
            # Check if temp files exist and are newer than some threshold
            # For now, always sync when called
            temp_run_file = os.path.join(temp_path, 'water_level_run.json')
            temp_wells_file = os.path.join(temp_path, 'wells_data.json')
            
            if not (os.path.exists(temp_run_file) and os.path.exists(temp_wells_file)):
                logger.warning(f"Temp files missing for cloud run {run_id}, cannot sync")
                return False
            
            # Get main window to access drive handler
            main_window = self.window()
            if hasattr(main_window, 'drive_data_handler') and main_window.drive_data_handler:
                logger.info(f"Syncing run {run_id} changes to cloud...")
                
                # Copy temp files to data/runs directory temporarily for upload
                local_run_dir = os.path.join('data', 'runs', run_id)
                os.makedirs(local_run_dir, exist_ok=True)
                
                import shutil
                shutil.copy2(temp_run_file, os.path.join(local_run_dir, 'water_level_run.json'))
                shutil.copy2(temp_wells_file, os.path.join(local_run_dir, 'wells_data.json'))
                
                # Upload to cloud
                success = main_window.drive_data_handler.upload_run_folder(run_id)
                
                if success:
                    logger.info(f"Successfully synced run {run_id} to cloud")
                else:
                    logger.warning(f"Failed to sync run {run_id} to cloud")
                
                return success
            else:
                logger.debug("No Google Drive data handler available for cloud sync")
                return True  # Return True for cloud-only mode
            
        except Exception as e:
            logger.error(f"Error syncing run {run_id} to cloud: {e}")
            return False

    def init_map(self):
        """Initialize the folium map centered on Memphis"""
        memphis_coords = [35.1495, -90.0490]
        self.folium_map = folium.Map(
            location=memphis_coords,
            zoom_start=10,
            tiles='OpenStreetMap'
        )
        
        # Save map to temporary HTML file with unique name
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        map_path = os.path.join(temp_dir, f"water_level_map_{timestamp}.html")
        self.folium_map.save(map_path)
        
        # Connect loadFinished to ensure QWebChannel is loaded if needed
        self.map_view.loadFinished.connect(self._on_map_loaded)
        
        # Display the map
        self.map_view.setUrl(QUrl.fromLocalFile(map_path))
        
    def _on_map_loaded(self, ok):
        """Handle map load completion and ensure QWebChannel is loaded."""
        if ok:
            try:
                # Disconnect to avoid multiple connections
                self.map_view.loadFinished.disconnect(self._on_map_loaded)
            except TypeError:
                # Ignore if not connected
                pass
                
            # Inject QWebChannel library if needed (for future use)
            # This prevents "QWebChannel is not defined" errors
            self._inject_qwebchannel_if_needed()
    
    def _inject_qwebchannel_if_needed(self):
        """Inject the QWebChannel JavaScript library if needed."""
        try:
            from PyQt5.QtCore import QFile, QIODevice
            
            # Check if the page already has QWebChannel defined
            check_js = "typeof QWebChannel !== 'undefined'"
            self.map_view.page().runJavaScript(check_js, self._handle_qwebchannel_check)
        except Exception as e:
            logger.error(f"Error checking for QWebChannel: {e}")
    
    def _handle_qwebchannel_check(self, qwebchannel_exists):
        """Handle the result of checking if QWebChannel exists."""
        if not qwebchannel_exists:
            try:
                # Find the qwebchannel.js file from PyQt resources
                from PyQt5.QtCore import QFile, QIODevice
                qwebchannel_js = QFile(':/qtwebchannel/qwebchannel.js')
                if qwebchannel_js.open(QIODevice.ReadOnly):
                    # Read the JavaScript content
                    js_bytes = qwebchannel_js.readAll()
                    js_string = str(js_bytes, 'utf-8')
                    qwebchannel_js.close()
                    
                    # Inject the QWebChannel library JavaScript
                    self.map_view.page().runJavaScript(js_string)
                    logger.debug("Injected QWebChannel JavaScript library in runs tab")
            except Exception as e:
                logger.error(f"Error injecting QWebChannel JS: {e}")

    def update_map_markers(self, run_id):
        """Update map markers based on well status"""
        if not run_id or run_id == "Select Run":
            return
        
        # Clear existing markers
        self.init_map()
        
        # Get well coordinates and status from database
        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                wells_query = """
                    SELECT well_number, latitude, longitude
                    FROM wells
                    WHERE well_number IN ({})
                """.format(','.join(['?'] * len(self.runs[run_id])))
                
                well_numbers = [well['well_number'] for well in self.runs[run_id]]
                wells_df = pd.read_sql(wells_query, conn, params=well_numbers)
                
                # Load current run status from temp directory
                import tempfile
                temp_dir = tempfile.gettempdir()
                run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', run_id)
                
                # Check if files exist in temp directory, if not skip map update
                run_json_path = os.path.join(run_dir, 'water_level_run.json')
                wells_json_path = os.path.join(run_dir, 'wells_data.json')
                
                if not (os.path.exists(run_json_path) and os.path.exists(wells_json_path)):
                    logger.info(f"Run data not available in temp directory for {run_id} - skipping map update")
                    return
                
                with open(run_json_path, 'r') as f:
                    run_data = json.load(f)
                with open(wells_json_path, 'r') as f:
                    wells_data = json.load(f)
                
                # Add markers for each well
                for _, well in wells_df.iterrows():
                    well_number = well['well_number']
                    well_status = run_data['runs'][0]['well_status'].get(well_number, {})
                    well_info = wells_data.get(well_number, {})
                    
                    # Set default colors to red (warning)
                    transducer_color = '#e63946'  # Default to red
                    manual_color = '#e63946'      # Default to red
                    
                    # Find the corresponding row in the table to get status colors
                    for row in range(self.wells_table.rowCount()):
                        if self.wells_table.item(row, 2).text() == well_number:
                            # Get the icons from the table
                            transducer_item = self.wells_table.item(row, 0)
                            manual_item = self.wells_table.item(row, 1)
                            
                            # Get the stored color names (defaulting to "red" if not set)
                            trans_color_name = transducer_item.data(Qt.UserRole) if transducer_item.data(Qt.UserRole) else "red"
                            manual_color_name = manual_item.data(Qt.UserRole) if manual_item.data(Qt.UserRole) else "red"
                            
                            # Map color names to hex colors
                            transducer_color = '#28a745' if trans_color_name == "green" else '#e63946'
                            manual_color = '#28a745' if manual_color_name == "green" else '#e63946'
                            
                            break
                    
                    # Create HTML for a pin using SVG triangles (flipped to point down)
                    html_content = f"""
                        <div style="position: relative; text-align: center;">
                            <svg width="40" height="40" viewBox="0 0 40 40">
                                <!-- Left triangle (transducer status) -->
                                <path d="M20 38 L2 2 L20 2 Z" 
                                    fill="{transducer_color}" 
                                    stroke="black" 
                                    stroke-width="1" />
                                
                                <!-- Right triangle (manual status) -->
                                <path d="M20 38 L38 2 L20 2 Z" 
                                    fill="{manual_color}" 
                                    stroke="black" 
                                    stroke-width="1" />
                                    
                                <!-- Center line to clearly separate the triangles -->
                                <line x1="20" y1="2" x2="20" y2="38" 
                                    stroke="black" 
                                    stroke-width="0.5" />
                            </svg>
                            <div style="position: absolute; width: 100%; text-align: center; top: 40px; 
                                      font-size: 12px; font-weight: bold; color: black; 
                                      text-shadow: -1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white;">
                                {well_info.get('cae_number', 'N/A')}
                            </div>
                        </div>
                    """
                    
                    # Create a DivIcon with the HTML content
                    icon = folium.DivIcon(
                        icon_size=(40, 40),
                        icon_anchor=(20, 38),  # Bottom center of the pin
                        popup_anchor=(0, -20),  # Center above the pin
                        html=html_content,
                        class_name="custom-pin"  # This removes the default leaflet-div-icon class styling
                    )
                    
                    # Format transducer data for popup - modified to show only date
                    transducer_text = "No data"
                    if well_status.get('tranducer_data_date'):
                        try:
                            date_obj = datetime.strptime(well_status['tranducer_data_date'], '%Y-%m-%d %H:%M:%S')
                            # Modified to show only date without time
                            transducer_text = f"{date_obj.strftime('%Y-%m-%d')} | From XLE file"
                        except:
                            transducer_text = well_status['tranducer_data_date']
                    
                    # Format manual reading data for popup - modified to show only date
                    manual_text = "No data"
                    if well_status.get('manual_data_date') and well_status.get('manual_record'):
                        try:
                            date_obj = datetime.strptime(well_status['manual_data_date'], '%Y-%m-%d %H:%M:%S')
                            manual_record = well_status['manual_record']
                            # Modified to show only date without time
                            manual_text = (f"{date_obj.strftime('%Y-%m-%d')} | "
                                          f"{manual_record.get('water_level', 0):.2f} ft | "
                                          f"DTW: {manual_record.get('dtw', 0):.2f} ft")
                        except:
                            manual_text = well_status['manual_data_date']
                    
                    # Create popup content - removed Last Visit field and updated format
                    popup_html = f"""
                        <div style='width: 300px'>
                            <h4>{well_number}</h4>
                            <p><b>Status:</b> {'Visited' if well_status.get('visited', False) else 'Pending'}</p>
                            <p><b>Last WL Reading:</b> {transducer_text}</p>
                            <p><b>Last Manual Reading:</b> {manual_text}</p>
                        </div>
                    """
                    
                    # Add marker to map
                    folium.Marker(
                        location=[well['latitude'], well['longitude']],
                        popup=folium.Popup(popup_html, max_width=350),
                        icon=icon
                    ).add_to(self.folium_map)
                
                # Update the map view with unique temp file
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time())
                temp_map_path = os.path.join(temp_dir, f"water_level_map_{timestamp}.html")
                self.folium_map.save(temp_map_path)
                self.map_view.setUrl(QUrl.fromLocalFile(temp_map_path))
                
        except Exception as e:
            logger.error(f"Error updating map markers: {e}")

    def sync_google_drive(self):
        """Sync Google Drive field data and refresh runs"""
        logger.info("Starting Google Drive sync operation")
            
        try:
            from ..dialogs.water_level_progress_dialog import WaterLevelProgressDialog
            
            # Show detailed progress dialog with logs
            progress_dialog = WaterLevelProgressDialog(self)
            progress_dialog.setWindowTitle("Google Drive Sync")
            progress_dialog.update_status("Initializing Google Drive sync...")
            progress_dialog.show()
            
            # Get main window
            main_window = self.window()
            
            # Check for authenticated drive service
            if hasattr(main_window, 'drive_service') and main_window.drive_service.authenticated:
                # Use the already authenticated service
                service = main_window.drive_service.get_service()
                
                # Set the authenticated service in the runs_monitor
                self.runs_monitor.set_authenticated_service(service)
                
                # Update progress
                progress_dialog.update_progress(20, 100)
                progress_dialog.update_status("Using existing Google Drive authentication...")
                progress_dialog.log_message("✓ Using existing authenticated Google Drive service")
            else:
                # Need to authenticate - this is the key addition
                progress_dialog.update_progress(10, 100)
                progress_dialog.update_status("Authenticating with Google Drive...")
                progress_dialog.log_message("Attempting to authenticate with Google Drive...")
                
                if not hasattr(main_window, 'settings_handler'):
                    progress_dialog.log_message("❌ Settings handler not found")
                    progress_dialog.finish_operation()
                    QMessageBox.warning(self, "Settings Not Found", "Google Drive settings not found.")
                    return
                    
                settings_handler = main_window.settings_handler
                client_secret_path = settings_handler.get_setting("google_drive_secret_path")
                
                # Authenticate Google Drive service
                if hasattr(main_window, 'drive_service'):
                    if not main_window.drive_service.authenticate(force=True):
                        progress_dialog.log_message("❌ Failed to authenticate with Google Drive")
                        progress_dialog.finish_operation()
                        QMessageBox.warning(self, "Authentication Failed", 
                                          "Failed to authenticate with Google Drive.")
                        return
                    
                    # Use the newly authenticated service
                    service = main_window.drive_service.get_service()
                    
                    # Set the authenticated service in the runs_monitor
                    self.runs_monitor.set_authenticated_service(service)
                    
                    # Update progress
                    progress_dialog.update_progress(20, 100)
                    progress_dialog.update_status("Successfully authenticated with Google Drive...")
                    progress_dialog.log_message("✓ Successfully authenticated with Google Drive")
                    
                    # Also initialize the data handler for future use
                    if hasattr(main_window, 'drive_data_handler') and main_window.drive_data_handler:
                        main_window.drive_data_handler.authenticate()
                else:
                    # Fall back to separate authentication
                    if not self.runs_monitor.authenticate(client_secret_path, force=True):
                        progress_dialog.log_message("❌ Failed to authenticate with Google Drive (fallback method)")
                        progress_dialog.finish_operation()
                        QMessageBox.warning(self, "Authentication Failed", 
                                          "Failed to authenticate with Google Drive.")
                        return
            
            # Step 1: Consolidate field data first
            progress_dialog.update_progress(30, 100)
            progress_dialog.update_status("Consolidating field data from laptops...")
            progress_dialog.log_message("Starting field data consolidation...")
            
            # Initialize the field data consolidator
            consolidator = FieldDataConsolidator(service, main_window.settings_handler)
            
            # Create a progress callback that logs to the dialog
            def consolidation_progress(message, percent):
                # Map consolidation progress (0-100) to our range (30-60)
                mapped_progress = 30 + int(percent * 0.3)
                progress_dialog.update_progress(mapped_progress, 100)
                progress_dialog.update_status(f"Field Data: {message}")
                progress_dialog.log_message(message)
            
            # Consolidate field data
            consolidation_success = consolidator.consolidate_field_data(consolidation_progress)
            
            if not consolidation_success:
                progress_dialog.log_message("⚠ Field data consolidation failed, continuing with existing data")
                logger.warning("Field data consolidation failed, continuing with existing data")
            else:
                progress_dialog.log_message("✓ Field data consolidation completed successfully")
            
            # Step 2: Update runs monitor to use consolidated folder
            progress_dialog.update_progress(60, 100)
            progress_dialog.update_status("Configuring data sources...")
            progress_dialog.log_message("Configuring runs monitor to use consolidated data...")
            
            # Get the consolidated folder ID and update runs monitor
            consolidated_folder_id = main_window.settings_handler.get_setting("consolidated_field_data_folder")
            logger.debug(f"Retrieved consolidated_field_data_folder from settings: {consolidated_folder_id}")
            logger.debug(f"Current runs_monitor.folder_id before update: {self.runs_monitor.folder_id}")
            if consolidated_folder_id:
                # Update the runs monitor to use the consolidated folder
                self.runs_monitor.folder_id = consolidated_folder_id
                progress_dialog.log_message(f"✓ Updated runs monitor to use consolidated folder: {consolidated_folder_id}")
                logger.info(f"Updated runs monitor to use consolidated folder: {consolidated_folder_id}")
                logger.debug(f"runs_monitor.folder_id after update: {self.runs_monitor.folder_id}")
            else:
                progress_dialog.log_message("⚠ Consolidated folder not found, using original folder")
                logger.warning("Consolidated folder not found, using original folder")
            
            # Step 3: Refresh runs list from cloud
            progress_dialog.update_progress(70, 100)
            progress_dialog.update_status("Refreshing runs from cloud...")
            progress_dialog.log_message("Loading existing runs from cloud structure...")
            
            # Reload runs to pick up any new cloud runs
            self.load_existing_runs()
            progress_dialog.log_message(f"✓ Loaded {len(self.runs)} runs from cloud")
            
            # Step 4: Update current run if one is selected
            latest_readings = {}
            if self.current_run_id:
                progress_dialog.update_progress(85, 100)
                progress_dialog.update_status("Updating current run data...")
                progress_dialog.log_message(f"Updating data for current run: {self.current_run_id}")
                
                # Get year and month from run ID (e.g., "2025-02") 
                year_month = self.current_run_id.split()[0]  # Gets "2025-02"
                
                # Get latest readings from the consolidated folder
                latest_readings = self.runs_monitor.get_latest_readings(year_month)
                progress_dialog.log_message(f"Found readings for {len(latest_readings)} locations")
                
                # Update the table with the new data and save to JSON
                self.update_table_with_readings(latest_readings)
                progress_dialog.log_message("✓ Updated table with latest readings")
            
            progress_dialog.update_progress(100, 100)
            progress_dialog.update_status("Sync completed successfully!")
            
            # Show completion message with consolidation info
            consolidation_msg = " (Field data consolidated)" if consolidation_success else " (Using existing field data)"
            runs_msg = f"Loaded {len(self.runs)} runs."
            readings_msg = f" Found readings for {len(latest_readings)} locations." if latest_readings else ""
            
            progress_dialog.log_message(f"✓ Sync complete: {runs_msg}{readings_msg}{consolidation_msg}")
            progress_dialog.finish_operation()
            
        except Exception as e:
            logger.error(f"Error syncing Google Drive: {e}")
            if 'progress_dialog' in locals():
                progress_dialog.log_message(f"❌ Error during sync: {str(e)}")
                progress_dialog.finish_operation()
            QMessageBox.critical(self, "Error", f"Failed to sync Google Drive: {str(e)}")

    def update_table_with_readings(self, latest_readings):
        """Update the table with the latest readings from Google Drive and update the JSON file"""
        if not self.current_run_id or not self.wells_table:
            return
            
        # Get current wells in the run
        wells = self.runs[self.current_run_id]
        
        # Log available readings for debugging
        logger.debug(f"Available readings in latest_readings: {list(latest_readings.keys())}")
        
        # Use temporary directory to avoid permission issues on macOS
        import tempfile
        
        # Try to use local storage in temp directory
        temp_dir = tempfile.gettempdir()
        run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', self.current_run_id)
        run_json_path = os.path.join(run_dir, 'water_level_run.json')
        
        logger.debug(f"Using temp run file at: {run_json_path}")
        
        # Try to ensure directory exists in temp directory
        local_storage_available = True
        if not os.path.exists(run_dir):
            try:
                logger.debug(f"Creating temp run directory: {run_dir}")
                os.makedirs(run_dir, exist_ok=True)
                logger.debug(f"Successfully created temp run directory: {run_dir}")
            except Exception as e:
                logger.warning(f"Cannot create temp run directory: {e}")
                logger.info("Continuing without local storage - using cloud-only mode")
                local_storage_available = False
        
        # Check if file exists, if not create a basic template (only if local storage is available)
        if local_storage_available and not os.path.exists(run_json_path):
            try:
                logger.warning(f"Run JSON file does not exist: {run_json_path}. Creating template.")
                # Create basic template for the run
                run_data = {
                    "runs": [{
                        "id": self.current_run_id,
                        "start_date": self.current_run_id.split()[0] + "-01",  # First day of month
                        "end_date": self.current_run_id.split()[0] + "-28",    # Approximate month end
                        "well_status": {}
                    }]
                }
                
                # Initialize well status for all wells in the run
                for well in wells:
                    run_data["runs"][0]["well_status"][well['well_number']] = {
                        "visited": False,
                        "tranducer_data_date": None,
                        "tranducer_record": None,
                        "manual_data_date": None,
                        "manual_record": None
                    }
                    
                # Save the initial template
                with open(run_json_path, 'w') as f:
                    json.dump(run_data, f, indent=4)
                    
            except Exception as e:
                logger.warning(f"Could not create local run template: {e}")
                local_storage_available = False
                
        # Only proceed with local file operations if storage is available
        if local_storage_available:
            # Also create an empty wells_data.json if it doesn't exist
            wells_data_path = os.path.join(run_dir, 'wells_data.json')
            if not os.path.exists(wells_data_path):
                try:
                    wells_data = {}
                    for well in wells:
                        wells_data[well['well_number']] = {
                            "cae_number": well['cae'],
                            "well_field": well['well_field'],
                            "cluster": well.get('cluster', "N/A"),
                            "last_wl_reading": "No data",
                            "last_manual_reading": "No data"
                        }
                    
                    with open(wells_data_path, 'w') as f:
                        json.dump(wells_data, f, indent=4)
                except Exception as e:
                    logger.warning(f"Could not create wells_data.json: {e}")
                    local_storage_available = False
        
        # Try to load existing run data, but don't fail if local storage is unavailable
        run_data = None
        if local_storage_available:
            try:
                with open(run_json_path, 'r') as f:
                    run_data = json.load(f)
            except FileNotFoundError:
                logger.warning(f"Run JSON file not found: {run_json_path}")
                local_storage_available = False
            except Exception as e:
                logger.error(f"Error reading run JSON file: {e}")
                local_storage_available = False
        
        # If we can't use local storage, log it and continue with cloud-only UI updates
        if not local_storage_available:
            logger.info("Local storage unavailable - continuing with cloud-only mode (UI updates only)")
            # In cloud-only mode, we still want to update the UI, just skip local file operations
            run_data = None
        
        # Continue with local file processing only if we have valid run_data
        if run_data:
            try:
                # Initialize the location to well mapping if needed
                if not hasattr(self.runs_monitor, 'location_to_well_mapping') or not self.runs_monitor.location_to_well_mapping:
                    # Set the database path and load the mapping
                    self.runs_monitor.db_path = self.db_manager.current_db
                    self.runs_monitor.location_to_well_mapping = self.runs_monitor.get_location_to_well_mapping()
                    logger.debug(f"Initialized location to well mapping with {len(self.runs_monitor.location_to_well_mapping)} entries")
                
                # Create a reverse mapping (well number to location code)
                well_to_location = {}
                for loc, well_num in self.runs_monitor.location_to_well_mapping.items():
                    well_to_location[well_num] = loc
                
                # Track whether we've made any changes that need to be saved
                changes_made = False
                
                # For each well in the run
                for well_number, well_status in run_data['runs'][0]['well_status'].items():
                    # Check if we have a location code for this well
                    location_code = well_to_location.get(well_number)
                
                    if location_code:
                        logger.debug(f"Found location code '{location_code}' for well {well_number}")
                        
                        # Normalize the location code for comparison
                        normalized_loc = location_code.replace('-', '').replace(' ', '').upper()
                        
                        # Look for this location in the latest readings
                        matched_loc = None
                        for reading_loc in latest_readings.keys():
                            normalized_reading_loc = reading_loc.replace('-', '').replace(' ', '').upper()
                            if normalized_reading_loc == normalized_loc:
                                matched_loc = reading_loc
                                break
                        
                        # If we found a match, update the well status
                        if matched_loc:
                            reading_info = latest_readings[matched_loc]
                            reading_date = reading_info['date']
                            
                            logger.debug(f"Matched well {well_number} with reading from {matched_loc} on date {reading_date}")
                            
                            # Get the file info - handle both possible key names (file_name from Google Drive or file_path from local files)
                            file_info = reading_info.get('file_name', reading_info.get('file_path', 'Unknown file'))
                            
                            # Update the well status with the transducer data
                            well_status['visited'] = True
                            well_status['tranducer_data_date'] = reading_date.strftime('%Y-%m-%d %H:%M:%S')
                            well_status['tranducer_record'] = {
                                'file_info': file_info,  # Using a consistent key name
                                'location': matched_loc,
                                'date': reading_date.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            changes_made = True
                            
                            # Update the table UI as well
                            for row in range(self.wells_table.rowCount()):
                                if self.wells_table.item(row, 2).text() == well_number:
                                    # Update transducer status icon
                                    transducer_item = QTableWidgetItem()
                                    transducer_item.setIcon(self.create_flag_icon("green"))
                                    transducer_item.setTextAlignment(Qt.AlignCenter)
                                    transducer_item.setData(Qt.UserRole, "green")
                                    self.wells_table.setItem(row, 0, transducer_item)
                                    
                                    # Update Last WL Reading column
                                    local_dt = reading_date.strftime('%Y-%m-%d %I:%M %p')
                                    wl_text = f"{local_dt} | From XLE file ({matched_loc})"
                                    self.wells_table.setItem(row, 5, QTableWidgetItem(wl_text))
                                    break
                
                # Save changes to JSON if any were made
                if changes_made:
                    logger.debug(f"Saving changes to {run_json_path}")
                    with open(run_json_path, 'w') as f:
                        json.dump(run_data, f, indent=4)
                    logger.info(f"Updated run data in {run_json_path}")
                else:
                    logger.debug("No changes made to JSON file")
                    
            except Exception as e:
                logger.error(f"Error updating JSON file with readings: {e}", exc_info=True)
        else:
            # Cloud-only mode: Update UI without local file operations
            logger.info("Cloud-only mode: Updating UI with latest readings")
            try:
                # Initialize the location to well mapping if needed
                if not hasattr(self.runs_monitor, 'location_to_well_mapping') or not self.runs_monitor.location_to_well_mapping:
                    # Set the database path and load the mapping
                    self.runs_monitor.db_path = self.db_manager.current_db
                    self.runs_monitor.location_to_well_mapping = self.runs_monitor.get_location_to_well_mapping()
                    logger.debug(f"Initialized location to well mapping with {len(self.runs_monitor.location_to_well_mapping)} entries")
                
                # Create a reverse mapping (well number to location code)
                well_to_location = {}
                for loc, well_num in self.runs_monitor.location_to_well_mapping.items():
                    well_to_location[well_num] = loc
                
                # Update UI for each well in the current run
                for well in wells:
                    well_number = well['well_number']
                    
                    # Check if we have a location code for this well
                    location_code = well_to_location.get(well_number)
                
                    if location_code:
                        logger.debug(f"Found location code '{location_code}' for well {well_number}")
                        
                        # Normalize the location code for comparison
                        normalized_loc = location_code.replace('-', '').replace(' ', '').upper()
                        
                        # Look for this location in the latest readings
                        matched_loc = None
                        for reading_loc in latest_readings.keys():
                            normalized_reading_loc = reading_loc.replace('-', '').replace(' ', '').upper()
                            if normalized_reading_loc == normalized_loc:
                                matched_loc = reading_loc
                                break
                        
                        # If we found a match, update the UI
                        if matched_loc:
                            reading_info = latest_readings[matched_loc]
                            reading_date = reading_info['date']
                            
                            logger.debug(f"Matched well {well_number} with reading from {matched_loc} on date {reading_date}")
                            
                            # Update the table UI
                            for row in range(self.wells_table.rowCount()):
                                if self.wells_table.item(row, 2).text() == well_number:
                                    # Update transducer status icon
                                    transducer_item = QTableWidgetItem()
                                    transducer_item.setIcon(self.create_flag_icon("green"))
                                    transducer_item.setTextAlignment(Qt.AlignCenter)
                                    transducer_item.setData(Qt.UserRole, "green")
                                    self.wells_table.setItem(row, 0, transducer_item)
                                    
                                    # Update Last WL Reading column
                                    local_dt = reading_date.strftime('%Y-%m-%d %I:%M %p')
                                    wl_text = f"{local_dt} | From XLE file ({matched_loc}) [Cloud-only]"
                                    self.wells_table.setItem(row, 5, QTableWidgetItem(wl_text))
                                    break
                        else:
                            logger.debug(f"No reading found for well {well_number} (location: {location_code})")
                    else:
                        logger.debug(f"No location code found for well {well_number}")
                        
            except Exception as e:
                logger.error(f"Error updating UI in cloud-only mode: {e}", exc_info=True)

    def update_manual_readings_status(self, run_id):
        """Update manual readings status for wells in the current run and update the JSON file"""
        if not run_id or run_id == "Select Run":
            return
        
        try:
            # Get the run start date from the run JSON in temp directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', run_id)
            run_json_path = os.path.join(run_dir, 'water_level_run.json')
            
            with open(run_json_path, 'r') as f:
                run_data = json.load(f)
            
            # Track whether we've made any changes that need to be saved
            changes_made = False
            
            # Extract year and month from run_id (e.g., "2025-02" -> 2025, 2)
            year, month = map(int, run_id.split()[0].split('-'))
            
            # Set start date to first day of the month
            run_start = datetime(year, month, 1)
            run_end = run_start + timedelta(days=60)  # Look for readings up to 2 months aheadd
            
            # Convert to UTC for database comparison
            run_start_utc = run_start.replace(hour=0, minute=0, second=0).astimezone(pytz.UTC)
            run_end_utc = run_end.replace(hour=23, minute=59, second=59).astimezone(pytz.UTC)
            
            logger.debug(f"Checking manual readings between {run_start_utc} and {run_end_utc}")
            
            # Query manual readings for the relevant period
            with sqlite3.connect(self.db_manager.current_db) as conn:
                query = """
                    SELECT 
                        well_number,
                        measurement_date_utc,
                        water_level,
                        dtw_avg,
                        collected_by,
                        comments
                    FROM manual_level_readings
                    WHERE measurement_date_utc >= ?
                    AND measurement_date_utc <= ?
                    AND well_number IN ({})
                    ORDER BY measurement_date_utc DESC
                """.format(','.join(['?'] * len(self.runs[run_id])))
                
                well_numbers = [well['well_number'] for well in self.runs[run_id]]
                params = [run_start_utc.strftime('%Y-%m-%d %H:%M:%S'), 
                        run_end_utc.strftime('%Y-%m-%d %H:%M:%S')] + well_numbers
                
                logger.debug(f"SQL Query: {query}")
                logger.debug(f"Query parameters: {params}")
                
                manual_readings = pd.read_sql(query, conn, params=params, 
                                            parse_dates=['measurement_date_utc'])
                
                logger.debug(f"Found {len(manual_readings)} manual readings")
                if not manual_readings.empty:
                    logger.debug("Sample of readings found:")
                    logger.debug(manual_readings[['well_number', 'measurement_date_utc']].to_string())
                
                    # Process all readings first, grouping by well number to find the most recent
                    well_readings = {}
                    for _, row in manual_readings.iterrows():
                        well_num = row['well_number']
                        
                        # If we don't have this well yet, or this reading is newer
                        if (well_num not in well_readings or 
                            row['measurement_date_utc'] > well_readings[well_num]['date']):
                            
                            # Store all needed data from this reading
                            well_readings[well_num] = {
                                'date': row['measurement_date_utc'],
                                'water_level': float(row['water_level']),
                                'dtw': float(row['dtw_avg']),
                                'collected_by': row['collected_by'],
                                'comments': row['comments'] if pd.notnull(row['comments']) else ''
                            }
                
                # Now update the JSON file with the collected readings
                for well_num, reading in well_readings.items():
                    if well_num in run_data['runs'][0]['well_status']:
                        # Get the well status object
                        well_status = run_data['runs'][0]['well_status'][well_num]
                        
                        # Update it with manual reading data
                        well_status['visited'] = True
                        well_status['manual_data_date'] = reading['date'].strftime('%Y-%m-%d %H:%M:%S')
                        well_status['manual_record'] = {
                            'water_level': reading['water_level'],
                            'dtw': reading['dtw'],
                            'collected_by': reading['collected_by'],
                            'comments': reading['comments']
                        }
                        changes_made = True
                        logger.debug(f"Updated well {well_num} with manual reading from {reading['date']}")
                
                # Then update the table display
                for row in range(self.wells_table.rowCount()):
                    well_number = self.wells_table.item(row, 2).text()
                    
                    if well_number in well_readings:
                        # Get the reading for this well
                        reading = well_readings[well_number]
                        
                        # Update icon to green
                        manual_item = QTableWidgetItem()
                        manual_item.setIcon(self.create_flag_icon("green"))
                        manual_item.setTextAlignment(Qt.AlignCenter)
                        manual_item.setData(Qt.UserRole, "green")
                        self.wells_table.setItem(row, 1, manual_item)
                        
                        # Format text for display
                        local_dt = reading['date'].tz_localize('UTC').tz_convert('America/Chicago')
                        manual_text = (f"{local_dt.strftime('%Y-%m-%d %I:%M %p')} | "
                                    f"{reading['water_level']:.2f} ft | "
                                    f"DTW: {reading['dtw']:.2f} ft | "
                                    f"By: {reading['collected_by']}")
                                    
                        # Update the text in the table
                        self.wells_table.setItem(row, 6, QTableWidgetItem(manual_text))
                
            # Save changes to JSON if any were made
            if changes_made:
                logger.debug(f"Saving changes to {run_json_path}")
                with open(run_json_path, 'w') as f:
                    json.dump(run_data, f, indent=4)
                logger.info(f"Updated run data in {run_json_path} with manual readings")
                
                # Sync changes to cloud if this is a cloud run
                self.sync_run_to_cloud(run_id)
            else:
                logger.debug("No changes made to JSON file")
                
        except Exception as e:
            logger.error(f"Error updating manual readings status: {e}", exc_info=True)

    def refresh_data(self):
        """Refresh the runs data."""
        logger.debug("Refreshing water level runs data")
        try:
            # Reload existing runs
            self.load_existing_runs()
            
            # If a run is currently selected, refresh its display
            if self.current_run_id:
                self.display_run_wells(self.current_run_id)
                self.update_map_markers(self.current_run_id)
                
            return True
        except Exception as e:
            logger.error(f"Error refreshing water level runs data: {e}")
            return False 

    def cleanup(self):
        """Clean up resources before tab is destroyed."""
        # Clear the wells table
        if hasattr(self, 'wells_table'):
            self.wells_table.clear()
            self.wells_table.setRowCount(0)
            self.wells_table.setColumnCount(0)
        
        # Clear the map view
        if hasattr(self, 'map_view'):
            self.map_view.setUrl(QUrl('about:blank'))
        
        # Clear any stored data
        self.runs.clear()
        self.selected_wells = [] 

    def upload_run_to_drive(self, run_id):
        """Upload a specific run to Google Drive."""
        try:
            logger.info(f"Uploading run folder to Google Drive: {run_id}")
            main_window = self.window()
            
            # Check if we have an authenticated Google Drive service
            if not (hasattr(main_window, 'drive_service') and main_window.drive_service.authenticated):
                logger.warning("Google Drive service not available for upload")
                return False
            
            # Get the Google Drive service
            service = main_window.drive_service.get_service()
            
            # Get current project context
            if not (hasattr(main_window, 'db_manager') and main_window.db_manager.is_cloud_database):
                logger.warning("No cloud database selected for upload")
                return False
            
            project_name = getattr(main_window.db_manager, 'cloud_project_name', None)
            if not project_name:
                logger.warning("No project name available for upload")
                return False
            
            logger.info(f"Uploading run {run_id} to project {project_name}")
            
            # Find or create the project's WATER_LEVEL_RUNS folder
            runs_folder_id = self._find_or_create_project_runs_folder(service, project_name)
            if not runs_folder_id:
                logger.error(f"Could not find/create WATER_LEVEL_RUNS folder for project {project_name}")
                return False
            
            # Find or create the month folder (e.g., 2025-06)
            month_folder_id = self._find_or_create_month_folder(service, runs_folder_id, run_id)
            if not month_folder_id:
                logger.error(f"Could not find/create month folder for run {run_id}")
                return False
            
            # Upload the JSON files
            success = self._upload_run_files(service, run_id, month_folder_id)
            
            if success:
                logger.info(f"Successfully uploaded run {run_id} to Google Drive")
            else:
                logger.error(f"Failed to upload run {run_id} to Google Drive")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in upload_run_to_drive: {e}")
            return False 

    def _find_or_create_project_runs_folder(self, service, project_name):
        """Find or create the WATER_LEVEL_RUNS folder for a project"""
        try:
            # Get main water_levels_monitoring folder
            main_folder_id = self.window().settings_handler.get_setting("google_drive_folder_id")
            if not main_folder_id:
                return None
            
            # Find Projects folder
            query = f"'{main_folder_id}' in parents and name='Projects' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            projects_folders = results.get('files', [])
            
            if not projects_folders:
                logger.error("Projects folder not found")
                return None
            
            projects_folder_id = projects_folders[0]['id']
            
            # Find project folder
            query = f"'{projects_folder_id}' in parents and name='{project_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            project_folders = results.get('files', [])
            
            if not project_folders:
                logger.error(f"Project folder {project_name} not found")
                return None
            
            project_folder_id = project_folders[0]['id']
            
            # Find or create WATER_LEVEL_RUNS folder
            query = f"'{project_folder_id}' in parents and name='WATER_LEVEL_RUNS' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            runs_folders = results.get('files', [])
            
            if runs_folders:
                logger.info(f"Found existing WATER_LEVEL_RUNS folder for {project_name}")
                return runs_folders[0]['id']
            else:
                # Create WATER_LEVEL_RUNS folder
                folder_metadata = {
                    'name': 'WATER_LEVEL_RUNS',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [project_folder_id]
                }
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                logger.info(f"Created WATER_LEVEL_RUNS folder for {project_name}")
                return folder.get('id')
                
        except Exception as e:
            logger.error(f"Error finding/creating project runs folder: {e}")
            return None
    
    def _find_or_create_month_folder(self, service, runs_folder_id, run_id):
        """Find or create month folder (e.g., 2025-06) in WATER_LEVEL_RUNS"""
        try:
            # Extract month from run_id (e.g., "2025-06" from "2025-06" or "2025-06 (2)")
            month_folder_name = run_id.split()[0]  # Gets "2025-06"
            
            # Find existing folder
            query = f"'{runs_folder_id}' in parents and name='{month_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            month_folders = results.get('files', [])
            
            if month_folders:
                logger.info(f"Found existing month folder {month_folder_name}")
                return month_folders[0]['id']
            else:
                # Create month folder
                folder_metadata = {
                    'name': month_folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [runs_folder_id]
                }
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                logger.info(f"Created month folder {month_folder_name}")
                return folder.get('id')
                
        except Exception as e:
            logger.error(f"Error finding/creating month folder: {e}")
            return None
    
    def _upload_run_files(self, service, run_id, month_folder_id):
        """Upload the JSON files for a run to Google Drive"""
        try:
            # Get local file paths
            import tempfile
            temp_dir = tempfile.gettempdir()
            run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', run_id)
            
            files_to_upload = [
                ('water_level_run.json', 'application/json'),
                ('wells_data.json', 'application/json')
            ]
            
            success_count = 0
            
            for filename, mimetype in files_to_upload:
                local_path = os.path.join(run_dir, filename)
                
                if not os.path.exists(local_path):
                    logger.warning(f"Local file not found: {local_path}")
                    continue
                
                # Check if file already exists in Google Drive
                query = f"'{month_folder_id}' in parents and name='{filename}' and trashed=false"
                results = service.files().list(q=query, fields="files(id)").execute()
                existing_files = results.get('files', [])
                
                try:
                    if existing_files:
                        # Update existing file
                        file_id = existing_files[0]['id']
                        from googleapiclient.http import MediaFileUpload
                        media = MediaFileUpload(local_path, mimetype=mimetype)
                        service.files().update(fileId=file_id, media_body=media).execute()
                        logger.info(f"Updated existing file: {filename}")
                    else:
                        # Create new file
                        file_metadata = {
                            'name': filename,
                            'parents': [month_folder_id]
                        }
                        from googleapiclient.http import MediaFileUpload
                        media = MediaFileUpload(local_path, mimetype=mimetype)
                        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                        logger.info(f"Uploaded new file: {filename}")
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error uploading {filename}: {e}")
            
            return success_count == len(files_to_upload)
            
        except Exception as e:
            logger.error(f"Error uploading run files: {e}")
            return False

    def create_flag_icon(self, color_name: str, diameter: int = 16):
        """Create an icon with a filled circle of the given color."""
        padding = 4
        total_size = diameter + (padding * 2)
        pixmap = QPixmap(total_size, total_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color_name))
        painter.setPen(Qt.NoPen)
        
        # Draw circle in center of pixmap
        painter.drawEllipse(padding, padding, diameter, diameter)
        painter.end()
        
        return QIcon(pixmap)

    def update_monet_data(self):
        """Call the update_monet_data function from water_level_tab"""
        # Get reference to water_level_tab
        water_level_tab = None
        main_window = self.parent()
        while main_window and not isinstance(main_window, QMainWindow):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, '_tabs'):
            water_level_tab = main_window._tabs.get('water_level')
        
        if water_level_tab:
            water_level_tab.update_monet_data()
        else:
            logger.error("Could not find water_level_tab to update Monet data")
            QMessageBox.warning(self, "Error", "Could not access Monet data update functionality") 

    def update_manual_readings_status(self, run_id):
        """Update manual readings status for wells in the current run and update the JSON file"""
        if not run_id or run_id == "Select Run":
            return
        
        # Use temp directory for local storage
        import tempfile
        temp_dir = tempfile.gettempdir()
        run_dir = os.path.join(temp_dir, 'water_levels_temp', 'runs', run_id)
        run_json_path = os.path.join(run_dir, 'water_level_run.json')
        
        # Check if temp storage is available
        local_storage_available = True
        if not os.path.exists(run_dir):
            try:
                os.makedirs(run_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"Cannot create temp run directory: {e}")
                logger.info("Continuing without local storage - using cloud-only mode")
                local_storage_available = False
        
        # If local storage is not available, skip this method
        if not local_storage_available:
            logger.info("Temp storage unavailable - skipping manual readings status update")
            return
            
        try:
            # Try to load existing run data
            run_data = None
            if os.path.exists(run_json_path):
                with open(run_json_path, 'r') as f:
                    run_data = json.load(f)
            else:
                logger.warning(f"Run JSON file not found: {run_json_path}. Cannot update manual readings.")
                return
            
            # Track whether we've made any changes that need to be saved
            changes_made = False
            
            # Extract year and month from run_id (e.g., "2025-02" -> 2025, 2)
            year, month = map(int, run_id.split()[0].split('-'))
            
            # Set start date to first day of the month
            run_start = datetime(year, month, 1)
            run_end = run_start + timedelta(days=60)  # Look for readings up to 2 months ahead
            
            # Convert to UTC for database comparison
            run_start_utc = run_start.replace(hour=0, minute=0, second=0).astimezone(pytz.UTC)
            run_end_utc = run_end.replace(hour=23, minute=59, second=59).astimezone(pytz.UTC)
            
            logger.debug(f"Checking manual readings between {run_start_utc} and {run_end_utc}")
            
            # Query manual readings for the relevant period
            with sqlite3.connect(self.db_manager.current_db) as conn:
                query = """
                    SELECT 
                        well_number,
                        measurement_date_utc,
                        water_level,
                        dtw_avg,
                        collected_by,
                        comments
                    FROM manual_level_readings
                    WHERE measurement_date_utc >= ?
                    AND measurement_date_utc <= ?
                    AND well_number IN ({})
                    ORDER BY measurement_date_utc DESC
                """.format(','.join(['?'] * len(self.runs[run_id])))
                
                well_numbers = [well['well_number'] for well in self.runs[run_id]]
                params = [run_start_utc.strftime('%Y-%m-%d %H:%M:%S'), 
                        run_end_utc.strftime('%Y-%m-%d %H:%M:%S')] + well_numbers
                
                logger.debug(f"SQL Query: {query}")
                logger.debug(f"Query parameters: {params}")
                
                manual_readings = pd.read_sql(query, conn, params=params, 
                                            parse_dates=['measurement_date_utc'])
                
                logger.debug(f"Found {len(manual_readings)} manual readings")
                
                # Initialize well_readings dictionary (empty if no readings found)
                well_readings = {}
                
                if not manual_readings.empty:
                    logger.debug("Sample of readings found:")
                    logger.debug(manual_readings[['well_number', 'measurement_date_utc']].to_string())
                
                    # Process all readings first, grouping by well number to find the most recent
                    well_readings = {}
                    for _, row in manual_readings.iterrows():
                        well_num = row['well_number']
                        
                        # If we don't have this well yet, or this reading is newer
                        if (well_num not in well_readings or 
                            row['measurement_date_utc'] > well_readings[well_num]['date']):
                            
                            # Store all needed data from this reading
                            well_readings[well_num] = {
                                'date': row['measurement_date_utc'],
                                'water_level': float(row['water_level']),
                                'dtw': float(row['dtw_avg']),
                                'collected_by': row['collected_by'],
                                'comments': row['comments'] if pd.notnull(row['comments']) else ''
                            }
                
                # Now update the JSON file with the collected readings
                for well_num, reading in well_readings.items():
                    if well_num in run_data['runs'][0]['well_status']:
                        # Get the well status object
                        well_status = run_data['runs'][0]['well_status'][well_num]
                        
                        # Update it with manual reading data
                        well_status['visited'] = True
                        well_status['manual_data_date'] = reading['date'].strftime('%Y-%m-%d %H:%M:%S')
                        well_status['manual_record'] = {
                            'water_level': reading['water_level'],
                            'dtw': reading['dtw'],
                            'collected_by': reading['collected_by'],
                            'comments': reading['comments']
                        }
                        changes_made = True
                        logger.debug(f"Updated well {well_num} with manual reading from {reading['date']}")
                
                # Then update the table display
                for row in range(self.wells_table.rowCount()):
                    well_number = self.wells_table.item(row, 2).text()
                    
                    if well_number in well_readings:
                        # Get the reading for this well
                        reading = well_readings[well_number]
                        
                        # Update icon to green
                        manual_item = QTableWidgetItem()
                        manual_item.setIcon(self.create_flag_icon("green"))
                        manual_item.setTextAlignment(Qt.AlignCenter)
                        manual_item.setData(Qt.UserRole, "green")
                        self.wells_table.setItem(row, 1, manual_item)
                        
                        # Format text for display
                        local_dt = reading['date'].tz_localize('UTC').tz_convert('America/Chicago')
                        manual_text = (f"{local_dt.strftime('%Y-%m-%d %I:%M %p')} | "
                                    f"{reading['water_level']:.2f} ft | "
                                    f"DTW: {reading['dtw']:.2f} ft | "
                                    f"By: {reading['collected_by']}")
                                    
                        # Update the text in the table
                        self.wells_table.setItem(row, 6, QTableWidgetItem(manual_text))
                
            # Save changes to JSON if any were made
            if changes_made:
                logger.debug(f"Saving changes to {run_json_path}")
                with open(run_json_path, 'w') as f:
                    json.dump(run_data, f, indent=4)
                logger.info(f"Updated run data in {run_json_path} with manual readings")
                
                # Sync changes to cloud if this is a cloud run
                self.sync_run_to_cloud(run_id)
            else:
                logger.debug("No changes made to JSON file")
                
        except Exception as e:
            logger.error(f"Error updating manual readings status: {e}", exc_info=True)

    def update_for_screen(self, screen):
        """Update layout for the current screen"""
        try:
            logger.debug(f"Updating WaterLevelRunsTab layout for screen: {screen.name()}")
            
            # Skip if we've updated recently (add a throttle)
            if hasattr(self, '_last_screen_update_time'):
                current_time = time.time()
                if current_time - self._last_screen_update_time < 1.0:  # 1 second throttle
                    logger.debug("Skipping layout update - throttled")
                    return
            
            # Update the timestamp
            self._last_screen_update_time = time.time()
            
            # Get screen dimensions
            available_size = screen.availableGeometry().size()
            
            # Update map view size if it exists
            if hasattr(self, 'map_view'):
                self.map_view.setMinimumHeight(int(available_size.height() * 0.4))
                
            # Update table dimensions if it exists
            if hasattr(self, 'wells_table'):
                # Adjust column widths based on screen width
                if self.wells_table.columnCount() >= 9:
                    header = self.wells_table.horizontalHeader()
                    
                    # Recalculate column widths based on screen width
                    screen_width_factor = available_size.width() / 1920.0  # Scale based on 1920 as reference
                    
                    # Only adjust the two smallest columns to reduce layout work
                    self.wells_table.setColumnWidth(0, int(50 * screen_width_factor))  # Transducer column
                    self.wells_table.setColumnWidth(1, int(50 * screen_width_factor))  # Manual column
            
            # Handle tab_widget layout safely
            if hasattr(self, 'tab_widget') and self.tab_widget and not self.tab_widget.isHidden():
                tab_layout = self.tab_widget.layout()
                if tab_layout and not getattr(self, '_layout_update_in_progress', False):
                    self._layout_update_in_progress = True
                    tab_layout.update()
                    self._layout_update_in_progress = False
            
            # Update the map with a significant delay and only if not already scheduled
            if hasattr(self, 'current_run_id') and self.current_run_id:
                if not hasattr(self, '_map_update_timer'):
                    self._map_update_timer = QTimer(self)
                    self._map_update_timer.setSingleShot(True)
                    self._map_update_timer.timeout.connect(lambda: self.update_map_markers(self.current_run_id))
                
                if not self._map_update_timer.isActive():
                    self._map_update_timer.start(800)  # Increased delay to 800ms to further reduce updates
            
        except Exception as e:
            logger.error(f"Error updating WaterLevelRunsTab for screen change: {e}")

    def update_run_with_latest_readings(self, run_data, latest_readings):
        """
        Update the run data with the latest transducer readings
        """
        self.logger.debug(f"Available readings in latest_readings: {list(latest_readings.keys())}")
        
        # Get the location to well number mapping from the runs folder monitor
        location_to_well_mapping = self.runs_folder_monitor.location_to_well_mapping
        self.logger.debug(f"Using location to well mapping with {len(location_to_well_mapping)} entries")
        
        # Track if any changes are made
        changes_made = False
        
        # For each well in the run
        for well_number, well_status in run_data['well_status'].items():
            # Find if we have a location code (CAE) for this well number
            location_code = None
            for loc, well_num in location_to_well_mapping.items():
                if well_num == well_number:
                    location_code = loc
                    break
            
            # If we found a matching location code and it's in the latest readings
            if location_code and location_code in latest_readings:
                self.logger.debug(f"Found matching reading for well {well_number} using location code {location_code}")
                reading_data = latest_readings[location_code]
                
                # Update the well status with the transducer data
                well_status['visited'] = True
                well_status['tranducer_data_date'] = reading_data['date'].strftime('%Y-%m-%d')
                well_status['tranducer_record'] = reading_data['file_path']
                changes_made = True
        
        # Log whether changes were made
        if changes_made:
            self.logger.debug(f"Updated JSON file with {sum(1 for w in run_data['well_status'].values() if w['tranducer_record'])} transducer readings")
        else:
            self.logger.debug("No changes made to JSON file")
        
        return changes_made

    def check_for_manual_readings(self, run_data, start_date, end_date):
        """
        Check for manual readings in the database for the wells in the run
        """
        # ...existing code...
        
        # For each manual reading found
        for _, row in readings_df.iterrows():
            well_number = row['well_number']
            
            # Check if this well is in the run
            if well_number in run_data['well_status']:
                # Update the well status with the manual reading
                run_data['well_status'][well_number]['visited'] = True
                run_data['well_status'][well_number]['manual_data_date'] = row['measurement_date_utc']
                run_data['well_status'][well_number]['manual_record'] = {
                    'water_level': row['water_level'],
                    'dtw_avg': row['dtw_avg'],
                    'collected_by': row['collected_by'],
                    'comments': row['comments']
                }
                changes_made = True
        
        # Log changes
        if changes_made:
            self.logger.debug(f"Updated JSON file with {sum(1 for w in run_data['well_status'].values() if w['manual_record'])} manual readings")
        
        return changes_made

    def reload_current_run(self):
        """Reload the current run data."""
        if self.current_run_id:
            logger.info(f"Reloading run: {self.current_run_id}")
            
            # Create a single progress dialog for the entire process
            main_window = self.window()
            progress_handler = None
            if hasattr(main_window, 'progress_dialog_handler'):
                progress_handler = main_window.progress_dialog_handler
                progress_handler.start_progress("Reloading Run Data", "Initializing...", 0, 100)
            
            # Process the run data with the single progress handler
            self.process_run_data(self.current_run_id, progress_handler)
            
            # Now display the run data
            self.display_run_wells(self.current_run_id)
            self.update_map_markers(self.current_run_id)
            
            # Close the progress dialog if it was created
            if progress_handler:
                progress_handler.finish()
                
            QMessageBox.information(self, "Reload Complete", f"Run '{self.current_run_id}' has been reloaded successfully")
        else:
            QMessageBox.warning(self, "No Run Selected", "Please select a run to reload")




