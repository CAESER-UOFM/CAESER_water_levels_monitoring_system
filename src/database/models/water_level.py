# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 10:42:57 2025

@author: bledesma
"""


import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import  Dict, Optional, Tuple
from src.gui.utils.time_utils import _get_dst_dates
from .well import WellModel  # Import from the correct module
from .base_model import BaseModel

logger = logging.getLogger(__name__)

class WaterLevelModel(BaseModel):
    def __init__(self, db_path: Path):
        """Initialize with database path"""
        super().__init__(db_path)
        self.well_model = WellModel(db_path)  # Add this line
        # Schema migration: ensure wells table has baro_status and level_status columns
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(wells)")
                cols = [row[1] for row in cursor.fetchall()]
                altered = False
                if 'baro_status' not in cols:
                    cursor.execute(
                        "ALTER TABLE wells ADD COLUMN baro_status TEXT CHECK(baro_status IN ('no_data','all_master','has_non_master')) DEFAULT 'no_data'"
                    )
                    altered = True
                if 'level_status' not in cols:
                    cursor.execute(
                        "ALTER TABLE wells ADD COLUMN level_status TEXT CHECK(level_status IN ('no_data','default_level','no_default')) DEFAULT 'no_data'"
                    )
                    altered = True
                if altered:
                    conn.commit()
        except Exception:
            pass
        # Comment out the flag recalculation that happens on initialization
        # This was causing performance issues when opening databases
        """
        # Populate flag summaries for all wells on startup
        try:
            flags = self.check_all_wells_flags()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for wn, status in flags.items():
                    cursor.execute(
                        "UPDATE wells SET baro_status = ?, level_status = ? WHERE well_number = ?",
                        (status.get('baro_status', 'no_data'), status.get('level_status', 'no_data'), wn)
                    )
                conn.commit()
        except Exception:
            pass
        """

    def get_readings(self, well_number: str, start_date: datetime = None, 
                    end_date: datetime = None) -> pd.DataFrame:
        """Get readings for a specific well, handling both transducer and telemetry sources"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First check the well's data_source
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data_source FROM wells 
                    WHERE well_number = ?
                """, (well_number,))
                
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Well {well_number} not found in database")
                    return pd.DataFrame()
                    
                data_source = result[0]
                logger.debug(f"Well {well_number} has data_source: {data_source}")
                
                # Initialize empty DataFrame for results
                df = pd.DataFrame()
                
                # Fetch from transducer readings table
                if data_source == 'transducer' or not data_source:
                    df = self._get_transducer_readings(well_number, start_date, end_date, conn)
                
                # Fetch from telemetry readings table
                elif data_source == 'telemetry':
                    df = self._get_telemetry_readings(well_number, start_date, end_date, conn)
                
                # Convert timestamps to datetime if we have data
                if not df.empty:
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                return df
                    
        except Exception as e:
            logger.error(f"Error getting readings for {well_number}: {e}")
            return pd.DataFrame()

    def _get_transducer_readings(self, well_number: str, start_date: datetime = None, 
                               end_date: datetime = None, conn = None) -> pd.DataFrame:
        """Get readings from the transducer readings table"""
        try:
            # If no connection was provided, create one
            close_conn = False
            if conn is None:
                conn = sqlite3.connect(self.db_path)
                close_conn = True
                
            # First check if there's any data
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM water_level_readings 
                WHERE well_number = ?
            """, (well_number,))
            
            count = cursor.fetchone()[0]
            if count == 0:
                return pd.DataFrame()
                
            # If we have data, proceed with retrieval
            query = """
                SELECT timestamp_utc,
                       pressure,
                       water_level,
                       temperature,
                       baro_flag,
                       level_flag
                FROM water_level_readings
                WHERE well_number = ?
            """
            params = [well_number]
            
            # Handle date range
            if start_date and end_date:
                if isinstance(start_date, str):
                    start_date = pd.to_datetime(start_date)
                if isinstance(end_date, str):
                    end_date = pd.to_datetime(end_date)
                    
                query += " AND timestamp_utc BETWEEN ? AND ?"
                params.extend([
                    start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    end_date.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            query += " ORDER BY julian_timestamp"
            
            # Execute query
            df = pd.read_sql_query(query, conn, params=params)
            
            # Close connection if we created it
            if close_conn:
                conn.close()
                
            return df
                
        except Exception as e:
            logger.error(f"Error getting transducer readings for {well_number}: {e}")
            return pd.DataFrame()

    def _get_telemetry_readings(self, well_number: str, start_date: datetime = None, 
                              end_date: datetime = None, conn = None) -> pd.DataFrame:
        """Get readings from the telemetry readings table"""
        try:
            # If no connection was provided, create one
            close_conn = False
            if conn is None:
                conn = sqlite3.connect(self.db_path)
                close_conn = True
                
            # First check if there's any data
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM telemetry_level_readings 
                WHERE well_number = ?
            """, (well_number,))
            
            count = cursor.fetchone()[0]
            if count == 0:
                return pd.DataFrame()
                
            # If we have data, proceed with retrieval
            query = """
                SELECT timestamp_utc,
                       water_level,
                       temperature,
                       dtw
                FROM telemetry_level_readings
                WHERE well_number = ?
            """
            params = [well_number]
            
            # Handle date range
            if start_date and end_date:
                if isinstance(start_date, str):
                    start_date = pd.to_datetime(start_date)
                if isinstance(end_date, str):
                    end_date = pd.to_datetime(end_date)
                    
                query += " AND timestamp_utc BETWEEN ? AND ?"
                params.extend([
                    start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    end_date.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            query += " ORDER BY julian_timestamp"
            
            # Execute query
            df = pd.read_sql_query(query, conn, params=params)
            
            # Add missing columns to match transducer readings format
            if not df.empty:
                # Add pressure column (derived from dtw if available)
                if 'dtw' in df.columns:
                    # Use a dummy pressure value based on dtw
                    df['pressure'] = df['dtw'] * 0.43  # Approximate PSI per foot
                else:
                    df['pressure'] = None
                    
                # Add standard flags
                df['baro_flag'] = 'standard'
                df['level_flag'] = 'telemetry'
            
            # Close connection if we created it
            if close_conn:
                conn.close()
                
            return df
                
        except Exception as e:
            logger.error(f"Error getting telemetry readings for {well_number}: {e}")
            return pd.DataFrame()

    def import_readings(self, well_number: str, readings_df: pd.DataFrame, 
                      overwrite: bool = False) -> bool:
        """Import or update water level readings for a well"""
        if readings_df.empty:
            logger.warning(f"No readings to import for well {well_number}")
            return False
        
        try:
            # Ensure all required columns exist
            required_columns = ['timestamp_utc', 'pressure']
            for col in required_columns:
                if col not in readings_df.columns:
                    logger.error(f"Required column {col} missing from readings data")
                    return False
                
            # Convert timestamps if they're not already
            if not pd.api.types.is_datetime64_any_dtype(readings_df['timestamp_utc']):
                readings_df['timestamp_utc'] = pd.to_datetime(readings_df['timestamp_utc'])
            
            # Store time range for message
            min_date = readings_df['timestamp_utc'].min()
            max_date = readings_df['timestamp_utc'].max()
            
            logger.info(f"Importing {len(readings_df)} readings for well {well_number} from {min_date} to {max_date}")
            
            # Prepare insertion records
            records = []
            for _, row in readings_df.iterrows():
                # Calculate Julian timestamp
                timestamp = row['timestamp_utc']
                julian_timestamp = timestamp.to_julian_date()
                
                # Add record with all data, using get() for optional fields
                records.append((
                    well_number,
                    row.get('serial_number', None),
                    timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    julian_timestamp,
                    row['pressure'],
                    row.get('water_pressure', None),  # Optional
                    row.get('water_level', None),     # Optional
                    row.get('temperature', None),     # Optional
                    row.get('baro_flag', None),       # Optional
                    row.get('level_flag', None)       # Optional
                ))
                
            # Insert readings and commit within a single write connection
            with sqlite3.connect(self.db_path, timeout=120.0) as conn:
                cursor = conn.cursor()
                
                if overwrite:
                    # Delete existing data for this well and time range
                    min_date_str = min_date.strftime('%Y-%m-%d %H:%M:%S')
                    max_date_str = max_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute("""
                        DELETE FROM water_level_readings 
                        WHERE well_number = ? AND timestamp_utc BETWEEN ? AND ?
                    """, (well_number, min_date_str, max_date_str))
                    
                    # Insert all records since we've deleted existing ones
                    logger.debug(f"Inserting {len(records)} records (overwrite mode)")
                    
                    # Insert in batches of 10,000 to avoid memory issues
                    batch_size = 10000
                    for i in range(0, len(records), batch_size):
                        batch = records[i:i+batch_size]
                        logger.debug(f"Inserting batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1} ({len(batch)} records)")
                        cursor.executemany("""
                            INSERT INTO water_level_readings (
                                well_number, serial_number, timestamp_utc, julian_timestamp, pressure,
                                water_pressure, water_level, temperature,
                                baro_flag, level_flag
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, batch)
                        conn.commit()  # Commit each batch
                else:
                    # Optimized approach: Get all existing timestamps in a single query
                    logger.debug("Checking for existing records...")
                    min_date_str = min_date.strftime('%Y-%m-%d %H:%M:%S')
                    max_date_str = max_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute("""
                        SELECT timestamp_utc FROM water_level_readings
                        WHERE well_number = ? AND timestamp_utc BETWEEN ? AND ?
                    """, (well_number, min_date_str, max_date_str))
                    
                    existing_timestamps = {row[0] for row in cursor.fetchall()}
                    logger.debug(f"Found {len(existing_timestamps)} existing records in date range")
                    
                    # Filter out existing records
                    records_to_insert = [r for r in records if r[2] not in existing_timestamps]
                    logger.debug(f"Filtered to {len(records_to_insert)} new records to insert")
                    
                    # Insert new records in batches to avoid memory issues
                    if records_to_insert:
                        batch_size = 10000
                        for i in range(0, len(records_to_insert), batch_size):
                            batch = records_to_insert[i:i+batch_size]
                            logger.debug(f"Inserting batch {i//batch_size + 1}/{(len(records_to_insert)-1)//batch_size + 1} ({len(batch)} records)")
                            cursor.executemany("""
                                INSERT INTO water_level_readings (
                                    well_number, serial_number, timestamp_utc, julian_timestamp, pressure,
                                    water_pressure, water_level, temperature,
                                    baro_flag, level_flag
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, batch)
                            conn.commit()  # Commit each batch
                    else:
                        logger.debug("No new records to insert")
                
                # Update well statistics after data has changed
                try:
                    from .well import WellModel
                    well_model = WellModel(self.db_path)
                    well_model.update_well_statistics(well_number)
                    logger.debug(f"Updated statistics for well {well_number}")
                    
                    # Also update the well flags in the wells table
                    self.update_well_flags(well_number)
                    logger.debug(f"Updated flag status for well {well_number}")
                except Exception as stats_error:
                    logger.error(f"Error updating well statistics or flags: {stats_error}")
                
            return True
                
        except Exception as e:
            logger.error(f"Error importing readings for well {well_number}: {e}")
            return False

    def get_latest_reading(self, well_number: str) -> Optional[Dict]:
        """Get the most recent reading for a well"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove the fields that don't exist in the table
                query = """
                    SELECT timestamp_utc, water_level,
                           temperature, baro_flag, level_flag
                    FROM water_level_readings
                    WHERE well_number = ?
                    ORDER BY timestamp_utc DESC
                    LIMIT 1
                """
                df = pd.read_sql_query(query, conn, params=(well_number,))
                if not df.empty:
                    return df.iloc[0].to_dict()
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest reading: {e}")
            return None
    
    def get_insertion_info(self, well_number: str, start_date: datetime, 
                          end_date: datetime) -> Optional[Dict]:
        """This method is deprecated as the fields are no longer stored in the database"""
        logger.warning("get_insertion_info is deprecated as insertion info is no longer stored in database")
        return None

    def check_data_overlap(self, well_number: str, start_date: datetime, 
                          end_date: datetime) -> Tuple[bool, str]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM water_level_readings 
                    WHERE well_number = ? AND timestamp_utc BETWEEN ? AND ?
                """, (well_number, start_date, end_date))
                
                overlap_count = cursor.fetchone()[0]
                if overlap_count > 0:
                    return True, f"Found {overlap_count} overlapping records"
                return False, "No overlap found"
                
        except Exception as e:
            return False, f"Error checking overlap: {str(e)}"
        
    def cleanup(self):
        """Clear any cached data"""
        self.db_path = None

    def well_has_data(self, well_number: str) -> bool:
        """Check if a well has any transducer data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT EXISTS (
                        SELECT 1 FROM water_level_readings 
                        WHERE well_number = ?
                        LIMIT 1
                    )
                """
                result = cursor.execute(query, (well_number,)).fetchone()
                return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Error checking well data: {e}")
            return False

    def check_well_flags(self, well_number: str) -> dict:
        """Check flag status for a well's data"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Query to check baro_flag and level_flag status
                query = """
                    SELECT
                        CASE
                            WHEN COUNT(*) = 0 THEN 'no_data'
                            WHEN COUNT(*) = SUM(CASE WHEN baro_flag IN ('master', 'master_corrected') THEN 1 ELSE 0 END) THEN 'all_master'
                            ELSE 'has_non_master'
                        END as baro_status,
                        CASE
                            WHEN COUNT(*) = 0 THEN 'no_data'
                            WHEN SUM(CASE WHEN level_flag = 'default_level' THEN 1 ELSE 0 END) > 0 THEN 'default_level'
                            ELSE 'no_default'
                        END as level_status
                    FROM water_level_readings
                    WHERE well_number = ?
                """
                result = cursor.execute(query, (well_number,)).fetchone()

                status_dict = {
                    'baro_status': result[0] if result else 'no_data',
                    'level_status': result[1] if result else 'no_data'
                }

                return status_dict
        except Exception as e:
            logger.error(f"Error checking well flags: {e}")
            return {'baro_status': 'error', 'level_status': 'error'}
            
    def check_all_wells_flags(self) -> dict:
        """Check flag status for ALL wells in a single, optimized query
        
        Returns a dictionary where keys are well_number and values are dictionaries
        containing 'baro_status' and 'level_status'.
        """
        try:
            logger.debug("Getting flags for all wells in a single query")
            start_time = datetime.now()
            
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Optimized query using EXISTS subqueries instead of counting all records
                # This avoids scanning all records for each well and is much faster
                query = """
                    WITH wells_with_readings AS (
                        SELECT DISTINCT well_number 
                        FROM water_level_readings
                    ),
                    non_master_wells AS (
                        SELECT DISTINCT well_number
                        FROM water_level_readings
                        WHERE baro_flag NOT IN ('master', 'master_corrected')
                    ),
                    default_level_wells AS (
                        SELECT DISTINCT well_number
                        FROM water_level_readings
                        WHERE level_flag = 'default_level'
                    )
                    SELECT 
                        w.well_number,
                        CASE
                            WHEN w.well_number NOT IN (SELECT well_number FROM wells_with_readings) THEN 'no_data'
                            WHEN w.well_number IN (SELECT well_number FROM non_master_wells) THEN 'has_non_master'
                            ELSE 'all_master'
                        END as baro_status,
                        CASE
                            WHEN w.well_number NOT IN (SELECT well_number FROM wells_with_readings) THEN 'no_data'
                            WHEN w.well_number IN (SELECT well_number FROM default_level_wells) THEN 'default_level'
                            ELSE 'no_default'
                        END as level_status
                    FROM wells w
                """
                results = cursor.execute(query).fetchall()

                # Convert to dictionary for fast lookup by well_number
                status_dict = {}
                for row in results:
                    status_dict[row[0]] = {
                        'baro_status': row[1],
                        'level_status': row[2]
                    }
                
                end_time = datetime.now()
                logger.debug(f"Retrieved flags for {len(status_dict)} wells in {(end_time-start_time).total_seconds():.4f} seconds")
                
                return status_dict
                
        except Exception as e:
            logger.error(f"Error checking all wells flags: {e}")
            return {}

    def update_well_flags(self, well_number: str):
        """Update baro_status and level_status in wells table for a given well"""
        try:
            flags = self.check_well_flags(well_number)
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE wells SET baro_status = ?, level_status = ? WHERE well_number = ?",
                    (flags.get('baro_status', 'no_data'), flags.get('level_status', 'no_data'), well_number)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating well flags for {well_number}: {e}")