# Google Drive Integration Analysis - Water Levels Monitoring

## Overview
This document provides a comprehensive analysis of all Google Drive connections and operations in the Water Levels Monitoring application. This analysis will serve as a reference for redesigning the Google Drive integration.

## Authentication & Connection Setup

### Authentication Service
- **Main Service**: `GoogleDriveService` (src/gui/handlers/google_drive_service.py)
- **Pattern**: Singleton pattern for centralized authentication
- **OAuth2 Flow**: Uses installed application flow with local server
- **Scopes**: `https://www.googleapis.com/auth/drive` (full Drive access)
- **Token Storage**: `~/.water_levels/token.json`
- **Client Secret**: Stored in `config/client_secret_*.json`
- **Auto-auth Control**: Can be disabled via `GOOGLE_DRIVE_NO_AUTO_AUTH=1` environment variable

### Authentication Process
1. Check for existing token at `~/.water_levels/token.json`
2. Validate token and refresh if expired
3. If no valid token, initiate OAuth2 flow with browser
4. Save new token for future use
5. Build Drive service using authenticated credentials

## Google Drive Handlers

### 1. GoogleDriveDataHandler
**Purpose**: Manages data folder operations (upload/download of experiment data)

**Key Operations**:
- **Download data folders**: Downloads entire folder structures recursively
- **Upload data folders**: Creates zip files and uploads
- **Create data folders**: Creates new folder structures
- **Upload run folders**: Handles specific run data with JSON files

**Folder Structure**:
```
Main Folder (1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK)
└── data/
    └── runs/ (1u1Ea9aRu3B405BmpaDJgads1BrLrCp4P)
        └── [run_id]/
            ├── *.json (experiment data)
            └── README.txt
```

### 2. GoogleDriveMonitor
**Purpose**: Monitors for XLE files, processes metadata, and organizes files

**Key Operations**:
- **Monitor XLE files**: Watches for new .xle files
- **Process metadata**: Extracts serial numbers, locations, dates
- **Rename files**: Based on metadata (format: SN_Location_StartDate_EndDate.xle)
- **Organize files**: Moves to appropriate folders

**Folder Structure**:
```
XLE Folder (monitored folder ID)
├── all/ (processed files archive)
│   └── [renamed XLE files]
└── runs/ (organized by month)
    └── YYYY_MM/
        └── [XLE files for that month]
```

### 3. GoogleDriveDatabaseHandler
**Purpose**: Manages SQLite database synchronization

**Key Operations**:
- **Download database**: Downloads with "(drive)" suffix
- **Upload database**: Updates or creates database file
- **Create database**: Creates empty database and uploads

**Files Managed**:
- `CAESER_GENERAL.db` - Main application database
- Downloads as `CAESER_GENERAL (drive).db` locally

### 4. UserAuthService
**Purpose**: Manages user authentication and roles

**Key Operations**:
- **Download users file**: With automatic backup
- **Upload users file**: Updates user credentials
- **Manage users**: Add/remove users with roles (admin/tech)

**Files Managed**:
- `water_levels_users.json` - User credentials and roles
- Local backup at `~/.water_levels/water_levels_users.json.backup`

## Google Drive API Methods Used

### Core API Methods
1. **files().list()** - Search and list files/folders
2. **files().get_media()** - Download file content
3. **files().create()** - Create new files/folders
4. **files().update()** - Update file content or metadata
5. **files().copy()** - Copy files to new locations

### Helper Classes
- **MediaIoBaseDownload** - Chunked file downloads with progress
- **MediaFileUpload** - Resumable file uploads

## File Operations Summary

### Read Operations
- Download files with progress tracking
- Recursive folder downloads
- Metadata extraction from XLE files
- User credentials retrieval

### Write Operations
- Upload files with resumable support
- Update existing files
- Rename files based on metadata
- Create zip archives for folder uploads

### File Modifications
- XLE files: Renamed based on metadata
- Database files: "(drive)" suffix added on download
- Folders: Files moved between folders using parent updates
- Temporary files: Zip files created for folder uploads

## Folder IDs and Locations

### Primary Folders
- **Main Data Folder**: `1vGoxkS-HQ0n0u0ToNcYL_wJGZ02RDhAK`
  - Contains: Database, user files, data folders
- **Runs Folder**: `1u1Ea9aRu3B405BmpaDJgads1BrLrCp4P`
  - Contains: Individual run data with JSON files
- **XLE Monitor Folder**: Configurable via settings
  - Contains: Raw XLE files for processing

### File Naming Conventions
- XLE files: `SerialNumber_Location_StartDate_EndDate.xle`
- Run folders: `YYYY_MM` format
- Database downloads: Original name + " (drive)" suffix

## Security & Permissions

### Authentication Security
- OAuth2 with user consent
- Token stored locally with user permissions
- Refresh tokens for long-term access
- Client secret required for authentication

### Error Handling
- Graceful authentication failure handling
- Automatic token refresh
- Backup creation before file modifications
- Extensive logging for debugging

## Configuration

### Settings Storage
- Client secret path
- Folder IDs (main folder, XLE folder)
- Auto-sync preferences
- Stored via SettingsHandler

### Environment Variables
- `GOOGLE_DRIVE_NO_AUTO_AUTH`: Disable automatic authentication

## Dependencies
- `google-api-python-client==2.161.0`
- `google-auth-oauthlib==1.2.1`
- PyQt5 for UI integration

## Key Design Patterns

1. **Singleton Service**: Centralized authentication prevents multiple auth flows
2. **Progress Tracking**: All long operations show progress dialogs
3. **Error Recovery**: Automatic retries and graceful degradation
4. **Offline Support**: Local caching and backup strategies
5. **Batch Operations**: Efficient API usage with batched requests

## Recommendations for Redesign

### Current Limitations
1. Full Drive scope might be excessive
2. Hardcoded folder IDs reduce flexibility
3. No selective sync options
4. Limited conflict resolution

### Suggested Improvements
1. Use more restrictive OAuth scopes
2. Dynamic folder discovery
3. Selective file synchronization
4. Better conflict resolution strategies
5. Offline-first design with sync queue
6. Modular handler architecture
7. Event-driven sync system
8. Better separation of concerns

## Usage Patterns

### Typical Workflow
1. User authenticates on first run
2. Database syncs on startup
3. XLE monitor runs in background
4. Data folders sync on demand
5. User management through admin interface

### File Lifecycle
1. **XLE Files**: Upload → Process → Rename → Organize
2. **Database**: Download → Modify → Upload
3. **Data Folders**: Create → Add files → Upload as archive
4. **User File**: Download → Modify → Upload with backup