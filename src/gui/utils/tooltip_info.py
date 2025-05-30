# src/gui/tooltip_info.py

class TooltipInfo:
    """Contains all tooltip and status bar messages for the application"""
    
    # Database Operations Section
    DB_OPS_GROUP = "Create or select a database for water level monitoring"
    DB_COMBO = "Select an existing database from the current project directory"
    NEW_DB = "Create a new empty database with the required structure"
    OPEN_DB = "Open an existing database from another location"
    CURRENT_DB = "Currently selected database"
    
    # Well Management Section
    WELL_MANAGEMENT = "Import wells from various sources and manage well data"
    IMPORT_SOURCE = "Select the source type for well data import"
    IMPORT_TYPE = "Choose to import all wells or select specific ones"
    CSV_FORMAT_BTN = "View required CSV format and example"
    IMPORT_BTN = "Start well import process with selected settings"
    
    # Barologger Management Section
    BARO_GROUP = "Manage barologgers and their assignments to wells"
    BARO_COMBO = "Select a barologger to manage its settings and assignments"
    REGISTER_BARO = "Register a new barologger in the system"
    ASSIGN_BARO = "Assign selected barologger to specific wells"
    
    # Status Section
    STATUS_GROUP = "Current database information and statistics"
    REFRESH_STATUS = "Update database statistics and status information"
    
    # Import Messages
    IMPORT_NO_DB = "Please create or select a database before importing data"
    IMPORT_SUCCESS = "Successfully imported {count} wells into the database"
    IMPORT_ERROR = "Error during import: {error}"
    
    # CSV Validation Messages
    CSV_MISSING_COLS = "Missing required columns: {columns}"
    CSV_INVALID_LAT = "Invalid latitude values found (must be between -90 and 90)"
    CSV_INVALID_LON = "Invalid longitude values found (must be between -180 and 180)"
    CSV_DUPLICATE_WELLS = "Duplicate well numbers found: {wells}"
    
    # Database Operation Messages
    DB_CREATE_SUCCESS = "Database created successfully: {name}"
    DB_CREATE_ERROR = "Failed to create database: {error}"
    DB_OPEN_ERROR = "Failed to open database: {error}"
    DB_REFRESH_ERROR = "Failed to refresh database status: {error}"
    
    # CSV Format Information
    CSV_FORMAT_INFO = """
    Required CSV Format for Well Import

    Required Columns:
    - WN (Well Number): Unique identifier
    - LAT (Latitude): Decimal degrees (-90 to 90)
    - LON (Longitude): Decimal degrees (-180 to 180)
    - TOC (Top of Casing): Elevation in feet
    - AQ (Aquifer): Aquifer designation

    Optional Columns:
    - CAE (Alternative Number): Secondary identifier
    - WF (Well Formation): Geological formation
    - CT (County): County name
    - RF_DATE (Reference Date): Date of measurement (MM/DD/YYYY)
    - RF_DW (Reference Depth to Water): In feet
    - Min_dist_stream: Distance to nearest stream in feet

    Example:
    WN,LAT,LON,TOC,AQ,CAE,WF,CT
    WELL001,35.1234,-89.9876,250.45,MRVA,CAE001,Memphis Sand,Shelby

    Notes:
    - Headers must match exactly (case-sensitive)
    - Use comma as delimiter
    - No special characters in well numbers
    - Dates in MM/DD/YYYY format
    - All numeric values should use decimal point (not comma)
    - Text values should not contain commas
    """
    
    # Dialog Titles
    TITLE_CSV_FORMAT = "Required CSV Format"
    TITLE_NEW_DB = "Create New Database"
    TITLE_OPEN_DB = "Open Database"
    TITLE_IMPORT = "Import Wells"
    TITLE_ERROR = "Error"
    TITLE_SUCCESS = "Success"
    TITLE_WARNING = "Warning"
    
    # Status Messages
    STATUS_NO_DB = "No database selected"
    STATUS_CURRENT_DB = "Current database: {name}"
    STATUS_WELLS = "Total Wells: {count}"
    STATUS_TRANSDUCERS = "Active Transducers: {count}"
    STATUS_BAROLOGGERS = "Active Barologgers: {count}"
    STATUS_LAST_UPDATE = "Last Update: {datetime}"
    
    # Field Validation Messages
    VALID_WELL_NUMBER = "Well number must be unique and contain only letters, numbers, and underscores"
    VALID_COORDINATES = "Coordinates must be in decimal degrees"
    VALID_ELEVATION = "Elevation must be a numeric value in feet"
    VALID_DATE = "Date must be in MM/DD/YYYY format"
    
    # Error Messages
    ERROR_FILE_NOT_FOUND = "File not found: {path}"
    ERROR_INVALID_FORMAT = "Invalid file format: {detail}"
    ERROR_DATABASE_LOCKED = "Database is locked by another process"
    ERROR_PERMISSION = "Permission denied: {detail}"
    ERROR_UNKNOWN = "An unexpected error occurred: {detail}"
    
    STATUS_LAST_UPDATE = "Last Update: {datetime}"

    # Barologger Management
    BARO_ADD = "Add a new barologger from manual entry, XLE file, or existing database"
    BARO_EDIT = "Edit selected barologger details"
    BARO_DELETE = "Remove selected barologger from database"
    BARO_LOCATION = "Update barologger location and track history"
    BARO_IMPORT_XLE = "Import barologger metadata from Solinst XLE file"
    BARO_IMPORT_DB = "Import barologger information from another database"
    BARO_LOCATION_HISTORY = "View location history for selected barologger"