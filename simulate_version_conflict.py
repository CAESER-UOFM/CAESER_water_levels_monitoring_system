#!/usr/bin/env python3
"""
Version Conflict Simulator

This script simulates another user modifying the cloud database by directly
updating the modification time on Google Drive. This allows us to test the
version conflict resolution system.

Usage:
1. Download and work with a cloud database
2. Run this script to simulate another user's changes
3. Try to save your changes - should trigger conflict resolution
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append('/Users/bmac/Library/CloudStorage/OneDrive-TheUniversityofMemphis/UofM/CAESER/2025/CAESER_water_levels_monitoring_system')

from src.gui.handlers.google_drive_service import GoogleDriveService
from src.gui.handlers.settings_handler import SettingsHandler

def simulate_version_conflict(project_name='CAESER_GENERAL'):
    """
    Simulate a version conflict by updating the cloud database modification time.
    This mimics another user making changes to the cloud database.
    """
    print(f"🔄 Simulating version conflict for project: {project_name}")
    
    try:
        # Initialize services
        settings_handler = SettingsHandler()
        drive_service = GoogleDriveService(settings_handler)
        
        # Authenticate
        if not drive_service.authenticated:
            print("❌ Google Drive not authenticated. Please authenticate first.")
            return False
        
        service = drive_service.get_service()
        if not service:
            print("❌ Could not get Google Drive service.")
            return False
        
        # Find the project database
        query = f"name='{project_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, fields="files(id, name)").execute()
        projects = response.get('files', [])
        
        if not projects:
            print(f"❌ Project '{project_name}' not found.")
            return False
        
        project_folder_id = projects[0]['id']
        print(f"✅ Found project folder: {project_folder_id}")
        
        # Find the database file
        db_query = f"'{project_folder_id}' in parents and name='{project_name}.db' and trashed=false"
        response = service.files().list(q=db_query, fields="files(id, name, modifiedTime)").execute()
        db_files = response.get('files', [])
        
        if not db_files:
            print(f"❌ Database file '{project_name}.db' not found.")
            return False
        
        db_file = db_files[0]
        print(f"✅ Found database file: {db_file['id']}")
        print(f"📅 Current modification time: {db_file['modifiedTime']}")
        
        # Update the file to trigger a new modification time
        # We'll update the description to simulate another user's change
        current_time = datetime.now().isoformat()
        
        file_metadata = {
            'description': f'Version conflict simulation - Updated at {current_time} by conflict simulator'
        }
        
        updated_file = service.files().update(
            fileId=db_file['id'],
            body=file_metadata,
            fields='id,modifiedTime'
        ).execute()
        
        print(f"✅ Simulated version conflict!")
        print(f"📅 New modification time: {updated_file['modifiedTime']}")
        print(f"🔄 The cloud database now appears to have been modified by another user.")
        print("")
        print("🧪 **NOW TEST VERSION CONFLICT RESOLUTION:**")
        print("1. Make some changes in your local application")
        print("2. Try to save to cloud")
        print("3. You should see the version conflict dialog!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error simulating version conflict: {e}")
        logging.error(f"Version conflict simulation error: {e}")
        return False

if __name__ == '__main__':
    project_name = sys.argv[1] if len(sys.argv) > 1 else 'CAESER_GENERAL'
    
    print("🧪 **VERSION CONFLICT SIMULATOR**")
    print("=" * 50)
    print(f"Target project: {project_name}")
    print("")
    
    success = simulate_version_conflict(project_name)
    
    if success:
        print("\n✅ Version conflict simulation complete!")
        print("Now try to save changes in your application to test conflict resolution.")
    else:
        print("\n❌ Version conflict simulation failed.")
        sys.exit(1)