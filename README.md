# Water Level Monitoring System

A comprehensive application for managing and analyzing water level data from transducers and barologgers.

## 🚀 Quick Start

### Download & Install

#### Option 1: Easy Installation (Recommended)
1. **Download** the latest release:
   - Go to [Releases](https://github.com/benjaled/water_levels_monitoring/releases)
   - Download `water_levels_monitoring_v1.0.0.zip` (or latest version)
   - Extract the ZIP file to a folder on your computer

2. **Run the installer**:
   - **Windows**: Double-click `docs/setup_enhanced.bat`
   - **macOS/Linux**: Open terminal, navigate to the folder, run `chmod +x docs/setup_enhanced.sh && ./docs/setup_enhanced.sh`

3. **Launch the application**:
   - **Windows**: `%USERPROFILE%\WaterLevelsApp\water_levels_app.bat`
   - **macOS/Linux**: `~/WaterLevelsApp/water_levels_app.command`

#### Option 2: Clone Repository (For Developers)
```bash
git clone https://github.com/benjaled/water_levels_monitoring.git
cd water_levels_monitoring
# Windows: run setup.bat
# macOS/Linux: run ./setup.sh
```

## ✨ Features

### Core Functionality
- **Water Level Data Management**: Import, visualize, and analyze transducer data
- **Barometric Pressure Compensation**: Automatic compensation using barologger data
- **Database Management**: SQLite-based data storage with cloud sync capabilities
- **Data Visualization**: Interactive plots with matplotlib integration
- **Export Capabilities**: Export data in various formats

### Data Sources
- **Solinst XLE Files**: Native support for Solinst transducer files
- **Manual Readings**: Manual data entry and CSV import
- **MONET Integration**: Connect to MONET API for additional data
- **Google Drive Sync**: Cloud storage and synchronization

### Advanced Tools
- **Auto-Update System**: Automatic application updates from GitHub
- **Data Visualizer**: Standalone visualization tool
- **File Converters**: LEV to XLE, CSV to XLE conversion tools
- **Metadata Editor**: Edit XLE file metadata
- **Unit Converter**: Convert between measurement units

## 📋 System Requirements

- **Windows**: Windows 10 or later
- **macOS**: macOS 10.14 or later  
- **Linux**: Ubuntu 18.04+ / CentOS 7+ or similar
- **RAM**: 4GB+ recommended
- **Storage**: 2GB+ free space
- **Internet**: Required for cloud features and updates

## 🔧 Installation Details

The installer automatically:
- Downloads and installs Python 3.11 (Windows) or uses system Python (macOS/Linux)
- Creates an isolated virtual environment
- Installs all required dependencies
- Sets up the application in `~/WaterLevelsApp` directory
- Creates desktop launchers
- Configures auto-update system

## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION_GUIDE.md)**: Detailed installation instructions
- **[User Manual](docs/)**: Complete user documentation
- **[Developer Guide](docs/)**: For developers and contributors

## ☁️ Google Drive Features

For full Google Drive functionality (cloud sync, shared databases), you'll need Google API credentials:

### For Authorized Users
- **📥 Download credentials**: [Google Drive Credentials Folder](https://drive.google.com/file/d/1Qn4jAPXTrT7GBzU6JdG6W-KogT4yZBlR/view?usp=drive_link)
- **⚙️ Setup**: Use **Update** → **Setup Google Credentials** in the app
- **✅ Easy process**: Download files, select in dialog, done!

*Note: If you can't access the credentials link, contact the repository owner for access.*

### For Independent Users
- Create your own Google Cloud project and API credentials
- Use the setup dialog to configure your own credentials
- See [documentation](docs/INSTALLATION_GUIDE.md) for detailed instructions

## 🔄 Updates

The application includes an automatic update system:
- Checks for updates on startup
- Manual check via **Update** → **Check for Updates** menu
- Safe updates with automatic backup and rollback
- Only downloads changed files for faster updates

## 🐛 Troubleshooting

### Common Issues

#### Installation Problems
- **Permission errors**: Run installer as Administrator (Windows) or with sudo (Linux)
- **Python not found**: Install Python 3.8+ from python.org or your package manager
- **Dependencies fail**: Use the debug launcher to see detailed error messages

#### Runtime Issues
- **Application won't start**: Use debug launcher (`water_levels_app_debug.bat/.command`)
- **Database errors**: Check file permissions and disk space
- **Cloud sync issues**: Verify internet connection and credentials

### Debug Mode
Always use debug mode for troubleshooting:
- **Windows**: `water_levels_app_debug.bat`
- **macOS/Linux**: `water_levels_app_debug.command`

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/benjaled/water_levels_monitoring/issues)
- **Discussions**: [GitHub Discussions](https://github.com/benjaled/water_levels_monitoring/discussions)
- **Documentation**: See `docs/` folder for detailed guides

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

## 🏷️ Latest Release

**Version 1.0.0** - Initial Release
- Full water level monitoring functionality
- Auto-update system
- Cloud synchronization
- Comprehensive tool suite

[**Download Latest Release**](https://github.com/benjaled/water_levels_monitoring/releases/latest)

---

## Quick Links
- [📥 Download Latest Release](https://github.com/benjaled/water_levels_monitoring/releases/latest)
- [📖 Installation Guide](docs/INSTALLATION_GUIDE.md)
- [🐛 Report Issues](https://github.com/benjaled/water_levels_monitoring/issues)
- [💬 Discussions](https://github.com/benjaled/water_levels_monitoring/discussions)