import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class MobileDatabaseReducer:
    """
    Creates a reduced version of the CAESER database optimized for mobile visualization.
    Removes unnecessary columns and includes only essential data for cloud sync.
    """
    
    def __init__(self, source_db_path: Path, target_db_path: Path):
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
    
    def create_reduced_database(self, well_number: Optional[str] = None):
        """
        Create a reduced database for mobile visualization.
        
        Args:
            well_number: If provided, only include data for this well
        """
        logger.info(f"Creating reduced database from {self.source_db_path} to {self.target_db_path}")
        
        # Remove existing target database if it exists
        if self.target_db_path.exists():
            self.target_db_path.unlink()
        
        with sqlite3.connect(self.source_db_path) as source_conn:
            with sqlite3.connect(self.target_db_path) as target_conn:
                target_cursor = target_conn.cursor()
                
                # Create reduced tables
                self._create_reduced_wells_table(target_cursor)
                self._create_reduced_water_level_readings_table(target_cursor)
                self._create_reduced_manual_level_readings_table(target_cursor)
                self._create_reduced_well_statistics_table(target_cursor)
                
                # Copy essential data
                self._copy_wells_data(source_conn, target_conn, well_number)
                self._copy_water_level_data(source_conn, target_conn, well_number)
                self._copy_manual_level_data(source_conn, target_conn, well_number)
                self._copy_well_statistics_data(source_conn, target_conn, well_number)
                
                target_conn.commit()
                
        logger.info(f"Reduced database created successfully at {self.target_db_path}")
    
    def _create_reduced_wells_table(self, cursor: sqlite3.Cursor):
        """Create wells table with only essential columns for mobile visualization"""
        cursor.execute('''
            CREATE TABLE wells (
                well_number TEXT PRIMARY KEY,
                cae_number TEXT,
                latitude REAL,
                longitude REAL,
                aquifer TEXT,
                well_field TEXT,
                cluster TEXT,
                county TEXT,
                data_source TEXT,
                user_flag TEXT DEFAULT 'unchecked',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_reduced_water_level_readings_table(self, cursor: sqlite3.Cursor):
        """Create water level readings table with only visualization essentials"""
        cursor.execute('''
            CREATE TABLE water_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                timestamp_utc TIMESTAMP,
                julian_timestamp REAL,
                water_level REAL,
                temperature REAL,
                baro_flag TEXT,
                level_flag TEXT,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
        
        # Create optimized index for mobile queries
        cursor.execute('''
            CREATE INDEX idx_water_level_mobile
            ON water_level_readings (well_number, julian_timestamp)
        ''')
    
    def _create_reduced_manual_level_readings_table(self, cursor: sqlite3.Cursor):
        """Create manual readings table with essential columns"""
        cursor.execute('''
            CREATE TABLE manual_level_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                well_number TEXT,
                measurement_date_utc TIMESTAMP,
                water_level REAL,
                dtw_avg REAL,
                comments TEXT,
                data_source TEXT,
                is_dry BOOLEAN DEFAULT 0,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
    
    def _create_reduced_well_statistics_table(self, cursor: sqlite3.Cursor):
        """Create well statistics table for mobile optimization"""
        cursor.execute('''
            CREATE TABLE well_statistics (
                well_number TEXT PRIMARY KEY,
                num_points INTEGER DEFAULT 0,
                min_timestamp TEXT,
                max_timestamp TEXT,
                last_update TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (well_number) REFERENCES wells (well_number)
            )
        ''')
    
    def _copy_wells_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy wells data with reduced columns"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, cae_number, latitude, longitude, aquifer, 
                   well_field, cluster, county, data_source, user_flag, created_at
            FROM wells
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        source_cursor.execute(query, params)
        wells_data = source_cursor.fetchall()
        
        target_cursor.executemany('''
            INSERT INTO wells (well_number, cae_number, latitude, longitude, aquifer,
                             well_field, cluster, county, data_source, user_flag, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', wells_data)
        
        logger.info(f"Copied {len(wells_data)} wells")
    
    def _copy_water_level_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy water level readings with reduced columns"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, timestamp_utc, julian_timestamp, water_level, 
                   temperature, baro_flag, level_flag
            FROM water_level_readings
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        # Order by timestamp for better mobile performance
        query += ' ORDER BY well_number, julian_timestamp'
        
        source_cursor.execute(query, params)
        
        # Process in batches to manage memory
        batch_size = 10000
        total_copied = 0
        
        while True:
            batch = source_cursor.fetchmany(batch_size)
            if not batch:
                break
            
            target_cursor.executemany('''
                INSERT INTO water_level_readings (well_number, timestamp_utc, julian_timestamp, 
                                                 water_level, temperature, baro_flag, level_flag)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            
            total_copied += len(batch)
            logger.info(f"Copied {total_copied} water level readings...")
        
        logger.info(f"Total water level readings copied: {total_copied}")
    
    def _copy_manual_level_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy manual level readings with reduced columns"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, measurement_date_utc, water_level, dtw_avg, 
                   comments, data_source, is_dry
            FROM manual_level_readings
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        source_cursor.execute(query, params)
        manual_data = source_cursor.fetchall()
        
        target_cursor.executemany('''
            INSERT INTO manual_level_readings (well_number, measurement_date_utc, water_level,
                                             dtw_avg, comments, data_source, is_dry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', manual_data)
        
        logger.info(f"Copied {len(manual_data)} manual level readings")
    
    def _copy_well_statistics_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy well statistics data"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, num_points, min_timestamp, max_timestamp, last_update
            FROM well_statistics
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        source_cursor.execute(query, params)
        stats_data = source_cursor.fetchall()
        
        if stats_data:
            target_cursor.executemany('''
                INSERT INTO well_statistics (well_number, num_points, min_timestamp, 
                                           max_timestamp, last_update)
                VALUES (?, ?, ?, ?, ?)
            ''', stats_data)
            
            logger.info(f"Copied {len(stats_data)} well statistics records")
    
    def get_database_size_info(self) -> dict:
        """Get size information about source and target databases"""
        info = {}
        
        # Source database info
        if self.source_db_path.exists():
            info['source_size_mb'] = self.source_db_path.stat().st_size / (1024 * 1024)
            
            with sqlite3.connect(self.source_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM water_level_readings")
                info['source_water_level_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM manual_level_readings")
                info['source_manual_count'] = cursor.fetchone()[0]
        
        # Target database info
        if self.target_db_path.exists():
            info['target_size_mb'] = self.target_db_path.stat().st_size / (1024 * 1024)
            
            with sqlite3.connect(self.target_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM water_level_readings")
                info['target_water_level_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM manual_level_readings")
                info['target_manual_count'] = cursor.fetchone()[0]
        
        return info


def create_mobile_database(source_db_path: str, target_db_path: str, well_number: Optional[str] = None) -> dict:
    """
    Convenience function to create a reduced database for mobile visualization.
    
    Args:
        source_db_path: Path to the source CAESER database
        target_db_path: Path where the reduced database should be created
        well_number: Optional well number to filter data (for testing with single well)
    
    Returns:
        Dictionary with size reduction information
    """
    source_path = Path(source_db_path)
    target_path = Path(target_db_path)
    
    reducer = MobileDatabaseReducer(source_path, target_path)
    reducer.create_reduced_database(well_number)
    
    return reducer.get_database_size_info()