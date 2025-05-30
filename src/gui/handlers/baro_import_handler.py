import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from ...database.models.barologger import BarologgerModel
from .solinst_reader import SolinstReader
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class BaroFileProcessor:
    def __init__(self, baro_model):
        self.baro_model = baro_model
        self.solinst_reader = SolinstReader()
        

    # baro_import_handler.py
    def validate_baro_file(self, file_path: Path) -> Tuple[bool, str, Optional[Dict]]:
        try:
            # Read file
            df, metadata = self.solinst_reader.read_xle(file_path)
            
            # Validate it's a barologger file
            if not self.solinst_reader.is_barologger(metadata):
                return False, "File is not from a barologger", None

            # Check if registered - but don't fail if not
            is_registered = self.baro_model.barologger_exists(metadata.serial_number)
            
            # Return success even if not registered, but include registration status in metadata
            return True, "File validated", {
                'serial_number': metadata.serial_number,
                'preview_data': df,
                'metadata': metadata,
                'needs_registration': not is_registered
            }

        except Exception as e:
            logger.error(f"Error validating file: {e}")
            return False, str(e), None
            
    def _is_barologger_registered(self, serial_number: str) -> bool:
        """Check if barologger is registered in database"""
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM barologgers 
                    WHERE serial_number = ?
                """, (serial_number,))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Error checking barologger registration: {e}")
            return False
        
    def get_logger_location(self, serial_number: str) -> str:
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT location_description 
                    FROM barologgers 
                    WHERE serial_number = ?
                """, (serial_number,))
                result = cursor.fetchone()
                return result[0] if result else "Unknown"
        except Exception as e:
            logger.error(f"Error getting logger location: {e}")
            return "Unknown"
                
    def check_data_overlap(self, serial_number: str, start_date: datetime, 
                          end_date: datetime) -> Tuple[bool, str]:
        """Check for overlapping data in the specified time range"""
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM barometric_readings 
                    WHERE serial_number = ? 
                    AND local_timestamp BETWEEN ? AND ?
                """, (serial_number, start_date, end_date))
                
                overlap_count = cursor.fetchone()[0]
                if overlap_count > 0:
                    return True, f"Found {overlap_count} overlapping records"
                return False, "No overlap found"
        except Exception as e:
            return False, f"Error checking overlap: {str(e)}"

    def get_existing_data(self, serial_number: str) -> pd.DataFrame:
        """Get existing data for a barologger"""
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                query = """
                    SELECT timestamp_utc, pressure, temperature
                    FROM barometric_readings
                    WHERE serial_number = ?
                    ORDER BY timestamp_utc
                """
                df = pd.read_sql_query(query, conn, params=(serial_number,))
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                return df
        except Exception as e:
            logger.error(f"Error getting existing data: {e}")
            return pd.DataFrame()