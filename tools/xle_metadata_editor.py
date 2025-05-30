from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QTableWidget, 
                           QTableWidgetItem, QFileDialog, QMessageBox,
                           QMenu, QCheckBox, QProgressDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QKeyEvent
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict
import shutil
import re  # Add missing import at the top with other imports

# Import SolinstReader from parent directory
sys.path.append(str(Path(__file__).parent.parent))
from src.gui.handlers.solinst_reader import SolinstReader

logger = logging.getLogger(__name__)

class XLELocationEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.solinst_reader = SolinstReader()
        self.files_data: Dict[str, Dict] = {}  # Store file paths and their data
        self.original_files_data: Dict[str, Dict] = {}  # Store original values for comparison
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("XLE Metadata Editor")  # Updated title
        self.setMinimumSize(1000, 600)  # Wider to accommodate more columns
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create buttons
        button_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select Folder")
        self.select_btn.clicked.connect(self.select_folder)
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)
        
        # Add paste button
        self.paste_btn = QPushButton("Paste to Selected Cells")
        self.paste_btn.clicked.connect(self.paste_to_selected)
        self.paste_btn.setEnabled(False)
        
        # Add force update checkbox
        self.force_update = QCheckBox("Force Update")
        self.force_update.setToolTip("Force update all selected files even if values appear unchanged")
        
        # Add include subfolders checkbox
        self.include_subfolders = QCheckBox("Include Subfolders")
        self.include_subfolders.setChecked(True)
        
        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(self.include_subfolders)
        button_layout.addWidget(self.paste_btn)
        button_layout.addWidget(self.force_update)  # Add force update checkbox
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(8)  # Increased count for Model Number column
        self.table.setHorizontalHeaderLabels([
            "File Name", 
            "Serial Number", 
            "Model Number",  # Added Model Number column
            "Location", 
            "Project ID", 
            "Latitude", 
            "Longitude",
            "Full Path"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        
        # Install event filter for keyboard shortcuts
        self.table.installEventFilter(self)
        
        # Connect cell edit signals
        self.table.itemChanged.connect(self.on_cell_edited)
        
    def eventFilter(self, obj, event):
        """Handle keyboard shortcuts for copy and paste"""
        if obj == self.table and event.type() == QKeyEvent.KeyPress:
            if event.matches(QKeySequence.Copy):
                self.copy_selection()
                return True
            elif event.matches(QKeySequence.Paste):
                self.paste_to_selected()
                return True
        return super().eventFilter(obj, event)
        
    def on_selection_changed(self):
        """Enable/disable paste button based on selection"""
        clipboard_has_text = bool(QApplication.clipboard().text())
        has_selection = bool(self.table.selectedRanges())
        self.paste_btn.setEnabled(has_selection and clipboard_has_text)
        
    def show_context_menu(self, position):
        """Show context menu for copy/paste operations"""
        menu = QMenu()
        copy_action = menu.addAction("Copy (Ctrl+C)")
        copy_action.triggered.connect(self.copy_selection)
        
        paste_action = menu.addAction("Paste (Ctrl+V)")
        paste_action.triggered.connect(self.paste_to_selected)
        paste_action.setEnabled(bool(self.table.selectedRanges()) and 
                              QApplication.clipboard().text())
        
        menu.exec_(self.table.viewport().mapToGlobal(position))
        
    def copy_selection(self):
        """Copy selected cells to clipboard in a tab-delimited format"""
        selection = self.table.selectedRanges()
        if not selection:
            return

        # Find the bounds of the entire selection
        min_row = min(sel.topRow() for sel in selection)
        max_row = max(sel.bottomRow() for sel in selection)
        min_col = min(sel.leftColumn() for sel in selection)
        max_col = max(sel.rightColumn() for sel in selection)

        # Create a matrix of the selected cells
        matrix = []
        for row in range(min_row, max_row + 1):
            row_data = []
            for col in range(min_col, max_col + 1):
                # Check if this cell is in any of the selected ranges
                cell_selected = any(
                    sel.topRow() <= row <= sel.bottomRow() and
                    sel.leftColumn() <= col <= sel.rightColumn()
                    for sel in selection
                )
                
                if cell_selected:
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                else:
                    row_data.append("")
            matrix.append("\t".join(row_data))

        # Join rows with newlines and copy to clipboard
        QApplication.clipboard().setText("\n".join(matrix))
        
        # Enable paste button if we have data in clipboard
        self.paste_btn.setEnabled(bool(self.table.selectedRanges()))
        
    def paste_to_selected(self):
        """Paste clipboard text to selected cells"""
        # Temporarily disable sorting for pasting operation
        was_sorting_enabled = self.table.isSortingEnabled()
        if was_sorting_enabled:
            self.table.setSortingEnabled(False)
            
        clipboard_text = QApplication.clipboard().text()
        if not clipboard_text:
            # Re-enable sorting before returning
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
            return
        
        selection = self.table.selectedRanges()
        if not selection:
            # Re-enable sorting before returning
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
            return
            
        # For single value paste to multiple cells
        if "\t" not in clipboard_text and "\n" not in clipboard_text:
            # Paste the same value to all selected cells
            for sel in selection:
                for row in range(sel.topRow(), sel.bottomRow() + 1):
                    for col in range(sel.leftColumn(), sel.rightColumn() + 1):
                        # Skip non-editable columns
                        if col in [0, 1, 7]:  # File name, serial number, full path
                            continue
                        
                        self.table.setItem(row, col, QTableWidgetItem(clipboard_text))
                        
                        # Update the files_data dictionary with the new value
                        file_path = self.table.item(row, 7).text()  # Using the hidden full path column
                        if file_path in self.files_data:
                            if col == 2:  # Model Number
                                self.files_data[file_path]['model_number'] = clipboard_text
                            elif col == 3:  # Location
                                self.files_data[file_path]['location'] = clipboard_text
                            elif col == 4:  # Project ID
                                self.files_data[file_path]['project_id'] = clipboard_text
                            elif col == 5:  # Latitude 
                                self.files_data[file_path]['latitude'] = clipboard_text
                            elif col == 6:  # Longitude
                                self.files_data[file_path]['longitude'] = clipboard_text
            # Re-enable sorting before returning
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
            return
        
        # For multi-cell clipboard content
        rows = clipboard_text.split('\n')
        if not rows:
            # Re-enable sorting before returning
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
            return
            
        # Get the starting point for pasting
        start_row = min(sel.topRow() for sel in selection)
        start_col = min(sel.leftColumn() for sel in selection)
        
        # Paste data
        for i, row_text in enumerate(rows):
            if not row_text:
                continue
                
            cells = row_text.split('\t')
            for j, cell_text in enumerate(cells):
                paste_row = start_row + i
                paste_col = start_col + j
                
                # Skip if outside the table or in non-editable columns
                if (paste_row >= self.table.rowCount() or 
                    paste_col >= self.table.columnCount() or
                    paste_col in [0, 1, 7]):  # Skip non-editable columns
                    continue
                    
                self.table.setItem(paste_row, paste_col, QTableWidgetItem(cell_text))
                
                # Update the files_data dictionary
                file_path = self.table.item(paste_row, 7).text()  # Using the hidden full path column
                if file_path in self.files_data:
                    if paste_col == 2:  # Model Number
                        self.files_data[file_path]['model_number'] = cell_text
                    elif paste_col == 3:  # Location
                        self.files_data[file_path]['location'] = cell_text
                    elif paste_col == 4:  # Project ID
                        self.files_data[file_path]['project_id'] = cell_text
                    elif paste_col == 5:  # Latitude
                        self.files_data[file_path]['latitude'] = cell_text
                    elif paste_col == 6:  # Longitude
                        self.files_data[file_path]['longitude'] = cell_text
        
        # Re-enable sorting if it was previously enabled
        if was_sorting_enabled:
            self.table.setSortingEnabled(True)
        
    def on_cell_edited(self, item):
        """Update files_data when a cell is edited directly by the user"""
        try:
            # Temporarily disable sorting to prevent issues when editing
            was_sorting_enabled = self.table.isSortingEnabled()
            if was_sorting_enabled:
                self.table.setSortingEnabled(False)
                
            # Get the row and column of the edited cell
            row = item.row()
            column = item.column()
            
            # Skip non-editable columns
            if column in [0, 1, 7]:  # File name, serial number, full path
                # Re-enable sorting before returning
                if was_sorting_enabled:
                    self.table.setSortingEnabled(True)
                return
                
            # Get the file path from the hidden column
            file_path_item = self.table.item(row, 7)
            if not file_path_item:
                # Re-enable sorting before returning
                if was_sorting_enabled:
                    self.table.setSortingEnabled(True)
                return
                
            file_path = file_path_item.text()
            if file_path not in self.files_data:
                # Re-enable sorting before returning
                if was_sorting_enabled:
                    self.table.setSortingEnabled(True)
                return
            
            # Get the new text value
            new_value = item.text()
            
            # Update the files_data dictionary
            if column == 2:  # Model Number
                self.files_data[file_path]['model_number'] = new_value
                print(f"Updated model number for {file_path}: {new_value}")
            elif column == 3:  # Location
                self.files_data[file_path]['location'] = new_value
                print(f"Updated location for {file_path}: {new_value}")
            elif column == 4:  # Project ID
                self.files_data[file_path]['project_id'] = new_value
                print(f"Updated project ID for {file_path}: {new_value}")
            elif column == 5:  # Latitude
                self.files_data[file_path]['latitude'] = new_value
                print(f"Updated latitude for {file_path}: {new_value}")
            elif column == 6:  # Longitude
                self.files_data[file_path]['longitude'] = new_value
                print(f"Updated longitude for {file_path}: {new_value}")
                
            # Re-enable sorting if it was previously enabled
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
                
        except Exception as e:
            print(f"Error updating files_data: {e}")
            # Ensure sorting is re-enabled even if there's an error
            self.table.setSortingEnabled(True)

    def select_folder(self):
        """Handle folder selection"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with XLE Files",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if not folder:
            return
            
        self.files_data.clear()
        self.table.setRowCount(0)
        
        # Temporarily disable sorting while populating the table
        self.table.setSortingEnabled(False)
        
        # Get all XLE files in folder (and subfolders if checked)
        folder_path = Path(folder)
        if self.include_subfolders.isChecked():
            xle_files = list(folder_path.rglob("*.xle"))
        else:
            xle_files = list(folder_path.glob("*.xle"))
            
        if not xle_files:
            QMessageBox.information(self, "No Files Found", "No XLE files found in the selected folder.")
            return
            
        # Create progress dialog
        progress = QProgressDialog("Reading XLE files...", "Cancel", 0, len(xle_files), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Processing Files")
        progress.setMinimumDuration(0)  # Show immediately
        
        for i, file_path in enumerate(xle_files):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            progress.setLabelText(f"Reading: {file_path.name}")
            QApplication.processEvents()
            
            try:
                _, metadata = self.solinst_reader.read_xle(file_path)
                
                # Use serial number from metadata instead of XML
                serial_number = metadata.serial_number or ""
                model_number = metadata.model_number or ""
                
                # Extract additional metadata
                project_id = ""
                latitude = ""
                longitude = ""
                
                # Read the XML to get additional fields
                try:
                    # First try using a more robust method to handle potentially invalid XML
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        xml_content = f.read()
                    
                    # Clean up problematic characters that might be causing XML parsing issues
                    xml_content = xml_content.replace('\x00', '')  # Remove null bytes
                    
                    # Try to parse the XML content
                    import io
                    tree = ET.parse(io.StringIO(xml_content))
                    root = tree.getroot()
                    
                    # Try to find Project_ID
                    project_id_elem = root.find('.//Instrument_info_data_header/Project_ID')
                    if project_id_elem is not None and project_id_elem.text:
                        project_id = project_id_elem.text
                        
                    # Try to find Latitude
                    lat_elem = root.find('.//Instrument_info_data_header/Latitude')
                    if lat_elem is not None and lat_elem.text:
                        latitude = lat_elem.text
                        
                    # Try to find Longitude (note the spelling in XML is "Longtitude")
                    lon_elem = root.find('.//Instrument_info_data_header/Longtitude')
                    if lon_elem is not None and lon_elem.text:
                        longitude = lon_elem.text
                except Exception as xml_error:
                    logger.warning(f"Could not parse XML for additional metadata in {file_path.name}: {xml_error}")
                    # Continue with empty metadata values
                
                self.files_data[str(file_path)] = {
                    'serial_number': serial_number,  # Use the serial number from metadata
                    'model_number': model_number,    # Add model number
                    'location': metadata.location or "",
                    'project_id': project_id,
                    'latitude': latitude,
                    'longitude': longitude
                }
                
                # Add to table
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # File name item (non-editable)
                name_item = QTableWidgetItem(str(file_path.relative_to(folder_path)))
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, name_item)
                
                # Serial Number (non-editable)
                serial_item = QTableWidgetItem(serial_number)
                serial_item.setFlags(serial_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 1, serial_item)
                
                # Model Number (editable)
                model_item = QTableWidgetItem(model_number)
                self.table.setItem(row, 2, model_item)
                
                # Location (editable)
                location_item = QTableWidgetItem(metadata.location or "")
                self.table.setItem(row, 3, location_item)
                
                # Project ID (editable)
                project_id_item = QTableWidgetItem(project_id)
                self.table.setItem(row, 4, project_id_item)
                
                # Latitude (editable)
                latitude_item = QTableWidgetItem(latitude)
                self.table.setItem(row, 5, latitude_item)
                
                # Longitude (editable)
                longitude_item = QTableWidgetItem(longitude)
                self.table.setItem(row, 6, longitude_item)
                
                # Add full path in a hidden column for reference
                path_item = QTableWidgetItem(str(file_path))
                self.table.setItem(row, 7, path_item)
                
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                QMessageBox.warning(self, "Warning", f"Failed to read {file_path.name}: {str(e)}")
        
        progress.setValue(len(xle_files))  # Ensure dialog closes
        self.save_btn.setEnabled(True)
        
        # After populating the table, re-enable sorting
        self.table.setSortingEnabled(True)
        
        # Hide the full path column - it's just used for storing data
        self.table.setColumnHidden(7, True)
        
        # Resize columns to content
        self.table.resizeColumnsToContents()
        
        # After loading all files, make a deep copy of the original data
        self.original_files_data = {}
        for file_path, data in self.files_data.items():
            self.original_files_data[file_path] = {
                'serial_number': data.get('serial_number', ''),
                'model_number': data.get('model_number', ''),  # Add model number to original data
                'location': data.get('location', ''),
                'project_id': data.get('project_id', ''),
                'latitude': data.get('latitude', ''),
                'longitude': data.get('longitude', '')
            }
        
    def save_changes(self):
        """Save location changes to files with progress dialog"""
        try:
            # Display debug information to console
            print("DEBUG: Checking for changes...")
            
            # Always REFRESH files_data from what's actually in the table
            self._refresh_files_data_from_table()
            
            # Count files that need modification
            files_to_modify = []
            # Get all selected files first if any
            selected_rows = set()
            for item in self.table.selectedItems():
                selected_rows.add(item.row())
            
            # Check if force update is enabled
            force_update = self.force_update.isChecked()
            print(f"Force Update checkbox state: {force_update}")
            
            # Check if any rows are selected - if so, we should only update those
            if selected_rows:
                print(f"Selected rows: {selected_rows}")
            
            # Create a dictionary to map table row indices to file paths for looking up selected rows
            row_to_file_map = {}
            for row in range(self.table.rowCount()):
                file_path_item = self.table.item(row, 7)
                if file_path_item and file_path_item.text():
                    row_to_file_map[row] = file_path_item.text()
            
            # Now process all files
            for file_path in self.files_data.keys():
                # Find the row for this file
                file_row = None
                for row, path in row_to_file_map.items():
                    if path == file_path:
                        file_row = row
                        break
                
                # Skip if we have selected rows and this file's row isn't selected
                if selected_rows and (file_row is None or file_row not in selected_rows):
                    print(f"Skipping file {Path(file_path).name} as it's not in selected rows")
                    continue
                
                # Do a sanity check on the file - make sure it exists
                if not Path(file_path).exists():
                    print(f"File {file_path} doesn't exist, skipping")
                    continue
                    
                # Get current values from files_data
                model_number = self.files_data[file_path].get('model_number', '')
                location = self.files_data[file_path].get('location', '')
                project_id = self.files_data[file_path].get('project_id', '')
                latitude = self.files_data[file_path].get('latitude', '')
                longitude = self.files_data[file_path].get('longitude', '')
                
                # Get original values from original_files_data
                if file_path in self.original_files_data:
                    original_model_number = self.original_files_data[file_path].get('model_number', '')
                    original_location = self.original_files_data[file_path].get('location', '')
                    original_project_id = self.original_files_data[file_path].get('project_id', '')
                    original_latitude = self.original_files_data[file_path].get('latitude', '')
                    original_longitude = self.original_files_data[file_path].get('longitude', '')
                else:
                    # Fall back to current data if original missing
                    original_model_number = model_number
                    original_location = location
                    original_project_id = project_id
                    original_latitude = latitude
                    original_longitude = longitude
                
                # More robust normalization function
                def normalize_string(s):
                    if s is None:
                        return ""
                    # Convert to string if not already
                    s = str(s)
                    # Remove common escape sequences
                    s = s.replace('\\n', ' ').replace('\\r', ' ').replace('\\t', ' ')
                    # Remove backslashes
                    s = s.replace('\\\\', '\\').replace('\\', '')
                    # Normalize whitespace
                    s = ' '.join(s.split())
                    return s.strip()
                
                # Normalize all strings for comparison
                norm_model_number = normalize_string(model_number)
                norm_original_model_number = normalize_string(original_model_number)
                norm_location = normalize_string(location)
                norm_original_location = normalize_string(original_location)
                norm_project_id = normalize_string(project_id)
                norm_original_project_id = normalize_string(original_project_id)
                norm_latitude = normalize_string(latitude)
                norm_original_latitude = normalize_string(original_latitude)
                norm_longitude = normalize_string(longitude)
                norm_original_longitude = normalize_string(original_longitude)
                
                # Print detailed comparison data including raw representation
                print(f"File: {Path(file_path).name}")
                print(f"  Model Number: {repr(original_model_number)} vs {repr(model_number)}")
                print(f"    Normalized: {repr(norm_original_model_number)} vs {repr(norm_model_number)}")
                print(f"    Equal?: {norm_original_model_number == norm_model_number}")
                
                print(f"  Location: {repr(original_location)} vs {repr(location)}")
                print(f"    Normalized: {repr(norm_original_location)} vs {repr(norm_location)}")
                print(f"    Equal?: {norm_original_location == norm_location}")
                
                print(f"  Project ID: {repr(original_project_id)} vs {repr(project_id)}")
                print(f"    Normalized: {repr(norm_original_project_id)} vs {repr(norm_project_id)}")
                print(f"    Equal?: {norm_original_project_id == norm_project_id}")
                
                print(f"  Latitude: {repr(original_latitude)} vs {repr(latitude)}")
                print(f"    Normalized: {repr(norm_original_latitude)} vs {repr(norm_latitude)}")
                print(f"    Equal?: {norm_original_latitude == norm_latitude}")
                
                print(f"  Longitude: {repr(original_longitude)} vs {repr(longitude)}")
                print(f"    Normalized: {repr(norm_original_longitude)} vs {repr(norm_longitude)}")
                print(f"    Equal?: {norm_original_longitude == norm_longitude}")
                
                # Determine if values have changed - compare with original values, not current
                values_changed = (
                    norm_original_model_number != norm_model_number or
                    norm_original_location != norm_location or
                    norm_original_project_id != norm_project_id or
                    norm_original_latitude != norm_latitude or
                    norm_original_longitude != norm_longitude
                )
                
                # Debug which specific fields changed
                if values_changed:
                    changed_fields = []
                    if norm_original_model_number != norm_model_number:
                        changed_fields.append("Model Number")
                    if norm_original_location != norm_location:
                        changed_fields.append("Location")
                    if norm_original_project_id != norm_project_id:
                        changed_fields.append("Project ID")
                    if norm_original_latitude != norm_latitude:
                        changed_fields.append("Latitude")
                    if norm_original_longitude != norm_longitude:
                        changed_fields.append("Longitude")
                    print(f"  Changed fields: {', '.join(changed_fields)}")
                
                # Should we include this file?
                # - If values have changed: Yes
                # - If force update is checked and (no rows are selected or this row is selected): Yes
                should_include = values_changed or (force_update and (not selected_rows or file_row in selected_rows))
                
                print(f"  Values changed: {values_changed}")
                print(f"  Force Update: {force_update}")
                print(f"  Should include: {should_include}")
                
                if should_include:
                    files_to_modify.append((
                        file_path,
                        model_number,  # Add model_number to the tuple
                        location,  
                        project_id,
                        latitude,
                        longitude
                    ))

            # ---------------- IMPORTANT USER MESSAGE -----------------
            print(f"Total files to modify: {len(files_to_modify)}")
            if not files_to_modify and force_update:
                note = ""
                if selected_rows:
                    note = " Make sure you've selected the files you want to update."
                QMessageBox.information(self, "No Changes", 
                                      f"No files to update. Force Update is ON but no changes were detected.{note}\n\n"
                                      "To modify files, check the 'Force Update' box and click 'Save Changes'.")
                return
            elif not files_to_modify:
                QMessageBox.information(self, "No Changes", 
                                      "No changes detected. If you want to force an update, "
                                      "check the 'Force Update' box and click 'Save Changes' again.")
                return

            # Create progress dialog
            progress = QProgressDialog("Saving changes...", "Cancel", 0, len(files_to_modify), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Saving Changes")
            progress.setMinimumDuration(0)

            modified_count = 0
            for i, (file_path, model_number, location, project_id, latitude, longitude) in enumerate(files_to_modify):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"Modifying: {Path(file_path).name}")
                QApplication.processEvents()

                try:
                    # Create backup with unique name
                    import time
                    timestamp = int(time.time())
                    backup_path = Path(f"{file_path}.{timestamp}.bak")
                    shutil.copy2(file_path, backup_path)

                    try:
                        # Use a more reliable method: parse and modify XML properly
                        success = self._modify_xml_safely(file_path, {
                            'Model_number': model_number,  # Add Model_number to the modifications
                            'Location': location,
                            'Project_ID': project_id,
                            'Latitude': latitude,
                            'Longtitude': longitude  # Note the spelling in XML
                        })
                        
                        if success:
                            print(f"Successfully modified file: {Path(file_path).name}")
                            modified_count += 1
                        else:
                            print(f"Failed to modify file: {Path(file_path).name}")
                            # Restore from backup
                            shutil.copy2(backup_path, file_path)

                    except Exception as e:
                        # Restore from backup if failed
                        print(f"Error modifying file, restoring from backup: {e}")
                        shutil.copy2(backup_path, file_path)
                        raise e
                    finally:
                        # Clean up backup
                        if backup_path.exists():
                            backup_path.unlink()

                except Exception as e:
                    logger.error(f"Error modifying file {file_path}: {e}")
                    if progress.wasCanceled():
                        break
                    response = QMessageBox.question(
                        self,
                        "Error",
                        f"Failed to modify {Path(file_path).name}: {str(e)}\nContinue with remaining files?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if response == QMessageBox.No:
                        break

            progress.setValue(len(files_to_modify))

            QMessageBox.information(
                self,
                "Success",
                f"Successfully modified {modified_count} of {len(files_to_modify)} files"
            )

            # Refresh the display
            self.select_folder()

        except Exception as e:
            logger.error(f"Error saving changes: {e}")
            print(f"ERROR in save_changes: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save changes: {str(e)}"
            )

    def _refresh_files_data_from_table(self):
        """Refresh the files_data dictionary from what's actually in the table"""
        try:
            print("Refreshing files_data from table values")
            
            # Go through each row in the table
            for row in range(self.table.rowCount()):
                # Get the file path from the hidden column
                file_path_item = self.table.item(row, 7)
                if not file_path_item:
                    continue
                    
                file_path = file_path_item.text()
                if file_path not in self.files_data:
                    continue
                
                # Get the values from the table
                model_number = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
                location = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
                project_id = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
                latitude = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
                longitude = self.table.item(row, 6).text() if self.table.item(row, 6) else ""
                
                # Update files_data with current table values
                self.files_data[file_path]['model_number'] = model_number
                self.files_data[file_path]['location'] = location
                self.files_data[file_path]['project_id'] = project_id
                self.files_data[file_path]['latitude'] = latitude
                self.files_data[file_path]['longitude'] = longitude
                
                print(f"Refreshed data for {Path(file_path).name}")
                
        except Exception as e:
            print(f"Error refreshing files_data: {e}")

    def _modify_xml_safely(self, file_path, tag_values):
        """
        A more reliable way to modify XML data in XLE files.
        Uses multiple approaches to ensure successful updates.
        
        Args:
            file_path: Path to the XLE file
            tag_values: Dictionary of tag names and new values
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Import os here to ensure it's available in this method's scope
        import os
        
        # First try the direct string replacement approach (faster)
        try:
            # Read the XML file as text
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                xml_content = f.read()
            
            # Clean up problematic characters
            xml_content = xml_content.replace('\x00', '')
            
            # Dictionary to track successful replacements
            replaced_tags = {}
            
            # Try direct string replacement first for each tag
            for tag_name, new_value in tag_values.items():
                start_tag = f"<{tag_name}>"
                end_tag = f"</{tag_name}>"
                
                # Find all occurrences - we may need to update multiple instances
                start_pos = 0
                replacement_count = 0
                
                while True:
                    # Find the next occurrence
                    tag_start = xml_content.find(start_tag, start_pos)
                    if tag_start == -1:
                        break
                    
                    # Find the closing tag
                    content_start = tag_start + len(start_tag)
                    tag_end = xml_content.find(end_tag, content_start)
                    
                    if tag_end == -1:
                        break
                    
                    # Replace the content
                    xml_content = xml_content[:content_start] + new_value + xml_content[tag_end:]
                    
                    # Update the search position
                    start_pos = content_start + len(new_value)
                    replacement_count += 1
                
                if replacement_count > 0:
                    replaced_tags[tag_name] = replacement_count
                    print(f"  Replaced {replacement_count} instances of {tag_name} with: {new_value}")
            
            # Write the modified XML back to the file if any replacements were made
            if replaced_tags:
                # Use a temporary file to avoid partial writes
                temp_path = f"{file_path}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                
                # Replace the original file with the temp file
                os.replace(temp_path, file_path)
                return True
            else:
                print(f"  No tags were replaced using direct string replacement")
                # If no replacements made, try the fallback approach
                raise ValueError("No replacements made with direct method")
        
        except Exception as e:
            print(f"  Direct string replacement failed, trying fallback approach: {e}")
            
            # Fallback approach: Use ElementTree with proper XML parsing
            try:
                # Try to parse the XML
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # Dictionary to track successful replacements
                replaced_tags = {}
                
                # Find and update elements, searching through all instrument_info_data_header sections
                for tag_name, new_value in tag_values.items():
                    # First check for direct children of root
                    elements = root.findall(f".//{tag_name}")
                    
                    # Also check specifically in the instrument_info_data_header section
                    header_elements = root.findall(f".//Instrument_info_data_header/{tag_name}")
                    
                    # Combine the results
                    all_elements = elements + header_elements
                    
                    # Update all found elements
                    for elem in all_elements:
                        elem.text = new_value
                        replaced_tags[tag_name] = replaced_tags.get(tag_name, 0) + 1
                        print(f"  ElementTree: Updated {tag_name} to {new_value}")
                
                # Write the modified XML back to the file if any replacements were made
                if replaced_tags:
                    # Use a temporary file to avoid partial writes
                    temp_path = f"{file_path}.tmp"
                    tree.write(temp_path, encoding='utf-8', xml_declaration=True)
                    
                    # Replace the original file with the temp file
                    os.replace(temp_path, file_path)
                    return True
                else:
                    print(f"  No tags were replaced using ElementTree approach")
                    # If no replacements made, try one last approach
                    raise ValueError("No replacements made with ElementTree method")
                    
            except Exception as xml_parse_error:
                print(f"  ElementTree approach failed, trying regex approach: {xml_parse_error}")
                
                # Last resort: Use regex with proper error handling
                try:
                    # Read the file again
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    # Dictionary to track successful replacements
                    replaced_tags = {}
                    
                    # Function to replace tag content using regex
                    def replace_tag_content_regex(content, tag_name, new_value):
                        import re
                        pattern = f"<{re.escape(tag_name)}>.*?</{re.escape(tag_name)}>"
                        replacement = f"<{tag_name}>{new_value}</{tag_name}>"
                        
                        # Count matches before replacement
                        matches = re.findall(pattern, content, re.DOTALL)
                        count = len(matches)
                        
                        if count > 0:
                            # Perform the replacement
                            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                            print(f"  Regex: Replaced {count} instances of {tag_name} with: {new_value}")
                            return new_content, count
                        else:
                            return content, 0
                    
                    # Apply regex replacement for each tag
                    for tag_name, new_value in tag_values.items():
                        content, count = replace_tag_content_regex(content, tag_name, new_value)
                        if count > 0:
                            replaced_tags[tag_name] = count
                    
                    # Write back if any replacements were made
                    if replaced_tags:
                        # Use a temporary file to avoid partial writes
                        temp_path = f"{file_path}.tmp"
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())  # Ensure data is written to disk
                        
                        # Replace the original file with the temp file
                        os.replace(temp_path, file_path)
                        return True
                    else:
                        print(f"  No tags were replaced using regex approach")
                        return False
                        
                except Exception as regex_error:
                    print(f"  All approaches failed to modify the file: {regex_error}")
                    return False

def main():
    app = QApplication(sys.argv)
    window = XLELocationEditor()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()