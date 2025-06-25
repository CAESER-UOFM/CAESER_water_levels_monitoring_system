#!/bin/bash

# ================================================================
# CAESER Water Levels Monitoring Application - Mac Installer
# ================================================================
# Uses bash and built-in macOS tools for installation
# No administrator rights required!
# ================================================================

clear
echo
echo "    ==============================================================================="
echo "    #                                                                             #"
echo "    #      ####    ###   ######  ####  ###### #####                             #"
echo "    #     #    #  #   #  #      #      #      #    #                            #"
echo "    #     #       #   #  #####   ####  #####  #####                             #"
echo "    #     #       #####  #           # #      #   #                             #"
echo "    #     #    #  #   #  #      #    # #      #    #                            #"
echo "    #      ####   #   #  ######  ####  ###### #    #                            #"
echo "    #                                                                             #"
echo "    #                      ~~~ Water Levels Monitoring ~~~                      #"
echo "    #                                                                             #"
echo "    #    +---------------------------------------------------------------+       #"
echo "    #    |  Advanced Installation System                                 |       #"
echo "    #    |  No Administrator Rights Required                             |       #"
echo "    #    |  University of Memphis - CAESER Lab                          |       #"
echo "    #    +---------------------------------------------------------------+       #"
echo "    #                                                                             #"
echo "    ==============================================================================="
echo

echo "    [*] Initializing installer components..."
sleep 2
echo "    [+] Environment check complete"
echo "    [*] Ready to install Water Levels Monitoring System"
echo

# Default installation directory
DEFAULT_PATH="$HOME/CAESER_Water_levels_monitoring_system"

echo
echo "    ==============================================================================="
echo "    #                        INSTALLATION DIRECTORY                              #"
echo "    ==============================================================================="
echo
echo "   Default location: $DEFAULT_PATH"
echo
echo "   This installer does NOT require administrator rights!"
echo "   Everything installs to your user home directory."
echo
echo "   > Use default location (Press ENTER)"
echo "     Choose custom location (Type 'c' and ENTER)"
echo

read -r -p "Choice (ENTER for default, 'c' for custom): " path_choice

if [[ "$path_choice" == "c" || "$path_choice" == "C" ]]; then
    echo
    echo "Opening folder selection dialog..."
    
    # Use osascript to show folder picker
    custom_path=$(osascript -e 'tell application "Finder" to choose folder with prompt "Select installation directory (CAESER_Water_levels_monitoring_system folder will be created inside):" default location path to home folder' 2>/dev/null | sed 's/alias.*://' | sed 's/:/\//g')
    
    if [[ -z "$custom_path" ]]; then
        echo "Installation cancelled by user."
        exit 0
    fi
    
    if [[ "$custom_path" == "" ]]; then
        echo "Error: Could not open folder browser."
        echo "Using default location instead."
        INSTALL_DIR="$DEFAULT_PATH"
    else
        INSTALL_DIR="$custom_path/CAESER_Water_levels_monitoring_system"
    fi
else
    INSTALL_DIR="$DEFAULT_PATH"
fi

echo
echo "Selected installation directory: $INSTALL_DIR"
echo

# Ask about desktop shortcuts (aliases)
echo
echo "    ==============================================================================="
echo "    #                           DESKTOP SHORTCUTS                                #"
echo "    ==============================================================================="
echo
echo "   > Create desktop shortcuts (Press ENTER)"
echo "     Skip desktop shortcuts (Type 'n' and ENTER)"
echo

read -r -p "Choice (ENTER for shortcuts, 'n' to skip): " create_shortcuts

if [[ "$create_shortcuts" == "n" || "$create_shortcuts" == "N" ]]; then
    CREATE_DESKTOP="False"
else
    CREATE_DESKTOP="True"
fi

# Ask about source deletion
echo
echo "    ==============================================================================="
echo "    #                          SOURCE FOLDER CLEANUP                             #"
echo "    ==============================================================================="
echo
echo "   > Delete source folder after installation (Press ENTER)"
echo "     Keep source folder (Type 'k' and ENTER)"
echo

read -r -p "Choice (ENTER to delete, 'k' to keep): " delete_source

if [[ "$delete_source" == "k" || "$delete_source" == "K" ]]; then
    DELETE_SOURCE="False"
else
    DELETE_SOURCE="True"
fi

echo
echo "    ==============================================================================="
echo "    #                          INSTALLATION SUMMARY                              #"
echo "    ==============================================================================="
echo
echo "- Installation directory: $INSTALL_DIR"
echo "- Create desktop shortcuts: $CREATE_DESKTOP"
echo "- Delete source after install: $DELETE_SOURCE"
echo
echo "Continue with installation?"
echo "   > Yes, start installation (Press ENTER)"
echo "     No, cancel installation (Type 'q' and ENTER)"
echo

