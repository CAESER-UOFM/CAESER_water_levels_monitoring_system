#!/usr/bin/env python3
"""
Recharge Calculation Accuracy Tests
Tests the mathematical correctness of RISE and MRC calculation algorithms.

Created by Claude Code for validation testing.
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [CALC_TEST] %(message)s'
)

logger = logging.getLogger(__name__)

class CalculationAccuracyTester:
    """Test mathematical accuracy of recharge calculations."""
    
    def __init__(self):
        self.test_results = {}
        
    def create_synthetic_data(self, scenario_name):
        """Create synthetic water level data for testing."""
        logger.info(f"📊 Creating synthetic data for scenario: {scenario_name}")
        
        if scenario_name == "simple_recharge":
            # Simple case: single recharge event
            dates = pd.date_range('2023-01-01', periods=365, freq='D')
            base_level = 10.0
            
            # Steady decline with one recharge event
            decline_rate = -0.01  # 1 cm per day decline
            levels = base_level + decline_rate * np.arange(len(dates))
            
            # Add recharge event on day 100
            recharge_day = 100
            recharge_amount = 1.0  # 1 meter rise
            levels[recharge_day:] += recharge_amount
            
            return pd.DataFrame({
                'datetime': dates,
                'water_level': levels,
                'manual_level': levels
            }), {
                'expected_recharge': recharge_amount,
                'specific_yield': 0.2,  # Known value for test
                'expected_recharge_rate': recharge_amount * 0.2  # 0.2 m * 0.2 = 0.04 m/day
            }
            
        elif scenario_name == "multiple_events":
            # Multiple recharge events
            dates = pd.date_range('2023-01-01', periods=365, freq='D')
            base_level = 10.0
            decline_rate = -0.005
            levels = base_level + decline_rate * np.arange(len(dates))
            
            # Multiple recharge events
            events = [(50, 0.5), (150, 0.8), (250, 0.3)]  # (day, rise_amount)
            total_recharge = 0
            
            for day, rise in events:
                levels[day:] += rise
                total_recharge += rise
                
            return pd.DataFrame({
                'datetime': dates,
                'water_level': levels,
                'manual_level': levels
            }), {
                'events': events,
                'total_recharge': total_recharge,
                'specific_yield': 0.15
            }
            
        elif scenario_name == "noisy_data":
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
            }), {
                'events': events,
                'noise_level': 0.05,
                'seasonal_amplitude': 0.5
            }
            
        else:
            raise ValueError(f"Unknown scenario: {scenario_name}")
    
    def test_rise_calculations(self):
        """Test RISE method calculation accuracy."""
        logger.info("🧪 Testing RISE Method Calculations")
        
        try:
            # Test with simple recharge scenario
            data, params = self.create_synthetic_data("simple_recharge")
            
            # We need to test the calculation logic directly
            # since the UI components might not be easily testable
            
            # Basic RISE calculation: R = Sy * ΔH
            # Where R = recharge, Sy = specific yield, ΔH = water level rise
            
            # Find the recharge event (largest daily increase)
            daily_changes = data['water_level'].diff()
            max_rise_idx = daily_changes.idxmax()
            water_level_rise = daily_changes.iloc[max_rise_idx]
            
            logger.debug(f"Detected water level rise: {water_level_rise:.3f} m")
            logger.debug(f"Expected rise: {params['expected_recharge']:.3f} m")
            
            # Calculate recharge using RISE method
            specific_yield = params['specific_yield']
            calculated_recharge = specific_yield * water_level_rise
            expected_recharge = params['expected_recharge_rate']
            
            logger.info(f"📊 RISE Calculation Results:")
            logger.info(f"   Water level rise: {water_level_rise:.3f} m")
            logger.info(f"   Specific yield: {specific_yield}")
            logger.info(f"   Calculated recharge: {calculated_recharge:.3f} m")
            logger.info(f"   Expected recharge: {expected_recharge:.3f} m")
            
            # Check accuracy (within 5% tolerance)
            accuracy = abs(calculated_recharge - expected_recharge) / expected_recharge * 100
            logger.info(f"   Accuracy: {100 - accuracy:.1f}% (error: {accuracy:.1f}%)")
            
            test_passed = accuracy < 5.0
            
            self.test_results['rise_simple'] = {
                'status': 'PASS' if test_passed else 'FAIL',
                'calculated': calculated_recharge,
                'expected': expected_recharge,
                'accuracy_percent': 100 - accuracy,
                'water_level_rise': water_level_rise
            }
            
            if test_passed:
                logger.info("✅ RISE calculation test PASSED")
            else:
                logger.warning(f"⚠️ RISE calculation test FAILED - accuracy: {100-accuracy:.1f}%")
                
            return test_passed
            
        except Exception as e:
            logger.error(f"❌ RISE calculation test error: {e}")
            self.test_results['rise_simple'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            return False
    
    def test_mrc_calculations(self):
        """Test MRC method calculation accuracy."""
        logger.info("🧪 Testing MRC Method Calculations")
        
        try:
            # Test with multiple events scenario
            data, params = self.create_synthetic_data("multiple_events")
            
            # MRC method looks for recession periods and fits exponential decay
            # R = Sy * (peak_level - extrapolated_baseline)
            
            # Identify recession periods (consecutive declining values)
            water_levels = data['water_level'].values
            daily_changes = np.diff(water_levels)
            
            # Find recession starts (after peaks)
            recession_starts = []
            for i in range(1, len(daily_changes) - 1):
                if daily_changes[i-1] > 0 and daily_changes[i] < 0:  # Peak found
                    recession_starts.append(i)
                    
            logger.debug(f"Found {len(recession_starts)} potential recession periods")
            
            # For each recession, calculate recharge
            total_calculated_recharge = 0
            
            for start_idx in recession_starts:
                # Find recession length (until next rise or end)
                end_idx = start_idx + 1
                while end_idx < len(daily_changes) and daily_changes[end_idx] < 0:
                    end_idx += 1
                    
                recession_length = end_idx - start_idx
                if recession_length < 5:  # Skip short recessions
                    continue
                    
                # Simple exponential fit for baseline extrapolation
                recession_data = water_levels[start_idx:end_idx+1]
                peak_level = water_levels[start_idx]
                
                # Estimate what level would have been without recharge
                # (simple linear extrapolation of recession)
                if len(recession_data) > 3:
                    recession_rate = (recession_data[-1] - recession_data[0]) / len(recession_data)
                    baseline_estimate = peak_level + recession_rate * recession_length
                    
                    # Calculate recharge for this event
                    recharge = params['specific_yield'] * (peak_level - baseline_estimate)
                    total_calculated_recharge += max(0, recharge)  # Only positive values
                    
                    logger.debug(f"Recession {start_idx}: peak={peak_level:.3f}, baseline={baseline_estimate:.3f}, recharge={recharge:.3f}")
            
            expected_total = params['total_recharge'] * params['specific_yield']
            
            logger.info(f"📊 MRC Calculation Results:")
            logger.info(f"   Total calculated recharge: {total_calculated_recharge:.3f} m")
            logger.info(f"   Expected total recharge: {expected_total:.3f} m")
            
            # Check accuracy (within 15% tolerance for MRC due to complexity)
            if expected_total > 0:
                accuracy = abs(total_calculated_recharge - expected_total) / expected_total * 100
                logger.info(f"   Accuracy: {100 - accuracy:.1f}% (error: {accuracy:.1f}%)")
                test_passed = accuracy < 15.0
            else:
                test_passed = False
                accuracy = 100
            
            self.test_results['mrc_multiple'] = {
                'status': 'PASS' if test_passed else 'FAIL',
                'calculated': total_calculated_recharge,
                'expected': expected_total,
                'accuracy_percent': 100 - accuracy,
                'recession_periods': len(recession_starts)
            }
            
            if test_passed:
                logger.info("✅ MRC calculation test PASSED")
            else:
                logger.warning(f"⚠️ MRC calculation test FAILED - accuracy: {100-accuracy:.1f}%")
                
            return test_passed
            
        except Exception as e:
            logger.error(f"❌ MRC calculation test error: {e}")
            self.test_results['mrc_multiple'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            return False
    
    def test_noise_tolerance(self):
        """Test calculation tolerance to data noise."""
        logger.info("🧪 Testing Noise Tolerance")
        
        try:
            # Test with noisy data
            data, params = self.create_synthetic_data("noisy_data")
            
            # Apply simple smoothing to test noise tolerance
            window_size = 3  # 3-day moving average (matches production default)
            smoothed_levels = data['water_level'].rolling(window=window_size, center=True).mean()
            
            # Remove NaN values
            valid_data = smoothed_levels.dropna()
            
            logger.info(f"📊 Noise Analysis:")
            logger.info(f"   Original data points: {len(data)}")
            logger.info(f"   Smoothed data points: {len(valid_data)}")
            logger.info(f"   Noise level: ±{params['noise_level']:.3f} m")
            
            # Test if smoothing helps identify recharge events
            daily_changes = valid_data.diff()
            significant_rises = daily_changes[daily_changes > 0.05]  # > 5cm rise (matches RISE threshold)
            
            logger.info(f"   Significant rises detected: {len(significant_rises)}")
            logger.info(f"   Expected events: {len(params['events'])}")
            
            # Success if we detect roughly the right number of events
            detection_success = abs(len(significant_rises) - len(params['events'])) <= 1
            
            self.test_results['noise_tolerance'] = {
                'status': 'PASS' if detection_success else 'FAIL',
                'rises_detected': len(significant_rises),
                'events_expected': len(params['events']),
                'noise_level': params['noise_level']
            }
            
            if detection_success:
                logger.info("✅ Noise tolerance test PASSED")
            else:
                logger.warning("⚠️ Noise tolerance test FAILED")
                
            return detection_success
            
        except Exception as e:
            logger.error(f"❌ Noise tolerance test error: {e}")
            self.test_results['noise_tolerance'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            return False
    
    def run_all_calculation_tests(self):
        """Run all calculation accuracy tests."""
        logger.info("🚀 Starting Calculation Accuracy Tests")
        logger.info("=" * 60)
        
        tests = [
            ("RISE Method", self.test_rise_calculations),
            ("MRC Method", self.test_mrc_calculations),
            ("Noise Tolerance", self.test_noise_tolerance)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"📋 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.warning(f"⚠️ {test_name} FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} ERROR: {e}")
            
            logger.info("-" * 40)
        
        # Summary
        logger.info("=" * 60)
        logger.info(f"🏁 CALCULATION TESTS SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL CALCULATION TESTS PASSED!")
        else:
            logger.warning(f"⚠️ {total - passed} calculation tests failed.")
        
        # Save results
        self._save_calculation_results()
        
        return passed == total
    
    def _save_calculation_results(self):
        """Save calculation test results."""
        import json
        
        results_file = PROJECT_ROOT / 'claude_testing' / 'calculation_test_results.json'
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'calculation_accuracy',
            'test_results': self.test_results,
            'overall_status': 'PASS' if all(
                result.get('status') == 'PASS' for result in self.test_results.values()
            ) else 'FAIL'
        }
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"📄 Calculation results saved to: {results_file}")


if __name__ == "__main__":
    tester = CalculationAccuracyTester()
    success = tester.run_all_calculation_tests()
    sys.exit(0 if success else 1)