# Dual Database System Design

## Current Understanding

### Database Modes
1. **Local Mode** (current system)
   - Database created/copied locally by user
   - Changes saved automatically
   - No cloud synchronization

2. **Cloud Mode** (new)
   - Database stored in Google Drive
   - Download latest version on open
   - Manual save with change tracking
   - Backup retention (1-2 versions)

### New Google Drive Structure
```
water_levels_monitoring/
└── Projects/
    ├── Project_A/
    │   ├── databases/
    │   │   ├── current_db.db
    │   │   ├── backup/
    │   │   │   ├── db_backup_2024-01-20_user1.db
    │   │   │   └── db_backup_2024-01-19_user2.db
    │   │   └── changes_log.json
    │   └── runs/
    │       └── [existing run structure]
    ├── Project_B/
    │   ├── databases/
    │   └── runs/
    └── Project_C/
        ├── databases/
        └── runs/
```

### Cloud Mode Workflow
1. User selects project from cloud
2. System downloads latest database
3. User makes changes (not auto-saved)
4. User clicks "Save to Cloud"
5. System prompts for:
   - User name
   - Change description
6. System creates backup of current cloud version
7. Uploads modified database
8. Updates change log

## Clarifying Questions

### 1. Project Management
- **How are projects created?** 
  - Can users create new projects from the app?
  - Or are projects pre-created in Google Drive?
- **Project selection UI:**
  - Dropdown list of available projects?
  - Separate dialog for project selection?
- **Can users switch between projects without restarting?**

### 2. Database Synchronization
- **Conflict resolution:**
  - What happens if two users edit the same cloud database?
  - Should we implement file locking?
  - Or merge conflicts manually?
- **Offline mode:**
  - Can users work offline in cloud mode?
  - How to handle sync when coming back online?
- **Database versioning:**
  - How many backups to keep? (suggested 1-2)
  - Naming convention for backups?
  - Auto-cleanup of old backups?

### 3. Change Tracking
- **What to track:**
  - Just user and comment?
  - Or detailed database changes (added/modified/deleted records)?
  - Timestamp of changes?
- **Change log format:**
  - JSON file with array of changes?
  - CSV for easier viewing?
  - SQLite table within the database?
- **Change comparison:**
  - Compare table row counts?
  - Track specific field modifications?
  - Generate diff report?

### 4. User Interface Changes
- **Mode selection:**
  - Toggle between Local/Cloud mode?
  - Selected at startup?
  - Can user switch modes for same database?
- **Save button placement:**
  - Main toolbar?
  - File menu?
  - Auto-save timer with manual save option?
- **Status indicators:**
  - Show "unsaved changes" indicator?
  - Last sync time?
  - Current user?

### 5. Authentication & Permissions
- **User identification:**
  - Use Google account name?
  - Manual user name entry?
  - Predefined user list?
- **Access control:**
  - All users can edit all projects?
  - Project-specific permissions?
  - Read-only mode for some users?

### 6. Technical Considerations
- **Database locking:**
  - Prevent concurrent edits?
  - Show "database in use by X" message?
- **Download optimization:**
  - Cache databases locally?
  - Check if database changed before downloading?
  - Use checksums/timestamps?
- **Upload handling:**
  - Progress indication for large databases?
  - Retry on failure?
  - Bandwidth optimization?

### 7. Run Data Integration
- **How do runs relate to projects?**
  - Automatic organization by project?
  - Can runs be shared between projects?
- **XLE file handling:**
  - Still use current XLE monitoring?
  - Project-specific XLE folders?

### 8. Migration Path
- **Existing databases:**
  - How to migrate current local databases to cloud?
  - Maintain backward compatibility?
- **Existing folder structure:**
  - How to handle current Google Drive structure?
  - Migration tool needed?

## Proposed Change Tracking System

### Option 1: JSON Change Log
```json
{
  "changes": [
    {
      "timestamp": "2024-01-20T10:30:00Z",
      "user": "John Doe",
      "comment": "Added new water level readings for Site A",
      "database_version": "v1.2.3",
      "changes_summary": {
        "tables_modified": ["water_levels", "sites"],
        "records_added": 15,
        "records_modified": 3,
        "records_deleted": 0
      }
    }
  ]
}
```

### Option 2: SQLite Change Tracking Table
```sql
CREATE TABLE change_log (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_name TEXT NOT NULL,
    comment TEXT,
    changes_summary TEXT,
    database_checksum TEXT
);
```

### Option 3: Detailed Change Tracking
- Use SQLite triggers to track all changes
- Store before/after values
- Generate detailed diff reports

## Additional Considerations

1. **Performance:**
   - Database size limits?
   - Compression for uploads/downloads?
   - Incremental updates instead of full uploads?

2. **Error Handling:**
   - Network failures during sync
   - Corrupted database handling
   - Rollback capabilities

3. **User Experience:**
   - Minimize workflow disruption
   - Clear indicators of mode/status
   - Intuitive save/sync process

4. **Security:**
   - Encrypt databases in transit?
   - Access audit trail?
   - Sensitive data handling?

Please provide answers to these questions so I can create a comprehensive implementation plan that meets all your requirements.