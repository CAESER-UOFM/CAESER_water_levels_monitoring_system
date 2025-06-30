# Dual Database Implementation Plan

## System Overview

### Database Modes
1. **Local Mode**
   - User creates and manages databases locally
   - Auto-save functionality (current behavior)
   - Full control by user

2. **Cloud Mode**
   - Admin-created projects in Google Drive
   - Download to temp folder for editing
   - Manual save with change tracking
   - 2-version backup retention

### Google Drive Structure
```
water_levels_monitoring/
└── Projects/
    ├── Project_Alpha/
    │   ├── databases/
    │   │   ├── project_alpha.db (current)
    │   │   ├── backup/
    │   │   │   ├── project_alpha_2024-01-20_14-30_john.db
    │   │   │   └── project_alpha_2024-01-19_10-15_mary.db
    │   │   └── changes.json
    │   └── runs/
    │       └── [run data files]
    └── Project_Beta/
        ├── databases/
        └── runs/
```

## Implementation Components

### 1. Database Manager Enhancement

```python
class DatabaseManager:
    """Enhanced database manager supporting local and cloud modes"""
    
    def __init__(self):
        self.current_mode = "local"  # "local" or "cloud"
        self.current_db_path = None
        self.cloud_project_name = None
        self.temp_db_path = None
        self.is_cloud_modified = False
        self.available_projects = {}
        
    def list_databases(self):
        """List both local and cloud databases"""
        databases = {
            "local": self._list_local_databases(),
            "cloud": self._list_cloud_databases()
        }
        return databases
    
    def _list_cloud_databases(self):
        """List available cloud projects"""
        # Connect to Google Drive
        # List Projects folder
        # For each project, check databases folder
        # Return project names and their database status
        
    def open_database(self, db_identifier, mode="local"):
        """Open database in specified mode"""
        if mode == "local":
            self._open_local_database(db_identifier)
        else:
            self._open_cloud_database(db_identifier)
            
    def _open_cloud_database(self, project_name):
        """Download and open cloud database"""
        # Download latest database to temp folder
        # Set temp_db_path
        # Track that we're in cloud mode
        # Enable save button in UI
```

### 2. UI Modifications

#### Database Selection Dropdown
```python
class DatabaseDropdown(QComboBox):
    """Enhanced dropdown showing local and cloud databases"""
    
    def populate_databases(self, databases):
        self.clear()
        
        # Add local databases
        self.addItem("-- Local Databases --")
        for db in databases["local"]:
            self.addItem(f"📁 {db.name}", {"mode": "local", "path": db.path})
            
        # Add separator
        self.insertSeparator(self.count())
        
        # Add cloud databases
        self.addItem("-- Cloud Projects --")
        for project in databases["cloud"]:
            self.addItem(f"☁️ {project.name}", {"mode": "cloud", "project": project.name})
```

#### Status Bar Indicator
```python
class StatusBarWidget(QWidget):
    """Shows current database mode and save status"""
    
    def __init__(self):
        self.mode_label = QLabel("Mode: Local")
        self.save_status = QLabel("")
        self.save_button = QPushButton("Save to Cloud")
        self.save_button.setVisible(False)
        
    def set_cloud_mode(self, project_name, modified=False):
        self.mode_label.setText(f"Mode: Cloud - {project_name}")
        self.save_button.setVisible(True)
        if modified:
            self.save_status.setText("⚠️ Unsaved changes")
```

### 3. Save to Cloud Dialog

```python
class SaveToCloudDialog(QDialog):
    """Dialog for saving changes to cloud with tracking"""
    
    def __init__(self, project_name, user_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Save to Cloud - {project_name}")
        
        layout = QVBoxLayout()
        
        # User info (pre-filled from app auth)
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("User:"))
        self.user_label = QLabel(user_name)
        user_layout.addWidget(self.user_label)
        
        # Change description
        layout.addWidget(QLabel("Describe your changes:"))
        self.change_text = QTextEdit()
        self.change_text.setPlaceholderText(
            "e.g., Added water level readings for January\n"
            "Updated site coordinates for Location A"
        )
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        
        layout.addLayout(user_layout)
        layout.addWidget(self.change_text)
        layout.addWidget(buttons)
```

### 4. Cloud Database Handler

```python
class CloudDatabaseHandler:
    """Handles cloud database operations"""
    
    def __init__(self, drive_service):
        self.drive_service = drive_service
        self.projects_folder_id = None  # Set from settings
        
    def list_projects(self):
        """List all available projects"""
        projects = []
        # Query: folders in Projects folder
        # For each project, check if databases folder exists
        return projects
    
    def download_database(self, project_name):
        """Download latest database to temp location"""
        # Create temp file
        temp_path = Path(tempfile.gettempdir()) / f"wlm_{project_name}_{uuid.uuid4()}.db"
        
        # Download current database
        # Return temp path
        return temp_path
    
    def save_database(self, project_name, temp_db_path, user_name, changes_desc):
        """Save database with backup and change tracking"""
        # 1. Download current change log
        changes = self._get_change_log(project_name)
        
        # 2. Create backup of current database
        self._create_backup(project_name, user_name)
        
        # 3. Upload new database
        self._upload_database(project_name, temp_db_path)
        
        # 4. Update change log
        self._update_change_log(project_name, user_name, changes_desc)
        
        # 5. Clean old backups (keep only 2)
        self._cleanup_backups(project_name)
    
    def _create_backup(self, project_name, user_name):
        """Create backup with timestamp and user"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_name = f"{project_name}_{timestamp}_{user_name}.db"
        
        # Copy current to backup folder
        # Return backup file ID
```

