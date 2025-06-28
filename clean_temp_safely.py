#!/usr/bin/env python3
"""
Clean Temp Folder Safely

Removes old temp files while preserving essential cache files.
"""

import os
import sys
import glob
from pathlib import Path

def clean_temp_safely():
    """Clean temp folder while preserving essential files"""
    
    temp_dir = "/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system/temp"
    
    print("🧹 CLEANING TEMP FOLDER SAFELY")
    print("=" * 40)
    
    # Files to KEEP (essential for caching system)
    keep_files = {
        'CAESER_GENERAL.db',           # Stable cache
        'CAESER_GENERAL_metadata.json', # Cache metadata  
        'version_metadata.json',       # Version tracking
        'SANDY_CREEK.db',              # Other project cache
        'SANDY_CREEK_metadata.json'   # Other project metadata
    }
    
    # Get current size
    total_size_before = sum(os.path.getsize(os.path.join(temp_dir, f)) 
                           for f in os.listdir(temp_dir) 
                           if os.path.isfile(os.path.join(temp_dir, f)))
    
    print(f"📊 Current temp folder size: {total_size_before / (1024**3):.1f} GB")
    print("")
    
    print("✅ KEEPING (Essential):")
    for keep_file in keep_files:
        file_path = os.path.join(temp_dir, keep_file)
        if os.path.exists(file_path):
            size_mb = os.path.getsize(file_path) / (1024**2)
            print(f"   📁 {keep_file} ({size_mb:.1f} MB)")
    print("")
    
    print("🗑️  REMOVING (Temporary):")
    removed_files = []
    removed_size = 0
    
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        
        if not os.path.isfile(file_path):
            continue
            
        # Skip essential files
        if filename in keep_files:
            continue
            
        # Remove temp files
        if (filename.startswith('wlm_') or 
            filename.endswith('.db-shm') or 
            filename.endswith('.db-wal') or
            filename.endswith('.tmp')):
            
            size = os.path.getsize(file_path)
            size_mb = size / (1024**2)
            
            try:
                os.remove(file_path)
                removed_files.append(filename)
                removed_size += size
                print(f"   🗑️  {filename} ({size_mb:.1f} MB)")
            except Exception as e:
                print(f"   ❌ Failed to remove {filename}: {e}")
    
    total_size_after = sum(os.path.getsize(os.path.join(temp_dir, f)) 
                          for f in os.listdir(temp_dir) 
                          if os.path.isfile(os.path.join(temp_dir, f)))
    
    print("")
    print("📊 CLEANUP SUMMARY:")
    print(f"   Files removed: {len(removed_files)}")
    print(f"   Space freed: {removed_size / (1024**3):.1f} GB")
    print(f"   Before: {total_size_before / (1024**3):.1f} GB")
    print(f"   After: {total_size_after / (1024**3):.1f} GB")
    print("")
    
    print("✅ TEMP FOLDER CLEANED!")
    print("Essential cache files preserved for fast loading.")
    
    return len(removed_files) > 0

if __name__ == '__main__':
    success = clean_temp_safely()
    if success:
        print("\n🎉 Cleanup complete! Ready to test upload with clean temp folder.")
    else:
        print("\n💡 No temp files to clean - folder is already tidy.")