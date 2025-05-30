#!/usr/bin/env python3
"""
Test script to verify the edit tracking system implementation
"""
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication
from src.gui.dialogs.water_level_edit_dialog import WaterLevelEditDialog

def create_test_data():
    """Create sample transducer and manual data for testing"""
    # Create time series
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(hours=i) for i in range(100)]
    
    # Create transducer data
    transducer_data = pd.DataFrame({
        'timestamp_utc': timestamps,
        'water_level': np.random.normal(50, 2, 100),
        'pressure': np.random.normal(14.7, 0.1, 100),
        'baro_flag': ['standard'] * 50 + ['master'] * 20 + ['standard'] * 30,
        'level_flag': ['standard'] * 100,
        'spike_flag': ['none'] * 100,
        'well_number': ['TEST_WELL'] * 100,
        'data_source': ['Transducer'] * 100
    })
    
    # Create manual data
    manual_timestamps = [timestamps[i] for i in [10, 30, 50, 70, 90]]
    manual_data = pd.DataFrame({
        'timestamp_utc': manual_timestamps,
        'water_level': [48.5, 51.2, 49.8, 50.5, 49.0],
        'well_number': ['TEST_WELL'] * 5,
        'data_source': ['Manual'] * 5
    })
    
    # Create master baro data
    master_baro_data = pd.DataFrame({
        'timestamp_utc': timestamps,
        'pressure': np.random.normal(14.7, 0.15, 100),
        'data_source': ['Master_Baro'] * 100
    })
    
    return transducer_data, manual_data, master_baro_data

def main():
    """Main test function"""
    app = QApplication(sys.argv)
    
    # Create test data
    transducer_data, manual_data, master_baro_data = create_test_data()
    
    # Create dialog
    dialog = WaterLevelEditDialog(
        transducer_data=transducer_data,
        manual_data=manual_data,
        master_baro_data=master_baro_data,
        parent=None,
        db_path=":memory:"
    )
    
    # Print initial state
    print("Initial edit history:")
    print(f"  Session ID: {dialog.session_id}")
    print(f"  Number of edits: {len(dialog.edit_history['edits'])}")
    
    # Show dialog
    dialog.show()
    
    # Add instructions
    print("\nTest Instructions:")
    print("1. Click 'Fix Spikes' and select some points to interpolate")
    print("2. Click 'Apply' in the spike helper dialog")
    print("3. Click 'Compensation' and apply compensation")
    print("4. Click 'Adjust Base Line' and make an adjustment")
    print("5. Try resetting individual edits using the Reset buttons")
    print("6. Try 'Reset All Edits' from the toolbar")
    print("7. Verify that edits can be applied/reset independently")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()