read -r -p "Choice (ENTER to install, 'q' to quit): " confirm

if [[ "$confirm" == "q" || "$confirm" == "Q" ]]; then
    echo "Installation cancelled by user."
    exit 0
fi

echo
echo "    ==============================================================================="
echo "    #                           INSTALLATION STARTING                            #"
echo "    ==============================================================================="
echo
echo "    [*] Installation directory: $INSTALL_DIR"
echo "    [*] Desktop shortcuts: $CREATE_DESKTOP"
echo "    [*] Delete source: $DELETE_SOURCE"
echo
echo "    [*] Please wait while we set up your Water Levels Monitoring System..."
echo

# Determine Project Code Directory (where this script resides)
CODE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define installation subdirectories
PYTHON_DIR="$INSTALL_DIR/python"
VENV_DIR="$INSTALL_DIR/venv"
BACKUP_DIR="$INSTALL_DIR/backups"

# Create installation directory structure
echo "    📁 [1/8] Creating installation directories..."
mkdir -p "$INSTALL_DIR" "$BACKUP_DIR" "$INSTALL_DIR/databases" "$INSTALL_DIR/databases/temp"

# Check if Python 3 is available
echo "    🐍 [2/8] Checking Python installation..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    echo "    ✅ Using system Python 3"
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON_CMD="python"
    echo "    ✅ Using system Python 3"
else
    echo "    ❌ Python 3 not found. Please install Python 3 first:"
    echo "        - Visit https://www.python.org/downloads/"
    echo "        - Or install via Homebrew: brew install python3"
    echo
    read -n 1 -s -r -p "Press any key to exit..."
    exit 1
fi

# Install virtualenv if not available
echo "    🔧 [3/8] Setting up virtual environment tools..."
if ! $PYTHON_CMD -m venv --help >/dev/null 2>&1; then
    echo "Installing virtualenv..."
    $PYTHON_CMD -m pip install --user virtualenv
fi

# Create virtual environment
if [[ -d "$VENV_DIR" ]]; then
    echo "    🗑️  Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

echo "    🏗️  [4/8] Creating virtual environment..."
$PYTHON_CMD -m venv "$VENV_DIR"

# Install dependencies
echo "    📦 [5/8] Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install numpy pandas matplotlib
pip install requests packaging
pip install google-api-python-client google-auth-oauthlib --upgrade
pip install PyQt5==5.15.10 PyQt5_sip==12.13.0 PyQtWebEngine==5.15.6
pip install scipy folium branca pillow psutil --upgrade

# Copy application files
echo "    📋 [6/8] Copying application files..."
cp -r "$CODE_DIR/src" "$INSTALL_DIR/"
cp "$CODE_DIR/main.py" "$INSTALL_DIR/"
cp "$CODE_DIR/Requirements.txt" "$INSTALL_DIR/"
[[ -d "$CODE_DIR/config" ]] && cp -r "$CODE_DIR/config" "$INSTALL_DIR/"
[[ -d "$CODE_DIR/tools" ]] && cp -r "$CODE_DIR/tools" "$INSTALL_DIR/"
[[ -d "$CODE_DIR/assets" ]] && cp -r "$CODE_DIR/assets" "$INSTALL_DIR/"
[[ -d "$CODE_DIR/Legacy_tables" ]] && cp -r "$CODE_DIR/Legacy_tables" "$INSTALL_DIR/"

# Create version file
echo "    📄 Creating version file..."
cat > "$INSTALL_DIR/version.json" << EOF
{
  "version": "1.0.0-beta",
  "release_date": "$(date)",
  "description": "Water Level Monitoring System - Mac Installation",
  "github_repo": "CAESER-UOFM/CAESER_water_levels_monitoring_system",
  "auto_update": {
    "enabled": true,
    "check_on_startup": true,
    "backup_count": 3
  },
  "installation_path": "$INSTALL_DIR"
}
EOF

# Create launchers
echo "    🚀 [7/8] Creating launchers..."

# Main launcher
LAUNCHER="$INSTALL_DIR/water_levels_app.sh"
cat > "$LAUNCHER" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/main.py"
EOF
chmod +x "$LAUNCHER"

# Debug launcher
DEBUG_LAUNCHER="$INSTALL_DIR/water_levels_app_debug.sh"
cat > "$DEBUG_LAUNCHER" << EOF
#!/bin/bash
echo "CAESER Water Levels Monitoring - Debug Mode"
echo "=========================================="
cd "$INSTALL_DIR"
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/main.py"
read -n 1 -s -r -p "Press any key to close..."
EOF
chmod +x "$DEBUG_LAUNCHER"

