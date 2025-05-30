"""
Handler for well data operations and utilities.
"""

import sqlite3
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class WellDataHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._well_cache = {}

    def get_well_info(self, well_number: str) -> Dict:
        """Get well information with caching to reduce database queries"""
        if well_number not in self._well_cache:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM wells WHERE well_number = ?", (well_number,))
                result = cursor.fetchone()
                if result:
                    # Convert to dictionary using column names
                    columns = [description[0] for description in cursor.description]
                    self._well_cache[well_number] = dict(zip(columns, result))
                else:
                    self._well_cache[well_number] = None
        return self._well_cache[well_number]

    def get_well_mapping(self) -> Dict[str, str]:
        """Get mapping of CAE numbers and well numbers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT well_number, cae_number 
                    FROM wells 
                    WHERE cae_number IS NOT NULL
                """)
                # Create both direct and normalized mappings
                mappings = {}
                for wn, cae in cursor.fetchall():
                    # Store original
                    mappings[cae] = wn
                    # Store without spaces
                    mappings[cae.replace(" ", "")] = wn
                    # Store uppercase
                    mappings[cae.upper()] = wn
                    mappings[cae.upper().replace(" ", "")] = wn
                return mappings
        except Exception as e:
            logger.error(f"Error getting well mapping: {e}")
            return {}

    def match_well_location(self, location: str, mapping: Dict[str, str]) -> Optional[str]:
        """Try to match location to a well number"""
        # Try direct match
        if location in mapping:
            return mapping[location]
        
        # Try normalized
        normalized = location.upper().replace(" ", "")
        if normalized in mapping:
            return mapping[normalized]
        
        return None

    def check_transducer_status(self, serial_number: str, well_number: str) -> Dict:
        """Check transducer status against database using UTC timestamps"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if transducer exists
                cursor.execute("""
                    SELECT well_number, installation_date, end_date
                    FROM transducers 
                    WHERE serial_number = ?
                    ORDER BY installation_date DESC 
                    LIMIT 1
                """, (serial_number,))
                
                result = cursor.fetchone()
                
                if not result:
                    return {
                        'status': 'warning',
                        'message': f"Transducer {serial_number} not found in database. "
                                 "Do you want to register it?",
                        'details': {'action': 'register_new'}
                    }
                
                current_well, install_date, end_date = result
                
                # Check if transducer is assigned to this well
                if current_well != well_number:
                    return {
                        'status': 'error',
                        'message': f"Transducer {serial_number} is currently assigned to well {current_well}. "
                                 "Please verify transducer assignment.",
                        'details': {
                            'current_well': current_well,
                            'install_date': install_date
                        }
                    }
                
                # Check if transducer was removed from well
                if end_date is not None:
                    return {
                        'status': 'warning',
                        'message': f"Transducer {serial_number} was marked as removed from {well_number} "
                                 f"on {end_date}. Do you want to update its status?",
                        'details': {
                            'end_date': end_date,
                            'action': 'update_status'
                        }
                    }
                
                # All checks passed
                return {
                    'status': 'ok',
                    'message': "Transducer assignment verified",
                    'details': {
                        'well_number': well_number,
                        'install_date': install_date
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Database error: {str(e)}",
                'details': None
            }

    def clear_cache(self):
        """Clear the well information cache"""
        self._well_cache.clear()

    def update_db_path(self, new_path: str):
        """Update the database path and clear cache"""
        self.db_path = new_path
        self.clear_cache() 