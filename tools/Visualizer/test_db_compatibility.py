#!/usr/bin/env python3
"""
Test script to verify database compatibility between the main app's initializer
and the visualizer tool.

This script checks:
1. Database connection
2. Required tables exist
3. Required columns exist in each table
4. Sample queries work as expected
"""

import sys
import sqlite3
import os
from pathlib import Path

# Add parent directories to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

def test_database_compatibility(db_path):
    """Test if the database is compatible with the visualizer"""
    
    print(f"\n=== Testing Database Compatibility ===")
    print(f"Database path: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database file does not exist at {db_path}")
        return False
    
    print(f"✓ Database file exists")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("✓ Successfully connected to database")
        
        # Define required tables and their critical columns
        required_tables = {
            'wells': {
                'required': ['well_number'],
                'optional': ['aquifer', 'cae_number', 'caesar_number', 'latitude', 'longitude', 
                           'data_source', 'top_of_casing', 'wellfield', 'toc']
            },
            'water_level_readings': {
                'required': ['well_number', 'timestamp_utc', 'water_level'],
                'optional': ['temperature', 'julian_timestamp', 'pressure', 'water_pressure',
                           'serial_number', 'baro_flag', 'level_flag']
            },
            'manual_level_readings': {
                'required': ['well_number', 'measurement_date_utc'],
                'optional': ['dtw_avg', 'water_level', 'dtw_1', 'dtw_2', 'tape_error',
                           'comments', 'data_source', 'collected_by', 'is_dry']
            },
            'telemetry_level_readings': {
                'required': ['well_number', 'timestamp_utc', 'water_level'],
                'optional': ['temperature', 'julian_timestamp', 'dtw']
            },
            'barologgers': {
                'required': ['serial_number'],
                'optional': ['location_description', 'installation_date', 'status', 'notes']
            },
            'barometric_readings': {
                'required': ['serial_number', 'timestamp_utc', 'pressure'],
                'optional': ['julian_timestamp', 'temperature', 'quality_flag', 'notes']
            },
            'master_baro_readings': {
                'required': ['timestamp_utc', 'pressure'],
                'optional': ['julian_timestamp', 'temperature', 'source_barologgers', 'notes']
            }
        }
        
        # Check tables exist
        print("\n--- Checking Tables ---")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_tables_ok = True
        for table_name, columns in required_tables.items():
            if table_name in existing_tables:
                print(f"✓ Table '{table_name}' exists")
                
                # Check columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = [col[1] for col in cursor.fetchall()]
                
                # Check required columns
                missing_required = []
                for col in columns['required']:
                    if col not in existing_columns:
                        missing_required.append(col)
                
                if missing_required:
                    print(f"  ❌ Missing required columns: {', '.join(missing_required)}")
                    all_tables_ok = False
                else:
                    print(f"  ✓ All required columns present")
                
                # Check optional columns (informational only)
                missing_optional = []
                for col in columns['optional']:
                    if col not in existing_columns:
                        missing_optional.append(col)
                
                if missing_optional:
                    print(f"  ℹ️  Missing optional columns: {', '.join(missing_optional)}")
                
            else:
                print(f"❌ Table '{table_name}' is MISSING")
                all_tables_ok = False
        
        # Test critical queries used by visualizer
        print("\n--- Testing Critical Queries ---")
        test_queries = [
            ("Wells with readings count", """
                SELECT well_number, 
                       (SELECT COUNT(*) FROM water_level_readings WHERE well_number = wells.well_number) as readings
                FROM wells 
                LIMIT 5
            """),
            ("Water level data sample", """
                SELECT timestamp_utc, water_level, temperature
                FROM water_level_readings
                LIMIT 5
            """),
            ("Manual readings sample", """
                SELECT well_number, measurement_date_utc, water_level
                FROM manual_level_readings
                LIMIT 5
            """),
            ("Telemetry data sample", """
                SELECT timestamp_utc, water_level, temperature
                FROM telemetry_level_readings
                LIMIT 5
            """)
        ]
        
        for query_name, query in test_queries:
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                print(f"✓ Query '{query_name}' executed successfully (returned {len(results)} rows)")
            except sqlite3.Error as e:
                print(f"❌ Query '{query_name}' failed: {e}")
                all_tables_ok = False
        
        # Test SimpleDatabaseManager compatibility
        print("\n--- Testing SimpleDatabaseManager ---")
        try:
            from simple_db_manager import SimpleDatabaseManager
            db_manager = SimpleDatabaseManager(db_path, quick_validation=True)
            print("✓ SimpleDatabaseManager initialized successfully")
            
            # Test basic operation
            test_conn = db_manager.get_connection()
            db_manager.return_connection(test_conn)
            print("✓ Connection pool operations work correctly")
            
            db_manager.close()
        except Exception as e:
            print(f"❌ SimpleDatabaseManager error: {e}")
            all_tables_ok = False
        
        # Test DataManager compatibility
        print("\n--- Testing DataManager ---")
        try:
            from gui.managers.data_manager import DataManager
            data_manager = DataManager(db_path)
            
            # Test getting wells
            wells = data_manager.get_wells()
            print(f"✓ DataManager.get_wells() returned {len(wells)} wells")
            
            # Test getting table schema
            schema = data_manager.get_table_schema('wells')
            print(f"✓ DataManager.get_table_schema('wells') returned {len(schema)} columns")
            
        except Exception as e:
            print(f"❌ DataManager error: {e}")
            all_tables_ok = False
        
        conn.close()
        
        # Summary
        print("\n=== Summary ===")
        if all_tables_ok:
            print("✅ Database is COMPATIBLE with the visualizer")
            return True
        else:
            print("❌ Database has COMPATIBILITY ISSUES with the visualizer")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Failed to test database: {e}")
        return False


def main():
    """Main function to run the compatibility test"""
    
    # Use command line argument if provided
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        print(f"Using command line database: {db_path}")
    else:
        # Look for databases in the configured databases folder
        from pathlib import Path
        
        # Check installation databases folder first
        installation_root = Path(__file__).parent.parent.parent
        databases_folder = installation_root / "databases"
        
        db_files = []
        if databases_folder.exists():
            db_files = list(databases_folder.glob("*.db"))
        
        # Also check for local test database
        local_test_db = installation_root / "T.db"
        if local_test_db.exists():
            db_files.append(local_test_db)
        
        if db_files:
            # Use the first database found
            db_path = str(db_files[0])
            print(f"Found database: {db_path}")
            if len(db_files) > 1:
                print(f"Note: {len(db_files)} databases found, using first one")
        else:
            print("No databases found in the databases folder.")
            print("Please:")
            print("1. Add a .db file to the databases folder, or")
            print("2. Specify a database path as command line argument")
            print("   Example: python test_db_compatibility.py path/to/your/database.db")
            return
    
    # Run the compatibility test
    success = test_database_compatibility(db_path)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()