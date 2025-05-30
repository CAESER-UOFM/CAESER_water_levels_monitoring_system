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

logger = logging.getLogger(__name__)

class WellModel:
    """Handles well-related database operations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def import_wells(self, wells_data: List[Dict]) -> Tuple[bool, str]:
        """Import wells into database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for well in wells_data:
                    cursor.execute('''
                        INSERT INTO wells (
                            well_number, cae_number, latitude, longitude, 
                            top_of_casing, aquifer, min_distance_to_stream,
                            well_field, cluster, county, picture_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        'default_well.jpg'
                    ))
                
                conn.commit()
                return True, f"Successfully imported {len(wells_data)} wells"
                
        except Exception as e:
            logger.error(f"Error importing wells: {e}")
            return False, str(e)
    
    def update_well_picture(self, well_number: str, picture_path: str) -> bool:
        """Update the picture for a specific well"""
        try:
            # Validate the image file
            img = Image.open(picture_path)
            img.verify()
            
            # Create well_pictures directory if it doesn't exist
            pictures_dir = self.db_path.parent / 'well_pictures'
            pictures_dir.mkdir(exist_ok=True)
            
            # Generate new filename based on well number and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{well_number}_{timestamp}{Path(picture_path).suffix}"
            new_path = pictures_dir / new_filename
            
            # Copy the image file
            shutil.copy2(picture_path, new_path)
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE wells 
                    SET picture_path = ?, picture_updated_at = CURRENT_TIMESTAMP
                    WHERE well_number = ?
                ''', (new_filename, well_number))
                conn.commit()
                
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
        """Retrieve all wells from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT well_number, cae_number, latitude, longitude, 
                           top_of_casing, aquifer, well_field, county,
                           picture_path
                    FROM wells
                    ORDER BY well_number
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
                           picture_path, data_source, url
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
        
    def add_transducer(self, data: dict) -> Tuple[bool, str]:
        """Add or update transducer location"""
        try:
            logger.debug(f"Starting add_transducer with data: {data}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get latest entry for this serial number
                logger.debug(f"Checking for existing transducer {data['serial_number']}")
                cursor.execute('''
                    SELECT well_number, installation_date 
                    FROM transducers 
                    WHERE serial_number = ?
                    ORDER BY installation_date DESC
                    LIMIT 1
                ''', (data['serial_number'],))
                
                existing = cursor.fetchone()
                logger.debug(f"Existing record found: {existing}")
                
                if existing:
                    current_well, current_date = existing
                    logger.debug(f"Current well: {current_well}, Current date: {current_date}")
                    
                    if current_well == data['well_number']:
                        logger.debug("Transducer already at this location")
                        return False, "Transducer already registered at this location"
                    
                    install_date = pd.to_datetime(data['installation_date'])
                    current_date = pd.to_datetime(current_date)
                    logger.debug(f"New install date: {install_date}, Current date: {current_date}")
                    
                    if install_date <= current_date:
                        logger.debug("Installation date precedes current installation")
                        return False, f"Transducer currently installed at different well since {current_date}"
                
                # Insert new record
                logger.debug("Inserting new transducer record")
                logger.debug(f"SQL parameters: {data['serial_number']}, {data['well_number']}, "
                            f"{data['installation_date']}, {data.get('notes', '')}")
                            
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
                
                conn.commit()
                logger.info(f"Successfully added transducer {data['serial_number']} to {data['well_number']}")
                return True, "Transducer location updated successfully"
                
        except Exception as e:
            logger.error(f"Error adding transducer: {e}", exc_info=True)
            return False, str(e)
    
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
                        
                        # Ensure dates are in UTC
                        df['Date_time'] = pd.to_datetime(df['Date_time']).dt.tz_convert('UTC').dt.tz_localize(None)
                        
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

    def update_manual_level_readings(self, manual_data: dict) -> Tuple[int, List[str], Dict]:
        """
        Update manual level readings in database
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

                # Get latest measurement dates for each well
                cursor.execute('''
                    SELECT well_number, MAX(measurement_date_utc) as last_date
                    FROM manual_level_readings
                    GROUP BY well_number
                ''')
                latest_dates = dict(cursor.fetchall())

                for gwi_id, df in manual_data.items():
                    # Check if well exists in our database
                    if gwi_id in well_mapping:
                        well_number = gwi_id
                        toc = well_mapping[gwi_id]
                        well_updates[well_number] = 0  # Initialize counter

                        # Ensure dates are in UTC
                        df['Date_time'] = pd.to_datetime(df['Date_time']).dt.tz_convert('UTC').dt.tz_localize(None)

                        # Filter only new measurements
                        if well_number in latest_dates and latest_dates[well_number]:
                            last_date = pd.to_datetime(latest_dates[well_number])
                            new_data = df[df['Date_time'] > last_date]
                        else:
                            new_data = df  # All data is new for this well

                        # Process only new measurements
                        for _, row in new_data.iterrows():
                            dtw_1 = row.get('DTW_1')
                            dtw_2 = row.get('DTW_2')

                            # Calculate average DTW
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
                                    row.get('data_source', 'UNKNOWN'),
                                    row.get('collected_by', 'UNKNOWN')
                                ))
                                records_added += 1
                                well_updates[well_number] += 1
                    else:
                        unmatched_ids.append(gwi_id)

                conn.commit()
                return records_added, unmatched_ids, well_updates

        except Exception as e:
            logger.error(f"Error updating manual level readings: {e}")
            raise