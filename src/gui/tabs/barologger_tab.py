# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 12:00:52 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                           QPushButton, QLabel, QComboBox, QGroupBox,
                           QTableWidget, QTableWidgetItem, QFileDialog,
                           QMessageBox, QDialog, QMainWindow, QProgressDialog, QHeaderView, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from pathlib import Path
from ..utils.tooltip_info import TooltipInfo
from ..dialogs.barologger_dialog import BarologgerDialog
from ..dialogs.barologger_location_dialog import BarologgerLocationDialog
from ..dialogs.baro_folder_import_dialog import BaroFolderImportDialog  # Add this line
from ..utils.tooltip_info import TooltipInfo
from ...database.models.barologger import BarologgerModel
import sqlite3
from ..dialogs.baro_import_dialog import SingleFileImportDialog
from ..dialogs.auto_update_config_dialog import AutoUpdateConfigDialog
from ..handlers.baro_folder_processor import BaroFolderProcessor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from ..handlers.baro_import_handler import BaroFileProcessor
from ..dialogs.master_baro_dialog import MasterBaroDialog
import matplotlib.dates as mdates
import time
import logging
from ..handlers.water_level_folder_handler import WaterLevelFolderProcessor
from ..handlers.progress_dialog_handler import progress_dialog
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT


logger = logging.getLogger(__name__)


class BarologgerTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.db_manager.database_changed.connect(self.sync_database_selection)
        self.baro_model = None
        self.current_dir = Path(__file__).parent.parent.parent.parent
        self._refresh_scheduled = False  # Flag to track if a refresh is already scheduled
        self.selected_barologgers = set()  # Store currently selected barologgers as a set
        self.is_loading = False  # Flag to track if data loading is in progress

        # Initialize plot components but defer actual plotting
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)

        # Initialize UI elements
        self.master_baro_btn = QPushButton()
        self.baro_table = QTableWidget()
        self.baro_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.baro_table.setSelectionMode(QTableWidget.ExtendedSelection)  # Allow multi-selection
        self.show_temp_btn = QPushButton("Show Temperature")
        self.show_temp_btn.setCheckable(True)

        # Initialize has_master_data but defer checking
        self.has_master_data = False
        logger.debug("__init__: Set has_master_data to False initially")

        # Setup UI (build widgets/layout, set up signals)
        self.setup_ui()

        # Initialize baro_model and load data if database is already set
        if db_manager and db_manager.current_db:
            logger.debug("Initializing with existing database")
            self.baro_model = BarologgerModel(db_manager.current_db)
            # Use QTimer to ensure UI is fully loaded before refreshing
            logger.debug("Scheduling initial_data_load")
            QTimer.singleShot(100, self.initial_data_load)

    def initial_data_load(self):
        """Load initial data and refresh display"""
        try:
            logger.debug("Performing initial data load")
            
            # Apply SQLite optimizations
            try:
                with sqlite3.connect(self.baro_model.db_path) as conn:
                    cursor = conn.cursor()
                    # Optimize SQLite for read operations
                    cursor.execute("PRAGMA temp_store = MEMORY")
                    cursor.execute("PRAGMA cache_size = 10000")
            except Exception as e:
                logger.error(f"Error applying SQLite optimizations: {e}")
            
            # Check for master data efficiently
            try:
                with sqlite3.connect(self.baro_model.db_path) as conn:
                    # First check if table exists
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='master_baro_readings'
                    """)
                    
                    table_exists = cursor.fetchone() is not None
                    if not table_exists:
                        self.master_data = None
                        self.has_master_data = False
                        logger.debug("PERF: Master baro table does not exist")
                    else:
                        # Just check if any data exists rather than loading it all
                        cursor.execute("SELECT COUNT(*) FROM master_baro_readings LIMIT 1")
                        has_rows = cursor.fetchone()[0] > 0
                        
                        if has_rows:
                            self.has_master_data = True
                            # We'll load the actual data later when needed
                            self.master_data = None
                            logger.debug("PERF: Master baro data exists, will load on demand")
                        else:
                            self.has_master_data = False
                            self.master_data = None
                            logger.debug("PERF: Master baro table exists but is empty")
            except Exception as e:
                logger.error(f"Error checking master data: {e}")
                self.has_master_data = False
                self.master_data = None
                
            logger.debug(f"has_master_data set to: {self.has_master_data}")
            
            # Update master baro button text
            master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
            self.master_baro_btn.setText(master_btn_text)
            
            # Set the flag before refreshing
            self._refresh_scheduled = True
            
            # Refresh barologger list without plotting individual barologgers
            self.refresh_barologger_list(skip_plot_refresh=False)
            
            # Reset the flag after refresh
            self._refresh_scheduled = False
            
            logger.debug("Initial data load completed")
        except Exception as e:
            # Reset the flag in case of error
            self._refresh_scheduled = False
            logger.error(f"Error in initial data load: {e}")

    def setup_ui(self):
        """Setup the main UI layout"""
        main_layout = QGridLayout(self)
        main_layout.setSpacing(10)

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
        title_label = QLabel("Barometric Pressure Data Management")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #495057;")
        
        header_layout.addWidget(title_label)
        
        # Add header to grid
        main_layout.addWidget(header_frame, 0, 0, 1, 2)  # Span across both columns

        # Add sections (shifted down one row)
        main_layout.addWidget(self.create_barologger_list_section(), 1, 0)
        main_layout.addWidget(self.create_data_import_section(), 1, 1)

        # Set stretch factors
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

    def create_database_section(self):
        """This method is no longer needed"""
        pass

    def create_barologger_list_section(self) -> QGroupBox:
        """Create barologger list section"""
        group = QGroupBox("Barologger Management")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: white;
                border-radius: 4px;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(8)  # Better spacing
        layout.setContentsMargins(12, 12, 12, 12)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        add_btn = QPushButton("Add Barologger")
        add_btn.setToolTip(TooltipInfo.BARO_ADD)
        add_btn.clicked.connect(self.add_barologger)
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #0056b3;
                border-radius: 6px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #003266;
            }
        """)

        edit_btn = QPushButton("Edit")
        edit_btn.setToolTip(TooltipInfo.BARO_EDIT)
        edit_btn.clicked.connect(self.edit_barologger)
        edit_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-weight: 500;
                min-height: 32px;
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

        delete_btn = QPushButton("Delete")
        delete_btn.setToolTip(TooltipInfo.BARO_DELETE)
        delete_btn.clicked.connect(self.delete_barologger)
        delete_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #c82333;
                border-radius: 6px;
                background-color: #dc3545;
                color: white;
                font-weight: 500;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #c82333;
                border-color: #bd2130;
            }
            QPushButton:pressed {
                background-color: #bd2130;
                border-color: #a71e2a;
            }
        """)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        
        # Add selection info
        self.selection_info = QLabel("0 barologgers selected")
        btn_layout.addWidget(self.selection_info)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

        # Table
        self.baro_table = QTableWidget()
        self.baro_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.baro_table.setSelectionMode(QTableWidget.ExtendedSelection)  # Allow multi-selection
        self.setup_barologger_table()
        self.baro_table.setMinimumHeight(350)  # Increased height to show more rows
        # Connect table item click event
        self.baro_table.itemClicked.connect(self.on_barologger_selected)
        self.baro_table.itemSelectionChanged.connect(self.update_selection_info)
        layout.addWidget(self.baro_table)

        # Add stretch to push icon to bottom
        layout.addStretch()

        # Icon at bottom center
        icon_container = QWidget()
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        icon_path = Path(__file__).parent.parent / "icons" / "Barologger_tab_icon.png"
        pixmap = QPixmap(str(icon_path))
        scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(scaled_pixmap)
        
        # Add stretches on both sides to center horizontally
        icon_layout.addStretch()
        icon_layout.addWidget(icon_label)
        icon_layout.addStretch()
        
        layout.addWidget(icon_container)

        group.setLayout(layout)
        return group

    def create_data_import_section(self) -> QGroupBox:
        group = QGroupBox("Data Import")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: white;
                border-radius: 4px;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Import buttons group
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        import_file_btn = QPushButton("Import Single File")
        import_file_btn.clicked.connect(self.import_single_file)
        import_file_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #0056b3;
                border-radius: 6px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #003266;
            }
        """)
        
        import_folder_btn = QPushButton("Import Folder")
        import_folder_btn.clicked.connect(self.import_folder)
        import_folder_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #0056b3;
                border-radius: 6px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #003266;
            }
        """)
        
        self.master_baro_btn = QPushButton()
        master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
        self.master_baro_btn.setText(master_btn_text)
        self.master_baro_btn.clicked.connect(self.create_master_baro)
        self.master_baro_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #0056b3;
                border-radius: 6px;
                background-color: #007bff;
                color: white;
                font-weight: 500;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #003266;
            }
        """)

        btn_layout.addWidget(import_file_btn)
        btn_layout.addWidget(import_folder_btn)
        # Removed auto_update_btn from layout
        btn_layout.addWidget(self.master_baro_btn)
        layout.addLayout(btn_layout)

        # Plot controls
        plot_controls = QHBoxLayout()
        self.show_temp_btn = QPushButton("Show Temperature")
        self.show_temp_btn.setCheckable(True)
        self.show_temp_btn.clicked.connect(self.toggle_plot_type)
        self.show_temp_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-weight: 500;
                min-height: 32px;
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
        plot_controls.addStretch()
        plot_controls.addWidget(self.show_temp_btn)
        layout.addLayout(plot_controls)

        # Initialize figure
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(600, 400)  # Set minimum size
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        nav_layout = QVBoxLayout()
        nav_layout.addWidget(self.toolbar)
        nav_layout.addWidget(self.canvas)
        layout.addLayout(nav_layout)

        group.setLayout(layout)
        return group

    def toggle_plot_type(self):
        """Toggle between pressure and temperature plots"""
        if self.show_temp_btn.isChecked():
            self.show_temp_btn.setText("Show Pressure")
        else:
            self.show_temp_btn.setText("Show Temperature")
            
        # Only show loading indicator if we have barologgers selected
        if self.selected_barologgers:
            # Show loading indicator while refreshing data
            self.is_loading = True
            progress_dialog.show("Updating plot...", "Please Wait", min_duration=0)
            
            # Use QTimer to ensure UI updates before loading data
            QTimer.singleShot(100, self._refresh_plot_with_loading)
        else:
            # If no barologgers selected, just refresh the plot (faster)
            self.refresh_timeline_plot()
            
    def _refresh_plot_with_loading(self):
        """Refresh plot with loading indicator"""
        try:
            self.refresh_timeline_plot()
        finally:
            # Always close the progress dialog and reset loading flag
            self.is_loading = False
            progress_dialog.close()

    def sync_database_selection(self, db_name: str):
        """Sync database selection and refresh data"""
        sync_start_time = time.time()
        logger.debug(f"PERF: Starting database sync for {db_name}")
        try:
            # Reset selected barologgers when database changes
            self.selected_barologgers.clear()
            reset_start = time.time()
            logger.debug(f"PERF: Reset selected barologgers in {(time.time() - reset_start)*1000:.2f}ms")
            
            # Create new baro model with current database
            model_start = time.time()
            self.baro_model = BarologgerModel(self.db_manager.current_db)
            logger.debug(f"PERF: Created new baro model in {(time.time() - model_start)*1000:.2f}ms")
            
            # Apply SQLite optimizations before loading data
            db_optimize_start = time.time()
            try:
                with sqlite3.connect(self.baro_model.db_path) as conn:
                    cursor = conn.cursor()
                    # Optimize SQLite for read operations
                    cursor.execute("PRAGMA temp_store = MEMORY")
                    cursor.execute("PRAGMA cache_size = 10000")
                    # Don't change journal_mode or synchronous modes as they could affect data integrity
                logger.debug(f"PERF: SQLite optimizations applied in {(time.time() - db_optimize_start)*1000:.2f}ms")
            except Exception as e:
                logger.error(f"Error applying SQLite optimizations: {e}")
            
            # Check for master data - use direct SQL for better performance
            master_start = time.time()
            logger.debug(f"PERF: Starting master data check at {master_start:.3f}s")
            
            try:
                with sqlite3.connect(self.baro_model.db_path) as conn:
                    # First check if table exists
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='master_baro_readings'
                    """)
                    
                    table_exists = cursor.fetchone() is not None
                    if not table_exists:
                        self.master_data = None
                        self.has_master_data = False
                        logger.debug("PERF: Master baro table does not exist")
                    else:
                        # For large databases, just check if any data exists rather than loading it all
                        cursor.execute("SELECT COUNT(*) FROM master_baro_readings LIMIT 1")
                        has_rows = cursor.fetchone()[0] > 0
                        
                        if has_rows:
                            self.has_master_data = True
                            # We'll load the actual data later when needed
                            self.master_data = None  # Will be loaded on demand
                            logger.debug("PERF: Master baro data exists, will load on demand")
                        else:
                            self.has_master_data = False
                            self.master_data = None
                            logger.debug("PERF: Master baro table exists but is empty")
            except Exception as e:
                logger.error(f"Error checking master data: {e}")
                self.has_master_data = False
                self.master_data = None
                
            master_end = time.time()
            logger.debug(f"PERF: Master data check took {(master_end - master_start)*1000:.2f}ms, has_master_data = {self.has_master_data}")
            
            # Update master baro button text
            ui_start = time.time()
            master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
            self.master_baro_btn.setText(master_btn_text)
            logger.debug(f"PERF: Updated UI in {(time.time() - ui_start)*1000:.2f}ms")
            
            # Only schedule a refresh if one isn't already pending
            schedule_start = time.time()
            if not self._refresh_scheduled:
                self._refresh_scheduled = True
                logger.debug("PERF: Scheduling data refresh")
                # Use QTimer to ensure UI update is complete, but only refresh once
                QTimer.singleShot(100, self._do_refresh)
            else:
                logger.debug("PERF: Refresh already scheduled, skipping")
            logger.debug(f"PERF: Scheduling took {(time.time() - schedule_start)*1000:.2f}ms")
            
            sync_end = time.time() 
            logger.debug(f"PERF: Total sync_database_selection took {(sync_end - sync_start_time)*1000:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error syncing database selection: {e}")
            sync_end = time.time()
            logger.debug(f"PERF: sync_database_selection failed after {(sync_end - sync_start_time)*1000:.2f}ms")

    def _do_refresh(self):
        """Execute the refresh and reset the flag"""
        refresh_start = time.time()
        logger.debug("PERF: Starting _do_refresh")
        try:
            # Refresh the barologger list
            list_start = time.time()
            self.refresh_barologger_list(skip_plot_refresh=True)
            logger.debug(f"PERF: refresh_barologger_list took {(time.time() - list_start)*1000:.2f}ms")
            
            # Only refresh the plot if we have master data
            if self.has_master_data:
                plot_start = time.time()
                self.refresh_timeline_plot()
                logger.debug(f"PERF: refresh_timeline_plot took {(time.time() - plot_start)*1000:.2f}ms")
        finally:
            # Always reset the flag, even if refresh fails
            self._refresh_scheduled = False
            refresh_end = time.time()
            logger.debug(f"PERF: Total _do_refresh took {(refresh_end - refresh_start)*1000:.2f}ms")

    def on_database_changed(self, db_name):
        """Handle database change events"""
        logger.debug(f"Database changed to {db_name}")
        if not db_name or db_name == "No databases found":
            return
        
        try:
            # This method is redundant with sync_database_selection
            # Database is already opened by MainWindow, just use the current connection
            logger.debug("on_database_changed called - this is redundant with sync_database_selection")
            self.baro_model = BarologgerModel(self.db_manager.current_db)
            
        except Exception as e:
            logger.error(f"Error handling database change: {e}")
            
    def refresh_data(self):
        """Refresh the barologger list and data display"""
        try:
            logger.debug("Refreshing barologger data")
            # First refresh the list
            self.refresh_barologger_list(skip_plot_refresh=True)
            # Then refresh the plot separately
            self.refresh_timeline_plot()
        except Exception as e:
            logger.error(f"Error refreshing barologger data: {e}")

    def load_databases(self):
        """This method is no longer needed"""
        pass

    def refresh_barologger_list(self, skip_plot_refresh=False):
        """Refresh the barologger list"""
        list_start_time = time.time()
        logger.debug(f"PERF: Starting refresh_barologger_list (skip_plot_refresh={skip_plot_refresh})")
        
        if not self.baro_model:
            logger.warning("PERF: No barologger model available, skipping barologger list refresh")
            self.baro_table.setRowCount(0)
            return

        try:
            # Get all barologgers
            fetch_start = time.time()
            barologgers = self.baro_model.get_all_barologgers()
            fetch_end = time.time()
            logger.debug(f"PERF: Retrieved {len(barologgers)} barologgers in {(fetch_end - fetch_start)*1000:.2f}ms")
            
            # Update table structure
            ui_start = time.time()
            self.baro_table.setRowCount(len(barologgers))
            logger.debug(f"PERF: Set table row count in {(time.time() - ui_start)*1000:.2f}ms")

            # Get last update date for each barologger
            conn_start = time.time()
            with sqlite3.connect(self.baro_model.db_path) as conn:
                logger.debug(f"PERF: Database connection established in {(time.time() - conn_start)*1000:.2f}ms")
                
                # Process all barologgers and calculate average time per barologger
                rows_start = time.time()
                for row, baro in enumerate(barologgers):
                    row_start = time.time()
                    serial = baro['serial_number']
                    
                    # Query to get the last update date
                    query = """
                        SELECT MAX(timestamp_utc) as last_update
                        FROM barometric_readings
                        WHERE serial_number = ?
                    """
                    
                    cursor = conn.cursor()
                    cursor.execute(query, (serial,))
                    result = cursor.fetchone()
                    
                    last_updated = result[0] if result and result[0] else ""
                    
                    # Create items with center alignment
                    for col, value in enumerate([
                        baro['serial_number'],
                        baro['location_description'],
                        baro['status'],
                        str(baro.get('installation_date', '')),
                        baro.get('notes', ''),
                        last_updated  # Use the queried last_updated value
                    ]):
                        item = QTableWidgetItem(value)
                        item.setTextAlignment(Qt.AlignCenter)  # Center align text
                        self.baro_table.setItem(row, col, item)
                    
                    if row == 0 or row == len(barologgers) - 1:
                        logger.debug(f"PERF: Processed barologger row {row} in {(time.time() - row_start)*1000:.2f}ms")
                        
                rows_end = time.time()
                total_rows_time = rows_end - rows_start
                avg_time_per_row = (total_rows_time * 1000) / max(1, len(barologgers))
                logger.debug(f"PERF: Processed all {len(barologgers)} barologger rows in {total_rows_time*1000:.2f}ms, avg {avg_time_per_row:.2f}ms per row")

            # Sort table by serial number
            sort_start = time.time()
            self.baro_table.sortItems(0)
            logger.debug(f"PERF: Sorted table in {(time.time() - sort_start)*1000:.2f}ms")
            
            logger.info("PERF: Barologger list refreshed successfully")
            
            # Update selection status
            selection_start = time.time()
            # Check if the previously selected barologgers still exist
            if self.selected_barologgers:
                selection_update_start = time.time()
                found = False
                for row in range(self.baro_table.rowCount()):
                    if self.baro_table.item(row, 0).text() in self.selected_barologgers:
                        found = True
                        # Highlight the selected rows
                        self.baro_table.selectRow(row)
                        break
                if not found:
                    # Reset selection if the barologgers no longer exist
                    self.selected_barologgers.clear()
                logger.debug(f"PERF: Updated row selection in {(time.time() - selection_update_start)*1000:.2f}ms")
            logger.debug(f"PERF: Selection handling took {(time.time() - selection_start)*1000:.2f}ms")
            
            # Only refresh plot if specifically requested and we're showing master baro or a selected barologger
            plot_refresh_decision_start = time.time()
            should_refresh_plot = (not skip_plot_refresh and (self.has_master_data or self.selected_barologgers))
            logger.debug(f"PERF: Plot refresh decision took {(time.time() - plot_refresh_decision_start)*1000:.2f}ms, should_refresh={should_refresh_plot}")
            
            if should_refresh_plot:
                plot_refresh_start = time.time()
                self.refresh_timeline_plot()
                logger.debug(f"PERF: Timeline plot refresh took {(time.time() - plot_refresh_start)*1000:.2f}ms")
                
            list_end_time = time.time()
            logger.debug(f"PERF: Total refresh_barologger_list took {(list_end_time - list_start_time)*1000:.2f}ms")
                
        except Exception as e:
            logger.error(f"PERF: Error refreshing barologger list: {e}")
            list_end_time = time.time()
            logger.debug(f"PERF: refresh_barologger_list failed after {(list_end_time - list_start_time)*1000:.2f}ms")

    def setup_barologger_table(self):
        """Setup the barologger table structure"""
        headers = [
            "Serial Number", "Location", "Status", "Installation Date",
            "Description", "Last Updated"  # Removed "Master" and "Type" columns
        ]
        self.baro_table.setColumnCount(len(headers))
        self.baro_table.setHorizontalHeaderLabels(headers)
        
        # Configure column resize behavior - resize to content
        header = self.baro_table.horizontalHeader()
        for i in range(len(headers) - 1):  # All columns except last one
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        # Last column stretches to fill remaining space
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.Stretch)
        
        self.baro_table.setMinimumSize(400, 300)  # Set minimum size

    def import_single_file(self):
        """Handle import of single XLE file"""
        if not self.baro_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select XLE File",
            "",
            "XLE files (*.xle)"
        )

        if file_path:
            logger.info(f"Selected file: {file_path}")
            try:
                processor = BaroFileProcessor(self.baro_model)
                logger.info("Created BaroFileProcessor")

                logger.info("Calling validate_baro_file...")
                is_valid, message, metadata = processor.validate_baro_file(Path(file_path))
                logger.info(f"Validation result: {is_valid}, {message}")

                if not is_valid:
                    QMessageBox.warning(self, "Warning", message)
                    return

                # Check if barologgers need registration
                if metadata.get('needs_registration', False):
                    # Fix for single file import - metadata has 'serial_number' not 'serial_numbers'
                    serial_display = metadata.get('serial_number', '')
                    
                    response = QMessageBox.question(
                        self,
                        "Barologger Not Registered",
                        f"Barologger {serial_display} is not registered in the database.\n"
                        "Would you like to register it?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if response == QMessageBox.No:
                        return

                # Show import dialog
                dialog = SingleFileImportDialog(self.baro_model, file_path, self, metadata)
                if dialog.exec_() == QDialog.Accepted:
                    self.refresh_timeline_plot()

            except Exception as e:
                logger.error(f"Error in import_single_file: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to validate file: {e}")

    def configure_auto_update(self):
        if not self.baro_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
        dialog = AutoUpdateConfigDialog(self.baro_model, self)
        dialog.exec_()  # The dialog will handle the refreshes if accepted

    def import_folder(self):
        """Handle import of folder containing XLE files"""
        if not self.baro_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return

        try:
            dialog = BaroFolderImportDialog(
                self.baro_model,
                parent=self
            )
            dialog.exec_()  # The dialog will handle the refreshes if accepted
        except Exception as e:
            logger.error(f"Error importing folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to import folder: {str(e)}")

    def refresh_timeline_plot(self):
        """Refresh the timeline plot with current data"""
        if not hasattr(self, 'figure') or not self.baro_model:
            logger.debug("Skipping plot refresh - no figure or model available")
            return
        logger.debug(f"Starting timeline plot refresh. has_master_data={self.has_master_data}, selected_barologgers={self.selected_barologgers}")
        start_time = time.time()
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                # Set optimized SQLite PRAGMAs for read operations
                cursor = conn.cursor()
                cursor.execute("PRAGMA temp_store = MEMORY")
                cursor.execute("PRAGMA cache_size = 10000")
                
                self.figure.clear()
                self.figure.subplots_adjust(left=0.12)
                ax = self.figure.add_subplot(111)

                has_data = False
                y_min, y_max = float('inf'), float('-inf')

                # Plot master baro data first if exists
                if self.has_master_data:
                    try:
                        logger.debug(f"T+{time.time() - start_time:.3f}s: Starting master data retrieval")
                        # Modified to use julian_timestamp for master_baro_readings
                        query_start_time = time.time()
                        master_query = """
                            SELECT 
                                timestamp_utc, 
                                pressure
                            FROM master_baro_readings
                            ORDER BY julian_timestamp
                        """
                        logger.debug(f"PERF: Master baro query constructed in {(time.time() - query_start_time)*1000:.2f}ms")
                        
                        # Measure just the SQL execution time
                        sql_start_time = time.time()
                        logger.debug(f"PERF: Starting SQL execution for master baro data")
                        master_data = pd.read_sql_query(master_query, conn)
                        sql_end_time = time.time()
                        sql_duration = sql_end_time - sql_start_time
                        logger.debug(f"PERF: SQL execution for master baro took {sql_duration*1000:.2f}ms, returned {len(master_data)} rows")
                        
                        # Log row count and first/last timestamps for debugging
                        if not master_data.empty:
                            first_ts = master_data['timestamp_utc'].iloc[0] if len(master_data) > 0 else "N/A"
                            last_ts = master_data['timestamp_utc'].iloc[-1] if len(master_data) > 0 else "N/A"
                            logger.debug(f"PERF: Master data spans from {first_ts} to {last_ts}")
                        
                        logger.debug(f"T+{time.time() - start_time:.3f}s: Master data loaded in plot refresh, empty: {master_data.empty if master_data is not None else 'None'}")
                        
                        # Additional debugging for master baro data
                        if master_data is not None and not master_data.empty:
                            logger.debug(f"DEBUG: Master baro data shape: {master_data.shape}")
                            logger.debug(f"DEBUG: Master baro pressure range: {master_data['pressure'].min():.2f} to {master_data['pressure'].max():.2f}")
                            logger.debug(f"DEBUG: First 3 rows of master baro data:\n{master_data.head(3)}")
                        
                        if not master_data.empty:
                            # Measure pandas operations
                            process_start = time.time()
                            master_data['timestamp_utc'] = pd.to_datetime(master_data['timestamp_utc'])
                            master_data = master_data.sort_values('timestamp_utc')
                            time_diff = master_data['timestamp_utc'].diff()
                            # Increased gap threshold to 48 hours for daily intervals
                            gaps = time_diff > pd.Timedelta(hours=48)
                            segment_ids = gaps.cumsum()
                            process_end = time.time()
                            logger.debug(f"PERF: Master data processing took {(process_end - process_start)*1000:.2f}ms")
                            
                            logger.debug(f"T+{time.time() - start_time:.3f}s: Starting master baro plotting")
                            plot_start = time.time()
                            for segment_id in segment_ids.unique():
                                segment = master_data[segment_ids == segment_id]
                                ax.plot(
                                    segment['timestamp_utc'],
                                    segment['pressure'],
                                    'k-',  # Changed to solid black line for better visibility
                                    label='Master Baro' if segment_id == 0 else "_nolegend_",
                                    linewidth=1.5,  # Slightly thinner line
                                    zorder=1,  # Lower zorder to be in the background
                                    alpha=0.7  # Slightly transparent to see overlapping data
                                )
                            plot_end = time.time()
                            logger.debug(f"PERF: Master baro plotting took {(plot_end - plot_start)*1000:.2f}ms")
                            
                            has_data = True
                            y_min = min(y_min, master_data['pressure'].min())
                            y_max = max(y_max, master_data['pressure'].max())
                            logger.debug(f"T+{time.time() - start_time:.3f}s: Successfully plotted master baro data")
                    except Exception as e:
                        logger.error(f"Error plotting master baro data: {e}")
                else:
                    logger.debug("Skipping master baro plot - has_master_data is False")

                # Only plot selected barologgers if they exist
                if self.selected_barologgers:
                    logger.debug(f"T+{time.time() - start_time:.3f}s: Plotting {len(self.selected_barologgers)} selected barologgers")
                    
                    # Generate colors for each barologger
                    colors = plt.cm.tab10(np.linspace(0, 1, len(self.selected_barologgers)))
                    
                    # Flag to check if we're showing temperature or pressure
                    show_temperature = self.show_temp_btn.isChecked()
                    data_type = 'temperature' if show_temperature else 'pressure'
                    
                    # Process each selected barologger
                    for i, (serial, color) in enumerate(zip(self.selected_barologgers, colors)):
                        logger.debug(f"T+{time.time() - start_time:.3f}s: Processing barologger {i+1}/{len(self.selected_barologgers)}: {serial}")
                        
                        # Get barologger details
                        barologger = self.baro_model.get_barologger(serial)
                        if barologger and barologger['status'] == 'active':
                            serial = barologger['serial_number']
                            location = barologger['location_description']
                            
                            # Database query timing
                            query_start = time.time()
                            # Modified to use daily intervals for better performance without forcing an index
                            query = f"""
                                SELECT 
                                    MIN(timestamp_utc) as timestamp_utc, 
                                    AVG({data_type}) as {data_type}
                                FROM barometric_readings
                                WHERE serial_number = ?
                                GROUP BY FLOOR(julian_timestamp)
                                ORDER BY julian_timestamp
                            """
                            df = pd.read_sql_query(query, conn, params=(serial,))
                            logger.debug(f"T+{time.time() - start_time:.3f}s: Database query for {serial} completed in {time.time() - query_start:.3f}s, fetched {len(df)} rows")
                            
                            if not df.empty:
                                # Data processing timing
                                process_start = time.time()
                                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                                time_diff = df['timestamp_utc'].diff()
                                # Increased gap threshold to 48 hours for daily intervals
                                gaps = time_diff > pd.Timedelta(hours=48)
                                segment_ids = gaps.cumsum()
                                logger.debug(f"T+{time.time() - start_time:.3f}s: Data processing for {serial} completed in {time.time() - process_start:.3f}s, found {len(segment_ids.unique())} segments")

                                has_data = True
                                label = f"{serial} ({location})"
                                
                                # Plotting timing
                                plot_start = time.time()
                                for segment_id in segment_ids.unique():
                                    segment = df[segment_ids == segment_id]
                                    ax.plot(
                                        segment['timestamp_utc'],
                                        segment[data_type],
                                        color=color,
                                        label=label if segment_id == 0 else "_nolegend_",
                                        linewidth=1
                                    )
                                    curr_min = segment[data_type].min()
                                    curr_max = segment[data_type].max()
                                    if pd.notna(curr_min) and pd.notna(curr_max):
                                        y_min = min(y_min, curr_min)
                                        y_max = max(y_max, curr_max)
                                logger.debug(f"T+{time.time() - start_time:.3f}s: Plotting for {serial} completed in {time.time() - plot_start:.3f}s")

                logger.debug(f"T+{time.time() - start_time:.3f}s: Starting final plot formatting")
                format_start = time.time()
                if has_data:
                    if self.show_temp_btn.isChecked():
                        ax.set_ylabel('Temperature\n(°C)', fontsize=10, labelpad=10)
                    else:
                        ax.set_ylabel('Pressure\n(PSI)', fontsize=10, labelpad=10)

                    if pd.notna(y_min) and pd.notna(y_max):
                        y_range = y_max - y_min
                        ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.5 * y_range)

                    ax.grid(True, linestyle='--', alpha=0.6)
                    ax.tick_params(axis='both', labelsize=9)

                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                    ax.tick_params(axis='x', rotation=45)
                    title = 'Barologger Temperature Data' if self.show_temp_btn.isChecked() else 'Barologger Pressure Data'
                    self.figure.suptitle(title, y=0.95, fontsize=11)

                    # Legend creation timing
                    legend_start = time.time()
                    handles, labels = ax.get_legend_handles_labels()
                    if handles:
                        # Set scrollable legend with smaller font if many items
                        if len(handles) > 8:
                            ax.legend(loc='upper right',
                                     bbox_to_anchor=(0.98, 0.98),
                                     fontsize=8,
                                     framealpha=0.9,
                                     ncol=2 if len(handles) > 12 else 1)
                        else:
                            ax.legend(loc='upper right',
                                     bbox_to_anchor=(0.98, 0.98),
                                     fontsize=9,
                                     framealpha=0.9)
                    logger.debug(f"T+{time.time() - start_time:.3f}s: Legend creation completed in {time.time() - legend_start:.3f}s")
                else:
                    ax.text(0.5, 0.5, 'No data available',
                            ha='center', va='center',
                            transform=ax.transAxes)

                # Layout and render timing
                layout_start = time.time()
                self.figure.tight_layout()
                logger.debug(f"T+{time.time() - start_time:.3f}s: tight_layout completed in {time.time() - layout_start:.3f}s")
                
                render_start = time.time()
                self.canvas.draw()
                logger.debug(f"T+{time.time() - start_time:.3f}s: canvas.draw completed in {time.time() - render_start:.3f}s")
                
                logger.debug(f"T+{time.time() - start_time:.3f}s: Timeline plot refresh completed successfully")
        except Exception as e:
            logger.error(f"Error refreshing timeline plot: {e}")

    def add_barologger(self):
        """Open dialog to add new barologger"""
        if not self.db_manager or not self.db_manager.current_db:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
        if not self.baro_model:
            self.baro_model = BarologgerModel(self.db_manager.current_db)
        dialog = BarologgerDialog(self.baro_model, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_barologger_list()

    def edit_barologger(self):
        """Open dialog to edit selected barologger"""
        if not self.baro_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return

        selected_items = self.baro_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a barologger to edit")
            return
            
        # Use only the first selected row for editing
        row = self.baro_table.row(selected_items[0])
        serial_number = self.baro_table.item(row, 0).text()
        
        barologger = self.baro_model.get_barologger(serial_number)
        if not barologger:
            QMessageBox.critical(self, "Error", f"Could not retrieve data for barologger {serial_number}")
            return

        dialog = BarologgerDialog(self.baro_model, self, barologger)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_barologger_list()

    def delete_barologger(self):
        """Delete selected barologger(s)"""
        if not self.baro_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return

        selected_rows = set()
        for item in self.baro_table.selectedItems():
            selected_rows.add(self.baro_table.row(item))
            
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select barologger(s) to delete")
            return
            
        # Get serial numbers for all selected rows
        serial_numbers = []
        for row in selected_rows:
            serial_numbers.append(self.baro_table.item(row, 0).text())
            
        # Confirm deletion with user
        confirm_text = f"Delete {len(serial_numbers)} selected barologger{'s' if len(serial_numbers) > 1 else ''}?\n\n"
        if len(serial_numbers) <= 5:  # List them individually if 5 or fewer
            confirm_text += "\n".join(serial_numbers)
        else:
            confirm_text += f"{len(serial_numbers)} barologgers will be deleted"
            
        confirm = QMessageBox.question(
            self, "Confirm Deletion", confirm_text,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                for serial in serial_numbers:
                    logger.info(f"Deleting barologger: {serial}")
                    self.baro_model.delete_barologger(serial)
                    
                # Clear the selected_barologgers set to avoid referencing deleted items
                self.selected_barologgers.clear()
                self.refresh_barologger_list()
                QMessageBox.information(self, "Success", f"Successfully deleted {len(serial_numbers)} barologger{'s' if len(serial_numbers) > 1 else ''}")
            except Exception as e:
                logger.error(f"Error deleting barologger: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")

    def create_master_baro(self):
        """Open dialog to create master baro readings"""
        if not self.baro_model:
            QMessageBox.warning(self, "Warning", "Please select a database first")
            return
        
        # Show progress dialog before loading the master baro data
        progress_dialog.show("Loading barologger data for master baro creation...", 
                            "Please Wait", min_duration=0)
        
        try:
            # Update progress as we go
            progress_dialog.update(20, "Initializing master baro dialog...")
            
            # Create the dialog (data loading happens here)
            dialog = MasterBaroDialog(self.baro_model, self)
            
            # Connect to the master_baro_created signal
            dialog.master_baro_created.connect(self.on_master_baro_created)
            
            # Close progress dialog before showing the actual dialog
            progress_dialog.close()
            
            # Show the dialog - result handling is now done through signal connection
            dialog.exec_()
            
        except Exception as e:
            # Make sure to close the dialog if an error occurs
            progress_dialog.close()
            logger.error(f"Error creating master baro dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open master baro dialog: {str(e)}")
            
    def on_master_baro_created(self):
        """Handle the master baro created signal"""
        # Show a progress dialog for reloading data
        progress_dialog.show("Reloading master barometric data...", 
                            "Updating", min_duration=0)
        
        try:
            # Update master baro status
            progress_dialog.update(30, "Loading master baro data...")
            master_data = self.baro_model.get_master_baro_data()
            self.master_data = master_data
            self.has_master_data = not master_data.empty

            # Update button text
            progress_dialog.update(60, "Updating interface...")
            master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
            self.master_baro_btn.setText(master_btn_text)
            
            # Refresh the plot with master baro data only
            progress_dialog.update(90, "Refreshing visualization...")
            self.refresh_timeline_plot()
            logger.debug("Master baro data reloaded successfully")
            
            progress_dialog.close()
        except Exception as e:
            progress_dialog.close()
            logger.error(f"Error reloading master baro data: {e}")
            QMessageBox.warning(self, "Warning", f"Error reloading master baro data: {str(e)}")

    def cleanup(self):
        """Clean up resources before closing"""
        try:
            # Close any open database connections
            if self.baro_model:
                self.baro_model = None

            # Clear matplotlib figure
            if hasattr(self, 'figure'):
                self.figure.clear()
                plt.close(self.figure)

            # Remove canvas
            if hasattr(self, 'canvas'):
                self.canvas.close()

            # Clear tables
            if hasattr(self, 'baro_table'):
                self.baro_table.clearContents()
                self.baro_table.setRowCount(0)

            # Delete widgets
            self.deleteLater()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def refresh_list(self):
        """Alias for refresh_barologger_list for compatibility"""
        self.refresh_barologger_list(skip_plot_refresh=True)  # Skip plot refresh for alias calls

    def load_barologger_list(self):
        """Alias for refresh_barologger_list"""
        self.refresh_barologger_list(skip_plot_refresh=True)  # Skip plot refresh for alias calls

    def downsample_timeseries(self, df, target_points=1000):
        """Downsample a timeseries dataframe to approximately target_points"""
        if len(df) > target_points:
            # Calculate sampling interval to get roughly target_points
            sample_size = len(df) // target_points
            return df.iloc[::sample_size].copy()
        return df

    def update_for_screen(self, screen, layout_only=False):
        """Update layout for the current screen"""
        try:
            logger.debug(f"Updating BarologgerTab layout for screen: {screen.name()}")
            
            # Get screen dimensions
            available_size = screen.availableGeometry().size()
            dpi_factor = screen.devicePixelRatio()
            
            # Update figure size based on screen dimensions
            if hasattr(self, 'figure'):
                # Calculate new figure size in inches (divide pixel size by DPI)
                width_inches = (available_size.width() * 0.6) / (self.figure.dpi * dpi_factor)
                height_inches = (available_size.height() * 0.3) / (self.figure.dpi * dpi_factor)
                self.figure.set_size_inches(width_inches, height_inches)
                
                # Update canvas minimum size
                if hasattr(self, 'canvas'):
                    self.canvas.setMinimumSize(int(available_size.width() * 0.5), 
                                              int(available_size.height() * 0.3))
            
            # Update table dimensions
            if hasattr(self, 'baro_table'):
                self.baro_table.setMinimumSize(int(available_size.width() * 0.3), 
                                              int(available_size.height() * 0.25))
                
            # Force layout update
            if self.layout():
                self.layout().update()
                self.layout().activate()
                
            # Redraw the plot only if not layout_only mode
            if not layout_only:
                self.refresh_timeline_plot()
            else:
                # Just redraw the existing figure without refreshing data
                logger.debug("Skipping data refresh in layout-only mode")
                if hasattr(self, 'canvas'):
                    self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating BarologgerTab for screen change: {e}")

    def on_barologger_selected(self, item):
        """Handle barologger selection from table"""
        # Get all selected rows
        selected_items = self.baro_table.selectedItems()
        
        # Extract serial numbers from the first column of each selected row
        selected_rows = set()
        new_selected_barologgers = set()
        
        for selected_item in selected_items:
            row = self.baro_table.row(selected_item)
            if row not in selected_rows:
                selected_rows.add(row)
                serial_number = self.baro_table.item(row, 0).text()
                new_selected_barologgers.add(serial_number)
        
        # Check if selection has changed
        if new_selected_barologgers != self.selected_barologgers:
            logger.debug(f"Selection changed: {new_selected_barologgers}")
            self.selected_barologgers = new_selected_barologgers
            
            # If we have selections, show loading indicator and refresh plot
            if self.selected_barologgers:
                # Show loading indicator
                self.is_loading = True
                progress_dialog.show("Loading barologger data...", "Please Wait", min_duration=0)
                
                # Use QTimer to ensure UI updates before loading data
                QTimer.singleShot(100, self._load_selected_barologgers)
    
    def _load_selected_barologgers(self):
        """Load data for selected barologgers"""
        try:
            self.refresh_timeline_plot()
        finally:
            # Always close the progress dialog and reset loading flag
            self.is_loading = False
            progress_dialog.close()

    def update_selection_info(self):
        """Update the selection info label"""
        selected_count = len(self.selected_barologgers)
        self.selection_info.setText(f"{selected_count} barologger{'s' if selected_count != 1 else ''} selected")

