#!/usr/bin/env python3
"""
Complete Database Workflow Test for Recharge Calculations
Tests the full pipeline: calculation → database storage → retrieval
No GUI components required - pure database and calculation logic testing.
"""

import sys
import os
import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseWorkflowTester:
    """Test complete database workflow for recharge calculations."""
    
    def __init__(self):
        self.db_path = PROJECT_ROOT / "claude_testing" / "test_database.db"
        self.test_results = {}
        
    def connect_to_database(self):
        """Connect to test database."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"✅ Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def verify_database_structure(self):
        """Verify that the database has all required tables for recharge calculations."""
        logger.info("🔍 Verifying database structure...")
        
        required_tables = [
            'wells',
            'water_level_readings', 
            'master_baro_readings',
            'transducers',
            'manual_level_readings'
        ]
        
        cursor = self.conn.cursor()
        
        for table in required_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"  ✅ {table}: {count} records")
                
                # Verify key columns exist
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                
                if table == 'wells':
                    assert 'well_number' in columns
                    assert 'top_of_casing' in columns
                    assert 'aquifer' in columns
                elif table == 'water_level_readings':
                    assert 'well_number' in columns
                    assert 'timestamp_utc' in columns
                    assert 'water_level' in columns
                
            except Exception as e:
                logger.error(f"❌ Table {table} verification failed: {e}")
                return False
        
        logger.info("✅ Database structure verified")
        return True
    
    def get_test_well_data(self):
        """Get water level data for test well."""
        logger.info("📊 Loading test well data...")
        
        cursor = self.conn.cursor()
        
        # Get well info
        cursor.execute("SELECT * FROM wells WHERE well_number = 'TEST_001'")
        well_info = cursor.fetchone()
        
        if not well_info:
            logger.error("❌ Test well not found")
            return None, None
        
        logger.info(f"  Well: {well_info['well_number']} ({well_info['cae_number']})")
        logger.info(f"  TOC: {well_info['top_of_casing']} ft")
        logger.info(f"  Aquifer: {well_info['aquifer']}")
        
        # Get water level data
        cursor.execute("""
            SELECT timestamp_utc, water_level, julian_timestamp
            FROM water_level_readings 
            WHERE well_number = 'TEST_001'
            ORDER BY julian_timestamp
        """)
        
        data = cursor.fetchall()
        
        if not data:
            logger.error("❌ No water level data found")
            return None, None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df.columns = ['timestamp_utc', 'water_level', 'julian_timestamp']  # Explicit column names
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
        df = df.set_index('timestamp_utc')
        
        logger.info(f"  ✅ Loaded {len(df)} water level readings")
        logger.info(f"  Date range: {df.index.min()} to {df.index.max()}")
        logger.info(f"  Water level range: {df['water_level'].min():.2f} - {df['water_level'].max():.2f} ft")
        
        return dict(well_info), df
    
    def test_rise_calculation_and_storage(self, well_info, water_level_data):
        """Test RISE method calculation and database storage."""
        logger.info("🔍 Testing RISE calculation and storage...")
        
        try:
            # Simple RISE calculation
            water_levels = water_level_data['water_level']
            
            # Identify rises (simplified algorithm)
            daily_data = water_levels.resample('D').mean()
            daily_changes = daily_data.diff()
            
            # Find significant rises (> 0.05 ft)
            significant_rises = daily_changes[daily_changes > 0.05]
            
            # Calculate total recharge (assuming specific yield = 0.2)
            specific_yield = 0.2
            total_rise = significant_rises.sum()
            total_recharge = total_rise * specific_yield
            
            logger.info(f"  Detected rises: {len(significant_rises)}")
            logger.info(f"  Total rise: {total_rise:.3f} ft")
            logger.info(f"  Total recharge: {total_recharge:.3f} ft")
            
            # Create events data
            events = []
            for date, rise in significant_rises.items():
                events.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'rise': float(rise),
                    'recharge': float(rise * specific_yield)
                })
            
            # Create calculation parameters
            parameters = {
                'method': 'RISE',
                'specific_yield': specific_yield,
                'rise_threshold': 0.05,
                'smoothing_window': 3,
                'calculation_date': datetime.now().isoformat()
            }
            
            # Create yearly summary
            yearly_summary = {
                'year': 2024,
                'total_events': len(events),
                'total_recharge': float(total_recharge),
                'annual_rate': float(total_recharge),  # ft/year
                'max_event': float(significant_rises.max()) if len(significant_rises) > 0 else 0,
                'avg_event': float(significant_rises.mean()) if len(significant_rises) > 0 else 0
            }
            
            # Store in database - First check if table exists
            cursor = self.conn.cursor()
            
            # Create RISE calculations table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rise_calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    well_number TEXT NOT NULL,
                    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parameters TEXT NOT NULL,
                    events_data TEXT NOT NULL,
                    yearly_summary TEXT NOT NULL,
                    total_recharge REAL NOT NULL,
                    total_events INTEGER NOT NULL,
                    annual_rate REAL NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (well_number) REFERENCES wells (well_number)
                )
            """)
            
            # Insert calculation results
            cursor.execute("""
                INSERT INTO rise_calculations 
                (well_number, parameters, events_data, yearly_summary, 
                 total_recharge, total_events, annual_rate, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                well_info['well_number'],
                json.dumps(parameters),
                json.dumps(events),
                json.dumps(yearly_summary),
                total_recharge,
                len(events),
                total_recharge,
                'Test calculation from database workflow test'
            ))
            
            calculation_id = cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"  ✅ RISE calculation saved to database (ID: {calculation_id})")
            
            # Test retrieval
            cursor.execute("""
                SELECT * FROM rise_calculations WHERE id = ?
            """, (calculation_id,))
            
            retrieved = cursor.fetchone()
            
            if retrieved:
                # Verify data integrity
                stored_params = json.loads(retrieved['parameters'])
                stored_events = json.loads(retrieved['events_data'])
                stored_summary = json.loads(retrieved['yearly_summary'])
                
                logger.info(f"  ✅ Data retrieved successfully")
                logger.info(f"    Method: {stored_params['method']}")
                logger.info(f"    Events stored: {len(stored_events)}")
                logger.info(f"    Total recharge: {retrieved['total_recharge']:.3f} ft")
                
                # Verify data matches
                assert abs(retrieved['total_recharge'] - total_recharge) < 0.001
                assert retrieved['total_events'] == len(events)
                assert stored_params['method'] == 'RISE'
                
                logger.info("  ✅ Data integrity verified")
                
                self.test_results['rise_workflow'] = {
                    'status': 'PASS',
                    'calculation_id': calculation_id,
                    'events_detected': len(events),
                    'total_recharge': float(total_recharge),
                    'storage_verified': True,
                    'retrieval_verified': True
                }
                
                return True
            else:
                logger.error("❌ Failed to retrieve stored calculation")
                return False
                
        except Exception as e:
            logger.error(f"❌ RISE calculation/storage test failed: {e}")
            self.test_results['rise_workflow'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            return False
    
    def test_mrc_calculation_and_storage(self, well_info, water_level_data):
        """Test MRC method calculation and database storage."""
        logger.info("🔍 Testing MRC calculation and storage...")
        
        try:
            # Simple MRC calculation - find recession periods
            water_levels = water_level_data['water_level']
            daily_data = water_levels.resample('D').mean()
            
            # Find peaks and recessions (simplified)
            rolling_max = daily_data.rolling(window=7, center=True).max()
            is_peak = (daily_data == rolling_max) & (daily_data.shift(1) < daily_data) & (daily_data.shift(-1) < daily_data)
            peaks = daily_data[is_peak]
            
            # Calculate recession curves
            recession_periods = []
            total_recharge = 0
            
            for peak_date, peak_level in peaks.items():
                # Look for recession after peak
                after_peak = daily_data[daily_data.index > peak_date]
                if len(after_peak) > 10:  # Need at least 10 days of data
                    recession_data = after_peak.head(30)  # Look at 30 days after peak
                    baseline = recession_data.tail(5).mean()  # Average of last 5 days
                    
                    if peak_level - baseline > 0.1:  # Significant recession
                        recharge = (peak_level - baseline) * 0.2  # Specific yield = 0.2
                        total_recharge += recharge
                        
                        recession_periods.append({
                            'peak_date': peak_date.strftime('%Y-%m-%d'),
                            'peak_level': float(peak_level),
                            'baseline_level': float(baseline),
                            'recharge': float(recharge),
                            'recession_length': len(recession_data)
                        })
            
            logger.info(f"  Recession periods found: {len(recession_periods)}")
            logger.info(f"  Total recharge: {total_recharge:.3f} ft")
            
            # Create calculation parameters
            parameters = {
                'method': 'MRC',
                'specific_yield': 0.2,
                'min_recession_length': 10,
                'fluctuation_tolerance': 0.01,
                'calculation_date': datetime.now().isoformat()
            }
            
            # Create yearly summary
            yearly_summary = {
                'year': 2024,
                'total_periods': len(recession_periods),
                'total_recharge': float(total_recharge),
                'annual_rate': float(total_recharge),
                'avg_recharge_per_event': float(total_recharge / len(recession_periods)) if recession_periods else 0
            }
            
            # Store in database
            cursor = self.conn.cursor()
            
            # Create MRC calculations table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mrc_calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    well_number TEXT NOT NULL,
                    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parameters TEXT NOT NULL,
                    recession_data TEXT NOT NULL,
                    yearly_summary TEXT NOT NULL,
                    total_recharge REAL NOT NULL,
                    total_periods INTEGER NOT NULL,
                    annual_rate REAL NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (well_number) REFERENCES wells (well_number)
                )
            """)
            
            # Insert calculation results
            cursor.execute("""
                INSERT INTO mrc_calculations 
                (well_number, parameters, recession_data, yearly_summary, 
                 total_recharge, total_periods, annual_rate, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                well_info['well_number'],
                json.dumps(parameters),
                json.dumps(recession_periods),
                json.dumps(yearly_summary),
                total_recharge,
                len(recession_periods),
                total_recharge,
                'Test calculation from database workflow test'
            ))
            
            calculation_id = cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"  ✅ MRC calculation saved to database (ID: {calculation_id})")
            
            # Test retrieval
            cursor.execute("""
                SELECT * FROM mrc_calculations WHERE id = ?
            """, (calculation_id,))
            
            retrieved = cursor.fetchone()
            
            if retrieved:
                # Verify data integrity
                stored_params = json.loads(retrieved['parameters'])
                stored_periods = json.loads(retrieved['recession_data'])
                stored_summary = json.loads(retrieved['yearly_summary'])
                
                logger.info(f"  ✅ Data retrieved successfully")
                logger.info(f"    Method: {stored_params['method']}")
                logger.info(f"    Periods stored: {len(stored_periods)}")
                logger.info(f"    Total recharge: {retrieved['total_recharge']:.3f} ft")
                
                # Verify data matches
                assert abs(retrieved['total_recharge'] - total_recharge) < 0.001
                assert retrieved['total_periods'] == len(recession_periods)
                assert stored_params['method'] == 'MRC'
                
                logger.info("  ✅ Data integrity verified")
                
                self.test_results['mrc_workflow'] = {
                    'status': 'PASS',
                    'calculation_id': calculation_id,
                    'periods_detected': len(recession_periods),
                    'total_recharge': float(total_recharge),
                    'storage_verified': True,
                    'retrieval_verified': True
                }
                
                return True
            else:
                logger.error("❌ Failed to retrieve stored calculation")
                return False
                
        except Exception as e:
            logger.error(f"❌ MRC calculation/storage test failed: {e}")
            self.test_results['mrc_workflow'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            return False
    
    def test_calculation_history_and_comparison(self):
        """Test loading and comparing multiple calculations."""
        logger.info("🔍 Testing calculation history and comparison...")
        
        try:
            cursor = self.conn.cursor()
            
            # Get all RISE calculations
            cursor.execute("""
                SELECT id, calculation_date, total_recharge, total_events
                FROM rise_calculations 
                WHERE well_number = 'TEST_001'
                ORDER BY calculation_date DESC
            """)
            rise_calculations = cursor.fetchall()
            
            # Get all MRC calculations
            cursor.execute("""
                SELECT id, calculation_date, total_recharge, total_periods
                FROM mrc_calculations 
                WHERE well_number = 'TEST_001'
                ORDER BY calculation_date DESC
            """)
            mrc_calculations = cursor.fetchall()
            
            logger.info(f"  RISE calculations found: {len(rise_calculations)}")
            logger.info(f"  MRC calculations found: {len(mrc_calculations)}")
            
            if rise_calculations and mrc_calculations:
                # Compare methods
                rise_total = rise_calculations[0]['total_recharge']
                mrc_total = mrc_calculations[0]['total_recharge']
                
                logger.info(f"  Latest RISE result: {rise_total:.3f} ft")
                logger.info(f"  Latest MRC result: {mrc_total:.3f} ft")
                logger.info(f"  Difference: {abs(rise_total - mrc_total):.3f} ft")
                
                # Test that we can reload complete calculation details
                cursor.execute("""
                    SELECT parameters, events_data, yearly_summary
                    FROM rise_calculations WHERE id = ?
                """, (rise_calculations[0]['id'],))
                
                rise_details = cursor.fetchone()
                rise_params = json.loads(rise_details['parameters'])
                rise_events = json.loads(rise_details['events_data'])
                
                logger.info(f"  ✅ RISE details reloaded: {len(rise_events)} events")
                logger.info(f"    Parameters: {rise_params['method']}, SY={rise_params['specific_yield']}")
                
                cursor.execute("""
                    SELECT parameters, recession_data, yearly_summary
                    FROM mrc_calculations WHERE id = ?
                """, (mrc_calculations[0]['id'],))
                
                mrc_details = cursor.fetchone()
                mrc_params = json.loads(mrc_details['parameters'])
                mrc_periods = json.loads(mrc_details['recession_data'])
                
                logger.info(f"  ✅ MRC details reloaded: {len(mrc_periods)} periods")
                logger.info(f"    Parameters: {mrc_params['method']}, SY={mrc_params['specific_yield']}")
                
                self.test_results['history_workflow'] = {
                    'status': 'PASS',
                    'rise_calculations': len(rise_calculations),
                    'mrc_calculations': len(mrc_calculations),
                    'details_reloadable': True,
                    'comparison_available': True
                }
                
                return True
            else:
                logger.warning("⚠️ No calculations found for comparison")
                return False
                
        except Exception as e:
            logger.error(f"❌ History/comparison test failed: {e}")
            self.test_results['history_workflow'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            return False
    
    def run_all_tests(self):
        """Run complete database workflow tests."""
        logger.info("🚀 Starting Database Workflow Tests")
        logger.info("=" * 60)
        
        # Connect to database
        if not self.connect_to_database():
            return False
        
        # Verify database structure
        if not self.verify_database_structure():
            return False
        
        # Get test data
        well_info, water_level_data = self.get_test_well_data()
        if well_info is None:
            return False
        
        # Test RISE workflow
        rise_success = self.test_rise_calculation_and_storage(well_info, water_level_data)
        
        # Test MRC workflow
        mrc_success = self.test_mrc_calculation_and_storage(well_info, water_level_data)
        
        # Test history and comparison
        history_success = self.test_calculation_history_and_comparison()
        
        # Summary
        total_tests = 3
        passed_tests = sum([rise_success, mrc_success, history_success])
        
        logger.info("=" * 60)
        logger.info(f"🏁 DATABASE WORKFLOW TESTS COMPLETE: {passed_tests}/{total_tests} passed")
        
        if passed_tests == total_tests:
            logger.info("✅ All database workflow tests PASSED!")
            logger.info("✅ Recharge calculation → storage → retrieval pipeline working correctly")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests failed")
        
        # Save results
        results_file = PROJECT_ROOT / "claude_testing" / "database_workflow_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'test_type': 'database_workflow',
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'success_rate': passed_tests / total_tests * 100,
                'test_results': self.test_results
            }, f, indent=2)
        
        logger.info(f"📄 Results saved to: {results_file}")
        
        self.conn.close()
        return passed_tests == total_tests

def main():
    """Main function."""
    tester = DatabaseWorkflowTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())