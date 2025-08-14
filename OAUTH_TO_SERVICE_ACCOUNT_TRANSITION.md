# Google Drive OAuth to Service Account Transition

## Overview
This document describes the major refactoring work to remove Google Drive OAuth 2.0 dependencies and transition to service account authentication for SOLINST folder access only.

## Background & Motivation

### Why Remove OAuth 2.0?
1. **Google removed storage quota for service accounts** - OAuth 2.0 databases became unsustainable
2. **Database replication issues** - OAuth 2.0 caused file replication for multiple users
3. **Stale data problems** - Google Drive data was no longer being updated but app still used it as fallback
4. **SMOO primary system** - Users with SMOO access already have full system connectivity

### New Architecture
- **Primary system**: SMOO shared drive (S:/) for all database operations
- **Service account**: Only for SOLINST folder monitoring and XLE file transfer
- **No OAuth**: Complete removal of Google Drive OAuth authentication flows

## Work Completed (Branch: `remove-oauth-google-drive`)

### Phase 1: OAuth Removal
**Files Modified**: `src/gui/main_window.py`, `src/gui/handlers/user_auth_service.py`

**Changes Made**:
1. **Removed Google Drive service initialization**
   ```python
   # REMOVED: self.drive_service = GoogleDriveService.get_instance(self.settings_handler)
   ```

2. **Removed OAuth authentication flows**
   - `authenticate_google_drive()` method
   - `_check_drive_and_continue_init()` method  
   - `handle_drive_login()` method

3. **Disabled OAuth-dependent features**
   - AutoUpdateHandler with Google Drive dependency
   - Feedback system (temporarily)
   - Google Drive credential setup flows

4. **Updated UserAuthService**
   - Modified to accept `None` for drive_service parameter
   - Maintains local user authentication without Google Drive dependency

### Phase 2: UI Cleanup  
**Changes Made**:
1. **Menu bar cleanup**
   - Removed "Check for Updates" (OAuth dependent)
   - Removed "Setup Google Credentials" 
   - Changed "Google Drive Setup" → "Service Account Setup (XLE Sync)"

2. **Error handling updates**
   - Replaced OAuth authentication checks with service account messages
   - Updated user-facing messages about transition

### Phase 3: SMOO Integration Fix
**Problem**: After OAuth removal, cloud database handler wasn't initializing, causing empty dropdown menus.

**Solution**: 
```python
def _finish_initialization(self):
    # Initialize cloud database handler for SMOO/shared drive access
    self.progress_dialog.setValue(65)
    self.progress_dialog.setLabelText("Initializing cloud database handler...")
    self._initialize_cloud_database_handler()
```

**Result**: SMOO shared drive projects now populate dropdown menu correctly.

## Current Status (✅ Working)

### What Works
- ✅ **Application startup** - Clean launch without OAuth prompts
- ✅ **User authentication** - Local admin/user login system
- ✅ **SMOO integration** - S: drive databases populate dropdown  
- ✅ **Local databases** - All local operations functional
- ✅ **Draft system** - Load/save/modify tracking works
- ✅ **All tabs initialize** - No missing dependencies

### What's Disabled (Intentionally)
- ❌ **AutoUpdateHandler** - Requires service account adaptation
- ❌ **Feedback system** - Temporarily disabled during transition
- ❌ **Google Drive OAuth features** - Completely removed

## SOLINST Folder Functionality (Preserved for Service Account)

### Files Preserved
1. **`FieldDataConsolidator`** (`src/gui/handlers/field_data_consolidator.py`)
   - Consolidates XLE files from SOLINST folder to organized structure
   - Currently uses OAuth - needs service account adaptation

2. **`GoogleDriveMonitor`** (`src/gui/handlers/google_drive_monitor.py`) 
   - Monitors SOLINST folder for new XLE files
   - Currently uses OAuth - needs service account adaptation

3. **Auto-sync menu structure** - Preserved but disabled pending service account implementation

### Service Account Implementation Needed
The following functionality needs to be rebuilt with service account:
- **SOLINST folder access** - Read XLE files from Google Drive SOLINST folder
- **File transfer to SMOO** - Move consolidated files to SMOO shared drive
- **Metadata processing** - Extract and organize XLE file metadata

## Troubleshooting Guide

### Application Won't Start
**Symptoms**: Import errors, missing modules
**Solution**: Check for uncommitted OAuth removal - some references may remain
**Command**: `python3 -m py_compile src/gui/main_window.py`

### Empty Dropdown Menu
**Symptoms**: No cloud projects showing in database dropdown
**Solution**: Check SMOO shared drive access
**Logs to check**:
```
- "Checking shared drive access..."
- "Shared drive accessible - using SharedDriveDbHandler" ✅
- "Shared drive root path not accessible" ❌
```

### Cloud Features Not Working  
**Symptoms**: "Cloud database handler is None" warnings
**Expected**: This is normal - OAuth cloud features are disabled
**Action**: Verify SMOO shared drive handler is working instead

### Login Issues
**Symptoms**: Authentication failures
**Solution**: UserAuthService should work with `None` drive_service
**Check**: `user_auth_service.py` accepts None parameter

## Next Steps (When Resuming Work)

### Immediate: Service Account Handler
1. **Create service account handler** (`src/gui/handlers/google_service_account.py`)
   - Simple Google Drive API access with service account key
   - Focus only on SOLINST folder access
   - No database storage operations

2. **Update FieldDataConsolidator**
   - Replace OAuth drive_service with service account handler
   - Modify destination to use SMOO instead of Google Drive folders

3. **Update GoogleDriveMonitor**
   - Replace OAuth authentication with service account
   - Keep SOLINST folder monitoring functionality

### Configuration Needed
- **Service account key file** - JSON credentials for Google Drive API
- **SOLINST folder ID** - Google Drive folder ID to monitor
- **SMOO destination path** - Where to place consolidated files on S: drive

## Testing Protocol

### Startup Test
```bash
python3 main.py
# Expected: Clean startup, admin login works, SMOO projects in dropdown
```

### SMOO Access Test
1. Open application
2. Login as admin  
3. Check dropdown menu for cloud projects
4. Open a cloud database from SMOO
5. Verify read/write operations work

### Error Detection
Monitor logs for:
- `AttributeError` related to missing `drive_service`
- `ImportError` for Google Drive modules
- `ConnectionError` for SMOO access issues

## Files Summary

### Modified Files
- `src/gui/main_window.py` - Major OAuth removal and SMOO integration  
- `src/gui/handlers/user_auth_service.py` - Support for None drive_service
- `main.py` - Logging configuration updates

### Preserved Files (Need Service Account Adaptation)
- `src/gui/handlers/field_data_consolidator.py`
- `src/gui/handlers/google_drive_monitor.py`  
- `src/gui/handlers/solinst_reader.py`

### Created Files
- `OAUTH_TO_SERVICE_ACCOUNT_TRANSITION.md` (this document)

## Branch Information
- **Working branch**: `remove-oauth-google-drive`
- **Status**: Tested and working on Windows with SMOO access
- **Safe to use**: Application fully functional for normal operations
- **Next work**: Service account implementation for SOLINST folder sync

---
*Documentation created: 2025-08-14*  
*Last updated: After successful SMOO integration testing*