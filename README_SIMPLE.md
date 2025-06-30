# CAESER Water Levels Monitoring System

Desktop application for processing water level data from Solinst data loggers. Handles barometric compensation, calculates recharge estimates, and manages well data.

## Quick Start

1. **Download** the latest release
2. **Run** `setup.bat` (Windows) or `setup.sh` (Mac/Linux)  
3. **Launch** using the created shortcut

No admin rights needed. Installs to your user folder only.

## What It Does

- **Import XLE files** from Solinst leveloggers and barologgers
- **Apply barometric correction** automatically 
- **Calculate recharge rates** using standard methods (RISE, MRC)
- **Visualize data** with interactive plots and maps
- **Export results** to CSV or other formats
- **Sync with Google Drive** for team collaboration (optional)

## Main Features

### Data Processing
- Handles Solinst XLE and LEV file formats
- Automatic quality control and data validation
- Manual reading integration
- Batch processing for multiple files

### Analysis Tools
- Multiple recharge calculation methods
- Statistical analysis and trend detection
- Interactive plotting and visualization
- Well location mapping

### Collaboration
- Google Drive database synchronization
- Multi-user access with conflict resolution
- Web-based visualizer for field access
- Data sharing and export tools

## System Requirements

- Windows 10+, macOS 10.14+, or Linux Ubuntu 18.04+
- 4GB RAM (8GB recommended for large datasets)
- 2GB free disk space
- Internet connection for updates and cloud features (optional)

## For CAESER Team Members

Contact the maintainer for Google Drive access credentials to enable full cloud synchronization features.

## Support

- Use the Help button in the application for guidance
- Report issues on GitHub
- Check the docs folder for detailed documentation

## Installation Notes

The installer:
- Downloads Python if needed (Windows only)
- Creates an isolated environment 
- Installs all dependencies automatically
- Creates desktop/start menu shortcuts
- Doesn't require administrator privileges
- Can be uninstalled by deleting the installation folder

Built for groundwater monitoring professionals who need reliable data processing and analysis tools.