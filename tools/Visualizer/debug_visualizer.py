#!/usr/bin/env python3
"""
Debug script to test the visualizer loading issues.
This script will test the database connection and data loading.
"""

import sys
import os
import logging
from pathlib import Path

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connection and queries."""
    
    # Test database path - use T.db from project root
    # Current file is in tools/Visualizer, so go up two levels to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    default_db_path = os.path.join(project_root, "T.db")
    
    # Check if database exists
    if not os.path.exists(default_db_path):
        print(f"❌ Database not found at: {default_db_path}")
        return False
    
    print(f"✅ Database found at: {default_db_path}")
    
    try:
        # Test basic SQLite connection
        import sqlite3
        conn = sqlite3.connect(default_db_path)
        cursor = conn.cursor()
        
        # Test if we can read from wells table
        cursor.execute("SELECT COUNT(*) FROM wells")
        well_count = cursor.fetchone()[0]
        print(f"✅ Wells table found with {well_count} wells")
        
        # Test if we can read from water_level_readings table
        cursor.execute("SELECT COUNT(*) FROM water_level_readings")
        reading_count = cursor.fetchone()[0]
        print(f"✅ Water level readings table found with {reading_count} readings")
        
        # Test a simple join
        cursor.execute("""
            SELECT w.well_number, COUNT(r.id) as reading_count
            FROM wells w
            LEFT JOIN water_level_readings r ON w.well_number = r.well_number
            GROUP BY w.well_number
            HAVING reading_count > 0
            LIMIT 5
        """)
        wells_with_data = cursor.fetchall()
        print(f"✅ Found {len(wells_with_data)} wells with data (showing first 5):")
        for well_num, count in wells_with_data:
            print(f"   - {well_num}: {count} readings")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_data_manager():
    """Test the DataManager class."""
    try:
        from gui.managers.data_manager import DataManager
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        default_db_path = os.path.join(project_root, "T.db")
        if not os.path.exists(default_db_path):
            print("❌ Database not found for DataManager test")
            return False
            
        print("Testing DataManager...")
        data_manager = DataManager(default_db_path)
        
        # Test getting wells with data
        wells_data = data_manager.get_wells_with_data()
        print(f"✅ DataManager found {len(wells_data)} wells with data")
        
        if wells_data:
            # Test getting data for the first well
            first_well = wells_data[0][0]  # well_number is first element of tuple
            print(f"Testing data retrieval for well: {first_well}")
            
            well_data = data_manager.get_well_data(first_well)
            print(f"✅ Retrieved {len(well_data)} data points for well {first_well}")
            
            return True
        else:
            print("❌ No wells with data found")
            return False
            
    except Exception as e:
        print(f"❌ DataManager error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_db_manager():
    """Test the SimpleDatabaseManager class."""
    try:
        from simple_db_manager import SimpleDatabaseManager
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        default_db_path = os.path.join(project_root, "T.db")
        if not os.path.exists(default_db_path):
            print("❌ Database not found for SimpleDatabaseManager test")
            return False
            
        print("Testing SimpleDatabaseManager...")
        db_manager = SimpleDatabaseManager(default_db_path, quick_validation=True)
        
        # Test if it initializes properly
        print(f"✅ SimpleDatabaseManager initialized for: {db_manager.current_db}")
        return True
        
    except Exception as e:
        print(f"❌ SimpleDatabaseManager error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🔍 Debugging Water Level Visualizer Loading Issues")
    print("=" * 60)
    
    # Test 1: Basic database connection
    print("\n1. Testing database connection...")
    db_ok = test_database_connection()
    
    # Test 2: SimpleDatabaseManager
    print("\n2. Testing SimpleDatabaseManager...")
    simple_db_ok = test_simple_db_manager()
    
    # Test 3: DataManager
    print("\n3. Testing DataManager...")
    data_manager_ok = test_data_manager()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Database Connection: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"SimpleDatabaseManager: {'✅ PASS' if simple_db_ok else '❌ FAIL'}")
    print(f"DataManager: {'✅ PASS' if data_manager_ok else '❌ FAIL'}")
    
    if all([db_ok, simple_db_ok, data_manager_ok]):
        print("\n🎉 All tests passed! The issue might be in the GUI components.")
        print("Possible issues to check:")
        print("- Plot handler initialization")
        print("- Qt event loop issues")
        print("- Well selection not triggering plot updates")
        print("- Signal/slot connections")
    else:
        print("\n❌ Some tests failed. Fix database/data manager issues first.")

if __name__ == "__main__":
    main()