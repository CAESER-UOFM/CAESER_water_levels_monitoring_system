import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd 
import json
logger = logging.getLogger(__name__)
import pytz
from src.gui.utils.time_utils import _get_dst_dates
from datetime import datetime, timedelta
import time
from typing import Optional, Union
from .base_model import BaseModel

class BarologgerModel(BaseModel):
    """Handles barologger-related database operations"""
    
    def __init__(self, db_path: Optional[Path] = None):
        super().__init__(db_path)
        self.utc_tz = pytz.UTC


    def add_barologger(self, data: Dict) -> Tuple[bool, str]:
        """Add a new barologger"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add to barologgers table
                cursor.execute('''
                    INSERT INTO barologgers (
                        serial_number, location_description,
                        installation_date, status, notes
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    data['serial_number'],
                    data['location_description'],
                    data['installation_date'],
                    data['status'],
                    data.get('notes', '')
                ))
                
                # Add initial location history entry
                cursor.execute('''
                    INSERT INTO barologger_locations (
                        serial_number, location_description,
                        start_date, notes
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    data['serial_number'],
                    data['location_description'],
                    data['installation_date'],
                    data.get('notes', '')
                ))
                
                conn.commit()
                
                # Mark the database as modified
                self.mark_modified()
                
                return True, f"Barologger {data['serial_number']} added successfully"
                
        except Exception as e:
            logger.error(f"Error adding barologger: {e}")
            return False, str(e)
            
    def delete_barologger(self, serial_number: str) -> Tuple[bool, str]:
        """Delete a barologger"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete from barologgers table
                cursor.execute("DELETE FROM barologgers WHERE serial_number = ?", (serial_number,))
                
                # Delete from barologger_locations table
                cursor.execute("DELETE FROM barologger_locations WHERE serial_number = ?", (serial_number,))
                
                # Delete from barometric_readings table
                cursor.execute("DELETE FROM barometric_readings WHERE serial_number = ?", (serial_number,))
                
                conn.commit()
                
                # Mark the database as modified
                self.mark_modified()
                
                return True, f"Barologger {serial_number} deleted successfully"
                
        except Exception as e:
            logger.error(f"Error deleting barologger: {e}")
            return False, str(e)
            
    def import_readings(self, df: pd.DataFrame, serial_number: str, overwrite: bool = False) -> bool:
        """Import barologger readings"""
        try:
            if df.empty:
                logger.warning(f"Empty dataframe provided for barologger {serial_number}")
                return False
                
            # Prepare data for insertion
            records = []
            for _, row in df.iterrows():
                # Calculate Julian timestamp
                timestamp = pd.to_datetime(row['timestamp_utc'])
                julian_timestamp = timestamp.to_julian_date()
                
                records.append((
                    serial_number,
                    timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    julian_timestamp,
                    float(row['pressure']),
                    float(row['temperature']),
                    row.get('quality_flag', 0),
                    row.get('notes', '')
                ))
                
            # Insert data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if overwrite:
                    # Delete existing data for this barologger and time range
                    min_date = df['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M:%S')
                    max_date = df['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute("""
                        DELETE FROM barometric_readings 
                        WHERE serial_number = ? AND timestamp_utc BETWEEN ? AND ?
                    """, (serial_number, min_date, max_date))
                    
                # Insert new data
                cursor.executemany("""
                    INSERT INTO barometric_readings (
                        serial_number, timestamp_utc, julian_timestamp, pressure, 
                        temperature, quality_flag, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, records)
                
                conn.commit()
                
                # Mark the database as modified
                self.mark_modified()
                
                logger.info(f"Imported {len(records)} readings for barologger {serial_number}")
                return True
                
        except Exception as e:
            logger.error(f"Error importing barologger readings: {e}")
            return False

        
    def create_master_baro(self, start_date: str, end_date: str, 
                          serial_numbers: List[str], min_readings: int = 2,
                          overwrite: bool = False, notes: str = "") -> Tuple[bool, str]:
        """Create master baro readings from selected barologgers in UTC"""
        try:
            readings_data = [self.get_readings(serial, start_date, end_date) for serial in serial_numbers]
            readings_data = [df for df in readings_data if not df.empty]

            if not readings_data:
                return False, "No data found for selected barologgers"

            processed_data = self._process_master_baro_data(readings_data, min_readings)
            if processed_data.empty:
                return False, "No valid data after processing"

            return self._save_master_baro_data(processed_data, serial_numbers, notes)
        except Exception as e:
            logger.error(f"Error creating master baro: {e}")
            return False, str(e)
    
    def _process_master_baro_data(self, readings_data: List[pd.DataFrame], min_readings: int = 2) -> pd.DataFrame:
        """
        Process and combine readings from multiple barologgers.
        Optimized version that assumes data is already in the correct format.
        """
        try:
            logger.debug(f"Starting _process_master_baro_data with {len(readings_data)} dataframes")
            if not readings_data:
                logger.warning("No readings data provided")
                return pd.DataFrame()

            # Process each dataframe to ensure consistent format
            processed_dfs = []
            for i, df in enumerate(readings_data):
                if df.empty:
                    logger.debug(f"Skipping empty dataframe {i}")
                    continue
                    
                logger.debug(f"Processing dataframe {i} with {len(df)} rows")
                
                # Set timestamp as index for resampling
                df = df.set_index('timestamp_utc')
                
                # Resample to 15-minute intervals using mean
                resampled = df.resample('15min').mean()
                logger.debug(f"After resampling df {i}: {len(resampled)} rows")
                
                processed_dfs.append(resampled)

            if not processed_dfs:
                logger.warning("No dataframes after processing")
                return pd.DataFrame()

            # Combine all data efficiently
            combined = pd.concat(processed_dfs, axis=1, keys=range(len(processed_dfs)))
            logger.debug(f"Combined data shape: {combined.shape}")

            # Calculate statistics across barologgers
            result = pd.DataFrame(index=combined.index)
            
            # Group pressure columns and calculate statistics efficiently
            pressure_cols = [col for col in combined.columns if col[1] == 'pressure']
            logger.debug(f"Found {len(pressure_cols)} pressure columns")
            
            if pressure_cols:
                pressures = combined[pressure_cols]
                # Calculate all statistics at once
                result['pressure_count'] = pressures.count(axis=1)
                result['pressure_mean'] = pressures.mean(axis=1)
                result['pressure_std'] = pressures.std(axis=1)
                result['pressure_min'] = pressures.min(axis=1)
                result['pressure_max'] = pressures.max(axis=1)
                logger.debug(f"After pressure calculations: {len(result)} rows")

            # Group temperature columns and calculate statistics
            temp_cols = [col for col in combined.columns if col[1] == 'temperature']
            if temp_cols:
                temps = combined[temp_cols]
                # Calculate all statistics at once
                result['temp_count'] = temps.count(axis=1)
                result['temp_mean'] = temps.mean(axis=1)
                result['temp_std'] = temps.std(axis=1)
                result['temp_min'] = temps.min(axis=1)
                result['temp_max'] = temps.max(axis=1)

            # Filter by minimum readings requirement
            result = result[result['pressure_count'] >= min_readings].copy()
            logger.debug(f"After min_readings filter ({min_readings}): {len(result)} rows")
            
            if result.empty:
                logger.warning(f"No data points with {min_readings} or more readings")
                return pd.DataFrame()

            # Reset index to get timestamp as column
            result = result.reset_index()
            
            # Add quality flags efficiently
            result['quality_flag'] = 'AUTO'
            variation_threshold = 0.1  # PSI
            
            # Calculate flags in one pass
            flag_conditions = (
                (result['pressure_std'] > variation_threshold) |
                ((result['pressure_max'] - result['pressure_min']) > 2 * variation_threshold)
            )
            result.loc[flag_conditions, 'quality_flag'] = 'CHECK'

            # Round numeric values efficiently
            numeric_cols = result.select_dtypes(include=['float64']).columns
            result[numeric_cols] = result[numeric_cols].round(3)

            # Add metadata
            result['processing_date'] = pd.Timestamp.now()
            result['calculation_method'] = f'Average of {min_readings}+ readings (15-min intervals)'

            logger.debug(f"Final result: {len(result)} rows")
            return result
            
        except Exception as e:
            logger.error(f"Error in _process_master_baro_data: {str(e)}", exc_info=True)
            return pd.DataFrame()


    def _save_master_baro_data(self, data: pd.DataFrame, 
                             source_barologgers: List[str],
                             notes: str,
                             overwrite: bool = False) -> Tuple[bool, str]:
        """Save processed Master Baro data to the database using batch processing."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                sources_json = json.dumps(source_barologgers)
    
                # If overwrite is enabled, delete overlapping timestamps
                if overwrite:
                    min_time = data['timestamp_utc'].min()
                    max_time = data['timestamp_utc'].max()
                    cursor.execute("""
                        DELETE FROM master_baro_readings
                        WHERE timestamp_utc BETWEEN ? AND ?
                    """, (min_time.strftime('%Y-%m-%d %H:%M:%S'), 
                          max_time.strftime('%Y-%m-%d %H:%M:%S')))
    
                # Prepare batch insert data
                insert_data = []
                for _, row in data.iterrows():
                    timestamp = pd.to_datetime(row['timestamp_utc'])
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    julian_timestamp = timestamp.to_julian_date()
                    
                    insert_data.append((
                        timestamp_str,
                        julian_timestamp,
                        row['pressure_mean'],
                        row['temp_mean'] if 'temp_mean' in row.index else None,
                        sources_json,
                        notes
                    ))
    
                # Batch insert
                cursor.executemany("""
                    INSERT INTO master_baro_readings (
                        timestamp_utc, julian_timestamp, pressure, temperature,
                        source_barologgers, notes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, insert_data)
    
                conn.commit()
                return True, f"Successfully created master baro from {len(source_barologgers)} barologgers"
    
        except Exception as e:
            logger.error(f"Error saving master baro data: {e}")
            return False, str(e)



    
    def get_master_baro_data(self, start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
        """
        Retrieve master baro data with enhanced segment handling.
        
        Args:
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            
        Returns:
            DataFrame with master baro data including segment information.
        """
        start_time = time.time()
        logger.debug(f"Starting get_master_baro_data() for {self.db_path}")
        
        if not self.db_path:
            logger.debug("No database path set, returning empty DataFrame")
            return pd.DataFrame()
    
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Apply performance optimizations
                conn.execute("PRAGMA temp_store = MEMORY")
                conn.execute("PRAGMA cache_size = 10000")
                
                # Build query parameters
                params = []
                query = """
                    SELECT timestamp_utc, pressure, temperature,
                    FROM master_baro_readings
                """

                if start_date and end_date:
                    query += " AND timestamp_utc BETWEEN ? AND ?"
                    params.extend([
                        start_date.strftime('%Y-%m-%d %H:%M:%S'),
                        end_date.strftime('%Y-%m-%d %H:%M:%S')
                    ])
    
                query += " ORDER BY julian_timestamp "
                
                # Execute query
                query_start = time.time()
                df = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp_utc'])
                query_end = time.time()
                
                # Log detailed timing but only for large result sets
                if len(df) > 10000:
                    logger.info(f"Master baro query returned {len(df)} rows in {(query_end - query_start)*1000:.2f}ms")
                
                # Return the dataframe
                end_time = time.time()
                logger.debug(f"Completed get_master_baro_data in {(end_time - start_time)*1000:.2f}ms")
                return df
                
        except Exception as e:
            logger.error(f"Error retrieving master baro data: {e}")
            return pd.DataFrame()

    
    def get_readings(self, serial_number: str, start_date: Optional[Union[str, datetime]] = None, 
                     end_date: Optional[Union[str, datetime]] = None) -> pd.DataFrame:
        """Retrieve barologger readings, ensuring timestamps are in datetime format."""
        try:
            # Convert string dates to datetime if needed
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
    
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT timestamp_utc, pressure, temperature
                    FROM barometric_readings
                    WHERE serial_number = ?
                """
                params = [serial_number]
    
                if start_date and end_date:
                    query += " AND timestamp_utc BETWEEN ? AND ?"
                    params.extend([
                        start_date.strftime('%Y-%m-%d %H:%M:%S'),
                        end_date.strftime('%Y-%m-%d %H:%M:%S')
                    ])
    
                query += " ORDER BY julian_timestamp "
    
                # Fetch data
                df = pd.read_sql_query(query, conn, params=params)
                if df.empty:
                    return df
    
                # Convert timestamp_utc from string to datetime
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    
                return df
    
        except Exception as e:
            logger.error(f"Error getting readings for {serial_number}: {e}")
            return pd.DataFrame()

    def get_all_barologgers(self, log_count=True) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        serial_number,
                        location_description,
                        installation_date,
                        status,
                        notes
                    FROM barologgers
                    ORDER BY serial_number
                ''')
                
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Only log if requested (to avoid duplicate logs)
                if log_count:
                    logger.debug(f"Retrieved {len(result)} barologgers")
                    
                return result
                
        except Exception as e:
            logger.error(f"Error retrieving barologgers: {e}")
            return []

    def get_barologger(self, serial_number: str) -> Dict:
        """Fetch details for a single barologger"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        serial_number,
                        location_description,
                        installation_date,
                        status,
                        notes
                    FROM barologgers
                    WHERE serial_number = ?
                ''', (serial_number,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'serial_number': row[0],
                        'location_description': row[1],
                        'installation_date': row[2],
                        'status': row[3],
                        'notes': row[4]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving barologger {serial_number}: {e}")
            return None

    def update_barologger(self, data: Dict) -> Tuple[bool, str]:
        """Update an existing barologger's metadata"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE barologgers 
                    SET location_description = ?,
                        installation_date = ?,
                        status = ?,
                        notes = ?
                    WHERE serial_number = ?
                ''', (
                    data['location_description'],
                    data['installation_date'],
                    data['status'],
                    data.get('notes', ''),
                    data['serial_number']
                ))
                
                if cursor.rowcount == 0:
                    return False, "Barologger not found"
                
                conn.commit()
                return True, "Barologger updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating barologger: {e}")
            return False, str(e)

    def barologger_exists(self, serial_number: str) -> bool:
        """Check if a barologger with the given serial number exists in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM barologgers 
                    WHERE serial_number = ?
                """, (serial_number,))
                count = cursor.fetchone()[0]
                logger.debug(f"Checking if barologger {serial_number} exists: {bool(count)}")
                return count > 0
        except Exception as e:
            logger.error(f"Error checking if barologger exists: {e}")
            return False

    def batch_import_readings(self, aggregated_data: Dict[str, Dict], 
                          progress_callback: callable = None) -> Tuple[bool, str]:
        """Batch import readings for multiple barologgers"""
        try:
            total_loggers = len(aggregated_data)
            if total_loggers == 0:
                return False, "No data provided for import"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")
                
                total_readings = 0
                processed_loggers = 0
                
                try:
                    for serial_number, logger_data in aggregated_data.items():
                        if progress_callback:
                            progress_callback(
                                processed_loggers + 1, 
                                total_loggers,
                                f"Importing data for logger {serial_number} ({processed_loggers + 1}/{total_loggers})"
                            )
                            
                        df = logger_data['data']
                        overwrite = logger_data.get('overwrite', False)
                        
                        if overwrite:
                            # Delete existing readings in the time range
                            min_time = df['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M:%S')
                            max_time = df['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute("""
                                DELETE FROM barometric_readings 
                                WHERE serial_number = ? 
                                AND timestamp_utc BETWEEN ? AND ?
                            """, (serial_number, min_time, max_time))
                        
                        # Prepare data for insertion with proper type conversion
                        readings_data = []
                        for _, row in df.iterrows():
                            # Calculate Julian timestamp
                            timestamp = pd.to_datetime(row['timestamp_utc'])
                            julian_timestamp = timestamp.to_julian_date()
                            
                            readings_data.append((
                                serial_number,
                                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                julian_timestamp,
                                float(row['pressure']),
                                float(row['temperature']) if 'temperature' in row and pd.notna(row['temperature']) else None,
                                row.get('quality_flag', 0),
                                row.get('notes', '')
                            ))
                        
                        # Batch insert readings
                        cursor.executemany("""
                            INSERT INTO barometric_readings 
                            (serial_number, timestamp_utc, julian_timestamp, pressure, temperature, quality_flag, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, readings_data)
                        
                        total_readings += len(readings_data)
                        processed_loggers += 1
                        
                    if progress_callback:
                        progress_callback(total_loggers, total_loggers, "Finalizing import...")
                        
                    # Commit transaction
                    conn.commit()
                    
                    return True, f"Successfully imported {total_readings} readings for {processed_loggers} loggers"
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    logger.error(f"Error in batch import: {e}")
                    return False, f"Error during batch import: {str(e)}"
                    
        except Exception as e:
            logger.error(f"Database connection error in batch import: {e}")
            return False, f"Database connection error: {str(e)}"
