import logging
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from .solinst_reader import SolinstReader
import numpy as np

logger = logging.getLogger(__name__)

class WaterLevelProcessor:
    """Core processor for water level data handling both single files and folders"""
    
    def __init__(self, water_level_model):
        self.water_level_model = water_level_model
        self.solinst_reader = SolinstReader()
        self.STANDARD_ATMOS_PRESSURE = 14.7
        
    def validate_transducer(self, well_number: str, serial_number: str) -> Tuple[bool, str, dict]:
        """Validate transducer assignment with detailed status and relocation handling"""
        try:
            logger.debug(f"Validating transducer {serial_number} for well {well_number}")
            
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if transducer exists
                cursor.execute("""
                    SELECT t.serial_number, t.well_number, t.installation_date,
                           w.well_number, w.cae_number
                    FROM transducers t
                    LEFT JOIN wells w ON t.well_number = w.well_number
                    WHERE t.serial_number = ? 
                    AND t.end_date IS NULL
                """, (serial_number,))
                
                result = cursor.fetchone()
                
                if not result:
                    logger.debug(f"Transducer {serial_number} needs registration")
                    return False, "needs_registration", {
                        'needs_registration': True,
                        'serial_number': serial_number,
                        'status': 'unregistered'
                    }
                
                current_serial, current_well, install_date, well_exists, cae_number = result
                
                # Case 1: Transducer is in the correct well
                if current_well == well_number:
                    logger.debug(f"Transducer {serial_number} is already in well {well_number}")
                    return True, "valid", {'serial_number': serial_number}
                    
                # Case 2: Well doesn't exist in database
                if not well_exists:
                    logger.debug(f"Well {current_well} for transducer {serial_number} doesn't exist")
                    return False, "invalid_well", {
                        'serial_number': serial_number,
                        'current_well': current_well,
                        'needs_well_registration': True,
                        'suggested_action': 'register_well'
                    }
                    
                # Case 3: Transducer needs relocation
                logger.debug(f"Transducer {serial_number} needs relocation from {current_well} to {well_number}")
                return False, "needs_relocation", {
                    'serial_number': serial_number,
                    'current_well': current_well,
                    'current_cae': cae_number,
                    'installation_date': install_date,
                    'new_well': well_number,
                    'needs_reassignment': True,
                    'suggested_action': 'relocate_transducer'
                }
                
        except Exception as e:
            logger.error(f"Error validating transducer: {e}", exc_info=True)
            return False, f"error: {str(e)}", None
        
    def relocate_transducer(self, serial_number: str, new_well: str, 
                            relocation_date: datetime, notes: str = "") -> Tuple[bool, str, Optional[Dict]]:
        """Handle transducer relocation with proper history tracking"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                
                # First, get the current well_number before making any changes
                logger.debug(f"Fetching current well number for serial: {serial_number}")
                cursor.execute("""
                    SELECT well_number FROM transducers 
                    WHERE serial_number = ?
                """, (serial_number,))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"Transducer {serial_number} not found")
                    return False, f"Transducer {serial_number} not found", None
                    
                current_well_number = result[0]
                logger.debug(f"Current well number: {current_well_number}")
                
                # Format relocation_date as string if it's a datetime object
                if isinstance(relocation_date, datetime):
                    relocation_date_str = relocation_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    relocation_date_str = str(relocation_date)
                
                # Now archive the current record using the directly retrieved well_number
                logger.debug(f"Updating end_date for current location: {current_well_number}")
                cursor.execute("""
                    UPDATE transducer_locations
                    SET end_date = ?
                    WHERE serial_number = ? 
                    AND well_number = ?
                    AND end_date IS NULL
                """, (relocation_date_str, serial_number, current_well_number))
                
                updated_rows = cursor.rowcount
                logger.debug(f"Updated {updated_rows} rows in transducer_locations")
                
                # Then, add a new record to transducer_locations for the new location
                logger.debug(f"Adding new location record for well: {new_well}")
                cursor.execute("""
                    INSERT INTO transducer_locations 
                    (serial_number, well_number, start_date, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    serial_number,
                    new_well,
                    relocation_date_str,
                    notes
                ))
                
                # Finally, update the transducer record
                logger.debug(f"Updating main transducer record to well: {new_well}")
                cursor.execute("""
                    UPDATE transducers 
                    SET well_number = ?,
                        installation_date = ?,
                        notes = ?
                    WHERE serial_number = ?
                """, (
                    new_well,
                    relocation_date_str,
                    notes,
                    serial_number
                ))
                
                conn.commit()
                logger.debug("Changes committed successfully")
                return True, "Transducer relocated successfully", {
                    'serial_number': serial_number,
                    'well_number': new_well,
                    'relocation_date': relocation_date
                }
                
        except Exception as e:
            logger.error(f"Error relocating transducer: {e}", exc_info=True)
            return False, str(e), None

    def get_well_info(self, well_number: str) -> Optional[Dict]:
        """Get well information"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT well_number, top_of_casing, cae_number
                    FROM wells
                    WHERE well_number = ?
                """, (well_number,))
                result = cursor.fetchone()
                if result:
                    return {
                        'well_number': result[0],
                        'top_of_casing': result[1],
                        'cae_number': result[2]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting well info: {e}")
            return None
            
    def determine_insertion_level(self, df: pd.DataFrame, well_info: Dict, 
                                manual_readings: pd.DataFrame = None,
                                existing_data: pd.DataFrame = None,
                                is_folder_import: bool = False,
                                progress_dialog = None) -> Dict:
        """Determine the height difference (dh) to apply to water pressure readings.
        
        Returns:
            Dict containing:
                - dh: float, the height difference to apply
                - method: str, how the dh was determined ('manual_readings', 'predicted', or 'default_level')
                - method_details: str, description of the calculation
        """
        try:
            # Get first and last timestamp of new data segment
            new_start = pd.to_datetime(df['timestamp_utc'].iloc[0])
            new_end = pd.to_datetime(df['timestamp_utc'].iloc[-1])
            logger.debug(f"Determining dh for data segment from {new_start} to {new_end}")
            
            # Case 1: Check manual readings within the data range (±1 hour)
            if manual_readings is not None and not manual_readings.empty:
                # Define the time range: ±1 hour from the imported data
                window_start = new_start - timedelta(hours=1)
                window_end = new_end + timedelta(hours=1)
                
                valid_readings = manual_readings[
                    (manual_readings['measurement_date_utc'] >= window_start) &
                    (manual_readings['measurement_date_utc'] <= window_end)
                ]
                
                if not valid_readings.empty:
                    logger.debug(f"Found {len(valid_readings)} manual readings in time window")
                    
                    # First, check for readings within the segment itself
                    segment_readings = valid_readings[
                        (valid_readings['measurement_date_utc'] >= new_start) &
                        (valid_readings['measurement_date_utc'] <= new_end)
                    ]
                    
                    selected_reading = None
                    selected_time = None
                    selected_level = None
                    
                    if not segment_readings.empty:
                        # Prioritize readings within the segment, closest to the end
                        time_to_end = abs(segment_readings['measurement_date_utc'] - new_end)
                        closest_idx = time_to_end.idxmin()
                        selected_reading = segment_readings.loc[closest_idx]
                        selected_time = selected_reading['measurement_date_utc']
                        selected_level = selected_reading['water_level']
                        
                        if progress_dialog:
                            progress_dialog.log_message(f"Found manual reading within segment, closest to end: {selected_time}")
                    else:
                        # If no readings in segment, look at ±1 hour window
                        # Use reading closest to end of segment
                        time_to_end = abs(valid_readings['measurement_date_utc'] - new_end)
                        closest_idx = time_to_end.idxmin()
                        selected_reading = valid_readings.loc[closest_idx]
                        selected_time = selected_reading['measurement_date_utc']
                        selected_level = selected_reading['water_level']
                        
                        if progress_dialog:
                            progress_dialog.log_message(f"Using closest manual reading to segment end: {selected_time}")
                    
                    # Find closest transducer reading to the selected manual reading
                    time_diffs = abs(df['timestamp_utc'] - selected_time)
                    closest_idx = time_diffs.idxmin()
                    closest_pressure = df.loc[closest_idx, 'water_pressure']
                    closest_time = df.loc[closest_idx, 'timestamp_utc']
                    
                    # Calculate dh using this single manual reading
                    dh = selected_level - closest_pressure
                    
                    if progress_dialog:
                        progress_dialog.log_message(
                            f"Manual reading: {selected_level:.2f} ft at {selected_time}, "
                            f"closest pressure: {closest_pressure:.2f} ft at {closest_time}, dh: {dh:.2f} ft"
                        )
                    
                    return {
                        'dh': float(dh),
                        'method': 'manual_readings',
                        'method_details': f"Single manual reading at {selected_time} (dh={dh:.2f})"
                    }
            
            # Case 2: Check existing data for readings before segment
            if existing_data is not None and not existing_data.empty:
                if progress_dialog:
                    progress_dialog.log_message(f"Found {len(existing_data)} existing readings to check")
                
                # Look for readings before our segment (predicted method)
                before_segment = existing_data[existing_data['timestamp_utc'] < new_start]
                
                if not before_segment.empty:
                    # Find the most recent reading before our segment
                    latest_idx = before_segment['timestamp_utc'].idxmax()
                    latest_level = before_segment.loc[latest_idx, 'water_level']
                    latest_time = before_segment.loc[latest_idx, 'timestamp_utc']
                    
                    # Calculate time gap in hours
                    time_gap = (new_start - latest_time).total_seconds() / 3600
                    
                    # Calculate dh using water pressure at start of new segment
                    start_pressure = df.loc[df['timestamp_utc'] == new_start, 'water_pressure'].iloc[0]
                    dh = latest_level - start_pressure
                    
                    if progress_dialog:
                        progress_dialog.log_message(f"Using existing level {latest_level:.2f} ft from {latest_time}")
                        progress_dialog.log_message(f"Time gap: {time_gap:.2f} hours, Calculated dh: {dh:.2f} ft")
                    
                    return {
                        'dh': float(dh),
                        'method': 'predicted',
                        'method_details': f"Predicted from existing data with {time_gap:.2f}h gap"
                    }
            
            # Case 3: Default fallback using TOC-30
            default_level = float(well_info['top_of_casing']) - 30
            start_pressure = df.loc[df['timestamp_utc'] == new_start, 'water_pressure'].iloc[0]
            dh = default_level - start_pressure
            
            if progress_dialog:
                progress_dialog.log_message(f"Using default level (TOC-30): {default_level:.2f} ft")
                progress_dialog.log_message(f"Calculated dh: {dh:.2f} ft")
            
            return {
                'dh': float(dh),
                'method': 'default_level',
                'method_details': f"Default level from top of casing ({well_info['top_of_casing']})"
            }
                
        except Exception as e:
            logger.error(f"Error determining insertion level: {e}", exc_info=True)
            if progress_dialog:
                progress_dialog.log_message(f"Error determining insertion level: {e}")
            
            # Even on error, return a consistent structure
            default_level = float(well_info['top_of_casing']) - 30
            start_pressure = df.loc[df['timestamp_utc'] == new_start, 'water_pressure'].iloc[0]
            dh = default_level - start_pressure
            
            return {
                'dh': float(dh),
                'method': 'default_level',
                'method_details': f"Error fallback to default level"
            }

    def _check_data_gap(self, df: pd.DataFrame, reference_data: pd.DataFrame, progress_dialog=None) -> float:
        """Calculate minimum time gap between datasets in hours"""
        try:
            if df.empty or reference_data.empty:
                if progress_dialog:
                    progress_dialog.log_message("Empty dataframe received")
                return float('inf')
            
            new_times = pd.to_datetime(df['timestamp_utc'])
            ref_times = pd.to_datetime(reference_data['timestamp_utc'])
            
            # Debug info to progress dialog
            if progress_dialog:
                progress_dialog.log_message(f"New data range: {new_times.min()} to {new_times.max()}")
                progress_dialog.log_message(f"Reference data range: {ref_times.min()} to {ref_times.max()}")
                if 'water_level' in reference_data.columns:
                    progress_dialog.log_message(f"Reference data levels: min={reference_data['water_level'].min():.2f}, max={reference_data['water_level'].max():.2f}")
            
            # Find closest reference point and its details
            time_diffs = abs(new_times.iloc[0] - ref_times)
            min_gap = time_diffs.min().total_seconds() / 3600
            closest_idx = time_diffs.argmin()
            
            # Get detailed info about closest point
            if progress_dialog:
                closest_time = ref_times.iloc[closest_idx]
                if 'water_level' in reference_data.columns:
                    closest_level = reference_data.iloc[closest_idx]['water_level']
                    progress_dialog.log_message("\nClosest reference point details:")
                    progress_dialog.log_message(f"  Time: {closest_time}")
                    progress_dialog.log_message(f"  Level: {closest_level:.2f} ft")
                    progress_dialog.log_message(f"  Gap: {min_gap:.2f} hours")
                    
                    # Show some surrounding data points
                    window = 2  # Points before and after
                    start_idx = max(0, closest_idx - window)
                    end_idx = min(len(reference_data), closest_idx + window + 1)
                    
                    progress_dialog.log_message("\nSurrounding data points:")
                    for idx in range(start_idx, end_idx):
                        progress_dialog.log_message(
                            f"  {ref_times[idx]}: {reference_data.iloc[idx]['water_level']:.2f} ft"
                        )
            
            return min_gap
            
        except Exception as e:
            if progress_dialog:
                progress_dialog.log_message(f"Error calculating data gap: {e}")
            return float('inf')

    def process_file(self, file_path: Path, well_number: str) -> Tuple[bool, str, Dict]:
        """Process a single XLE file"""
        try:
            # Read file
            df, metadata = self.solinst_reader.read_xle(file_path)
            
            # Ensure timestamp_utc is datetime
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
            
            # Validate transducer
            valid, status, details = self.validate_transducer(well_number, metadata.serial_number)
            if not valid:
                return False, status, details
                
            # Get well info
            well_info = self.get_well_info(well_number)
            if not well_info:
                return False, f"Well {well_number} not found", None
                
            # Get manual readings and existing data
            time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
            manual_readings = self._get_manual_readings(well_number, time_range)
            existing_data = self._get_existing_data(well_number, time_range)
            
            # Check barometric coverage
            baro_coverage = self._check_baro_coverage(time_range)
            
            # Ensure timestamps in existing_data are datetime
            if not existing_data.empty:
                existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])
            
            # Correct boundary readings
            df = self.correct_boundary_readings(df)
            
            # Process data
            processed_data = self.process_data(df, well_info, manual_readings, existing_data)
            
            return True, "File processed successfully", {
                'data': processed_data,
                'metadata': metadata,
                'well_info': well_info,
                'manual_readings': manual_readings,
                'existing_data': existing_data,
                'time_range': time_range,
                'baro_coverage': baro_coverage  # Add this
            }
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return False, str(e), None

    def _check_baro_coverage(self, time_range: Tuple[datetime, datetime]) -> Dict:
        """Check barometric data coverage for time range"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                start, end = time_range
                logger.debug(f"Checking baro coverage for range: {start} to {end}")
                
                # First check if master_baro_readings table exists
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='master_baro_readings'
                """)
                
                if not cursor.fetchone():
                    logger.debug("No master_baro_readings table found")
                    return {
                        'type': 'none',
                        'complete': False,
                        'message': 'No barometric data available. Standard pressure will be used.',
                        'data': None
                    }
                
                # Get actual barometric data with expanded range for better coverage assessment
                # Add a small buffer to better handle edge cases
                buffer_time = timedelta(hours=1)
                query = """
                    SELECT timestamp_utc, pressure, temperature
                    FROM master_baro_readings
                    WHERE timestamp_utc BETWEEN ? AND ?
                    ORDER BY timestamp_utc
                """
                
                df = pd.read_sql_query(query, conn, params=(
                    (start - buffer_time).strftime('%Y-%m-%d %H:%M:%S'),
                    (end + buffer_time).strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                if not df.empty:
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    min_time = df['timestamp_utc'].min()
                    max_time = df['timestamp_utc'].max()
                    start_ts = pd.to_datetime(start)
                    end_ts = pd.to_datetime(end)
                    
                    # Check for complete coverage
                    complete = (min_time <= start_ts and max_time >= end_ts)
                    
                    # Check for partial coverage - if we cover at least 75% of the time range
                    # and have points before and after, consider it usable
                    partial = False
                    if not complete:
                        time_span = (end_ts - start_ts).total_seconds()
                        coverage_span = 0
                        
                        if min_time <= start_ts:
                            # We have coverage from the start to max_time
                            coverage_span = (max_time - start_ts).total_seconds()
                        elif max_time >= end_ts:
                            # We have coverage from min_time to the end
                            coverage_span = (end_ts - min_time).total_seconds()
                        else:
                            # We have coverage from min_time to max_time
                            coverage_span = (max_time - min_time).total_seconds()
                        
                        coverage_percentage = (coverage_span / time_span) * 100
                        logger.debug(f"Partial baro coverage: {coverage_percentage:.1f}%")
                        
                        # If we have at least 75% coverage, consider it usable
                        if coverage_percentage >= 75:
                            partial = True
                            logger.debug(f"Using partial baro coverage ({coverage_percentage:.1f}%)")
                    
                    logger.debug(f"Baro data found: range {min_time} to {max_time}, complete coverage: {complete}, partial: {partial}")
                    
                    return {
                        'type': 'master',
                        'complete': complete or partial,  # Consider it complete if we have good partial coverage
                        'partial': partial,
                        'message': 'Master barometric data available',
                        'data': df
                    }
                    
                logger.debug("No baro data found in range")
                return {
                    'type': 'none',
                    'complete': False,
                    'message': 'No barometric data for this time range. Standard pressure will be used.',
                    'data': None
                }
                    
        except Exception as e:
            logger.error(f"Error checking baro coverage: {e}", exc_info=True)
            return {
                'type': 'none',
                'complete': False,
                'message': f'Error checking barometric data: {str(e)}. Standard pressure will be used.',
                'data': None
            }

    def process_data(self, df: pd.DataFrame, well_info: Dict,
                    manual_readings: pd.DataFrame = None,
                    existing_data: pd.DataFrame = None,
                    is_folder_import: bool = False) -> pd.DataFrame:
        """Process water level data"""
        try:
            df = df.copy()
            
            # Ensure timestamp_utc is datetime and remove any NaT values early
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
            df = df.dropna(subset=['timestamp_utc'])
            
            # Check if barometric processing has already been done
            # This happens when folder_handler sets these columns for consistency
            barometric_processed = ('water_pressure' in df.columns and 
                                   'baro_flag' in df.columns and 
                                   'baro_source' in df.columns)
            
            # Only do barometric processing if not already done
            if not barometric_processed:
                # Get barometric data for this time range
                time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
                logger.debug(f"Getting baro data for time range: {time_range}")
                logger.debug(f"Time range types: {type(time_range[0])}, {type(time_range[1])}")
                
                baro_coverage = self._check_baro_coverage(time_range)
                
                # Calculate water pressure with appropriate compensation
                if baro_coverage['type'] == 'master' and baro_coverage['complete']:
                    # Use master barometric data
                    baro_df = baro_coverage['data']
                    logger.debug("Using master baro data for compensation")
                    
                    # Check if we can interpolate safely
                    can_interpolate = True
                    if len(baro_df) < 2:
                        can_interpolate = False
                        logger.warning("Not enough barometric points for interpolation")
                    
                    if can_interpolate:
                        # Ensure baro timestamps are datetime
                        baro_df['timestamp_utc'] = pd.to_datetime(baro_df['timestamp_utc'])
                        
                        # Check if we need to extrapolate
                        start_ts = pd.to_datetime(time_range[0])
                        end_ts = pd.to_datetime(time_range[1])
                        baro_start = baro_df['timestamp_utc'].min()
                        baro_end = baro_df['timestamp_utc'].max()
                        
                        extrapolation_needed = (start_ts < baro_start or end_ts > baro_end)
                        if extrapolation_needed and 'partial' in baro_coverage and baro_coverage['partial']:
                            logger.debug("Using partial baro coverage with extrapolation")
                        
                        # Interpolate barometric pressure to match our timestamps
                        baro_pressure = np.interp(
                            df['timestamp_utc'].values.astype('datetime64[ns]').astype(float),
                            baro_df['timestamp_utc'].values.astype('datetime64[ns]').astype(float),
                            baro_df['pressure'].values
                        )
                        df['water_pressure'] = df['pressure'] - baro_pressure
                        df['baro_source'] = 'master_baro'
                        df['baro_flag'] = 'master'
                    else:
                        logger.debug("Not enough baro data for interpolation, using standard pressure")
                        df['water_pressure'] = df['pressure'] - self.STANDARD_ATMOS_PRESSURE
                        df['baro_source'] = 'standard_pressure'
                        df['baro_flag'] = 'standard'
                else:
                    logger.debug("Using standard atmospheric pressure")
                    # Use standard atmospheric pressure
                    df['water_pressure'] = df['pressure'] - self.STANDARD_ATMOS_PRESSURE
                    df['baro_source'] = 'standard_pressure'
                    df['baro_flag'] = 'standard'
            else:
                logger.debug(f"Barometric processing already done, baro_flag={df['baro_flag'].iloc[0]}")
            
            # Ensure all timestamps in reference data are datetime
            if existing_data is not None and not existing_data.empty:
                existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])
            if manual_readings is not None and not manual_readings.empty:
                manual_readings['measurement_date_utc'] = pd.to_datetime(manual_readings['measurement_date_utc'])
            
            # Determine insertion level
            insertion_info = self.determine_insertion_level(
                df,
                well_info,
                manual_readings,
                existing_data,
                is_folder_import
            )
            
            # Calculate water levels
            if insertion_info:
                # Apply the insertion level using _apply_insertion_level
                df = self._apply_insertion_level(df, insertion_info)
                
                # Set insertion_time to timestamp_utc if not present
                df['insertion_time'] = df['timestamp_utc']
                
                # Verify no NaT values were introduced
                if df['timestamp_utc'].isna().any():
                    logger.warning("NaT values detected in timestamp_utc after processing")
                    df = df.dropna(subset=['timestamp_utc'])
                
                return df
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing data: {e}", exc_info=True)
            return df

    def _get_manual_readings(self, well_number: str, time_range: Tuple[datetime, datetime]) -> pd.DataFrame:
        """Get manual readings from database"""
        try:
            start, end = time_range
            buffer = timedelta(minutes=30)
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                query = """
                    SELECT measurement_date_utc, water_level
                    FROM manual_level_readings
                    WHERE well_number = ?
                    AND measurement_date_utc BETWEEN ? AND ?
                    ORDER BY measurement_date_utc
                """
                df = pd.read_sql_query(query, conn, params=(
                    well_number,
                    (start - buffer).strftime('%Y-%m-%d %H:%M:%S'),
                    (end + buffer).strftime('%Y-%m-%d %H:%M:%S')
                ))
                if not df.empty:
                    df['measurement_date_utc'] = pd.to_datetime(df['measurement_date_utc'])
                return df
        except Exception as e:
            logger.error(f"Error getting manual readings: {e}")
            return pd.DataFrame()

    def _get_existing_data(self, well_number: str, time_range: Tuple[datetime, datetime]) -> pd.DataFrame:
        """Get existing readings from database"""
        try:
            start, end = time_range
            buffer = timedelta(hours=2)
            logger.debug(f"\n=== Getting existing data for well {well_number} ===")
            logger.debug(f"Time range: {start} to {end}")
            
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                # First check if the level_flag column exists
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(water_level_readings)")
                columns = [col[1] for col in cursor.fetchall()]
                logger.debug(f"Available columns in water_level_readings table: {columns}")
                
                # Build query based on available columns
                select_columns = [
                    "timestamp_utc", "pressure", "water_level", "temperature",
                    "baro_flag"
                ]
                if "level_flag" in columns:
                    select_columns.append("level_flag")
                    logger.debug("level_flag column exists and will be included in query")
                else:
                    logger.debug("level_flag column NOT FOUND in table!")
                
                query = f"""
                    SELECT {', '.join(select_columns)}
                    FROM water_level_readings 
                    WHERE well_number = ? 
                    AND timestamp_utc BETWEEN ? AND ?
                    ORDER BY timestamp_utc
                """
                logger.debug(f"Executing query: {query}")
                logger.debug(f"Query parameters: {well_number}, {(start - buffer).strftime('%Y-%m-%d %H:%M:%S')}, {(end + buffer).strftime('%Y-%m-%d %H:%M:%S')}")
                
                df = pd.read_sql_query(query, conn, params=(
                    well_number,
                    (start - buffer).strftime('%Y-%m-%d %H:%M:%S'),
                    (end + buffer).strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                logger.debug(f"Query returned {len(df)} rows")
                if not df.empty:
                    logger.debug(f"Columns in returned DataFrame: {df.columns.tolist()}")
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    if 'insertion_time_utc' in df.columns:
                        df['insertion_time_utc'] = pd.to_datetime(df['insertion_time_utc'])
                else:
                    logger.debug("Query returned empty DataFrame")
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting existing data: {e}", exc_info=True)
            return pd.DataFrame()

    def correct_boundary_readings(self, df: pd.DataFrame, progress_dialog=None) -> pd.DataFrame:
        """Correct anomalous readings at file boundaries using time series behavior"""
        try:
            BOUNDARY_MINUTES = 15  # Minutes to check at boundaries
            ANALYSIS_HOURS = 1     # Hours of data to analyze for behavior
            
            if progress_dialog:
                progress_dialog.log_message("\nStarting boundary reading corrections...")
                progress_dialog.log_message(f"Total readings: {len(df)}")
                progress_dialog.log_message(f"Initial range: {df['pressure'].min():.2f} to {df['pressure'].max():.2f} PSI")
            
            # Make a copy of the dataframe to avoid modifying the original
            df = df.copy()
            df = df.sort_values('timestamp_utc').reset_index(drop=True)
            
            # Get boundary periods
            start_time = df['timestamp_utc'].min()
            end_time = df['timestamp_utc'].max()
            start_boundary = start_time + timedelta(minutes=BOUNDARY_MINUTES)
            end_boundary = end_time - timedelta(minutes=BOUNDARY_MINUTES)
            
            # Get reference behavior from middle section (1 hour after start)
            reference_start = start_time + timedelta(hours=1)
            reference_end = reference_start + timedelta(hours=1)
            reference_data = df[
                (df['timestamp_utc'] >= reference_start) & 
                (df['timestamp_utc'] <= reference_end)
            ]
            
            if not reference_data.empty:
                # Calculate typical rate of change from reference period
                time_diff = reference_data['timestamp_utc'].diff().dt.total_seconds() / 3600
                pressure_diff = reference_data['pressure'].diff()
                typical_rate = pressure_diff[~pressure_diff.isnull()].median()
                
                if progress_dialog:
                    progress_dialog.log_message(f"Reference period rate: {typical_rate:.3f} PSI/hour")
                
                # Process start boundary (first 15 minutes)
                start_mask = df['timestamp_utc'] <= start_boundary
                start_segment = df[start_mask]
                if not start_segment.empty:
                    # Calculate rates for start segment
                    segment_rates = start_segment['pressure'].diff() / \
                                  (start_segment['timestamp_utc'].diff().dt.total_seconds() / 3600)
                    
                    # Detect anomalies (>3x typical rate)
                    threshold = 3 * abs(typical_rate)
                    anomalies = abs(segment_rates) > threshold
                    
                    if anomalies.any():
                        if progress_dialog:
                            progress_dialog.log_message(f"Found {anomalies.sum()} anomalies at start")
                            
                        # Get reference level from after boundary period
                        reference_level = df[~start_mask]['pressure'].iloc[0]
                        for idx in start_segment.index[anomalies]:
                            # Linear interpolation towards reference
                            time_diff = (df.loc[idx, 'timestamp_utc'] - start_boundary).total_seconds() / 3600
                            df.loc[idx, 'pressure'] = reference_level + (typical_rate * time_diff)
                
                # Process end boundary (last 15 minutes) - similar logic
                end_mask = df['timestamp_utc'] >= end_boundary
                end_segment = df[end_mask]
                if not end_segment.empty:
                    segment_rates = end_segment['pressure'].diff() / \
                                  (end_segment['timestamp_utc'].diff().dt.total_seconds() / 3600)
                    anomalies = abs(segment_rates) > threshold
                    
                    if anomalies.any():
                        if progress_dialog:
                            progress_dialog.log_message(f"Found {anomalies.sum()} anomalies at end")
                            
                        reference_level = df[~end_mask]['pressure'].iloc[-1]
                        for idx in end_segment.index[anomalies]:
                            time_diff = (df.loc[idx, 'timestamp_utc'] - end_boundary).total_seconds() / 3600
                            df.loc[idx, 'pressure'] = reference_level + (typical_rate * time_diff)
            
            if progress_dialog:
                progress_dialog.log_message(f"\nFinal range: {df['pressure'].min():.2f} to {df['pressure'].max():.2f} PSI")
            
            return df
            
        except Exception as e:
            if progress_dialog:
                progress_dialog.log_message(f"Error in boundary correction: {e}")
            logger.error(f"Error correcting boundary readings: {e}")
            return df
            
    def _extrapolate_value(self, valid_data: pd.DataFrame, target_time: datetime) -> float:
        """Linear extrapolation based on pressure data behavior"""
        try:
            # Use last few valid points for extrapolation
            recent_data = valid_data.sort_values('timestamp_utc').tail(5)
            
            if len(recent_data) >= 2:
                # Calculate rate of change using pressure
                time_diff = (recent_data['timestamp_utc'].max() - 
                           recent_data['timestamp_utc'].min()).total_seconds() / 3600
                pressure_diff = (recent_data['pressure'].max() - 
                               recent_data['pressure'].min())
                rate = pressure_diff / time_diff
                
                # Extrapolate pressure
                time_to_target = (target_time - 
                                recent_data['timestamp_utc'].max()).total_seconds() / 3600
                return recent_data['pressure'].iloc[-1] + (rate * time_to_target)
            
            return valid_data['pressure'].iloc[-1]
            
        except Exception as e:
            logger.error(f"Error extrapolating value: {e}")
            return valid_data['pressure'].iloc[-1]

    def _apply_insertion_level(self, df: pd.DataFrame, insertion_info: Dict) -> pd.DataFrame:
        """Apply height difference (dh) to water pressure readings to get water levels."""
        try:
            df = df.copy()
            
            # Apply dh to all readings
            df['water_level'] = df['water_pressure'] + insertion_info['dh']
            
            # Add metadata
            df['level_flag'] = insertion_info['method']
            df['level_details'] = insertion_info['method_details']
            
            return df
            
        except Exception as e:
            logger.error(f"Error applying insertion level: {e}", exc_info=True)
            raise
