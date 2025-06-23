#!/bin/bash

# Enhanced Setup Script for Water Levels Monitoring Application
# Includes auto-update system and improved directory structure

# Determine Project Code Directory (where this script resides)
CODE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Define installation directories
INSTALL_DIR="$HOME/WaterLevelsApp"
VENV_DIR="$INSTALL_DIR/venv"
APP_DIR="$INSTALL_DIR/app"
BACKUP_DIR="$INSTALL_DIR/backups"

echo "==============================================="
echo "Water Levels Monitoring Application Setup"
echo "Enhanced Installation with Auto-Update System"
echo "==============================================="
echo "Installation directory: $INSTALL_DIR"
echo

# Create installation directory structure
echo "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$BACKUP_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first:"
    echo
    echo "On macOS with Homebrew:"
    echo "  brew install python@3.11"
    echo
    echo "On Ubuntu/Debian:"
    echo "  sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo
    echo "On CentOS/RHEL:"
    echo "  sudo yum install python3 python3-pip"
    echo
    exit 1
fi

# Remove existing virtual environment if it exists (for clean install)
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment for clean install..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment
echo "Creating virtual environment in $VENV_DIR..."
python3 -m venv "$VENV_DIR"

# Install dependencies
echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install core dependencies first with compatible versions
echo "Installing core dependencies..."
python -m pip install "pandas>=2.0.0" "numpy>=1.24.0" "matplotlib>=3.7.0"

# Install auto-update dependencies
echo "Installing auto-update system dependencies..."
python -m pip install "requests>=2.28.0" "packaging>=21.0"

# Install PyQt5 and WebEngine components
echo "Installing PyQt5 and WebEngine components..."
python -m pip install "PyQt5>=5.15.11" "PyQtWebEngine>=5.15.6"

# Create a temporary requirements file with compatible versions
TEMP_REQUIREMENTS="$INSTALL_DIR/temp_requirements.txt"
cat > "$TEMP_REQUIREMENTS" << EOF
branca>=0.8.1
folium>=0.19.4
google-api-python-client>=2.161.0
google-auth-oauthlib>=1.2.1
scipy>=1.10.0
pillow>=9.0.0
psutil>=5.9.0
EOF

# Install remaining requirements
echo "Installing remaining packages from temporary requirements..."
python -m pip install -r "$TEMP_REQUIREMENTS"
rm "$TEMP_REQUIREMENTS"

# Copy application files to installation directory
echo "Copying application files..."
cp -r "$CODE_DIR/../src" "$APP_DIR/"
cp "$CODE_DIR/../main.py" "$APP_DIR/"
cp "$CODE_DIR/../Requirements.txt" "$APP_DIR/"
if [ -d "$CODE_DIR/../config" ]; then
    cp -r "$CODE_DIR/../config" "$APP_DIR/"
fi
if [ -d "$CODE_DIR/../tools" ]; then
    cp -r "$CODE_DIR/../tools" "$APP_DIR/"
fi

# Create version.json file
echo "Creating version file..."
cat > "$APP_DIR/version.json" << EOF
{
  "version": "1.0.0",
  "release_date": "$(date +%Y-%m-%d)",
  "description": "Water Level Monitoring System - Initial Installation",
  "github_repo": "benjaled/water_levels_monitoring_-for_external_edits-",
  "auto_update": {
    "enabled": true,
    "check_on_startup": true,
    "backup_count": 3
  },
  "installation_path": "$APP_DIR"
}
EOF

# Create enhanced launcher script with auto-update check
LAUNCHER="$INSTALL_DIR/water_levels_app.command"
cat > "$LAUNCHER" << EOF
#!/bin/bash
# Water Levels Monitoring Application Launcher
# With Auto-Update Support

# Get the directory where this script is located
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"

# Change to the application directory
cd "$APP_DIR"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Check for missing dependencies and install if needed
echo "Checking dependencies..."

if ! python -c "import googleapiclient" 2>/dev/null; then
    echo "Installing missing Google API packages. Please wait..."
    python -m pip install google-api-python-client google-auth-oauthlib --upgrade
fi

