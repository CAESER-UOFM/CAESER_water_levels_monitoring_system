from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QTableWidget, 
                           QTableWidgetItem, QFileDialog, QMessageBox,
                           QLineEdit, QLabel, QCheckBox, QProgressDialog,
                           QTabWidget, QSizePolicy, QDialog, QRadioButton,
                           QButtonGroup, QHeaderView)
from PyQt5.QtCore import Qt, QPoint
import sys
from pathlib import Path
import logging
from typing import List, Dict, Tuple, Optional
import datetime
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.legend import Legend
import numpy as np
import re
import shutil

# Import SolinstReader from parent directory
sys.path.append(str(Path(__file__).parent.parent))
from src.gui.handlers.solinst_reader import SolinstReader

logger = logging.getLogger(__name__)

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.fig.tight_layout()
        self.fig.subplots_adjust(bottom=0.15)  # Make room for date labels
        
    def plot_data(self, data_dict):
        """Plot data from multiple files
        
        Args:
            data_dict: Dictionary with file names as keys and pandas dataframes as values
        """
        self.axes.clear()
        if not data_dict:
            self.axes.set_title("No data to display")
            self.draw()
            return
        
        # Get count of files
        file_count = len(data_dict)
        logger.info(f"Attempting to plot {file_count} files")
        
        # Prepare distinct visual elements for each plot
        line_styles = ['-', '--', '-.', ':']
        markers = ['o', 's', '^', 'D', 'v', '*', 'p', 'h', '+', 'x']
        colors = [
            'blue', 'red', 'green', 'purple', 'orange', 'brown', 
            'pink', 'gray', 'olive', 'cyan', 'magenta', 'lime',
            'navy', 'teal', 'coral', 'gold', 'darkred', 'darkgreen'
        ]
        
        # Create a list of files with their dates for sorting
        file_date_list = []
        for file_name, df in data_dict.items():
            if df.empty:
                continue
                
            # Extract the date information
            x_col = 'timestamp_utc' if 'timestamp_utc' in df.columns else 'timestamp'
            if x_col in df.columns and not df[x_col].empty:
                try:
                    # Use the earliest date in the file for sorting
                    earliest_date = df[x_col].min()
                    file_date_list.append((file_name, earliest_date, df))
                except:
                    # If we can't get a date, just use the filename
                    file_date_list.append((file_name, None, df))
            else:
                file_date_list.append((file_name, None, df))
        
        # Sort files by date (earliest first), handling None values
        file_date_list.sort(key=lambda x: (x[1] is None, x[1]))
        
        # Limit the number of files to plot if there are too many
        max_files_to_plot = 50  # Setting a reasonable limit
        show_warning = False
        
        if len(file_date_list) > max_files_to_plot:
            show_warning = True
            # Only keep the first max_files_to_plot sorted files
            file_date_list = file_date_list[:max_files_to_plot]
        
        # Keep track of plotted files
        plotted_files = []
        handles = []
        labels = []
        
        # Plot each file in date order
        for i, (file_name, date, df) in enumerate(file_date_list):
            if df.empty:
                logger.debug(f"Skipping empty DataFrame for {file_name}")
                continue
                
            # Use timestamp_utc if available, otherwise use timestamp
            x_col = 'timestamp_utc' if 'timestamp_utc' in df.columns else 'timestamp'
            
            if x_col in df.columns and 'pressure' in df.columns:
                # Get clean data only
                valid_data = df.dropna(subset=[x_col, 'pressure'])
                
                if len(valid_data) > 0:
                    try:
                        # Cycle through visual elements
                        color = colors[i % len(colors)]
                        line_style = line_styles[i % len(line_styles)]
                        marker = markers[i % len(markers)]
                        
                        # Use a shorter display name with date prefix if we have a date
                        display_name = file_name
                        if date is not None:
                            try:
                                date_str = date.strftime('%Y-%m-%d')
                                # Add date prefix to the display name
                                if len(file_name) > 20:
                                    # Truncate long filenames
                                    short_name = file_name[:10] + '...' + file_name[-7:]
                                    display_name = f"{date_str}: {short_name}"
                                else:
                                    display_name = f"{date_str}: {file_name}"
                            except:
                                # If date formatting fails, just use the filename
                                if len(file_name) > 25:
                                    display_name = file_name[:12] + '...' + file_name[-10:]
                        elif len(file_name) > 25:
                            # Truncate to 25 chars with ellipsis in the middle if no date
                            display_name = file_name[:12] + '...' + file_name[-10:]
                        
                        # Plot the data - protect against different return values
                        result = self.axes.plot(
                            valid_data[x_col], 
                            valid_data['pressure'], 
                            linestyle=line_style,
                            marker=marker,
                            markersize=4,
                            markevery=720,  # Show marker only every 2,880 data points
                            linewidth=1.5,
                            color=color,
                            alpha=0.8,
                            label=display_name
                        )
                        
                        # Get the line object regardless of what plot returns
                        if result and len(result) > 0:
                            line = result[0]  # Get the first element
                            
                            # Track plotted files and their handles
                            plotted_files.append(display_name)
                            handles.append(line)
                            labels.append(display_name)
                            
                            logger.debug(f"Plotted file {i+1}/{file_count}: {file_name} with {len(valid_data)} points")
                    except Exception as e:
                        logger.error(f"Error plotting file {file_name}: {e}")
        
        # Format the plot
        if handles:  # Only if we have plotted at least one file
            self.axes.set_xlabel('Date', fontsize=10)
            self.axes.set_ylabel('Level/Pressure', fontsize=10)
            self.axes.grid(True, linestyle='--', alpha=0.6)
            
            # Format date axis
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            for label in self.axes.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
            
            # Add title showing the number of files
            title = f"Data from {len(plotted_files)} files"
            if show_warning:
                title += f" (showing first {max_files_to_plot} of {file_count})"
            self.axes.set_title(title, fontsize=12)
            
            # Determine optimal legend layout based on number of entries
            if len(handles) <= 3:
                # Few files: standard legend at "best" location
                ncols = 1
                fontsize = 9
                loc = 'best'
            elif len(handles) <= 6:
                # Medium number: 2 columns
                ncols = 2
                fontsize = 8
                loc = 'upper right'
            elif len(handles) <= 12:
                # More files: 3 columns with smaller font
                ncols = 3
                fontsize = 7
                loc = 'upper right'
            else:
                # Many files: 4 columns with smallest font
                ncols = 4
                fontsize = 6
                loc = 'upper right'
            
            try:
                # Create the legend with optimized parameters
                legend = self.axes.legend(
                    handles, 
                    labels, 
                    loc=loc,
                    ncol=ncols,
                    fontsize=fontsize,
                    framealpha=0.8,
                    title="File Names",
                    title_fontsize=fontsize+1
                )
                
                # Make legend draggable
                legend.set_draggable(True)
            except Exception as e:
                logger.error(f"Error creating legend: {e}")
            
            # Adjust layout to make room for legend
            self.fig.tight_layout()
        else:
            self.axes.set_title("No valid data to display")
            
        self.draw()

