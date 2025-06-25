#!/usr/bin/env python3
"""
Quick test to verify manual readings can be fetched from the database.
"""

import sys
import os
import sqlite3
import pandas as pd

# Add the project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def test_manual_readings():
    """Test manual readings retrieval."""
    # Look for databases in the installation databases folder
    from pathlib import Path
    
    installation_root = Path(__file__).parent.parent.parent
    databases_folder = installation_root / "databases"
    
    # Find any .db file
    db_files = []
    if databases_folder.exists():
        db_files = list(databases_folder.glob("*.db"))
    
    # Also check for local test database
    local_test_db = installation_root / "Test.db"
    if local_test_db.exists():
        db_files.append(local_test_db)
    
    if not db_files:
        print("No databases found. Please add a .db file to the databases folder.")
        return
    
    db_path = str(db_files[0])
    print(f"Testing manual readings from: {db_path}")
    if len(db_files) > 1:
        print(f"Note: Found {len(db_files)} databases, using first one")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Get all wells with manual readings
            query = """
                SELECT well_number, COUNT(*) as count
                FROM manual_level_readings
                GROUP BY well_number
                ORDER BY count DESC
            """
            wells_df = pd.read_sql_query(query, conn)
            print(f"\n✅ Found manual readings for {len(wells_df)} wells:")
            for _, row in wells_df.iterrows():
                print(f"   - {row['well_number']}: {row['count']} readings")
            
            # Test specific well TN157_000364 (the one that was selected)
            test_well = "TN157_000364"
            query = """
                SELECT measurement_date_utc, water_level
                FROM manual_level_readings
                WHERE well_number = ?
                ORDER BY measurement_date_utc
            """
            manual_data = pd.read_sql_query(query, conn, params=(test_well,))
            
            if not manual_data.empty:
                manual_data['measurement_date_utc'] = pd.to_datetime(manual_data['measurement_date_utc'])
                print(f"\n✅ Found {len(manual_data)} manual readings for well {test_well}:")
                print(f"   Date range: {manual_data['measurement_date_utc'].min()} to {manual_data['measurement_date_utc'].max()}")
                print(f"   Water level range: {manual_data['water_level'].min():.2f} to {manual_data['water_level'].max():.2f}")
                print(f"   Sample readings:")
                for _, row in manual_data.head(3).iterrows():
                    print(f"     {row['measurement_date_utc']}: {row['water_level']:.2f}")
            else:
                print(f"❌ No manual readings found for well {test_well}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_manual_readings()