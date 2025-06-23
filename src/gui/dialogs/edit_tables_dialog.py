from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QMessageBox, QLabel, QLineEdit, QScrollBar,
    QApplication, QShortcut, QFrame, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
import sqlite3
from ...database.manager import DatabaseManager
from ..handlers.style_handler import StyleHandler  # Import the style handler

class EditTablesDialog(QDialog):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # Pagination settings
        self.page_size = 100  # Number of records per page
        self.current_offset = 0  # Current offset for pagination
        self.total_records = 0  # Total number of records in the table
        self.is_loading = False  # Flag to prevent multiple loads
        self.current_table = ""  # Current table name
        self.current_well = ""  # Current well number (for water_level_readings)
        self.column_names = []  # Column names for the current table
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Edit Tables")
        self.setMinimumSize(900, 700)  # Slightly larger default size
        
        # Apply StyleHandler common stylesheet
        self.setStyleSheet(StyleHandler.get_common_stylesheet())
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Consistent margins
        layout.setSpacing(8)  # Consistent spacing
        
        # Create header with title and tools
        header_layout = QHBoxLayout()
        title_label = QLabel("Database Table Editor")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #3070B0;
            margin-bottom: 5px;
        """)
        header_layout.addWidget(title_label)
        
        # Add Load Legacy Tables button
        load_legacy_button = QPushButton("Load Legacy Tables")
        load_legacy_button.setStyleSheet("""
            background-color: #3070B0;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 6px 12px;
            margin-right: 10px;
        """)
        load_legacy_button.clicked.connect(self.load_legacy_tables)
        header_layout.addWidget(load_legacy_button)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Add a line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #CCDDEE;")
        layout.addWidget(line)
        
        # Create table selection area
        table_layout = QHBoxLayout()
        table_layout.setSpacing(10)  # Add spacing between elements
        
        table_label = QLabel("Select Table:")
        table_label.setStyleSheet("font-weight: bold;")
        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)  # Make the dropdown wider
        
        # Add available tables
        self.tables = [
            "wells",
            "transducers",
            "transducer_locations",
            "barologgers",
            "barologger_locations",
            "barometric_readings",
            "water_level_readings",
            "master_baro_readings",
            "manual_level_readings",
            "water_level_meter_corrections",
            "telemetry_level_readings",
            "transducer_imported_files",  # Add transducer imported files table
            "barologger_imported_files"   # Add barologger imported files table
        ]
        self.table_combo.addItems(self.tables)
        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        
        table_layout.addWidget(table_label)
        table_layout.addWidget(self.table_combo)
        
        # Add well filter dropdown (initially hidden)
        self.well_label = QLabel("Well:")
        self.well_label.setStyleSheet("font-weight: bold;")
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(150)
        self.well_combo.currentTextChanged.connect(self.load_well_data)
        self.well_label.setVisible(False)
        self.well_combo.setVisible(False)
        
        table_layout.addWidget(self.well_label)
        table_layout.addWidget(self.well_combo)
        
        # Add filter section
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("font-weight: bold;")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by Well Number or CAE...")
        self.filter_input.setMinimumWidth(250)
        self.filter_input.textChanged.connect(self.apply_filter)
        
        table_layout.addWidget(filter_label)
        table_layout.addWidget(self.filter_input)
        table_layout.addStretch()
        
        layout.addLayout(table_layout)
        
        # Create table widget with better styling
        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CCDDEE;
                gridline-color: #E0E8F0;
                selection-background-color: #3070B0;
                selection-color: white;
                alternate-background-color: #F0F4F8;
            }
            QHeaderView::section {
                background-color: #CCDDEE;
                color: #333366;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #E0E8F0;
            }
            QTableWidget::item:selected {
                background-color: #3070B0;
                color: white;
            }
        """)
        
        # Enable sorting
        self.table_widget.setSortingEnabled(True)
        
        # Enable copy and paste functionality
        self.table_widget.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table_widget.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        
        # Connect scroll events for lazy loading
        self.table_widget.verticalScrollBar().valueChanged.connect(self.check_scroll_position)
        
        # Status label for showing record count and loading status
        self.status_label = QLabel("No data loaded")
        self.status_label.setStyleSheet("""
            font-style: italic;
            color: #555555;
            padding: 5px;
        """)
        
        # Create buttons with improved styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Add spacing between buttons
        
        # Add Delete Row button
        delete_button = QPushButton("Delete Selected Row")
        delete_button.setStyleSheet("""
            background-color: #B03050;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 6px 12px;
        """)
        delete_button.clicked.connect(self.delete_selected_row)
        
        # Add Export to CSV button
        export_button = QPushButton("Export to CSV")
        export_button.setStyleSheet("""
            background-color: #3070B0;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 6px 12px;
        """)
        export_button.clicked.connect(self.export_to_csv)
        
        save_button = QPushButton("Save Changes")
        save_button.setStyleSheet(StyleHandler.get_action_button_style())
        save_button.clicked.connect(self.save_changes)
        
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            background-color: #707070;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 6px 12px;
        """)
        close_button.clicked.connect(self.close)
        
        button_layout.addWidget(delete_button)
        button_layout.addWidget(export_button)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)
        
        # Add all components to main layout
        layout.addWidget(self.table_widget)
        layout.addWidget(self.status_label)
        
        # Add padding before buttons
        spacer = QFrame()
        spacer.setFixedHeight(5)
        layout.addWidget(spacer)
        
        layout.addLayout(button_layout)
        
        # Load initial table data
        self.on_table_changed(self.tables[0])
        
        # Add keyboard shortcuts for copy and paste
        copy_shortcut = QShortcut(QKeySequence.Copy, self)
        copy_shortcut.activated.connect(self.copy_selection)
        paste_shortcut = QShortcut(QKeySequence.Paste, self)
        paste_shortcut.activated.connect(self.paste_selection)
        
        # Add tooltip to show keyboard shortcuts
        self.setToolTip("Keyboard Shortcuts:\nCtrl+C: Copy\nCtrl+V: Paste")
    
    def on_table_changed(self, table_name):
        """Handle table selection changes"""
        self.current_table = table_name
        self.current_offset = 0
        
        # Show/hide well filter for water_level_readings and telemetry_level_readings tables
        is_water_levels = table_name in ("water_level_readings", "telemetry_level_readings")
        self.well_label.setVisible(is_water_levels)
        self.well_combo.setVisible(is_water_levels)
        
        if is_water_levels:
            # Load well list
            self.load_wells_list()
            # Clear the table
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.status_label.setText("Select a well to load data")
        else:
            # For other tables, just load the data directly
            self.get_table_structure(table_name)
            self.load_page_data()
    
    def get_table_structure(self, table_name):
        """Get table structure (column names) and total record count"""
        try:
            if not self.db_manager.current_db:
                return
                
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                # Get column names
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                self.column_names = [info[1] for info in cursor.fetchall()]
                
                # Get total record count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                self.total_records = cursor.fetchone()[0]
                
                # Set up table structure
                self.table_widget.setColumnCount(len(self.column_names))
                self.table_widget.setHorizontalHeaderLabels(self.column_names)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error getting table structure: {str(e)}")
    
    def load_wells_list(self):
        """Load list of wells into well combo box"""
        try:
            if not self.db_manager.current_db:
                return
                
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT well_number FROM wells ORDER BY well_number")
                wells = cursor.fetchall()
                
                # Clear and repopulate wells dropdown
                self.well_combo.clear()
                self.well_combo.addItem("-- Select Well --")
                for well in wells:
                    self.well_combo.addItem(well[0])
                
                # Clear table while well is not selected
                self.table_widget.setRowCount(0)
                self.table_widget.setColumnCount(0)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading wells list: {str(e)}")
    
    def load_well_data(self, well_number):
        """Load water level data for a specific well"""
        if well_number == "-- Select Well --":
            # Clear table and return
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.status_label.setText("Select a well to load data")
            return
            
        self.current_well = well_number
        self.current_offset = 0
        
        # Get the table structure for the selected well
        try:
            if not self.db_manager.current_db:
                QMessageBox.warning(self, "Warning", "No database is currently open.")
                return
                
            # Get the column structure for the table
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({self.current_table})")
                self.column_names = [info[1] for info in cursor.fetchall()]
                
                # Get total count for this well
                cursor.execute(f"SELECT COUNT(*) FROM {self.current_table} WHERE well_number = ?", 
                             (well_number,))
                self.total_records = cursor.fetchone()[0]
            
            # Set up the table structure
            self.table_widget.setColumnCount(len(self.column_names))
            self.table_widget.setHorizontalHeaderLabels(self.column_names)
            
            # Update window title to include well info
            self.setWindowTitle(f"Edit Tables - {self.current_table} for {well_number}")
            
            # Load the first page of data
            self.load_page_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error setting up well data: {str(e)}")
    
    def load_page_data(self):
        """Load a page of data from the current offset"""
        if self.is_loading:
            return
            
        self.is_loading = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.status_label.setText(f"Loading... ({self.current_offset+1}-{min(self.current_offset+self.page_size, self.total_records)} of {self.total_records})")
        
        try:
            if not self.db_manager.current_db:
                self.is_loading = False
                QApplication.restoreOverrideCursor()
                return
                
            with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                cursor = conn.cursor()
                
                if self.current_table in ("water_level_readings", "telemetry_level_readings") and self.current_well:
                    # Load data for a specific well with pagination
                    query = f"""
                        SELECT * FROM {self.current_table} 
                        WHERE well_number = ? 
                        ORDER BY timestamp_utc DESC 
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(query, (self.current_well, self.page_size, self.current_offset))
                else:
                    # Load data for any other table with pagination
                    query = f"""
                        SELECT * FROM {self.current_table} 
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(query, (self.page_size, self.current_offset))
                
                # Fetch data
                data = cursor.fetchall()
                
                # Preserve existing rows if this is not the first page
                existing_rows = self.table_widget.rowCount()
                if self.current_offset == 0:
                    self.table_widget.setRowCount(len(data))
                    row_offset = 0
                else:
                    self.table_widget.setRowCount(existing_rows + len(data))
                    row_offset = existing_rows
                
                # Fill data
                for i, row_data in enumerate(data):
                    row_index = row_offset + i
                    for col, value in enumerate(row_data):
                        item = QTableWidgetItem(str(value) if value is not None else "")
                        # Added styling for cells with NULL values
                        if value is None:
                            item.setBackground(Qt.lightGray)
                            item.setForeground(Qt.darkGray)
                        self.table_widget.setItem(row_index, col, item)
                
                # Adjust column widths only on first load
                if self.current_offset == 0:
                    self.table_widget.resizeColumnsToContents()
                
                # Update status label with better formatting
                loaded_records = min(self.current_offset + self.page_size, self.total_records)
                if self.current_offset + self.page_size < self.total_records:
                    load_message = f" (Scroll down for more)"
                else:
                    load_message = f" (All records loaded)"
                    
                self.status_label.setText(
                    f"Showing {self.table_widget.rowCount()} of {self.total_records} records • "
                    f"{loaded_records} loaded{load_message}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")
            
        finally:
            self.is_loading = False
            QApplication.restoreOverrideCursor()
    
    def check_scroll_position(self, value):
        """Check scroll position and load more data if necessary"""
        if self.is_loading:
            return
            
        scroll_bar = self.table_widget.verticalScrollBar()
        
        # If scrolled near the bottom (within 20% of the end) and more data is available
        if (value > scroll_bar.maximum() * 0.8 and 
            self.current_offset + self.page_size < self.total_records):
            
            # Load the next page
            self.current_offset += self.page_size
            
            # Use a short timer to prevent multiple loads when scrolling quickly
            QTimer.singleShot(100, self.load_page_data)
    
    def load_table_data(self, table_name):
        """Reset and load first page of table data"""
        self.current_table = table_name
        self.current_offset = 0
        self.current_well = ""
        
        self.get_table_structure(table_name)
        self.load_page_data()
        
        # Reset window title
        self.setWindowTitle(f"Edit Tables")
    
    def save_changes(self):
        """Save changes to the database"""
        try:
            if not self.db_manager.current_db:
                QMessageBox.warning(self, "Warning", "No database is currently open.")
                return

            reply = QMessageBox.question(
                self,
                "Confirm Save",
                "Are you sure you want to save changes to the database?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Show temporary status message
                original_status = self.status_label.text()
                self.status_label.setText("Saving changes to database...")
                self.status_label.setStyleSheet("color: #3070B0; font-weight: bold;")
                QApplication.processEvents()  # Update UI immediately
                
                # Get current table name
                table_name = self.table_combo.currentText()
                
                # Connect to the database using the path
                with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                    cursor = conn.cursor()
                    
                    # Get column names
                    columns = []
                    for col in range(self.table_widget.columnCount()):
                        columns.append(self.table_widget.horizontalHeaderItem(col).text())
                    
                    # Prepare data for update
                    for row in range(self.table_widget.rowCount()):
                        row_data = []
                        for col in range(self.table_widget.columnCount()):
                            item = self.table_widget.item(row, col)
                            value = item.text() if item else None
                            row_data.append(value)
                        
                        # Update database
                        update_query = f"UPDATE {table_name} SET "
                        update_query += ", ".join([f"{col} = ?" for col in columns[1:]])
                        update_query += f" WHERE {columns[0]} = ?"
                        
                        # Reorder values to put primary key at the end
                        values = row_data[1:] + [row_data[0]]
                        
                        cursor.execute(update_query, values)
                    
                    conn.commit()
                
                # Mark database as modified
                self.db_manager.mark_as_modified()
                
                # Restore status label style but with success message
                self.status_label.setText("Changes saved successfully!")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Set a timer to restore the original status message after 3 seconds
                QTimer.singleShot(3000, lambda: self.status_label.setText(original_status))
                QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("font-style: italic; color: #555555;"))
                
                QMessageBox.information(self, "Success", "Changes saved successfully!")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving changes: {str(e)}")

    def apply_filter(self):
        """Apply filter to the table"""
        filter_text = self.filter_input.text().lower()
        
        for row in range(self.table_widget.rowCount()):
            show_row = False
            
            # Check all columns for the filter text
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item and filter_text in item.text().lower():
                    show_row = True
                    break
            
            self.table_widget.setRowHidden(row, not show_row)

    def delete_selected_row(self):
        """Delete the selected row from the database"""
        current_row = self.table_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a row to delete")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this row? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Show temporary status message
                original_status = self.status_label.text()
                self.status_label.setText("Deleting row...")
                self.status_label.setStyleSheet("color: #B03050; font-weight: bold;")
                QApplication.processEvents()  # Update UI immediately
                
                # Get the primary key (first column) value
                primary_key_value = self.table_widget.item(current_row, 0).text()
                table_name = self.table_combo.currentText()
                primary_key_column = self.table_widget.horizontalHeaderItem(0).text()

                # Delete from database
                with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                    cursor = conn.cursor()
                    delete_query = f"DELETE FROM {table_name} WHERE {primary_key_column} = ?"
                    cursor.execute(delete_query, (primary_key_value,))
                    conn.commit()

                # Remove row from table widget
                self.table_widget.removeRow(current_row)
                
                # Mark database as modified
                self.db_manager.mark_as_modified()
                
                # Restore status label style but with success message
                self.status_label.setText("Row deleted successfully!")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Set a timer to restore the original status message after 3 seconds
                QTimer.singleShot(3000, lambda: self.status_label.setText(original_status))
                QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("font-style: italic; color: #555555;"))
                
                QMessageBox.information(self, "Success", "Row deleted successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting row: {str(e)}")

    def copy_selection(self):
        """Copy selected cells to clipboard in Excel-compatible format"""
        selected_ranges = self.table_widget.selectedRanges()
        if not selected_ranges:
            return
            
        # Find the overall bounds of all selections
        min_row = min(range_item.topRow() for range_item in selected_ranges)
        max_row = max(range_item.bottomRow() for range_item in selected_ranges)
        min_col = min(range_item.leftColumn() for range_item in selected_ranges)
        max_col = max(range_item.rightColumn() for range_item in selected_ranges)
        
        # Create a matrix to store the data
        matrix = []
        
        # Fill the matrix with data from all selected ranges
        for row in range(min_row, max_row + 1):
            row_data = []
            for col in range(min_col, max_col + 1):
                # Check if the current cell is within any of the selected ranges
                cell_selected = any(
                    range_item.topRow() <= row <= range_item.bottomRow() and
                    range_item.leftColumn() <= col <= range_item.rightColumn()
                    for range_item in selected_ranges
                )
                
                if cell_selected:
                    item = self.table_widget.item(row, col)
                    row_data.append(item.text() if item else "")
                else:
                    row_data.append("")
            matrix.append(row_data)
        
        # Convert matrix to clipboard text (tab-separated for Excel compatibility)
        clipboard_text = "\n".join("\t".join(str(cell) for cell in row) for row in matrix)
        
        # Set clipboard content
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text)
        
    def paste_selection(self):
        """Paste data from clipboard to selected cells with Excel-like behavior"""
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        if not clipboard_text:
            return
            
        # Get the current selection
        selected_ranges = self.table_widget.selectedRanges()
        if not selected_ranges:
            return
        
        # Parse clipboard data
        rows = clipboard_text.split("\n")
        parsed_data = [row.split("\t") for row in rows if row.strip()]
        
        if not parsed_data:
            return
            
        # Get dimensions of clipboard data
        clipboard_rows = len(parsed_data)
        clipboard_cols = len(parsed_data[0])
        
        # Special case: Single cell copied to multiple cells
        is_single_cell = clipboard_rows == 1 and clipboard_cols == 1
        
        # For each selected range
        for range_item in selected_ranges:
            start_row = range_item.topRow()
            start_col = range_item.leftColumn()
            range_rows = range_item.rowCount()
            range_cols = range_item.columnCount()
            
            if is_single_cell:
                # Fill all selected cells with the single value
                single_value = parsed_data[0][0]
                for row in range(start_row, start_row + range_rows):
                    for col in range(start_col, start_col + range_cols):
                        if row < self.table_widget.rowCount() and col < self.table_widget.columnCount():
                            item = self.table_widget.item(row, col)
                            if not item:
                                item = QTableWidgetItem()
                                self.table_widget.setItem(row, col, item)
                            item.setText(single_value)
            else:
                # Fill the range with repeating pattern from clipboard
                for i in range(range_rows):
                    for j in range(range_cols):
                        # Calculate source indices with wrapping
                        source_row = i % clipboard_rows
                        source_col = j % clipboard_cols
                        
                        # Calculate target position
                        target_row = start_row + i
                        target_col = start_col + j
                        
                        # Check bounds
                        if (target_row >= self.table_widget.rowCount() or 
                            target_col >= self.table_widget.columnCount()):
                            continue
                        
                        # Get value from clipboard data
                        value = parsed_data[source_row][source_col]
                        
                        # Update or create item
                        item = self.table_widget.item(target_row, target_col)
                        if not item:
                            item = QTableWidgetItem()
                            self.table_widget.setItem(target_row, target_col, item)
                        item.setText(value)
        
        # Mark database as modified
        self.db_manager.mark_as_modified()

    def export_to_csv(self):
        """Export the current table data to a CSV file"""
        try:
            # Get the current table name for the default filename
            table_name = self.table_combo.currentText()
            if self.current_well:
                table_name = f"{table_name}_{self.current_well}"
            
            # Open file dialog to get save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export to CSV",
                f"{table_name}.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # Show temporary status message
            original_status = self.status_label.text()
            self.status_label.setText("Exporting to CSV...")
            self.status_label.setStyleSheet("color: #3070B0; font-weight: bold;")
            QApplication.processEvents()
            
            # Get headers
            headers = []
            for col in range(self.table_widget.columnCount()):
                headers.append(self.table_widget.horizontalHeaderItem(col).text())
            
            # Write to CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                import csv
                writer = csv.writer(csvfile)
                writer.writerow(headers)  # Write headers
                
                # Write data rows (only visible rows)
                for row in range(self.table_widget.rowCount()):
                    if not self.table_widget.isRowHidden(row):
                        row_data = []
                        for col in range(self.table_widget.columnCount()):
                            item = self.table_widget.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
            
            # Restore status label style but with success message
            self.status_label.setText("Export completed successfully!")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Set a timer to restore the original status message after 3 seconds
            QTimer.singleShot(3000, lambda: self.status_label.setText(original_status))
            QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("font-style: italic; color: #555555;"))
            
            QMessageBox.information(self, "Success", "Table exported to CSV successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting to CSV: {str(e)}")

    def load_legacy_tables(self):
        """Load data from legacy CSV files into the database"""
        # List of tables to update
        legacy_tables = [
            "barologger_locations",
            "barologgers",
            "transducer_locations",
            "transducers",
            "wells"
        ]
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Load Legacy Tables",
            "This will replace the data in the following tables:\n\n" + 
            "\n".join(f"• {table}" for table in legacy_tables) + 
            "\n\nAre you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Show temporary status message
                original_status = self.status_label.text()
                self.status_label.setText("Loading legacy tables...")
                self.status_label.setStyleSheet("color: #3070B0; font-weight: bold;")
                QApplication.processEvents()
                
                import os
                import csv
                import pandas as pd
                
                # Get the legacy tables directory path relative to the database location
                db_dir = os.path.dirname(str(self.db_manager.current_db))
                legacy_dir = os.path.join(db_dir, "legacy_tables")
                
                if not os.path.exists(legacy_dir):
                    raise Exception(f"Legacy tables directory not found at: {legacy_dir}")
                
                with sqlite3.connect(str(self.db_manager.current_db)) as conn:
                    for table in legacy_tables:
                        # Construct the CSV file path
                        csv_path = os.path.join(legacy_dir, f"{table}.csv")
                        
                        if not os.path.exists(csv_path):
                            raise Exception(f"Legacy file not found: {csv_path}")
                        
                        # Read CSV file using pandas
                        df = pd.read_csv(csv_path)
                        
                        # Begin transaction for this table
                        cursor = conn.cursor()
                        
                        # Clear existing data
                        cursor.execute(f"DELETE FROM {table}")
                        
                        # Get column names from the table
                        cursor.execute(f"PRAGMA table_info({table})")
                        db_columns = [info[1] for info in cursor.fetchall()]
                        
                        # Filter DataFrame to only include columns that exist in the database
                        df = df[[col for col in df.columns if col in db_columns]]
                        
                        # Insert new data
                        placeholders = ",".join(["?" for _ in df.columns])
                        insert_query = f"INSERT INTO {table} ({','.join(df.columns)}) VALUES ({placeholders})"
                        
                        # Convert DataFrame to list of tuples for insertion
                        data = [tuple(x) for x in df.values]
                        cursor.executemany(insert_query, data)
                        
                        # Update status
                        self.status_label.setText(f"Loaded {len(data)} records into {table}...")
                        QApplication.processEvents()
                
                # Mark database as modified
                self.db_manager.mark_as_modified()
                
                # Refresh current table view if it's one of the updated tables
                current_table = self.table_combo.currentText()
                if current_table in legacy_tables:
                    self.on_table_changed(current_table)
                
                # Show success message
                self.status_label.setText("Legacy tables loaded successfully!")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Set a timer to restore the original status message
                QTimer.singleShot(3000, lambda: self.status_label.setText(original_status))
                QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("font-style: italic; color: #555555;"))
                
                QMessageBox.information(self, "Success", "Legacy tables loaded successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading legacy tables: {str(e)}")
                self.status_label.setText("Error loading legacy tables")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")