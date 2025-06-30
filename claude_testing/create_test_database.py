#!/usr/bin/env python3
"""
Create a minimal test database for recharge calculation testing.
This creates a SQLite database with one well and synthetic but realistic data.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_database(db_path):
    """Create a minimal test database with one well's data."""
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database: {db_path}")
    
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create wells table
        cursor.execute('''
            CREATE TABLE wells (
                well_number TEXT PRIMARY KEY,
                cae_number TEXT,
                latitude REAL,
                longitude REAL,
                top_of_casing REAL,
                aquifer TEXT,
                min_distance_to_stream REAL,
                well_field TEXT,
                cluster TEXT,
                county TEXT,
                picture_path TEXT DEFAULT 'default_well.jpg',
                data_source TEXT CHECK(data_source IN ('transducer', 'telemetry')),
                url TEXT,
                user_flag TEXT CHECK(user_flag IN ('unchecked', 'error', 'approved')) DEFAULT 'unchecked',
                baro_status TEXT CHECK(baro_status IN ('no_data','all_master','has_non_master')) DEFAULT 'no_data',
                level_status TEXT CHECK(level_status IN ('no_data','default_level','no_default')) DEFAULT 'no_data',
                parking_instructions TEXT,
                access_requirements TEXT,
                safety_notes TEXT,
                special_instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create water_level_readings table
        cursor.execute('''
            CREATE TABLE water_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                pressure REAL,
                water_pressure REAL,
                water_level REAL,
                temperature REAL,
                serial_number TEXT,
                baro_flag TEXT,
                level_flag TEXT,
                processing_date_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number),
                UNIQUE (well_number, timestamp_utc)
            )
        ''')
        
        # Create master_baro_readings table
        cursor.execute('''
            CREATE TABLE master_baro_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                pressure REAL,
                temperature REAL,
                source_barologgers TEXT,
                processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # Create transducers table
        cursor.execute('''
            CREATE TABLE transducers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT UNIQUE,
                well_number TEXT,
                installation_date TIMESTAMP,
                end_date TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # Create manual_level_readings table
        cursor.execute('''
            CREATE TABLE manual_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                measurement_date_utc TIMESTAMP,
                dtw_avg REAL,
                dtw_1 REAL,
                dtw_2 REAL,
                tape_error REAL,
                comments TEXT,
                water_level REAL,
                data_source TEXT,
                collected_by TEXT,
                is_dry BOOLEAN DEFAULT 0,
                FOREIGN KEY (well_number) REFERENCES wells (well_number),
                UNIQUE(well_number, measurement_date_utc)
            )
        ''')
        
        # Create performance indexes
        cursor.execute('CREATE INDEX idx_water_levels_well_time ON water_level_readings(well_number, julian_timestamp)')
        cursor.execute('CREATE INDEX idx_baro_time ON master_baro_readings(julian_timestamp)')
        cursor.execute('CREATE INDEX idx_manual_well_time ON manual_level_readings(well_number, measurement_date_utc)')
        
        logger.info("Created database tables and indexes")
        
        # Insert test well data
        well_data = {
            'well_number': 'TEST_001',
            'cae_number': 'T001',
            'latitude': 35.100331,
            'longitude': -90.03924,
            'top_of_casing': 295.07,
            'aquifer': 'SHAL',
            'min_distance_to_stream': 1.2,
            'well_field': 'Memphis',
            'cluster': 'Test Cluster',
            'county': 'Shelby',
            'data_source': 'transducer',
            'user_flag': 'approved',
            'baro_status': 'all_master',
            'level_status': 'default_level'
        }
        
        cursor.execute('''
            INSERT INTO wells (well_number, cae_number, latitude, longitude, top_of_casing, 
                             aquifer, min_distance_to_stream, well_field, cluster, county, 
                             data_source, user_flag, baro_status, level_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            well_data['well_number'], well_data['cae_number'], well_data['latitude'], 
            well_data['longitude'], well_data['top_of_casing'], well_data['aquifer'],
            well_data['min_distance_to_stream'], well_data['well_field'], 
            well_data['cluster'], well_data['county'], well_data['data_source'],
            well_data['user_flag'], well_data['baro_status'], well_data['level_status']
        ))
        
        # Insert transducer data
        cursor.execute('''
            INSERT INTO transducers (serial_number, well_number, installation_date, notes)
            VALUES (?, ?, ?, ?)
        ''', ('TN157_TEST001', 'TEST_001', '2024-01-01 00:00:00', 'Test transducer'))
        
        logger.info("Inserted well and transducer data")
        
        # Generate realistic water level time series data
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        # Generate 6-hourly timestamps
        timestamps = []
        current = start_date
        while current <= end_date:
            timestamps.append(current)
            current += timedelta(hours=6)
        
        logger.info(f"Generating {len(timestamps)} water level readings...")
        
        # Create realistic water level data with recharge events
        base_level = 250.0  # Base water level (feet above MSL)
        seasonal_amplitude = 2.0  # Seasonal variation
        noise_level = 0.1  # Random noise
        
        water_levels = []
        for i, timestamp in enumerate(timestamps):
            # Seasonal component (lowest in fall, highest in spring)
            day_of_year = timestamp.timetuple().tm_yday
            seasonal = seasonal_amplitude * np.sin(2 * np.pi * (day_of_year - 60) / 365.25)
            
            # Add some recharge events (sharp rises)
            recharge_events = 0
            if day_of_year in [50, 120, 180, 250, 320]:  # 5 recharge events per year
                recharge_events = np.random.uniform(0.3, 0.8)  # 0.3-0.8 ft rises
            
            # Random noise
            noise = np.random.normal(0, noise_level)
            
            # Combine components
            level = base_level + seasonal + recharge_events + noise
            water_levels.append(level)
        
        # Apply some smoothing to make gradual changes
        water_levels = pd.Series(water_levels).rolling(window=3, center=True).mean().fillna(method='bfill').fillna(method='ffill')
        
        # Insert water level readings
        water_level_data = []
        for i, (timestamp, water_level) in enumerate(zip(timestamps, water_levels)):
            # Convert to julian timestamp
            julian_ts = timestamp.timestamp()
            
            # Calculate synthetic pressure values
            # Assuming transducer at ~45ft depth below TOC
            depth_to_transducer = 45.0
            transducer_elevation = well_data['top_of_casing'] - depth_to_transducer
            depth_to_water = well_data['top_of_casing'] - water_level
            water_column_height = depth_to_transducer - depth_to_water
            
            # Water pressure (psi): 1 ft water = 0.433 psi
            water_pressure = water_column_height * 0.433 if water_column_height > 0 else 0
            
            # Total pressure (add atmospheric ~14.7 psi)
            atmospheric_pressure = 14.7 + np.random.normal(0, 0.1)
            total_pressure = atmospheric_pressure + water_pressure
            
            # Temperature (seasonal variation)
            temp_base = 60  # Base temperature (°F)
            temp_seasonal = 10 * np.sin(2 * np.pi * timestamp.timetuple().tm_yday / 365.25)
            temperature = temp_base + temp_seasonal + np.random.normal(0, 2)
            
            water_level_data.append((
                well_data['well_number'],
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                julian_ts,
                total_pressure,
                water_pressure,
                water_level,
                temperature,
                'TN157_TEST001',
                'corrected',
                'good'
            ))
        
        # Batch insert water level data
        cursor.executemany('''
            INSERT INTO water_level_readings 
            (well_number, timestamp_utc, julian_timestamp, pressure, water_pressure, 
             water_level, temperature, serial_number, baro_flag, level_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', water_level_data)
        
        logger.info(f"Inserted {len(water_level_data)} water level readings")
        
        # Generate barometric pressure data (15-minute intervals)
        baro_timestamps = []
        current = start_date
        while current <= end_date:
            baro_timestamps.append(current)
            current += timedelta(minutes=15)
        
        logger.info(f"Generating {len(baro_timestamps)} barometric readings...")
        
        # Generate realistic barometric pressure data
        baro_data = []
        base_pressure = 29.92  # Base atmospheric pressure (inHg)
        
        for timestamp in baro_timestamps:
            # Realistic barometric pressure variation
            pressure_variation = np.random.normal(0, 0.3)  # Weather variations
            daily_cycle = 0.05 * np.sin(2 * np.pi * timestamp.hour / 24)  # Small daily cycle
            pressure = base_pressure + pressure_variation + daily_cycle
            
            # Temperature variation
            temp_base = 65  # Base temperature (°F)
            temp_seasonal = 20 * np.sin(2 * np.pi * timestamp.timetuple().tm_yday / 365.25)
            temp_daily = 15 * np.sin(2 * np.pi * (timestamp.hour - 6) / 24)
            temperature = temp_base + temp_seasonal + temp_daily + np.random.normal(0, 3)
            
            baro_data.append((
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                timestamp.timestamp(),
                pressure,
                temperature,
                '["2100114", "2100118"]'  # JSON array of source barologgers
            ))
        
        # Batch insert barometric data
        cursor.executemany('''
            INSERT INTO master_baro_readings 
            (timestamp_utc, julian_timestamp, pressure, temperature, source_barologgers)
            VALUES (?, ?, ?, ?, ?)
        ''', baro_data)
        
        logger.info(f"Inserted {len(baro_data)} barometric readings")
        
        # Add a few manual level readings for validation
        manual_readings = [
            ('2024-03-15 10:00:00', 45.1, 45.0, 45.2, 0.0, 249.97, 'Spring measurement'),
            ('2024-06-15 14:00:00', 44.8, 44.7, 44.9, 0.0, 250.27, 'Summer measurement'),
            ('2024-09-15 11:00:00', 45.5, 45.4, 45.6, 0.0, 249.57, 'Fall measurement'),
            ('2024-12-15 09:00:00', 45.2, 45.1, 45.3, 0.0, 249.87, 'Winter measurement')
        ]
        
        for date, dtw_avg, dtw_1, dtw_2, tape_error, water_level, comments in manual_readings:
            cursor.execute('''
                INSERT INTO manual_level_readings 
                (well_number, measurement_date_utc, dtw_avg, dtw_1, dtw_2, tape_error, 
                 water_level, comments, data_source, collected_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('TEST_001', date, dtw_avg, dtw_1, dtw_2, tape_error, water_level, 
                  comments, 'manual', 'Test Technician'))
        
        logger.info("Inserted manual level readings")
        
        # Commit all changes
        conn.commit()
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM wells")
        well_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM water_level_readings")
        water_level_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM master_baro_readings")
        baro_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM manual_level_readings")
        manual_count = cursor.fetchone()[0]
        
        logger.info(f"Database created successfully:")
        logger.info(f"  Wells: {well_count}")
        logger.info(f"  Water level readings: {water_level_count}")
        logger.info(f"  Barometric readings: {baro_count}")
        logger.info(f"  Manual readings: {manual_count}")
        
        # Test data quality
        cursor.execute('''
            SELECT MIN(water_level), MAX(water_level), AVG(water_level) 
            FROM water_level_readings WHERE well_number = 'TEST_001'
        ''')
        min_level, max_level, avg_level = cursor.fetchone()
        
        logger.info(f"Water level statistics:")
        logger.info(f"  Min: {min_level:.2f} ft")
        logger.info(f"  Max: {max_level:.2f} ft")
        logger.info(f"  Average: {avg_level:.2f} ft")
        logger.info(f"  Range: {max_level - min_level:.2f} ft")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False
    
    finally:
        conn.close()

def main():
    """Main function to create test database."""
    # Define database path
    db_path = os.path.join(os.path.dirname(__file__), 'test_database.db')
    
    logger.info(f"Creating test database: {db_path}")
    
    success = create_test_database(db_path)
    
    if success:
        logger.info("✅ Test database created successfully!")
        logger.info(f"Database location: {db_path}")
        logger.info("Ready for recharge calculation testing.")
    else:
        logger.error("❌ Failed to create test database")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())