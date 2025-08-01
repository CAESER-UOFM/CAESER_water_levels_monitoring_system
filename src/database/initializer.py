import sqlite3
import logging
from pathlib import Path
from PIL import Image, ImageDraw
import shutil
from typing import Union

logger = logging.getLogger(__name__)

class DatabaseInitializer:    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
    def initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            self._create_wells_table(cursor)
            self._create_well_flag_changes_table(cursor)
            self._create_user_notes_table(cursor)
            self._create_transducers_table(cursor)
            self._create_baro_tables(cursor)
            self._create_water_level_readings_table(cursor)
            self._create_master_baro_table(cursor) 
            self._create_manual_level_readings_table(cursor)
            self._create_water_level_meter_corrections_table(cursor)
            self._create_telemetry_level_readings_table(cursor)
            self._create_transducer_imported_files_table(cursor)  # Renamed method
            self._create_barologger_imported_files_table(cursor)  # New method
            self._create_well_statistics_table(cursor)
            self._create_xle_files_table(cursor)  # XLE file tracking
            self._create_recharge_calculations_tables(cursor)  # Recharge calculation storage
            
            pictures_dir = self.db_path.parent / 'well_pictures'
            pictures_dir.mkdir(exist_ok=True)
            
            default_picture = pictures_dir / 'default_well.jpg'
            if not default_picture.exists():
                img = Image.new('RGB', (400, 300), color='lightgray')
                d = ImageDraw.Draw(img)
                d.text((200, 150), "No Picture Available", fill='black')
                img.save(default_picture)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def _create_wells_table(self, cursor: sqlite3.Cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wells (
                well_number TEXT PRIMARY KEY,
                cae_number TEXT,
                latitude REAL,
                longitude REAL,
                top_of_casing REAL,
                aquifer TEXT,
                min_distance_to_stream REAL,
                well_field TEXT,
                cluster TEXT,
                county TEXT,
                picture_path TEXT DEFAULT 'default_well.jpg',
                picture_updated_at TIMESTAMP,
                data_source TEXT CHECK(data_source IN ('transducer', 'telemetry')),
                url TEXT,
                user_flag TEXT CHECK(user_flag IN ('unchecked', 'error', 'approved')) DEFAULT 'unchecked',
                baro_status TEXT CHECK(baro_status IN ('no_data','all_master','has_non_master')) DEFAULT 'no_data',
                level_status TEXT CHECK(level_status IN ('no_data','default_level','no_default')) DEFAULT 'no_data',
                parking_instructions TEXT,
                access_requirements TEXT,
                safety_notes TEXT,
                special_instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_well_flag_changes_table(self, cursor: sqlite3.Cursor):
        """Create table for tracking well user flag changes with comments"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS well_flag_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_id TEXT NOT NULL,
                old_flag_value TEXT,
                new_flag_value TEXT NOT NULL,
                comment TEXT NOT NULL,
                user_name TEXT,
                timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_id) REFERENCES wells (well_number)
            )
        ''')
    
    def _create_user_notes_table(self, cursor: sqlite3.Cursor):
        """Create table for tracking user notes about water level data analysis"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT NOT NULL,
                user_name TEXT NOT NULL,
                note_text TEXT NOT NULL,
                time_range_type TEXT CHECK(time_range_type IN ('full', 'specific')) NOT NULL,
                time_range_start TIMESTAMP,
                time_range_end TIMESTAMP,
                timestamp_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # Create index for efficient queries by well and creation time
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_notes_well_time 
            ON user_notes (well_number, created_at DESC)
        ''')
    
    def _create_transducers_table(self, cursor: sqlite3.Cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transducers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT UNIQUE,
                well_number TEXT,
                installation_date TIMESTAMP,
                end_date TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transducer_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT,
                well_number TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (serial_number) REFERENCES transducers (serial_number),
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
    
    def _create_baro_tables(self, cursor: sqlite3.Cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barologgers (
                serial_number TEXT PRIMARY KEY,
                location_description TEXT,
                installation_date TIMESTAMP,
                status TEXT CHECK(status IN ('active', 'inactive')),
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barologger_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT,
                location_description TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (serial_number) REFERENCES barologgers (serial_number)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barometric_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                pressure REAL,
                temperature REAL,
                quality_flag TEXT,
                notes TEXT,
                FOREIGN KEY (serial_number) REFERENCES barologgers (serial_number)
            )
        ''')
        
        # Optimized indices for barometric readings
        
        # Basic lookup index for serial + time for Julian timestamp sorting
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_barometric_readings_serial_time_julian
            ON barometric_readings (serial_number, julian_timestamp)
        ''')

        
        # For improved aggregation performance in barologger tab (legacy)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_barometric_readings_date_groups
            ON barometric_readings (serial_number, strftime('%Y-%m-%d', timestamp_utc))
        ''')
    
    def _create_master_baro_table(self, cursor: sqlite3.Cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_baro_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                pressure REAL,
                temperature REAL,
                source_barologgers TEXT,
                processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # Index for basic timestamp lookup operations (most common query pattern)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_master_baro_timestamp 
            ON master_baro_readings (julian_timestamp)
        ''')
        

#Water levels

    def _create_water_level_readings_table(self, cursor: sqlite3.Cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS water_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                pressure REAL,
                water_pressure REAL,
                water_level REAL,
                temperature REAL,
                serial_number TEXT,
                baro_flag TEXT,
                level_flag TEXT,
                temperature_spike_flag TEXT DEFAULT 'none',
                processing_date_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imported_time_range TEXT,
                source_xle_file TEXT,
                FOREIGN KEY (well_number) REFERENCES wells (well_number),
                FOREIGN KEY (serial_number) REFERENCES transducers (serial_number),
                UNIQUE (well_number, timestamp_utc)
            )
        ''')
        
        # Optimized indices for the most common query patterns
        
        # For well flag queries - optimize for well + flags #### Is this index working?
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_water_level_readings_well_flags
            ON water_level_readings (well_number, baro_flag, level_flag) 
        ''')
        
        # Basic lookup index for well + time using julian timestamp
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_water_level_readings_well_time 
            ON water_level_readings (well_number, julian_timestamp)
        ''')
        
    
    def _create_manual_level_readings_table(self, cursor: sqlite3.Cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manual_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                measurement_date_utc TIMESTAMP,
                dtw_avg REAL,
                dtw_1 REAL,
                dtw_2 REAL,
                tape_error REAL,
                comments TEXT,
                water_level REAL,
                data_source TEXT,
                collected_by TEXT,
                is_dry BOOLEAN DEFAULT 0,
                FOREIGN KEY (well_number) REFERENCES wells (well_number),
                UNIQUE(well_number, measurement_date_utc)
            )
        ''')

    def _create_water_level_meter_corrections_table(self, cursor: sqlite3.Cursor):
        """Create table for water level meter correction factors"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS water_level_meter_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                serial_number TEXT NOT NULL,
                range_start REAL NOT NULL,
                range_end REAL NOT NULL,
                correction_factor REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(serial_number, range_start, range_end)
            )
        ''')
    
    def _create_telemetry_level_readings_table(self, cursor: sqlite3.Cursor):
        """Create table for telemetry water level readings"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                water_level REAL,
                temperature REAL,
                dtw REAL,
                processing_date_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number),
                UNIQUE(well_number, timestamp_utc)
            )
        ''')
        
        # Optimized indices for telemetry readings

        # Basic lookup index for well + time using julian timestamp
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_telemetry_well_time 
            ON telemetry_level_readings (well_number, julian_timestamp)
        ''')


    def _create_transducer_imported_files_table(self, cursor: sqlite3.Cursor):
        """Create table for tracking imported transducer files"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transducer_imported_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                serial_number TEXT,
                starting_date TIMESTAMP,
                end_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number),
                FOREIGN KEY (serial_number) REFERENCES transducers (serial_number)
            )
        ''')
        
        # Create index for lookups by serial number
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transducer_imported_files_serial 
            ON transducer_imported_files (serial_number)
        ''')
        
    def _create_barologger_imported_files_table(self, cursor: sqlite3.Cursor):
        """Create table for tracking imported barologger files"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barologger_imported_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT,
                starting_date TIMESTAMP,
                end_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (serial_number) REFERENCES barologgers (serial_number)
            )
        ''')
        

    def _create_well_statistics_table(self, cursor: sqlite3.Cursor):
        """Create table for well statistics summaries"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS well_statistics (
                well_number TEXT PRIMARY KEY,
                num_points INTEGER DEFAULT 0,
                min_timestamp TEXT,
                max_timestamp TEXT,
                last_update TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
    
    def _create_xle_files_table(self, cursor: sqlite3.Cursor):
        """Create table for tracking XLE files and their upload status"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS xle_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT CHECK(file_type IN ('transducer', 'barologger')) NOT NULL,
                serial_number TEXT,
                well_number TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                file_size INTEGER,
                file_hash TEXT,
                local_import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upload_status TEXT CHECK(upload_status IN ('pending', 'uploading', 'uploaded', 'failed')) DEFAULT 'pending',
                cloud_file_id TEXT,
                cloud_folder_id TEXT,
                project_name TEXT,
                upload_timestamp TIMESTAMP,
                upload_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (serial_number) REFERENCES transducers (serial_number),
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # Indexes for efficient queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_xle_files_upload_status 
            ON xle_files (upload_status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_xle_files_project 
            ON xle_files (project_name, upload_status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_xle_files_well 
            ON xle_files (well_number, upload_status)
        ''')
    
    def _create_recharge_calculations_tables(self, cursor: sqlite3.Cursor):
        """Create tables for storing recharge calculation results"""
        
        # RISE method calculations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rise_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT NOT NULL,
                calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parameters TEXT NOT NULL,
                events_data TEXT NOT NULL,
                yearly_summary TEXT NOT NULL,
                total_recharge REAL NOT NULL,
                total_events INTEGER NOT NULL,
                annual_rate REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # MRC method calculations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mrc_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT NOT NULL,
                calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parameters TEXT NOT NULL,
                recession_data TEXT NOT NULL,
                yearly_summary TEXT NOT NULL,
                total_recharge REAL NOT NULL,
                total_periods INTEGER NOT NULL,
                annual_rate REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # ERC method calculations (for future implementation)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS erc_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT NOT NULL,
                calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parameters TEXT NOT NULL,
                curve_data TEXT NOT NULL,
                yearly_summary TEXT NOT NULL,
                total_recharge REAL NOT NULL,
                curve_quality REAL,
                annual_rate REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # Indexes for recharge calculations
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rise_calculations_well 
            ON rise_calculations (well_number, calculation_date DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_mrc_calculations_well 
            ON mrc_calculations (well_number, calculation_date DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_erc_calculations_well 
            ON erc_calculations (well_number, calculation_date DESC)
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_well_statistics_well_number
            ON well_statistics (well_number)
        ''')