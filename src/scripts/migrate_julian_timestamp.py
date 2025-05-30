#!/usr/bin/env python
"""
Migration script to add julian_timestamp values to existing records in:
- water_level_readings
- telemetry_level_readings
"""

import sqlite3
import logging
import pandas as pd
from pathlib import Path
import time
import argparse
import sys

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_water_level_readings(db_path: Path, batch_size: int = 10000):
    """Add julian_timestamp values to existing water_level_readings records"""
    logger.info(f"Migrating water_level_readings in {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # First check if there are any records without julian_timestamp
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM water_level_readings 
                WHERE julian_timestamp IS NULL
            """)
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("No water_level_readings records need migration")
                return
                
            logger.info(f"Found {count} water_level_readings records to migrate")
            
            # Process in batches
            processed = 0
            start_time = time.time()
            
            while processed < count:
                # Get a batch of records
                cursor.execute("""
                    SELECT id, timestamp_utc FROM water_level_readings
                    WHERE julian_timestamp IS NULL
                    LIMIT ?
                """, (batch_size,))
                
                records = cursor.fetchall()
                if not records:
                    break
                    
                # Process each record
                updates = []
                for record_id, timestamp_utc in records:
                    # Convert to datetime and calculate julian_timestamp
                    dt = pd.to_datetime(timestamp_utc)
                    julian_timestamp = dt.to_julian_date()
                    updates.append((julian_timestamp, record_id))
                
                # Update in a single transaction
                cursor.executemany("""
                    UPDATE water_level_readings
                    SET julian_timestamp = ?
                    WHERE id = ?
                """, updates)
                
                conn.commit()
                
                processed += len(records)
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                logger.info(f"Processed {processed}/{count} water_level_readings records "
                           f"({processed/count*100:.1f}%, {rate:.1f} records/sec)")
                
            logger.info(f"Migration of water_level_readings completed in {time.time() - start_time:.1f} seconds")
            
    except Exception as e:
        logger.error(f"Error migrating water_level_readings: {e}")
        raise

def migrate_telemetry_readings(db_path: Path, batch_size: int = 10000):
    """Add julian_timestamp values to existing telemetry_level_readings records"""
    logger.info(f"Migrating telemetry_level_readings in {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # First check if there are any records without julian_timestamp
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM telemetry_level_readings 
                WHERE julian_timestamp IS NULL
            """)
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("No telemetry_level_readings records need migration")
                return
                
            logger.info(f"Found {count} telemetry_level_readings records to migrate")
            
            # Process in batches
            processed = 0
            start_time = time.time()
            
            while processed < count:
                # Get a batch of records
                cursor.execute("""
                    SELECT id, timestamp_utc FROM telemetry_level_readings
                    WHERE julian_timestamp IS NULL
                    LIMIT ?
                """, (batch_size,))
                
                records = cursor.fetchall()
                if not records:
                    break
                    
                # Process each record
                updates = []
                for record_id, timestamp_utc in records:
                    # Convert to datetime and calculate julian_timestamp
                    dt = pd.to_datetime(timestamp_utc)
                    julian_timestamp = dt.to_julian_date()
                    updates.append((julian_timestamp, record_id))
                
                # Update in a single transaction
                cursor.executemany("""
                    UPDATE telemetry_level_readings
                    SET julian_timestamp = ?
                    WHERE id = ?
                """, updates)
                
                conn.commit()
                
                processed += len(records)
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                logger.info(f"Processed {processed}/{count} telemetry_level_readings records "
                           f"({processed/count*100:.1f}%, {rate:.1f} records/sec)")
                
            logger.info(f"Migration of telemetry_level_readings completed in {time.time() - start_time:.1f} seconds")
            
    except Exception as e:
        logger.error(f"Error migrating telemetry_level_readings: {e}")
        raise

def main():
    """Main function to run migration"""
    parser = argparse.ArgumentParser(description='Migrate database to add julian_timestamp values')
    parser.add_argument('--db-path', type=str, required=True, help='Path to the database file')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size for processing')
    
    args = parser.parse_args()
    db_path = Path(args.db_path)
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    try:
        migrate_water_level_readings(db_path, args.batch_size)
        migrate_telemetry_readings(db_path, args.batch_size)
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 