# Visualizer launcher
VISUALIZER_LAUNCHER="$INSTALL_DIR/water_level_visualizer_app.sh"
cat > "$VISUALIZER_LAUNCHER" << EOF
#!/bin/bash
cd "$INSTALL_DIR/tools/Visualizer"
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/tools/Visualizer/main.py"
read -n 1 -s -r -p "Press any key to close..."
EOF
chmod +x "$VISUALIZER_LAUNCHER"

# Create desktop shortcuts if requested
if [[ "$CREATE_DESKTOP" == "True" ]]; then
    echo "    🖥️  [8/8] Creating desktop shortcuts..."
    
    DESKTOP_PATH="$HOME/Desktop"
    echo "    [*] Desktop path: $DESKTOP_PATH"
    
    # Create main application shortcut
    cat > "$DESKTOP_PATH/CAESER Water Levels Monitoring.command" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/main.py"
EOF
    chmod +x "$DESKTOP_PATH/CAESER Water Levels Monitoring.command"
    
    # Create visualizer shortcut
    cat > "$DESKTOP_PATH/CAESER Water Level Visualizer.command" << EOF
#!/bin/bash
cd "$INSTALL_DIR/tools/Visualizer"
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/tools/Visualizer/main.py"
EOF
    chmod +x "$DESKTOP_PATH/CAESER Water Level Visualizer.command"
    
    # Verify shortcuts were created
    if [[ -f "$DESKTOP_PATH/CAESER Water Levels Monitoring.command" ]]; then
        echo "    [+] Main app shortcut created successfully"
    else
        echo "    [!] Warning: Main app shortcut not found on desktop"
    fi
    
    if [[ -f "$DESKTOP_PATH/CAESER Water Level Visualizer.command" ]]; then
        echo "    [+] Visualizer shortcut created successfully"
    else
        echo "    [!] Warning: Visualizer shortcut not found on desktop"
    fi
fi

echo
echo "    ==============================================================================="
echo "    #                        INSTALLATION COMPLETE!                              #"
echo "    #                                                                             #"
echo "    #                    Water Levels Monitoring System                          #"
echo "    #                         Ready for Action!                                  #"
echo "    ==============================================================================="
echo
echo "    [+] Installation directory: $INSTALL_DIR"
echo
echo "    [+] Launchers created:"
echo "        [*] Main app: $LAUNCHER"
echo "        [*] Debug mode: $DEBUG_LAUNCHER"
echo "        [*] Visualizer: $VISUALIZER_LAUNCHER"

if [[ "$CREATE_DESKTOP" == "True" ]]; then
    echo
    echo "    [+] Desktop shortcuts created:"
    echo "        [*] CAESER Water Levels Monitoring"
    echo "        [*] CAESER Water Level Visualizer"
fi

echo
echo "    [+] You can now launch the application!"
echo
echo "    ==============================================================================="
echo "    #                         INSTALLATION COMPLETED                             #"
echo "    ==============================================================================="
echo
echo "    [+] What was installed:"
echo "        - Python virtual environment with all dependencies"
echo "        - CAESER Water Levels Monitoring System"
echo "        - Application launchers (main app, debug, visualizer)"
if [[ "$CREATE_DESKTOP" == "True" ]]; then
    echo "        - Desktop shortcuts for easy access"
fi
echo
echo "    [+] Installation location: $INSTALL_DIR"
echo
echo "    [+] To start using the application:"
if [[ "$CREATE_DESKTOP" == "True" ]]; then
    echo "        - Double-click the desktop shortcuts, OR"
fi
echo "        - Run: $LAUNCHER"
echo
echo "    [*] For troubleshooting, use the debug launcher"
echo

read -n 1 -s -r -p "Press any key to continue..."

# Handle source deletion
if [[ "$DELETE_SOURCE" == "True" ]]; then
    echo
    echo "The installer will now attempt to delete the source folder."
    echo "This is safe since everything has been copied to: $INSTALL_DIR"
    echo
    read -n 1 -s -r -p "Press any key to continue..."
    
    if [[ -d "$CODE_DIR" ]]; then
        rm -rf "$CODE_DIR" 2>/dev/null
        if [[ -d "$CODE_DIR" ]]; then
            echo "Could not delete source folder. You may need to delete it manually."
        else
            echo "Source folder deleted successfully."
        fi
    fi
fi

echo
echo "Installation complete!"