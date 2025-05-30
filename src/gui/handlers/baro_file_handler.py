import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from .solinst_reader import SolinstReader
import pandas as pd
from datetime import timedelta
from ..utils.file_organizer import XLEFileOrganizer  # Import the new utility

logger = logging.getLogger(__name__)

class BaroFileHandler:
    """Handles Solinst barologger file operations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.solinst_reader = SolinstReader()
        # Initialize file organizer with app root directory (parent of database)
        self.file_organizer = XLEFileOrganizer(db_path.parent, db_name=db_path.stem)

    def import_file(self, file_path: Path, serial_number: str, 
                   overwrite: bool = False) -> Tuple[bool, str]:
        """Import data from XLE file"""
        try:
            # Read and validate file
            df, metadata = self.solinst_reader.read_xle(file_path)
            
            if not self.solinst_reader.is_barologger(metadata):
                return False, "File is not from a barologger"
                
            # Verify serial number matches
            if metadata.serial_number != serial_number:
                return False, f"Serial number mismatch. File: {metadata.serial_number}, Expected: {serial_number}"
            
            # Import the readings
            success = self._save_readings(df, serial_number, overwrite)
            if success:
                # Record the import
                self._record_import_history(serial_number, file_path, len(df))
                
                # Organize the imported file
                try:
                    # Get location description from database
                    location = self._get_location_description(serial_number)
                    # Get start and end dates from data
                    start_date = pd.to_datetime(df['timestamp_utc'].min())
                    end_date = pd.to_datetime(df['timestamp_utc'].max())
                    
                    # Organize the file
                    organized_path = self.file_organizer.organize_barologger_file(
                        file_path, serial_number, location, start_date, end_date
                    )
                    
                    if organized_path:
                        logger.info(f"File organized at: {organized_path}")
                except Exception as e:
                    logger.error(f"Error organizing file: {e}")
                    # Continue with success even if file organization fails
                
                return True, f"Successfully imported {len(df)} readings"
            else:
                return False, "Failed to save readings to database"
                
        except Exception as e:
            logger.error(f"Error importing file {file_path}: {e}")
            return False, str(e)
    
    def scan_folder(self, folder_path: Path, serial_number: str) -> List[Path]:
        """Find XLE files for specific barologger in folder"""
        try:
            xle_files = []
            for file_path in folder_path.rglob('*.xle'):
                try:
                    _, metadata = self.solinst_reader.read_xle(file_path)
                    if (self.solinst_reader.is_barologger(metadata) and 
                        metadata.serial_number == serial_number):
                        xle_files.append(file_path)
                except Exception as e:
                    logger.warning(f"Skipping {file_path}: {e}")
                    continue
            return xle_files
            
        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")
            return []
    
    def _save_readings(self, df: pd.DataFrame, serial_number: str, overwrite: bool) -> bool:
        """Save barometric readings to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    if overwrite:
                        cursor.execute('''
                            DELETE FROM barometric_readings
                            WHERE serial_number = ? AND timestamp_utc = ?
                        ''', (serial_number, row['timestamp_utc']))
    
                    # Store timestamp in UTC
                    timestamp_utc = pd.to_datetime(row['timestamp_utc'])
    
                    cursor.execute('''
                        INSERT INTO barometric_readings (
                            serial_number, timestamp_utc, pressure,
                            temperature, quality_flag
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        serial_number,
                        timestamp_utc.strftime('%Y-%m-%d %H:%M:%S'),
                        float(row.get('pressure', row.get('level', 0))),
                        float(row['temperature']) if 'temperature' in row else None,
                        row.get('quality_flag')
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving readings: {e}")
            return False

    def _record_import_history(self, serial_number: str, file_path: Path, 
                             record_count: int):
        """Record import in history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO baro_import_history (
                        serial_number, file_name, record_count,
                        import_date
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    serial_number,
                    file_path.name,
                    record_count
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error recording import history: {e}")
    
    def _get_location_description(self, serial_number: str) -> str:
        """Get location description for a barologger"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT location_description
                    FROM barologgers
                    WHERE serial_number = ?
                ''', (serial_number,))
                result = cursor.fetchone()
                return result[0] if result else "Unknown"
        except Exception as e:
            logger.error(f"Error getting location description: {e}")
            return "Unknown"