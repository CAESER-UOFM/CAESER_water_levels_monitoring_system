# Installation Guide for Authorized Users

This guide is for users who have been granted access to the Google Drive credentials for the Water Level Monitoring System.

## 🎯 Quick Overview

The application is split into two parts for security:
1. **Public Repository**: Main application code (this repository)
2. **Private Credentials**: Google API credentials (separate private repository)

## 📥 Installation Steps

### Step 1: Download Main Application
1. Go to [Releases](https://github.com/benjaled/water_levels_monitoring_-for_external_edits-/releases/latest)
2. Download `Source code (zip)` from the latest release
3. Extract to a folder on your computer

### Step 2: Get Credentials Access
**Contact the repository owner** for access to the private credentials repository:
- You'll be added as a collaborator to the private repository
- You'll receive a link to download the credential files

### Step 3: Install Application

#### Windows:
1. Double-click `setup.bat` in the main application folder
2. Wait for installation to complete
3. When prompted for credentials during first run, use the setup dialog

#### macOS/Linux:
1. Open terminal and navigate to the application folder
2. Run: `chmod +x setup.sh && ./setup.sh`
3. Wait for installation to complete
4. When prompted for credentials during first run, use the setup dialog

### Step 4: Set Up Credentials

When you first run the application, you'll see a credentials setup dialog with three options:

#### Option A: From Private Repository (Recommended)
1. Download the credentials folder from the private repository
2. In the setup dialog, go to "📂 From Private Repository" tab
3. Click "Select Folder" and choose the downloaded credentials folder
4. The app will automatically copy the files to the correct location

#### Option B: Manual File Selection
1. Download individual credential files from the private repository
2. In the setup dialog, go to "📁 Select Files Manually" tab
3. Select each file individually:
   - Service Account file (usually has a long name like `water-levels-monitoring-xxxxx.json`)
   - OAuth Client file (starts with `client_secret_`)

#### Option C: Skip Setup
- Choose this only if you don't need Google Drive features
- The application will work but with limited cloud functionality

## 🗂️ File Structure After Setup

After successful installation and credential setup:

```
~/WaterLevelsApp/                    # Installation directory
├── app/                            # Application files
│   ├── config/                     # Configuration (including credentials)
│   │   ├── water-levels-monitoring-*.json     # Service account (from private repo)
│   │   ├── client_secret_*.json              # OAuth client (from private repo)
│   │   └── other config files...
│   ├── src/                        # Application source code
│   └── main.py                     # Main application file
├── venv/                           # Python virtual environment
└── Launchers:
    ├── water_levels_app.bat/.command         # Main application
    ├── water_levels_app_debug.bat/.command   # Debug mode
    └── water_level_visualizer_app.bat/.command # Visualizer tool
```

## ✨ What You Get

With proper credentials, you can use:
- ✅ **Google Drive Sync**: Automatic cloud synchronization
- ✅ **Shared Databases**: Access shared project databases
- ✅ **Auto Backup**: Automatic backup to Google Drive
- ✅ **Collaboration**: Multiple users on same projects
- ✅ **Remote Access**: Access data from anywhere

## 🔧 Troubleshooting

### Credential Issues
- **"Credentials not found"**: Make sure files are copied to `config/` folder
- **"Authentication failed"**: Check if service account has access to your Google Drive
- **"Wrong credentials"**: Ensure both files are from the same Google Cloud project

### Installation Issues
- **Permission errors**: Run installer as Administrator (Windows) or with sudo (Linux)
- **Python not found**: Install Python 3.8+ first
- **Dependencies fail**: Use debug launcher for detailed error messages

### Getting Help
1. Use debug launcher to see detailed error messages
2. Contact repository owner for credential-related issues
3. Create issue in main repository for application bugs

## 🔄 Updates

The application includes automatic updates:
- Updates check the public repository for new versions
- Credentials are preserved during updates
- You only need to set up credentials once

## 🔒 Security Notes

- **Never share credential files** publicly
- **Keep credentials secure** on your local machine
- **Don't commit credentials** to any public repository
- **Report security issues** to repository owner immediately

## 📞 Support

For credential access or setup issues:
- Contact repository owner directly
- Include your GitHub username for repository access
- Specify which features you need access to

For application issues:
- Use [GitHub Issues](https://github.com/benjaled/water_levels_monitoring_-for_external_edits-/issues)
- Include debug log output
- Mention if you're an authorized user

---

**Remember**: This setup process only needs to be done once. After initial setup, the application will remember your credentials and work normally.