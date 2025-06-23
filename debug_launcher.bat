@echo off
cd /d "S:\Water_Projects\CAESER\Water_Data_Series\water_levels_monitoring"
call "C:\Users\bledesma\WaterLevelsApp\venv\Scripts\activate.bat"
if not exist "C:\Users\bledesma\WaterLevelsApp\venv\Lib\site-packages\googleapiclient" (
    echo Installing missing Google API packages. Please wait...
    python -m pip install google-api-python-client google-auth-oauthlib --upgrade
)
if not exist "C:\Users\bledesma\WaterLevelsApp\venv\Lib\site-packages\pandas" (
    echo Installing missing pandas package. Please wait...
    python -m pip install pandas matplotlib scipy --upgrade
)
python "S:\Water_Projects\CAESER\Water_Data_Series\water_levels_monitoring\main.py"
pause
