#!/usr/bin/env python3
"""
Verify Clean Start

This script verifies that the system is ready for fresh testing:
1. No cached database files
2. No temp files
3. No draft files
4. Clean draft system ready
"""

import os
import sys
import glob

# Add project root to path
sys.path.append('/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system')

def check_clean_start():
    """Verify the system is clean for fresh testing"""
    
    base_path = '/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system'
    
    print("🧪 VERIFYING CLEAN START FOR TESTING")
    print("=" * 50)
    
    # Check 1: No cached CAESER_GENERAL files
    print("1. Checking for cached database files...")
    caeser_files = glob.glob(f"{base_path}/**/CAESER_GENERAL*", recursive=True)
    if caeser_files:
        print(f"❌ Found cached files: {caeser_files}")
        return False
    else:
        print("✅ No cached CAESER_GENERAL files found")
    
    # Check 2: No temp WAL/SHM files
    print("\n2. Checking for temp WAL/SHM files...")
    temp_files = glob.glob(f"{base_path}/temp/wlm_*.db-*")
    if temp_files:
        print(f"❌ Found temp files: {temp_files}")
        return False
    else:
        print("✅ No temp WAL/SHM files found")
    
    # Check 3: No draft files
    print("\n3. Checking for draft files...")
    draft_files = glob.glob(f"{base_path}/**/drafts/**", recursive=True)
    if draft_files:
        print(f"⚠️ Found draft files: {draft_files}")
        print("   (This is ok - draft system is ready)")
    else:
        print("✅ No existing draft files")
    
    # Check 4: Test imports
    print("\n4. Testing system imports...")
    try:
        from src.gui.handlers.cloud_database_handler import CloudDatabaseHandler
        from src.gui.handlers.draft_manager import DraftManager
        from src.gui.dialogs.version_conflict_dialog import VersionConflictDialog
        print("✅ All systems import successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Check 5: Verify temp folder contents
    print("\n5. Checking temp folder contents...")
    temp_contents = os.listdir(f"{base_path}/temp")
    expected_files = ['CAESER_WEB_OPTIMIZED.db', 'SANDY_CREEK.db', 'SINGLE_WELL_TEST.db']
    unexpected_files = [f for f in temp_contents if f not in expected_files]
    
    if unexpected_files:
        print(f"⚠️ Unexpected files in temp: {unexpected_files}")
    
    print(f"📁 Temp folder contains: {len(temp_contents)} files")
    for f in temp_contents:
        if 'CAESER_GENERAL' not in f:
            print(f"   📄 {f}")
    
    print("\n" + "=" * 50)
    print("🎉 SYSTEM IS CLEAN AND READY FOR TESTING!")
    print("\n📋 WHAT TO TEST:")
    print("1. Launch application")
    print("2. Open Cloud Database → CAESER_GENERAL")
    print("3. Make changes to test local draft system")
    print("4. Test save operations and version control")
    print("5. Verify WAL/SHM cleanup after operations")
    
    print("\n🎯 EXPECTED BEHAVIORS:")
    print("✅ Fresh download (no existing cache)")
    print("✅ Single temp file created (no duplicates)")
    print("✅ Local changes saved as drafts automatically")
    print("✅ Version conflict detection if cloud changes")
    print("✅ Clean WAL/SHM cleanup after operations")
    
    return True

if __name__ == '__main__':
    success = check_clean_start()
    sys.exit(0 if success else 1)