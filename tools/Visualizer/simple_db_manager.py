import sqlite3
import logging
import psutil  # Add psutil for memory detection
from pathlib import Path
from sqlite3 import Connection
import queue
import time
import os
import threading
import functools

logger = logging.getLogger(__name__)

class SimpleDatabaseManager:
    """A simplified database manager for the visualizer application."""
    
    def __init__(self, db_path, quick_validation=False, deferred_init=False):
        self.current_db = db_path
        # Create connection pool with smaller size for better resource usage
        self._connection_pool = queue.Queue(maxsize=3)  # Reduced pool size
        self._schema_cache = {}  # Cache for schema information
        self._query_cache = {}   # Cache for frequently accessed query results
        self._cache_lock = threading.RLock()  # Lock for thread-safe cache access
        
        # Debug database
        logger.info(f"Database path: {db_path}")
        db_exists = Path(db_path).exists()
        logger.info(f"Database exists: {db_exists}")
        
        # Skip size check to improve startup time
        if not db_exists:
            raise ValueError(f"Database file does not exist: {db_path}")
            
        # For deferred init, just prepare without full loading
        if deferred_init:
            self.conn = None
            logger.info("Using deferred initialization - database will be loaded when needed")
            return
            
        # Create initial connection with immediate PRAGMA optimizations
        self.conn = self._create_connection(minimal=True)
        
        # Apply minimal validation - just verify one table exists
        try:
            # Just check that at least one table exists
            self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
            logger.info("Quick database validation passed")
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            raise ValueError(f"Invalid or corrupt database: {e}")
    
    def _cache_table_schema(self, table_name):
        """Cache table schema information to avoid repeated queries"""
        try:
            if not self.conn:
                # Lazily initialize connection if needed
                self.conn = self._create_connection()
                
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]
            self._schema_cache[table_name] = column_names
            logger.debug(f"Cached schema for table {table_name}: {column_names}")
        except Exception as e:
            logger.error(f"Error caching schema for {table_name}: {e}")
    
    def get_table_schema(self, table_name):
        """Get table schema from cache or database"""
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        # Not in cache, fetch and store
        self._cache_table_schema(table_name)
        return self._schema_cache.get(table_name, [])

    def configure_connection(self, conn, minimal=False):
        """
        Configure SQLite connection with optimized PRAGMA settings based on available system memory.
        
        Args:
            conn: SQLite connection to configure
            minimal: If True, apply only critical settings for faster initial loading
        """
        # Get system memory (in GB)
        available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        # Read-only optimization settings - these are safe for all scenarios
        conn.execute('PRAGMA journal_mode = OFF')  # Disable journaling completely for read-only
        conn.execute('PRAGMA synchronous = OFF')   # No need for durability in read-only mode
        conn.execute('PRAGMA locking_mode = NORMAL')  # No need for exclusive lock in read-only
        conn.execute('PRAGMA query_only = TRUE')   # Enforce read-only at SQLite level
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA foreign_keys = OFF')
        
        # Disable integrity checks for read-only operation
        conn.execute('PRAGMA ignore_check_constraints = TRUE')
        conn.execute('PRAGMA cell_size_check = FALSE')
        
        # Skip additional settings for minimal initialization
        if minimal:
            return
            
        # Full configuration settings for read-only mode
        conn.execute('PRAGMA page_size = 8192')
        conn.execute('PRAGMA count_changes = OFF')
        conn.execute('PRAGMA cache_spill = FALSE')  # Prevent cache spilling to disk
        
        # Disable auto checkpointing for WAL (not needed for read-only)
        conn.execute('PRAGMA wal_autocheckpoint = 0')
        
        # Adapt settings to available memory - be more aggressive for read-only
        if available_memory_gb > 16:
            # High-performance settings for well-equipped machines
            conn.execute('PRAGMA cache_size = -409600')       # 400MB cache for read-only
            conn.execute('PRAGMA mmap_size = 17179869184')    # 16GB mmap for read-only
            logger.debug(f"Using high-performance read-only SQLite settings (mem: {available_memory_gb:.1f}GB)")
        elif available_memory_gb > 8:
            # Medium settings
            conn.execute('PRAGMA cache_size = -204800')       # 200MB cache
            conn.execute('PRAGMA mmap_size = 8589934592')     # 8GB mmap
            logger.debug(f"Using medium read-only SQLite settings (mem: {available_memory_gb:.1f}GB)")
        else:
            # Conservative settings for limited resources
            conn.execute('PRAGMA cache_size = -51200')        # 50MB cache for read-only
            conn.execute('PRAGMA mmap_size = 2147483648')     # 2GB mmap for read-only
            logger.debug(f"Using conservative read-only SQLite settings (mem: {available_memory_gb:.1f}GB)")
    
    def _create_connection(self, minimal=False) -> Connection:
        """Create a new database connection with optimized settings"""
        # For read-only databases, use most aggressive optimizations
        try:
            # Enhanced URI mode with all possible read-only optimization flags
            uri = f"file:{self.current_db}?mode=ro&immutable=1&nolock=1&cache=shared"
            conn = sqlite3.connect(uri, uri=True, timeout=5)
            logger.debug("Connected to database using fully optimized read-only URI mode")
        except sqlite3.OperationalError:
            # Fallback to standard connection
            conn = sqlite3.connect(self.current_db, timeout=5)
            logger.debug("Connected to database using standard connection")
            
        # Apply only critical settings for minimal initialization
        if minimal:
            # Only apply essential performance settings
            conn.execute('PRAGMA journal_mode = OFF')  
            conn.execute('PRAGMA synchronous = OFF')   
            conn.execute('PRAGMA query_only = TRUE')   
            conn.execute('PRAGMA temp_store = MEMORY')
            return conn
        
        # Apply full optimization settings
        self.configure_connection(conn, minimal)
        return conn

    def cache_query(self, max_age_seconds=3600):
        """
        Decorator for caching query results.
        
        Args:
            max_age_seconds: Maximum age in seconds to keep cache entries
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Create a cache key from function name and arguments
                key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                with self._cache_lock:
                    # Check if we have a cached result
                    if key in self._query_cache:
                        cache_time, result = self._query_cache[key]
                        age = time.time() - cache_time
                        
                        # Return cached result if still valid
                        if age < max_age_seconds:
                            logger.debug(f"Cache hit for query: {key[:100]}...")
                            return result
                
                # Execute the function to get fresh result
                result = func(*args, **kwargs)
                
                # Cache the result
                with self._cache_lock:
                    self._query_cache[key] = (time.time(), result)
                    
                    # Log cache size periodically
                    if len(self._query_cache) % 10 == 0:
                        logger.debug(f"Query cache contains {len(self._query_cache)} entries")
                
                return result
            return wrapper
        return decorator
                
    def execute_query(self, query, params=(), fetch_all=True, cache=False, cache_time=3600):
        """
        Execute a query with optional result caching for read-only queries.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_all: Whether to fetch all results
            cache: Whether to cache the results
            cache_time: How long to cache results in seconds
            
        Returns:
            Query results
        """
        # For quick caching of simple queries
        if cache:
            cache_key = f"query:{query}:{str(params)}"
            
            with self._cache_lock:
                if cache_key in self._query_cache:
                    cache_time_saved, result = self._query_cache[cache_key]
                    age = time.time() - cache_time_saved
                    
                    if age < cache_time:
                        logger.debug(f"Cache hit for direct query")
                        return result
        
        # Get a connection from the pool
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            start_time = time.time()
            
            # Execute the query
            cursor.execute(query, params)
            
            # Fetch results
            if fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()
                
            # Log query execution time
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"Query executed in {elapsed:.2f}ms: {query[:100]}...")
            
            # Cache the result if requested
            if cache:
                with self._cache_lock:
                    self._query_cache[cache_key] = (time.time(), result)
            
            return result
            
        finally:
            # Return the connection to the pool
            self.return_connection(conn)

    def get_connection(self) -> Connection:
        """Get a connection from the pool, or create one if needed."""
        try:
            # First check if we have any in the pool
            if not self._connection_pool.empty():
                conn = self._connection_pool.get(block=False)
                return conn
            
            # Create main connection if we're using deferred init and haven't created it yet
            if not self.conn:
                logger.info("Creating initial database connection (deferred initialization)")
                self.conn = self._create_connection()
            
            # None in pool, create new connection
            conn = self._create_connection()
            return conn
            
        except Exception as e:
            logger.error(f"Error getting database connection: {e}")
            # Fallback to the main connection if pool fails
            if not self.conn:
                self.conn = self._create_connection()
            return self.conn
    
    def return_connection(self, conn: Connection):
        """Return a connection to the pool"""
        try:
            if conn and conn != self.conn:  # Don't put the main connection in the pool
                try:
                    self._connection_pool.put_nowait(conn)
                    logger.debug("Returned connection to pool")
                except queue.Full:
                    logger.debug("Connection pool full, closing excess connection")
                    conn.close()
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            try:
                if conn and conn != self.conn:
                    conn.close()
            except:
                pass
    
    def close(self):
        """Close all database connections"""
        logger.debug("Closing all database connections")
        start_time = time.time()
        
        # Close connections in the pool
        connections_closed = 0
        while True:
            try:
                conn = self._connection_pool.get_nowait()
                if conn:
                    connections_closed += 1
                    conn.close()
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error closing connection from pool: {e}")
        
        # Close the main connection
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
        except Exception as e:
            logger.error(f"Error closing main connection: {e}")
        
        # Clear caches
        with self._cache_lock:
            cache_size = len(self._query_cache)
            self._query_cache.clear()
            self._schema_cache.clear()
            logger.debug(f"Cleared {cache_size} query cache entries")
        
        end_time = time.time()
        logger.debug(f"Database connection cleanup completed in {(end_time-start_time)*1000:.2f}ms")

    def preload_common_data(self):
        """
        Preload frequently accessed data into memory cache for faster access.
        Call this method after initialization if you want to front-load database access.
        """
        logger.info("Preloading common data into memory cache...")
        start_time = time.time()
        
        try:
            # Preload only essential wells data (not all columns) to reduce memory usage
            wells_data = self.execute_query(
                "SELECT well_number, well_name, latitude, longitude FROM wells", 
                cache=True, 
                cache_time=3600
            )
            logger.info(f"Preloaded {len(wells_data)} wells into cache")
            
            # Get well IDs for selective loading
            well_ids = [row[0] for row in wells_data] if wells_data else []
            
            # If there are too many wells, just load a subset for the most common ones
            if len(well_ids) > 25:
                logger.info(f"Limiting preload to first 25 wells out of {len(well_ids)}")
                well_ids = well_ids[:25]
            
            if well_ids:
                # Use a SINGLE query with IN clause instead of multiple individual queries
                # This dramatically reduces the number of database calls
                placeholders = ','.join(['?'] * len(well_ids))
                recent_readings_query = f"""
                    SELECT well_number, MAX(timestamp_utc), depth_to_water_ft
                    FROM water_level_readings 
                    WHERE well_number IN ({placeholders})
                    GROUP BY well_number
                """
                self.execute_query(recent_readings_query, well_ids, cache=True, cache_time=3600)
                logger.info(f"Preloaded most recent readings for {len(well_ids)} wells with a single query")
            
            # Preload table counts - essential for UI display
            for table in ['wells', 'water_level_readings']:
                try:
                    self.execute_query(f"SELECT COUNT(*) FROM {table}", cache=True, cache_time=3600)
                except Exception as e:
                    logger.debug(f"Could not preload count for table {table}: {e}")
                    
            # Preload essential table schemas only
            for table in ['wells', 'water_level_readings']:
                self.get_table_schema(table)
                
            end_time = time.time()
            logger.info(f"Preloaded common data in {(end_time - start_time)*1000:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error during data preloading: {e}")
