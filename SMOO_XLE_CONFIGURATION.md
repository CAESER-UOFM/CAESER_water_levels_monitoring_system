# SMOO XLE File Configuration Guide

## Overview

This document describes the configuration and structure for the new SMOO XLE file workflow implemented to handle XLE files differently for local versus shared databases.

## XLE File Workflow Summary

### Local Databases
- **Storage Type**: Permanent storage
- **Location**: `imported_xle_files/{DATABASE_NAME}/`
- **Structure**:
  ```
  imported_xle_files/
  └── {DATABASE_NAME}/
      ├── barologgers/
      │   └── {SERIAL_NUMBER}/
      │       └── {LOCATION}_{START_DATE}_To_{END_DATE}.xle
      └── transducers/
          └── {WELL_NUMBER}/
              └── {LOCATION}_{START_DATE}_To_{END_DATE}.xle
  ```

### Shared Databases (wlm_ prefix)
- **Storage Type**: Temporary during draft phase → SMOO structure on push
- **Temp Location**: `cache/temp_xle_files/{PROJECT_NAME}/`
- **SMOO Location**: `{SHARED_DRIVE}/Projects/{PROJECT_NAME}/XLE_Files/`
- **Structure**:
  ```
  # Temp Storage (during draft phase):
  cache/temp_xle_files/
  └── {PROJECT_NAME}/
      ├── barologger/
      │   └── {UNIQUE_ID}_{LOCATION}_{START_DATE}_To_{END_DATE}.xle
      └── transducer/
          └── {UNIQUE_ID}_{LOCATION}_{START_DATE}_To_{END_DATE}.xle
  
  # SMOO Structure (after database push):
  {SHARED_DRIVE}/Projects/{PROJECT_NAME}/XLE_Files/
  ├── barologgers/
  │   └── {SERIAL_NUMBER}/
  │       └── {LOCATION}_{START_DATE}_To_{END_DATE}.xle
  └── transducers/
      └── {WELL_NUMBER}/
          └── {LOCATION}_{START_DATE}_To_{END_DATE}.xle
  ```

## Configuration Settings

### Required Settings (settings.json)

#### 1. XLE Import Directory (Local Databases)
```json
{
  "xle_import_directory": "/path/to/imported_xle_files"
}
```
- **Purpose**: Base directory for permanent XLE file storage for local databases
- **Default**: `{APP_DIR}/imported_xle_files`
- **Used by**: XLEFileOrganizer for local database mode

#### 2. Shared Drive Root (Shared Databases)
```json
{
  "shared_drive_root": "/path/to/shared/drive"
}
```
- **Purpose**: Root directory of the shared drive containing Projects folder
- **Required for**: Shared database SMOO push functionality
- **Used by**: SharedDriveDbHandler for SMOO XLE operations

#### 3. Local Database Directory (Cache)
```json
{
  "local_db_directory": "/path/to/databases"
}
```
- **Purpose**: Base directory for database cache and temp files
- **Temp XLE Location**: `{local_db_directory}/temp/temp_xle_files/`
- **Used by**: SharedDatabaseXLEManager for temp storage

### Obsolete Settings (No Longer Used)

These settings are no longer used in the new SMOO workflow:

```json
{
  "google_drive_xle_folder_id": "...",  // OBSOLETE - XLE uploads disabled
  // Other Google Drive settings for XLE upload
}
```

## Component Configuration

### SharedDatabaseXLEManager
- **Cache Directory**: Automatically derived from SharedDriveDbHandler
- **Temp Registry**: JSON file tracking temp XLE files
- **Structure**: `cache/temp_xle_files/{PROJECT}/`

### XLEFileOrganizer
- **Detection**: Automatically detects shared database mode using `wlm_` prefix
- **Routing**: Automatically routes to temp or permanent storage
- **Fallback**: Falls back to permanent storage if temp storage unavailable

### SharedDriveDbHandler
- **XLE Integration**: Automatically initialized with SharedDatabaseXLEManager
- **Push Mechanism**: Integrated into `save_database()` method
- **Cleanup**: Integrated into `clear_draft()` method

## Environment Requirements

### Development Environment (Mac)
- **Shared Drive**: Local test directory simulating shared drive
- **Cache Directory**: `databases/temp/` in application directory
- **Testing**: Uses temporary directories for isolation

### Production Environment (Windows)
- **Shared Drive**: Actual network shared drive (S: drive)
- **Cache Directory**: `databases/temp/` in application directory
- **SMOO Structure**: Real SMOO directory structure in shared drive

## Migration Notes

### From Old Google Drive XLE Workflow
1. **Existing Tracking**: Old XLE tracking records remain in database but are ignored
2. **Upload Functionality**: Google Drive XLE upload disabled (returns early)
3. **Import Dialogs**: Updated to use new workflow automatically
4. **No Data Loss**: Existing permanently stored XLE files remain accessible

### Database Mode Detection
- **Local Database**: Database name without `wlm_` prefix → permanent storage
- **Shared Database**: Database name with `wlm_` prefix → temp → SMOO workflow
- **Automatic**: No manual configuration required

## Operational Workflow

### Shared Database Lifecycle
1. **Import**: XLE files stored in temp cache with tracking
2. **Draft Phase**: Files remain in temp storage, visible in registry
3. **Database Push**: Files moved to SMOO structure, temp cleaned up
4. **Draft Discard**: Temp files cleaned up, no SMOO push

### Local Database Lifecycle
1. **Import**: XLE files immediately stored in permanent location
2. **No Draft Phase**: Direct permanent storage
3. **No Push/Cleanup**: Files remain permanently organized

## Troubleshooting

### Common Issues

#### Temp Storage Not Available
- **Symptom**: Shared database files go to permanent storage
- **Cause**: Missing cache_dir or SharedDatabaseXLEManager
- **Resolution**: Verify shared drive handler configuration

#### SMOO Push Failures
- **Symptom**: Database saves but XLE files don't move to SMOO
- **Cause**: Shared drive access issues or path problems
- **Resolution**: Check shared drive connectivity and permissions

#### Missing Cache Directory
- **Symptom**: Temp storage initialization fails
- **Cause**: Cache directory not writable or doesn't exist
- **Resolution**: Verify cache directory permissions and path

### Debug Logging
All components use detailed logging with prefixes:
- `XLE_TRACK`: XLE file tracking operations
- `SMOO_PUSH`: SMOO push operations  
- `TEMP_CLEANUP`: Temp file cleanup operations

## Testing Configuration

The test suite includes comprehensive tests for all configuration scenarios:
- Local database workflows
- Shared database workflows  
- Configuration fallbacks
- Error handling
- Multi-project isolation

Run the complete test suite:
```bash
python3 test_scripts/run_all_smoo_xle_tests.py
```

## Future Enhancements

Potential future configuration additions:
1. **Configurable SMOO Structure**: Allow customization of SMOO directory layout
2. **Retention Policies**: Configure temp file cleanup timing
3. **Backup Integration**: Configure XLE file backup strategies
4. **Performance Tuning**: Configure batch sizes for large file operations

---

*This configuration guide covers the complete SMOO XLE file workflow implementation. For technical details, see the individual component documentation and test files.*