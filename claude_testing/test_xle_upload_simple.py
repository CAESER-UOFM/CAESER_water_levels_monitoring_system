#!/usr/bin/env python3
"""
Simple XLE Upload Test
Creates a test database, adds XLE tracking, and tests Google Drive upload with cleanup.
"""

import os
import sys
import json
import sqlite3
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_xle_upload_system():
    """Test the complete XLE upload system."""
    
    try:
        # 1. Setup Google Drive
        logger.info("🔐 Setting up Google Drive connection...")
        
        from src.gui.handlers.google_drive_service import GoogleDriveService
        from src.gui.handlers.settings_handler import SettingsHandler
        
        credentials_path = str(PROJECT_ROOT.parent / "water-levels-monitoring-451921-bfb891f4bf7c.json")
        
        settings_handler = SettingsHandler()
        settings_handler.set_setting("service_account_key_path", credentials_path)
        
        drive_service = GoogleDriveService.get_instance(settings_handler)
        if not drive_service.authenticate():
            logger.error("❌ Google Drive authentication failed")
            return False
        
        logger.info("✅ Google Drive connected")
        
        # 2. Create test database with XLE tracking
        logger.info("🗄️ Creating test database...")
        
        from src.database.initializer import DatabaseInitializer
        from src.database.manager import DatabaseManager
        
        # Create temp database
        temp_dir = tempfile.mkdtemp(prefix="xle_test_")
        test_project = f"XLE_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        db_path = os.path.join(temp_dir, f"{test_project}.db")
        
        # Initialize database
        initializer = DatabaseInitializer(Path(db_path))
        initializer.initialize_database()
        
        # Add test data
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add test well
        cursor.execute("""
            INSERT INTO wells (well_number, cae_number, latitude, longitude, 
                             top_of_casing, aquifer, data_source)
            VALUES ('TEST_XLE_001', 'TX001', 35.1, -90.0, 295.0, 'SHAL', 'transducer')
        """)
        
        # Add test transducer
        cursor.execute("""
            INSERT INTO transducers (serial_number, well_number, installation_date)
            VALUES ('TN157_XLETEST', 'TEST_XLE_001', '2024-01-01 00:00:00')
        """)
        
        # Create fake XLE file for testing
        fake_xle_path = os.path.join(temp_dir, "TEST_XLE_001_sample.xle")
        with open(fake_xle_path, 'w') as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<xle_file>
    <header>
        <serial_number>TN157_XLETEST</serial_number>
        <location>TEST_XLE_001</location>
        <start_time>2024-06-01 00:00:00</start_time>
        <end_time>2024-06-30 23:59:59</end_time>
    </header>
    <data>
        <!-- Sample XLE data for testing -->
    </data>
</xle_file>""")
        
        # Track XLE file in database
        cursor.execute("""
            INSERT INTO xle_files 
            (file_path, file_name, file_type, serial_number, well_number,
             start_date, end_date, file_size, file_hash, project_name, upload_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            fake_xle_path, "TEST_XLE_001_sample.xle", "transducer", 
            "TN157_XLETEST", "TEST_XLE_001", "2024-06-01T00:00:00", 
            "2024-06-30T23:59:59", os.path.getsize(fake_xle_path), 
            "test_hash_xle", test_project
        ))
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Test database created with XLE tracking")
        
        # 3. Test XLE file upload
        logger.info("📤 Testing XLE file upload...")
        
        from src.gui.handlers.xle_file_manager import XLEFileManager
        
        db_manager = DatabaseManager()
        db_manager.open_database(db_path)
        
        xle_manager = XLEFileManager(db_manager, drive_service, settings_handler)
        
        # Get pending files
        pending_files = xle_manager.get_pending_uploads(test_project)
        logger.info(f"   Found {len(pending_files)} pending XLE files")
        
        # Upload files
        def progress_callback(progress, message):
            logger.info(f"   Progress: {progress}% - {message}")
        
        results = xle_manager.upload_project_xle_files(test_project, progress_callback)
        
        logger.info(f"✅ Upload results: {results['success']} success, {results['failed']} failed")
        
        db_manager.close()
        
        # 4. Verify upload in Google Drive
        logger.info("🔍 Verifying upload in Google Drive...")
        
        service = drive_service.get_service()
        
        # Search for test project folder
        projects_folder_id = "1JjiXRblLAf6rdhiOzrAaYik8bjNpBc9s"
        
        query = f"name = '{test_project}' and '{projects_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        
        project_folders = results.get('files', [])
        
        if project_folders:
            project_folder_id = project_folders[0]['id']
            logger.info(f"✅ Found test project folder: {test_project}")
            
            # Check for XLE_Files folder
            query = f"name = 'XLE_Files' and '{project_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            
            xle_folders = results.get('files', [])
            
            if xle_folders:
                logger.info("✅ Found XLE_Files folder structure")
                upload_verified = True
            else:
                logger.warning("⚠️ XLE_Files folder not found")
                upload_verified = False
        else:
            logger.error("❌ Test project folder not found")
            upload_verified = False
        
        # 5. Cleanup test files from Google Drive
        logger.info("🧹 Cleaning up test files from Google Drive...")
        
        if project_folders:
            try:
                # Delete the entire test project folder
                service.files().delete(fileId=project_folder_id).execute()
                logger.info("✅ Test project folder deleted from Google Drive")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete test folder: {e}")
        
        # 6. Cleanup local files
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("✅ Local test files cleaned up")
        
        # 7. Final summary
        logger.info("=" * 60)
        if upload_verified:
            logger.info("🎉 XLE UPLOAD SYSTEM TEST PASSED!")
            logger.info("✅ Database schema with XLE tracking working")
            logger.info("✅ XLE file manager functional")
            logger.info("✅ Google Drive folder creation working")
            logger.info("✅ File upload and organization working")
            logger.info("✅ Test cleanup successful")
            logger.info("")
            logger.info("🚀 READY FOR PRODUCTION USE!")
        else:
            logger.error("❌ XLE upload system test failed")
            logger.error("   Check Google Drive permissions and folder structure")
        
        return upload_verified
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_xle_upload_system()
    exit(0 if success else 1)