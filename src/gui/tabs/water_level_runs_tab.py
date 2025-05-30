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
import json
import folium
from folium import plugins
import branca
from ..handlers.google_drive_monitor import GoogleDriveMonitor
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
                            wl_text = (f"{local_dt.strftime('%Y-%m-%d %I:%M %p')} | "
                                     f"{well.get('water_level'):.2f} ft | "
                                     f"T: {well.get('temperature'):.1f}°C | {data_source}")
                        else:
                            wl_text = "No data"
                        self.wells_table.setItem(row, 6, QTableWidgetItem(wl_text))
                        
                        # Last Manual Reading
                        if pd.notnull(well.get('measurement_date_utc')) and pd.notnull(well.get('water_level_manual')):
                            utc_dt = pd.to_datetime(well.get('measurement_date_utc'))
                            local_dt = utc_dt.tz_localize('UTC').tz_convert('America/Chicago').tz_localize(None)
                            manual_text = (f"{local_dt.strftime('%Y-%m-%d %I:%M %p')} | "
                                         f"{well.get('water_level_manual'):.2f} ft | "
                                         f"DTW: {well.get('dtw_avg'):.2f} ft | By: {well.get('collected_by')}")
                        else:
                            manual_text = "No data"
                        self.wells_table.setItem(row, 7, QTableWidgetItem(manual_text))
                        
                        # Notes
                        notes = []
                        if pd.notnull(well.get('top_of_casing')):
                            notes.append(f"TOC: {well.get('top_of_casing'):.2f} ft")
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
        self.current_run_id = None  # Track the currently selected run
        
        # Initialize the runs folder monitor without connecting
        self.runs_monitor = RunsFolderMonitor()
        
        # Initialize tracking variables for Google Drive connection
        self.is_drive_connected = False
        
        self.setup_ui()
        self.load_existing_runs()
        
        # Initialize in disconnected state by default
        self._update_connection_state(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create overlay widget for blocking interaction
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.7);
                border: none;
            }
        """)
        self.overlay.hide()
        
        # Add connection status banner with connect button
        self.connection_banner = QFrame()
        self.connection_banner.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.connection_banner.setMaximumHeight(40)
        banner_layout = QHBoxLayout(self.connection_banner)
        banner_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_text = QLabel("Not connected to Google Drive")
        self.status_text.setStyleSheet("font-weight: bold; color: #F44336;")
        banner_layout.addWidget(self.status_text)
        
        # Add Google Drive connect button
        self.connect_drive_btn = QPushButton("Connect to Google Drive")
        self.connect_drive_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.connect_drive_btn.clicked.connect(self._connect_to_drive)
        banner_layout.addWidget(self.connect_drive_btn)
        
        banner_layout.addStretch(1)
        layout.addWidget(self.connection_banner)
        
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
        
        # Button to check Google Drive
        self.google_drive_btn = QPushButton("Check Google Drive")
        self.google_drive_btn.setFont(QFont("Arial", 10))
        self.google_drive_btn.clicked.connect(self.check_google_drive)
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
        
        # Show overlay initially since we start disconnected
        self._update_connection_state(False)

    def _connect_to_drive(self):
        """Handle Google Drive connection by using the centralized authentication in main window"""
        # Get main window reference
        main_window = self.window()
        
        # Create progress dialog 
        progress = QProgressDialog("Connecting to Google Drive...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Google Drive Connection")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        progress.show()
        
        try:
            self.connect_drive_btn.setEnabled(False)
            self.status_text.setText("Connecting to Google Drive...")
            
            # Check if main window exists and has drive_service
            if hasattr(main_window, 'drive_service'):
                # Update progress
                progress.setValue(20)
                progress.setLabelText("Authenticating with Google Drive...")
                
                # Use main window's authentication method
                if main_window.authenticate_google_drive(force=True):
                    # Authentication successful
                    progress.setValue(70)
                    progress.setLabelText("Authentication successful, updating UI...")
                    
                    # Get authenticated service for runs monitor
                    service = main_window.drive_service.get_service()
                    if service:
                        self.runs_monitor.set_authenticated_service(service)
                        self.is_drive_connected = True
                    
                    # Reload runs list
                    progress.setValue(80)
                    progress.setLabelText("Loading existing runs...")
                    self.runs.clear()
                    self.runs_dropdown.clear()
                    self.runs_dropdown.addItem("Select Run")
                    self.load_existing_runs()
                    
                    # Complete the progress
                    progress.setValue(100)
                    progress.setLabelText("Connection complete!")
                    
                    self._update_connection_state(True)
                    logger.debug("Successfully connected to Google Drive")
                else:
                    progress.close()
                    self._update_connection_state(False)
                    QMessageBox.warning(self, "Connection Failed", 
                                     "Failed to connect to Google Drive. Please check Google Drive settings in the Tools menu.")
            else:
                progress.close()
                self._update_connection_state(False)
                QMessageBox.warning(self, "Error", 
                                  "Google Drive service not available. Please check Google Drive settings in the Tools menu.")
                
        except Exception as e:
            progress.close()
            logger.error(f"Error connecting to Google Drive: {e}")
            self._update_connection_state(False)
            QMessageBox.critical(self, "Error", 
                               f"Error connecting to Google Drive: {str(e)}")
        finally:
            self.connect_drive_btn.setEnabled(True)
            if progress.isVisible():
                progress.close()

    def _update_connection_state(self, is_connected: bool):
        """Update UI elements based on connection state"""
        if is_connected:
            self.status_text.setText("Connected to Google Drive")
            self.status_text.setStyleSheet("font-weight: bold; color: #4CAF50;")
            self.connect_drive_btn.setText("Reconnect")
            self.overlay.hide()
        else:
            self.status_text.setText("Not connected to Google Drive")
            self.status_text.setStyleSheet("font-weight: bold; color: #F44336;")
            self.connect_drive_btn.setText("Connect to Google Drive")
            
            # Position overlay to cover everything EXCEPT the header - use 15% as header size
            overlay_rect = self.rect()
            header_height = int(self.height() * 0.1)  # Use 15% for header (decreased from 30%)
            overlay_rect.setTop(header_height)
            self.overlay.setGeometry(overlay_rect)
            self.overlay.raise_()
            self.overlay.show()
            
            # Save the header height for resizing
            self._header_height_percent = 0.1
        
        # Update button states
        self.create_run_btn.setEnabled(is_connected)
        self.google_drive_btn.setEnabled(is_connected)
        self.update_monet_btn.setEnabled(is_connected)
        self.reload_run_btn.setEnabled(is_connected)
        self.runs_dropdown.setEnabled(is_connected)

    def resizeEvent(self, event):
        """Handle resize events to keep overlay properly sized"""
        super().resizeEvent(event)
        if hasattr(self, 'overlay') and self.overlay.isVisible():
            # Recalculate header height with the stored percentage
            header_height = int(self.height() * getattr(self, '_header_height_percent', 0.3))
            overlay_rect = self.rect()
            overlay_rect.setTop(header_height)
            self.overlay.setGeometry(overlay_rect)

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
                    # Create directory for the run if it doesn't exist
                    run_dir = os.path.join('data', 'runs', run_id)
                    os.makedirs(run_dir, exist_ok=True)
                    
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
            
            # Load the JSON file to get status information
            run_dir = os.path.join('data', 'runs', run_id)
            run_json_path = os.path.join(run_dir, 'water_level_run.json')
            
            try:
                with open(run_json_path, 'r') as f:
                    run_data = json.load(f)
                    
                for row, well in enumerate(wells):
                    well_number = well['well_number']
                    well_status = run_data['runs'][0]['well_status'].get(well_number, {})
                    
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
                            manual_text = (f"{local_dt} | "
                                         f"{manual_record.get('water_level', 0):.2f} ft | "
                                         f"DTW: {manual_record.get('dtw_avg', 0)::.2f} ft | By: {manual_record.get('collected_by', 'Unknown')}")
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
                
                # Fall back to the database check for manual readings
                self.update_manual_readings_status(run_id)

    def load_existing_runs(self):
        base_dir = os.path.join('data', 'runs')
        if not os.path.exists(base_dir):
            return

        # Iterate over all run directories (each folder name corresponds to a run ID)
        for run_id in os.listdir(base_dir):
            run_dir = os.path.join(base_dir, run_id)
            water_level_run_file = os.path.join(run_dir, 'water_level_run.json')
            wells_data_file = os.path.join(run_dir, 'wells_data.json')
            if os.path.exists(water_level_run_file) and os.path.exists(wells_data_file):
                with open(water_level_run_file, 'r') as f:
                    run_data = json.load(f)
                with open(wells_data_file, 'r') as f:
                    wells_data = json.load(f)

                # Extract well IDs from the run JSON (assumes structure as created in create_run)
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
                            "notes": "No notes"
                        }
                        well_list.append(well_dict)

                # Store the well list in the runs dictionary and add to dropdown if not already present
                self.runs[run_id] = well_list
                if run_id not in [self.runs_dropdown.itemText(i) for i in range(self.runs_dropdown.count())]:
                    self.runs_dropdown.addItem(run_id) 

    def init_map(self):
        """Initialize the folium map centered on Memphis"""
        memphis_coords = [35.1495, -90.0490]
        self.folium_map = folium.Map(
            location=memphis_coords,
            zoom_start=10,
            tiles='OpenStreetMap'
        )
        
        # Save map to temporary HTML file
        map_path = os.path.abspath('temp_map.html')
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
                
                # Load current run status
                run_dir = os.path.join('data', 'runs', run_id)
                with open(os.path.join(run_dir, 'water_level_run.json'), 'r') as f:
                    run_data = json.load(f)
                with open(os.path.join(run_dir, 'wells_data.json'), 'r') as f:
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
                
                # Update the map view
                self.folium_map.save('temp_map.html')
                self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath('temp_map.html')))
                
        except Exception as e:
            logger.error(f"Error updating map markers: {e}")

    def check_google_drive(self):
        """Check Google Drive for XLE files relevant to current run"""
        if not self.current_run_id:
            QMessageBox.warning(self, "No Run Selected", "Please select a run first.")
            return
            
        try:
            # Show progress dialog
            progress = QProgressDialog("Checking Google Drive...", None, 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(500)
            progress.show()
            
            # Get main window
            main_window = self.window()
            
            # Check for authenticated drive service
            if hasattr(main_window, 'drive_service') and main_window.drive_service.authenticated:
                # Use the already authenticated service
                service = main_window.drive_service.get_service()
                
                # Set the authenticated service in the runs_monitor
                self.runs_monitor.set_authenticated_service(service)
                self.is_drive_connected = True
                
                # Update progress
                progress.setValue(20)
                progress.setLabelText("Using existing Google Drive authentication...")
            else:
                # Need to authenticate - this is the key addition
                progress.setValue(10)
                progress.setLabelText("Authenticating with Google Drive...")
                
                if not hasattr(main_window, 'settings_handler'):
                    progress.close()
                    QMessageBox.warning(self, "Settings Not Found", "Google Drive settings not found.")
                    return
                    
                settings_handler = main_window.settings_handler
                client_secret_path = settings_handler.get_setting("google_drive_secret_path")
                
                # Authenticate Google Drive service
                if hasattr(main_window, 'drive_service'):
                    if not main_window.drive_service.authenticate(force=True):
                        progress.close()
                        QMessageBox.warning(self, "Authentication Failed", 
                                          "Failed to authenticate with Google Drive.")
                        return
                    
                    # Use the newly authenticated service
                    service = main_window.drive_service.get_service()
                    
                    # Set the authenticated service in the runs_monitor
                    self.runs_monitor.set_authenticated_service(service)
                    self.is_drive_connected = True
                    
                    # Update progress
                    progress.setValue(20)
                    progress.setLabelText("Successfully authenticated with Google Drive...")
                    
                    # Also initialize the data handler for future use
                    if hasattr(main_window, 'drive_data_handler') and main_window.drive_data_handler:
                        main_window.drive_data_handler.authenticate()
                else:
                    # Fall back to separate authentication
                    if not self.runs_monitor.authenticate(client_secret_path, force=True):
                        progress.close()
                        QMessageBox.warning(self, "Authentication Failed", 
                                          "Failed to authenticate with Google Drive.")
                        return
            
            # Get year and month from run ID (e.g., "2025-02")
            year_month = self.current_run_id.split()[0]  # Gets "2025-02"
            
            # Update progress
            progress.setValue(40)
            progress.setLabelText("Scanning for XLE files...")
            
            # Get latest readings from drive
            latest_readings = self.runs_monitor.get_latest_readings(year_month)
            
            # Update progress
            progress.setValue(60)
            progress.setLabelText("Updating well information...")
            
            # Update the table with the new data and save to JSON
            self.update_table_with_readings(latest_readings)
            
            progress.setValue(100)
            progress.close()
            
            QMessageBox.information(self, "Scan Complete", 
                                  f"Found readings for {len(latest_readings)} locations.")
            
        except Exception as e:
            logger.error(f"Error checking Google Drive: {e}")
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to check Google Drive: {str(e)}")

    def update_table_with_readings(self, latest_readings):
        """Update the table with the latest readings from Google Drive and update the JSON file"""
        if not self.current_run_id or not self.wells_table:
            return
            
        # Get current wells in the run
        wells = self.runs[self.current_run_id]
        
        # Log available readings for debugging
        logger.debug(f"Available readings in latest_readings: {list(latest_readings.keys())}")
        
        # Use absolute path from application root directory
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        run_dir = os.path.join(app_root, 'data', 'runs', self.current_run_id)
        run_json_path = os.path.join(run_dir, 'water_level_run.json')
        
        logger.debug(f"Looking for run file at: {run_json_path}")
        
        # Ensure directory exists
        if not os.path.exists(run_dir):
            logger.warning(f"Run directory does not exist: {run_dir}. Creating it.")
            os.makedirs(run_dir, exist_ok=True)
        
        # Check if file exists, if not create a basic template
        if not os.path.exists(run_json_path):
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
                
            # Also create an empty wells_data.json
            wells_data = {}
            for well in wells:
                wells_data[well['well_number']] = {
                    "cae_number": well['cae'],
                    "well_field": well['well_field'],
                    "cluster": well.get('cluster', "N/A"),
                    "last_wl_reading": "No data",
                    "last_manual_reading": "No data"
                }
            
            wells_data_path = os.path.join(run_dir, 'wells_data.json')
            with open(wells_data_path, 'w') as f:
                json.dump(wells_data, f, indent=4)
        
        try:
            with open(run_json_path, 'r') as f:
                run_data = json.load(f)
            
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

    def update_manual_readings_status(self, run_id):
        """Update manual readings status for wells in the current run and update the JSON file"""
        if not run_id or run_id == "Select Run":
            return
        
        try:
            # Get the run start date from the run JSON
            run_dir = os.path.join('data', 'runs', run_id)
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
            if hasattr(main_window, 'drive_data_handler') and main_window.drive_data_handler:
                # Don't create a new progress dialog here - we're already showing progress
                # in the parent method (process_run_data)
                
                # Use the new method to upload just this run
                success = main_window.drive_data_handler.upload_run_folder(run_id)
                logger.info(f"Upload completed with result: {success}")
                return success
            else:
                logger.warning("No Google Drive data handler available for uploading run folder")
                return False
            
        except Exception as e:
            logger.error(f"Error in upload_run_to_drive: {e}")
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
        
        try:
            # Get the run start date from the run JSON
            run_dir = os.path.join('data', 'runs', run_id)
            run_json_path = os.path.join(run_dir, 'water_level_run.json')
            
            with open(run_json_path, 'r') as f:
                run_data = json.load(f)
            
            # Track whether we've made any changes that need to be saved
            changes_made = False
            
            # Extract year and month from run_id (e.g., "2025-02" -> 2025, 2)
            year, month = map.int(run_id.split()[0].split('-'))
            
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

    def setup_limited_mode(self, drive_service):
        """Setup limited mode UI elements without Google Drive access"""
        # Create a banner at the top of the tab
        self.connection_banner = QWidget()
        banner_layout = QHBoxLayout(self.connection_banner)
        banner_layout.setContentsMargins(10, 5, 10, 5)
        
        # Warning icon
        warning_label = QLabel()
        warning_icon = QIcon("src/gui/icons/warning.png")  # Create or use an existing icon
        warning_label.setPixmap(warning_icon.pixmap(24, 24))
        banner_layout.addWidget(warning_label)
        
        # Message
        message = QLabel("Limited functionality: Connect to Google Drive to access all field data features")
        banner_layout.addWidget(message, 1)  # Stretch factor 1
        
        # Connect button
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(lambda: self._connect_to_google_drive(drive_service))
        banner_layout.addWidget(connect_btn)
        
        # Add banner to the top of the layout
        if self.layout():
            self.layout().insertWidget(0, self.connection_banner)
        
        # Store drive service reference
        self._drive_service = drive_service
        
        # Disable features that require Google Drive
        if hasattr(self, 'import_button'):
            self.import_button.setEnabled(False)
            self.import_button.setToolTip("Google Drive connection required")

    def _connect_to_google_drive(self, drive_service):
        """Connect to Google Drive when requested from limited mode"""
        try:
            # Show progress dialog
            progress = QProgressDialog("Connecting to Google Drive...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Google Drive Connection")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            progress.setValue(10)
            
            # Get client secret path from settings
            main_window = self.window()
            if not hasattr(main_window, 'settings_handler'):
                progress.close()
                QMessageBox.warning(self, "Settings Not Found", "Google Drive settings not found.")
                return
                
            settings_handler = main_window.settings_handler
            client_secret_path = settings_handler.get_setting("google_drive_secret_path", "")
            
            # If the client secret path doesn't exist, try to find a default one
            if not client_secret_path or not os.path.exists(client_secret_path):
                progress.setLabelText("Looking for client secret file...")
                progress.setValue(20)
                
                config_dir = Path.cwd() / "config"
                if config_dir.exists():
                    # Look for client_secret*.json files
                    secret_files = list(config_dir.glob("client_secret*.json"))
                    if secret_files:
                        client_secret_path = str(secret_files[0])
                        logger.info(f"Using default client secret file: {client_secret_path}")
                        # Update the setting for future use
                        settings_handler.set_setting("google_drive_secret_path", client_secret_path)
            
            # If we still don't have a valid client secret file, show settings dialog
            if not client_secret_path or not os.path.exists(client_secret_path):
                progress.close()
                reply = QMessageBox.question(
                    self,
                    "Google Drive Setup Required",
                    "The client secret file for Google Drive authentication was not found.\n\n"
                    "You need to set up Google Drive integration to use this tab fully.\n\n"
                    "Would you like to configure Google Drive settings now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    # Open Google Drive settings dialog
                    from ..dialogs.google_drive_settings_dialog import GoogleDriveSettingsDialog
                    dialog = GoogleDriveSettingsDialog(settings_handler, self)
                    if dialog.exec_():
                        # Retry with new settings
                        client_secret_path = settings_handler.get_setting("google_drive_secret_path", "")
                        if not client_secret_path or not os.path.exists(client_secret_path):
                            QMessageBox.warning(self, "Configuration Failed", 
                                            "Failed to configure Google Drive. Please try again.")
                            return
                    else:
                        return
                else:
                    return
            
            # Update progress
            progress.setLabelText("Authenticating with Google Drive...")
            progress.setValue(30)
            
            # Key change: Add force=True parameter to override the environment variable
            if drive_service.authenticate(force=True):
                # Update progress
                progress.setLabelText("Successfully authenticated, initializing handlers...")
                progress.setValue(50)
                
                # Initialize Google Drive monitor
                xle_folder_id = settings_handler.get_setting("google_drive_xle_folder_id", "")
                if not xle_folder_id:
                    logger.warning("Google Drive XLE folder ID not set, using default")
                    xle_folder_id = "1-0UspcEy9NJjFzMHk7egilqKh-FwhVJW"  # Default XLE files folder ID
                    settings_handler.set_setting("google_drive_xle_folder_id", xle_folder_id)
                
                # Set the authenticated service in the runs_monitor
                self.runs_monitor.set_authenticated_service(drive_service.get_service())
                
                # Update progress
                progress.setLabelText("Downloading data folder from Google Drive...")
                progress.setValue(60)
                
                # Download data folder from Google Drive
                if hasattr(main_window, 'drive_data_handler') and main_window.drive_data_handler:
                    try:
                        # Make sure the data handler is authenticated 
                        main_window.drive_data_handler.authenticate()
                        
                        # Download the data folder
                        success = main_window.drive_data_handler.download_data_folder()
                        if not success:
                            logger.warning("Failed to download data folder from Google Drive")
                    except Exception as e:
                        logger.error(f"Error downloading data folder: {e}")
                        # Continue anyway - non-critical
                
                # Update progress
                progress.setLabelText("Checking for new XLE files...")
                progress.setValue(80)
                
                # Use get_latest_readings instead of check_for_new_files
                try:
                    # Get the current year and month for checking files
                    from datetime import datetime
                    current_year_month = datetime.now().strftime("%Y-%m")
                    self.runs_monitor.get_latest_readings(current_year_month)
                    logger.info(f"Successfully checked for new XLE files for {current_year_month}")
                except Exception as e:
                    logger.error(f"Error checking for new XLE files: {e}")
                    # Continue anyway - non-critical
                
                # Mark as connected and enable UI elements
                self.is_drive_connected = True
                self.enable_google_drive_features()
                
                # Reload runs data
                progress.setLabelText("Reloading run data...")
                progress.setValue(90)
                self.load_existing_runs()
                
                progress.setValue(100)
                progress.close()
                
                QMessageBox.information(self, "Connected", 
                                      "Successfully connected to Google Drive.\nAll features are now available.")
            else:
                progress.close()
                QMessageBox.warning(self, "Connection Failed", 
                                   "Failed to connect to Google Drive.\nSome features will remain limited.")
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            logging.error(f"Error connecting to Google Drive: {e}")
            QMessageBox.critical(self, "Error", f"Error connecting to Google Drive: {str(e)}")

    def update_drive_state(self, is_connected):
        """Update the tab's connection state after authentication from another part of the app"""
        # Only update if the state has changed
        if self.is_drive_connected != is_connected:
            self.is_drive_connected = is_connected
            
            # Update the UI
            self._update_connection_state(is_connected)
            
            # If we just connected, refresh the runs list
            if is_connected:
                # Reload runs list
                self.runs.clear()
                self.runs_dropdown.clear()
                self.runs_dropdown.addItem("Select Run")
                self.load_existing_runs()
                
                # Update runs monitor
                main_window = self.window()
                if hasattr(main_window, 'drive_service'):
                    service = main_window.drive_service.get_service()
                    if service:
                        self.runs_monitor.set_authenticated_service(service)