#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Change to the project directory
cd "/Volumes/caeserdata/sharedworkspace/Water_Projects/CAESER/Water_Data_Series/water_levels_monitoring"
# Activate the virtual environment
source "/Users/bmac/WaterLevelsApp/venv/bin/activate"
# Run the application
python main.py
echo "Press Enter to exit..."
read
