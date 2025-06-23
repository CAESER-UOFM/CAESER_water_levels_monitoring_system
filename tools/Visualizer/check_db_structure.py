#!/usr/bin/env python3
"""
Quick script to check database structure and find where water level data is stored.
"""

import sqlite3
import os
import sys

# Add the project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def check_database_structure(db_path):
    """Check the database structure to find water level data tables."""
    print(f"Checking database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"\n✅ Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} rows")
            
            # Check if this might be a water level table
            if 'water' in table_name.lower() or 'level' in table_name.lower() or 'reading' in table_name.lower():
                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"     Columns: {', '.join([col[1] for col in columns])}")
        
        # Check specific wells table structure
        print("\n📊 Wells table structure:")
        cursor.execute("PRAGMA table_info(wells)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
            
        # Try to find water level data
        print("\n🔍 Looking for water level data...")
        
        # Check different possible table names
        possible_tables = [
            'water_level_readings',
            'transducer_level_readings', 
            'telemetry_level_readings',
            'manual_level_readings',
            'water_levels',
            'readings'
        ]
        
        for table in possible_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"   ✅ Found data in {table}: {count} rows")
                    # Get sample well numbers
                    cursor.execute(f"SELECT DISTINCT well_number FROM {table} LIMIT 5")
                    wells = cursor.fetchall()
                    print(f"      Sample wells: {', '.join([w[0] for w in wells])}")
            except sqlite3.OperationalError:
                pass
                
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    # Use Test.db from the actual testing location
    db_path = "/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/dbs_test/Test.db"
    check_database_structure(db_path)