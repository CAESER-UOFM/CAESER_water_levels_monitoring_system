# Cloud Database Caching System

## Overview
The Water Level Monitoring system implements intelligent caching for cloud databases to improve performance and reduce bandwidth usage.

## How Version Tracking Works

### 1. Cache Storage
- **Location**: `~/tmp/wlm_cloud_cache/`
- **Database Files**: `{project_name}.db`
- **Metadata Files**: `{project_name}_metadata.json`

### 2. Version Detection
When a user selects a cloud database:

1. **Check Cloud Version**: The system queries Google Drive for the database's `modifiedTime`
2. **Compare with Cache**: Checks if a cached version exists and compares timestamps
3. **Decision Logic**:
   - If cached version matches cloud version → Use cache (instant load)
   - If cloud version is newer → Download and update cache
   - If no cache exists → Download and create cache

### 3. Metadata Structure
Each cached database has an associated metadata file:
```json
{
  "project_name": "CAESER_GENERAL",
  "database_name": "CAESER_GENERAL.db",
  "modifiedTime": "2024-06-21T10:30:45.123Z",
  "cached_at": "2024-06-21T13:10:58.456Z",
  "database_id": "1NeIpAkHeCyJo0skPlW5RvDgMIQkiWtD0"
}
```

### 4. Cache Workflow

```
User selects cloud database
    ↓
Check if cache exists
    ↓
  YES → Compare modifiedTime
    ↓         ↓
  MATCH    DIFFERENT
    ↓         ↓
Use cache  Download new
    ↓         ↓
    └─────────┘
         ↓
   Load database
```

## Benefits

1. **Performance**: Cached databases load in seconds vs minutes for downloads
2. **Bandwidth**: Only downloads when database actually changes
3. **Offline Access**: Recently used databases available even without internet
4. **Automatic Updates**: Always gets latest version when cloud database is modified

## Progress Tracking

The progress dialog shows different stages:
- **0-10%**: Initialization and cache checking
- **10-80%**: Download progress (only if downloading)
- **80-85%**: Database opening
- **85-100%**: Tab loading

For cached databases, the download phase is skipped, providing instant access.

## Cache Management

- Cache files persist across sessions
- Old cache files are automatically cleaned up when newer versions are downloaded
- Temporary working copies are created to prevent cache corruption
- Each download updates both the cached database and its metadata

## Technical Implementation

See `CloudDatabaseHandler` class in `src/gui/handlers/cloud_database_handler.py` for implementation details.