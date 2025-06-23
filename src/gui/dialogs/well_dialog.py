from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                           QLineEdit, QDoubleSpinBox, QPushButton,
                           QDialogButtonBox, QMessageBox, QFileDialog,
                           QHBoxLayout, QLabel, QComboBox, QTextEdit)
from PyQt5.QtCore import Qt
from pathlib import Path
import sqlite3
import logging

logger = logging.getLogger(__name__)

class WellDialog(QDialog):
    def __init__(self, well_model, well_data=None, parent=None):
        super().__init__(parent)
        self.well_model = well_model
        self.well_data = well_data
        self.delete_btn = None  # Add this line
        self.setup_ui()
        if well_data:
            self.load_well_data()
            # Update delete button state after loading data
            if self.delete_btn:
                has_data = self.check_well_has_data()
                self.delete_btn.setEnabled(has_data)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Well Details")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Well Number
        self.well_number = QLineEdit()
        form.addRow("Well Number:", self.well_number)
        
        # CAE Number
        self.cae_number = QLineEdit()
        form.addRow("CAE Number:", self.cae_number)
        
        # Coordinates
        self.latitude = QDoubleSpinBox()
        self.latitude.setRange(-90, 90)
        self.latitude.setDecimals(6)
        form.addRow("Latitude:", self.latitude)
        
        self.longitude = QDoubleSpinBox()
        self.longitude.setRange(-180, 180)
        self.longitude.setDecimals(6)
        form.addRow("Longitude:", self.longitude)
        
        # Top of Casing
        self.toc = QDoubleSpinBox()
        self.toc.setRange(0, 10000)
        self.toc.setDecimals(2)
        form.addRow("Top of Casing (ft):", self.toc)
        
        # Aquifer
        self.aquifer = QLineEdit()
        form.addRow("Aquifer:", self.aquifer)
        
        # Well Field
        self.well_field = QLineEdit()
        form.addRow("Well Field:", self.well_field)
        
        # County
        self.county = QLineEdit()
        form.addRow("County:", self.county)

        # Data Source Type
        self.data_source = QComboBox()
        self.data_source.addItems(['transducer', 'telemetry'])
        self.data_source.currentTextChanged.connect(self.on_data_source_changed)
        form.addRow("Data Source:", self.data_source)

        # URL (for telemetry)
        self.url = QLineEdit()
        self.url.setEnabled(False)  # Initially disabled
        form.addRow("Telemetry URL:", self.url)
        
        # Add new fields for site logistics
        # Parking Instructions
        self.parking_instructions = QTextEdit()
        self.parking_instructions.setMaximumHeight(60)
        form.addRow("Parking Instructions:", self.parking_instructions)
        
        # Access Requirements
        self.access_requirements = QTextEdit()
        self.access_requirements.setMaximumHeight(60)
        form.addRow("Access Requirements:", self.access_requirements)
        
        # Safety Notes
        self.safety_notes = QTextEdit()
        self.safety_notes.setMaximumHeight(60)
        form.addRow("Safety Notes:", self.safety_notes)
        
        # Special Instructions
        self.special_instructions = QTextEdit()
        self.special_instructions.setMaximumHeight(60)
        form.addRow("Special Instructions:", self.special_instructions)
        
        # Picture
        picture_layout = QHBoxLayout()
        self.picture_path = QLineEdit()
        self.picture_path.setReadOnly(True)
        picture_btn = QPushButton("Browse...")
        picture_btn.clicked.connect(self.browse_picture)
        picture_layout.addWidget(self.picture_path)
        picture_layout.addWidget(picture_btn)
        form.addRow("Picture:", picture_layout)
        
        layout.addLayout(form)
        
        # Add data summary and delete button when editing existing well
        if self.well_data:
            # Add data summary label
            self.data_summary_label = QLabel()
            self.data_summary_label.setWordWrap(True)
            self.data_summary_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(self.data_summary_label)
            
            self.delete_btn = QPushButton("Delete Transducer Data")  # Changed button text
            self.delete_btn.clicked.connect(self.delete_well_data)
            self.delete_btn.setEnabled(False)
            layout.addWidget(self.delete_btn)
            
            # Update data summary immediately
            self.update_data_summary()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Disable well number if editing
        if self.well_data:
            self.well_number.setEnabled(False)
    
    def on_data_source_changed(self, source: str):
        """Handle data source selection change"""
        self.url.setEnabled(source == 'telemetry')
        if source == 'transducer':
            self.url.clear()

    def load_well_data(self):
        """Load existing well data into form"""
        logger.debug("Loading well data")
        self.well_number.setText(self.well_data['well_number'])
        self.cae_number.setText(self.well_data.get('cae_number', ''))
        self.latitude.setValue(float(self.well_data['latitude']))
        self.longitude.setValue(float(self.well_data['longitude']))
        self.toc.setValue(float(self.well_data['top_of_casing']))
        self.aquifer.setText(self.well_data['aquifer'])
        self.well_field.setText(self.well_data.get('well_field', ''))
        self.county.setText(self.well_data.get('county', ''))
        self.picture_path.setText(self.well_data.get('picture_path', ''))
        
        # Set data source and URL if available
        data_source = self.well_data.get('data_source', 'transducer')
        self.data_source.setCurrentText(data_source)
        if data_source == 'telemetry':
            self.url.setText(self.well_data.get('url', ''))
            self.url.setEnabled(True)
            
        # Load new field values
        self.parking_instructions.setText(self.well_data.get('parking_instructions', ''))
        self.access_requirements.setText(self.well_data.get('access_requirements', ''))
        self.safety_notes.setText(self.well_data.get('safety_notes', ''))
        self.special_instructions.setText(self.well_data.get('special_instructions', ''))
        
        # Update data summary after loading
        self.update_data_summary()
        logger.debug("Finished loading well data")
    
    def get_data(self) -> dict:
        """Get form data as dictionary"""
        data = {
            'well_number': self.well_number.text(),
            'cae_number': self.cae_number.text(),
            'latitude': self.latitude.value(),
            'longitude': self.longitude.value(),
            'top_of_casing': self.toc.value(),
            'aquifer': self.aquifer.text(),
            'well_field': self.well_field.text(),
            'county': self.county.text(),
            'picture_path': self.picture_path.text(),
            'data_source': self.data_source.currentText(),
            'parking_instructions': self.parking_instructions.toPlainText(),
            'access_requirements': self.access_requirements.toPlainText(),
            'safety_notes': self.safety_notes.toPlainText(),
            'special_instructions': self.special_instructions.toPlainText()
        }
        
        # Only include URL if data source is telemetry
        if self.data_source.currentText() == 'telemetry':
            data['url'] = self.url.text()
            
        return data
    
    def validate(self) -> bool:
        """Validate form data"""
        if not self.well_number.text():
            QMessageBox.warning(self, "Validation Error", "Well number is required")
            return False
            
        if not self.aquifer.text():
            QMessageBox.warning(self, "Validation Error", "Aquifer is required")
            return False
            
        # Validate URL if data source is telemetry
        if self.data_source.currentText() == 'telemetry' and not self.url.text():
            QMessageBox.warning(self, "Validation Error", "URL is required for telemetry data source")
            return False
            
        return True
    
    def browse_picture(self):
        """Open file dialog to select well picture"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Well Picture",
            "",
            "Image Files (*.jpg *.jpeg *.png)"
        )
        
        if file_path:
            self.picture_path.setText(file_path)
    
    def accept(self):
        """Handle dialog acceptance"""
        if not self.validate():
            return
            
        data = self.get_data()
        
        try:
            if self.well_data:
                # Update existing well
                success, message = self.well_model.update_well(
                    self.well_data['well_number'], 
                    data
                )
            else:
                # Add new well
                success, message = self.well_model.add_well(data)
                
            if success:
                super().accept()
            else:
                QMessageBox.critical(self, "Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def check_well_has_data(self) -> bool:
        """Check if well has any transducer data"""
        if not self.well_data:
            logger.debug("No well data provided")
            return False
            
        try:
            well_number = self.well_data['well_number']
            logger.debug(f"Checking transducer data for well {well_number}")
            
            with sqlite3.connect(self.well_model.db_path) as conn:
                cursor = conn.cursor()
                
                # Log current tables and schema
                logger.debug("Checking database schema before executing query")
                try:
                    cursor.execute("PRAGMA table_list")
                    tables = cursor.fetchall()
                    logger.debug(f"Available tables: {[table[1] for table in tables]}")
                except Exception as schema_error:
                    logger.error(f"Error listing tables: {schema_error}")
                    # Try an alternative approach
                    try:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        logger.debug(f"Available tables (alt method): {[table[0] for table in tables]}")
                    except Exception as alt_error:
                        logger.error(f"Alternative table listing also failed: {alt_error}")
                
                # Check water_level_readings table schema
                try:
                    cursor.execute("PRAGMA table_info(water_level_readings)")
                    columns = cursor.fetchall()
                    logger.debug(f"water_level_readings columns: {[col[1] for col in columns]}")
                except Exception as table_error:
                    logger.error(f"Error checking water_level_readings schema: {table_error}")
                
                # Now perform the actual data check with plenty of logging
                logger.debug(f"Executing count query for well {well_number}")
                try:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM water_level_readings
                        WHERE well_number = ?
                    """, (well_number,))
                    transducer_count = cursor.fetchone()[0]
                    logger.debug(f"Transducer readings count: {transducer_count}")
                    
                    has_data = transducer_count > 0
                    logger.debug(f"Well has transducer data: {has_data}")
                    return has_data
                except Exception as query_error:
                    logger.error(f"Error executing count query: {query_error}")
                    if "no such column" in str(query_error).lower():
                        missing_col = str(query_error).split("no such column:")[-1].strip()
                        logger.error(f"Query failed due to missing column: '{missing_col}'")
                    return False
                
        except Exception as e:
            logger.error(f"Error checking well data: {e}", exc_info=True)
            return False

    def update_data_summary(self):
        """Update the data summary label with date ranges"""
        try:
            well_number = self.well_data['well_number']
            logger.debug(f"Updating data summary for well {well_number}")
            
            with sqlite3.connect(self.well_model.db_path) as conn:
                cursor = conn.cursor()
                
                # Log table structures to identify missing columns
                logger.debug("Checking tables structure for potential issues")
                for table in ['wells', 'water_level_readings', 'manual_level_readings']:
                    try:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = cursor.fetchall()
                        logger.debug(f"Table {table} columns: {[col[1] for col in columns]}")
                    except Exception as schema_error:
                        logger.error(f"Error examining schema for table {table}: {schema_error}")
                
                # Get manual readings range
                logger.debug("Getting manual readings information")
                try:
                    cursor.execute("""
                        SELECT MIN(measurement_date_utc), MAX(measurement_date_utc), COUNT(*)
                        FROM manual_level_readings 
                        WHERE well_number = ?
                    """, (well_number,))
                    manual_min, manual_max, manual_count = cursor.fetchone()
                    logger.debug(f"Manual readings: {manual_count} records, range: {manual_min} to {manual_max}")
                except Exception as manual_error:
                    logger.error(f"Error getting manual readings info: {manual_error}")
                    manual_min, manual_max, manual_count = None, None, 0
                
                # Get transducer readings range
                logger.debug("Getting transducer readings information")
                try:
                    cursor.execute("""
                        SELECT MIN(timestamp_utc), MAX(timestamp_utc), COUNT(*)
                        FROM water_level_readings
                        WHERE well_number = ?
                    """, (well_number,))
                    trans_min, trans_max, trans_count = cursor.fetchone()
                    logger.debug(f"Transducer readings: {trans_count} records, range: {trans_min} to {trans_max}")
                except Exception as trans_error:
                    logger.error(f"Error getting transducer readings info: {trans_error}")
                    trans_min, trans_max, trans_count = None, None, 0
                
                # Also check well's metadata for any flags
                logger.debug("Checking well metadata")
                try:
                    cursor.execute("""
                        SELECT baro_status, level_status
                        FROM wells
                        WHERE well_number = ?
                    """, (well_number,))
                    result = cursor.fetchone()
                    if result:
                        baro_status, level_status = result
                        logger.debug(f"Well flags: baro_status={baro_status}, level_status={level_status}")
                except Exception as meta_error:
                    logger.error(f"Error getting well metadata: {meta_error}")
                
                summary_text = []
                if manual_count > 0:
                    summary_text.append(f"Manual readings: {manual_count} records\n({manual_min} to {manual_max})")
                if trans_count > 0:
                    summary_text.append(f"Transducer readings: {trans_count} records\n({trans_min} to {trans_max})")
                
                if summary_text:
                    logger.debug(f"Setting summary text with {len(summary_text)} sections")
                    self.data_summary_label.setText("\n\n".join(summary_text))
                    self.data_summary_label.show()
                    self.delete_btn.setEnabled(True)
                    logger.debug("Enabled delete button - data found")
                else:
                    logger.debug("No data found - showing empty message")
                    self.data_summary_label.setText("No data available for this well")
                    self.data_summary_label.show()
                    self.delete_btn.setEnabled(False)
                    logger.debug("Disabled delete button - no data found")
                
        except Exception as e:
            logger.error(f"Error updating data summary: {e}", exc_info=True)
            # Try to identify specifically which query might be failing
            if "no such column" in str(e).lower():
                column_name = str(e).split("no such column:")[-1].strip()
                logger.error(f"Missing column appears to be: '{column_name}'")
                
            self.data_summary_label.setText("Error checking data availability")
            self.delete_btn.setEnabled(False)

    def delete_well_data(self):
        """Delete transducer data for the well"""
        well_number = self.well_data['well_number']
        logger.info(f"Attempting to delete transducer data for well {well_number}")
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete all TRANSDUCER data for well {well_number}?\n"
            "Manual readings will be preserved.\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                logger.info(f"User confirmed deletion for well {well_number}")
                with sqlite3.connect(self.well_model.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get count before deletion for reporting
                    cursor.execute("SELECT COUNT(*) FROM water_level_readings WHERE well_number = ?", (well_number,))
                    before_count = cursor.fetchone()[0]
                    logger.info(f"Found {before_count} records to delete for well {well_number}")
                    
                    # Alternative approach that avoids potential trigger issues
                    logger.info(f"Using alternative approach to delete records for well {well_number}")
                    
                    # First check table structure to be sure
                    cursor.execute("PRAGMA table_info(water_level_readings)")
                    columns = [col[1] for col in cursor.fetchall()]
                    logger.debug(f"Water_level_readings columns: {columns}")
                    
                    # Use a simpler, more direct approach
                    logger.info("Executing simple deletion query")
                    cursor.execute("""
                        DELETE FROM water_level_readings 
                        WHERE well_number = ?
                    """, (well_number,))
                    
                    # If the above fails, try an alternative that works around potential trigger issues
                    # by selecting IDs first and then deleting by ID
                    
                    transducer_count = cursor.rowcount
                    logger.info(f"Deleted {transducer_count} records from water_level_readings")
                    
                    # Also reset the well's flag status
                    try:
                        cursor.execute("""
                            UPDATE wells 
                            SET baro_status = 'no_data', level_status = 'no_data' 
                            WHERE well_number = ?
                        """, (well_number,))
                    except Exception as flag_error:
                        logger.error(f"Failed to update well flags: {flag_error}")
                    
                    conn.commit()
                    logger.info(f"Transaction committed successfully")
                    
                    # Verify deletion
                    cursor.execute("SELECT COUNT(*) FROM water_level_readings WHERE well_number = ?", (well_number,))
                    after_count = cursor.fetchone()[0]
                    logger.info(f"After deletion: {after_count} records remain for well {well_number}")
                    
                    QMessageBox.information(
                        self,
                        "Data Deleted",
                        f"Successfully deleted {transducer_count} transducer readings"
                    )
                    
                    # Update the summary and button state
                    logger.info("Updating data summary after deletion")
                    self.update_data_summary()
                    
            except Exception as e:
                logger.error(f"Error deleting data: {str(e)}", exc_info=True)
                
                # Handle specific error
                if "no such column: data_points" in str(e):
                    # Attempt alternative approach that bypasses potential triggers
                    logger.info("Detected data_points error, trying alternative deletion approach")
                    try:
                        with sqlite3.connect(self.well_model.db_path) as conn:
                            # Use a direct, simple approach with minimal SQL syntax
                            conn.execute("DELETE FROM water_level_readings WHERE well_number = ?", (well_number,))
                            deleted_count = conn.total_changes
                            conn.commit()
                            
                            logger.info(f"Alternative deletion succeeded, removed {deleted_count} records")
                            
                            QMessageBox.information(
                                self,
                                "Data Deleted",
                                f"Successfully deleted {deleted_count} transducer readings"
                            )
                            
                            # Update the summary and button state
                            self.update_data_summary()
                            return
                    except Exception as alt_error:
                        logger.error(f"Alternative deletion also failed: {alt_error}")
                        # Continue to the error message below
                
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete data: {str(e)}"
                )