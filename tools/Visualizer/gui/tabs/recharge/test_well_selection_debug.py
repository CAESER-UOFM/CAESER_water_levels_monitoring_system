#!/usr/bin/env python3
"""
Debug script to test well selection in method launcher.
This script helps debug the "Well Unknown" issue.
"""

import sys
import os
import logging

# Add the current directory to the path
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_well_data_formats():
    """Test different well data formats that might be passed to the launcher."""
    
    print("=" * 60)
    print("TESTING WELL DATA FORMATS")
    print("=" * 60)
    
    # Test formats
    test_cases = [
        # Standard format (what should be passed)
        ("Standard Format", [("W001", "Monitoring Well A"), ("W002", "Production Well B")]),
        
        # Format with Unknown names (the problem case)
        ("Unknown Names", [("W001", "Unknown"), ("W002", "Unknown")]),
        
        # Format with empty names
        ("Empty Names", [("W001", ""), ("W002", None)]),
        
        # Dictionary format
        ("Dictionary Format", [
            {"well_id": "W001", "well_name": "Monitoring Well A"},
            {"well_id": "W002", "well_name": "Production Well B"}
        ]),
        
        # Mixed formats
        ("Mixed Format", [("W001", "Monitoring Well A"), {"well_id": "W002", "well_name": "Production Well B"}]),
        
        # Single values
        ("Single Values", ["W001", "W002"]),
    ]
    
    # Import the method launcher logic (without creating GUI)
    try:
        from method_launcher import MethodLauncher
        
        for test_name, test_data in test_cases:
            print(f"\n--- Testing {test_name} ---")
            print(f"Input data: {test_data}")
            
            # Simulate the well processing logic
            processed_wells = []
            
            for i, well_data in enumerate(test_data):
                print(f"  Processing well {i}: {well_data} (type: {type(well_data)})")
                
                well_id = None
                well_name = None
                
                # Handle the standard format used by the other tabs: (well_id, well_name)
                if isinstance(well_data, (list, tuple)) and len(well_data) >= 2:
                    well_id, well_name = well_data[0], well_data[1]
                    print(f"    Standard tuple format - ID: '{well_id}', Name: '{well_name}'")
                    
                    # Check if the well_name is meaningful
                    if well_name == 'Unknown' or not well_name or str(well_name).strip() == '':
                        print(f"    Well {well_id} has no meaningful name ('{well_name}'), using ID")
                        well_name = f"Well {well_id}"
                
                # Handle dictionary format (backup)
                elif isinstance(well_data, dict):
                    well_id = well_data.get('well_id', well_data.get('id'))
                    well_name = well_data.get('well_name', well_data.get('name'))
                    print(f"    Dict format - ID: '{well_id}', Name: '{well_name}'")
                    
                    # Try alternative keys if primary ones don't work
                    if well_name is None or well_name == 'Unknown':
                        well_name = well_data.get('location_id', well_data.get('location_name'))
                    
                    if well_name is None or well_name == 'Unknown':
                        well_name = f"Well {well_id}"
                
                # Handle single value (assume it's well_id)
                elif isinstance(well_data, (str, int)):
                    well_id = well_data
                    well_name = f"Well {well_id}"
                    print(f"    Single value format - ID: '{well_id}', Generated Name: '{well_name}'")
                
                else:
                    print(f"    WARNING: Unexpected well data format: {well_data} (type: {type(well_data)})")
                    continue
                
                # Validate we have at least an ID
                if well_id is None or str(well_id).strip() == '':
                    print(f"    WARNING: Could not extract valid well ID from: {well_data}")
                    continue
                
                # Create display name (use the same format as the other tabs)
                if well_name and well_name != 'Unknown' and str(well_name).strip():
                    # Format: "WellName (ID)" to match other tabs
                    display_name = f"{str(well_name).strip()} ({well_id})"
                else:
                    display_name = f"Well {well_id}"
                
                processed_wells.append((display_name, well_id))
                print(f"    RESULT: '{display_name}' (ID: {well_id})")
            
            print(f"  Final processed wells: {processed_wells}")
            print()
        
    except ImportError as e:
        print(f"Could not import method_launcher: {e}")
        print("This is expected if running outside the main application.")

def print_troubleshooting_guide():
    """Print troubleshooting guide for the user."""
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING GUIDE: Well Unknown Issue")
    print("=" * 60)
    
    print("""
PROBLEM: Method launcher shows "Well Unknown" instead of actual well names

POSSIBLE CAUSES:
1. Wells in the main interface have names set to "Unknown"
2. No wells are selected in the main interface before opening launcher
3. Well data format is not what's expected
4. Data manager is not providing well names correctly

SOLUTIONS TO TRY:

1. CHECK MAIN INTERFACE WELL SELECTION:
   - Make sure you have selected wells in the main 'Available Wells' table
   - Check that the selected wells have proper names (not "Unknown")
   - Try selecting different wells to see if the issue persists

2. CHECK WELL DATA IN MAIN INTERFACE:
   - Look at the main well table - do the wells have proper names there?
   - If wells show as "Unknown" in main interface, the problem is upstream
   - Check if well data was imported correctly

3. USE REFRESH BUTTON:
   - Click the "🔄 Refresh" button in the launcher
   - This will reload the well data

4. CHECK APPLICATION LOGS:
   - Look for detailed logging information about well processing
   - The logs will show exactly what data is being processed

5. FALLBACK - USE DATA MANAGER WELLS:
   - If no wells are selected, launcher tries to load all available wells
   - This may provide access to wells even if selection isn't working

EXPECTED BEHAVIOR:
- Wells should appear as "WellName (ID)" in the dropdown
- If well has no name, should appear as "Well ID"
- At least one well should be available for method testing

If none of these solutions work, there may be a deeper issue with well data
loading in the main application that needs to be addressed.
""")

if __name__ == "__main__":
    print("Debug Script: Method Launcher Well Selection")
    print("This script helps debug the 'Well Unknown' issue in the method launcher.")
    print()
    
    test_well_data_formats()
    print_troubleshooting_guide()
    
    print("\nTo run this debug script:")
    print("cd /path/to/recharge/folder")
    print("python test_well_selection_debug.py")