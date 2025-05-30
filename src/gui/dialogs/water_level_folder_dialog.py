from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QTableWidget, QTableWidgetItem, QCheckBox,
                           QProgressBar, QMessageBox, QGroupBox, QHeaderView, QFileDialog, QWidget, QSizePolicy, QRadioButton)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from pathlib import Path
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from ..handlers.water_level_folder_handler import WaterLevelFolderProcessor
from .water_level_preview_dialog import WaterLevelPreviewDialog
from .water_level_progress_dialog import WaterLevelProgressDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.widgets import Cursor
from PyQt5.QtGui import QIcon
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

class DetailedPlotDialog(QDialog):
    def __init__(self, data, well_number, parent=None):
        super().__init__(parent)
        self.data = data
        self.well_number = well_number
        self.selected_point = None
        self.annotation = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Detailed View - Well {self.well_number}")
        self.resize(1200, 800)
        layout = QVBoxLayout(self)
        
        # Create figure with larger size
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Plot data
        self.plot_data()
        
        # Connect events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        
    def plot_data(self):
        """Plot data with detailed labels in full view"""
        self.ax.clear()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        if 'processed_data' in self.data:
            # Get existing data first for context
            existing_data = self.parent().water_level_model.get_readings(self.well_number)
            if not existing_data.empty:
                existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])
                self.ax.plot(existing_data['timestamp_utc'], existing_data['water_level'],
                           color='gray', alpha=0.3, linewidth=0.5, label='Existing',
                           zorder=1)  # Lowest layer

            # Plot processed segments
            df = self.data['processed_data']
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
            
            # Plot by level method to show different sources
            method_colors = {
                'predicted': '#1f77b4',
                'manual_readings': '#2ca02c',
                'existing_mean': '#ff7f0e',
                'default_level': '#d62728'
            }
            
            for method in df['level_flag'].unique():
                mask = df['level_flag'] == method
                method_data = df[mask]
                color = method_colors.get(method, colors[0])
                self.ax.plot(method_data['timestamp_utc'], method_data['water_level'], 
                           color=color, label=method, linewidth=1.5,
                           zorder=2)  # Middle layer
            
            # Plot insertion points last and above the line
            mask = df['timestamp_utc'] == df['insertion_time']
            if mask.any():
                self.ax.scatter(df.loc[mask, 'timestamp_utc'],
                             df.loc[mask, 'water_level'],
                             color='red', marker='*', s=150,
                             label='Insertion Points',
                             zorder=3,  # Top layer
                             edgecolor='black', linewidth=1)  # Added border

            self.ax.set_ylabel('Water Level (ft)')
            title = f"Well {self.well_number} - Processed Water Levels"
            if self.data.get('has_overlap'):
                title += " (Has Overlaps)"
            self.ax.set_title(title)
        else:
            # Before processing - show raw pressure with detailed labels
            for idx, file_path in enumerate(self.data['files']):
                df, metadata = self.parent().processor.solinst_reader.read_xle(file_path)
                color = colors[idx % len(colors)]
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                # Detailed label for full view
                label = (f"File {idx+1}: {df['timestamp_utc'].min().strftime('%Y-%m-%d')} to "
                        f"{df['timestamp_utc'].max().strftime('%Y-%m-%d')} "
                        f"(SN: {metadata.serial_number})")
                self.ax.plot(df['timestamp_utc'], df['pressure'], 
                           color=color, label=label, linewidth=1.5)

            self.ax.set_ylabel('Pressure (PSI)')
            self.ax.set_title(f"Well {self.well_number} - Raw Pressure Data")
        
        # Show overlap regions in both cases
        if self.data.get('has_overlap'):
            overlap_start, overlap_end = self.data['overlap_range']
            self.ax.axvspan(overlap_start, overlap_end,
                         color='yellow', alpha=0.2,
                         label='Overlap Region')

        # Common formatting
        self.ax.set_xlabel('Time (UTC)')
        self.ax.grid(True, which='major', linestyle='--', alpha=0.6)
        self.ax.grid(True, which='minor', linestyle=':', alpha=0.3)
        
        # Format x-axis to show dates nicely
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # Rotate and align the tick labels so they look better
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
        
        # Add legend with better placement and formatting
        self.ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', 
                     title="Data Sources", frameon=True, 
                     fancybox=True, shadow=True)
        
        # Adjust layout to prevent label cutoff
        self.figure.tight_layout()
        self.canvas.draw()
        
    def on_click(self, event):
        if event.inaxes != self.ax:
            return
            
        # Find closest point
        lines = self.ax.get_lines()
        min_dist = float('inf')
        closest_point = None
        
        for line in lines:
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            
            # Convert data coordinates to display coordinates
            display_coords = self.ax.transData.transform(list(zip(mdates.date2num(xdata), ydata)))
            distances = np.sqrt((display_coords[:, 0] - event.x) ** 2 + 
                              (display_coords[:, 1] - event.y) ** 2)
            
            idx = np.argmin(distances)
            if distances[idx] < min_dist:
                min_dist = distances[idx]
                closest_point = (xdata[idx], ydata[idx])
        
        if closest_point and min_dist < 50:  # Threshold in display coordinates
            if self.annotation:
                self.annotation.remove()
            
            # Format timestamp
            timestamp = closest_point[0]
            if isinstance(timestamp, np.datetime64):
                timestamp = pd.Timestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            self.annotation = self.ax.annotate(
                f'Time: {timestamp}\nValue: {closest_point[1]:.3f}',
                xy=closest_point,
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
            self.canvas.draw()
            
    def on_hover(self, event):
        if event.inaxes != self.ax:
            return
            
        # Update cursor to show it's interactive
        self.canvas.setCursor(Qt.CrossCursor)

class WaterLevelFolderDialog(QDialog):
    def __init__(self, water_level_model, parent=None):
        super().__init__(parent)
        self.water_level_model = water_level_model
        self.folder_path = None  # Initialize as None since we select it in dialog
        self.processor = WaterLevelFolderProcessor(water_level_model)
        self.data = None
        
        self.setup_ui()  # Set up UI before processing any folder

    def set_button_width_with_padding(self, button, padding=20):
        """Set button width based on content plus padding"""
        hint = button.sizeHint()
        button.setFixedWidth(hint.width() + padding)

    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("Import Folder Data")
        self.resize(1200, 800)
        self.setMinimumSize(1200, 800)
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
        button_layout.setSpacing(2)  # Very tight spacing between these controls
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

        # Check mode panel has been removed

        # Info section
        info_group = QGroupBox("Data Information")
        info_layout = QVBoxLayout()
        self.status_label = QLabel()
        info_layout.addWidget(self.status_label)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Split view for table and plot
        content_layout = QHBoxLayout()

        # Wells table
        table_group = QGroupBox("Wells Found")
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(4, 4, 4, 4)  # Reduce margins
        self.wells_table = QTableWidget()
        self.setup_wells_table()
        table_layout.addWidget(self.wells_table)
        table_group.setLayout(table_layout)
        table_group.setMaximumWidth(400)  # Limit table width
        content_layout.addWidget(table_group)

        # Plot area
        plot_group = QGroupBox("Data Preview")
        plot_layout = QVBoxLayout()
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        # Add Full View button to toolbar
        self.full_view_btn = QPushButton()
        self.full_view_btn.setToolTip("Open in Full View")
        self.full_view_btn.setText("Full View")
        self.full_view_btn.setFixedWidth(100)
        self.full_view_btn.clicked.connect(self.show_full_view)
        self.toolbar.addWidget(self.full_view_btn)
        
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)
        content_layout.addWidget(plot_group, 1)  # Give plot all remaining space

        main_layout.addLayout(content_layout)
        
        # Bottom controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        self.process_btn = QPushButton("Process Files")
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setEnabled(False)
        
        self.import_btn = QPushButton("Import Selected")
        self.import_btn.clicked.connect(self.import_selected)
        self.import_btn.setEnabled(False)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        # Set dynamic widths with padding for bottom buttons
        self.set_button_width_with_padding(self.process_btn, 30)
        self.set_button_width_with_padding(self.import_btn, 30)
        self.set_button_width_with_padding(cancel_btn, 30)
        
        controls_layout.setContentsMargins(0, 0, 12, 0)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.process_btn)
        controls_layout.addWidget(self.import_btn)
        controls_layout.addWidget(cancel_btn)
        main_layout.addLayout(controls_layout)

    def setup_wells_table(self):
        """Setup the wells table structure"""
        headers = ["Include", "Overwrite", "Well Number", "CAE", "Files"]
        self.wells_table.setColumnCount(len(headers))
        self.wells_table.setHorizontalHeaderLabels(headers)
        self.wells_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.wells_table.setSelectionMode(QTableWidget.SingleSelection)  # Only allow single row selection
        
        # Set table properties
        self.wells_table.setShowGrid(True)
        self.wells_table.setAlternatingRowColors(True)
        self.wells_table.verticalHeader().setVisible(False)  # Hide row numbers
        self.wells_table.setWordWrap(False)  # Prevent text wrapping
        
        # Center align headers
        for i in range(len(headers)):
            self.wells_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        # Set fixed widths for certain columns
        self.wells_table.setColumnWidth(0, 70)  # Include
        self.wells_table.setColumnWidth(1, 80)  # Overwrite
        self.wells_table.setColumnWidth(4, 60)  # Files
        
        # Set column resize modes
        self.wells_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # Include
        self.wells_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)  # Overwrite
        self.wells_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Well Number
        self.wells_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # CAE
        self.wells_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)  # Files
        
        # Prevent table from expanding beyond its container
        self.wells_table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Make the table adjust to the available space
        self.wells_table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.wells_table.horizontalHeader().setStretchLastSection(False)
        
        self.wells_table.itemSelectionChanged.connect(self.on_selection_changed)

    def process_folder(self):
        """Process folder contents"""
        try:
            self.data = self.processor.scan_folder(self.folder_path)
            
            if not self.data:
                QMessageBox.critical(self, "Error", "No valid water level files found in folder")
                self.reject()
                return
            
            self.populate_wells_table()
            self.update_status()
            
        except Exception as e:
            logger.error(f"Error processing folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process folder: {str(e)}")
            self.reject()
            
    def populate_wells_table(self):
        """Fill wells table with data"""
        self.wells_table.setRowCount(len(self.data))
        
        for row, (well_number, info) in enumerate(self.data.items()):
            # Include checkbox
            include_cb = QCheckBox()
            include_cb.setChecked(True)  # Initially checked
            include_cb.setEnabled(True)  # Enable for selection before processing
            include_widget = QWidget()
            layout = QHBoxLayout(include_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(include_cb)
            layout.setAlignment(Qt.AlignCenter)
            self.wells_table.setCellWidget(row, 0, include_widget)
            
            # Overwrite checkbox
            overlap_cb = QCheckBox()
            overlap_cb.setEnabled(False)  # Initially disabled
            overlap_cb.setChecked(False)
            overlap_widget = QWidget()
            layout = QHBoxLayout(overlap_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(overlap_cb)
            layout.setAlignment(Qt.AlignCenter)
            self.wells_table.setCellWidget(row, 1, overlap_widget)
            
            # Well Number
            well_item = QTableWidgetItem(well_number)
            well_item.setTextAlignment(Qt.AlignCenter)
            self.wells_table.setItem(row, 2, well_item)
            
            # CAE Number (from metadata)
            cae = info['metadata'].location if info['metadata'] else ""
            cae_item = QTableWidgetItem(cae)
            cae_item.setTextAlignment(Qt.AlignCenter)
            self.wells_table.setItem(row, 3, cae_item)
            
            # Files count
            files_item = QTableWidgetItem(str(len(info['files'])))
            files_item.setTextAlignment(Qt.AlignCenter)
            self.wells_table.setItem(row, 4, files_item)
            
    def update_status(self):
        """Update status information"""
        total_wells = len(self.data)
        total_files = sum(len(info['files']) for info in self.data.values())
        overlaps = sum(1 for info in self.data.values() if info['has_overlap'])
        
        status = f"Found {total_files} files for {total_wells} wells. "
        if overlaps:
            status += f"{overlaps} wells have overlapping data."
            
        self.status_label.setText(status)
        
    def show_well_plot(self, well_number: str):
        """Show plot dialog for selected well"""
        try:
            dialog = WaterLevelPreviewDialog(
                well_number=well_number,
                well_data=self.data[well_number],
                parent=self
            )
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing plot for well {well_number}: {e}")
            
    def import_selected(self):
        """Import selected well data"""
        try:
            # Get selected wells that have been processed
            wells_to_import = []
            for row in range(self.wells_table.rowCount()):
                include_widget = self.wells_table.cellWidget(row, 0)
                include_cb = include_widget.findChild(QCheckBox)
                if include_cb and include_cb.isChecked():
                    well_number = self.wells_table.item(row, 2).text()
                    if self.data[well_number].get('has_been_processed', False):
                        overwrite_widget = self.wells_table.cellWidget(row, 1)
                        overwrite_cb = overwrite_widget.findChild(QCheckBox)
                        overwrite = overwrite_cb.isChecked() if overwrite_cb else False
                        wells_to_import.append((well_number, overwrite))

            if not wells_to_import:
                QMessageBox.warning(self, "Warning", "No processed wells selected for import")
                return

            # Show progress dialog
            progress_dialog = WaterLevelProgressDialog(self)
            progress_dialog.setWindowTitle("Importing Data")
            progress_dialog.show()
            QApplication.processEvents()

            total_imported = 0
            total_readings = sum(len(self.data[well_number]['processed_data']) for well_number, _ in wells_to_import)
            processed_readings = 0
            progress_dialog.update_progress(0, total_readings)
            
            # Track which wells were successfully imported
            successfully_imported_wells = []

            for idx, (well_number, overwrite) in enumerate(wells_to_import, 1):
                try:
                    progress_dialog.update_status(f"Importing well {well_number} ({idx}/{len(wells_to_import)})")
                    progress_dialog.log_message(f"\n=== Importing {well_number} ===")
                    
                    # Use the exact same data we're plotting successfully
                    df = self.data[well_number]['processed_data']
                    progress_dialog.log_message(f"Importing {len(df)} readings")
                    
                    if overwrite:
                        progress_dialog.log_message("Overwriting existing data")
                    else:
                        progress_dialog.log_message("Skipping overlapping data")
                    
                    # Import all data for the well in a single batch for better performance
                    success = self.water_level_model.import_readings(
                        well_number,
                        df,
                        overwrite
                    )
                    if not success:
                        progress_dialog.log_message(f"Failed to import data for well {well_number}")
                    else:
                        processed_readings += len(df)
                        progress_dialog.update_progress(processed_readings, total_readings)
                        progress_dialog.log_message(f"Imported {len(df)} readings for well {well_number}")
                        QApplication.processEvents()
                    
                    if success:
                        total_imported += 1
                        successfully_imported_wells.append(well_number)  # Add to successful list
                        progress_dialog.log_message(f"Successfully imported data for well {well_number}")
                        # Update per-well flag summary in wells table after import
                        try:
                            self.water_level_model.update_well_flags(well_number)
                        except Exception as e:
                            logger.error(f"Error updating well flags after folder import for {well_number}: {e}")
                    else:
                        progress_dialog.log_message(f"Failed to import data for well {well_number}")
                    
                except Exception as e:
                    progress_dialog.log_message(f"Error importing well {well_number}: {str(e)}")
                    logger.error(f"Error importing well {well_number}: {e}", exc_info=True)
                    continue

            # Only organize files for wells that were successfully imported
            if successfully_imported_wells:
                progress_dialog.log_message("\n=== Organizing Files ===")
                progress_dialog.update_status("Organizing files...")
                
                try:
                    # Import file organizer here to ensure it's available
                    from ..utils.file_organizer import XLEFileOrganizer
                    app_root_dir = Path(__file__).parent.parent.parent.parent
                    
                    # Create file organizer
                    organizer = XLEFileOrganizer(app_root_dir, db_name=Path(self.water_level_model.db_path).stem)
                    logger.warning("FILE_ORG_IMPORT: Created file organizer")
                    progress_dialog.log_message(f"File organizer created with root: {app_root_dir}")
                    
                    # Process only wells that were successfully imported
                    for well_idx, well_number in enumerate(successfully_imported_wells, 1):
                        if not self.data[well_number].get('has_been_processed', False):
                            continue
                        
                        logger.warning(f"FILE_ORG_IMPORT: Processing files for well {well_number}")
                        progress_dialog.log_message(f"\nOrganizing files for well {well_number} ({well_idx}/{len(successfully_imported_wells)})")
                        
                        # Process each file for this well
                        for file_idx, file_path in enumerate(self.data[well_number]['files'], 1):
                            if not file_path.exists():
                                logger.error(f"FILE_ORG_IMPORT: File does not exist: {file_path}")
                                progress_dialog.log_message(f"Error: File does not exist: {file_path}")
                                continue
                            
                            logger.warning(f"FILE_ORG_IMPORT: Processing file {file_path}")
                            progress_dialog.log_message(f"Processing file {file_idx}/{len(self.data[well_number]['files'])}: {file_path.name}")
                            
                            try:
                                # Get file metadata for organization
                                metadata, _ = self.processor.solinst_reader.get_file_metadata(file_path)
                                
                                # Get timestamp range from this file's metadata
                                file_start_date = pd.to_datetime(metadata.start_time)
                                file_end_date = pd.to_datetime(metadata.stop_time)
                                
                                # Check if this is a barologger (which should be rare)
                                is_baro = self.processor.solinst_reader.is_barologger(metadata)
                                
                                # Log what we're going to do
                                progress_dialog.log_message(f"  Serial: {metadata.serial_number}")
                                progress_dialog.log_message(f"  Location: {metadata.location}")
                                progress_dialog.log_message(f"  Date Range: {file_start_date} to {file_end_date}")
                                progress_dialog.log_message(f"  Barologger: {'Yes' if is_baro else 'No'}")
                                
                                # Organize the file
                                logger.warning(f"FILE_ORG_IMPORT: About to organize file {file_path.name}, is_baro={is_baro}")
                                
                                if is_baro:
                                    # For barologgers (rare in water level import)
                                    result_path = organizer.organize_barologger_file(
                                        file_path,
                                        metadata.serial_number,
                                        metadata.location,
                                        file_start_date,
                                        file_end_date
                                    )
                                else:
                                    # For transducers (typical case)
                                    result_path = organizer.organize_transducer_file(
                                        file_path,
                                        metadata.serial_number,
                                        metadata.location,
                                        file_start_date,
                                        file_end_date,
                                        well_number  # Pass well number for folder organization
                                    )
                                
                                logger.warning(f"FILE_ORG_IMPORT: Result path: {result_path}")
                                
                                if result_path:
                                    progress_dialog.log_message(f"  Successfully organized to: {result_path}")
                                else:
                                    progress_dialog.log_message(f"  Warning: File organization returned None")
                                    
                            except Exception as e:
                                logger.error(f"FILE_ORG_IMPORT: Error organizing file {file_path}: {e}", exc_info=True)
                                progress_dialog.log_message(f"  Error organizing file: {str(e)}")
                        
                        progress_dialog.update_progress(well_idx, len(successfully_imported_wells))
                        QApplication.processEvents()
                        
                except Exception as e:
                    error_msg = f"Error organizing files: {str(e)}"
                    logger.error(f"FILE_ORG_IMPORT: {error_msg}", exc_info=True)
                    progress_dialog.log_message(error_msg)
            else:
                progress_dialog.log_message("\n=== No Wells Successfully Imported ===")
                progress_dialog.log_message("Skipping file organization since no wells were successfully imported.")

            # Final summary
            progress_dialog.log_message(f"\n=== Import Complete ===")
            progress_dialog.log_message(f"Successfully imported {total_imported} of {len(wells_to_import)} wells")
            progress_dialog.log_message(f"Total readings imported: {processed_readings}")
            progress_dialog.update_status("Import complete")
            progress_dialog.finish_operation()

            if total_imported > 0:
                # Refresh parent UI so wells table icons update
                parent = self.parent()
                if parent:
                    try:
                        parent.update_plot()
                    except Exception:
                        pass
                    try:
                        parent.refresh_wells_table()
                    except Exception:
                        pass
                self.accept()

        except Exception as e:
            logger.error(f"Error in import_selected: {e}", exc_info=True)
            if progress_dialog:
                progress_dialog.log_message(f"Error during import: {str(e)}")
                progress_dialog.finish_operation()
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")

    def on_selection_changed(self):
        """Handle selection changes in the wells table"""
        try:
            selected_items = self.wells_table.selectedItems()
            if not selected_items:
                return

            # Get well number from selected row
            row = selected_items[0].row()
            well_number = self.wells_table.item(row, 2).text()  # Well Number is in column 2
            
            # Update plot for selected well
            if (well_number in self.data):
                self.preview_data(well_number)
                
        except Exception as e:
            logger.error(f"Error handling selection change: {e}")
            
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
                    # Color by data source
                    # for source in existing_data['data_source'].unique():
                    #     mask = existing_data['data_source'] == source
                    #     ax.plot(existing_data[mask]['timestamp_utc'], 
                    #            existing_data[mask]['water_level'],
                    #            color='gray', alpha=0.3, linewidth=0.5, 
                    #            label=f'Existing ({source})',
                    #            zorder=1)

                # Plot processed segments
                df = well_data['processed_data']
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                
                # Downsample data for preview if too many points
                if len(df) > 1000:
                    df = df.iloc[::len(df)//1000]
                
                # Method colors mapping
                method_colors = {
                    'predicted': '#1f77b4',
                    'manual_readings': '#2ca02c',
                    'existing_mean': '#ff7f0e',
                    'default_level': '#d62728'
                }
                
                # Sort by timestamp to ensure chronological order
                df = df.sort_values('timestamp_utc')
                
                # Plot as a continuous series with changing colors based on method
                # First plot the complete line in a light gray as a background
                ax.plot(df['timestamp_utc'], df['water_level'], 
                       color='lightgray', alpha=0.5, linewidth=1.0,
                       zorder=1)
                
                # Then plot each segment with the appropriate color
                methods = df['level_flag'].unique()
                for method in methods:
                    # Create a new dataframe with NaN values where the method doesn't match
                    method_df = df.copy()
                    method_df.loc[method_df['level_flag'] != method, 'water_level'] = float('nan')
                    
                    # Plot only the non-NaN segments with the method color
                    color = method_colors.get(method, colors[0])
                    ax.plot(method_df['timestamp_utc'], method_df['water_level'], 
                           color=color, label=f'New ({method})', linewidth=1.5,
                           zorder=2)

                # Plot first point of each file
                for idx, file_path in enumerate(well_data['files']):
                    try:
                        # Read the raw file data
                        file_df, metadata = self.processor.solinst_reader.read_xle(file_path)
                        file_df['timestamp_utc'] = pd.to_datetime(file_df['timestamp_utc'])
                        
                        # Get first point from raw data
                        first_point = file_df.iloc[0]
                        first_time = first_point['timestamp_utc']
                        
                        # Find corresponding water level in processed data with a small time tolerance
                        time_tolerance = pd.Timedelta(seconds=1)
                        first_mask = (df['timestamp_utc'] >= first_time - time_tolerance) & (df['timestamp_utc'] <= first_time + time_tolerance)
                        
                        if first_mask.any():
                            water_level = df.loc[first_mask, 'water_level'].iloc[0]
                            # Only add label for the first point, others will use the same label
                            label = 'Starting Points' if idx == 0 else None
                            ax.scatter(first_time, water_level,
                                     color='red', marker='o', s=65,
                                     label=label,
                                     zorder=4,  # Top layer
                                     edgecolor='black', linewidth=1)
                    except Exception as e:
                        logger.error(f"Error plotting points for file {file_path}: {e}")
                        continue
                
                # Get and plot manual readings within the time range
                time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
                manual_readings = self.processor.processor._get_manual_readings(well_number, time_range)
                
                if not manual_readings.empty:
                    manual_readings['measurement_date_utc'] = pd.to_datetime(manual_readings['measurement_date_utc'])
                    ax.scatter(manual_readings['measurement_date_utc'],
                             manual_readings['water_level'],
                             color='green', marker='^', s=65,  # Reduced from 100
                             label='Manual Readings',
                             zorder=5,  # Top layer
                             edgecolor='black', linewidth=1)
                
                # Plot insertion points if available
                insertion_time_col = 'insertion_time_utc' if 'insertion_time_utc' in df.columns else 'insertion_time'
                if insertion_time_col in df.columns:
                    mask = df['timestamp_utc'] == df[insertion_time_col]
                    if mask.any():
                        ax.scatter(df.loc[mask, 'timestamp_utc'],
                                 df.loc[mask, 'water_level'],
                                 color='red', marker='*', s=98,  # Reduced from 150
                                 label='Insertion Points',
                                 zorder=3,  # Top layer
                                 edgecolor='black', linewidth=1)

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
            # Shorten path if too long by showing only last parts
            path_str = str(self.folder_path)
            if len(path_str) > 50:
                parts = path_str.split('\\')
                if len(parts) > 3:
                    path_str = "..." + '\\'.join(parts[-3:])  # Keep the ... in path shortening
            self.folder_label.setText(path_str)
            self.folder_label.setToolTip(str(self.folder_path))  # Show full path on hover
            self.scan_btn.setEnabled(True)
            # Clear previous results
            self.data = None
            self.wells_table.setRowCount(0)
            self.status_label.clear()
            self.figure.clear()
            self.canvas.draw()

    def scan_folder(self):
        """Scan folder for files and group by well"""
        if not self.folder_path:
            QMessageBox.warning(self, "Warning", "Please select a folder first")
            return

        # Always use double check mode (Serial + CAE) since check mode panel has been removed
        check_mode = 'double'

        # Show progress dialog
        progress_dialog = WaterLevelProgressDialog(self)
        progress_dialog.setWindowTitle("Scanning Folder")
        progress_dialog.show()
        QApplication.processEvents()

        try:
            # Pass check mode to scan_folder
            self.data = self.processor.scan_folder(
                self.folder_path,
                self.subfolder_cb.isChecked(),
                progress_dialog,
                check_mode
            )
            
            if not self.data:
                progress_dialog.close()
                return
            
            self.populate_wells_table()
            self.update_status()
            
            # Enable process button if we have valid data
            self.process_btn.setEnabled(bool(self.data))
            
            # Prepare plot preview (90%)
            progress_dialog.update_status("Preparing data preview...")
            progress_dialog.update_progress(90, 100)
            
            # Auto-select and preview first well
            if self.wells_table.rowCount() > 0:
                self.wells_table.selectRow(0)
                well_number = self.wells_table.item(0, 2).text()  # Well number is in column 2
                progress_dialog.update_status("Generating preview plot...")
                self.preview_data(well_number)
            
            # Finalize (100%)
            progress_dialog.update_status("Scan complete")
            progress_dialog.update_progress(100, 100)
            QApplication.processEvents()
            
            # Keep dialog open and change to Close button
            progress_dialog.finish_operation()
            
        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to scan folder: {str(e)}")

    def process_files(self):
        """Process files"""
        try:
            logger.info("Starting file processing...")
            progress_dialog = WaterLevelProgressDialog(self)
            progress_dialog.setWindowTitle("Processing Files")
            progress_dialog.show()
            QApplication.processEvents()

            # Get selected wells to process
            wells_to_process = []
            for row in range(self.wells_table.rowCount()):
                include_widget = self.wells_table.cellWidget(row, 0)
                include_cb = include_widget.findChild(QCheckBox)
                if include_cb and include_cb.isChecked():
                    well_number = self.wells_table.item(row, 2).text()
                    wells_to_process.append(well_number)

            if not wells_to_process:
                QMessageBox.warning(self, "Warning", "No wells selected for processing")
                progress_dialog.close()
                return

            total_wells = len(wells_to_process)
            total_files = sum(len(self.data[wn]['files']) for wn in wells_to_process)
            processed_wells = 0
            processed_files = 0
            start_time = pd.Timestamp.now()

            progress_dialog.log_message(f"Found {total_wells} wells with {total_files} total files to process")
            progress_dialog.update_progress(0, total_files)

            # Process each selected well
            for well_number in wells_to_process:
                if progress_dialog.was_canceled():
                    break

                well_data = self.data[well_number]
                well_start_time = pd.Timestamp.now()
                progress_dialog.update_status(f"Processing well {well_number} ({processed_wells + 1}/{total_wells})")
                progress_dialog.log_message(f"\n=== Processing Well {well_number} ({processed_wells + 1}/{total_wells}) ===")
                
                try:
                    # Get full time range for this well
                    start_time = well_data['time_range'][0]
                    end_time = well_data['time_range'][1]
                    
                    logger.debug(f"Processing time range for well {well_number}: {start_time} to {end_time}")
                    progress_dialog.log_message(f"Time Range: {start_time} to {end_time}")
                    progress_dialog.log_message(f"Files to Process: {len(well_data['files'])}")
                    
                    # Initialize comparison vector with existing data
                    progress_dialog.log_message("Getting reference data...")
                    comparison_start_time = pd.Timestamp.now()
                    comparison_vector = self.processor.processor._get_existing_data(well_number, (start_time, end_time))
                    logger.debug(f"Got existing data in {(pd.Timestamp.now() - comparison_start_time).total_seconds():.2f} seconds")
                    
                    if not comparison_vector.empty:
                        progress_dialog.log_message(f"Found {len(comparison_vector)} existing readings in range")
                    
                    # Initialize new_data_vector with correct columns
                    new_data_vector = pd.DataFrame(columns=[
                        'timestamp_utc', 'pressure', 'water_pressure', 'water_level',
                        'temperature', 'insertion_level', 'insertion_time',
                        'baro_source', 'baro_flag', 'level_flag', 'level_details'
                    ])
                    
                    # Get manual readings once for the entire period
                    manual_start_time = pd.Timestamp.now()
                    manual_readings = self.processor.processor._get_manual_readings(well_number, (start_time, end_time))
                    logger.debug(f"Got manual readings in {(pd.Timestamp.now() - manual_start_time).total_seconds():.2f} seconds")
                    
                    if not manual_readings.empty:
                        progress_dialog.log_message(f"Found {len(manual_readings)} manual readings in range")
                    
                    # Process files in chronological order
                    for idx, file_path in enumerate(well_data['files'], 1):
                        if progress_dialog.was_canceled():
                            return
                            
                        file_start_time = pd.Timestamp.now()
                        file_name = file_path.name
                        progress_dialog.update_status(f"Processing file {idx} of {len(well_data['files'])}: {file_name}")
                        progress_dialog.update_progress(processed_files, total_files)
                        progress_dialog.log_message(f"\n=== Processing {file_name} ===")
                        
                        # Read raw data
                        read_start_time = pd.Timestamp.now()
                        df, metadata = self.processor.solinst_reader.read_xle(file_path)
                        logger.debug(f"Read XLE file in {(pd.Timestamp.now() - read_start_time).total_seconds():.2f} seconds")
                        progress_dialog.log_message(f"Time Range: {metadata.start_time} to {metadata.stop_time}")
                        progress_dialog.log_message(f"Readings: {len(df)}")
                        
                        # Apply barometric compensation
                        baro_start_time = pd.Timestamp.now()
                        progress_dialog.log_message("\nApplying barometric compensation...")
                        df = self.processor.processor.correct_boundary_readings(df, progress_dialog)
                        
                        time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
                        baro_coverage = self.processor.processor._check_baro_coverage(time_range)
                        if baro_coverage['type'] == 'master' and baro_coverage['complete']:
                            # Use master barometric data
                            baro_df = baro_coverage['data']
                            progress_dialog.log_message("Using master barometric data")
                            # Interpolate barometric pressure to match our timestamps
                            baro_pressure = np.interp(
                                df['timestamp_utc'].astype(np.int64),
                                baro_df['timestamp_utc'].astype(np.int64),
                                baro_df['pressure']
                            )
                            df['water_pressure'] = df['pressure'] - baro_pressure
                            df['baro_source'] = 'master_baro'
                            df['baro_flag'] = 'master'
                        else:
                            progress_dialog.log_message("Using standard atmospheric pressure")
                            df['water_pressure'] = df['pressure'] - self.processor.processor.STANDARD_ATMOS_PRESSURE
                            df['baro_source'] = 'standard_pressure'
                            df['baro_flag'] = 'standard'
                        logger.debug(f"Applied barometric compensation in {(pd.Timestamp.now() - baro_start_time).total_seconds():.2f} seconds")
                        
                        # Process segment
                        level_start_time = pd.Timestamp.now()
                        progress_dialog.log_message(
                            "First segment - determining initial level..." if idx == 1 
                            else "Using previous segment for continuity..."
                        )
                        
                        # Create reference data for level determination
                        ref_data_for_level = pd.DataFrame()
                        
                        if idx == 1:
                            # For first file, use existing data from database
                            if not comparison_vector.empty and 'timestamp_utc' in comparison_vector.columns and 'water_level' in comparison_vector.columns:
                                comparison_vector['timestamp_utc'] = pd.to_datetime(comparison_vector['timestamp_utc'])
                                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                                mask = comparison_vector['timestamp_utc'] < df['timestamp_utc'].min()
                                ref_data_for_level = comparison_vector[mask][['timestamp_utc', 'water_level']].copy()
                                progress_dialog.log_message(f"Using {len(ref_data_for_level)} reference points from existing data")
                        else:
                            # For subsequent files, use only the last few readings from previous file
                            if not new_data_vector.empty and 'timestamp_utc' in new_data_vector.columns and 'water_level' in new_data_vector.columns:
                                ref_data_for_level = new_data_vector.tail(10)[['timestamp_utc', 'water_level']].copy()
                                ref_data_for_level['timestamp_utc'] = pd.to_datetime(ref_data_for_level['timestamp_utc'])
                                progress_dialog.log_message(f"Using {len(ref_data_for_level)} reference points from previous file")
                        
                        # Get insertion level
                        insertion_info = self.processor.processor.determine_insertion_level(
                            df,
                            well_data['well_info'],
                            manual_readings,
                            ref_data_for_level,
                            is_folder_import=True  # This is folder import
                        )
                        logger.debug(f"Determined insertion level in {(pd.Timestamp.now() - level_start_time).total_seconds():.2f} seconds")
                        
                        progress_dialog.log_message(f"Using {insertion_info['method']} method for level determination")
                        progress_dialog.log_message(f"Details: {insertion_info['method_details']}")

                        # Apply insertion level
                        progress_dialog.log_message("\nApplying insertion level")
                        df = self.processor.processor._apply_insertion_level(df, insertion_info)
                        
                        # Append to new_data_vector
                        new_data_vector = pd.concat([new_data_vector, df])
                        
                        file_time = (pd.Timestamp.now() - file_start_time).total_seconds()
                        logger.debug(f"Processed file {file_name} in {file_time:.2f} seconds ({len(df)} readings)")
                        progress_dialog.log_message(f"\nProcessed {len(df)} readings in {file_time:.1f} seconds")
                        progress_dialog.log_message(f"Water Level Range: {df['water_level'].min():.2f} to {df['water_level'].max():.2f} ft")
                        
                        processed_files += 1
                        QApplication.processEvents()  # Keep UI responsive

                    # Store processed data
                    if not new_data_vector.empty:
                        well_data['processed_data'] = new_data_vector.sort_values('timestamp_utc')
                        well_data['has_been_processed'] = True
                        total_readings = len(well_data['processed_data'])
                        well_time = (pd.Timestamp.now() - well_start_time).total_seconds()
                        
                        progress_dialog.log_message(f"\n=== Well Processing Complete ===")
                        progress_dialog.log_message(f"Total Files: {len(well_data['files'])}")
                        progress_dialog.log_message(f"Total Readings: {total_readings}")
                        progress_dialog.log_message(f"Processing Time: {well_time:.1f} seconds")
                        progress_dialog.log_message(f"Time Range: {well_data['processed_data']['timestamp_utc'].min()} to {well_data['processed_data']['timestamp_utc'].max()}")
                        
                        logger.debug(f"Processed well {well_number} in {well_time:.2f} seconds ({total_readings} readings)")

                        # Update plot if this is the currently selected well
                        selected_items = self.wells_table.selectedItems()
                        if selected_items:
                            selected_well = self.wells_table.item(selected_items[0].row(), 2).text()
                            if selected_well == well_number:
                                self.preview_data(well_number)

                except Exception as e:
                    error_msg = f"Error processing well {well_number}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    progress_dialog.log_message(error_msg)
                    continue

                processed_wells += 1
                progress_dialog.update_progress(processed_files, total_files)  # Update progress after each well
                QApplication.processEvents()  # Keep UI responsive

            # After processing all wells
            self._update_checkboxes_after_processing()
            
            # Enable import button if we have any processed data
            self.import_btn.setEnabled(any(info.get('has_been_processed', False) 
                                         for info in self.data.values()))
            
            total_time = (pd.Timestamp.now() - start_time).total_seconds()
            logger.info(f"Processing complete in {total_time:.2f} seconds. Processed {processed_wells} wells, {processed_files} files")
            
            # Ensure we show 100% progress at the end
            progress_dialog.update_progress(total_files, total_files)
            progress_dialog.update_status("Processing complete")
            progress_dialog.log_message(f"\nAll processing complete in {total_time:.1f} seconds")
            progress_dialog.log_message(f"Processed {processed_wells} wells, {processed_files} files")
            QApplication.processEvents()
            
            # Keep dialog open and change to Close button
            progress_dialog.finish_operation()
                
        except Exception as e:
            error_msg = f"Error processing files: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if progress_dialog:
                progress_dialog.log_message(error_msg)
                progress_dialog.close()
            QMessageBox.critical(self, "Error", error_msg)

    def _get_row_for_well(self, well_number: str) -> Optional[int]:
        """Helper to find the row index for a well number"""
        for row in range(self.wells_table.rowCount()):
            if self.wells_table.item(row, 3).text() == well_number:  # Well Number is in column 3
                return row
        return None

    def _update_checkboxes_after_processing(self):
        """Update checkbox states after processing"""
        for row in range(self.wells_table.rowCount()):
            well_number = self.wells_table.item(row, 2).text()
            well_data = self.data.get(well_number, {})
            
            # Include checkbox
            include_widget = self.wells_table.cellWidget(row, 0)
            include_cb = include_widget.findChild(QCheckBox)
            if include_cb:
                if well_data.get('has_been_processed', False):
                    include_cb.setChecked(True)
                    include_cb.setEnabled(True)
                else:
                    include_cb.setChecked(False)
                    include_cb.setEnabled(False)
            
            # Overwrite checkbox
            overlap_widget = self.wells_table.cellWidget(row, 1)
            overlap_cb = overlap_widget.findChild(QCheckBox)
            if overlap_cb:
                has_overlap = well_data.get('has_overlap', False)
                is_processed = well_data.get('has_been_processed', False)
                overlap_cb.setEnabled(has_overlap and is_processed)
                overlap_cb.setChecked(False)

    def show_full_view(self):
        """Open the current plot in a detailed view dialog"""
        if not self.data:
            return
            
        # Get currently selected well
        selected_items = self.wells_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        well_number = self.wells_table.item(row, 2).text()
        
        if well_number in self.data:
            # Show loading cursor
            self.setCursor(Qt.WaitCursor)
            QApplication.processEvents()
            
            try:
                dialog = DetailedPlotDialog(self.data[well_number], well_number, self)
                dialog.exec_()
            except Exception as e:
                logger.error(f"Error showing detailed plot: {e}")
                QMessageBox.critical(self, "Error", f"Failed to show detailed plot: {str(e)}")
            finally:
                # Always restore cursor
                self.setCursor(Qt.ArrowCursor)
                QApplication.processEvents()

    def _plot_data_by_method(self, df: pd.DataFrame, ax):
        """Plot data with different colors for each level determination method"""
        if df.empty:
            return
        
        if 'level_flag' in df.columns:
            for method in df['level_flag'].unique():
                mask = df['level_flag'] == method
                ax.plot(df[mask]['timestamp_utc'], df[mask]['water_level'],
                       label=f'Method: {method}', alpha=0.7)
        else:
            ax.plot(df['timestamp_utc'], df['water_level'],
                   label='Water Level', alpha=0.7)

    def import_data(self):
        """Import data for selected wells"""
        try:
            # ...existing code...
            
            # First import all data to the database
            for well_number, well_data in self.processed_wells.items():
                if not well_data.get('has_been_processed'):
                    continue
                
                # Import the data
                self.log_message(f"Importing data for well {well_number}...")
                success = self.water_level_model.import_readings(
                    well_number,
                    well_data['processed_data'],
                    self.overwrite_existing
                )
                
                if success:
                    self.log_message(f"Successfully imported {len(well_data['processed_data'])} readings for well {well_number}")
                else:
                    self.log_message(f"Failed to import data for well {well_number}")
                    
            self.log_message("\nData import complete.")
            
            # Now organize all files for each well after database import is complete
            try:
                self.log_message("\n=== Organizing Files ===")
                
                # Initialize file organizer
                from ..utils.file_organizer import XLEFileOrganizer
                app_root_dir = Path(__file__).parent.parent.parent.parent
                organizer = XLEFileOrganizer(app_root_dir, db_name=Path(self.water_level_model.db_path).stem)
                self.log_message(f"File organizer initialized with root dir: {app_root_dir}")
                
                for well_number, well_data in self.processed_wells.items():
                    if not well_data.get('has_been_processed'):
                        continue
                        
                    self.log_message(f"\nOrganizing files for well {well_number}...")
                    
                    # Organize each file for this well
                    for file_path in well_data['files']:
                        # Get metadata from file
                        _, metadata = self.processor.solinst_reader.read_xle(file_path)
                        
                        # Get timestamp range for this file
                        file_start_date = pd.to_datetime(metadata.start_time)
                        file_end_date = pd.to_datetime(metadata.stop_time)
                        
                        self.log_message(f"Organizing file: {file_path.name}")
                        self.log_message(f"  Serial: {metadata.serial_number}")
                        self.log_message(f"  Location: {metadata.location}")
                        
                        # Check if this is a barologger (which should be rare)
                        is_baro = hasattr(metadata, 'is_barologger') and metadata.is_barologger
                        
                        # Organize the file
                        if is_baro:
                            # For barologgers (rare in water level import)
                            result_path = organizer.organize_barologger_file(
                                file_path,
                                metadata.serial_number,
                                metadata.location,
                                file_start_date,
                                file_end_date
                            )
                            self.log_message(f"  Organized as barologger file")
                        else:
                            # For transducers (typical case)
                            result_path = organizer.organize_transducer_file(
                                file_path,
                                metadata.serial_number,
                                metadata.location,
                                file_start_date,
                                file_end_date,
                                well_number  # Pass well number for folder organization
                            )
                            self.log_message(f"  Organized as transducer file")
                        
                        if result_path:
                            self.log_message(f"  File successfully organized to: {result_path}")
                        else:
                            self.log_message(f"  Warning: File organization returned None")
                            
                self.log_message("\nFile organization complete.")
                
            except Exception as e:
                self.log_message(f"Error during file organization: {str(e)}")
                logger.error(f"Error organizing files: {e}", exc_info=True)
            
            self.accept()
        except Exception as e:
            logger.error(f"Error importing data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to import data: {str(e)}")