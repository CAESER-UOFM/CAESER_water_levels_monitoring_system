# Installation and Auto-Update System Design

## Overview
This document outlines the installation and auto-update system for the Water Level Monitoring application.

## Current Structure
```
WaterLevelsApp/
├── python/              # Embedded Python installation (Windows only)
├── venv/               # Virtual environment with dependencies
├── water_levels_app.bat/.command    # Main launcher
├── water_levels_app_debug.bat/.command  # Debug launcher
├── water_level_visualizer_app.bat/.command  # Visualizer launcher
└── updater/            # Auto-update system (NEW)
    ├── updater.py
    ├── version_checker.py
    └── backup_manager.py
```

## Installation Process

### 1. Initial Setup
Users download the repository and run the installer:
- **Windows**: `setup.bat`
- **macOS/Linux**: `setup.sh`

The installer:
1. Creates `~/WaterLevelsApp` (macOS/Linux) or `%USERPROFILE%\WaterLevelsApp` (Windows)
2. Downloads and installs Python (Windows only)
3. Creates virtual environment
4. Installs all dependencies
5. Creates launcher scripts
6. Sets up auto-update system

### 2. Directory Structure After Installation
```
~/WaterLevelsApp/           # Installation directory
├── app/                    # Application files (NEW)
│   ├── main.py
│   ├── src/
│   ├── config/
│   ├── tools/
│   └── version.json        # Version tracking
├── backups/               # Backup directory (NEW)
│   ├── v1.0.0/
│   ├── v1.0.1/
│   └── current/
├── updater/               # Update system (NEW)
│   ├── updater.py
│   ├── version_checker.py
│   ├── backup_manager.py
│   └── update_config.json
├── python/                # Python installation (Windows)
├── venv/                  # Virtual environment
└── launchers/             # Launch scripts
    ├── water_levels_app.bat/.command
    ├── water_levels_app_debug.bat/.command
    └── water_level_visualizer_app.bat/.command
```

## Auto-Update System

### 1. Version Management
- Each release has a version number (semantic versioning: MAJOR.MINOR.PATCH)
- Version information stored in `version.json`
- GitHub releases used for distribution

### 2. Update Process
1. **Check for Updates**: On app startup, check GitHub for newer releases
2. **Download Updates**: Download only the `src/` folder and changed files
3. **Backup Current**: Create backup of current version
4. **Apply Update**: Replace files with new versions
5. **Update Dependencies**: Install any new requirements
6. **Cleanup**: Remove old backups (keep last 3 versions)

### 3. Update Components
- **Core Application**: `src/` folder
- **Dependencies**: `Requirements.txt` changes
- **Configuration**: New config files
- **Tools**: Updates to visualization tools

### 4. Rollback System
- Keep backups of last 3 versions
- Ability to rollback if update fails
- Automatic rollback on startup failure

## Implementation Files

### 1. Enhanced Setup Scripts
- Modified `setup.bat` and `setup.sh`
- Copy application files to installation directory
- Set up auto-update system
- Create version tracking

### 2. Auto-Update Components
- `updater/updater.py`: Main update logic
- `updater/version_checker.py`: Check GitHub for updates
- `updater/backup_manager.py`: Handle backups and rollbacks
- `updater/update_config.json`: Update configuration

### 3. Version Tracking
- `version.json`: Current version info
- GitHub releases for version management
- Changelog integration

## Benefits

### For Users
- **Easy Installation**: Single-script setup
- **Automatic Updates**: No manual download/install
- **Safe Updates**: Backup and rollback capability
- **Minimal Disruption**: Only update changed files
- **Clean Environment**: Isolated Python and dependencies

### For Developers
- **Easy Distribution**: Release via GitHub
- **Incremental Updates**: Only changed files
- **Version Control**: Clear version tracking
- **Error Recovery**: Automatic rollback on failure
- **User Feedback**: Update success/failure reporting

## Security Considerations
- Verify update signatures/checksums
- HTTPS-only downloads
- User confirmation for major updates
- Backup before any changes
- Rollback on failure

## Future Enhancements
- Delta updates (only changed files)
- Background updates
- Update scheduling
- Progress indicators
- Update notifications
- Telemetry (optional)