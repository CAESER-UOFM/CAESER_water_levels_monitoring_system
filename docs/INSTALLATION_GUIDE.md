# Water Level Monitoring System - Installation & Update Guide

## Overview

This guide explains how to install the Water Level Monitoring System with the new enhanced installation and auto-update system.

## System Requirements

### Windows
- Windows 10 or later
- 4GB+ RAM recommended
- 2GB free disk space
- Internet connection for downloads and updates

### macOS
- macOS 10.14 or later
- 4GB+ RAM recommended
- 2GB free disk space
- Python 3.8+ (can be installed via Homebrew)

### Linux
- Ubuntu 18.04+ / CentOS 7+ / Similar distributions
- 4GB+ RAM recommended
- 2GB free disk space
- Python 3.8+ and development packages

## Installation

### Option 1: Enhanced Installation (Recommended)

#### Windows
1. Download or clone the repository
2. Navigate to the project root folder
3. Run `setup.bat` as Administrator
4. The installer will:
   - Create `%USERPROFILE%\WaterLevelsApp` directory
   - Download and install Python 3.11.6 (if needed)
   - Create isolated virtual environment
   - Install all dependencies
   - Copy application files
   - Create desktop launchers
   - Set up auto-update system

#### macOS/Linux
1. Download or clone the repository
2. Navigate to the project root folder
3. Make the script executable: `chmod +x setup.sh`
4. Run: `./setup.sh`
5. The installer will:
   - Create `~/WaterLevelsApp` directory
   - Use system Python 3 (install if needed)
   - Create isolated virtual environment
   - Install all dependencies
   - Copy application files
   - Create launchers
   - Set up auto-update system

### Option 2: Legacy Installation

If you need the older installation method, it has been deprecated in favor of the enhanced setup scripts above.

## Directory Structure After Installation

```
~/WaterLevelsApp/               # Installation directory
├── app/                        # Application files
│   ├── src/                   # Source code
│   ├── main.py               # Main application
│   ├── config/               # Configuration files
│   ├── tools/                # Additional tools
│   └── version.json          # Version information
├── backups/                   # Automatic backups
│   ├── v1.0.0/              # Previous versions
│   └── v1.0.1/
├── python/                    # Python installation (Windows only)
├── venv/                      # Virtual environment
└── Launchers:
    ├── water_levels_app.bat/.command         # Main launcher
    ├── water_levels_app_debug.bat/.command   # Debug launcher
    ├── water_level_visualizer_app.bat/.command # Visualizer
    └── uninstall.bat/.command               # Uninstaller
```

## Running the Application

### Main Application
- **Windows**: Double-click `water_levels_app.bat`
- **macOS/Linux**: Double-click `water_levels_app.command`

### Debug Mode (for troubleshooting)
- **Windows**: Double-click `water_levels_app_debug.bat`
- **macOS/Linux**: Double-click `water_levels_app_debug.command`

### Visualizer Tool
- **Windows**: Double-click `water_level_visualizer_app.bat`
- **macOS/Linux**: Double-click `water_level_visualizer_app.command`

## Auto-Update System

### How It Works
- Checks GitHub for new releases on startup
- Downloads only changed files (typically just the `src/` folder)
- Creates automatic backups before updating
- Can rollback if update fails
- Updates dependencies as needed

### Update Process
1. **Automatic Check**: App checks for updates on startup (if enabled)
2. **User Notification**: Shows update dialog if new version available
3. **Backup**: Creates backup of current version
4. **Download**: Downloads update files from GitHub
5. **Apply**: Replaces old files with new ones
6. **Verify**: Ensures update completed successfully
7. **Cleanup**: Removes old backups (keeps last 3)

### Manual Update Check
- Open the application
- Go to **Update** menu → **Check for Updates**
- Follow prompts if update is available

### Version Information
- Go to **Update** menu → **About Version**
- Shows current version, installation path, and update status

### Rollback (if needed)
If an update fails, the system automatically attempts to rollback to the previous version using the backup.

## Configuration

### Auto-Update Settings
Edit `version.json` in the app directory:

```json
{
  "auto_update": {
    "enabled": true,           // Enable/disable auto-update
    "check_on_startup": true,  // Check for updates on startup
    "backup_count": 3          // Number of backups to keep
  }
}
```

### GitHub Repository
The default repository is set to `bmac2558/water_levels_monitoring`. Update this in:
- `version.json` → `github_repo`
- Application source code if needed

## Troubleshooting

### Installation Issues

#### Python Not Found (macOS/Linux)
```bash
# Install Python 3 via package manager
# macOS (Homebrew):
brew install python@3.11

# Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL:
sudo yum install python3 python3-pip
```

#### Permission Errors
- **Windows**: Run installer as Administrator
- **macOS/Linux**: Ensure user has write permissions to home directory

#### Missing Dependencies
- Run the debug launcher to see detailed error messages
- Dependencies are automatically installed on first run

### Update Issues

#### Update Download Fails
- Check internet connection
- Verify GitHub repository exists and is accessible
- Check firewall/antivirus settings

#### Update Application Fails
- Automatic rollback should restore previous version
- Check logs in debug mode
- Manually restore from backup if needed

#### Cannot Find Updates
- Verify `github_repo` setting in `version.json`
- Check if repository has releases/tags
- Ensure version numbering follows semantic versioning

### Debug Mode
Always run in debug mode to see detailed error messages:
- Shows Python version and dependency status
- Displays detailed error messages
- Keeps console open after application exits

## Uninstallation

### Automatic Uninstaller
- **Windows**: Run `uninstall.bat` in the installation directory
- **macOS/Linux**: Run `uninstall.command` in the installation directory

### Manual Uninstallation
Simply delete the installation directory:
- **Windows**: `%USERPROFILE%\WaterLevelsApp`
- **macOS/Linux**: `~/WaterLevelsApp`

## Advanced Usage

### Development Mode
If running from source (not installed), the system automatically:
- Detects development environment
- Disables automatic updates
- Uses version "1.0.0-dev"

### Custom Installation Location
Modify the setup scripts to change the installation directory by editing the `INSTALL_DIR` variable.

### Multiple Versions
You can install multiple versions by:
1. Changing the installation directory in setup scripts
2. Installing to different locations
3. Each installation is completely isolated

## Support

### Getting Help
- Use the debug launcher to get detailed error information
- Check the logs for specific error messages
- Consult the GitHub repository for issues and documentation

### Reporting Issues
When reporting issues, include:
- Operating system and version
- Python version (from debug mode)
- Complete error message
- Steps to reproduce the issue

### Updates and Releases
- Check the GitHub repository for latest releases
- Release notes describe changes and fixes
- Subscribe to repository notifications for update alerts