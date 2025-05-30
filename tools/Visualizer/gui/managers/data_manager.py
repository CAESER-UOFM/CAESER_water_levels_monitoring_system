import sqlite3
import pandas as pd
import logging
import psutil  # Add psutil for memory detection
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class DataManager:
    """Handles database interactions for fetching well data and metadata."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._db_manager = None
        self._schema_cache = {}
        self._data_cache = {}  # Cache for frequently accessed data
        self._initialize_db_manager()
    
    def _initialize_db_manager(self):
        """Initialize the database manager if not already done"""
        try:
            from simple_db_manager import SimpleDatabaseManager
            # Check if we're dealing with a large database
            db_size_mb = Path(self.db_path).stat().st_size / (1024 * 1024)
            quick_validation = db_size_mb > 100
            self._db_manager = SimpleDatabaseManager(self.db_path, quick_validation=quick_validation)
            logger.info(f"Initialized SimpleDatabaseManager for {self.db_path} (size: {db_size_mb:.2f} MB)")
        except Exception as e:
            logger.error(f"Failed to initialize SimpleDatabaseManager: {e}")
            self._db_manager = None

    def get_optimized_connection(self):
        """Create and return a connection with optimized PRAGMA settings."""
        # Try to use DB manager's connection pool if available
        if self._db_manager:
            return self._db_manager.get_connection()
        
        # Fallback to direct connection
        conn = sqlite3.connect(self.db_path)
        self.configure_connection(conn)
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
        
    def configure_connection(self, conn):
        """
        Configure SQLite connection with optimized PRAGMA settings based on available system memory.
        
        Args:
            conn: SQLite connection to configure
        """
        # Get system memory (in GB)
        available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        # Basic settings that work everywhere
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = OFF')
        
        # Adapt settings to available memory
        if available_memory_gb > 16:
            # High-performance settings for well-equipped machines
            conn.execute('PRAGMA cache_size = -204800')       # 200MB cache
            conn.execute('PRAGMA mmap_size = 8589934592')     # 8GB mmap
            logger.debug(f"Using high-performance SQLite settings (mem: {available_memory_gb:.1f}GB)")
        elif available_memory_gb > 8:
            # Medium settings
            conn.execute('PRAGMA cache_size = -102400')       # 100MB cache
            conn.execute('PRAGMA mmap_size = 4294967296')     # 4GB mmap
            logger.debug(f"Using medium SQLite settings (mem: {available_memory_gb:.1f}GB)")
        else:
            # Conservative settings for limited resources
            conn.execute('PRAGMA cache_size = -10240')        # 10MB cache
            conn.execute('PRAGMA mmap_size = 1073741824')     # 1GB mmap
            logger.debug(f"Using conservative SQLite settings (mem: {available_memory_gb:.1f}GB)")
        
        # Common settings for all configurations
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA page_size = 8192')

    def get_table_schema(self, table_name):
        """Get cached schema for the specified table"""
        # Try to use the db_manager's schema cache if available
        if self._db_manager and hasattr(self._db_manager, 'get_table_schema'):
            return self._db_manager.get_table_schema(table_name)
        
        # Use internal cache if available
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        # Not in cache, fetch from database
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

    def get_wells(self):
        """
        Fetch all wells from the database, returning a list of dictionaries.
        
        Returns:
            list: A list of dictionaries containing well information.
        """
        # Check cache first
        cache_key = 'all_wells'
        if cache_key in self._data_cache:
            logger.debug("Using cached well data")
            return self._data_cache[cache_key]
        
        start_time = time.time()
        try:
            conn = self.get_optimized_connection()
            
            # Get schema but try to use cached schema first
            column_names = self.get_table_schema('wells')
            
            # Build query dynamically based on what columns exist
            select_columns = ["well_number"]
            
            if "aquifer" in column_names:
                select_columns.append("aquifer")
            
            # Check for cae_number field - try both possible field names
            if "cae_number" in column_names:
                select_columns.append("cae_number")
            elif "caesar_number" in column_names:
                select_columns.append("caesar_number as cae_number")
            
            # Add the readings count as a subquery, but only if needed
            readings_count = "(SELECT COUNT(*) FROM water_level_readings WHERE well_number = wells.well_number) as readings"
            
            query = f"""
                SELECT {', '.join(select_columns)}, {readings_count}
                FROM wells
                ORDER BY well_number
            """
            
            logger.debug(f"Executing query: {query}")
            
            try:
                df = pd.read_sql_query(query, conn)
                
                # Add missing columns with default values
                if "aquifer" not in df.columns:
                    df['aquifer'] = 'Unknown'
                
                # Add cae_number with default value if it doesn't exist
                if "cae_number" not in df.columns:
                    df['cae_number'] = ''
                
                # Always add status with default value since it doesn't exist in the table
                df['status'] = 'Active'
                
                # Convert DataFrame to list of dictionaries
                wells = df.to_dict(orient='records')
                
                # Cache the result
                self._data_cache[cache_key] = wells
                
                exec_time = time.time() - start_time
                logger.info(f"Retrieved {len(wells)} wells from database in {exec_time*1000:.1f}ms")
                
                self.release_connection(conn)
                return wells
                
            except sqlite3.OperationalError as e:
                logger.error(f"SQL error while executing dynamic query: {e}")
                # If all else fails, use the most basic query
                fallback_query = "SELECT well_number FROM wells ORDER BY well_number"
                df = pd.read_sql_query(fallback_query, conn)
                
                # Add all missing columns
                df['aquifer'] = 'Unknown'
                df['cae_number'] = ''
                df['status'] = 'Active'
                df['readings'] = 0
                
                wells = df.to_dict(orient='records')
                self._data_cache[cache_key] = wells
                
                logger.warning(f"Used fallback query to retrieve {len(df)} wells")
                self.release_connection(conn)
                return wells
                
        except Exception as e:
            logger.error(f"Error fetching wells: {e}")
            return []

    def get_all_wells(self):
        """
        Fetch all available wells and their metadata from the database.

        Returns:
            tuple: A list of well data rows and a list of column display names.
        """
        # Check cache first
        cache_key = 'all_wells_with_display'
        if cache_key in self._data_cache:
            logger.debug("Using cached well metadata")
            return self._data_cache[cache_key]
            
        try:
            conn = self.get_optimized_connection()
            cursor = conn.cursor()

            # Get cached schema if available
            column_names = self.get_table_schema('wells')

            # Define default and optional columns
            available_columns = ["well_number"]  # Always include well_number
            display_names = ["Well Number"]

            column_mappings = {
                "caesar_number": "CAESER Number",
                "wellfield": "Wellfield",
                "aquifer": "Aquifer",
                "toc": "TOC",
            }

            # Add optional columns if they exist in the database
            for db_col, display_name in column_mappings.items():
                if db_col in column_names:
                    available_columns.append(db_col)
                    display_names.append(display_name)

            # Query the wells table for the available columns
            query = f"SELECT {', '.join(available_columns)} FROM wells ORDER BY well_number"
            cursor.execute(query)
            wells = cursor.fetchall()

            # Cache the result
            result = (wells, display_names)
            self._data_cache[cache_key] = result
            
            self.release_connection(conn)
            return result

        except Exception as e:
            logger.error(f"Error fetching wells: {e}")
            return [], []

    def get_well_data(self, well_number):
        """
        Fetch time series data for a specific well.

        Args:
            well_number (str): The well number to fetch data for.

        Returns:
            pd.DataFrame: A DataFrame containing the well's time series data.
        """
        # Check cache for well data source
        source_cache_key = f'data_source_{well_number}'
        data_source = None
        if source_cache_key in self._data_cache:
            data_source = self._data_cache[source_cache_key]
            
        try:
            conn = self.get_optimized_connection()
            cursor = conn.cursor()

            # Determine the data source for the well if not cached
            if not data_source:
                cursor.execute("SELECT data_source FROM wells WHERE well_number = ?", (well_number,))
                result = cursor.fetchone()
                data_source = result[0] if result else 'transducer'
                # Cache the data source for future use
                self._data_cache[source_cache_key] = data_source

            # Query the appropriate table based on the data source
            if data_source == 'telemetry':
                query = """
                    SELECT timestamp_utc, water_level, temperature
                    FROM telemetry_level_readings
                    WHERE well_number = ?
                    ORDER BY timestamp_utc
                """
            else:
                query = """
                    SELECT timestamp_utc, water_level, temperature
                    FROM water_level_readings
                    WHERE well_number = ?
                    ORDER BY timestamp_utc
                """

            # Use optimized batch loading instead of all at once
            try:
                # First check how many records we'll need to load
                count_query = f"""
                    SELECT COUNT(*) FROM {data_source == 'telemetry' and 'telemetry_level_readings' or 'water_level_readings'}
                    WHERE well_number = ?
                """
                cursor.execute(count_query, (well_number,))
                record_count = cursor.fetchone()[0]
                
                if record_count > 100000:
                    logger.info(f"Loading large dataset ({record_count} records) for well {well_number} in batches")
                    # Use chunked reading for very large datasets
                    df = pd.read_sql_query(query, conn, params=(well_number,), chunksize=50000)
                    # Combine all chunks
                    df = pd.concat(list(df))
                else:
                    # Standard loading for smaller datasets
                    df = pd.read_sql_query(query, conn, params=(well_number,))
            except Exception as e:
                logger.error(f"Error executing optimized query: {e}")
                # Fallback to standard query
                df = pd.read_sql_query(query, conn, params=(well_number,))
                
            if not df.empty:
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

            self.release_connection(conn)
            return df

        except Exception as e:
            logger.error(f"Error fetching data for well {well_number}: {e}")
            return pd.DataFrame()

    def get_well_locations(self):
        """
        Fetch the locations of all wells.

        Returns:
            list: A list of dictionaries containing well location data.
        """
        try:
            with self.get_optimized_connection() as conn:
                query = """
                    SELECT well_number, latitude, longitude
                    FROM wells
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                """
                df = pd.read_sql_query(query, conn)
                return df.to_dict(orient='records')

        except Exception as e:
            logger.error(f"Error fetching well locations: {e}")
            return []

    def get_manual_readings(self, well_number):
        """
        Fetch manual readings for a specific well.

        Args:
            well_number (str): The well number to fetch data for.

        Returns:
            pd.DataFrame: A DataFrame containing the well's manual readings.
        """
        try:
            with self.get_optimized_connection() as conn:
                # Determine the table name for manual readings - might be different in your DB
                query = """
                    SELECT measurement_date_utc, water_level
                    FROM manual_level_readings  -- Check if this is the correct table name
                    WHERE well_number = ?
                    ORDER BY measurement_date_utc
                """
                
                df = pd.read_sql_query(query, conn, params=(well_number,))
                if not df.empty:
                    df['measurement_date_utc'] = pd.to_datetime(df['measurement_date_utc'])
                
                logger.info(f"Found {len(df)} manual readings for well {well_number}")
                return df

        except Exception as e:
            logger.error(f"Error fetching manual readings for well {well_number}: {e}")
            return pd.DataFrame()

    def filter_data_by_date_range(self, df, start_date, end_date):
        """
        Filter DataFrame by date range.
        
        Args:
            df (pd.DataFrame): DataFrame to filter
            start_date (str): Start date in format 'YYYY-MM-DD'
            end_date (str): End date in format 'YYYY-MM-DD'
            
        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        try:
            if df.empty:
                return df
                
            # Convert strings to datetime objects if needed
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
                
            # Determine the date column (might be timestamp_utc or measurement_date_utc)
            date_column = None
            if 'timestamp_utc' in df.columns:
                date_column = 'timestamp_utc'
            elif 'measurement_date_utc' in df.columns:
                date_column = 'measurement_date_utc'
            elif df.index.name in ['timestamp_utc', 'measurement_date_utc']:
                # Handle case where date is the index
                date_column = df.index
            else:
                logger.warning("No timestamp column found in DataFrame, unable to filter by date")
                return df
                
            # Filter the DataFrame
            if isinstance(date_column, pd.DatetimeIndex):
                filtered_df = df[(df.index >= start_date) & (df.index <= end_date)]
            else:
                filtered_df = df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]
                
            logger.info(f"Filtered data from {len(df)} to {len(filtered_df)} records")
            return filtered_df
            
        except Exception as e:
            logger.error(f"Error filtering data by date range: {e}")
            return df  # Return original DataFrame in case of error

    def get_wells_with_data(self):
        """
        Fetch wells that actually have water level data, returning a list of tuples.
        
        Returns:
            list: A list of tuples containing (well_number, cae_number, water_body).
        """
        try:
            with self.get_optimized_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # First, check what columns actually exist in the wells table
                cursor.execute("PRAGMA table_info(wells)")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]
                
                # Build query dynamically based on what columns exist
                select_columns = ["w.well_number"]
                
                # Check for different column names for the CAE number
                if "cae_number" in column_names:
                    select_columns.append("w.cae_number")
                elif "caesar_number" in column_names:
                    select_columns.append("w.caesar_number as cae_number")
                else:
                    select_columns.append("NULL as cae_number")
                
                # Check for different column names for the water body
                if "aquifer" in column_names:
                    select_columns.append("w.aquifer as water_body")
                elif "water_body" in column_names:
                    select_columns.append("w.water_body")
                else:
                    select_columns.append("NULL as water_body")
                
                # Build query to only select wells with data
                query = f"""
                    SELECT {', '.join(select_columns)}
                    FROM wells w
                    INNER JOIN (
                        SELECT DISTINCT well_number 
                        FROM water_level_readings
                    ) r ON w.well_number = r.well_number
                    ORDER BY w.well_number
                """
                
                logger.info(f"Executing query: {query}")
                
                try:
                    cursor.execute(query)
                    wells = []
                    
                    for row in cursor.fetchall():
                        well_number = row['well_number']
                        cae_number = row['cae_number'] if 'cae_number' in row.keys() else ""
                        water_body = row['water_body'] if 'water_body' in row.keys() else ""
                        
                        # Skip null values
                        cae_number = cae_number if cae_number else ""
                        water_body = water_body if water_body else ""
                        
                        wells.append((well_number, cae_number, water_body))
                    
                    logger.info(f"Retrieved {len(wells)} wells with data from database")
                    return wells
                    
                except sqlite3.OperationalError as e:
                    logger.error(f"SQL error while executing dynamic query: {e}")
                    # If all else fails, use the most basic query
                    fallback_query = """
                        SELECT DISTINCT w.well_number, '' as cae_number, '' as water_body
                        FROM wells w
                        INNER JOIN water_level_readings r ON w.well_number = r.well_number
                        ORDER BY w.well_number
                    """
                    cursor.execute(fallback_query)
                    wells = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
                    
                    logger.warning(f"Used fallback query to retrieve {len(wells)} wells")
                    return wells
                
        except Exception as e:
            logger.error(f"Error fetching wells with data: {e}", exc_info=True)
            return []

    def get_reading_count(self, well_number):
        """
        Get the count of readings for a specific well.
        
        Args:
            well_number (str): The well number to count readings for
            
        Returns:
            int: The number of readings for the well
        """
        try:
            with self.get_optimized_connection() as conn:
                cursor = conn.cursor()
                
                # Count readings in the water_level_readings table
                cursor.execute(
                    "SELECT COUNT(*) FROM water_level_readings WHERE well_number = ?", 
                    (well_number,)
                )
                count = cursor.fetchone()[0]
                
                return count
                
        except Exception as e:
            logger.error(f"Error getting reading count for well {well_number}: {e}")
            return 0
