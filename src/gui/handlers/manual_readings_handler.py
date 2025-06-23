"""
Handler for manual water level readings operations and utilities.
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class ManualReadingsHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def add_reading(self, data: Dict) -> Tuple[bool, str]:
        """Add a single manual reading to the database"""
        try:
            # Calculate water level from DTW measurements
            valid_measurements = [m for m in [data['dtw1'], data['dtw2']] if m is not None]
            dtw_avg = sum(valid_measurements) / len(valid_measurements)
            water_level = float(data['top_of_casing']) - dtw_avg
            
            # Insert into database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO manual_level_readings 
                    (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2, 
                     tape_error, comments, water_level, data_source, collected_by, is_dry)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['well_number'],
                    data['measurement_date'].strftime('%Y-%m-%d %H:%M:%S'),
                    dtw_avg,
                    data['dtw1'],
                    data['dtw2'],
                    None,
                    data['comments'],
                    water_level,
                    data.get('data_source', 'Manual'),
                    data.get('collected_by', 'UNKNOWN'),
                    data.get('is_dry', False)
                ))
                conn.commit()
            return True, "Manual reading added successfully"
            
        except Exception as e:
            return False, f"Error adding manual reading: {str(e)}"

    def import_readings(self, df: pd.DataFrame, selected_wells: Dict[str, Dict]) -> Tuple[int, List[str]]:
        """Import readings from a DataFrame"""
        try:
            records_added = 0
            errors = []
            
            logger.debug(f"Importing readings for {len(selected_wells)} wells from DataFrame with {len(df)} rows")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Process each well
                for well_number, options in selected_wells.items():
                    # Filter DataFrame for this well
                    well_data = df[df['well_number'] == well_number]
                    
                    logger.debug(f"Processing {len(well_data)} rows for well {well_number}")
                    
                    if well_data.empty:
                        continue
                    
                    # Get well's top of casing
                    cursor.execute('SELECT top_of_casing FROM wells WHERE well_number = ?', (well_number,))
                    result = cursor.fetchone()
                    
                    if not result:
                        errors.append(f"Well {well_number} not found in database")
                        continue
                    
                    top_of_casing = result[0]
                    
                    # Handle overwrite option
                    overwrite = options.get('overwrite', False)
                    
                    # Delete existing data if overwrite is requested
                    if overwrite and options.get('delete_existing', False):
                        cursor.execute('''
                            DELETE FROM manual_level_readings
                            WHERE well_number = ?
                        ''', (well_number,))
                        logger.debug(f"Deleted existing readings for well {well_number}")
                    
                    # Insert new readings
                    for _, row in well_data.iterrows():
                        try:
                            # Calculate water level
                            water_level = top_of_casing - row['dtw_avg']
                            
                            # Use INSERT OR REPLACE to handle existing readings
                            cursor.execute('''
                                INSERT OR REPLACE INTO manual_level_readings 
                                (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2,
                                 tape_error, comments, water_level, data_source, collected_by, is_dry)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                well_number,
                                row['measurement_date_utc'],
                                row['dtw_avg'],
                                row['dtw_1'],
                                row['dtw_2'],
                                row.get('tape_error'),
                                row.get('comments', ''),
                                water_level,
                                row.get('data_source', 'CSV Import'),
                                row.get('collected_by', 'UNKNOWN'),
                                row.get('is_dry', False)
                            ))
                            records_added += 1
                            logger.debug(f"Successfully inserted reading")
                        except Exception as e:
                            error_msg = f"Error importing reading for well {well_number}: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            errors.append(error_msg)
                
                conn.commit()
                logger.debug(f"Import completed. Added {records_added} records with {len(errors)} errors")
                
            return records_added, errors
            
        except Exception as e:
            logger.error(f"Error importing readings: {e}", exc_info=True)
            return 0, [f"Error: {str(e)}"]

    def update_monet_data(self, monet_data: Dict[str, pd.DataFrame]) -> Tuple[int, List[str], Dict[str, int]]:
        """Update readings from Monet data"""
        records_added = 0
        unmatched = []
        well_updates = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get mapping of well numbers - the GWI_ID from Monet matches our well_number!
                cursor.execute("SELECT well_number FROM wells")
                valid_wells = {row[0] for row in cursor.fetchall()}
                logger.debug(f"Found {len(valid_wells)} wells in database")
                logger.debug(f"Sample of well numbers: {list(valid_wells)[:5]}")
                
                # Process Monet data
                for gwi_id, well_df in monet_data.items():
                    # The GWI_ID from Monet is our well_number
                    if gwi_id not in valid_wells:
                        logger.debug(f"No matching well found for GWI_ID {gwi_id}")
                        if gwi_id not in unmatched:
                            unmatched.append(gwi_id)
                        continue
                    
                    # Process each reading for this well
                    for _, row in well_df.iterrows():
                        # Check if reading already exists
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM manual_level_readings 
                            WHERE well_number = ? 
                            AND measurement_date_utc = ?
                            AND data_source = 'Monet'
                        """, (gwi_id, row['Date_time']))
                        
                        if cursor.fetchone()[0] == 0:
                            # Extract serial number from Num_etape
                            tape_serial = None
                            if pd.notnull(row.get('Num_etape')) and '_' in str(row.get('Num_etape')):
                                tape_parts = str(row.get('Num_etape')).split('_')
                                if len(tape_parts) == 2:
                                    tape_serial = tape_parts[1]
                                    
                            # Get well's top of casing
                            cursor.execute("SELECT top_of_casing FROM wells WHERE well_number = ?", (gwi_id,))
                            top_of_casing = cursor.fetchone()[0]
                            
                            # Get the raw DTW values
                            dtw1 = row['DTW_1'] if pd.notnull(row['DTW_1']) else None
                            dtw2 = row['DTW_2'] if pd.notnull(row['DTW_2']) else None
                            
                            # Apply tape corrections if serial number is available
                            if tape_serial:
                                # Get correction factors for this tape
                                cursor.execute("""
                                    SELECT range_start, range_end, correction_factor
                                    FROM water_level_meter_corrections
                                    WHERE serial_number = ?
                                    ORDER BY range_start
                                """, (tape_serial,))
                                correction_factors = cursor.fetchall()
                                
                                # Apply corrections to DTW values based on depth
                                if correction_factors:
                                    if dtw1 is not None:
                                        for range_start, range_end, correction in correction_factors:
                                            if range_start <= dtw1 <= range_end:
                                                dtw1 += correction
                                                break
                                    
                                    if dtw2 is not None:
                                        for range_start, range_end, correction in correction_factors:
                                            if range_start <= dtw2 <= range_end:
                                                dtw2 += correction
                                                break
                            
                            # Calculate DTW average
                            dtw_avg = None
                            valid_measurements = [m for m in [dtw1, dtw2] if m is not None]
                            if valid_measurements:
                                dtw_avg = sum(valid_measurements) / len(valid_measurements)
                                water_level = float(top_of_casing) - dtw_avg
                                
                                # Insert new reading
                                cursor.execute('''
                                    INSERT INTO manual_level_readings 
                                    (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2,
                                     tape_error, water_level, data_source, collected_by, comments)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Monet', ?, ?)
                                ''', (
                                    gwi_id,
                                    row['Date_time'],
                                    dtw_avg,
                                    dtw1,  # Use corrected values
                                    dtw2,  # Use corrected values
                                    tape_serial,  # Store the extracted tape serial in tape_error field
                                    water_level,
                                    row.get('User_', 'UNKNOWN'),
                                    row.get('Comments', '')
                                ))
                                records_added += 1
                                well_updates[gwi_id] = well_updates.get(gwi_id, 0) + 1
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating Monet data: {e}")
            
        return records_added, unmatched, well_updates

    def get_readings(self, well_number: str) -> pd.DataFrame:
        """Get all manual readings for a well"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT measurement_date_utc, water_level, dtw_avg,
                           dtw_1, dtw_2, comments, data_source, collected_by
                    FROM manual_level_readings
                    WHERE well_number = ?
                    ORDER BY measurement_date_utc
                """
                df = pd.read_sql_query(query, conn, params=(well_number,))
                df['measurement_date_utc'] = pd.to_datetime(df['measurement_date_utc'])
                return df
                
        except Exception as e:
            logger.error(f"Error getting manual readings: {e}")
            return pd.DataFrame()

    def update_db_path(self, new_path: str):
        """Update the database path"""
        self.db_path = new_path