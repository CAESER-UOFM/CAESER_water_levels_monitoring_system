import sqlite3
import pandas as pd
import logging
import psutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class FastDataManager:
    """Optimized data manager for fastest possible loading."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._db_manager = None
        self._schema_cache = {}
        self._data_cache = {}
        self._initialize_db_manager()
        # Pre-warm database connection to avoid cold start delay
        self._pre_warm_database()
    
    def _initialize_db_manager(self):
        """Initialize the database manager if not already done"""
        try:
            from simple_db_manager import SimpleDatabaseManager
            db_size_mb = Path(self.db_path).stat().st_size / (1024 * 1024)
            quick_validation = db_size_mb > 100
            self._db_manager = SimpleDatabaseManager(self.db_path, quick_validation=quick_validation, deferred_init=True)
            logger.info(f"Initialized FastDataManager for {self.db_path} (size: {db_size_mb:.2f} MB)")
        except Exception as e:
            logger.error(f"Failed to initialize SimpleDatabaseManager: {e}")
            self._db_manager = None
    
    def _pre_warm_database(self):
        """Pre-warm database connection to avoid cold start delay."""
        import threading
        import time
        
        def warm_connection():
            try:
                logger.info("[PREWARM] Starting database pre-warm...")
                start_time = time.time()
                
                # Create a connection and run a simple query
                conn = self.get_optimized_connection()
                cursor = conn.cursor()
                
                # Run a simple query to warm up the database cache
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                # Also warm up the wells table
                cursor.execute("SELECT COUNT(*) FROM wells")
                well_count = cursor.fetchone()[0]
                
                self.release_connection(conn)
                
                elapsed = time.time() - start_time
                logger.info(f"[PREWARM] Database pre-warm complete: {table_count} tables, {well_count} wells, took {elapsed:.3f}s")
                
            except Exception as e:
                logger.warning(f"[PREWARM] Database pre-warm failed: {e}")
        
        # Run in background thread to not block initialization
        thread = threading.Thread(target=warm_connection, daemon=True)
        thread.start()

    def get_optimized_connection(self):
        """Create and return a connection with optimized PRAGMA settings."""
        if self._db_manager:
            return self._db_manager.get_connection()
        
        # Fallback to direct connection with minimal settings
        conn = sqlite3.connect(self.db_path)
        # Apply minimal settings for speed
        conn.execute('PRAGMA journal_mode = OFF')
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA cache_size = -50000')  # 50MB cache
        return conn
    
    def release_connection(self, conn):
        """Return a connection to the pool when done"""
        if self._db_manager:
            self._db_manager.return_connection(conn)
        else:
            try:
                conn.close()
            except:
                pass
        
    def get_table_schema(self, table_name):
        """Get table schema from cache or database"""
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        try:
            conn = self.get_optimized_connection()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]
            self._schema_cache[table_name] = column_names
            self.release_connection(conn)
            return column_names
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            return []

    def get_wells_with_data(self):
        """
        Fast wells loading - just get all wells initially, skip data checks.
        """
        cache_key = 'wells_with_data_fast'
        if cache_key in self._data_cache:
            logger.debug("Using cached wells data")
            return self._data_cache[cache_key]
        
        start_time = time.time()
        try:
            conn = self.get_optimized_connection()
            cursor = conn.cursor()
            
            # Get schema once
            column_names = self.get_table_schema('wells')
            
            # Build simple query - just get all wells, no data checks
            select_columns = ["well_number"]
            
            if "cae_number" in column_names:
                select_columns.append("cae_number")
            elif "caesar_number" in column_names:
                select_columns.append("caesar_number as cae_number")
            else:
                select_columns.append("'' as cae_number")
            
            if "aquifer" in column_names:
                select_columns.append("aquifer as water_body")
            elif "water_body" in column_names:
                select_columns.append("water_body")
            else:
                select_columns.append("'' as water_body")
            
            # Simple query - no joins or subqueries
            query = f"""
                SELECT {', '.join(select_columns)}
                FROM wells 
                ORDER BY well_number
            """
            
            logger.debug(f"Executing fast query: {query}")
            
            cursor.execute(query)
            wells = []
            
            for row in cursor.fetchall():
                well_number = row[0] if row[0] else ""
                cae_number = row[1] if len(row) > 1 and row[1] else ""
                water_body = row[2] if len(row) > 2 and row[2] else ""
                wells.append((well_number, cae_number, water_body))
            
            # Cache the result
            self._data_cache[cache_key] = wells
            
            exec_time = time.time() - start_time
            logger.info(f"Fast wells query retrieved {len(wells)} wells in {exec_time*1000:.1f}ms")
            
            self.release_connection(conn)
            return wells
                    
        except Exception as e:
            logger.error(f"Error in fast wells loading: {e}")
            self.release_connection(conn)
            return []

    def get_reading_count(self, well_number):
        """Get reading count for a well - use cached or quick query"""
        cache_key = f'reading_count_{well_number}'
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]
        
        try:
            conn = self.get_optimized_connection()
            cursor = conn.cursor()
            
            # Quick count query
            cursor.execute("SELECT COUNT(*) FROM water_level_readings WHERE well_number = ?", (well_number,))
            count = cursor.fetchone()[0]
            
            # Cache it
            self._data_cache[cache_key] = count
            
            self.release_connection(conn)
            return count
            
        except Exception as e:
            logger.debug(f"Error getting reading count for {well_number}: {e}")
            return 0

    def get_well_data(self, well_number, start_date=None, end_date=None, downsample=None):
        """Fast well data retrieval with optional date filtering and downsampling"""
        import time
        total_start = time.time()
        
        try:
            # Time the connection process
            conn_start = time.time()
            conn = self.get_optimized_connection()
            conn_time = time.time() - conn_start
            logger.info(f"[TIMING] Database connection took {conn_time:.3f} seconds")
            
            cursor = conn.cursor()

            # Time the data source lookup
            source_start = time.time()
            cursor.execute("SELECT data_source FROM wells WHERE well_number = ?", (well_number,))
            result = cursor.fetchone()
            data_source = result[0] if result else 'transducer'
            source_time = time.time() - source_start
            logger.info(f"[TIMING] Data source lookup took {source_time:.3f} seconds")

            # Build query with optional date filtering
            base_query = """
                SELECT timestamp_utc, water_level, temperature
                FROM {table}
                WHERE well_number = ?
            """
            
            params = [well_number]
            
            # Add date filtering if provided
            if start_date:
                base_query += " AND timestamp_utc >= ?"
                params.append(start_date)
            if end_date:
                base_query += " AND timestamp_utc <= ?"
                params.append(end_date)
                
            base_query += " ORDER BY timestamp_utc"
            
            # Query appropriate table  
            query_build_start = time.time()
            if data_source == 'telemetry':
                query = base_query.format(table="telemetry_level_readings")
            else:
                query = base_query.format(table="water_level_readings")
            query_build_time = time.time() - query_build_start
            logger.info(f"[TIMING] Query building took {query_build_time:.3f} seconds")
            
            # Time the actual SQL query execution
            sql_start = time.time()
            df = pd.read_sql_query(query, conn, params=params)
            sql_time = time.time() - sql_start
            logger.info(f"[TIMING] SQL query execution took {sql_time:.3f} seconds ({len(df)} raw rows)")
            
            self.release_connection(conn)
            conn_release_time = time.time() - sql_start - sql_time
            logger.info(f"[TIMING] Connection release took {conn_release_time:.3f} seconds")
            
            # Time the downsampling process
            if downsample and len(df) > 0:
                downsample_start = time.time()
                original_count = len(df)
                # Convert timestamp to datetime if not already
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                df = df.set_index('timestamp_utc')
                
                # Downsample to the specified frequency (e.g., '1D' for daily, '1H' for hourly)
                df = df.resample(downsample).mean()
                df = df.reset_index()
                
                downsample_time = time.time() - downsample_start
                logger.info(f"[TIMING] Downsampling took {downsample_time:.3f} seconds: {original_count} -> {len(df)} points using {downsample}")
            elif downsample:
                logger.info(f"[TIMING] No data to downsample")
            
            total_time = time.time() - total_start
            logger.info(f"[TIMING] Total get_well_data took {total_time:.3f} seconds")
            return df

        except Exception as e:
            logger.error(f"Error fetching well data for {well_number}: {e}")
            return pd.DataFrame()

    # Compatibility methods - delegate to original DataManager for complex operations
    def get_wells(self):
        """Get wells in original format"""
        wells_data = self.get_wells_with_data()
        return [{'well_number': w[0], 'cae_number': w[1], 'aquifer': w[2]} for w in wells_data]
    
    def get_all_wells(self):
        """Get wells with display names"""
        wells_data = self.get_wells_with_data()
        display_names = ["Well Number", "CAE Number", "Aquifer"]
        return wells_data, display_names