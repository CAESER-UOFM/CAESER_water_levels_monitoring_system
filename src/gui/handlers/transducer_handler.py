"""
Handler for transducer operations and utilities.
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from ...database.models.well import WellModel

logger = logging.getLogger(__name__)

class TransducerHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.well_model = None  # Initialize as None
        self.parent = None
        if db_path:  # Only create well_model if we have a valid path
            self.well_model = WellModel(db_path)

    def get_transducer(self, serial_number: str) -> Optional[Dict]:
        """Get transducer information from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.*, w.cae_number
                    FROM transducers t
                    LEFT JOIN wells w ON t.well_number = w.well_number
                    WHERE t.serial_number = ?
                    ORDER BY t.installation_date DESC
                    LIMIT 1
                """, (serial_number,))
                result = cursor.fetchone()
                
                if result:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, result))
                return None
                
        except Exception as e:
            logger.error(f"Error getting transducer info: {e}")
            return None

    def get_all_transducers(self) -> List[Dict]:
        """Get all transducers with their current locations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    WITH LocationCount AS (
                        SELECT serial_number, COUNT(*) as loc_count
                        FROM transducers 
                        GROUP BY serial_number
                    ),
                    LastInstall AS (
                        SELECT t.serial_number, t.well_number, t.installation_date,
                               w.cae_number
                        FROM transducers t
                        LEFT JOIN wells w ON t.well_number = w.well_number
                        WHERE (t.serial_number, t.installation_date) IN (
                            SELECT serial_number, MAX(installation_date)
                            FROM transducers
                            GROUP BY serial_number
                        )
                    )
                    SELECT 
                        l.serial_number,
                        l.well_number,
                        l.cae_number,
                        l.installation_date,
                        c.loc_count
                    FROM LastInstall l
                    JOIN LocationCount c ON l.serial_number = c.serial_number
                    ORDER BY l.serial_number
                ''')
                
                results = cursor.fetchall()
                transducers = []
                
                for result in results:
                    transducers.append({
                        'serial_number': result[0],
                        'well_number': result[1],
                        'cae_number': result[2],
                        'installation_date': result[3],
                        'location_count': result[4]
                    })
                
                return transducers
                
        except Exception as e:
            logger.error(f"Error getting all transducers: {e}")
            return []

    def add_transducer(self, data: dict) -> Tuple[bool, str, Optional[Dict]]:
        """Add or update transducer with location confirmation"""
        logger.debug(f"Adding transducer with data: {data}")
        if not self.well_model:
            logger.error("No well_model available")
            return False, "Database not properly initialized", None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if transducer exists and get current location
                cursor.execute("""
                    SELECT t.well_number, w.cae_number 
                    FROM transducers t
                    LEFT JOIN wells w ON t.well_number = w.well_number
                    WHERE t.serial_number = ?
                    ORDER BY t.installation_date DESC
                    LIMIT 1
                """, (data['serial_number'],))
                
                result = cursor.fetchone()
                
                if result and result[0]:  # If transducer exists and has a location
                    current_location = {
                        'well_number': result[0],
                        'cae_number': result[1]
                    }
                    new_location = {
                        'well_number': data['well_number'],
                        'installation_date': data['installation_date']
                    }
                    return True, "needs_confirmation", {
                        'current_location': current_location,
                        'new_location': new_location
                    }
                
                # If no existing location or confirmation received, add new record
                cursor.execute("""
                    INSERT INTO transducers 
                    (serial_number, well_number, installation_date, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    data['serial_number'],
                    data['well_number'],
                    data['installation_date'],
                    data.get('notes', '')
                ))
                
                # Also add initial location to locations table
                cursor.execute("""
                    INSERT INTO transducer_locations 
                    (serial_number, well_number, start_date, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    data['serial_number'],
                    data['well_number'],
                    data['installation_date'],
                    data.get('notes', '')
                ))
                
                conn.commit()
                return True, "Transducer added successfully", None
                
        except sqlite3.IntegrityError as e:
            logger.error(f"Database integrity error: {e}")
            return False, f"Database integrity error: {str(e)}", None
        except Exception as e:
            logger.error(f"Error adding transducer: {e}")
            return False, f"Error adding transducer: {str(e)}", None

    def update_transducer(self, data: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """Update transducer information"""
        try:
            logger.debug(f"Starting update_transducer with data: {data}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, get the current well_number before making any changes
                logger.debug(f"Fetching current well number for serial: {data['serial_number']}")
                cursor.execute("""
                    SELECT well_number FROM transducers 
                    WHERE serial_number = ?
                """, (data['serial_number'],))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"Transducer {data['serial_number']} not found")
                    return False, f"Transducer {data['serial_number']} not found", None
                    
                current_well_number = result[0]
                logger.debug(f"Current well number: {current_well_number}")
                
                # Get current timestamp for end_date
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.debug(f"Current timestamp for end_date: {current_time}")
                
                # First check if there's an existing record in locations with no end_date
                logger.debug("Checking for existing location record with no end_date")
                cursor.execute("""
                    SELECT id, well_number FROM transducer_locations
                    WHERE serial_number = ? AND end_date IS NULL
                """, (data['serial_number'],))
                
                existing_locations = cursor.fetchall()
                logger.debug(f"Found {len(existing_locations)} existing location records with no end_date")
                
                # Now archive the current record using the directly retrieved well_number
                logger.debug(f"Updating end_date for current location: {current_well_number}")
                cursor.execute("""
                    UPDATE transducer_locations
                    SET end_date = ?
                    WHERE serial_number = ? 
                    AND well_number = ?
                    AND end_date IS NULL
                """, (current_time, data['serial_number'], current_well_number))
                
                updated_rows = cursor.rowcount
                logger.debug(f"Updated {updated_rows} rows in transducer_locations")
                
                # Then, add a new record to transducer_locations for the new location
                logger.debug(f"Adding new location record for well: {data['well_number']}")
                cursor.execute("""
                    INSERT INTO transducer_locations 
                    (serial_number, well_number, start_date, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    data['serial_number'],
                    data['well_number'],
                    data['installation_date'],
                    data.get('notes', '')
                ))
                
                # Finally, update the transducer record
                logger.debug(f"Updating main transducer record to well: {data['well_number']}")
                cursor.execute("""
                    UPDATE transducers 
                    SET well_number = ?,
                        installation_date = ?,
                        notes = ?
                    WHERE serial_number = ?
                """, (
                    data['well_number'],
                    data['installation_date'],
                    data.get('notes', ''),
                    data['serial_number']
                ))
                
                main_updated = cursor.rowcount
                logger.debug(f"Updated {main_updated} rows in transducers table")
                
                # Verify the changes before committing
                logger.debug("Verifying updates before commit")
                cursor.execute("""
                    SELECT t.well_number, l.well_number, l.end_date
                    FROM transducers t
                    LEFT JOIN transducer_locations l ON t.serial_number = l.serial_number
                    WHERE t.serial_number = ?
                    ORDER BY l.start_date DESC
                """, (data['serial_number'],))
                
                verification = cursor.fetchall()
                logger.debug(f"Verification results: {verification}")
                
                conn.commit()
                logger.debug("Changes committed successfully")
                
                # Return 3 values to match expected signature
                update_info = {
                    'serial_number': data['serial_number'],
                    'well_number': data['well_number'],
                    'installation_date': data['installation_date']
                }
                return True, "Transducer updated successfully", update_info
                    
        except sqlite3.IntegrityError as e:
            logger.error(f"Database integrity error: {e}", exc_info=True)
            return False, f"Database integrity error: {str(e)}", None
        except Exception as e:
            logger.error(f"Error updating transducer: {e}", exc_info=True)
            return False, f"Error updating transducer: {str(e)}", None

    def delete_transducer(self, serial_number: str) -> Tuple[bool, str]:
        """Delete a transducer registration while preserving measurement data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First check if there are water level readings for this transducer
                cursor.execute("""
                    SELECT COUNT(*) FROM water_level_readings 
                    WHERE serial_number = ?
                """, (serial_number,))
                
                reading_count = cursor.fetchone()[0]
                
                # Delete from transducer_locations table
                cursor.execute("""
                    DELETE FROM transducer_locations 
                    WHERE serial_number = ?
                """, (serial_number,))
                
                locations_deleted = cursor.rowcount
                
                # Delete from transducers table
                cursor.execute("""
                    DELETE FROM transducers 
                    WHERE serial_number = ?
                """, (serial_number,))
                
                conn.commit()
                
                if reading_count > 0:
                    return True, f"Transducer registration removed. {reading_count} water level readings preserved."
                else:
                    return True, f"Transducer registration removed. No water level readings found."
                
        except Exception as e:
            logger.error(f"Error deleting transducer: {e}", exc_info=True)
            return False, f"Error deleting transducer: {str(e)}"

    def update_db_path(self, new_path: str):
        """Update the database path and recreate well_model"""
        self.db_path = new_path
        if new_path:  # Only create well_model if we have a valid path
            self.well_model = WellModel(new_path)
        else:
            self.well_model = None