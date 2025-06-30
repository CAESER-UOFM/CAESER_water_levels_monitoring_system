#!/usr/bin/env python3
"""
Complete Workflow Test: Database + Recharge + XLE Upload + Google Drive Sync
Tests the entire pipeline from empty database to full sync with all new features.
"""

import os
import sys
import json
import logging
import sqlite3
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

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

class CompleteWorkflowTester:
    """Test complete workflow from empty database to full sync."""
    
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.test_results = {}
        self.test_db_path = None
        self.project_name = f"TEST_COMPLETE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def test_1_create_empty_database(self):
        """Step 1: Create a fresh empty database with new schema."""
        logger.info("🗄️ Step 1: Creating fresh database with XLE tracking...")
        
        try:
            from database.initializer import DatabaseInitializer
            
            # Create temporary database
            temp_dir = tempfile.mkdtemp(prefix="complete_test_")
            self.test_db_path = os.path.join(temp_dir, f"{self.project_name}.db")
            
            # Initialize with new schema including XLE tracking and recharge tables
            initializer = DatabaseInitializer(Path(self.test_db_path))
            initializer.initialize_database()
            
            # Verify new tables exist
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'wells', 'water_level_readings', 'xle_files', 
                'rise_calculations', 'mrc_calculations'
            ]
            
            missing_tables = [t for t in required_tables if t not in tables]
            
            # Check for new column in water_level_readings
            cursor.execute("PRAGMA table_info(water_level_readings)")
            columns = [row[1] for row in cursor.fetchall()]
            has_xle_column = 'source_xle_file' in columns
            
            conn.close()
            
            logger.info(f"✅ Database created: {self.test_db_path}")
            logger.info(f"   Tables: {len(tables)} total")
            logger.info(f"   Missing required: {missing_tables}")
            logger.info(f"   XLE source column: {'✅' if has_xle_column else '❌'}")
            
            self.test_results['database_creation'] = {
                'status': 'PASS' if not missing_tables and has_xle_column else 'FAIL',
                'tables_count': len(tables),
                'missing_tables': missing_tables,
                'xle_column_exists': has_xle_column,
                'database_path': self.test_db_path
            }
            
            return not missing_tables and has_xle_column
            
        except Exception as e:
            logger.error(f"❌ Database creation failed: {e}")
            self.test_results['database_creation'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_2_add_sample_data(self):
        """Step 2: Add sample wells and basic data."""
        logger.info("📊 Step 2: Adding sample wells and data...")
        
        try:
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # Add sample wells
            wells = [
                ('TEST_W001', 'TW1', 35.1, -90.0, 295.0, 'SHAL', 'TEST_FIELD'),
                ('TEST_W002', 'TW2', 35.2, -90.1, 298.5, 'SHAL', 'TEST_FIELD'),
            ]
            
            for well_data in wells:
                cursor.execute("""
                    INSERT INTO wells (well_number, cae_number, latitude, longitude, 
                                     top_of_casing, aquifer, well_field, data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'transducer')
                """, well_data)
            
            # Add sample transducers
            cursor.execute("""
                INSERT INTO transducers (serial_number, well_number, installation_date)
                VALUES ('TN157_TEST001', 'TEST_W001', '2024-01-01 00:00:00')
            """)
            
            cursor.execute("""
                INSERT INTO transducers (serial_number, well_number, installation_date)
                VALUES ('TN157_TEST002', 'TEST_W002', '2024-01-01 00:00:00')
            """)
            
            # Add sample water level readings with XLE source tracking
            base_time = datetime(2024, 6, 1)
            readings = []
            
            for i in range(100):  # 100 readings over ~25 days
                timestamp = base_time + timedelta(hours=6*i)
                
                # Create realistic water level with some variation and recharge events
                base_level = 250.0
                seasonal = 1.0 * (i / 100)  # Slight seasonal trend
                noise = 0.1 * (i % 7 - 3)  # Weekly variation
                
                # Add recharge events at specific points
                recharge = 0
                if i in [20, 45, 70]:  # Three recharge events
                    recharge = 0.3 + (i % 3) * 0.2  # 0.3-0.7 ft rises
                
                water_level = base_level + seasonal + noise + recharge
                
                readings.append((
                    'TEST_W001', timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    timestamp.timestamp(), 15.2, 5.1, water_level, 65.0,
                    'TN157_TEST001', 'corrected', 'good', 
                    '/test/path/TEST_W001_sample.xle'  # XLE source file
                ))
            
            cursor.executemany("""
                INSERT INTO water_level_readings 
                (well_number, timestamp_utc, julian_timestamp, pressure, water_pressure,
                 water_level, temperature, serial_number, baro_flag, level_flag, source_xle_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, readings)
            
            # Add XLE file tracking record
            cursor.execute("""
                INSERT INTO xle_files 
                (file_path, file_name, file_type, serial_number, well_number,
                 start_date, end_date, file_size, file_hash, project_name,
                 upload_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                '/test/path/TEST_W001_sample.xle', 'TEST_W001_sample.xle',
                'transducer', 'TN157_TEST001', 'TEST_W001',
                base_time.isoformat(), (base_time + timedelta(days=25)).isoformat(),
                524288, 'test_hash_123', self.project_name, 'pending'
            ))
            
            conn.commit()
            
            # Verify data
            cursor.execute("SELECT COUNT(*) FROM wells")
            well_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM water_level_readings")
            reading_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM xle_files WHERE upload_status = 'pending'")
            pending_xle_count = cursor.fetchone()[0]
            
            conn.close()
            
            logger.info(f"✅ Sample data added:")
            logger.info(f"   Wells: {well_count}")
            logger.info(f"   Water level readings: {reading_count}")
            logger.info(f"   Pending XLE files: {pending_xle_count}")
            
            self.test_results['sample_data'] = {
                'status': 'PASS',
                'wells': well_count,
                'readings': reading_count,
                'pending_xle_files': pending_xle_count
            }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Sample data creation failed: {e}")
            self.test_results['sample_data'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_3_recharge_calculations(self):
        """Step 3: Test recharge calculations and database storage."""
        logger.info("⚡ Step 3: Testing recharge calculations...")
        
        try:
            from database.manager import DatabaseManager
            
            # Initialize database manager
            db_manager = DatabaseManager()
            db_manager.open_database(self.test_db_path)
            
            # Import our database workflow tester functions
            sys.path.insert(0, str(PROJECT_ROOT / "claude_testing"))
            from test_database_workflow import DatabaseWorkflowTester
            
            # Create workflow tester and test recharge calculations
            workflow_tester = DatabaseWorkflowTester()
            workflow_tester.db_path = self.test_db_path
            workflow_tester.conn = sqlite3.connect(self.test_db_path)
            workflow_tester.conn.row_factory = sqlite3.Row
            
            # Get test well data
            well_info, water_level_data = workflow_tester.get_test_well_data()
            
            if well_info:
                # Test RISE calculations
                rise_success = workflow_tester.test_rise_calculation_and_storage(well_info, water_level_data)
                
                # Test MRC calculations  
                mrc_success = workflow_tester.test_mrc_calculation_and_storage(well_info, water_level_data)
                
                workflow_tester.conn.close()
                db_manager.close()
                
                logger.info(f"✅ Recharge calculations:")
                logger.info(f"   RISE method: {'✅' if rise_success else '❌'}")
                logger.info(f"   MRC method: {'✅' if mrc_success else '❌'}")
                
                self.test_results['recharge_calculations'] = {
                    'status': 'PASS' if rise_success and mrc_success else 'FAIL',
                    'rise_success': rise_success,
                    'mrc_success': mrc_success
                }
                
                return rise_success and mrc_success
            else:
                logger.error("❌ Could not load test well data")
                self.test_results['recharge_calculations'] = {'status': 'FAIL', 'error': 'No test data'}
                return False
                
        except Exception as e:
            logger.error(f"❌ Recharge calculation test failed: {e}")
            self.test_results['recharge_calculations'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_4_xle_file_tracking(self):
        """Step 4: Test XLE file tracking and management."""
        logger.info("📁 Step 4: Testing XLE file tracking...")
        
        try:
            from database.manager import DatabaseManager
            from gui.handlers.google_drive_service import GoogleDriveService
            from gui.handlers.settings_handler import SettingsHandler
            from gui.handlers.xle_file_manager import XLEFileManager
            
            # Setup services
            settings_handler = SettingsHandler()
            settings_handler.set_setting("service_account_key_path", self.credentials_path)
            
            drive_service = GoogleDriveService.get_instance(settings_handler)
            drive_service.authenticate()
            
            db_manager = DatabaseManager()
            db_manager.open_database(self.test_db_path)
            
            # Initialize XLE manager
            xle_manager = XLEFileManager(db_manager, drive_service, settings_handler)
            
            # Get pending uploads
            pending_files = xle_manager.get_pending_uploads(self.project_name)
            
            # Create folder structure (test folder creation)
            folders = xle_manager.create_project_xle_folders(self.project_name)
            
            logger.info(f"✅ XLE file tracking:")
            logger.info(f"   Pending files: {len(pending_files)}")
            logger.info(f"   Folder structure created: {len(folders)} folders")
            logger.info(f"   Project folder: {folders.get('project', 'N/A')}")
            
            db_manager.close()
            
            self.test_results['xle_tracking'] = {
                'status': 'PASS',
                'pending_files': len(pending_files),
                'folders_created': len(folders),
                'project_folder_id': folders.get('project')
            }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ XLE file tracking test failed: {e}")
            self.test_results['xle_tracking'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_5_complete_sync_workflow(self):
        """Step 5: Test complete database upload with XLE file sync."""
        logger.info("☁️ Step 5: Testing complete sync workflow...")
        
        try:
            from database.manager import DatabaseManager
            from gui.handlers.google_drive_service import GoogleDriveService
            from gui.handlers.settings_handler import SettingsHandler
            from gui.handlers.cloud_database_handler import CloudDatabaseHandler
            
            # Setup services
            settings_handler = SettingsHandler()
            settings_handler.set_setting("service_account_key_path", self.credentials_path)
            
            drive_service = GoogleDriveService.get_instance(settings_handler)
            drive_service.authenticate()
            
            db_manager = DatabaseManager()
            db_manager.open_database(self.test_db_path)
            
            # Initialize cloud handler
            cloud_handler = CloudDatabaseHandler(drive_service, settings_handler)
            cloud_handler.set_database_manager(db_manager)
            
            # Test upload database with XLE files
            def progress_callback(progress, message):
                logger.info(f"   Progress: {progress}% - {message}")
            
            upload_success = cloud_handler.upload_database(
                self.test_db_path,
                self.project_name,
                description="Complete workflow test with XLE file upload",
                progress_callback=progress_callback
            )
            
            if upload_success:
                logger.info("✅ Complete sync workflow successful!")
                
                # Verify upload by listing projects
                projects = cloud_handler.list_projects()
                test_project = next((p for p in projects if p['name'] == self.project_name), None)
                
                success = test_project is not None
                
                self.test_results['complete_sync'] = {
                    'status': 'PASS' if success else 'FAIL',
                    'upload_success': upload_success,
                    'project_found': test_project is not None,
                    'project_info': test_project
                }
                
                db_manager.close()
                return success
            else:
                logger.error("❌ Database upload failed")
                self.test_results['complete_sync'] = {'status': 'FAIL', 'error': 'Upload failed'}
                db_manager.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ Complete sync workflow failed: {e}")
            self.test_results['complete_sync'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def run_complete_workflow_test(self):
        """Run all workflow tests in sequence."""
        logger.info("🚀 Starting Complete Workflow Test")
        logger.info("=" * 70)
        logger.info(f"Test Project: {self.project_name}")
        logger.info("=" * 70)
        
        tests = [
            ("Empty Database Creation", self.test_1_create_empty_database),
            ("Sample Data Addition", self.test_2_add_sample_data),
            ("Recharge Calculations", self.test_3_recharge_calculations),
            ("XLE File Tracking", self.test_4_xle_file_tracking),
            ("Complete Sync Workflow", self.test_5_complete_sync_workflow)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"📋 Running: {test_name}")
            
            try:
                success = test_func()
                if success:
                    passed_tests += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.error(f"❌ {test_name} FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED with exception: {e}")
            
            logger.info("-" * 50)
        
        # Final summary
        logger.info("=" * 70)
        logger.info(f"🏁 COMPLETE WORKFLOW TEST SUMMARY")
        logger.info(f"Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED!")
            logger.info("   ✅ Database schema with XLE tracking")
            logger.info("   ✅ Recharge calculations and storage")
            logger.info("   ✅ XLE file management")
            logger.info("   ✅ Complete Google Drive sync")
            logger.info("")
            logger.info("🚀 READY FOR PRODUCTION TESTING!")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests failed")
        
        # Save results
        results_file = PROJECT_ROOT / "claude_testing" / "complete_workflow_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'test_type': 'complete_workflow',
                'project_name': self.project_name,
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'success_rate': passed_tests / total_tests * 100,
                'test_results': self.test_results
            }, f, indent=2)
        
        logger.info(f"📄 Detailed results saved to: {results_file}")
        
        # Cleanup
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
                logger.info("🧹 Cleaned up test database")
            except:
                pass
        
        return passed_tests == total_tests

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test complete workflow with XLE upload')
    parser.add_argument('credentials', help='Path to Google Drive service account credentials')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.credentials):
        print(f"❌ Credentials file not found: {args.credentials}")
        return 1
    
    tester = CompleteWorkflowTester(args.credentials)
    success = tester.run_complete_workflow_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())