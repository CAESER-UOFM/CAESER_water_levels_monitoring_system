#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to add well_statistics table to existing databases
This script should be run once to update all databases.
After running successfully, this script can be deleted.
"""

import os
import sqlite3
import logging
import argparse
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_well_statistics_table(db_path):
    """Add well_statistics table to the database"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if table already exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='well_statistics'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Check if it has the expected columns
                cursor.execute("PRAGMA table_info(well_statistics)")
                columns = {row[1] for row in cursor.fetchall()}
                expected_columns = {'well_number', 'num_points', 'min_timestamp', 'max_timestamp', 'last_update'}
                
                if expected_columns.issubset(columns):
                    logger.info(f"Table well_statistics already exists with expected columns in {db_path}")
                    return True
                else:
                    logger.warning(f"Table well_statistics exists but is missing expected columns in {db_path}")
                    logger.warning(f"Expected: {expected_columns}, Found: {columns}")
                    logger.warning(f"Dropping and recreating the table...")
                    
                    # Drop and recreate the table
                    cursor.execute("DROP TABLE well_statistics")
                    table_exists = False
            
            if not table_exists:
                # Create the well statistics table
                cursor.execute('''
                    CREATE TABLE well_statistics (
                        well_number TEXT PRIMARY KEY,
                        num_points INTEGER DEFAULT 0,
                        min_timestamp TEXT,
                        max_timestamp TEXT,
                        last_update TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (well_number) REFERENCES wells (well_number)
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('''
                    CREATE INDEX idx_well_statistics_well_number
                    ON well_statistics (well_number)
                ''')
                
                logger.info(f"Created well_statistics table in {db_path}")
                
                # Populate the table with current statistics
                logger.info(f"Populating well_statistics with current data...")
                cursor.execute('''
                    INSERT INTO well_statistics (well_number, num_points, min_timestamp, max_timestamp)
                    SELECT 
                        w.well_number,
                        COUNT(l.timestamp_utc) AS num_points,
                        MIN(l.timestamp_utc) AS min_timestamp,
                        MAX(l.timestamp_utc) AS max_timestamp
                    FROM wells w
                    LEFT JOIN water_level_readings l ON w.well_number = l.well_number
                    GROUP BY w.well_number
                ''')
                
                conn.commit()
                logger.info(f"Populated well_statistics table with data for {cursor.rowcount} wells")
            
            return True
            
    except Exception as e:
        logger.error(f"Error adding well_statistics table to {db_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Add well_statistics table to existing databases')
    parser.add_argument('--data_dir', type=str, default='data/databases',
                       help='Directory containing database files')
    parser.add_argument('--single_db', type=str, default=None,
                       help='Single database file to process (optional)')
    
    args = parser.parse_args()
    
    if args.single_db:
        if not os.path.exists(args.single_db):
            logger.error(f"Database file {args.single_db} does not exist")
            return
        
        add_well_statistics_table(args.single_db)
    else:
        if not os.path.exists(args.data_dir):
            logger.error(f"Data directory {args.data_dir} does not exist")
            return
        
        # Find all .db files in the directory
        db_files = list(Path(args.data_dir).glob('*.db'))
        
        if not db_files:
            logger.warning(f"No database files found in {args.data_dir}")
            return
        
        logger.info(f"Found {len(db_files)} database files")
        
        # Process each database file
        for db_file in tqdm(db_files, desc="Processing databases"):
            add_well_statistics_table(str(db_file))
    
    logger.info("Migration completed")

if __name__ == "__main__":
    main() 