if ! python -c "import pandas" 2>/dev/null; then
    echo "Installing missing pandas package. Please wait..."
    python -m pip install pandas matplotlib scipy --upgrade
fi

if ! python -c "import requests" 2>/dev/null; then
    echo "Installing missing requests package for auto-update. Please wait..."
    python -m pip install requests packaging --upgrade
fi

# Run the application
python "$APP_DIR/main.py"
EOF
chmod +x "$LAUNCHER"

# Create debug launcher script
DEBUG_LAUNCHER="$INSTALL_DIR/water_levels_app_debug.command"
cat > "$DEBUG_LAUNCHER" << EOF
#!/bin/bash
echo "Water Levels Monitoring Application - Debug Mode"
echo "============================================="

# Change to the application directory
cd "$APP_DIR"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

echo
echo "Python version:"
python --version
echo

echo "Checking critical dependencies..."
python -c "import pandas; print('pandas: OK')" 2>&1 || echo "pandas: MISSING"
python -c "import matplotlib; print('matplotlib: OK')" 2>&1 || echo "matplotlib: MISSING"
python -c "import PyQt5; print('PyQt5: OK')" 2>&1 || echo "PyQt5: MISSING"
python -c "import requests; print('requests: OK')" 2>&1 || echo "requests: MISSING"
python -c "import googleapiclient; print('Google API: OK')" 2>&1 || echo "Google API: MISSING"

echo
echo "Starting application..."
python "$APP_DIR/main.py"

echo
echo "Application ended. Press Enter to close..."
read
EOF
chmod +x "$DEBUG_LAUNCHER"

# Create visualizer launcher script
VISUALIZER_LAUNCHER="$INSTALL_DIR/water_level_visualizer_app.command"
cat > "$VISUALIZER_LAUNCHER" << EOF
#!/bin/bash
# Change to the visualizer directory
cd "$APP_DIR/tools/Visualizer"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Check for matplotlib
if ! python -c "import matplotlib" 2>/dev/null; then
    echo "Installing missing matplotlib package. Please wait..."
    python -m pip install pandas matplotlib scipy --upgrade
fi

# Run the visualizer
python "$APP_DIR/tools/Visualizer/main.py"
echo "Press Enter to exit..."
read
EOF
chmod +x "$VISUALIZER_LAUNCHER"

# Create uninstaller script
UNINSTALLER="$INSTALL_DIR/uninstall.command"
cat > "$UNINSTALLER" << EOF
#!/bin/bash
echo "Water Levels Monitoring Application Uninstaller"
echo "==============================================="
echo
echo "This will completely remove the Water Levels Monitoring application"
echo "and all its data from your computer."
echo
echo "Installation directory: $INSTALL_DIR"
echo

read -p "Are you sure you want to uninstall? (y/N): " confirm
if [[ \$confirm != [yY] ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo
echo "Removing application files..."
cd "\$HOME"
rm -rf "$INSTALL_DIR"
echo
echo "Uninstall complete."
echo "Press Enter to close..."
read
EOF
chmod +x "$UNINSTALLER"

# Copy debug launcher to project folder for development
cp "$DEBUG_LAUNCHER" "$CODE_DIR/../debug_launcher.command"
chmod +x "$CODE_DIR/../debug_launcher.command"

echo
echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo
echo "Installation directory: $INSTALL_DIR"
echo "Application files: $APP_DIR"
echo
echo "Launchers created:"
echo "  Main app: $LAUNCHER"
echo "  Debug mode: $DEBUG_LAUNCHER"
echo "  Visualizer: $VISUALIZER_LAUNCHER"
echo "  Uninstaller: $UNINSTALLER"
echo
echo "Features included:"
echo "  ✓ Isolated Python environment"
echo "  ✓ All dependencies installed"
echo "  ✓ Auto-update system enabled"
echo "  ✓ Backup system for safe updates"
echo "  ✓ Debug mode for troubleshooting"
echo "  ✓ Easy uninstall option"
echo
echo "You can create desktop shortcuts for these launchers for easy access."
echo "The application will automatically check for updates on startup."
echo
echo "For troubleshooting, use the debug launcher to see detailed error messages."
echo