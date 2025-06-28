#!/usr/bin/env python3
"""
Check Version Status

Check what version tracking files we have and current status.
"""

import os
import sys
import json

# Add project root to path
sys.path.append('/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system')

def check_version_status():
    """Check current version tracking status"""
    
    print("🔍 CHECKING VERSION TRACKING STATUS")
    print("=" * 50)
    
    temp_dir = "/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system/temp"
    
    # Check version metadata file
    version_metadata_file = os.path.join(temp_dir, 'version_metadata.json')
    
    print("📁 FILES IN TEMP DIRECTORY:")
    if os.path.exists(temp_dir):
        items = os.listdir(temp_dir)
        for item in items:
            if 'CAESER_GENERAL' in item or item == 'version_metadata.json':
                file_path = os.path.join(temp_dir, item)
                if os.path.isfile(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"   📄 {item} ({size_mb:.1f} MB)")
    
    print("\n📊 VERSION METADATA:")
    if os.path.exists(version_metadata_file):
        try:
            with open(version_metadata_file, 'r') as f:
                metadata = json.load(f)
            
            print("✅ version_metadata.json exists!")
            
            if 'CAESER_GENERAL' in metadata:
                caeser_info = metadata['CAESER_GENERAL']
                print(f"   🎯 CAESER_GENERAL tracking:")
                print(f"      • Local version time: {caeser_info.get('local_version_time', 'Unknown')}")
                print(f"      • Last sync time: {caeser_info.get('last_sync_time', 'Unknown')}")
                print(f"      • Local DB path: {caeser_info.get('local_db_path', 'Unknown')}")
                print(f"      • File size: {caeser_info.get('file_size_mb', 0)} MB")
                print(f"      • Operation: {caeser_info.get('operation', 'Unknown')}")
                print(f"      • Is current: {caeser_info.get('is_current', 'Unknown')}")
                
                # Check if the tracked file actually exists
                local_path = caeser_info.get('local_db_path', '')
                if local_path and os.path.exists(local_path):
                    print(f"      ✅ Local database file exists")
                else:
                    print(f"      ❌ Local database file missing!")
            else:
                print("   ❌ No CAESER_GENERAL tracking found")
                
        except Exception as e:
            print(f"   ❌ Error reading metadata: {e}")
    else:
        print("❌ version_metadata.json not found")
    
    print("\n🎯 NEXT STEPS TO TEST VERSION CHOICE:")
    print("-" * 40)
    print("1. 🔄 Close the current app")
    print("2. 🚀 Reopen: python3 src/main.py")
    print("3. 📂 Go to Cloud Database → CAESER_GENERAL")
    print("4. 🎨 Should see VERSION CHOICE DIALOG!")
    print("5. ✅ Choose 'Use Local Cache' → Instant load!")
    
    print("\n💡 WHAT THE VERSION DIALOG WILL SHOW:")
    print("• 📅 Your local version timestamp")
    print("• ☁️ Current cloud version timestamp") 
    print("• ✅ 'Use Local Cache (Recommended)' - since you just downloaded")
    print("• ⚡ Instant loading if you choose cache")
    
    return True

if __name__ == '__main__':
    check_version_status()