### 5. Change Tracking System

```python
class ChangeTracker:
    """Tracks database changes"""
    
    def __init__(self):
        self.changes_file = "changes.json"
        
    def load_changes(self, file_content):
        """Load change history from JSON"""
        return json.loads(file_content)
    
    def add_change(self, user_name, description, db_stats=None):
        """Add new change entry"""
        change = {
            "timestamp": datetime.now().isoformat(),
            "user": user_name,
            "description": description,
            "app_version": self.get_app_version()
        }
        
        if db_stats:
            change["statistics"] = db_stats
            
        return change
    
    def get_db_statistics(self, db_path):
        """Get basic database statistics"""
        # Connect to database
        # Count records in main tables
        # Return summary
        stats = {
            "total_sites": 0,
            "total_readings": 0,
            "last_reading_date": None
        }
        return stats
```

### 6. Conflict Prevention

```python
class CloudLockManager:
    """Simple locking mechanism using Drive metadata"""
    
    def __init__(self, drive_service):
        self.drive_service = drive_service
        self.lock_duration = 300  # 5 minutes
        
    def check_lock(self, project_name):
        """Check if database is locked by another user"""
        # Check custom property on database file
        # Return (is_locked, user_name, lock_time)
        
    def acquire_lock(self, project_name, user_name):
        """Try to acquire lock on database"""
        # Set custom property with user and timestamp
        # Return success/failure
        
    def release_lock(self, project_name):
        """Release lock on database"""
        # Clear custom property
```

## Workflow Implementation

### Opening Cloud Database
```python
def open_cloud_database(self, project_name):
    # 1. Check if locked by another user
    lock_info = self.lock_manager.check_lock(project_name)
    if lock_info.is_locked:
        QMessageBox.warning(
            self, 
            "Database Locked",
            f"Database is being edited by {lock_info.user}\n"
            f"Try again in a few minutes."
        )
        return
    
    # 2. Acquire lock
    if not self.lock_manager.acquire_lock(project_name, self.current_user):
        return
    
    # 3. Download database
    progress = QProgressDialog("Downloading database...", None, 0, 0, self)
    temp_path = self.cloud_handler.download_database(project_name)
    
    # 4. Open in application
    self.database_manager.open_cloud_database(temp_path, project_name)
    
    # 5. Update UI
    self.status_bar.set_cloud_mode(project_name)
    self.enable_cloud_features()
```

### Saving Cloud Database
```python
def save_cloud_database(self):
    # 1. Show save dialog
    dialog = SaveToCloudDialog(
        self.database_manager.cloud_project_name,
        self.current_user
    )
    
    if dialog.exec_() != QDialog.Accepted:
        return
        
    # 2. Get change description
    changes_desc = dialog.change_text.toPlainText()
    
    # 3. Save with progress
    progress = QProgressDialog("Saving to cloud...", None, 0, 3, self)
    
    progress.setValue(1)
    progress.setLabelText("Creating backup...")
    
    self.cloud_handler.save_database(
        self.database_manager.cloud_project_name,
        self.database_manager.temp_db_path,
        self.current_user,
        changes_desc
    )
    
    progress.setValue(2)
    progress.setLabelText("Uploading database...")
    
    progress.setValue(3)
    progress.setLabelText("Updating change log...")
    
    # 4. Release lock
    self.lock_manager.release_lock(self.database_manager.cloud_project_name)
    
    # 5. Update UI
    self.status_bar.set_cloud_mode(
        self.database_manager.cloud_project_name, 
        modified=False
    )
    
    QMessageBox.information(self, "Success", "Database saved to cloud!")
```

### Application Cleanup
```python
def closeEvent(self, event):
    """Handle application closing"""
    if self.database_manager.current_mode == "cloud":
        if self.database_manager.is_cloud_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes in the cloud database.\n"
                "Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_cloud_database()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        
        # Clean up temp file
        if self.database_manager.temp_db_path:
            Path(self.database_manager.temp_db_path).unlink(missing_ok=True)
            
        # Release lock if held
        if self.database_manager.cloud_project_name:
            self.lock_manager.release_lock(
                self.database_manager.cloud_project_name
            )
```

## Change Log Format

```json
{
  "project": "Project_Alpha",
  "changes": [
    {
      "timestamp": "2024-01-20T14:30:00Z",
      "user": "John Doe",
      "description": "Added January water level readings for sites A, B, C",
      "app_version": "2.1.0",
      "statistics": {
        "total_sites": 45,
        "total_readings": 12350,
        "last_reading_date": "2024-01-20"
      }
    },
    {
      "timestamp": "2024-01-19T10:15:00Z",
      "user": "Mary Smith",
      "description": "Updated site coordinates and added new monitoring location",
      "app_version": "2.1.0"
    }
  ]
}
```

## Key Features

1. **Seamless Mode Switching**: Users can switch between local and cloud databases without restarting
2. **Visual Indicators**: Clear UI showing current mode and save status
3. **Simple Conflict Prevention**: 5-minute lock system prevents concurrent edits
4. **Automatic Cleanup**: Temp files removed on close, old backups auto-deleted
5. **Change Tracking**: User and description tracked for each save
6. **Backup Management**: Automatic 2-version retention

## Next Steps

1. Implement CloudDatabaseHandler
2. Modify UI to add cloud indicators
3. Add save dialog and workflow
4. Test with sample cloud projects
5. Add error handling and retry logic