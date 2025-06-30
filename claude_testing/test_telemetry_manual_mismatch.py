#!/usr/bin/env python3
"""
Test to identify and fix telemetry vs manual data calculation mismatches.

This test demonstrates the root causes of discrepancies between telemetry and manual readings:
1. Sensor orientation assumptions (up vs down reading)
2. Unit conversion inconsistencies 
3. Different reference point calculations
4. DTW vs pressure conversion methods
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def test_calculation_mismatch():
    """Test that demonstrates the mismatch between telemetry and manual calculations"""
    
    print("=== TELEMETRY vs MANUAL CALCULATION MISMATCH TEST ===\n")
    
    # Test scenario: Same well, same time, different data sources
    test_well = {
        'well_number': 'TEST001',
        'top_of_casing': 100.0,  # feet above datum
        'ground_elevation': 95.0,  # feet above datum
    }
    
    test_time = datetime(2024, 6, 15, 12, 0, 0)
    actual_water_level = 85.0  # feet above datum (true value)
    
    print(f"Test Well: {test_well['well_number']}")
    print(f"Top of Casing: {test_well['top_of_casing']} ft")
    print(f"Actual Water Level: {actual_water_level} ft")
    print(f"Actual DTW: {test_well['top_of_casing'] - actual_water_level} ft\n")
    
    # ========================================
    # MANUAL READING CALCULATION (CORRECT)
    # ========================================
    print("1. MANUAL READING CALCULATION:")
    manual_dtw1 = 15.0  # feet below TOC
    manual_dtw2 = 15.1  # feet below TOC (slight measurement variation)
    
    # Manual calculation (from manual_readings_handler.py:21-23)
    valid_measurements = [manual_dtw1, manual_dtw2]
    dtw_avg = sum(valid_measurements) / len(valid_measurements)
    manual_water_level = test_well['top_of_casing'] - dtw_avg
    
    print(f"   DTW_1: {manual_dtw1} ft")
    print(f"   DTW_2: {manual_dtw2} ft") 
    print(f"   DTW_avg: {dtw_avg} ft")
    print(f"   Manual Water Level = TOC - DTW = {test_well['top_of_casing']} - {dtw_avg} = {manual_water_level} ft")
    print(f"   Error from actual: {abs(manual_water_level - actual_water_level):.2f} ft\n")
    
    # ========================================
    # TELEMETRY CALCULATION (PROBLEMATIC)
    # ========================================
    print("2. TELEMETRY CALCULATION:")
    
    # Simulate telemetry sensor reading distance to water
    # ISSUE 1: Telemetry might read "distance to water" differently than DTW
    telemetry_distance = 15.2  # feet (sensor to water surface)
    
    # ISSUE 2: Current telemetry processing adds dummy pressure conversion
    # (from water_level.py:222)
    dummy_pressure = telemetry_distance * 0.43  # PSI per foot conversion
    print(f"   Telemetry distance to water: {telemetry_distance} ft")
    print(f"   Dummy pressure conversion: {telemetry_distance} * 0.43 = {dummy_pressure:.2f} PSI")
    
    # ISSUE 3: If telemetry provides water_level directly, it might use different reference
    # Some telemetry systems might calculate from ground level instead of TOC
    telemetry_water_level_ground_ref = test_well['ground_elevation'] - telemetry_distance
    telemetry_water_level_toc_ref = test_well['top_of_casing'] - telemetry_distance
    
    print(f"   If telemetry uses ground reference: {test_well['ground_elevation']} - {telemetry_distance} = {telemetry_water_level_ground_ref} ft")
    print(f"   If telemetry uses TOC reference: {test_well['top_of_casing']} - {telemetry_distance} = {telemetry_water_level_toc_ref} ft")
    print(f"   Ground ref error: {abs(telemetry_water_level_ground_ref - actual_water_level):.2f} ft")
    print(f"   TOC ref error: {abs(telemetry_water_level_toc_ref - actual_water_level):.2f} ft\n")
    
    # ========================================
    # TRANSDUCER CALCULATION (COMPLEX)
    # ========================================
    print("3. TRANSDUCER CALCULATION:")
    
    # Simulate transducer at bottom of well reading pressure upward
    well_depth = 50.0  # feet below TOC
    transducer_depth = well_depth - 5.0  # 5 feet from bottom
    water_column_height = actual_water_level - (test_well['top_of_casing'] - transducer_depth)
    
    # Pressure from water column (PSI = feet * 0.43)
    water_pressure_psi = water_column_height * 0.43307  # exact conversion
    atmospheric_pressure = 14.7  # PSI
    total_pressure = water_pressure_psi + atmospheric_pressure
    
    print(f"   Transducer depth below TOC: {transducer_depth} ft")
    print(f"   Water column height above transducer: {water_column_height:.2f} ft")
    print(f"   Water pressure: {water_column_height:.2f} * 0.43307 = {water_pressure_psi:.2f} PSI")
    print(f"   Total pressure: {water_pressure_psi:.2f} + {atmospheric_pressure} = {total_pressure:.2f} PSI")
    
    # Convert back to water level (with insertion level calibration)
    # ISSUE 4: insertion_dh calculation might be wrong
    # From water_level_processor.py:852: water_level = water_pressure + insertion_dh
    compensated_pressure = total_pressure - atmospheric_pressure  # Remove baro
    
    # Calculate correct insertion_dh
    correct_insertion_dh = actual_water_level - compensated_pressure
    transducer_water_level = compensated_pressure + correct_insertion_dh
    
    print(f"   Compensated pressure: {compensated_pressure:.2f} PSI")
    print(f"   Correct insertion_dh: {correct_insertion_dh:.2f}")
    print(f"   Calculated water level: {compensated_pressure:.2f} + {correct_insertion_dh:.2f} = {transducer_water_level:.2f} ft")
    print(f"   Error from actual: {abs(transducer_water_level - actual_water_level):.2f} ft\n")
    
    # ========================================
    # UNIT CONVERSION PRECISION TEST
    # ========================================
    print("4. UNIT CONVERSION PRECISION TEST:")
    
    # Test current conversion factors vs exact values
    current_m_to_ft = 3.28084  # from solinst_reader.py
    current_kpa_to_psi = 0.145038  # from solinst_reader.py
    
    exact_m_to_ft = 3.280839895  # exact conversion
    exact_kpa_to_psi = 0.145037738  # exact conversion
    
    test_meters = 10.0
    test_kpa = 100.0
    
    current_ft = test_meters * current_m_to_ft
    exact_ft = test_meters * exact_m_to_ft
    
    current_psi = test_kpa * current_kpa_to_psi
    exact_psi = test_kpa * exact_kpa_to_psi
    
    print(f"   {test_meters}m using current factor: {current_ft:.6f} ft")
    print(f"   {test_meters}m using exact factor: {exact_ft:.6f} ft")
    print(f"   Difference: {abs(current_ft - exact_ft):.6f} ft")
    print()
    print(f"   {test_kpa} kPa using current factor: {current_psi:.6f} PSI")
    print(f"   {test_kpa} kPa using exact factor: {exact_psi:.6f} PSI")
    print(f"   Difference: {abs(current_psi - exact_psi):.6f} PSI\n")
    
    # ========================================
    # SUMMARY OF ISSUES FOUND
    # ========================================
    print("=== IDENTIFIED ISSUES ===")
    print("1. TELEMETRY REFERENCE CONFUSION:")
    print(f"   - Ground reference error: {abs(telemetry_water_level_ground_ref - actual_water_level):.2f} ft")
    print(f"   - Some sensors may read from ground vs TOC")
    print()
    print("2. DUMMY PRESSURE CONVERSION:")
    print(f"   - Telemetry creates fake pressure: DTW * 0.43 = {dummy_pressure:.2f} PSI")
    print(f"   - This doesn't represent actual sensor data")
    print()
    print("3. UNIT CONVERSION PRECISION:")
    print(f"   - Meters conversion error: {abs(current_ft - exact_ft):.6f} ft per 10m")
    print(f"   - Pressure conversion error: {abs(current_psi - exact_psi):.6f} PSI per 100 kPa")
    print()
    print("4. INSERTION LEVEL CALIBRATION:")
    print(f"   - Requires accurate manual reading correlation")
    print(f"   - Default fallback (TOC-30) may be wrong for shallow wells")
    print()
    
    # Save test results
    results = {
        'test_timestamp': datetime.now().isoformat(),
        'test_well': test_well,
        'actual_water_level': actual_water_level,
        'manual_calculation': {
            'dtw_avg': dtw_avg,
            'water_level': manual_water_level,
            'error': abs(manual_water_level - actual_water_level)
        },
        'telemetry_ground_ref': {
            'water_level': telemetry_water_level_ground_ref,
            'error': abs(telemetry_water_level_ground_ref - actual_water_level)
        },
        'telemetry_toc_ref': {
            'water_level': telemetry_water_level_toc_ref,
            'error': abs(telemetry_water_level_toc_ref - actual_water_level)
        },
        'transducer_calculation': {
            'water_level': transducer_water_level,
            'error': abs(transducer_water_level - actual_water_level),
            'insertion_dh': correct_insertion_dh
        },
        'unit_conversion_errors': {
            'meters_to_feet_error': abs(current_ft - exact_ft),
            'kpa_to_psi_error': abs(current_psi - exact_psi)
        }
    }
    
    with open('telemetry_manual_mismatch_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("Test results saved to: telemetry_manual_mismatch_results.json")
    return results

if __name__ == "__main__":
    test_calculation_mismatch()