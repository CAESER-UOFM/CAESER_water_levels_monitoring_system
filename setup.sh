#!/bin/bash

# Determine Project Code Directory (where this script resides)
CODE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Define installation directories
INSTALL_DIR="$HOME/WaterLevelsApp"
PYTHON_DIR="$INSTALL_DIR/python"
VENV_DIR="$INSTALL_DIR/venv"

echo "Setting up Water Levels Monitoring application..."
echo "Installation directory: $INSTALL_DIR"

# Create installation directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 using Homebrew or download it from python.org"
    echo "You can install it using: brew install python@3.11"
    exit 1
fi

# Remove existing virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment..."
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
EOF

# Install remaining requirements
echo "Installing remaining packages from temporary requirements..."
python -m pip install -r "$TEMP_REQUIREMENTS"
rm "$TEMP_REQUIREMENTS"

# Create normal launcher script
LAUNCHER="$INSTALL_DIR/water_levels_app.command"
cat > "$LAUNCHER" << EOF
#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
# Change to the project directory
cd "$CODE_DIR"
# Activate the virtual environment
source "$VENV_DIR/bin/activate"
# Run the application
python main.py
EOF
chmod +x "$LAUNCHER"

# Create debug launcher script
DEBUG_LAUNCHER="$INSTALL_DIR/water_levels_app_debug.command"
cat > "$DEBUG_LAUNCHER" << EOF
#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
# Change to the project directory
cd "$CODE_DIR"
# Activate the virtual environment
source "$VENV_DIR/bin/activate"
# Run the application
python main.py
echo "Press Enter to exit..."
read
EOF
chmod +x "$DEBUG_LAUNCHER"

# Create visualizer launcher script
VISUALIZER_LAUNCHER="$INSTALL_DIR/water_level_visualizer_app.command"
cat > "$VISUALIZER_LAUNCHER" << EOF
#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
# Change to the visualizer directory
cd "$CODE_DIR/tools/Visualizer"
# Activate the virtual environment
source "$VENV_DIR/bin/activate"
# Run the visualizer
python main.py
echo "Press Enter to exit..."
read
EOF
chmod +x "$VISUALIZER_LAUNCHER"

# Copy debug launcher to project folder
cp "$DEBUG_LAUNCHER" "$CODE_DIR/debug_launcher.command"
chmod +x "$CODE_DIR/debug_launcher.command"

echo
echo "Setup complete!"
echo "Launcher created at: $LAUNCHER"
echo "Debug launcher created at: $DEBUG_LAUNCHER"
echo "Visualizer launcher created at: $VISUALIZER_LAUNCHER"
echo
echo "For troubleshooting, use the debug launcher to see error messages."
echo
echo "You can create desktop shortcuts for these launchers for easy access."
echo 