#!/usr/bin/env python3
"""
Simple Version Debug

Just test the VersionManager directly
"""

import os
import sys

# Add project root to path
sys.path.append('/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system')

def simple_version_debug():
    """Test VersionManager directly"""
    
    try:
        from src.gui.handlers.version_manager import VersionManager
        
        print("🔍 TESTING VERSION MANAGER DIRECTLY")
        print("=" * 40)
        
        # Initialize version manager
        temp_dir = '/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system/temp'
        version_manager = VersionManager(temp_dir)
        
        # Test the comparison
        project_name = "CAESER_GENERAL"
        cloud_version_time = "2025-06-28T00:49:08.513Z"
        
        print(f"📋 Testing for {project_name}")
        print(f"🕐 Cloud version time: {cloud_version_time}")
        print("")
        
        # Get local version info
        local_info = version_manager.get_local_version_info(project_name)
        print(f"📊 Local version info: {local_info}")
        
        if local_info:
            local_db_path = local_info.get('local_db_path', '')
            print(f"📁 Local DB path: {local_db_path}")
            print(f"📂 File exists: {os.path.exists(local_db_path)}")
        
        print("")
        
        # Test comparison
        comparison = version_manager.compare_versions(project_name, cloud_version_time)
        print("🎯 VERSION COMPARISON RESULT:")
        print("-" * 30)
        for key, value in comparison.items():
            print(f"   {key}: {value}")
        
        print("")
        print("🎨 DIALOG DECISION:")
        local_db_exists = comparison.get('local_db_exists', False)
        print(f"   local_db_exists: {local_db_exists}")
        
        if local_db_exists:
            print("   ✅ VERSION CHOICE DIALOG SHOULD APPEAR!")
        else:
            print("   ❌ No dialog - will proceed with direct download")
            print(f"   📝 Reason: {comparison.get('message', 'Unknown')}")
        
        return comparison
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    simple_version_debug()