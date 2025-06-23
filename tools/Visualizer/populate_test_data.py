#!/usr/bin/env python3
"""
Script to populate the database with test data for visualizer testing.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add the project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def populate_test_data():
    """Populate database with test wells and synthetic water level data."""
    db_path = os.path.join(project_root, "T.db")
    
    print(f"Populating test data in: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, add some test wells from the CSV
        wells_csv = os.path.join(project_root, "Legacy_tables", "wells.csv")
        if os.path.exists(wells_csv):
            wells_df = pd.read_csv(wells_csv)
            # Take first 5 wells for testing
            test_wells = wells_df.head(5)
            
            print(f"Adding {len(test_wells)} test wells...")
            for _, well in test_wells.iterrows():
                # Ensure data_source is valid (transducer or telemetry)
                data_source = well['data_source'] if well['data_source'] in ['transducer', 'telemetry'] else 'transducer'
                
                cursor.execute("""
                    INSERT OR REPLACE INTO wells 
                    (well_number, cae_number, latitude, longitude, top_of_casing, aquifer, data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    well['well_number'],
                    well['cae_number'],
                    well['latitude'],
                    well['longitude'],
                    well['top_of_casing'],
                    well['aquifer'],
                    data_source
                ))
            
            # Generate synthetic water level data for each well
            print("Generating synthetic water level data...")
            
            # Create date range (last 3 months)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            date_range = pd.date_range(start=start_date, end=end_date, freq='6H')
            
            for _, well in test_wells.iterrows():
                well_number = well['well_number']
                
                # Generate synthetic data with seasonal variation
                base_level = 250.0  # Base water level
                seasonal_variation = 5.0 * np.sin(2 * np.pi * np.arange(len(date_range)) / (365 * 4))  # 4 readings per day
                noise = np.random.normal(0, 0.5, len(date_range))  # Random noise
                trend = -0.01 * np.arange(len(date_range))  # Slight declining trend
                
                water_levels = base_level + seasonal_variation + noise + trend
                temperatures = 15 + 5 * np.sin(2 * np.pi * np.arange(len(date_range)) / (365 * 4)) + np.random.normal(0, 1, len(date_range))
                
                # Insert water level readings
                for i, (timestamp, level, temp) in enumerate(zip(date_range, water_levels, temperatures)):
                    cursor.execute("""
                        INSERT INTO water_level_readings 
                        (well_number, timestamp_utc, water_level, temperature, serial_number, processing_date_utc)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        well_number,
                        timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        round(level, 2),
                        round(temp, 1),
                        'TEST_SENSOR',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                
                print(f"  Added {len(date_range)} readings for well {well_number}")
        
        conn.commit()
        conn.close()
        
        print("✅ Test data populated successfully!")
        
        # Verify the data
        verify_test_data()
        
    except Exception as e:
        print(f"❌ Error populating test data: {e}")

def verify_test_data():
    """Verify that test data was added correctly."""
    db_path = os.path.join(project_root, "T.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check wells
        cursor.execute("SELECT COUNT(*) FROM wells")
        well_count = cursor.fetchone()[0]
        print(f"Wells in database: {well_count}")
        
        # Check water level readings
        cursor.execute("SELECT COUNT(*) FROM water_level_readings")
        reading_count = cursor.fetchone()[0]
        print(f"Water level readings: {reading_count}")
        
        # Sample data
        cursor.execute("""
            SELECT well_number, COUNT(*) as reading_count 
            FROM water_level_readings 
            GROUP BY well_number
        """)
        wells_with_data = cursor.fetchall()
        
        print("Wells with data:")
        for well, count in wells_with_data:
            print(f"  {well}: {count} readings")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verifying test data: {e}")

if __name__ == "__main__":
    populate_test_data()