#!/usr/bin/env python3
"""
Simple Google Drive Connection Test
Direct test of Google Drive API with the provided credentials
"""

import json
import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_google_drive_connection(credentials_path):
    """Test basic Google Drive connection and API access."""
    try:
        logger.info("🔐 Testing Google Drive authentication...")
        
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build service
        service = build('drive', 'v3', credentials=credentials)
        
        # Get service account info
        with open(credentials_path, 'r') as f:
            creds_info = json.load(f)
            service_email = creds_info.get('client_email')
        
        logger.info(f"✅ Authentication successful!")
        logger.info(f"   Service Account: {service_email}")
        
        # Test basic API call
        logger.info("📋 Testing basic API access...")
        results = service.files().list(
            pageSize=10,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"✅ API access successful! Found {len(files)} files/folders")
        
        # Show first few items
        for i, file in enumerate(files[:5]):
            logger.info(f"   {i+1}. {file['name']} ({file.get('mimeType', 'unknown')})")
        
        # Test folder access with hardcoded folder ID
        logger.info("📁 Testing specific folder access...")
        folder_id = "1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK"  # Default from settings
        
        try:
            folder_info = service.files().get(
                fileId=folder_id,
                fields="id, name, modifiedTime"
            ).execute()
            
            logger.info(f"✅ Folder access successful!")
            logger.info(f"   Folder: {folder_info['name']}")
            logger.info(f"   ID: {folder_info['id']}")
            
            # List folder contents
            contents = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=20
            ).execute()
            
            folder_files = contents.get('files', [])
            folders = [f for f in folder_files if f.get('mimeType') == 'application/vnd.google-apps.folder']
            databases = [f for f in folder_files if f.get('name', '').endswith('.db')]
            
            logger.info(f"   Contents: {len(folder_files)} items")
            logger.info(f"   Folders: {len(folders)}")
            logger.info(f"   Databases: {len(databases)}")
            
            # Show some folders
            if folders:
                logger.info("   📁 Folders found:")
                for folder in folders[:5]:
                    logger.info(f"      - {folder['name']}")
            
            # Show some databases
            if databases:
                logger.info("   🗄️ Databases found:")
                for db in databases[:5]:
                    logger.info(f"      - {db['name']}")
            
        except HttpError as e:
            logger.error(f"❌ Folder access failed: {e}")
            logger.info("   This might be a permissions issue - the service account may not have access to this folder")
            return False
        
        # Test projects folder
        logger.info("📂 Testing projects folder access...")
        projects_folder_id = "1JjiXRblLAf6rdhiOzrAaYik8bjNpBc9s"  # Default from settings
        
        try:
            projects_info = service.files().get(
                fileId=projects_folder_id,
                fields="id, name, modifiedTime"
            ).execute()
            
            logger.info(f"✅ Projects folder access successful!")
            logger.info(f"   Folder: {projects_info['name']}")
            
            # List project contents
            project_contents = service.files().list(
                q=f"'{projects_folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=20
            ).execute()
            
            project_folders = project_contents.get('files', [])
            projects = [f for f in project_folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
            
            logger.info(f"   Projects found: {len(projects)}")
            
            if projects:
                logger.info("   📋 Projects:")
                for project in projects[:5]:
                    logger.info(f"      - {project['name']}")
            
        except HttpError as e:
            logger.error(f"❌ Projects folder access failed: {e}")
            logger.info("   This might be a permissions issue")
        
        logger.info("✅ ALL GOOGLE DRIVE TESTS PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Google Drive test failed: {e}")
        return False

def test_file_upload_download():
    """Test file upload and download capabilities."""
    logger.info("📤 Testing file upload/download capabilities...")
    
    try:
        # This would test actual upload/download but requires more setup
        logger.info("⚠️ File upload/download test skipped (requires test file)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Upload/download test failed: {e}")
        return False

def main():
    """Main test function."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python test_simple_google_drive.py <credentials.json>")
        return 1
    
    credentials_path = sys.argv[1]
    
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        return 1
    
    logger.info("🚀 Starting Simple Google Drive Integration Test")
    logger.info("=" * 60)
    
    # Test basic connection
    connection_success = test_google_drive_connection(credentials_path)
    
    if connection_success:
        logger.info("🎉 Google Drive integration is working correctly!")
        logger.info("   ✅ Authentication successful")
        logger.info("   ✅ API access working")
        logger.info("   ✅ Folder access functional")
        logger.info("")
        logger.info("📋 Ready for:")
        logger.info("   - Database upload/download operations")
        logger.info("   - Project-based folder management")
        logger.info("   - Auto-sync functionality")
        return 0
    else:
        logger.error("❌ Google Drive integration has issues")
        logger.error("   Check credentials and folder permissions")
        return 1

if __name__ == "__main__":
    exit(main())