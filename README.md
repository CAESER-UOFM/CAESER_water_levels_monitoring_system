# Water Levels Monitoring Application

## First Time Setup

### For Windows Users

1. Double-click `setup.bat` in the project folder.
   - This script will download and install Python 3.11.6 specifically for this application.
   - Creates a virtual environment in your user directory at `%USERPROFILE%\WaterLevelsApp`.
   - Installs all required packages from `Requirements.txt`.
   - Creates a launcher `start_app.bat` in your personal folder.

2. After the script completes, you can copy the launcher (`start_app.bat`) to your desktop for easy access.

### For macOS Users

1. Open Terminal and navigate to the project folder.
2. Make the setup script executable: `chmod +x setup.sh`
3. Run the setup script: `./setup.sh`
   - This script will install Python 3.11.6 using Homebrew.
   - Creates a virtual environment in your home directory at `~/WaterLevelsApp`.
   - Installs all required packages.
   - Creates an executable launcher `start_app.sh`.

4. You can run the launcher directly or create an alias for easier access.

## Running the Application

### Windows
- Simply double-click the `start_app.bat` launcher.
- This activates the virtual environment silently and starts the application.

### macOS
- Run the launcher with: `~/WaterLevelsApp/start_app.sh`
- Or use the alias if you created one.

## Shared Database

- Place your shared SQLite databases in the network folder that contains this project.
- The application will reference these database files relative to the project root.
- No additional configuration is needed for database paths.

## Troubleshooting

### Windows
1. Re-run `setup.bat` to repair the environment.
2. Ensure you have write permissions to `%USERPROFILE%\WaterLevelsApp`.
3. If you move the project folder, re-run `setup.bat` to update paths.

### macOS
1. Re-run `setup.sh` to repair the environment.
2. Check permissions with: `ls -la ~/WaterLevelsApp/`
3. If Homebrew installation fails, try installing it manually first.

## Updates

- To update the application, replace the contents of the shared project folder with the latest version.
- Users should re-run the setup script (`setup.bat` or `setup.sh`) after major updates.