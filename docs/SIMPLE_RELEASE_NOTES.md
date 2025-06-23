# Water Level Monitoring System v1.0.0

A PyQt5 application for managing water level data from transducers and barologgers.

## What it does:
- Import and visualize Solinst XLE files
- Barometric pressure compensation using barologger data
- Manual readings and CSV import  
- SQLite database with Google Drive sync
- Interactive plots with matplotlib
- Export data in various formats
- Auto-update system checks GitHub for new versions

## Installation:
1. Download source code from GitHub releases
2. Run setup.bat (Windows) or setup.sh (macOS/Linux) 
3. Launch from created shortcuts in ~/WaterLevelsApp/

## Google Drive Features:
For cloud sync capabilities, download credentials from: 
https://drive.google.com/file/d/1Qn4jAPXTrT7GBzU6JdG6W-KogT4yZBlR/view

Then use Update → Setup Google Credentials in the app.

## Requirements:
- Windows 10+ / macOS 10.14+ / Linux Ubuntu 18.04+
- Python 3.8+ (installer handles this)
- 4GB RAM recommended
- Internet for updates and cloud features

## Tools included:
- Data Visualizer
- LEV to XLE converter
- CSV to XLE converter  
- XLE metadata editor
- Unit converter