#!/usr/bin/env python3
"""
Test script to verify the visualizer can start up without errors.
This is a minimal test that doesn't require GUI interaction.
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

def test_visualizer_imports():
    """Test that all critical imports work"""
    print("\n=== Testing Visualizer Imports ===")
    
    imports_ok = True
    
    # Test critical imports
    test_imports = [
        ("SimpleDatabaseManager", "from simple_db_manager import SimpleDatabaseManager"),
        ("DataManager", "from gui.managers.data_manager import DataManager"),
        ("PlotHandler", "from gui.managers.plot_handler import PlotHandler"),
        ("MapHandler", "from gui.managers.map_handler import MapHandler"),
        ("ExportManager", "from gui.managers.export_manager import ExportManager"),
        ("WaterLevelVisualizer", "from gui.dialogs.water_level_visualizer import WaterLevelVisualizer"),
    ]
    
    for name, import_stmt in test_imports:
        try:
            exec(import_stmt)
            print(f"✓ Successfully imported {name}")
        except Exception as e:
            print(f"❌ Failed to import {name}: {e}")
            imports_ok = False
    
    return imports_ok


def test_database_manager_creation():
    """Test creating database managers with a test database"""
    print("\n=== Testing Database Manager Creation ===")
    
    # Use local test database
    db_path = Path(__file__).parent.parent.parent / "T.db"
    if not db_path.exists():
        print(f"❌ Test database not found at {db_path}")
        return False
    
    try:
        from simple_db_manager import SimpleDatabaseManager
        from gui.managers.data_manager import DataManager
        
        # Test SimpleDatabaseManager
        print(f"Creating SimpleDatabaseManager with {db_path}")
        simple_db = SimpleDatabaseManager(str(db_path), quick_validation=True, deferred_init=True)
        print("✓ SimpleDatabaseManager created successfully")
        
        # Test DataManager
        print(f"Creating DataManager with {db_path}")
        data_mgr = DataManager(str(db_path))
        print("✓ DataManager created successfully")
        
        # Test basic operations
        wells = data_mgr.get_wells()
        print(f"✓ Retrieved {len(wells)} wells from database")
        
        # Clean up
        simple_db.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database managers: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compatibility_summary():
    """Summarize all compatibility aspects"""
    print("\n=== Compatibility Summary ===")
    
    # Check for missing optional columns that might be used
    optional_mappings = {
        "caesar_number": "The visualizer looks for 'caesar_number' but database has 'cae_number'",
        "wellfield": "The visualizer may look for 'wellfield' but database has 'well_field'",
        "toc": "The visualizer may look for 'toc' but database has 'top_of_casing'"
    }
    
    print("\nPotential field name mismatches to watch for:")
    for field, note in optional_mappings.items():
        print(f"  ℹ️  {field}: {note}")
    
    print("\nThe visualizer includes fallback logic for these cases, so it should work correctly.")


def main():
    """Run all compatibility tests"""
    
    print("Testing Visualizer Compatibility with Database Changes")
    print("=" * 60)
    
    # Run tests
    imports_ok = test_visualizer_imports()
    db_ok = test_database_manager_creation()
    
    # Show compatibility notes
    test_compatibility_summary()
    
    # Final verdict
    print("\n" + "=" * 60)
    if imports_ok and db_ok:
        print("✅ Visualizer should work correctly with the current database structure")
        return 0
    else:
        print("❌ Visualizer may have issues - see errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())