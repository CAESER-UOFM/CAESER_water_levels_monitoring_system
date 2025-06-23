"""
Central data store for managing shared data between visualizer components.
Prevents redundant database queries and provides a single source of truth.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from PyQt5.QtCore import QObject, pyqtSignal
import pandas as pd
import threading
from functools import lru_cache
import time

logger = logging.getLogger(__name__)


class CentralDataStore(QObject):
    """
    Central data store that manages data loading and distribution to all visualizer components.
    Uses Qt signals to notify components when data is updated.
    """
    
    # Signals for data updates
    well_data_updated = pyqtSignal(str, pd.DataFrame)  # well_id, data
    wells_list_updated = pyqtSignal(list)  # list of wells
    loading_started = pyqtSignal(str)  # loading message
    loading_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self._cache = {}  # Cache for loaded data
        self._cache_timestamps = {}  # Track when data was cached
        self._cache_ttl = 300  # Cache time-to-live in seconds (5 minutes)
        self._loading_locks = {}  # Prevent duplicate concurrent loads
        self._wells_cache = None
        self._wells_cache_time = None
        
    def get_wells_list(self) -> List[Tuple[str, str, str]]:
        """Get the list of wells, using cache if available."""
        # Check cache validity
        if (self._wells_cache is not None and 
            self._wells_cache_time is not None and
            time.time() - self._wells_cache_time < self._cache_ttl):
            return self._wells_cache
            
        # Load from database
        try:
            self.loading_started.emit("Loading wells list...")
            wells = self.data_manager.get_wells_with_data()
            self._wells_cache = wells
            self._wells_cache_time = time.time()
            self.wells_list_updated.emit(wells)
            return wells
        except Exception as e:
            logger.error(f"Error loading wells list: {e}")
            self.error_occurred.emit(f"Failed to load wells: {str(e)}")
            return []
        finally:
            self.loading_finished.emit()
    
    def get_well_data(self, well_id: str, force_reload: bool = False, 
                     date_range: Optional[Dict[str, Any]] = None,
                     downsample: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Get well data with caching and deduplication.
        
        Args:
            well_id: Well identifier
            force_reload: Force reload from database
            date_range: Optional date range filter {'start': date, 'end': date}
            downsample: Optional downsampling frequency (e.g., '1D', '1H')
            
        Returns:
            DataFrame with well data or None if error
        """
        # Create cache key including parameters
        cache_key = f"{well_id}_{date_range}_{downsample}"
        
        # Check cache validity
        if not force_reload and cache_key in self._cache:
            cache_time = self._cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self._cache_ttl:
                logger.debug(f"Returning cached data for {well_id}")
                return self._cache[cache_key].copy()
        
        # Prevent duplicate concurrent loads
        lock_key = cache_key
        if lock_key not in self._loading_locks:
            self._loading_locks[lock_key] = threading.Lock()
            
        # Check if another thread is already loading this data
        if not self._loading_locks[lock_key].acquire(blocking=False):
            logger.debug(f"Another thread is loading {well_id}, waiting...")
            self._loading_locks[lock_key].acquire()
            self._loading_locks[lock_key].release()
            
            # Check if data was loaded by the other thread
            if cache_key in self._cache:
                return self._cache[cache_key].copy()
        
        try:
            # Load data from database
            self.loading_started.emit(f"Loading data for {well_id}...")
            
            # Extract date range if provided
            start_date = None
            end_date = None
            if date_range:
                if 'start' in date_range:
                    start_date = date_range['start']
                if 'end' in date_range:
                    end_date = date_range['end']
            
            # Use optimized data loading
            df = self.data_manager.get_well_data(
                well_id,
                start_date=start_date,
                end_date=end_date,
                downsample=downsample
            )
            
            if df is not None and not df.empty:
                # Cache the data
                self._cache[cache_key] = df.copy()
                self._cache_timestamps[cache_key] = time.time()
                
                # Emit signal for interested components
                self.well_data_updated.emit(well_id, df.copy())
                
                logger.info(f"Loaded {len(df)} points for {well_id}")
                return df.copy()
            else:
                logger.warning(f"No data found for {well_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading data for {well_id}: {e}")
            self.error_occurred.emit(f"Failed to load {well_id}: {str(e)}")
            return None
        finally:
            self._loading_locks[lock_key].release()
            self.loading_finished.emit()
    
    def clear_cache(self, well_id: Optional[str] = None):
        """Clear cache for specific well or all wells."""
        if well_id:
            # Clear specific well data
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(well_id)]
            for key in keys_to_remove:
                del self._cache[key]
                self._cache_timestamps.pop(key, None)
            logger.debug(f"Cleared cache for {well_id}")
        else:
            # Clear all cache
            self._cache.clear()
            self._cache_timestamps.clear()
            self._wells_cache = None
            self._wells_cache_time = None
            logger.debug("Cleared all cache")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache state."""
        return {
            'cached_wells': len(self._cache),
            'cache_size_mb': sum(df.memory_usage(deep=True).sum() 
                               for df in self._cache.values()) / 1024 / 1024,
            'oldest_cache_age': min((time.time() - t for t in self._cache_timestamps.values()), 
                                   default=0) if self._cache_timestamps else 0
        }