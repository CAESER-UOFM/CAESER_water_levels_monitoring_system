# Backup Folder Structure Fix

## Problem Fixed
Previously, SharedDriveDbHandler created backup files directly in the DATABASES folder, creating a messy structure that was inconsistent with Google Drive's organized approach.

## Before (Messy):
```
S:/Projects/MEGASITE/DATABASES/
├── MEGASITE.db                           ← Main database
├── MEGASITE_backup_1641234567.db         ← Backup mixed with main
├── MEGASITE_backup_1641234890.db         ← More backups cluttering folder
├── MEGASITE_backup_1641235123.db
├── drafts/
│   └── draft_20240115_143022.db
└── changes/
    └── changes_20240115_143022.json
```

## After (Organized):
```
S:/Projects/MEGASITE/DATABASES/
├── MEGASITE.db                           ← Main database
├── backup/                               ← Dedicated backup folder
│   ├── MEGASITE_backup_2024-01-15_14-30.db
│   ├── MEGASITE_backup_2024-01-14_10-15.db
│   ├── MEGASITE_backup_2024-01-13_16-45.db
│   ├── MEGASITE_backup_2024-01-12_09-20.db
│   └── MEGASITE_backup_2024-01-11_13-10.db  ← Only keeps 5 most recent
├── drafts/
│   └── draft_20240115_143022.db
└── changes/
    └── changes_20240115_143022.json
```

## Changes Made

### 1. **Organized Backup Structure**
- **Before**: Backups created directly in `DATABASES/` folder
- **After**: Backups created in `DATABASES/backup/` subfolder

### 2. **Better Filename Format**
- **Before**: `PROJECT_backup_1641234567.db` (Unix timestamp)
- **After**: `PROJECT_backup_2024-01-15_14-30.db` (Human-readable)

### 3. **Automatic Cleanup**
- **Before**: No cleanup - backups accumulated indefinitely
- **After**: Keeps only 5 most recent backups per project

### 4. **Consistent with Google Drive**
- **Before**: Different structure than Google Drive handler
- **After**: Same organized structure as Google Drive handler

## Code Changes

### SharedDriveDbHandler Updates:

1. **New Helper Method**:
   ```python
   def _get_shared_drive_backup_folder_path(self, project_name: str) -> str:
       """Get the shared drive backup folder path for a project"""
       db_folder_path = self._get_shared_drive_db_folder_path(project_name)
       return os.path.join(db_folder_path, "backup")
   ```

2. **Updated Backup Creation**:
   ```python
   # Create backup folder (matching Google Drive structure)
   backup_folder_path = self._get_shared_drive_backup_folder_path(project_name)
   os.makedirs(backup_folder_path, exist_ok=True)
   
   # Generate backup filename with timestamp and better format
   timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
   backup_name = f"{project_name}_backup_{timestamp}.db"
   backup_path = os.path.join(backup_folder_path, backup_name)
   ```

3. **New Cleanup Method**:
   ```python
   def _cleanup_old_backups(self, backup_folder_path: str, project_name: str, keep_count: int = 5):
       """Clean up old backup files, keeping only the most recent ones"""
   ```

## Benefits

1. **🗂️ Organization**: Clean separation of backups from main database
2. **👀 Readability**: Human-readable timestamps in filenames
3. **💾 Space Management**: Automatic cleanup prevents disk space bloat
4. **🔄 Consistency**: Same structure as Google Drive handler
5. **🔍 Maintainability**: Easier to find and manage backup files

## Migration Notes

- **Existing backups**: Old backup files in DATABASES/ folder will remain until manually cleaned up
- **New backups**: All new backups will be created in the organized structure
- **No breaking changes**: Existing functionality preserved
- **Backward compatible**: No changes to database loading or main operations

## Example Log Output

```
INFO - Backup created in backup/ folder: MEGASITE_backup_2024-01-15_14-30.db
INFO - Cleaned up 3 old backup files, keeping 5 most recent
INFO - Uploading database for MEGASITE to shared drive
```

This fix ensures that SharedDriveDbHandler follows the same professional backup management practices as the Google Drive handler.