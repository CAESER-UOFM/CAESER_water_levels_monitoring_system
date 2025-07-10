# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 12:00:19 2025

@author: bledesma
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from PIL import Image
import shutil
import pandas as pd
from .base_model import BaseModel

logger = logging.getLogger(__name__)

class WellModel(BaseModel):
    """Handles well-related database operations"""
    
    def __init__(self, db_path: Path):
        super().__init__(db_path)
    
    def import_wells(self, wells_data: List[Dict]) -> Tuple[bool, str]:
        """Import wells into database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for well in wells_data:
                    # Normalize data_source if present, or use default
                    data_source = well.get('data_source')
                    if data_source:
                        # Convert to lowercase to match the constraint
                        data_source = data_source.strip().lower()
                        # Ensure value matches the database constraint
                        if data_source not in ('transducer', 'telemetry'):
                            # Default to 'transducer' if invalid value provided
                            data_source = 'transducer'
                    else:
                        # Default to "transducer" if not specified
                        data_source = 'transducer'
                    
                    cursor.execute('''
                        INSERT INTO wells (
                            well_number, cae_number, latitude, longitude, 
                            top_of_casing, aquifer, min_distance_to_stream,
                            well_field, cluster, county, picture_path,
                            data_source, url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        well['WN'],
                        well.get('CAE'),
                        float(well['LAT']),
                        float(well['LON']),
                        float(well['TOC']),
                        well['AQ'],
                        float(well.get('Min_dist_stream', 0)) if 'Min_dist_stream' in well else None,
                        well.get('WF'),
                        well.get('CT'),
                        well.get('County'),
                        'default_well.jpg',
                        data_source,  # Use lowercase data_source to match constraint
                        well.get('url')
                    ))
                
                conn.commit()
                
                # Mark the database as modified
                self.mark_modified()
                
                return True, f"Successfully imported {len(wells_data)} wells"
                
        except Exception as e:
            logger.error(f"Error importing wells: {e}")
            return False, str(e)
    
    def update_well_picture(self, well_number: str, picture_path: str) -> bool:
        """Update the picture for a specific well"""
        try:
            # Get the current picture path
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT picture_path FROM wells WHERE well_number = ?", (well_number,))
                result = cursor.fetchone()
                
                if not result:
                    logger.error(f"Well {well_number} not found")
                    return False
                
                # Create pictures directory if it doesn't exist
                if not self.db_path:
                    logger.error("DEBUG: Database path is None, cannot create pictures directory")
                    logger.error(f"DEBUG: self.db_path value: {repr(self.db_path)}")
                    return False
                logger.debug(f"DEBUG: Creating pictures directory from db_path: {self.db_path}")
                pictures_dir = Path(self.db_path).parent / 'pictures'
                pictures_dir.mkdir(exist_ok=True)
                
                # Generate a new filename
                new_filename = f"{well_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                new_path = pictures_dir / new_filename
                
                # Copy and resize the image
                img = Image.open(picture_path)
                img = img.convert('RGB')  # Convert to RGB if it's not
                img.thumbnail((800, 800))  # Resize while maintaining aspect ratio
                img.save(new_path, 'JPEG')
                
                # Update the database
                cursor.execute(
                    "UPDATE wells SET picture_path = ? WHERE well_number = ?",
                    (new_filename, well_number)
                )
                conn.commit()
                
                # Mark the database as modified
                self.mark_modified()
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating well picture: {e}")
            return False
    
    def get_well_picture_path(self, well_number: str) -> str:
        """Get the full path to a well's picture"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT picture_path 
                    FROM wells 
                    WHERE well_number = ?
                ''', (well_number,))
                result = cursor.fetchone()
                
                if (result):
                    pictures_dir = self.db_path.parent / 'well_pictures'
                    return str(pictures_dir / result[0])
                else:
                    return str(self.db_path.parent / 'well_pictures' / 'default_well.jpg')
                    
        except Exception as e:
            logger.error(f"Error getting well picture path: {e}")
            return str(self.db_path.parent / 'well_pictures' / 'default_well.jpg')
        
    def get_all_wells(self) -> List[Dict]:
        """Retrieve all wells from database with their latest flags"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    WITH LatestFlags AS (
                        SELECT 
                            well_number,
                            baro_flag,
                            level_flag,
                            ROW_NUMBER() OVER (PARTITION BY well_number ORDER BY timestamp_utc DESC) as rn
                        FROM water_level_readings
                    )
                    SELECT 
                        w.well_number, 
                        w.cae_number, 
                        w.latitude, 
                        w.longitude, 
                        w.top_of_casing, 
                        w.aquifer, 
                        w.well_field, 
                        w.county,
                        w.picture_path,
                        f.baro_flag,
                        f.level_flag
                    FROM wells w
                    LEFT JOIN LatestFlags f ON w.well_number = f.well_number AND f.rn = 1
                    ORDER BY w.well_number
                ''')
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error retrieving wells: {e}")
            return []

    def get_well(self, well_number: str) -> Optional[Dict]:
        """Get a single well by well number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT well_number, cae_number, latitude, longitude, 
                           top_of_casing, aquifer, well_field, county,
                           picture_path, data_source, url, parking_instructions,
                           access_requirements, safety_notes, special_instructions
                    FROM wells
                    WHERE well_number = ?
                ''', (well_number,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving well: {e}")
            return None
        
    def add_transducer(self, data: dict) -> Tuple[bool, str, dict]:
        """
        Add or update transducer location
        Returns: (success, message, additional_data)
        additional_data includes current location info if needs confirmation
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check current location
                current_location = self._get_current_transducer_location(cursor, data['serial_number'])
                
                if current_location:
                    if current_location['well_number'] == data['well_number']:
                        return False, "Transducer already registered at this location", None
                    
                    # Return info for confirmation
                    return False, "needs_confirmation", {
                        'current_location': current_location,
                        'new_location': data
                    }
                
                # No current location, proceed with insert
                return self._insert_new_transducer_location(cursor, data)
                
        except Exception as e:
            logger.error(f"Error adding transducer: {e}", exc_info=True)
            return False, str(e), None

    def _get_current_transducer_location(self, cursor: sqlite3.Cursor, serial_number: str) -> Optional[Dict]:
        """Get current active location for a transducer"""
        cursor.execute('''
            SELECT t.well_number, t.installation_date, t.id
            FROM transducers t
            WHERE t.serial_number = ?
            AND t.end_date IS NULL  -- Only get active installations
            ORDER BY t.installation_date DESC
            LIMIT 1
        ''', (serial_number,))
        
        row = cursor.fetchone()
        if row:
            return {
                'well_number': row[0],
                'start_date': row[1],
                'location_id': row[2]
            }
        return None

    def update_transducer_location(self, old_location_id: int, new_location_data: dict) -> Tuple[bool, str]:
        """Update transducer location with proper history tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # End current location
                cursor.execute('''
                    UPDATE transducer_locations 
                    SET end_date = ? 
                    WHERE id = ?
                ''', (datetime.now(), old_location_id))
                
                # Insert new location
                success, message, _ = self._insert_new_transducer_location(cursor, new_location_data)
                return success, message
                
        except Exception as e:
            logger.error(f"Error updating transducer location: {e}", exc_info=True)
            return False, str(e)

    def _insert_new_transducer_location(self, cursor: sqlite3.Cursor, data: dict) -> Tuple[bool, str, None]:
        """Insert new transducer location record"""
        try:
            # Check for existing active installation first
            cursor.execute('''
                SELECT 1 FROM transducers 
                WHERE serial_number = ? 
                AND well_number = ? 
                AND end_date IS NULL
            ''', (data['serial_number'], data['well_number']))
            
            if cursor.fetchone():
                return False, "Transducer already registered at this location", None
            
            # Insert into transducers if not exists
            cursor.execute('''
                INSERT INTO transducers 
                (serial_number, well_number, installation_date, notes)
                VALUES (?, ?, ?, ?)
            ''', (
                data['serial_number'],
                data['well_number'],
                data['installation_date'],
                data.get('notes', '')
            ))
            
            # Insert into transducer_locations
            cursor.execute('''
                INSERT INTO transducer_locations 
                (serial_number, well_number, start_date, notes)
                VALUES (?, ?, ?, ?)
            ''', (
                data['serial_number'],
                data['well_number'],
                data['installation_date'],
                data.get('notes', '')
            ))
            
            return True, "Transducer location updated successfully", None
            
        except Exception as e:
            raise e

    def get_transducer(self, serial_number: str) -> Optional[Dict]:
        """Get single transducer by serial number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT serial_number, well_number, installation_date, notes
                    FROM transducers
                    WHERE serial_number = ?
                    ORDER BY installation_date DESC
                    LIMIT 1
                ''', (serial_number,))
                
                row = cursor.fetchone()
                if row:
                    return dict(zip(['serial_number', 'well_number', 'installation_date', 'notes'], row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting transducer: {e}")
            return None

    def get_active_transducers(self) -> List[Dict]:
        """Get list of all active transducers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT serial_number, well_number, installation_date, notes 
                    FROM transducers 
                    ORDER BY installation_date DESC
                ''')
                
                columns = ['serial_number', 'well_number', 'installation_date', 'notes']
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting active transducers: {e}")
            return []

    def update_monet_data(self, monet_data: dict) -> Tuple[int, List[str], Dict]:
        records_added = 0
        unmatched_ids = []
        well_updates = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get mapping using well_number
                cursor.execute('SELECT well_number, top_of_casing FROM wells')
                well_mapping = {wn: toc for wn, toc in cursor.fetchall()}
                
                # Get latest measurement dates for each well
                cursor.execute('''
                    SELECT well_number, MAX(measurement_date_utc) as last_date
                    FROM manual_level_readings
                    GROUP BY well_number
                ''')
                latest_dates = dict(cursor.fetchall())
                
                for gwi_id, df in monet_data.items():
                    if gwi_id in well_mapping:
                        well_number = gwi_id
                        toc = well_mapping[gwi_id]
                        well_updates[well_number] = 0
                        
                        # Filter only new measurements
                        if well_number in latest_dates and latest_dates[well_number]:
                            last_date = pd.to_datetime(latest_dates[well_number])
                            new_data = df[df['Date_time'] > last_date]
                        else:
                            new_data = df
                        
                        for _, row in new_data.iterrows():
                            dtw_1 = row.get('DTW_1')
                            dtw_2 = row.get('DTW_2')
                            
                            valid_measurements = [m for m in [dtw_1, dtw_2] if pd.notna(m)]
                            if valid_measurements:
                                dtw_avg = sum(valid_measurements) / len(valid_measurements)
                                water_level = float(toc) - dtw_avg
                                
                                cursor.execute('''
                                    INSERT INTO manual_level_readings 
                                    (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2, 
                                     tape_error, comments, water_level, data_source, collected_by)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    well_number,
                                    row['Date_time'].strftime('%Y-%m-%d %H:%M:%S'),  # Store in UTC
                                    dtw_avg,
                                    dtw_1,
                                    dtw_2,
                                    row.get('Tape_error'),
                                    row.get('Comments', ''),
                                    water_level,
                                    'Monet',                     # Set data_source to 'Monet'
                                    row.get('User', 'UNKNOWN')   # Get collector from User field
                                ))
                                records_added += 1
                                well_updates[well_number] += 1
                    else:
                        unmatched_ids.append(gwi_id)
                
                conn.commit()
                return records_added, unmatched_ids, well_updates
                    
        except Exception as e:
            logger.error(f"Error updating Monet data: {e}")
            raise

    def update_manual_level_readings(self, manual_data: dict, selected_wells: dict) -> Tuple[int, List[str], Dict]:
        """
        Update manual level readings in database
        Args:
            manual_data: Dictionary mapping well numbers to their measurement data
            selected_wells: Dictionary mapping well numbers to dict with 'overwrite' flag
        Returns tuple of:
        - number of records added
        - list of unmatched GWI_IDs
        - dict of updates per well
        """
        records_added = 0
        unmatched_ids = []
        well_updates = {}  # Track updates per well

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get mapping using well_number
                cursor.execute('SELECT well_number, top_of_casing FROM wells')
                well_mapping = {wn: toc for wn, toc in cursor.fetchall()}

                for gwi_id, df in manual_data.items():
                    # Check if well exists in our database and is selected
                    if gwi_id in well_mapping and gwi_id in selected_wells:
                        well_number = gwi_id
                        toc = well_mapping[gwi_id]
                        well_updates[well_number] = 0  # Initialize counter
                        overwrite = selected_wells[well_number].get('overwrite', False)

                        # Process measurements
                        for _, row in df.iterrows():
                            dtw_1 = row.get('DTW_1')
                            dtw_2 = row.get('DTW_2')

                            # Calculate average DTW
                            valid_measurements = [m for m in [dtw_1, dtw_2] if pd.notna(m)]
                            if valid_measurements:
                                dtw_avg = sum(valid_measurements) / len(valid_measurements)
                                water_level = float(toc) - dtw_avg

                                # Use appropriate INSERT clause based on overwrite flag
                                if overwrite:
                                    sql = '''
                                        INSERT OR REPLACE INTO manual_level_readings 
                                        (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2, 
                                         tape_error, comments, water_level, data_source, collected_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    '''
                                else:
                                    sql = '''
                                        INSERT OR IGNORE INTO manual_level_readings 
                                        (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2, 
                                         tape_error, comments, water_level, data_source, collected_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    '''

                                cursor.execute(sql, (
                                    well_number,
                                    row['Date_time'].strftime('%Y-%m-%d %H:%M:%S'),  # Store in UTC
                                    dtw_avg,
                                    dtw_1,
                                    dtw_2,
                                    row.get('Tape_error'),
                                    row.get('Comments', ''),
                                    water_level,
                                    row.get('data_source', 'UNKNOWN'),
                                    row.get('collected_by', 'UNKNOWN')
                                ))

                                # Only increment counters if a row was actually inserted/updated
                                if cursor.rowcount > 0:
                                    records_added += 1
                                    well_updates[well_number] += 1
                    else:
                        if gwi_id not in well_mapping:
                            unmatched_ids.append(gwi_id)

                conn.commit()
                return records_added, unmatched_ids, well_updates

        except Exception as e:
            logger.error(f"Error updating manual level readings: {e}")
            raise

    def add_well(self, data: dict) -> Tuple[bool, str]:
        """Add a new well to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if well already exists
                cursor.execute("SELECT 1 FROM wells WHERE well_number = ?", (data['well_number'],))
                if cursor.fetchone():
                    return False, f"Well {data['well_number']} already exists"
                
                # Normalize data_source if present, or use default
                data_source = data.get('data_source')
                if data_source:
                    # Convert to lowercase to match the constraint
                    data_source = data_source.strip().lower()
                    # Ensure value matches the database constraint
                    if data_source not in ('transducer', 'telemetry'):
                        # Default to 'transducer' if invalid value provided
                        data_source = 'transducer'
                else:
                    # Default to "transducer" if not specified
                    data_source = 'transducer'
                
                # Insert the well
                cursor.execute('''
                    INSERT INTO wells (
                        well_number, cae_number, latitude, longitude, 
                        top_of_casing, aquifer, min_distance_to_stream,
                        well_field, cluster, county, picture_path,
                        data_source, url, parking_instructions, 
                        access_requirements, safety_notes, special_instructions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['well_number'],
                    data.get('cae_number'),
                    float(data['latitude']),
                    float(data['longitude']),
                    float(data['top_of_casing']),
                    data['aquifer'],
                    float(data.get('min_distance_to_stream', 0)) if data.get('min_distance_to_stream') else None,
                    data.get('well_field'),
                    data.get('cluster'),
                    data.get('county'),
                    'default_well.jpg',
                    data_source,  # Use lowercase data_source to match constraint
                    data.get('url'),
                    data.get('parking_instructions'),
                    data.get('access_requirements'),
                    data.get('safety_notes'),
                    data.get('special_instructions')
                ))
                
                conn.commit()
                
                # Track the well addition for change tracking
                if (self.db_manager and hasattr(self.db_manager, 'change_tracker') and 
                    self.db_manager.change_tracker):
                    from src.gui.handlers.change_tracker import ChangeType, ChangeAction
                    self.db_manager.change_tracker.track_change(
                        ChangeType.MANUAL, ChangeAction.INSERT, "wells",
                        data['well_number'], description=f"Added new well {data['well_number']} ({data.get('cae_number', 'no CAE')})"
                    )
                
                # Mark the database as modified
                self.mark_modified()
                
                return True, f"Well {data['well_number']} added successfully"
                
        except Exception as e:
            logger.error(f"Error adding well: {e}")
            return False, str(e)

    def update_well(self, well_number: str, data: dict) -> Tuple[bool, str]:
        """Update an existing well in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if well exists
                cursor.execute("SELECT 1 FROM wells WHERE well_number = ?", (well_number,))
                if not cursor.fetchone():
                    return False, f"Well {well_number} not found"
                
                # Normalize data_source if present, or use default
                data_source = data.get('data_source')
                if data_source:
                    # Convert to lowercase to match the constraint
                    data_source = data_source.strip().lower()
                    # Ensure value matches the database constraint
                    if data_source not in ('transducer', 'telemetry'):
                        # Default to 'transducer' if invalid value provided
                        data_source = 'transducer'
                else:
                    # Default to "transducer" if not specified
                    data_source = 'transducer'
                
                # Update the well
                cursor.execute('''
                    UPDATE wells SET
                        cae_number = ?,
                        latitude = ?,
                        longitude = ?,
                        top_of_casing = ?,
                        aquifer = ?,
                        min_distance_to_stream = ?,
                        well_field = ?,
                        cluster = ?,
                        county = ?,
                        data_source = ?,
                        url = ?,
                        parking_instructions = ?,
                        access_requirements = ?,
                        safety_notes = ?,
                        special_instructions = ?
                    WHERE well_number = ?
                ''', (
                    data.get('cae_number'),
                    float(data['latitude']),
                    float(data['longitude']),
                    float(data['top_of_casing']),
                    data['aquifer'],
                    float(data.get('min_distance_to_stream', 0)) if data.get('min_distance_to_stream') else None,
                    data.get('well_field'),
                    data.get('cluster'),
                    data.get('county'),
                    data_source,  # Use lowercase data_source to match constraint
                    data.get('url'),
                    data.get('parking_instructions'),
                    data.get('access_requirements'),
                    data.get('safety_notes'),
                    data.get('special_instructions'),
                    well_number
                ))
                
                conn.commit()
                
                # Track the well update for change tracking
                if (self.db_manager and hasattr(self.db_manager, 'change_tracker') and 
                    self.db_manager.change_tracker):
                    from src.gui.handlers.change_tracker import ChangeType, ChangeAction
                    self.db_manager.change_tracker.track_change(
                        ChangeType.MANUAL, ChangeAction.UPDATE, "wells",
                        well_number, description=f"Updated well {well_number} information"
                    )
                
                # Mark the database as modified
                self.mark_modified()
                
                return True, f"Well {well_number} updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating well: {e}")
            return False, str(e)

    def delete_well(self, well_number: str) -> Tuple[bool, str]:
        """Delete a well and all associated data from the database"""
        logger.info(f"DELETE_DEBUG: Starting well deletion for well: {well_number}")
        logger.info(f"DELETE_DEBUG: Database path: {self.db_path}")
        logger.info(f"DELETE_DEBUG: Database manager: {self.db_manager}")
        
        # Check if this is a cloud database
        is_cloud_db = (hasattr(self.db_manager, 'is_cloud_database') and 
                      self.db_manager.is_cloud_database if self.db_manager else False)
        logger.info(f"DELETE_DEBUG: Is cloud database: {is_cloud_db}")
        
        if self.db_manager and hasattr(self.db_manager, 'current_db'):
            logger.info(f"DELETE_DEBUG: Database manager current_db: {self.db_manager.current_db}")
            
        if self.db_manager and hasattr(self.db_manager, 'temp_db_path'):
            logger.info(f"DELETE_DEBUG: Database manager temp_db_path: {self.db_manager.temp_db_path}")
            
        # CRITICAL: Check if current_db and temp_db_path are the same
        if (self.db_manager and 
            hasattr(self.db_manager, 'current_db') and 
            hasattr(self.db_manager, 'temp_db_path')):
            current_db_str = str(self.db_manager.current_db) if self.db_manager.current_db else "None"
            temp_db_str = str(self.db_manager.temp_db_path) if self.db_manager.temp_db_path else "None"
            logger.info(f"DELETE_DEBUG: current_db == temp_db_path: {current_db_str == temp_db_str}")
            logger.info(f"DELETE_DEBUG: self.db_path == current_db: {str(self.db_path) == current_db_str}")
            logger.info(f"DELETE_DEBUG: self.db_path == temp_db_path: {str(self.db_path) == temp_db_str}")
            
        try:
            # Check if file exists and get size before deletion
            import os
            if os.path.exists(self.db_path):
                file_size_before = os.path.getsize(self.db_path)
                logger.info(f"DELETE_DEBUG: Database file size before deletion: {file_size_before} bytes")
            else:
                logger.warning(f"DELETE_DEBUG: Database file does not exist: {self.db_path}")
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if well exists
                cursor.execute("SELECT 1 FROM wells WHERE well_number = ?", (well_number,))
                if not cursor.fetchone():
                    return False, f"Well {well_number} not found"
                
                # Count associated data for reporting
                cursor.execute("SELECT COUNT(*) FROM transducers WHERE well_number = ?", (well_number,))
                transducer_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM water_level_readings WHERE well_number = ?", (well_number,))
                water_level_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_flags WHERE well_number = ?", (well_number,))
                user_flag_count = cursor.fetchone()[0]
                
                # Check if user_notes table exists before querying it (for older databases)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_notes'")
                user_notes_table_exists = cursor.fetchone() is not None
                
                if user_notes_table_exists:
                    cursor.execute("SELECT COUNT(*) FROM user_notes WHERE well_number = ?", (well_number,))
                    user_note_count = cursor.fetchone()[0]
                else:
                    user_note_count = 0
                
                # Delete all associated data in proper order (child tables first)
                
                # Delete water level readings
                cursor.execute("DELETE FROM water_level_readings WHERE well_number = ?", (well_number,))
                deleted_readings = cursor.rowcount
                logger.info(f"Deleted {deleted_readings} water level readings for well {well_number}")
                
                # Track the deletion for change tracking
                if (self.db_manager and hasattr(self.db_manager, 'change_tracker') and 
                    self.db_manager.change_tracker and deleted_readings > 0):
                    self.db_manager.change_tracker.track_bulk_water_level_delete(well_number, deleted_readings)
                
                # Delete user flags
                cursor.execute("DELETE FROM user_flags WHERE well_number = ?", (well_number,))
                
                # Delete user notes (only if table exists)
                if user_notes_table_exists:
                    cursor.execute("DELETE FROM user_notes WHERE well_number = ?", (well_number,))
                
                # Delete transducers (this will cascade to any transducer-specific data)
                cursor.execute("DELETE FROM transducers WHERE well_number = ?", (well_number,))
                
                # Delete the well registration
                cursor.execute("DELETE FROM wells WHERE well_number = ?", (well_number,))
                
                conn.commit()
                logger.info(f"DELETE_DEBUG: Transaction committed to database")
                
                # Force SQLite to write changes to disk immediately
                cursor.execute("PRAGMA wal_checkpoint(FULL)")
                cursor.execute("VACUUM")
                conn.commit()
                logger.info(f"DELETE_DEBUG: WAL checkpoint and VACUUM completed")
                
                # Check file size after deletion
                if os.path.exists(self.db_path):
                    file_size_after = os.path.getsize(self.db_path)
                    logger.info(f"DELETE_DEBUG: Database file size after deletion: {file_size_after} bytes")
                    logger.info(f"DELETE_DEBUG: File size change: {file_size_before - file_size_after} bytes")
                
                # Mark the database as modified
                self.mark_modified()
                logger.info(f"DELETE_DEBUG: Database marked as modified")
                
                # Build detailed message about what was deleted
                deleted_items = [f"well {well_number}"]
                if transducer_count > 0:
                    deleted_items.append(f"{transducer_count} transducer(s)")
                if water_level_count > 0:
                    deleted_items.append(f"{water_level_count} water level reading(s)")
                if user_flag_count > 0:
                    deleted_items.append(f"{user_flag_count} user flag(s)")
                if user_note_count > 0:
                    deleted_items.append(f"{user_note_count} user note(s)")
                
                return True, f"Successfully deleted {', '.join(deleted_items)}"
                
        except Exception as e:
            logger.error(f"Error deleting well: {e}")
            return False, str(e)

    def update_well_statistics(self, well_number: str) -> bool:
        """Update the statistics for a specific well"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate current statistics
                cursor.execute("""
                    SELECT 
                        COUNT(timestamp_utc) AS num_points,
                        MIN(timestamp_utc) AS min_timestamp,
                        MAX(timestamp_utc) AS max_timestamp
                    FROM water_level_readings
                    WHERE well_number = ?
                """, (well_number,))
                
                stats = cursor.fetchone()
                if not stats:
                    # No readings found, but we should still update the record with zeros
                    stats = (0, None, None)
                
                # Check if record already exists
                cursor.execute("SELECT well_number FROM well_statistics WHERE well_number = ?", (well_number,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing record
                    cursor.execute("""
                        UPDATE well_statistics 
                        SET num_points = ?,
                            min_timestamp = ?,
                            max_timestamp = ?,
                            last_update = CURRENT_TIMESTAMP
                        WHERE well_number = ?
                    """, (*stats, well_number))
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO well_statistics 
                        (well_number, num_points, min_timestamp, max_timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (well_number, *stats))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating well statistics: {e}")
            return False

    def get_well_statistics(self, well_number: str = None) -> List[Dict]:
        """Get statistics for one well or all wells"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First check if the well_statistics table exists and has the expected columns
                cursor.execute("PRAGMA table_info(well_statistics)")
                columns = {row[1] for row in cursor.fetchall()}
                
                # Check if table exists with the expected structure
                if not columns or 'num_points' not in columns:
                    logger.warning("well_statistics table doesn't exist or doesn't have expected columns")
                    # Fallback to direct query instead
                    return self._get_well_statistics_direct(cursor, well_number)
                
                if well_number:
                    # Get statistics for a specific well
                    cursor.execute("""
                        SELECT 
                            w.well_number, 
                            w.cae_number, 
                            w.latitude, 
                            w.longitude,
                            IFNULL(s.num_points, 0) AS num_points,
                            s.min_timestamp,
                            s.max_timestamp
                        FROM wells w
                        LEFT JOIN well_statistics s ON w.well_number = s.well_number
                        WHERE w.well_number = ?
                    """, (well_number,))
                else:
                    # Get statistics for all wells
                    cursor.execute("""
                        SELECT 
                            w.well_number, 
                            w.cae_number, 
                            w.latitude, 
                            w.longitude,
                            IFNULL(s.num_points, 0) AS num_points,
                            s.min_timestamp,
                            s.max_timestamp
                        FROM wells w
                        LEFT JOIN well_statistics s ON w.well_number = s.well_number
                        WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
                    """)
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error retrieving well statistics: {e}")
            return []

    def _get_well_statistics_direct(self, cursor, well_number: str = None) -> List[Dict]:
        """Get well statistics directly with a query that doesn't use the statistics table"""
        try:
            if well_number:
                # Get statistics for a specific well with a direct count query
                cursor.execute("""
                    SELECT 
                        w.well_number, 
                        w.cae_number, 
                        w.latitude, 
                        w.longitude,
                        COUNT(l.timestamp_utc) AS num_points,
                        MIN(l.timestamp_utc) AS min_timestamp,
                        MAX(l.timestamp_utc) AS max_timestamp
                    FROM wells w
                    LEFT JOIN water_level_readings l ON w.well_number = l.well_number
                    WHERE w.well_number = ?
                    GROUP BY w.well_number, w.cae_number, w.latitude, w.longitude
                """, (well_number,))
            else:
                # Get statistics for all wells with a direct count query
                cursor.execute("""
                    SELECT 
                        w.well_number, 
                        w.cae_number, 
                        w.latitude, 
                        w.longitude,
                        COUNT(l.timestamp_utc) AS num_points,
                        MIN(l.timestamp_utc) AS min_timestamp,
                        MAX(l.timestamp_utc) AS max_timestamp
                    FROM wells w
                    LEFT JOIN water_level_readings l ON w.well_number = l.well_number
                    WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
                    GROUP BY w.well_number, w.cae_number, w.latitude, w.longitude
                """)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving well statistics directly: {e}")
            return []