#!/usr/bin/env python3
"""
Simple test to check database write access.
"""

import sqlite3
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(project_root, "T.db")

print(f"Testing database write access: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")
print(f"File size: {os.path.getsize(db_path) if os.path.exists(db_path) else 'N/A'} bytes")

try:
    # Test simple connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test that we can read
    cursor.execute("SELECT COUNT(*) FROM wells")
    well_count = cursor.fetchone()[0]
    print(f"Can read: {well_count} wells in database")
    
    # Test WAL mode (maybe the issue is journal mode)
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0]
    print(f"Journal mode: {journal_mode}")
    
    # Try to set to DELETE mode for testing
    cursor.execute("PRAGMA journal_mode=DELETE")
    new_mode = cursor.fetchone()[0]
    print(f"Changed journal mode to: {new_mode}")
    
    # Test simple write
    cursor.execute("SELECT COUNT(*) FROM wells WHERE well_number = 'TEST123'")
    test_count = cursor.fetchone()[0]
    
    if test_count == 0:
        cursor.execute("INSERT INTO wells (well_number, cae_number, data_source) VALUES ('TEST123', 'TEST', 'test')")
        print("✅ Successfully inserted test well")
    else:
        print("Test well already exists")
    
    conn.commit()
    conn.close()
    print("✅ Database write test successful")
    
except Exception as e:
    print(f"❌ Database write test failed: {e}")
    print(f"Error type: {type(e).__name__}")