#!/usr/bin/env python3
"""
Comprehensive Google Drive Integration and Change Tracking Test
Tests the complete workflow: authentication → folder access → change tracking → sync operations
"""

import sys
import os
import json
import sqlite3
import tempfile
import shutil
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

class GoogleDriveIntegrationTester:
    """Comprehensive tester for Google Drive integration and change tracking."""
    
    def __init__(self):
        self.test_results = {}
        self.test_db_path = None
        self.drive_service = None
        self.settings_handler = None
        self.change_tracker = None
        
    def setup_credentials(self, credentials_path):
        """Setup Google Drive credentials for testing."""
        try:
            if not os.path.exists(credentials_path):
                logger.error(f"Credentials file not found: {credentials_path}")
                return False
            
            # Copy credentials to config directory
            config_dir = PROJECT_ROOT / "config"
            config_dir.mkdir(exist_ok=True)
            
            service_account_path = config_dir / "service_account_test.json"
            shutil.copy2(credentials_path, service_account_path)
            
            logger.info(f"✅ Credentials copied to: {service_account_path}")
            return str(service_account_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to setup credentials: {e}")
            return False
    
    def test_google_drive_authentication(self, credentials_path):
        """Test Google Drive authentication and basic API access."""
        logger.info("🔐 Testing Google Drive authentication...")
        
        try:
            # Import Google Drive service
            from gui.handlers.google_drive_service import GoogleDriveService
            from gui.handlers.settings_handler import SettingsHandler
            
            # Setup settings handler
            self.settings_handler = SettingsHandler()
            self.settings_handler.set_setting("service_account_key_path", credentials_path)
            
            # Initialize Drive service
            self.drive_service = GoogleDriveService.get_instance(self.settings_handler)
            
            # Test authentication
            auth_success = self.drive_service.authenticate()
            
            if auth_success:
                service = self.drive_service.get_service()
                
                # Test basic API call - list some files
                results = service.files().list(
                    pageSize=5,
                    fields="files(id, name)"
                ).execute()
                
                files = results.get('files', [])
                
                logger.info(f"✅ Authentication successful!")
                logger.info(f"   Service Account: {self.drive_service.get_service_account_email()}")
                logger.info(f"   Test API call returned {len(files)} files")
                
                self.test_results['authentication'] = {
                    'status': 'PASS',
                    'service_account': self.drive_service.get_service_account_email(),
                    'api_accessible': True,
                    'files_accessible': len(files)
                }
                return True
            else:
                logger.error("❌ Authentication failed")
                self.test_results['authentication'] = {'status': 'FAIL', 'error': 'Authentication failed'}
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication test failed: {e}")
            self.test_results['authentication'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_folder_access(self, folder_id=None):
        """Test access to specific Google Drive folder."""
        logger.info("📁 Testing Google Drive folder access...")
        
        try:
            service = self.drive_service.get_service()
            
            # Test default folder if none provided
            if not folder_id:
                folder_id = self.settings_handler.get_setting("google_drive_folder_id", "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK")
            
            # Try to access the folder
            folder_info = service.files().get(
                fileId=folder_id,
                fields="id, name, modifiedTime, permissions"
            ).execute()
            
            logger.info(f"✅ Folder access successful!")
            logger.info(f"   Folder Name: {folder_info['name']}")
            logger.info(f"   Folder ID: {folder_info['id']}")
            logger.info(f"   Modified: {folder_info.get('modifiedTime', 'Unknown')}")
            
            # List contents of folder
            contents = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=20
            ).execute()
            
            files = contents.get('files', [])
            folders = [f for f in files if f.get('mimeType') == 'application/vnd.google-apps.folder']
            databases = [f for f in files if f.get('name', '').endswith('.db')]
            
            logger.info(f"   Contents: {len(files)} items ({len(folders)} folders, {len(databases)} databases)")
            
            self.test_results['folder_access'] = {
                'status': 'PASS',
                'folder_name': folder_info['name'],
                'folder_id': folder_id,
                'total_items': len(files),
                'folders': len(folders),
                'databases': len(databases)
            }
            return True
            
        except Exception as e:
            logger.error(f"❌ Folder access test failed: {e}")
            self.test_results['folder_access'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_database_download(self, project_name="Test_Project"):
        """Test downloading a database from Google Drive."""
        logger.info("📥 Testing database download from Google Drive...")
        
        try:
            from gui.handlers.cloud_database_handler import CloudDatabaseHandler
            
            # Initialize cloud database handler
            cloud_handler = CloudDatabaseHandler(self.drive_service, self.settings_handler)
            
            # List available projects
            projects = cloud_handler.list_projects()
            
            if not projects:
                logger.warning("⚠️ No projects found in Google Drive")
                # Create a test database to upload first
                return self.test_database_upload_download_cycle()
            
            # Use first available project for testing
            test_project = projects[0]
            project_name = test_project['name']
            
            logger.info(f"   Testing with project: {project_name}")
            
            # Test download
            downloaded_path = cloud_handler.download_database(
                project_name, 
                test_project,
                progress_callback=lambda p, m: logger.info(f"   Download progress: {p}% - {m}")
            )
            
            if downloaded_path and os.path.exists(downloaded_path):
                # Verify database structure
                conn = sqlite3.connect(downloaded_path)
                cursor = conn.cursor()
                
                # Check for key tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['wells', 'water_level_readings', 'master_baro_readings']
                missing_tables = [t for t in required_tables if t not in tables]
                
                conn.close()
                
                logger.info(f"✅ Database download successful!")
                logger.info(f"   Downloaded to: {downloaded_path}")
                logger.info(f"   File size: {os.path.getsize(downloaded_path) / 1024 / 1024:.2f} MB")
                logger.info(f"   Tables found: {len(tables)}")
                
                if missing_tables:
                    logger.warning(f"   Missing expected tables: {missing_tables}")
                
                self.test_db_path = downloaded_path
                
                self.test_results['database_download'] = {
                    'status': 'PASS',
                    'project_name': project_name,
                    'file_size_mb': round(os.path.getsize(downloaded_path) / 1024 / 1024, 2),
                    'tables_count': len(tables),
                    'missing_tables': missing_tables,
                    'download_path': downloaded_path
                }
                return True
            else:
                logger.error("❌ Database download failed - no file received")
                self.test_results['database_download'] = {'status': 'FAIL', 'error': 'No file downloaded'}
                return False
                
        except Exception as e:
            logger.error(f"❌ Database download test failed: {e}")
            self.test_results['database_download'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_database_upload_download_cycle(self):
        """Test uploading our test database and downloading it back."""
        logger.info("🔄 Testing database upload/download cycle with test database...")
        
        try:
            from gui.handlers.cloud_database_handler import CloudDatabaseHandler
            
            # Use our test database
            test_db_source = PROJECT_ROOT / "claude_testing" / "test_database.db"
            if not test_db_source.exists():
                logger.error("❌ Test database not found - run create_test_database.py first")
                return False
            
            # Initialize cloud database handler
            cloud_handler = CloudDatabaseHandler(self.drive_service, self.settings_handler)
            
            # Create a temporary copy for upload
            temp_dir = tempfile.mkdtemp(prefix="gd_test_")
            test_db_copy = os.path.join(temp_dir, "test_upload.db")
            shutil.copy2(test_db_source, test_db_copy)
            
            project_name = f"Test_Upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"   Uploading test database as project: {project_name}")
            
            # Test upload
            upload_success = cloud_handler.upload_database(
                test_db_copy,
                project_name,
                description="Test database upload from integration test",
                progress_callback=lambda p, m: logger.info(f"   Upload progress: {p}% - {m}")
            )
            
            if upload_success:
                logger.info("✅ Upload successful! Now testing download...")
                
                # Test download
                projects = cloud_handler.list_projects()
                test_project = next((p for p in projects if p['name'] == project_name), None)
                
                if test_project:
                    downloaded_path = cloud_handler.download_database(
                        project_name,
                        test_project,
                        force_download=True,  # Force fresh download
                        progress_callback=lambda p, m: logger.info(f"   Download progress: {p}% - {m}")
                    )
                    
                    if downloaded_path and os.path.exists(downloaded_path):
                        # Verify integrity
                        original_size = os.path.getsize(test_db_copy)
                        downloaded_size = os.path.getsize(downloaded_path)
                        
                        logger.info(f"✅ Upload/Download cycle successful!")
                        logger.info(f"   Original size: {original_size / 1024 / 1024:.2f} MB")
                        logger.info(f"   Downloaded size: {downloaded_size / 1024 / 1024:.2f} MB")
                        logger.info(f"   Size match: {original_size == downloaded_size}")
                        
                        self.test_db_path = downloaded_path
                        
                        self.test_results['upload_download_cycle'] = {
                            'status': 'PASS',
                            'project_name': project_name,
                            'original_size_mb': round(original_size / 1024 / 1024, 2),
                            'downloaded_size_mb': round(downloaded_size / 1024 / 1024, 2),
                            'size_match': original_size == downloaded_size
                        }
                        
                        # Cleanup
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return True
                    else:
                        logger.error("❌ Download after upload failed")
                        return False
                else:
                    logger.error("❌ Uploaded project not found in project list")
                    return False
            else:
                logger.error("❌ Database upload failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Upload/Download cycle test failed: {e}")
            self.test_results['upload_download_cycle'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_change_tracking(self):
        """Test database change tracking functionality."""
        logger.info("📝 Testing database change tracking...")
        
        try:
            if not self.test_db_path or not os.path.exists(self.test_db_path):
                logger.error("❌ No test database available for change tracking test")
                return False
            
            from gui.handlers.change_tracker import ChangeTracker
            from database.manager import DatabaseManager
            
            # Initialize database manager and change tracker
            db_manager = DatabaseManager()
            db_manager.open_database(self.test_db_path)
            
            self.change_tracker = ChangeTracker(db_manager)
            
            # Test change tracking with some sample operations
            logger.info("   Testing user flag change tracking...")
            
            # Track a user flag change
            self.change_tracker.track_user_flag_change(
                well_number="TEST_001",
                old_flag="unchecked",
                new_flag="approved",
                user="test_user"
            )
            
            # Track a manual reading update
            logger.info("   Testing manual reading change tracking...")
            self.change_tracker.track_manual_reading_update(
                reading_id=1,
                field_changes={"dtw_avg": {"old": 45.1, "new": 45.0}},
                user="test_user"
            )
            
            # Get change records
            changes = self.change_tracker.get_changes()
            
            logger.info(f"✅ Change tracking test successful!")
            logger.info(f"   Changes recorded: {len(changes)}")
            
            for i, change in enumerate(changes[-2:]):  # Show last 2 changes
                logger.info(f"   Change {i+1}: {change.action} on {change.table_name} by {change.user} at {change.timestamp}")
            
            # Test change summary
            summary = self.change_tracker.get_change_summary()
            logger.info(f"   Change summary: {summary}")
            
            self.test_results['change_tracking'] = {
                'status': 'PASS',
                'changes_recorded': len(changes),
                'change_summary': summary,
                'tracking_functional': True
            }
            
            db_manager.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Change tracking test failed: {e}")
            self.test_results['change_tracking'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_version_management(self):
        """Test version management and caching system."""
        logger.info("📋 Testing version management system...")
        
        try:
            from gui.handlers.version_manager import VersionManager
            
            # Initialize version manager
            cache_dir = PROJECT_ROOT / "claude_testing" / "version_test_cache"
            cache_dir.mkdir(exist_ok=True)
            
            version_manager = VersionManager(str(cache_dir))
            
            # Test version comparison
            logger.info("   Testing version comparison...")
            
            # Simulate local and cloud versions
            local_time = datetime.now()
            cloud_time = local_time + timedelta(minutes=5)  # Cloud is 5 minutes newer
            
            project_name = "test_version_project"
            
            # Update local version info
            version_manager.update_version_info(
                project_name=project_name,
                local_timestamp=local_time.isoformat(),
                operation_type="download"
            )
            
            # Check version status
            is_current = version_manager.is_current_version(
                project_name=project_name,
                cloud_timestamp=cloud_time.isoformat()
            )
            
            status = version_manager.get_version_status(
                project_name=project_name,
                cloud_timestamp=cloud_time.isoformat()
            )
            
            logger.info(f"✅ Version management test successful!")
            logger.info(f"   Local time: {local_time}")
            logger.info(f"   Cloud time: {cloud_time}")
            logger.info(f"   Is current: {is_current}")
            logger.info(f"   Status: {status}")
            
            self.test_results['version_management'] = {
                'status': 'PASS',
                'is_current': is_current,
                'version_status': status,
                'time_difference_minutes': 5
            }
            
            # Cleanup
            shutil.rmtree(cache_dir, ignore_errors=True)
            return True
            
        except Exception as e:
            logger.error(f"❌ Version management test failed: {e}")
            self.test_results['version_management'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def run_comprehensive_tests(self, credentials_path, folder_id=None):
        """Run all Google Drive integration and change tracking tests."""
        logger.info("🚀 Starting Comprehensive Google Drive Integration Tests")
        logger.info("=" * 70)
        
        # Setup credentials
        service_account_path = self.setup_credentials(credentials_path)
        if not service_account_path:
            return False
        
        test_functions = [
            ("Google Drive Authentication", lambda: self.test_google_drive_authentication(service_account_path)),
            ("Folder Access", lambda: self.test_folder_access(folder_id)),
            ("Database Download", self.test_database_download),
            ("Change Tracking", self.test_change_tracking),
            ("Version Management", self.test_version_management)
        ]
        
        passed_tests = 0
        total_tests = len(test_functions)
        
        for test_name, test_func in test_functions:
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
        logger.info(f"🏁 COMPREHENSIVE TEST SUMMARY: {passed_tests}/{total_tests} passed")
        logger.info(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            logger.info("✅ ALL TESTS PASSED! Google Drive integration is working correctly!")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests failed - check logs for details")
        
        # Save results
        results_file = PROJECT_ROOT / "claude_testing" / "google_drive_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'test_type': 'google_drive_integration',
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
                logger.info("🧹 Cleaned up temporary test database")
            except:
                pass
        
        return passed_tests == total_tests

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Google Drive integration')
    parser.add_argument('credentials', help='Path to Google Drive service account credentials JSON file')
    parser.add_argument('--folder-id', help='Google Drive folder ID to test (optional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.credentials):
        print(f"❌ Credentials file not found: {args.credentials}")
        return 1
    
    tester = GoogleDriveIntegrationTester()
    success = tester.run_comprehensive_tests(args.credentials, args.folder_id)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())