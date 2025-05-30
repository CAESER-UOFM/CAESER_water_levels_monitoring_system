# src/gui/handlers/csv_handler.py
import pandas as pd
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                           QTableWidgetItem, QPushButton, QLabel, QCheckBox,
                           QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt
from datetime import datetime
import logging
import sqlite3

logger = logging.getLogger(__name__)

class CSVPreviewDialog(QDialog):
    """Dialog for previewing and selecting wells from CSV"""
    
    def __init__(self, csv_path, db_manager, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path
        self.db_manager = db_manager
        self.required_columns = ['WN', 'LAT', 'LON', 'TOC', 'AQ']
        self.df = None
        
        # Setup UI
        self.setWindowTitle("Preview Wells from CSV")
        self.resize(800, 600)
        self.setup_ui()
        self.load_csv()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Create table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Button layout
        btn_layout = QHBoxLayout()
        
        # Select All checkbox
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.setChecked(True)
        self.select_all_cb.stateChanged.connect(self.toggle_all_selections)
        btn_layout.addWidget(self.select_all_cb)
        
        btn_layout.addStretch()
        
        # Import and Cancel buttons
        self.import_btn = QPushButton("Import Selected")
        self.import_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.import_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_csv(self):
        """Load and validate CSV data"""
        try:
            # Read CSV file
            self.df = pd.read_csv(self.csv_path)
            
            # Validate required columns
            if not self.validate_structure():
                return
            
            # Validate data types
            if not self.validate_data_types():
                return
            
            # Populate table with data
            self.populate_table()
            
            # Update status
            self.status_label.setText(f"Found {len(self.df)} wells in CSV file")
            self.status_label.setStyleSheet("color: green")
            self.import_btn.setEnabled(True)
            
        except Exception as e:
            self.show_error(f"Error reading CSV file: {str(e)}")
    
    def validate_structure(self):
        """Validate CSV has all required columns"""
        missing_cols = [col for col in self.required_columns 
                       if col not in self.df.columns]
        if missing_cols:
            self.show_error(
                f"Missing required columns: {', '.join(missing_cols)}\n"
                "Please check the CSV format requirements."
            )
            return False
        return True
    
    def validate_data_types(self):
        """Validate data types in CSV"""
        try:
            # Convert numeric columns
            numeric_cols = ['LAT', 'LON', 'TOC']
            for col in numeric_cols:
                self.df[col] = pd.to_numeric(self.df[col], errors='raise')
            
            # Check value ranges
            if (self.df['LAT'].abs() > 90).any():
                self.show_error("Invalid latitude values found (must be between -90 and 90)")
                return False
            
            if (self.df['LON'].abs() > 180).any():
                self.show_error("Invalid longitude values found (must be between -180 and 180)")
                return False
            
            # Check for duplicates
            duplicates = self.df['WN'].duplicated()
            if duplicates.any():
                dup_wells = self.df[duplicates]['WN'].tolist()
                self.show_error(
                    f"Duplicate well numbers found: {', '.join(dup_wells)}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.show_error(f"Error validating data: {str(e)}")
            return False
    
    def populate_table(self):
        """Fill table with CSV data"""
        # Set up table columns
        self.table.setRowCount(len(self.df))
        self.table.setColumnCount(len(self.df.columns) + 1)  # +1 for checkbox
        
        # Set headers
        headers = ['Select'] + list(self.df.columns)
        self.table.setHorizontalHeaderLabels(headers)
        
        # Fill data
        for row in range(len(self.df)):
            # Add checkbox
            chk = QCheckBox()
            chk.setChecked(True)
            self.table.setCellWidget(row, 0, chk)
            
            # Add data
            for col in range(len(self.df.columns)):
                item = QTableWidgetItem(str(self.df.iloc[row, col]))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make read-only
                self.table.setItem(row, col + 1, item)
        
        # Adjust column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for i in range(1, len(self.df.columns) + 1):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
    
    def toggle_all_selections(self, state):
        """Handle Select All checkbox"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
    
    def get_selected_wells(self):
        """Return data for selected wells"""
        selected_wells = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                well_data = {}
                for col in range(1, self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col).text()
                    item = self.table.item(row, col)
                    well_data[header] = item.text()
                selected_wells.append(well_data)
        return selected_wells
    
    def show_error(self, message):
        """Display error message"""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: red")
        self.import_btn.setEnabled(False)
        QMessageBox.warning(self, "Error", message)


class CSVImporter:
    """Handles CSV import operations"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        print(f"CSVImporter initialized with manager: {db_manager}")  # Debug print
    
    def import_wells(self, wells_data):
        """Import wells into database"""
        try:
            # Print debug info
            print(f"Attempting to import {len(wells_data)} wells")
            print("First well data:", wells_data[0])  # Show sample data
            
            # Use DatabaseManager to import wells
            self.db_manager.import_wells(wells_data)
            return True, f"Successfully imported {len(wells_data)} wells"
            
        except Exception as e:
            print(f"Error in CSVImporter: {e}")  # Debug print
            return False, f"Error importing wells: {str(e)}"


class ManualReadingsCSVHandler:
    """Handler for manual water level readings CSV files"""
    
    REQUIRED_COLUMNS = {
        'well_number': str,
        'dtw_1': float,
    }
    
    OPTIONAL_COLUMNS = {
        'dtw_2': float,
        'dtw_avg': float,
        'measurement_date': str,  # Expected in local time (America/Chicago)
        'comments': str,
        'collected_by': str,
        'data_source': str,
        'tape_error': float,
        'water_level': float,
        'id': str,
        'is_dry': bool,
    }
    
    @staticmethod
    def validate_and_process(file_path: str) -> pd.DataFrame:
        """
        Validate and process a CSV file containing manual readings.
        Returns cleaned DataFrame with standardized column names and data types.
        
        Expected CSV format:
        - well_number: Well identifier (required)
        - dtw_1: First depth to water measurement (required)
        - dtw_2: (optional) Second depth to water measurement
        - dtw_avg: (optional) Average depth to water 
        - measurement_date: (optional) Local time (America/Chicago) in any standard date format
        - measurement_date_utc: (optional) UTC time in any standard date format
        - comments: (optional) Any comments about the measurement
        - collected_by: (optional) Person who took the measurement
        - data_source: (optional) Source of the data
        - tape_error: (optional) Tape error measurement
        - water_level: (optional) Water level elevation
        - id: (optional) Unique identifier for the reading
        - is_dry: (optional) Boolean indicating if the well is dry
        """
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.lower().str.strip()
            
            # Handle common column name variations
            column_mapping = {
                'date': 'measurement_date',
                'datetime': 'measurement_date',
                'measured_date': 'measurement_date',
                'measure_date': 'measurement_date',
                'date_utc': 'measurement_date_utc',
                'datetime_utc': 'measurement_date_utc',
                'timestamp_utc': 'measurement_date_utc',
                'well_num': 'well_number',
                'well': 'well_number',
                'well_id': 'well_number',
                'well_name': 'well_number',
                'average': 'dtw_avg',
                'dtw': 'dtw_1',
                'depth_to_water': 'dtw_1',
                'depth': 'dtw_1',
                'depth1': 'dtw_1',
                'depth2': 'dtw_2',
                'comment': 'comments',
                'note': 'comments',
                'notes': 'comments',
                'source': 'data_source',
                'collected': 'collected_by',
                'collector': 'collected_by',
                'water_lev': 'water_level',
                'water_elevation': 'water_level',
                'elevation': 'water_level',
                'tape_err': 'tape_error',
                'dry': 'is_dry'
            }
            
            # Apply column name mappings for known variations
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
            # Check required columns
            missing_cols = [col for col in ManualReadingsCSVHandler.REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
                
            # Clean well numbers
            df['well_number'] = df['well_number'].astype(str).str.strip()
            
            # Handle date columns
            # Case 1: measurement_date_utc is present (directly use it assuming it's in UTC)
            if 'measurement_date_utc' in df.columns:
                logger.debug("Using measurement_date_utc from CSV")
                # Parse as datetime - try multiple formats for different date formats
                try:
                    # First try automatic parsing
                    df['measurement_date_utc'] = pd.to_datetime(df['measurement_date_utc'], errors='coerce')
                    
                    # Check if we have any NaT values from parsing errors
                    if df['measurement_date_utc'].isna().any():
                        logger.debug("Some date parsing errors detected, trying manual formats")
                        # Get the original strings for failed dates
                        mask = df['measurement_date_utc'].isna()
                        original_dates = df.loc[mask, 'measurement_date_utc'].astype(str)
                        
                        # Try common date formats for failed dates
                        formats = ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', 
                                  '%m/%d/%Y', '%d/%m/%Y %H:%M', '%d-%m-%Y %H:%M']
                        
                        for fmt in formats:
                            try:
                                parsed_dates = pd.to_datetime(original_dates, format=fmt, errors='coerce')
                                # Update only the previously failed dates that were successfully parsed
                                new_mask = ~parsed_dates.isna()
                                if new_mask.any():
                                    logger.debug(f"Format {fmt} matched some dates")
                                    df.loc[mask & new_mask.values, 'measurement_date_utc'] = parsed_dates[new_mask]
                            except Exception as e:
                                logger.debug(f"Format {fmt} failed: {e}")
                except Exception as e:
                    logger.error(f"Error parsing dates: {e}")
                
                # Fill NA values with current time
                na_count = df['measurement_date_utc'].isna().sum()
                if na_count > 0:
                    logger.warning(f"Found {na_count} unparseable dates - using current time")
                    df.loc[df['measurement_date_utc'].isna(), 'measurement_date_utc'] = pd.Timestamp.now(tz='UTC')
                
                # Ensure timezone is UTC
                if df['measurement_date_utc'].dt.tz is None:
                    df['measurement_date_utc'] = df['measurement_date_utc'].dt.tz_localize('UTC')
                
                # Format as string for SQL
                df['measurement_date_utc'] = df['measurement_date_utc'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Log sample of processed dates
                logger.debug(f"Processed dates sample: {df['measurement_date_utc'].head(3).tolist()}")
                
                # Also create a measurement_date in local time for display
                if 'measurement_date' not in df.columns:
                    df['measurement_date'] = pd.to_datetime(df['measurement_date_utc']).dt.tz_localize('UTC').dt.tz_convert('America/Chicago')
            
            # Case 2: measurement_date is present (convert from local to UTC)
            elif 'measurement_date' in df.columns:
                logger.debug("Converting measurement_date to UTC")
                # Parse to datetime with robust handling of different formats
                try:
                    # First try automatic parsing
                    df['measurement_date'] = pd.to_datetime(df['measurement_date'], errors='coerce')
                    
                    # Check if we have any NaT values from parsing errors
                    if df['measurement_date'].isna().any():
                        logger.debug("Some date parsing errors detected, trying manual formats")
                        # Get the original strings for failed dates
                        mask = df['measurement_date'].isna()
                        original_dates = df.loc[mask, 'measurement_date'].astype(str)
                        
                        # Try common date formats for failed dates
                        formats = ['%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', 
                                  '%m/%d/%Y', '%d/%m/%Y %H:%M', '%d-%m-%Y %H:%M']
                        
                        for fmt in formats:
                            try:
                                parsed_dates = pd.to_datetime(original_dates, format=fmt, errors='coerce')
                                # Update only the previously failed dates that were successfully parsed
                                new_mask = ~parsed_dates.isna()
                                if new_mask.any():
                                    logger.debug(f"Format {fmt} matched some dates")
                                    df.loc[mask & new_mask.values, 'measurement_date'] = parsed_dates[new_mask]
                            except Exception as e:
                                logger.debug(f"Format {fmt} failed: {e}")
                except Exception as e:
                    logger.error(f"Error parsing dates: {e}")
                
                # Fill NA values with current time
                na_count = df['measurement_date'].isna().sum()
                if na_count > 0:
                    logger.warning(f"Found {na_count} unparseable dates - using current time")
                    df.loc[df['measurement_date'].isna(), 'measurement_date'] = pd.Timestamp.now(tz='America/Chicago')
                
                # Log sample of processed dates
                logger.debug(f"Processed local dates sample: {df['measurement_date'].head(3).tolist()}")
                
                # Localize to Central Time and convert to UTC
                if df['measurement_date'].dt.tz is None:
                    df['measurement_date_utc'] = (df['measurement_date']
                        .dt.tz_localize('America/Chicago', ambiguous='infer')
                        .dt.tz_convert('UTC')
                        .dt.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    # Already has timezone, just convert to UTC
                    df['measurement_date_utc'] = df['measurement_date'].dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Case 3: No date column present (use current time)
            else:
                logger.debug("No date column found, using current time")
                now_utc = pd.Timestamp.now(tz='UTC')
                now_local = now_utc.tz_convert('America/Chicago')
                
                df['measurement_date'] = now_local
                df['measurement_date_utc'] = now_utc.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate dtw_avg from dtw_1 and dtw_2 if not provided
            if 'dtw_avg' not in df.columns:
                if 'dtw_2' in df.columns:
                    # Fill any missing dtw_2 values with dtw_1
                    df['dtw_2'] = df.get('dtw_2').fillna(df['dtw_1'])
                    df['dtw_avg'] = df[['dtw_1', 'dtw_2']].mean(axis=1)
                else:
                    df['dtw_avg'] = df['dtw_1']
                    df['dtw_2'] = df['dtw_1']
            
            # Set is_dry to 0 (False) if not provided
            if 'is_dry' not in df.columns:
                df['is_dry'] = 0
            
            # Convert boolean-like values to actual booleans
            if 'is_dry' in df.columns:
                # Convert various representations of true/false to 1/0
                df['is_dry'] = df['is_dry'].astype(str).str.lower()
                df['is_dry'] = df['is_dry'].apply(
                    lambda x: 1 if x in ['true', '1', 't', 'yes', 'y'] else 0
                )
            
            # Set placeholders for any missing optional columns
            for col, dtype in ManualReadingsCSVHandler.OPTIONAL_COLUMNS.items():
                if col not in df.columns and col not in ['measurement_date', 'measurement_date_utc']:  # already handled above
                    if dtype == bool:
                        df[col] = False
                    elif dtype == float:
                        df[col] = None
                    else:
                        df[col] = None
            
            # Calculate water_level (will be updated with actual TOC during import) if not provided
            if 'water_level' not in df.columns:
                df['water_level'] = None  # Placeholder, will be calculated during import
            
            # Debug log the processed data
            logger.debug(f"Processed {len(df)} rows from CSV with columns: {list(df.columns)}")
            logger.debug(f"Sample data: {df.head(1).to_dict('records')}")
                
            return df
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            raise

    @staticmethod
    def import_to_database(df: pd.DataFrame, db_manager, selected_wells: dict) -> tuple:
        """
        Import the validated data into the database.
        Returns (records_added, errors)
        """
        records_added = 0
        errors = []
        
        with sqlite3.connect(db_manager.current_db) as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                well = row['well_number']
                if well not in selected_wells:
                    continue
                    
                try:
                    # Handle overwrite
                    if selected_wells[well].get('overwrite', False):
                        cursor.execute('''
                            DELETE FROM manual_level_readings 
                            WHERE well_number = ? AND measurement_date_utc = ?
                        ''', (well, row['measurement_date_utc']))
                    
                    # Get well info and calculate water level if not provided
                    well_info = db_manager.well_model.get_well(well)
                    if not well_info:
                        errors.append(f"Well {well} not found in database")
                        continue
                        
                    toc = well_info['top_of_casing']
                    
                    # Use provided values or calculate them
                    dtw1 = float(row['dtw_1']) if pd.notna(row['dtw_1']) else None
                    dtw2 = float(row['dtw_2']) if 'dtw_2' in row and pd.notna(row['dtw_2']) else dtw1
                    
                    # Use provided dtw_avg or calculate it
                    if 'dtw_avg' in row and pd.notna(row['dtw_avg']):
                        dtw_avg = float(row['dtw_avg'])
                    elif dtw1 is not None:
                        dtw_avg = (dtw1 + (dtw2 or dtw1)) / 2
                    else:
                        dtw_avg = None
                    
                    # Use provided water_level or calculate it from TOC - dtw_avg
                    if 'water_level' in row and pd.notna(row['water_level']):
                        water_level = float(row['water_level'])
                    elif dtw_avg is not None and toc is not None:
                        water_level = float(toc) - dtw_avg
                    else:
                        water_level = None
                    
                    # Get tape error value if provided
                    tape_error = float(row['tape_error']) if 'tape_error' in row and pd.notna(row['tape_error']) else None
                    
                    # Get is_dry flag
                    is_dry = bool(row['is_dry']) if 'is_dry' in row else False
                    
                    # Use INSERT OR REPLACE to handle duplicate entries with the same well_number and measurement_date_utc
                    cursor.execute('''
                        INSERT OR REPLACE INTO manual_level_readings 
                        (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2, 
                         tape_error, comments, water_level, data_source, collected_by, is_dry)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        well,
                        row['measurement_date_utc'],
                        dtw_avg,
                        dtw1,
                        dtw2,
                        tape_error,
                        row.get('comments', ''),
                        water_level,
                        row.get('data_source', 'MANUAL'),
                        row.get('collected_by', 'UNKNOWN'),
                        1 if is_dry else 0
                    ))
                    records_added += 1
                    
                except Exception as e:
                    errors.append(f"Error processing well {well}: {str(e)}")
            
            conn.commit()
        
        return records_added, errors