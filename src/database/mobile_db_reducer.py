import sqlite3
import logging
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class MobileDatabaseReducer:
    """
    Creates an optimized version of the CAESER database for mobile visualization.
    Matches the exact schema used in the Turso optimized database.
    """
    
    def __init__(self, source_db_path: Path, target_db_path: Path):
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
    
    def create_reduced_database(self, well_number: Optional[str] = None):
        """
        Create an optimized database for mobile visualization.
        
        Args:
            well_number: If provided, only include data for this well
        """
        logger.info(f"Creating optimized database from {self.source_db_path} to {self.target_db_path}")
        
        # Remove existing target database if it exists
        if self.target_db_path.exists():
            self.target_db_path.unlink()
        
        with sqlite3.connect(self.source_db_path) as source_conn:
            with sqlite3.connect(self.target_db_path) as target_conn:
                target_cursor = target_conn.cursor()
                
                # Create optimized tables matching Turso schema exactly
                self._create_reduced_wells_table(target_cursor)
                self._create_reduced_water_level_readings_table(target_cursor)
                self._create_reduced_manual_level_readings_table(target_cursor)
                self._create_reduced_telemetry_level_readings_table(target_cursor)
                self._create_reduced_well_statistics_table(target_cursor)
                self._create_reduced_rise_calculations_table(target_cursor)
                self._create_reduced_master_baro_table(target_cursor)
                
                # Copy essential data
                self._copy_wells_data(source_conn, target_conn, well_number)
                self._copy_water_level_data(source_conn, target_conn, well_number)
                self._copy_manual_level_data(source_conn, target_conn, well_number)
                self._copy_telemetry_level_data(source_conn, target_conn, well_number)
                self._calculate_and_copy_well_statistics(source_conn, target_conn, well_number)
                self._copy_rise_calculations_data(source_conn, target_conn, well_number)
                self._copy_master_baro_data(source_conn, target_conn, well_number)
                
                target_conn.commit()
                
        logger.info(f"Optimized database created successfully at {self.target_db_path}")
    
    def _create_reduced_wells_table(self, cursor: sqlite3.Cursor):
        """Create wells table matching Turso optimized schema"""
        cursor.execute('''
            CREATE TABLE wells (
                well_number TEXT PRIMARY KEY,
                cae_number TEXT,
                latitude REAL,
                longitude REAL,
                aquifer TEXT,
                well_field TEXT,
                cluster TEXT,
                top_of_casing REAL
            )
        ''')
    
    def _create_reduced_water_level_readings_table(self, cursor: sqlite3.Cursor):
        """Create water level readings table matching Turso schema"""
        cursor.execute('''
            CREATE TABLE water_level_readings (
                well_number TEXT,
                reading_date TEXT,
                water_level REAL,
                temperature REAL
            )
        ''')
        
        # Create optimized index matching Turso
        cursor.execute('''
            CREATE INDEX idx_water_level_readings
            ON water_level_readings (well_number, reading_date)
        ''')
    
    def _create_reduced_manual_level_readings_table(self, cursor: sqlite3.Cursor):
        """Create manual readings table matching Turso schema"""
        cursor.execute('''
            CREATE TABLE manual_level_readings (
                well_number TEXT,
                measurement_date_utc TEXT,
                water_level REAL,
                dtw_avg REAL,
                comments TEXT,
                data_source TEXT
            )
        ''')
    
    def _create_reduced_telemetry_level_readings_table(self, cursor: sqlite3.Cursor):
        """Create telemetry readings table matching Turso schema"""
        cursor.execute('''
            CREATE TABLE telemetry_level_readings (
                well_number TEXT,
                timestamp_utc TEXT,
                water_level REAL,
                temperature REAL
            )
        ''')
    
    def _create_reduced_well_statistics_table(self, cursor: sqlite3.Cursor):
        """Create well statistics table matching Turso schema"""
        cursor.execute('''
            CREATE TABLE well_statistics (
                well_number TEXT PRIMARY KEY,
                total_readings INTEGER,
                data_start_date TEXT,
                data_end_date TEXT,
                total_days INTEGER,
                min_water_level REAL,
                max_water_level REAL,
                avg_water_level REAL,
                min_level_date TEXT,
                max_level_date TEXT,
                trend_direction TEXT,
                trend_change_per_year REAL,
                highest_month TEXT,
                lowest_month TEXT,
                readings_last_30_days INTEGER,
                last_reading_date TEXT
            )
        ''')
    
    def _create_reduced_rise_calculations_table(self, cursor: sqlite3.Cursor):
        """Create RISE calculations table matching Turso schema"""
        cursor.execute('''
            CREATE TABLE rise_calculations (
                well_number TEXT,
                calculation_date TEXT,
                parameters TEXT,
                events_data TEXT,
                yearly_summary TEXT,
                total_recharge REAL,
                total_events INTEGER,
                annual_rate REAL,
                notes TEXT
            )
        ''')
    
    def _create_reduced_master_baro_table(self, cursor: sqlite3.Cursor):
        """Create master baro readings table matching Turso schema for plotting"""
        cursor.execute('''
            CREATE TABLE master_baro_readings (
                timestamp_utc TEXT,
                julian_timestamp REAL,
                pressure REAL,
                temperature REAL,
                source_barologgers TEXT,
                processing_date TEXT,
                notes TEXT
            )
        ''')
        
        # Create optimized index for timestamp queries
        cursor.execute('''
            CREATE INDEX idx_master_baro_timestamp 
            ON master_baro_readings (timestamp_utc)
        ''')
    
    def _copy_wells_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy wells data with optimized columns matching Turso schema"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, cae_number, latitude, longitude, aquifer, 
                   well_field, cluster, top_of_casing
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
                             well_field, cluster, top_of_casing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', wells_data)
        
        logger.info(f"Copied {len(wells_data)} wells")
    
    def _copy_water_level_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy water level readings matching Turso schema (reading_date format)"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, timestamp_utc, water_level, temperature
            FROM water_level_readings
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        # Order by timestamp for better mobile performance
        query += ' ORDER BY well_number, timestamp_utc'
        
        source_cursor.execute(query, params)
        
        # Process in batches to manage memory
        batch_size = 10000
        total_copied = 0
        
        while True:
            batch = source_cursor.fetchmany(batch_size)
            if not batch:
                break
            
            # Convert timestamp_utc to reading_date format
            converted_batch = []
            for row in batch:
                well_number_val, timestamp_utc, water_level, temperature = row
                # Convert timestamp to reading_date format (YYYY-MM-DD HH:MM:SS)
                reading_date = timestamp_utc
                converted_batch.append((well_number_val, reading_date, water_level, temperature))
            
            target_cursor.executemany('''
                INSERT INTO water_level_readings (well_number, reading_date, water_level, temperature)
                VALUES (?, ?, ?, ?)
            ''', converted_batch)
            
            total_copied += len(batch)
            logger.info(f"Copied {total_copied} water level readings...")
        
        logger.info(f"Total water level readings copied: {total_copied}")
    
    def _copy_manual_level_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy manual level readings matching Turso schema"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        query = '''
            SELECT well_number, measurement_date_utc, water_level, dtw_avg, 
                   comments, data_source
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
                                             dtw_avg, comments, data_source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', manual_data)
        
        logger.info(f"Copied {len(manual_data)} manual level readings")
    
    def _copy_telemetry_level_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy telemetry level readings matching Turso schema"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        # Check if telemetry table exists
        source_cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='telemetry_level_readings'
        """)
        if not source_cursor.fetchone():
            logger.info("No telemetry_level_readings table found in source database")
            return
        
        query = '''
            SELECT well_number, timestamp_utc, water_level, temperature
            FROM telemetry_level_readings
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        # Order by timestamp for better mobile performance
        query += ' ORDER BY well_number, timestamp_utc'
        
        source_cursor.execute(query, params)
        
        # Process in batches
        batch_size = 10000
        total_copied = 0
        
        while True:
            batch = source_cursor.fetchmany(batch_size)
            if not batch:
                break
            
            target_cursor.executemany('''
                INSERT INTO telemetry_level_readings (well_number, timestamp_utc, water_level, temperature)
                VALUES (?, ?, ?, ?)
            ''', batch)
            
            total_copied += len(batch)
            logger.info(f"Copied {total_copied} telemetry level readings...")
        
        logger.info(f"Total telemetry level readings copied: {total_copied}")
    
    def _calculate_and_copy_well_statistics(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Calculate and create well statistics matching Turso schema"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        # Get list of wells to process
        if well_number:
            wells = [(well_number,)]
        else:
            source_cursor.execute("SELECT DISTINCT well_number FROM water_level_readings")
            wells = source_cursor.fetchall()
        
        for (well,) in wells:
            # Calculate statistics for each well
            stats_query = '''
                SELECT 
                    COUNT(*) as total_readings,
                    MIN(timestamp_utc) as data_start_date,
                    MAX(timestamp_utc) as data_end_date,
                    MIN(water_level) as min_water_level,
                    MAX(water_level) as max_water_level,
                    AVG(water_level) as avg_water_level
                FROM water_level_readings
                WHERE well_number = ?
            '''
            source_cursor.execute(stats_query, (well,))
            stats = source_cursor.fetchone()
            
            if stats and stats[0] > 0:  # If there are readings
                total_readings, start_date, end_date, min_level, max_level, avg_level = stats
                
                # Calculate total days
                if start_date and end_date:
                    start_dt = datetime.fromisoformat(start_date.replace(' ', 'T'))
                    end_dt = datetime.fromisoformat(end_date.replace(' ', 'T'))
                    total_days = (end_dt - start_dt).days
                else:
                    total_days = 0
                
                # Get dates for min/max levels
                source_cursor.execute(
                    "SELECT timestamp_utc FROM water_level_readings WHERE well_number = ? AND water_level = ? LIMIT 1",
                    (well, min_level)
                )
                min_result = source_cursor.fetchone()
                min_level_date = min_result[0] if min_result else None
                
                source_cursor.execute(
                    "SELECT timestamp_utc FROM water_level_readings WHERE well_number = ? AND water_level = ? LIMIT 1",
                    (well, max_level)
                )
                max_result = source_cursor.fetchone()
                max_level_date = max_result[0] if max_result else None
                
                # Count readings in last 30 days
                source_cursor.execute(
                    "SELECT COUNT(*) FROM water_level_readings WHERE well_number = ? AND timestamp_utc > datetime('now', '-30 days')",
                    (well,)
                )
                readings_last_30_days = source_cursor.fetchone()[0]
                
                # Simple trend calculation (could be enhanced)
                trend_direction = 'stable'
                trend_change_per_year = 0.0
                
                # Monthly analysis for highest/lowest months
                source_cursor.execute('''
                    SELECT strftime('%m', timestamp_utc) as month, AVG(water_level) as avg_level
                    FROM water_level_readings
                    WHERE well_number = ?
                    GROUP BY month
                    ORDER BY avg_level
                ''', (well,))
                monthly_data = source_cursor.fetchall()
                if monthly_data:
                    lowest_month = monthly_data[0][0]  # Month with lowest average
                    highest_month = monthly_data[-1][0]  # Month with highest average
                else:
                    lowest_month = highest_month = None
                
                # Insert calculated statistics
                target_cursor.execute('''
                    INSERT INTO well_statistics (
                        well_number, total_readings, data_start_date, data_end_date,
                        total_days, min_water_level, max_water_level, avg_water_level,
                        min_level_date, max_level_date, trend_direction, trend_change_per_year,
                        highest_month, lowest_month, readings_last_30_days, last_reading_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    well, total_readings, start_date, end_date,
                    total_days, min_level, max_level, avg_level,
                    min_level_date, max_level_date, trend_direction, trend_change_per_year,
                    highest_month, lowest_month, readings_last_30_days, end_date
                ))
        
        logger.info(f"Calculated and inserted statistics for {len(wells)} wells")
    
    def _copy_rise_calculations_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy RISE calculation results matching Turso schema"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        # Check if rise_calculations table exists
        source_cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='rise_calculations'
        """)
        if not source_cursor.fetchone():
            logger.info("No rise_calculations table found in source database")
            return
        
        query = '''
            SELECT well_number, calculation_date, parameters, events_data, 
                   yearly_summary, total_recharge, total_events, annual_rate, notes
            FROM rise_calculations
        '''
        params = []
        
        if well_number:
            query += ' WHERE well_number = ?'
            params.append(well_number)
        
        query += ' ORDER BY well_number, calculation_date DESC'
        
        source_cursor.execute(query, params)
        rise_data = source_cursor.fetchall()
        
        if rise_data:
            target_cursor.executemany('''
                INSERT INTO rise_calculations (well_number, calculation_date, parameters, events_data,
                                             yearly_summary, total_recharge, total_events, annual_rate, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', rise_data)
            
            logger.info(f"Copied {len(rise_data)} RISE calculation records")
        else:
            logger.info("No RISE calculation data to copy")
    
    def _copy_master_baro_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, well_number: Optional[str]):
        """Copy master barometric readings for plotting support"""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        # Check if master_baro_readings table exists
        source_cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='master_baro_readings'
        """)
        if not source_cursor.fetchone():
            logger.info("No master_baro_readings table found in source database")
            return
        
        # If well_number is specified, we need to get the time range from water level data
        if well_number:
            # Get time range for the specific well
            source_cursor.execute("""
                SELECT MIN(timestamp_utc), MAX(timestamp_utc)
                FROM water_level_readings
                WHERE well_number = ?
            """, (well_number,))
            time_range = source_cursor.fetchone()
            
            if not time_range or not time_range[0]:
                logger.info(f"No water level data found for well {well_number}")
                return
            
            min_time, max_time = time_range
            
            # Copy master baro data for this time range
            query = '''
                SELECT timestamp_utc, julian_timestamp, pressure, temperature,
                       source_barologgers, processing_date, notes
                FROM master_baro_readings
                WHERE timestamp_utc BETWEEN ? AND ?
                ORDER BY julian_timestamp
            '''
            params = (min_time, max_time)
        else:
            # Copy all master baro data
            query = '''
                SELECT timestamp_utc, julian_timestamp, pressure, temperature,
                       source_barologgers, processing_date, notes
                FROM master_baro_readings
                ORDER BY julian_timestamp
            '''
            params = []
        
        source_cursor.execute(query, params)
        
        # Process in batches to manage memory
        batch_size = 10000
        total_copied = 0
        
        while True:
            batch = source_cursor.fetchmany(batch_size)
            if not batch:
                break
            
            target_cursor.executemany('''
                INSERT INTO master_baro_readings (timestamp_utc, julian_timestamp, pressure, temperature,
                                                source_barologgers, processing_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            
            total_copied += len(batch)
            logger.info(f"Copied {total_copied} master baro readings...")
        
        logger.info(f"Total master baro readings copied: {total_copied}")
    
    def get_database_size_info(self) -> dict:
        """Get size information about source and target databases"""
        info = {}
        
        # Source database info
        if self.source_db_path.exists():
            info['source_size_mb'] = self.source_db_path.stat().st_size / (1024 * 1024)
            
            with sqlite3.connect(self.source_db_path) as conn:
                cursor = conn.cursor()
                
                # Get source counts safely
                try:
                    cursor.execute("SELECT COUNT(*) FROM water_level_readings")
                    info['source_water_level_count'] = cursor.fetchone()[0]
                except:
                    info['source_water_level_count'] = 0
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM manual_level_readings")
                    info['source_manual_count'] = cursor.fetchone()[0]
                except:
                    info['source_manual_count'] = 0
                
                # Check for telemetry data
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='telemetry_level_readings'
                """)
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM telemetry_level_readings")
                    info['source_telemetry_count'] = cursor.fetchone()[0]
                else:
                    info['source_telemetry_count'] = 0
                
                # Check for RISE calculations
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='rise_calculations'
                """)
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM rise_calculations")
                    info['source_rise_calculations_count'] = cursor.fetchone()[0]
                else:
                    info['source_rise_calculations_count'] = 0
                
                # Check for master baro data
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='master_baro_readings'
                """)
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM master_baro_readings")
                    info['source_master_baro_count'] = cursor.fetchone()[0]
                else:
                    info['source_master_baro_count'] = 0
        
        # Target database info
        if self.target_db_path.exists():
            info['target_size_mb'] = self.target_db_path.stat().st_size / (1024 * 1024)
            
            with sqlite3.connect(self.target_db_path) as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM water_level_readings")
                    info['target_water_level_count'] = cursor.fetchone()[0]
                except:
                    info['target_water_level_count'] = 0
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM manual_level_readings")
                    info['target_manual_count'] = cursor.fetchone()[0]
                except:
                    info['target_manual_count'] = 0
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM telemetry_level_readings")
                    info['target_telemetry_count'] = cursor.fetchone()[0]
                except:
                    info['target_telemetry_count'] = 0
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM rise_calculations")
                    info['target_rise_calculations_count'] = cursor.fetchone()[0]
                except:
                    info['target_rise_calculations_count'] = 0
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM wells")
                    info['target_wells_count'] = cursor.fetchone()[0]
                except:
                    info['target_wells_count'] = 0
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM master_baro_readings")
                    info['target_master_baro_count'] = cursor.fetchone()[0]
                except:
                    info['target_master_baro_count'] = 0
        
        return info


def create_mobile_database(source_db_path: str, target_db_path: str, well_number: Optional[str] = None) -> dict:
    """
    Convenience function to create an optimized database for mobile visualization.
    
    Args:
        source_db_path: Path to the source CAESER database
        target_db_path: Path where the optimized database should be created
        well_number: Optional well number to filter data (for testing with single well)
    
    Returns:
        Dictionary with size reduction information
    """
    source_path = Path(source_db_path)
    target_path = Path(target_db_path)
    
    reducer = MobileDatabaseReducer(source_path, target_path)
    reducer.create_reduced_database(well_number)
    
    return reducer.get_database_size_info()