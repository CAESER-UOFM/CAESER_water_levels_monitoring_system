# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 12:00:52 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                           QPushButton, QLabel, QComboBox, QGroupBox,
                           QTableWidget, QTableWidgetItem, QFileDialog,
                           QMessageBox, QDialog, QMainWindow, QProgressDialog, QHeaderView)
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


logger = logging.getLogger(__name__)


class BarologgerTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.db_manager.database_changed.connect(self.sync_database_selection)
        self.baro_model = None
        self.current_dir = Path(__file__).parent.parent.parent.parent
        self._refresh_scheduled = False  # Flag to track if a refresh is already scheduled

        # Initialize plot components but defer actual plotting
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)

        # Initialize UI elements
        self.master_baro_btn = QPushButton()
        self.baro_table = QTableWidget()
        self.baro_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.baro_table.setSelectionMode(QTableWidget.SingleSelection)
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
            # Check for master data
            master_data = self.baro_model.get_master_baro_data()
            logger.debug(f"Master data loaded, empty: {master_data.empty if master_data is not None else 'None'}")
            self.master_data = master_data
            self.has_master_data = not master_data.empty if master_data is not None else False
            logger.debug(f"has_master_data set to: {self.has_master_data}")
            
            # Update master baro button text
            master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
            self.master_baro_btn.setText(master_btn_text)
            
            # Set the flag before refreshing
            self._refresh_scheduled = True
            
            # Refresh barologger list
            self.refresh_barologger_list()
            
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

        # Add sections
        main_layout.addWidget(self.create_barologger_list_section(), 0, 0)
        main_layout.addWidget(self.create_data_import_section(), 0, 1)

        # Set stretch factors
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

    def create_database_section(self):
        """This method is no longer needed"""
        pass

    def create_barologger_list_section(self) -> QGroupBox:
        """Create barologger list section"""
        group = QGroupBox("Barologger Management")
        layout = QVBoxLayout()
        layout.setSpacing(2)  # Minimal spacing
        layout.setContentsMargins(5, 5, 5, 5)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Barologger")
        add_btn.setToolTip(TooltipInfo.BARO_ADD)
        add_btn.clicked.connect(self.add_barologger)

        edit_btn = QPushButton("Edit")
        edit_btn.setToolTip(TooltipInfo.BARO_EDIT)
        edit_btn.clicked.connect(self.edit_barologger)

        delete_btn = QPushButton("Delete")
        delete_btn.setToolTip(TooltipInfo.BARO_DELETE)
        delete_btn.clicked.connect(self.delete_barologger)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.baro_table = QTableWidget()
        self.baro_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.baro_table.setSelectionMode(QTableWidget.SingleSelection)
        self.setup_barologger_table()
        self.baro_table.setMinimumHeight(350)  # Increased height to show more rows
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
        scaled_pixmap = pixmap.scaled(300, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        layout = QVBoxLayout()

        # Import buttons group
        btn_layout = QHBoxLayout()

        import_file_btn = QPushButton("Import Single File")
        import_file_btn.clicked.connect(self.import_single_file)
        import_folder_btn = QPushButton("Import Folder")
        import_folder_btn.clicked.connect(self.import_folder)
        self.master_baro_btn = QPushButton()
        master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
        self.master_baro_btn.setText(master_btn_text)
        self.master_baro_btn.clicked.connect(self.create_master_baro)

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
        plot_controls.addStretch()
        plot_controls.addWidget(self.show_temp_btn)
        layout.addLayout(plot_controls)

        # Initialize figure
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(600, 400)  # Set minimum size
        layout.addWidget(self.canvas)

        group.setLayout(layout)
        return group

    def toggle_plot_type(self):
        """Toggle between pressure and temperature plots"""
        if self.show_temp_btn.isChecked():
            self.show_temp_btn.setText("Show Pressure")
        else:
            self.show_temp_btn.setText("Show Temperature")
        self.refresh_timeline_plot()

    def sync_database_selection(self, db_name: str):
        """Sync database selection and refresh data"""
        logger.debug(f"Syncing database selection to {db_name}")
        try:
            # Create new baro model with current database
            self.baro_model = BarologgerModel(self.db_manager.current_db)
            
            # Check for master data
            master_data = self.baro_model.get_master_baro_data()
            self.master_data = master_data
            self.has_master_data = not master_data.empty if master_data is not None else False
            logger.debug(f"sync_database_selection: Updated has_master_data to {self.has_master_data}")
            
            # Update master baro button text
            master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
            self.master_baro_btn.setText(master_btn_text)
            
            # Only schedule a refresh if one isn't already pending
            if not self._refresh_scheduled:
                self._refresh_scheduled = True
                logger.debug("Scheduling data refresh")
                # Use QTimer to ensure UI update is complete, but only refresh once
                QTimer.singleShot(100, self._do_refresh)
            else:
                logger.debug("Refresh already scheduled, skipping")
            
        except Exception as e:
            logger.error(f"Error syncing database selection: {e}")
            
    def _do_refresh(self):
        """Execute the refresh and reset the flag"""
        try:
            self.refresh_data()
        finally:
            # Always reset the flag, even if refresh fails
            self._refresh_scheduled = False

    def on_database_changed(self, db_name):
        """Handle database change events"""
        logger.debug(f"Database changed to {db_name}")
        if not db_name or db_name == "No databases found":
            return
        
        try:
            # This method is likely redundant with sync_database_selection
            # and may be causing duplicate refreshes
            logger.debug("on_database_changed called - this may be redundant with sync_database_selection")
            
            # We'll skip the refresh here since sync_database_selection will handle it
            self.db_manager.open_database(str(self.current_dir / db_name))
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
        if not self.baro_model:
            logger.warning("No barologger model available")
            self.baro_table.setRowCount(0)
            return

        try:
            barologgers = self.baro_model.get_all_barologgers()
            logger.debug(f"Retrieved {len(barologgers)} barologgers")
            
            self.baro_table.setRowCount(len(barologgers))

            # Get last update date for each barologger
            with sqlite3.connect(self.baro_model.db_path) as conn:
                for row, baro in enumerate(barologgers):
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

            # Sort table by serial number
            self.baro_table.sortItems(0)
            
            logger.info("Barologger list refreshed successfully")
            
            # Only refresh plot if not skipped
            if not skip_plot_refresh:
                self.refresh_timeline_plot()
                
        except Exception as e:
            logger.error(f"Error refreshing barologger list: {e}")

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

                # Check if barologger needs registration
                if metadata.get('needs_registration', False):
                    response = QMessageBox.question(
                        self,
                        "Barologger Not Registered",
                        f"Barologger {metadata['serial_number']} is not registered in the database.\n"
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
        logger.debug(f"Starting timeline plot refresh. has_master_data={self.has_master_data}")
        start_time = time.time()
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                self.figure.clear()
                self.figure.subplots_adjust(left=0.12)
                ax = self.figure.add_subplot(111)

                has_data = False
                y_min, y_max = float('inf'), float('-inf')

                # Plot master baro data first if exists
                if self.has_master_data:
                    try:
                        logger.debug(f"T+{time.time() - start_time:.3f}s: Starting master data retrieval")
                        # Modified to use daily intervals for better performance
                        master_query = f"""
                            SELECT 
                                MIN(timestamp_utc) as timestamp_utc, 
                                AVG(pressure) as pressure
                            FROM master_baro_readings
                            GROUP BY strftime('%Y-%m-%d', timestamp_utc)
                            ORDER BY timestamp_utc
                        """
                        master_data = pd.read_sql_query(master_query, conn)
                        logger.debug(f"T+{time.time() - start_time:.3f}s: Master data loaded in plot refresh, empty: {master_data.empty if master_data is not None else 'None'}")
                        if not master_data.empty:
                            master_data['timestamp_utc'] = pd.to_datetime(master_data['timestamp_utc'])
                            master_data = master_data.sort_values('timestamp_utc')
                            time_diff = master_data['timestamp_utc'].diff()
                            # Increased gap threshold to 48 hours for daily intervals
                            gaps = time_diff > pd.Timedelta(hours=48)
                            segment_ids = gaps.cumsum()
                            
                            logger.debug(f"T+{time.time() - start_time:.3f}s: Starting master baro plotting")
                            for segment_id in segment_ids.unique():
                                segment = master_data[segment_ids == segment_id]
                                ax.plot(
                                    segment['timestamp_utc'],
                                    segment['pressure'],
                                    'k--',  # Black dashed line
                                    label='Master Baro' if segment_id == 0 else "_nolegend_",
                                    linewidth=0.8,  # Thinner line
                                    zorder=10,  # Higher zorder to be on top
                                    alpha=0.8  # Slightly transparent
                                )
                            
                            has_data = True
                            y_min = min(y_min, master_data['pressure'].min())
                            y_max = max(y_max, master_data['pressure'].max())
                            logger.debug(f"T+{time.time() - start_time:.3f}s: Successfully plotted master baro data")
                    except Exception as e:
                        logger.error(f"Error plotting master baro data: {e}")
                else:
                    logger.debug("Skipping master baro plot - has_master_data is False")

                # Get active barologgers
                logger.debug(f"T+{time.time() - start_time:.3f}s: Retrieving active barologgers")
                active_barologgers = [b for b in self.baro_model.get_all_barologgers(log_count=False) if b['status'] == 'active']
                barologgers = [(b['serial_number'], b['location_description']) for b in active_barologgers]
                logger.debug(f"T+{time.time() - start_time:.3f}s: Found {len(barologgers)} active barologgers")

                if barologgers:
                    colors = plt.cm.tab10(np.linspace(0, 1, len(barologgers)))
                    show_temperature = self.show_temp_btn.isChecked()
                    data_type = 'temperature' if show_temperature else 'pressure'

                    for i, ((serial, location), color) in enumerate(zip(barologgers, colors)):
                        logger.debug(f"T+{time.time() - start_time:.3f}s: Starting processing for barologger {i+1}/{len(barologgers)}: {serial}")
                        
                        # Database query timing
                        query_start = time.time()
                        # Modified to use daily intervals for better performance
                        query = f"""
                            SELECT 
                                MIN(timestamp_utc) as timestamp_utc, 
                                AVG({data_type}) as {data_type}
                            FROM barometric_readings
                            WHERE serial_number = ?
                            GROUP BY strftime('%Y-%m-%d', timestamp_utc)
                            ORDER BY timestamp_utc
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
                    title = 'Barologger Temperature Data' if show_temperature else 'Barologger Pressure Data'
                    self.figure.suptitle(title, y=0.95, fontsize=11)

                    # Legend creation timing
                    legend_start = time.time()
                    handles, labels = ax.get_legend_handles_labels()
                    if handles:
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

        current_row = self.baro_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a barologger to edit")
            return

        serial_number = self.baro_table.item(current_row, 0).text()
        barologger = self.baro_model.get_barologger(serial_number)
        if not barologger:
            QMessageBox.critical(self, "Error", f"Could not retrieve data for barologger {serial_number}")
            return

        dialog = BarologgerDialog(self.baro_model, self, barologger)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_barologger_list()

    def delete_barologger(self):
        """Delete selected barologger and all its data"""
        current_row = self.baro_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a barologger to delete")
            return

        serial_number = self.baro_table.item(current_row, 0).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete barologger {serial_number} and ALL its associated data?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success, message = self.baro_model.delete_barologger(serial_number)
            if success:
                self.refresh_barologger_list()
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.critical(self, "Error", message)

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
            
            # Close progress dialog before showing the actual dialog
            progress_dialog.close()
            
            # Show the dialog
            if dialog.exec_() == QDialog.Accepted:
                # Update master baro status
                master_data = self.baro_model.get_master_baro_data()
                self.master_data = master_data
                self.has_master_data = not master_data.empty

                # Update button text
                master_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
                self.master_baro_btn.setText(master_btn_text)
                self.refresh_timeline_plot()
                logger.debug("Master baro dialog closed successfully, plot refreshed")
        except Exception as e:
            # Make sure to close the dialog if an error occurs
            progress_dialog.close()
            logger.error(f"Error creating master baro dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open master baro dialog: {str(e)}")

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