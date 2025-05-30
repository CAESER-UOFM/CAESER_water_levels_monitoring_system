# -*- coding: utf-8 -*-
"""
Created on Sun Feb  2 21:39:12 2025

@author: Benja
"""

import logging 
from pathlib import Path
from typing import Dict, Tuple, List, Optional  # Add Optional here
from datetime import datetime, timedelta  # Add datetime here
import pandas as pd
import sqlite3
from collections import defaultdict
from .solinst_reader import SolinstReader
from ...database.models.water_level import WaterLevelModel
from ..dialogs.water_level_progress_dialog import WaterLevelProgressDialog
from ...core.water_level_processor import WaterLevelProcessor  # Add this import

logger = logging.getLogger(__name__)

# Add debug logging to monitor flow
logger.debug("Initializing water_level_folder_processor.py")

class WaterLevelFolderProcessor:
    def __init__(self, water_level_model):
        self.water_level_model = water_level_model
        self.processor = WaterLevelProcessor(water_level_model)
        self.solinst_reader = SolinstReader()
    
    def scan_folder(self, folder_path: Path, include_subfolders: bool = False,
                   progress_dialog: WaterLevelProgressDialog = None) -> Dict:
        """Only scan and organize files, no processing"""
        try:
            # Find all XLE files
            pattern = "**/*.xle" if include_subfolders else "*.xle"
            all_files = list(folder_path.glob(pattern))
            total_files = len(all_files)
            
            logger.debug(f"Found {total_files} XLE files in {folder_path}")
            
            if progress_dialog:
                progress_dialog.update_status("Scanning files...")
                progress_dialog.update_progress(0, total_files)
                progress_dialog.log_message(f"Found {total_files} XLE files to process")

            # Get well mappings first
            well_mapping = self._get_well_mapping()
            
            # Group files by well
            well_files = defaultdict(list)
            metadata_cache = {}
            processed = 0
            matched_wells = set()

            for file_path in all_files:
                if progress_dialog and progress_dialog.was_canceled():
                    return {'error': "Operation canceled by user"}

                try:
                    # Get metadata from file
                    metadata, _ = self.solinst_reader.get_file_metadata(file_path)
                    logger.debug(f"Processing file {file_path.name} - Location: {metadata.location}")
                    
                    # Skip barologgers
                    if self.solinst_reader.is_barologger(metadata):
                        continue

                    # Match CAE number to well number
                    well_number = self._match_well_location(metadata.location, well_mapping)
                    if not well_number:
                        logger.warning(f"Could not match CAE {metadata.location} to any well - File: {file_path.name}")
                        continue
                        
                    # Validate transducer
                    well_info = self.processor.get_well_info(well_number)
                    if not well_info or not self.processor.validate_transducer(well_number, metadata.serial_number):
                        continue

                    if well_number not in matched_wells:
                        matched_wells.add(well_number)
                        logger.info(f"Found new well {well_number} (CAE: {metadata.location})")
                        if progress_dialog:
                            progress_dialog.log_message(f"Found well {well_number} (CAE: {metadata.location})")

                    # Store basic info
                    metadata_cache[file_path] = {
                        'metadata': metadata,
                        'time_range': (metadata.start_time, metadata.stop_time),
                        'well_info': well_info
                    }
                    well_files[well_number].append(file_path)
                    
                    logger.debug(f"Added file {file_path.name} to well {well_number}")
                    
                except Exception as e:
                    logger.error(f"Error scanning file {file_path}: {e}")
                    if progress_dialog:
                        progress_dialog.log_message(f"Error with file {file_path.name}: {str(e)}")
                    continue

                processed += 1
                if progress_dialog:
                    progress_dialog.update_progress(processed, total_files)
                    progress_dialog.update_status(f"Scanning files ({processed}/{total_files})")

            logger.info(f"Scan complete - Found {len(matched_wells)} wells with valid data")
            if progress_dialog:
                progress_dialog.log_message(f"\nScan complete - Found {len(matched_wells)} wells with valid data")

            # Process each well's data to check for overlaps
            results = {}
            for well_number, files in well_files.items():
                well_data = {
                    'files': sorted(files, key=lambda f: metadata_cache[f]['time_range'][0]),
                    'metadata': metadata_cache[files[0]]['metadata'],
                    'well_info': metadata_cache[files[0]]['well_info'],
                    'time_range': (
                        min(metadata_cache[f]['time_range'][0] for f in files),
                        max(metadata_cache[f]['time_range'][1] for f in files)
                    )
                }
                
                # Check for overlaps with existing data
                start_time, end_time = well_data['time_range']
                with sqlite3.connect(self.water_level_model.db_path) as conn:
                    # Get existing data range
                    query = """
                        SELECT MIN(timestamp_utc), MAX(timestamp_utc)
                        FROM water_levels
                        WHERE well_number = ?
                        AND timestamp_utc BETWEEN ? AND ?
                    """
                    cursor = conn.cursor()
                    cursor.execute(query, (
                        well_number,
                        start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        end_time.strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    existing_range = cursor.fetchone()
                    
                    if existing_range[0]:  # If we have overlapping data
                        well_data['has_overlap'] = True
                        well_data['overlap_range'] = (
                            pd.to_datetime(existing_range[0]),
                            pd.to_datetime(existing_range[1])
                        )
                    else:
                        well_data['has_overlap'] = False
                        well_data['overlap_range'] = None
                
                results[well_number] = well_data

            return results

        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
            return {'error': str(e)}
            
    def process_file(self, file_path: Path, well_number: str) -> Tuple[bool, str, Dict]:
        """Process a single file using the core processor"""
        return self.processor.process_file(file_path, well_number)

    def _validate_transducer(self, well_number: str, serial_number: str) -> bool:
        """Validate transducer serial number against well assignments"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM transducers 
                    WHERE well_number = ? 
                    AND serial_number = ? 
                    AND end_date IS NULL
                """, (well_number, serial_number))
                
                return cursor.fetchone()[0] > 0
                
        except Exception as e:
            logger.error(f"Error validating transducer: {e}")
            return False

    def _remove_duplicates(self, files: List[Path], metadata_cache: Dict) -> List[Path]:
        """Remove duplicate files based on time ranges"""
        if not files:
            return []

        unique_files = []
        seen_ranges = set()

        for file_path in files:
            time_range = metadata_cache[file_path]['time_range']
            range_key = (time_range[0], time_range[1])
            
            if range_key not in seen_ranges:
                seen_ranges.add(range_key)
                unique_files.append(file_path)

        return unique_files

    def _process_file(self, processed_data: Dict, well_number: str, file_path: Path, 
                     progress_dialog: WaterLevelProgressDialog = None):
        """Process a single file for a well"""
        try:
            logger.debug(f"Starting to process file {file_path.name} for well {well_number}")
            
            if progress_dialog:
                progress_dialog.log_message(f"Reading file: {file_path.name}")

            # Read full file data
            logger.debug("Reading XLE file")
            df, metadata = self.solinst_reader.read_xle(file_path)
            
            if progress_dialog:
                progress_dialog.log_message("Processing data segment...")

            # Process the segment
            logger.debug("Processing segment")
            self._process_segment(processed_data, well_number, df, metadata, file_path, progress_dialog)
            logger.debug(f"Completed processing file {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)

    def _get_well_mapping(self) -> Dict[str, str]:
        """Get mapping of CAE numbers to well numbers"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT well_number, cae_number 
                    FROM wells 
                    WHERE cae_number IS NOT NULL
                """)
                # Create both direct and normalized mappings
                mappings = {}
                for wn, cae in cursor.fetchall():
                    if cae:  # Only if CAE is not None
                        # Store original
                        mappings[cae] = wn
                        # Store without spaces
                        mappings[cae.replace(" ", "")] = wn
                        # Store uppercase
                        mappings[cae.upper()] = wn
                        mappings[cae.upper().replace(" ", "")] = wn
                return mappings
        except Exception as e:
            logger.error(f"Error getting well mapping: {e}")
            return {}

    def _match_well_location(self, location: str, mapping: Dict[str, str]) -> str:
        """Try to match location to a well number"""
        # Try direct match
        if location in mapping:
            return mapping[location]
        
        # Try normalized
        normalized = location.upper().replace(" ", "")
        if normalized in mapping:
            return mapping[normalized]
        
        return None

    def _process_time_ranges(self, file_map: Dict, well_number: str):
        """Process time ranges and check for overlaps using UTC timestamps"""
        try:
            data = file_map[well_number]['data']
            if not data.empty:
                # Find segments based on 30-minute gaps
                time_diff = data['timestamp_utc'].diff()
                gaps = time_diff > timedelta(minutes=30)
                segment_ids = gaps.cumsum()
                
                # Process each segment
                segments = []
                for segment_id in segment_ids.unique():
                    segment = data[segment_ids == segment_id].copy()
                    segments.append(segment)
                
                # Store segments
                file_map[well_number]['segments'] = segments
                
                # Check for overlap with existing data
                min_time = data['timestamp_utc'].min()
                max_time = data['timestamp_utc'].max()
                
                with sqlite3.connect(self.water_level_model.db_path) as conn:
                    query = """
                        SELECT timestamp_utc
                        FROM water_levels
                        WHERE well_number = ?
                        AND timestamp_utc BETWEEN ? AND ?
                    """
                    
                    existing_df = pd.read_sql_query(query, conn, params=(
                        well_number,
                        min_time.strftime('%Y-%m-%d %H:%M:%S'),
                        max_time.strftime('%Y-%m-%d %H:%M:%S')
                    ))

                    if not existing_df.empty:
                        # Ensure all timestamps are naive UTC
                        existing_df['timestamp_utc'] = pd.to_datetime(existing_df['timestamp_utc'])
                        
                        # Find actual overlapping timestamps
                        new_timestamps = set(data['timestamp_utc'])
                        existing_timestamps = set(existing_df['timestamp_utc'])
                        overlap_timestamps = new_timestamps.intersection(existing_timestamps)
                        
                        if overlap_timestamps:
                            overlap_start = min(overlap_timestamps)
                            overlap_end = max(overlap_timestamps)
                            
                            file_map[well_number]['has_overlap'] = True
                            file_map[well_number]['overlap_range'] = (overlap_start, overlap_end)
                        else:
                            file_map[well_number]['has_overlap'] = False
                            file_map[well_number]['overlap_range'] = None
                        
        except Exception as e:
            logger.error(f"Error processing time ranges for {well_number}: {e}")
            file_map[well_number]['has_overlap'] = False
            file_map[well_number]['overlap_range'] = None

    def _get_well_info(self, well_number: str) -> Dict:
        """Get well information from database"""
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
                return pd.read_sql_query(query, conn, params=(
                    well_number,
                    (start - buffer).strftime('%Y-%m-%d %H:%M:%S'),
                    (end + buffer).strftime('%Y-%m-%d %H:%M:%S')
                ))
        except Exception as e:
            logger.error(f"Error getting manual readings: {e}")
            return pd.DataFrame()

    def _determine_insertion_level(self, df: pd.DataFrame, manual_readings: pd.DataFrame, 
                                 existing_data: pd.DataFrame, well_info: Dict) -> Dict:
        """Determine insertion level using same logic as single file import"""
        try:
            new_start = df['timestamp_utc'].iloc[0]
            new_end = df['timestamp_utc'].iloc[-1]
            logger.debug(f"Determining insertion level for data from {new_start} to {new_end}")
            
            # Case 1: Check existing data within 1 hour
            logger.debug("Checking existing data for continuity")
            if not existing_data.empty:
                data_gap = self._check_data_gap(df, existing_data)
                logger.debug(f"Gap with existing data: {data_gap} hours")
                if data_gap <= 1.0:  # Less than 1 hour gap
                    last_reading = existing_data.sort_values('timestamp_utc').iloc[-1]
                    logger.debug(f"Using predicted level from existing data: {last_reading['water_level']}")
                    logger.info(f"Insertion method for segment {new_start}: predicted from existing data")
                    return {
                        'level': float(last_reading['water_level']),
                        'time': new_start,
                        'reference_time': last_reading['timestamp_utc'],
                        'method': 'predicted',
                        'method_details': f"Predicted from existing data with {data_gap:.2f}h gap"
                    }
            
            # Case 2: Check manual readings
            logger.debug("Checking manual readings")
            if not manual_readings.empty:
                logger.debug(f"Found {len(manual_readings)} manual readings")
                valid_readings = manual_readings[
                    (manual_readings['measurement_date_utc'] >= (new_start - timedelta(minutes=30))) &
                    (manual_readings['measurement_date_utc'] <= (new_end + timedelta(minutes=30)))
                ]
                if not valid_readings.empty:
                    avg_level = valid_readings['water_level'].mean()
                    logger.debug(f"Using manual reading average: {avg_level}")
                    logger.info(f"Insertion method for segment {new_start}: manual readings average")
                    return {
                        'level': float(avg_level),
                        'time': new_start,
                        'reference_time': valid_readings['measurement_date_utc'].iloc[0],
                        'method': 'manual_readings',
                        'method_details': f"Average of {len(valid_readings)} manual readings"
                    }
            
            # Case 3: Use existing data mean if available
            logger.debug("Checking for existing data mean")
            if not existing_data.empty:
                mean_level = existing_data['water_level'].mean()
                logger.debug(f"Using existing data mean: {mean_level}")
                logger.info(f"Insertion method for segment {new_start}: existing data mean")
                return {
                    'level': float(mean_level),
                    'time': new_start,
                    'reference_time': None,
                    'method': 'existing_mean',
                    'method_details': f"Mean of {len(existing_data)} existing readings"
                }
            
            # Case 4: Default fallback
            default_level = float(well_info['top_of_casing']) - 30
            logger.debug(f"Using default level: {default_level}")
            logger.info(f"Insertion method for segment {new_start}: default level")
            return {
                'level': default_level,
                'time': new_start,
                'reference_time': None,
                'method': 'default_level',
                'method_details': f"Default level from top of casing ({well_info['top_of_casing']})"
            }
                
        except Exception as e:
            logger.error(f"Error determining insertion level: {e}")
            # Ultimate fallback
            default_level = float(well_info['top_of_casing']) - 30
            logger.debug(f"Error fallback to default level: {default_level}")
            logger.info(f"Insertion method for segment {new_start}: error fallback")
            return {
                'level': default_level,
                'time': new_start,
                'reference_time': None,
                'method': 'default_level',
                'method_details': f"Error fallback to default level"
            }

    def _apply_insertion_level(self, df: pd.DataFrame, insertion_info: Dict) -> pd.DataFrame:
        """Apply insertion level to data"""
        try:
            df = df.copy()
            # Calculate water pressure
            df['water_pressure'] = df['pressure'] - 14.7  # Standard atmospheric pressure
            
            # Find insertion pressure
            insertion_mask = df['timestamp_utc'] == insertion_info['time']
            insertion_pressure = df.loc[insertion_mask, 'water_pressure'].iloc[0]
            
            # Calculate dh
            dh = insertion_info['level'] - insertion_pressure
            
            # Apply to all readings
            df['water_level'] = df['water_pressure'] + dh
            df['insertion_level'] = insertion_info['level']
            df['insertion_time'] = insertion_info['time']
            df['level_flag'] = insertion_info['method']
            
            return df
            
        except Exception as e:
            logger.error(f"Error applying insertion level: {e}")
            return df

    def _get_existing_data(self, well_number: str, time_range: Tuple[datetime, datetime]) -> pd.DataFrame:
        """Get readings for a specific time range with buffer"""
        try:
            start, end = time_range
            buffer = timedelta(hours=2)  # Keep buffer for gap checking
            
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                # First check if there's any data at all
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM water_levels 
                    WHERE well_number = ?
                """, (well_number,))
                
                if cursor.fetchone()[0] == 0:
                    return pd.DataFrame()
    
                # Get data only in relevant range
                query = """
                    SELECT timestamp_utc, pressure, water_level, temperature,
                           baro_flag, baro_source, insertion_level, insertion_time_utc
                    FROM water_levels 
                    WHERE well_number = ? 
                    AND timestamp_utc BETWEEN ? AND ?
                    ORDER BY timestamp_utc
                """
                return pd.read_sql_query(query, conn, params=(
                    well_number,
                    (start - buffer).strftime('%Y-%m-%d %H:%M:%S'),
                    (end + buffer).strftime('%Y-%m-%d %H:%M:%S')
                ))
                    
        except Exception as e:
            logger.error(f"Error getting existing data: {e}")
            return pd.DataFrame()

    def _get_closest_data(self, df: pd.DataFrame, existing_data: pd.DataFrame, 
                         prev_segments: list) -> pd.DataFrame:
        """Find the closest data points from either existing data or previous segments"""
        try:
            closest_data = pd.DataFrame()
            new_start = pd.to_datetime(df['timestamp_utc'].min())
            logger.debug(f"Looking for closest data to {new_start}")
            
            # Only check the last segment since files are in chronological order
            if prev_segments:
                last_segment = prev_segments[-1]
                segment_times = pd.to_datetime(last_segment['timestamp_utc'])
                time_diff = (segment_times - new_start).abs().min()
                logger.debug(f"Time difference with previous segment: {time_diff}")
                if time_diff <= timedelta(hours=1):
                    logger.debug("Using previous segment for prediction")
                    closest_data = last_segment
            
            # If no close segment, check existing data
            if closest_data.empty and not existing_data.empty:
                logger.debug("Checking existing data")
                existing_times = pd.to_datetime(existing_data['timestamp_utc'])
                time_diff = (existing_times - new_start).abs().min()
                logger.debug(f"Time difference with existing data: {time_diff}")
                if time_diff <= timedelta(hours=1):
                    logger.debug("Using existing data for prediction")
                    closest_data = existing_data
                    
            if closest_data.empty:
                logger.debug("No close data found for prediction")
            return closest_data
            
        except Exception as e:
            logger.error(f"Error finding closest data: {e}")
            return pd.DataFrame()

    def _check_data_gap(self, df: pd.DataFrame, reference_data: pd.DataFrame) -> float:
        """Calculate minimum time gap between datasets in hours using vectorized operations"""
        try:
            if df.empty or reference_data.empty:
                return float('inf')
                
            # Get array of timestamps
            new_times = pd.to_datetime(df['timestamp_utc'].iloc[0])  # Only need first timestamp
            ref_times = pd.to_datetime(reference_data['timestamp_utc'])
            
            # Vectorized time difference calculation
            time_diffs = abs(ref_times - new_times)
            min_gap = time_diffs.min().total_seconds() / 3600
            
            logger.debug(f"Minimum gap between datasets: {min_gap} hours")
            return min_gap
            
        except Exception as e:
            logger.error(f"Error calculating data gap: {e}")
            return float('inf')

    def _process_segment(self, file_map: Dict, well_number: str, df: pd.DataFrame, 
                        metadata: object, file_path: Path, 
                        progress_dialog: WaterLevelProgressDialog = None):
        """Process a single data segment"""
        try:
            logger.debug(f"Processing segment for well {well_number}")
            
            if progress_dialog:
                progress_dialog.log_message("Getting previous segments...")
            
            # Get data from previously processed segments
            prev_segments = file_map[well_number]['segments']
            logger.debug(f"Found {len(prev_segments)} previous segments")
            
            # Get manual readings and existing data
            time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
            logger.debug(f"Getting data for time range: {time_range[0]} to {time_range[1]}")
            
            if progress_dialog:
                progress_dialog.log_message("Getting manual readings and existing data...")
            
            manual_readings = self._get_manual_readings(well_number, time_range)
            
            # Use cached existing data instead of querying again
            existing_data = file_map[well_number].get('existing_data', pd.DataFrame())
            
            # Only look at last segment since files are in chronological order
            prev_segments = file_map[well_number]['segments'][-1:] if file_map[well_number]['segments'] else []
            
            # Find closest data for prediction
            logger.debug("Finding closest data for prediction")
            if progress_dialog:
                progress_dialog.log_message("Finding closest data for prediction...")
            closest_data = self._get_closest_data(df, existing_data, prev_segments)
            
            # Calculate insertion level
            logger.debug("Calculating insertion level")
            if progress_dialog:
                progress_dialog.log_message("Calculating insertion level...")
            insertion_info = self._determine_insertion_level(
                df, manual_readings, closest_data, 
                file_map[well_number]['well_info']
            )
            
            # Apply insertion level
            logger.debug("Applying insertion level")
            if progress_dialog:
                progress_dialog.log_message(f"Applying insertion level ({insertion_info['method']})")
                progress_dialog.log_message(f"Details: {insertion_info['method_details']}")
            df = self._apply_insertion_level(df, insertion_info)
            
            # Store processed segment with method info
            logger.debug("Storing processed segment")
            if progress_dialog:
                progress_dialog.log_message("Storing processed segment...")
            df['level_method'] = insertion_info['method']
            df['level_details'] = insertion_info['method_details']
            file_map[well_number]['segments'].append(df)
            file_map[well_number]['files'].append(file_path)
            file_map[well_number]['metadata'] = metadata
            logger.debug("Segment processing complete")
            if progress_dialog:
                progress_dialog.log_message("Segment processing complete")
            
        except Exception as e:
            logger.error(f"Error processing segment: {e}", exc_info=True)
