#!/usr/bin/env python3
"""
Debug Version Check

Test what check_version_status returns for CAESER_GENERAL
"""

import os
import sys

# Add project root to path
sys.path.append('/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system')

def debug_version_check():
    """Test version checking logic directly"""
    
    try:
        from src.gui.handlers.cloud_database_handler import CloudDatabaseHandler
        from src.gui.handlers.google_drive_service import GoogleDriveService
        from src.gui.handlers.settings_handler import SettingsHandler
        
        print("🔍 DEBUGGING VERSION CHECK")
        print("=" * 40)
        
        # Initialize handlers
        settings_handler = SettingsHandler()
        drive_service = GoogleDriveService(settings_handler)
        cloud_handler = CloudDatabaseHandler(drive_service, '/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system/temp')
        
        # Simulate the cloud version time we get from project info
        cloud_version_time = "2025-06-28T00:49:08.513Z"
        project_name = "CAESER_GENERAL"
        
        print(f"📋 Testing check_version_status for {project_name}")
        print(f"🕐 Cloud version time: {cloud_version_time}")
        print("")
        
        # Call the same method that main_window calls
        version_comparison = cloud_handler.check_version_status(project_name, cloud_version_time)
        
        print("🎯 VERSION COMPARISON RESULT:")
        print("-" * 30)
        for key, value in version_comparison.items():
            print(f"   {key}: {value}")
        
        print("")
        print("🎨 DIALOG DECISION:")
        local_db_exists = version_comparison.get('local_db_exists', False)
        print(f"   local_db_exists: {local_db_exists}")
        
        if local_db_exists:
            print("   ✅ VERSION CHOICE DIALOG SHOULD APPEAR!")
        else:
            print("   ❌ No dialog - will proceed with direct download")
        
        return version_comparison
        
    except Exception as e:
        print(f"❌ Error debugging version check: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    debug_version_check()