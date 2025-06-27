"""
Database manager for RISE calculation storage.
Handles saving and retrieving RISE method calculations from the main database.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class RiseDatabase:
    """Database manager for RISE calculation storage."""
    
    def __init__(self, db_path):
        """
        Initialize the RISE database manager.
        
        Args:
            db_path: Path to the main SQLite database file
        """
        self.db_path = str(db_path)
        
    def get_connection(self):
        """
        Create a read-write connection to the database.
        
        Returns:
            sqlite3.Connection: Database connection configured for read-write operations
        """
        conn = sqlite3.connect(self.db_path)
        # Configure for read-write operations with reasonable performance
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA cache_size = -10000')  # 10MB cache
        return conn
    
    def create_tables(self):
        """
        Create the RISE calculations table if it doesn't exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create the main RISE calculations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rise_calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    well_number TEXT NOT NULL,
                    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parameters TEXT NOT NULL,
                    events_data TEXT NOT NULL,
                    yearly_summary TEXT NOT NULL,
                    total_recharge REAL NOT NULL,
                    total_events INTEGER NOT NULL,
                    annual_rate REAL NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (well_number) REFERENCES wells (well_number)
                )
            ''')
            
            # Create index for faster well lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_rise_calculations_well 
                ON rise_calculations (well_number)
            ''')
            
            # Create index for date-based queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_rise_calculations_date 
                ON rise_calculations (calculation_date)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("RISE calculations table created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating RISE tables: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def save_calculation(self, well_number, parameters, events, yearly_summary, 
                        total_recharge, annual_rate, notes=None):
        """
        Save a RISE calculation to the database.
        
        Args:
            well_number (str): Well identifier
            parameters (dict): Calculation parameters (specific yield, threshold, etc.)
            events (list): List of rise events
            yearly_summary (list): Yearly statistics
            total_recharge (float): Total recharge in inches
            annual_rate (float): Annual recharge rate
            notes (str, optional): Additional notes
            
        Returns:
            int or None: Calculation ID if successful, None otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert complex data to JSON strings
            parameters_json = json.dumps(parameters)
            events_json = json.dumps(events, default=str)  # Handle datetime objects
            yearly_json = json.dumps(yearly_summary)
            
            # Insert the calculation
            cursor.execute('''
                INSERT INTO rise_calculations 
                (well_number, parameters, events_data, yearly_summary, 
                 total_recharge, total_events, annual_rate, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                well_number,
                parameters_json,
                events_json,
                yearly_json,
                total_recharge,
                len(events),
                annual_rate,
                notes
            ))
            
            calculation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Saved RISE calculation {calculation_id} for well {well_number}")
            return calculation_id
            
        except Exception as e:
            logger.error(f"Error saving RISE calculation: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return None
    
    def get_calculations_for_well(self, well_number):
        """
        Get all RISE calculations for a specific well.
        
        Args:
            well_number (str): Well identifier
            
        Returns:
            list: List of calculation records
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, calculation_date, parameters, events_data, yearly_summary,
                       total_recharge, total_events, annual_rate, notes, created_at
                FROM rise_calculations
                WHERE well_number = ?
                ORDER BY calculation_date DESC
            ''', (well_number,))
            
            calculations = []
            for row in cursor.fetchall():
                calc_id, calc_date, params_json, events_json, yearly_json, \
                total_recharge, total_events, annual_rate, notes, created_at = row
                
                # Parse JSON data
                parameters = json.loads(params_json)
                events = json.loads(events_json)
                yearly_summary = json.loads(yearly_json)
                
                calculations.append({
                    'id': calc_id,
                    'calculation_date': calc_date,
                    'parameters': parameters,
                    'events': events,
                    'yearly_summary': yearly_summary,
                    'total_recharge': total_recharge,
                    'total_events': total_events,
                    'annual_rate': annual_rate,
                    'notes': notes,
                    'created_at': created_at
                })
            
            conn.close()
            return calculations
            
        except Exception as e:
            logger.error(f"Error retrieving calculations for well {well_number}: {e}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def delete_calculation(self, calculation_id):
        """
        Delete a RISE calculation.
        
        Args:
            calculation_id (int): Calculation ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM rise_calculations WHERE id = ?', (calculation_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted RISE calculation {calculation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting calculation {calculation_id}: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def check_existing_calculations(self, well_number):
        """
        Check if a well has existing RISE calculations.
        
        Args:
            well_number (str): Well identifier
            
        Returns:
            dict: Information about existing calculations
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*), MAX(calculation_date), MAX(total_recharge)
                FROM rise_calculations
                WHERE well_number = ?
            ''', (well_number,))
            
            count, last_date, last_recharge = cursor.fetchone()
            
            conn.close()
            
            return {
                'has_calculations': count > 0,
                'count': count,
                'last_calculation_date': last_date,
                'last_total_recharge': last_recharge
            }
            
        except Exception as e:
            logger.error(f"Error checking existing calculations for well {well_number}: {e}")
            if 'conn' in locals():
                conn.close()
            return {'has_calculations': False, 'count': 0}
    
    def get_calculation_details(self, calculation_id):
        """
        Get detailed information for a specific calculation.
        
        Args:
            calculation_id (int): Calculation ID
            
        Returns:
            dict: Calculation details or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT well_number, calculation_date, parameters, events_data, yearly_summary,
                       total_recharge, total_events, annual_rate, notes, created_at
                FROM rise_calculations
                WHERE id = ?
            ''', (calculation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            well_number, calc_date, params_json, events_json, yearly_json, \
            total_recharge, total_events, annual_rate, notes, created_at = row
            
            # Parse JSON data
            parameters = json.loads(params_json)
            events = json.loads(events_json)
            yearly_summary = json.loads(yearly_json)
            
            # Flatten parameters for easy access
            calc_details = {
                'id': calculation_id,
                'well_number': well_number,
                'calculation_date': calc_date,
                'total_recharge': total_recharge,
                'total_events': total_events,
                'annual_rate': annual_rate,
                'notes': notes,
                'created_at': created_at,
                'rise_events': events,
                'yearly_summaries': yearly_summary
            }
            
            # Add individual parameters for easy access
            calc_details.update(parameters)
            
            conn.close()
            return calc_details
            
        except Exception as e:
            logger.error(f"Error getting calculation details for ID {calculation_id}: {e}")
            if 'conn' in locals():
                conn.close()
            return None