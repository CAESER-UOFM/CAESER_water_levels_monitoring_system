#!/usr/bin/env python3
"""
Debug script for the noise tolerance test to understand why it's failing.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def create_noisy_data():
    """Create the same synthetic noisy data as in the test."""
    # Realistic data with noise
    dates = pd.date_range('2023-01-01', periods=365, freq='D')
    base_level = 10.0
    
    # Seasonal pattern + decline + noise
    seasonal = 0.5 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
    decline = -0.008 * np.arange(len(dates))
    noise = np.random.normal(0, 0.05, len(dates))  # 5cm noise
    
    levels = base_level + seasonal + decline + noise
    
    # Add recharge events
    events = [(75, 0.6), (200, 0.4)]
    for day, rise in events:
        levels[day:] += rise
        
    return pd.DataFrame({
        'datetime': dates,
        'water_level': levels,
        'manual_level': levels
    }), events

def analyze_noise_tolerance():
    """Analyze the noise tolerance issue."""
    print("=== Debugging Noise Tolerance Test ===")
    
    # Create synthetic data
    data, events = create_noisy_data()
    
    print(f"Created data with {len(data)} points")
    print(f"Expected recharge events: {events}")
    
    # Show some statistics
    print(f"\nData statistics:")
    print(f"  Min water level: {data['water_level'].min():.3f} ft")
    print(f"  Max water level: {data['water_level'].max():.3f} ft")
    print(f"  Range: {data['water_level'].max() - data['water_level'].min():.3f} ft")
    print(f"  Std dev: {data['water_level'].std():.3f} ft")
    
    # Apply the same smoothing as in the test
    window_size = 7  # 7-day moving average
    smoothed_levels = data['water_level'].rolling(window=window_size, center=True).mean()
    
    # Remove NaN values
    valid_data = smoothed_levels.dropna()
    
    print(f"\nAfter smoothing:")
    print(f"  Original data points: {len(data)}")
    print(f"  Smoothed data points: {len(valid_data)}")
    print(f"  Smoothed min: {valid_data.min():.3f} ft")
    print(f"  Smoothed max: {valid_data.max():.3f} ft")
    print(f"  Smoothed range: {valid_data.max() - valid_data.min():.3f} ft")
    
    # Test for significant rises
    daily_changes = valid_data.diff()
    print(f"\nDaily changes analysis:")
    print(f"  Max daily change: {daily_changes.max():.3f} ft")
    print(f"  Min daily change: {daily_changes.min():.3f} ft")
    print(f"  Changes > 0.1 ft: {len(daily_changes[daily_changes > 0.1])}")
    print(f"  Changes > 0.05 ft: {len(daily_changes[daily_changes > 0.05])}")
    print(f"  Changes > 0.02 ft: {len(daily_changes[daily_changes > 0.02])}")
    
    # Look at the dates around the expected events
    print(f"\nAnalyzing around expected events:")
    for i, (day, expected_rise) in enumerate(events):
        event_date = data.iloc[day]['datetime']
        print(f"\nEvent {i+1} (day {day}, {event_date.strftime('%Y-%m-%d')}):")
        print(f"  Expected rise: {expected_rise:.3f} ft")
        
        # Look at raw data around this date
        start_idx = max(0, day - 10)
        end_idx = min(len(data), day + 10)
        raw_slice = data.iloc[start_idx:end_idx]
        
        print(f"  Raw data around event:")
        for j, row in raw_slice.iterrows():
            marker = " <-- EVENT" if j == day else ""
            print(f"    Day {j}: {row['water_level']:.3f} ft{marker}")
        
        # Look at smoothed data around this date (accounting for NaN removal)
        smoothed_start = max(0, day - 10 - 3)  # Account for rolling window
        smoothed_end = min(len(valid_data), day + 10 - 3)
        if smoothed_start < len(valid_data) and smoothed_end > 0:
            smoothed_slice = valid_data.iloc[smoothed_start:smoothed_end]
            print(f"  Smoothed data around event:")
            for j, level in enumerate(smoothed_slice):
                actual_day = smoothed_start + j
                marker = " <-- EVENT" if abs(actual_day - day) <= 3 else ""
                print(f"    Day ~{actual_day}: {level:.3f} ft{marker}")

    # Let's also try different thresholds
    print(f"\nTesting different detection thresholds:")
    thresholds = [0.01, 0.02, 0.05, 0.1, 0.2]
    for threshold in thresholds:
        significant_rises = daily_changes[daily_changes > threshold]
        print(f"  Threshold {threshold:.2f} ft: {len(significant_rises)} rises detected")
    
    # Let's see if the step-change approach works better
    print(f"\nTesting step-change detection (3-day comparison):")
    step_changes = []
    for i in range(3, len(valid_data)):
        current_avg = valid_data.iloc[i-2:i+1].mean()
        previous_avg = valid_data.iloc[i-5:i-2].mean()
        change = current_avg - previous_avg
        if change > 0.1:  # 10cm threshold
            step_changes.append((i, change))
    
    print(f"  Step changes detected: {len(step_changes)}")
    for i, change in step_changes:
        print(f"    Position {i}: {change:.3f} ft rise")

if __name__ == "__main__":
    analyze_noise_tolerance()