class CheckBoxHeader(QHeaderView):
    """Custom header view with a checkbox for selecting all items"""
    
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.parent = parent
        self.is_checked = True
        
        # Create the checkbox
        self.checkbox = QCheckBox(parent)
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.on_state_changed)
        
    def paintSection(self, painter, rect, logical_index):
        # Call the base implementation to draw the section
        super().paintSection(painter, rect, logical_index)
        
        # Draw the checkbox only in the first column
        if logical_index == 0:
            # Calculate the position to place the checkbox
            checkbox_size = self.checkbox.sizeHint()
            x = rect.x() + (rect.width() - checkbox_size.width()) // 2
            y = rect.y() + (rect.height() - checkbox_size.height()) // 2
            
            # Move the checkbox to this position and ensure it's visible
            self.checkbox.setGeometry(x, y, checkbox_size.width(), checkbox_size.height())
            self.checkbox.setVisible(True)
    
    def on_state_changed(self, state):
        """Handle checkbox state changes"""
        self.is_checked = state == Qt.Checked
        self.parent.toggle_all_checkboxes(state)

class FindXLEBySerial(QMainWindow):
    def __init__(self):
        super().__init__()
        self.solinst_reader = SolinstReader()
        self.found_files: List[Dict] = []  # Store found files data
        self.plot_data_dict = {}  # Store data for plotting
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Find XLE by Serial Number")
        self.setMinimumSize(900, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Folder:")
        self.folder_path = QLineEdit()
        self.folder_path.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(self.browse_btn)
        
        # Include subfolders checkbox
        self.include_subfolders = QCheckBox("Include Subfolders")
        self.include_subfolders.setChecked(True)
        folder_layout.addWidget(self.include_subfolders)
        
        # Add folder layout to main layout
        layout.addLayout(folder_layout)
        
        # File type selection
        file_type_layout = QHBoxLayout()
        self.file_type_label = QLabel("File Type:")
        
        # Radio buttons for file type
        self.file_type_group = QButtonGroup(self)
        self.xle_radio = QRadioButton("XLE")
        self.csv_radio = QRadioButton("CSV")
        self.both_radio = QRadioButton("Both")
        
        # Set XLE as default
        self.xle_radio.setChecked(True)
        
        # Add radio buttons to group
        self.file_type_group.addButton(self.xle_radio)
        self.file_type_group.addButton(self.csv_radio)
        self.file_type_group.addButton(self.both_radio)
        
        file_type_layout.addWidget(self.file_type_label)
        file_type_layout.addWidget(self.xle_radio)
        file_type_layout.addWidget(self.csv_radio)
        file_type_layout.addWidget(self.both_radio)
        file_type_layout.addStretch()
        
        # Add file type layout to main layout
        layout.addLayout(file_type_layout)
        
        # Serial number input
        serial_layout = QHBoxLayout()
        self.serial_label = QLabel("Serial Number:")
        self.serial_input = QLineEdit()
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_files)
        
        # Add import button
        self.import_btn = QPushButton("Import Files")
        self.import_btn.clicked.connect(self.import_files)
        self.import_btn.setEnabled(False)  # Disabled until search finds files
        
        serial_layout.addWidget(self.serial_label)
        serial_layout.addWidget(self.serial_input)
        serial_layout.addWidget(self.search_btn)
        serial_layout.addWidget(self.import_btn)
        
        # Add serial layout to main layout
        layout.addLayout(serial_layout)
        
        # Add file type filter checkboxes
        self.filter_layout = QHBoxLayout()
        self.filter_unique_check = QCheckBox("Filter Duplicates")
        self.filter_unique_check.setToolTip("Show only one file per unique time range")
        self.filter_unique_check.setEnabled(False)  # Disabled until search finds files
        self.filter_unique_check.stateChanged.connect(self.filter_unique_files)
        
        self.filter_xle_check = QCheckBox("Show XLE")
        self.filter_csv_check = QCheckBox("Show CSV")
        self.filter_xle_check.setChecked(True)
        self.filter_csv_check.setChecked(True)
        self.filter_xle_check.setEnabled(False)  # Disabled until search finds files
        self.filter_csv_check.setEnabled(False)  # Disabled until search finds files
        self.filter_xle_check.stateChanged.connect(self.apply_filters)
        self.filter_csv_check.stateChanged.connect(self.apply_filters)
        
        self.filter_layout.addWidget(self.filter_unique_check)
        self.filter_layout.addWidget(self.filter_xle_check)
        self.filter_layout.addWidget(self.filter_csv_check)
        self.filter_layout.addStretch()
        
        # Add the filter layout to main layout
        layout.addLayout(self.filter_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create table tab
        self.table_tab = QWidget()
        table_layout = QVBoxLayout(self.table_tab)
        
        # Create results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)  # Added column for checkboxes
        self.results_table.setHorizontalHeaderLabels([
            "Select",  # New checkbox column
            "File Name", 
            "Location", 
            "Serial Number", 
            "Start Date",
            "End Date", 
            "Model",
            "Reading Count",
            "Relative Path",
            "File Type"
        ])
        
        # Set custom header with checkbox
        header = CheckBoxHeader(Qt.Horizontal, self)
        self.results_table.setHorizontalHeader(header)
        
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSortingEnabled(True)
        
        # Set reasonable width for the checkbox column
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        table_layout.addWidget(self.results_table)
        
        # Create plot tab
        self.plot_tab = QWidget()
        plot_layout = QVBoxLayout(self.plot_tab)
        
        # Add plot canvas and navigation toolbar - reordered to put toolbar on top
        self.plot_canvas = PlotCanvas(self.plot_tab)
        self.plot_toolbar = NavigationToolbar(self.plot_canvas, self.plot_tab)
        
        plot_layout.addWidget(self.plot_toolbar)  # Toolbar first (on top)
        plot_layout.addWidget(self.plot_canvas)   # Canvas second (below toolbar)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.table_tab, "Table")
        self.tab_widget.addTab(self.plot_tab, "Plot")
        
        layout.addWidget(self.tab_widget)
        
    def select_folder(self):
        """Handle folder selection"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with XLE Files",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.folder_path.setText(folder)
            
    def search_files(self):
        """Search for XLE/CSV files with the specified serial number"""
        # Get inputs
        folder = self.folder_path.text()
        if not folder:
            QMessageBox.warning(self, "Missing Input", "Please select a folder first.")
            return
            
        serial_number = self.serial_input.text().strip()
        if not serial_number:
            QMessageBox.warning(self, "Missing Input", "Please enter a serial number to search for.")
            return
            
        # Clear previous results
        self.results_table.setRowCount(0)
        self.found_files.clear()
        self.plot_data_dict.clear()
        
        # Store all found files separately (including duplicates)
        self.all_found_files = []
        
        # Determine file types to search for based on radio button selection
        file_types = []
        if self.xle_radio.isChecked() or self.both_radio.isChecked():
            file_types.append("*.xle")
        if self.csv_radio.isChecked() or self.both_radio.isChecked():
            file_types.append("*.csv")
        
        # Get all matching files in folder (and subfolders if checked)
        folder_path = Path(folder)
        all_files = []
        
        for file_type in file_types:
            if self.include_subfolders.isChecked():
                all_files.extend(list(folder_path.rglob(file_type)))
            else:
                all_files.extend(list(folder_path.glob(file_type)))
            
        if not all_files:
            file_types_str = " and ".join([ft.replace("*", "") for ft in file_types])
            QMessageBox.information(
                self, 
                "No Files Found", 
                f"No {file_types_str} files found in the selected folder."
            )
            return
            
        # Create progress dialog
        progress = QProgressDialog("Searching files...", "Cancel", 0, len(all_files), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Searching Files")
        progress.setMinimumDuration(0)  # Show immediately
        
        found_count = 0
        
        for i, file_path in enumerate(all_files):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            progress.setLabelText(f"Searching: {file_path.name}")
            QApplication.processEvents()
            
            try:
                # Process file based on extension
                if file_path.suffix.lower() == '.xle':
                    # Read XLE file using existing method
                    data, metadata = self.solinst_reader.read_xle(file_path)
                    
                    # More flexible serial number matching
                    file_serial = metadata.serial_number.strip() if metadata.serial_number else ""
                    
                    # Check if this file matches the search criteria
                    if self.is_serial_match(file_serial, serial_number):
                        found_count += 1
                        
                        # Get dates directly from metadata - they're already parsed in SolinstReader
                        start_date = "Not available"
                        end_date = "Not available"
                        
                        # Format start_time if available
                        if hasattr(metadata, 'start_time') and metadata.start_time:
                            try:
                                start_date = metadata.start_time.strftime('%Y-%m-%d')
                            except Exception as e:
                                logger.debug(f"Error formatting start_time: {e}")
                        
                        # Format stop_time if available
                        if hasattr(metadata, 'stop_time') and metadata.stop_time:
                            try:
                                end_date = metadata.stop_time.strftime('%Y-%m-%d')
                            except Exception as e:
                                logger.debug(f"Error formatting stop_time: {e}")
                        
                        # Calculate relative path
                        try:
                            relative_path = str(file_path.relative_to(folder_path))
                        except ValueError:
                            # Handle case where file might not be relative to the folder
                            relative_path = str(file_path)
                        
                        # Create a key for this time range for deduplication
                        time_range_key = f"{start_date}_to_{end_date}"
                        
                        # Store data for plotting
                        if not data.empty:
                            self.plot_data_dict[file_path.name] = data
                        
                        # Create file data record
                        file_data = {
                            'file_path': str(file_path),
                            'file_name': file_path.name,
                            'location': metadata.location or "",
                            'serial_number': file_serial,
                            'start_date': start_date,
                            'end_date': end_date,
                            'time_range_key': time_range_key,  # Store the time range key for filtering
                            'reading_count': metadata.num_log if hasattr(metadata, 'num_log') else len(data),
                            'relative_path': relative_path,
                            'model': metadata.instrument_type or "",  # Add model field back
                            'is_compensated': "compensated" in file_path.name.lower(),  # Flag compensated files
                            'file_type': 'XLE'  # Add file type field
                        }
                        
                        # Add to all found files list
                        self.all_found_files.append(file_data)
                
                elif file_path.suffix.lower() == '.csv':
                    # Read CSV file using our new method
                    data, metadata_dict = self.read_csv_file(file_path)
                    
                    # Get serial from metadata
                    file_serial = metadata_dict.get('serial_number', '').strip()
                    
                    # Check if this file matches the search criteria with more flexible matching
                    if self.is_serial_match(file_serial, serial_number):
                        found_count += 1
                        
                        # Get dates from metadata
                        start_date = "Not available"
                        end_date = "Not available"
                        
                        # Format start_time if available
                        if metadata_dict.get('start_time'):
                            try:
                                start_date = metadata_dict['start_time'].strftime('%Y-%m-%d')
                            except Exception as e:
                                logger.debug(f"Error formatting start_time: {e}")
                        
                        # Format stop_time if available
                        if metadata_dict.get('stop_time'):
                            try:
                                end_date = metadata_dict['stop_time'].strftime('%Y-%m-%d')
                            except Exception as e:
                                logger.debug(f"Error formatting stop_time: {e}")
                        
                        # Calculate relative path
                        try:
                            relative_path = str(file_path.relative_to(folder_path))
                        except ValueError:
                            # Handle case where file might not be relative to the folder
                            relative_path = str(file_path)
                        
                        # Create a key for this time range for deduplication
                        time_range_key = f"{start_date}_to_{end_date}"
                        
                        # Store data for plotting
                        if data is not None and not data.empty:
                            self.plot_data_dict[file_path.name] = data
                        
                        # Create file data record
                        file_data = {
                            'file_path': str(file_path),
                            'file_name': file_path.name,
                            'location': metadata_dict.get('location', ""),
                            'serial_number': file_serial,
                            'start_date': start_date,
                            'end_date': end_date,
                            'time_range_key': time_range_key,  # Store the time range key for filtering
                            'reading_count': metadata_dict.get('num_log', 0),
                            'relative_path': relative_path,
                            'model': metadata_dict.get('instrument_type', ""),
                            'is_compensated': "compensated" in file_path.name.lower(),  # Flag compensated files
                            'file_type': 'CSV'  # Add file type field
                        }
                        
                        # Add to all found files list
                        self.all_found_files.append(file_data)
                    
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                # Log more detailed error information for debugging
                import traceback
                logger.debug(f"Detailed error: {traceback.format_exc()}")
                # Continue with next file
        
        progress.setValue(len(all_files))
        
        # Display all files initially
        self.display_file_list(self.all_found_files)
        
        # Plot the data
        self.plot_canvas.plot_data(self.plot_data_dict)
        
        # Show message with results
        file_types_str = " and ".join([ft.replace("*", "") for ft in file_types])
        if found_count == 0:
            QMessageBox.information(
                self, 
                "Search Complete", 
                f"No {file_types_str} files found with serial number '{serial_number}'."
            )
            # Switch to table tab if no data to plot
            self.tab_widget.setCurrentIndex(0)
            # Disable buttons
            self.import_btn.setEnabled(False)
            self.filter_unique_check.setEnabled(False)
            self.filter_xle_check.setEnabled(False)
            self.filter_csv_check.setEnabled(False)
        else:
            QMessageBox.information(
                self, 
                "Search Complete", 
                f"Found {found_count} {file_types_str} file(s) with serial number '{serial_number}'."
            )
            # Enable buttons
            self.import_btn.setEnabled(True)
            self.filter_unique_check.setEnabled(True)
            self.filter_xle_check.setEnabled(True)
            self.filter_csv_check.setEnabled(True)
            # Uncheck filter checkbox
            self.filter_unique_check.setChecked(False)
    
    def display_file_list(self, files_to_display):
        """Display a list of files in the table and update found_files list"""
        # Clear the table
        self.results_table.setRowCount(0)
        self.found_files = files_to_display.copy()
        
        # Add to table
        for file_data in self.found_files:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # Add checkbox to first column
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Checked by default
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(5, 0, 5, 0)
            self.results_table.setCellWidget(row, 0, checkbox_widget)
            
            # File name
            self.results_table.setItem(row, 1, QTableWidgetItem(file_data['file_name']))
            
            # Location
            self.results_table.setItem(row, 2, QTableWidgetItem(file_data['location']))
            
            # Serial Number
            self.results_table.setItem(row, 3, QTableWidgetItem(file_data['serial_number']))
            
            # Start Date
            self.results_table.setItem(row, 4, QTableWidgetItem(file_data['start_date']))
            
            # End Date
            self.results_table.setItem(row, 5, QTableWidgetItem(file_data['end_date']))
            
            # Model - if available in the data
            model = file_data.get('model', '')
            self.results_table.setItem(row, 6, QTableWidgetItem(model))
            
            # Reading Count
            self.results_table.setItem(row, 7, QTableWidgetItem(str(file_data['reading_count'])))
            
            # Relative Path
            self.results_table.setItem(row, 8, QTableWidgetItem(file_data['relative_path']))
            
            # File Type - new column
            file_type = file_data.get('file_type', '')
            self.results_table.setItem(row, 9, QTableWidgetItem(file_type))
        
        # Resize columns to content
        self.results_table.resizeColumnsToContents()
        
    def toggle_all_checkboxes(self, state):
        """Toggle all checkboxes in the table"""
        checked = state == Qt.Checked
        
        # Update all checkboxes in the table
        for row in range(self.results_table.rowCount()):
            checkbox_widget = self.results_table.cellWidget(row, 0)
            if checkbox_widget:
                # Get the checkbox from the widget
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(checked)
    
    def import_files(self):
        """Import files to a selected folder with deduplication and renaming"""
        # First check if we have any files
        if not self.found_files:
            QMessageBox.warning(self, "No Files", "No files found to import.")
            return
            
        # Get selected files
        selected_files = []
        for row in range(self.results_table.rowCount()):
            checkbox_widget = self.results_table.cellWidget(row, 0)
            if checkbox_widget:
                # Get the checkbox from the widget
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked() and row < len(self.found_files):
                    selected_files.append(self.found_files[row])
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to import.")
            return
            
        # Get destination folder
        destination_root = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if not destination_root:
            return  # User cancelled
        
        try:
            # Get the serial number from our search
            serial_number = self.serial_input.text().strip()
            if not serial_number:
                # Try to get it from the first file if not in search box
                if selected_files and 'serial_number' in selected_files[0]:
                    serial_number = selected_files[0]['serial_number']
                    
            if not serial_number:
                QMessageBox.warning(self, "Missing Serial Number", "Could not determine serial number for folder naming.")
                return
                
            # Create a subfolder with the serial number
            destination_folder = Path(destination_root) / serial_number
            if not destination_folder.exists():
                destination_folder.mkdir(parents=True)
                
            # Create a progress dialog
            progress = QProgressDialog("Importing files...", "Cancel", 0, len(selected_files), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Importing Files")
            progress.setMinimumDuration(0)
            
            # Deduplicate files by time range
            time_ranges = {}  # Dictionary to track unique time ranges
            imported_count = 0
            skipped_compensated = 0
            skipped_duplicates = 0
            
            for i, file_data in enumerate(selected_files):
                if progress.wasCanceled():
                    break
                    
                progress.setValue(i)
                file_path = file_data['file_path']
                file_name = file_data['file_name'].lower()
                file_type = file_data.get('file_type', '')
                
                # Skip files with "compensated" in the name
                if "compensated" in file_name:
                    progress.setLabelText(f"Skipping compensated file: {file_name}")
                    skipped_compensated += 1
                    continue
                
                # Get start/end dates and location from metadata
                start_date = file_data.get('start_date', '')
                end_date = file_data.get('end_date', '')
                location = file_data.get('location', '')
                
                # Skip if we can't determine dates
                if start_date == "Not available" or end_date == "Not available":
                    progress.setLabelText(f"Skipping file without date range: {file_name}")
                    continue
                
                # Create a key for this time range
                time_range_key = f"{start_date}_to_{end_date}"
                
                # Check if we already have a file with this time range
                if time_range_key in time_ranges:
                    # If we already have a file for this time range, prefer XLE over CSV
                    existing_file_data = time_ranges[time_range_key]
                    existing_file_type = existing_file_data.get('file_type', '')
                    
                    # If current file is CSV and existing is XLE, skip this CSV file
                    if file_type == 'CSV' and existing_file_type == 'XLE':
                        progress.setLabelText(f"Skipping CSV file (XLE exists): {file_name}")
                        skipped_duplicates += 1
                        continue
                    
                    # If current file is XLE and existing is CSV, replace with this XLE file
                    elif file_type == 'XLE' and existing_file_type == 'CSV':
                        # Update the time_ranges dictionary to prefer XLE file
                        time_ranges[time_range_key] = file_data
                    else:
                        # Both are same type, skip duplicate
                        progress.setLabelText(f"Skipping duplicate time range: {file_name}")
                        skipped_duplicates += 1
                        continue
                else:
                    # Mark this time range as seen
                    time_ranges[time_range_key] = file_data
                
                # Format dates for filename
                try:
                    # Parse dates from string format if needed
                    if isinstance(start_date, str):
                        start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                    else:
                        start_date_obj = start_date
                        
                    if isinstance(end_date, str):
                        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                    else:
                        end_date_obj = end_date
                    
                    # Format the dates for the filename
                    start_year = start_date_obj.year
                    start_month = start_date_obj.month
                    start_day = start_date_obj.day
                    
                    end_year = end_date_obj.year
                    end_month = end_date_obj.month
                    end_day = end_date_obj.day
                    
                    # Format the date part of the filename
                    if start_year == end_year:
                        # Same year, use format YYYY_MM_DD_To_MM_DD
                        date_part = f"{start_year}_{start_month:02d}_{start_day:02d}_To_{end_month:02d}_{end_day:02d}"
                    else:
                        # Different years, use format YYYY_MM_DD_To_YYYY_MM_DD
                        date_part = f"{start_year}_{start_month:02d}_{start_day:02d}_To_{end_year}_{end_month:02d}_{end_day:02d}"
                except Exception as e:
                    logger.warning(f"Error formatting dates for filename: {e}")
                    # Fallback to using the original date strings
                    date_part = f"{start_date}_To_{end_date}"
                
                # Clean the location name for use in filename (remove invalid characters)
                clean_location = ""
                if location:
                    # Replace spaces with underscores and remove invalid filename characters
                    clean_location = re.sub(r'[\\/*?:"<>|]', '', location.replace(' ', '_'))
                
                # Create new filename with pattern: serialNumber_location_date1_To_date2.extension
                extension = Path(file_path).suffix.lower()
                if clean_location:
                    new_filename = f"{serial_number}_{clean_location}_{date_part}{extension}"
                else:
                    new_filename = f"{serial_number}_{date_part}{extension}"
                
                # Copy the file with the new name
                source_path = Path(file_path)
                destination_path = destination_folder / new_filename
                
                try:
                    progress.setLabelText(f"Copying: {source_path.name} → {new_filename}")
                    shutil.copy2(source_path, destination_path)
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Error copying file {source_path}: {e}")
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to copy {source_path.name}: {str(e)}"
                    )
            
            progress.setValue(len(selected_files))
            
            # Show summary
            QMessageBox.information(
                self,
                "Import Complete",
                f"Import results:\n"
                f"- {imported_count} files successfully imported\n"
                f"- {skipped_compensated} compensated files skipped\n"
                f"- {skipped_duplicates} duplicate time range files skipped\n\n"
                f"Files saved to: {destination_folder}"
            )
            
        except Exception as e:
            logger.error(f"Error importing files: {e}")
            import traceback
            logger.debug(f"Detailed error: {traceback.format_exc()}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to import files: {str(e)}"
            )

    def filter_unique_files(self, state):
        """Filter the file list to show only unique files based on time range"""
        self.apply_filters()
    
    def apply_filters(self):
        """Apply all active filters (unique and file type)"""
        if not hasattr(self, 'all_found_files') or not self.all_found_files:
            return
            
        # Start with all files
        filtered_files = self.all_found_files.copy()
        
        # Apply file type filters
        if not self.filter_xle_check.isChecked() or not self.filter_csv_check.isChecked():
            # Filter by file type
            if self.filter_xle_check.isChecked() and not self.filter_csv_check.isChecked():
                # Show only XLE files
                filtered_files = [f for f in filtered_files if f.get('file_type', '') == 'XLE']
            elif self.filter_csv_check.isChecked() and not self.filter_xle_check.isChecked():
                # Show only CSV files
                filtered_files = [f for f in filtered_files if f.get('file_type', '') == 'CSV']
            # If both checked or both unchecked, no filtering needed
        
        # Apply unique filter if checked
        if self.filter_unique_check.isChecked():
            # Show only unique files (one per time range)
            unique_files = {}
            # Sort by reading count (higher first) to get the best file for each time range
            # Then sort by file type (XLE preferred over CSV)
            sorted_files = sorted(
                filtered_files, 
                key=lambda x: (
                    -x.get('reading_count', 0),  # Negative to sort in descending order
                    0 if x.get('file_type', '') == 'XLE' else 1  # XLE files first
                )
            )
            
            for file_data in sorted_files:
                # Skip compensated files
                if "compensated" in file_data['file_name'].lower():
                    continue
                
                # Create a unique key based on time range
                time_range_key = f"{file_data['start_date']}_{file_data['end_date']}"
                
                # If we haven't seen this time range before, add it
                if time_range_key not in unique_files:
                    unique_files[time_range_key] = file_data
            
            # Update the displayed files
            filtered_files = list(unique_files.values())
        
        # Update display with filtered files
        self.found_files = filtered_files
        
        # Create status message
        xle_count = sum(1 for f in filtered_files if f.get('file_type', '') == 'XLE')
        csv_count = sum(1 for f in filtered_files if f.get('file_type', '') == 'CSV')
        total_count = len(self.all_found_files)
        
        if self.filter_unique_check.isChecked():
            self.status_message = f"Showing {len(filtered_files)} unique files ({xle_count} XLE, {csv_count} CSV) out of {total_count} total"
        else:
            self.status_message = f"Showing {len(filtered_files)} files ({xle_count} XLE, {csv_count} CSV) out of {total_count} total"
        
        # Update the table with filtered list
        self.display_file_list(self.found_files)
        
        # Update the plot to show only the filtered files
        self.update_plot_with_filtered_data()

    def update_plot_with_filtered_data(self):
        """Update the plot to show only the filtered files"""
        if not self.found_files:
            return
            
        # Create a new plot data dictionary with only the filtered files
        filtered_plot_data = {}
        for file_data in self.found_files:
            file_path = file_data['file_path']
            file_name = file_data['file_name']
            
            # If we have this file in our original plot data, add it to filtered data
            if file_name in self.plot_data_dict:
                filtered_plot_data[file_name] = self.plot_data_dict[file_name]
        
        # Update the plot with the filtered data
        self.plot_canvas.plot_data(filtered_plot_data)
        
        # Update status label for filter status if we have one
        if hasattr(self, 'status_message') and hasattr(self, 'status_label'):
            self.status_label.setText(self.status_message)

    def read_csv_file(self, file_path: Path) -> Tuple[Optional[pd.DataFrame], dict]:
        """Read a CSV file in the specified format and return dataframe and metadata.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Tuple containing:
            - DataFrame with data (or None if error)
            - Dictionary with metadata
        """
        # Initialize metadata dictionary
        metadata = {
            'serial_number': '',
            'location': '',
            'project_id': '',
            'level_unit': '',
            'temperature_unit': '',
            'offset': '',
            'start_time': None,
            'stop_time': None,
            'instrument_type': 'Levelogger',  # Default value
            'num_log': 0
        }
        
        # Try different encodings
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        
        for encoding in encodings:
            try:
                # Try to infer serial number from filename first
                file_name = file_path.name
                # Common patterns for serial numbers in filenames
                serial_patterns = [
                    r'(\d{7})',  # 7-digit number (common Solinst format)
                    r'_(\d{6,8})_',  # 6-8 digit number between underscores
                    r'-(\d{6,8})-',  # 6-8 digit number between hyphens
                ]
                
                # Try to extract serial from filename
                for pattern in serial_patterns:
                    import re
                    match = re.search(pattern, file_name)
                    if match:
                        metadata['serial_number'] = match.group(1)
                        logger.debug(f"Extracted serial from filename: {metadata['serial_number']}")
                        break
                
                # Read header lines to extract metadata
                header_lines = []
                with open(file_path, 'r', encoding=encoding) as f:
                    # Read first 15 lines to capture metadata (increased from 10)
                    for i in range(15):
                        try:
                            line = f.readline().strip()
                            header_lines.append(line)
                            if not line:
                                continue
                                
                            # Check for metadata in the line - more flexible matching
                            if any(x in line.upper() for x in ['SERIAL', 'SERIAL_NUMBER', 'SERIAL NUMBER']):
                                # Extract serial number with flexibility
                                # First, try to split by colon
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        serial_candidate = parts[1].strip()
                                        # If it's not empty and contains digits, use it
                                        if serial_candidate and any(c.isdigit() for c in serial_candidate):
                                            metadata['serial_number'] = serial_candidate
                                            logger.debug(f"Extracted serial from header colon format: {metadata['serial_number']}")
                                # Next, try to find numbers after "serial" text
                                else:
                                    # Look for numbers after "serial" text
                                    serial_match = re.search(r'[Ss][Ee][Rr][Ii][Aa][Ll].*?(\d+)', line)
                                    if serial_match:
                                        metadata['serial_number'] = serial_match.group(1)
                                        logger.debug(f"Extracted serial using regex: {metadata['serial_number']}")
                            
                            elif any(x in line.upper() for x in ['PROJECT ID', 'PROJECT_ID', 'PROJECTID']):
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['project_id'] = parts[1].strip()
                            
                            elif 'LOCATION' in line.upper():
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['location'] = parts[1].strip()
                            
                            elif 'LEVEL' in line.upper() and 'UNIT' in line.upper():
                                if 'UNIT:' in line:
                                    parts = line.split('UNIT:', 1)
                                    metadata['level_unit'] = parts[1].strip() if len(parts) > 1 else ''
                                elif ':' in line:  # More flexible matching
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['level_unit'] = parts[1].strip()
                            
                            elif 'OFFSET' in line.upper():
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['offset'] = parts[1].strip()
                            
                            elif 'TEMPERATURE' in line.upper() and 'UNIT' in line.upper():
                                if 'UNIT:' in line:
                                    parts = line.split('UNIT:', 1)
                                    metadata['temperature_unit'] = parts[1].strip() if len(parts) > 1 else ''
                                elif ':' in line:  # More flexible matching
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        metadata['temperature_unit'] = parts[1].strip()
                        except:
                            # If we hit an error reading a line, move on to the next one
                            continue
                
                # If we still don't have a serial number, try to find it in the first few rows of data
                if not metadata['serial_number']:
                    # Try to read the file with pandas
                    for skip_rows in range(0, 20):  # Try different header rows
                        try:
                            temp_df = pd.read_csv(file_path, encoding=encoding, skiprows=skip_rows, nrows=5)
                            
                            # Look for columns that might contain serial numbers
                            for col in temp_df.columns:
                                if any(x in col.upper() for x in ['SERIAL', 'ID', 'NUMBER']):
                                    # Check values in this column
                                    for val in temp_df[col]:
                                        if isinstance(val, str) and any(c.isdigit() for c in val):
                                            # Look for numeric patterns in the value
                                            serial_match = re.search(r'(\d{6,8})', str(val))
                                            if serial_match:
                                                metadata['serial_number'] = serial_match.group(1)
                                                logger.debug(f"Extracted serial from data column: {metadata['serial_number']}")
                                                break
                            
                            if metadata['serial_number']:
                                break  # Stop if we found a serial number
                        except:
                            # If reading fails, try the next skip_rows value
                            continue
                
                # Read the data portion
                try:
                    # First try using pandas to determine the header row
                    df = pd.read_csv(file_path, encoding=encoding)
                    
                    # If that works without errors, check if we need to skip rows
                    # Check if the first row looks like metadata or headers
                    if not any(col.upper() in ['DATE', 'TIME', 'LEVEL', 'TEMPERATURE'] for col in df.columns):
                        # Try again with skiprows
                        for skip_rows in range(5, 20):  # Try skipping 5 to 19 rows
                            try:
                                df = pd.read_csv(file_path, encoding=encoding, skiprows=skip_rows)
                                # If we got proper column names, break
                                if any(col.upper() in ['DATE', 'TIME', 'LEVEL', 'TEMPERATURE'] for col in df.columns):
                                    break
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"Error with default read_csv, trying with skiprows: {e}")
                    # If that fails, try skipping rows explicitly
                    for skip_rows in range(5, 20):  # Try skipping 5 to 19 rows
                        try:
                            df = pd.read_csv(file_path, encoding=encoding, skiprows=skip_rows)
                            # If we made it here, we have a valid dataframe
                            break
                        except:
                            # Continue to next row count
                            continue
                
                # Check if we have the expected columns or close matches
                expected_columns = ['Date', 'Time', 'ms', 'LEVEL', 'TEMPERATURE']
                
                # Process column names to handle variations
                column_map = {}
                for col in df.columns:
                    col_upper = col.upper()
                    if any(x in col_upper for x in ['DATE', 'DATETIME']):
                        column_map[col] = 'Date'
                    elif 'TIME' in col_upper and 'DATE' not in col_upper:
                        column_map[col] = 'Time'
                    elif any(x in col_upper for x in ['MS', 'MILLISECONDS']):
                        column_map[col] = 'ms'
                    elif any(x in col_upper for x in ['LEVEL', 'WATER LEVEL', 'WATERLEVEL', 'LEVEL_M']):
                        column_map[col] = 'LEVEL'
                    elif any(x in col_upper for x in ['TEMPERATURE', 'TEMP', 'TEMPERATURE_C']):
                        column_map[col] = 'TEMPERATURE'
                
                # Rename columns if mapping exists
                if column_map:
                    df = df.rename(columns=column_map)
                
                # Convert Date and Time to timestamp
                if 'Date' in df.columns and 'Time' in df.columns:
                    try:
                        # Combine Date and Time columns
                        df['timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
                        
                        # Set start and stop times in metadata
                        if not df.empty and not df['timestamp'].isna().all():
                            metadata['start_time'] = df['timestamp'].min()
                            metadata['stop_time'] = df['timestamp'].max()
                            metadata['num_log'] = len(df)
                    except Exception as e:
                        logger.warning(f"Error parsing datetime in CSV: {e}")
                # Try for a single datetime column
                elif any(col for col in df.columns if 'DATE' in col.upper() and 'TIME' in col.upper()):
                    datetime_col = next(col for col in df.columns if 'DATE' in col.upper() and 'TIME' in col.upper())
                    try:
                        df['timestamp'] = pd.to_datetime(df[datetime_col], errors='coerce')
                        
                        # Set start and stop times in metadata
                        if not df.empty and not df['timestamp'].isna().all():
                            metadata['start_time'] = df['timestamp'].min()
                            metadata['stop_time'] = df['timestamp'].max()
                            metadata['num_log'] = len(df)
                    except Exception as e:
                        logger.warning(f"Error parsing datetime column in CSV: {e}")
                
                # Rename LEVEL to pressure to match XLE format
                if 'LEVEL' in df.columns:
                    df = df.rename(columns={'LEVEL': 'pressure'})
                
                # Add timestamp_utc column (same as timestamp for CSV files)
                if 'timestamp' in df.columns:
                    df['timestamp_utc'] = df['timestamp']
                
                # Success! Return the dataframe and metadata
                logger.info(f"Successfully read CSV file with encoding {encoding}, serial={metadata['serial_number']}")
                return df, metadata
                
            except Exception as e:
                logger.debug(f"Failed to read {file_path} with encoding {encoding}: {e}")
                # Continue to next encoding
                continue
        
        # If we get here, we failed with all encodings
        logger.warning(f"Error reading CSV file {file_path}: Failed with all encodings")
        return None, metadata

    def is_serial_match(self, file_serial: str, search_serial: str) -> bool:
        """More flexible serial number matching"""
        if not file_serial or not search_serial:
            return False
            
        # Standardize and clean serial numbers
        file_serial = file_serial.strip().upper()
        search_serial = search_serial.strip().upper()
        
        # Direct equality check
        if file_serial == search_serial:
            return True
            
        # Check if one contains the other
        if search_serial in file_serial or file_serial in search_serial:
            return True
            
        # Remove non-alphanumeric characters and check again
        import re
        clean_file_serial = re.sub(r'\W+', '', file_serial)
        clean_search_serial = re.sub(r'\W+', '', search_serial)
        
        if clean_file_serial == clean_search_serial:
            return True
            
        # Check if the numeric parts match
        file_digits = ''.join(c for c in file_serial if c.isdigit())
        search_digits = ''.join(c for c in search_serial if c.isdigit())
        
        if file_digits and search_digits and (file_digits == search_digits):
            return True
            
        return False

def main():
    app = QApplication(sys.argv)
    window = FindXLEBySerial()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main() 