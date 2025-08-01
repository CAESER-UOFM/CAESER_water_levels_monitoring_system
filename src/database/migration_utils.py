# -*- coding: utf-8 -*-
"""
Database Migration Utilities

Provides utilities for migrating older databases to newer schemas.
This ensures backward compatibility when new tables or columns are added.

@author: claude
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Callable

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """Handles database schema migrations for backward compatibility"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        
    def check_and_migrate(self) -> bool:
        """
        Check database schema and apply any necessary migrations.
        
        Returns:
            True if migrations were successful or not needed, False if errors occurred
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # List of migrations to check and apply
                migrations = [
                    self._migrate_user_notes_table,
                    self._migrate_temperature_spike_flag,
                    # Add more migrations here as needed
                ]
                
                for migration in migrations:
                    try:
                        if migration(cursor):
                            logger.info(f"Applied migration: {migration.__name__}")
                        else:
                            logger.debug(f"Migration not needed: {migration.__name__}")
                    except Exception as e:
                        logger.error(f"Error in migration {migration.__name__}: {e}")
                        return False
                
                conn.commit()
                logger.info("Database migration check completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error during database migration: {e}")
            return False
    
    def _migrate_user_notes_table(self, cursor: sqlite3.Cursor) -> bool:
        """
        Create user_notes table if it doesn't exist (for databases created before this feature).
        
        Returns:
            True if table was created, False if it already existed
        """
        try:
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='user_notes'
            """)
            
            if cursor.fetchone():
                return False  # Table already exists
            
            # Create the user_notes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    well_number TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    note_text TEXT NOT NULL,
                    time_range_type TEXT CHECK(time_range_type IN ('full', 'specific')) NOT NULL,
                    time_range_start TIMESTAMP,
                    time_range_end TIMESTAMP,
                    timestamp_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (well_number) REFERENCES wells (well_number)
                )
            ''')
            
            # Create index for efficient queries by well and creation time
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_notes_well_time 
                ON user_notes (well_number, created_at DESC)
            ''')
            
            logger.info("Created user_notes table for older database")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user_notes table: {e}")
            raise
    
    def _migrate_temperature_spike_flag(self, cursor: sqlite3.Cursor) -> bool:
        """
        Add temperature_spike_flag column to water_level_readings table if it doesn't exist.
        
        Returns:
            True if column was added, False if already exists
        """
        try:
            # Check if the column already exists
            cursor.execute("PRAGMA table_info(water_level_readings)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'temperature_spike_flag' in columns:
                return False  # Column already exists
            
            # Add the column
            cursor.execute('''
                ALTER TABLE water_level_readings 
                ADD COLUMN temperature_spike_flag TEXT DEFAULT 'none'
            ''')
            
            logger.info("Added temperature_spike_flag column to water_level_readings table")
            return True
            
        except Exception as e:
            logger.error(f"Error adding temperature_spike_flag column: {e}")
            raise
    
    def get_missing_tables(self) -> List[str]:
        """
        Get a list of tables that are missing from the current database schema.
        
        Returns:
            List of missing table names
        """
        missing_tables = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # List of tables that should exist in current schema
                expected_tables = [
                    'wells',
                    'well_flag_changes',
                    'user_notes',  # This is the one that might be missing
                    'transducers',
                    'water_level_readings',
                    'manual_level_readings',
                    # Add more as needed
                ]
                
                for table_name in expected_tables:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table_name,))
                    
                    if not cursor.fetchone():
                        missing_tables.append(table_name)
                        
        except Exception as e:
            logger.error(f"Error checking for missing tables: {e}")
            
        return missing_tables
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a specific table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False

def migrate_database(db_path: str) -> bool:
    """
    Convenience function to migrate a database.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if migration was successful, False otherwise
    """
    migration = DatabaseMigration(db_path)
    return migration.check_and_migrate()