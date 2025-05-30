# -*- coding: utf-8 -*-
"""
Created on Sun Feb  2 21:39:12 2025

@author: Benja
"""

import logging 
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from collections import defaultdict
from .solinst_reader import SolinstReader
from ...database.models.water_level import WaterLevelModel
from ..dialogs.water_level_progress_dialog import WaterLevelProgressDialog
from .water_level_processor import WaterLevelProcessor
from PyQt5.QtWidgets import QApplication, QMessageBox
import numpy as np

logger = logging.getLogger(__name__)

class WaterLevelFolderProcessor:
    def __init__(self, water_level_model):
        self.water_level_model = water_level_model
        self.processor = WaterLevelProcessor(water_level_model)
        self.solinst_reader = SolinstReader()

    def scan_folder(self, folder_path: Path, include_subfolders: bool = False,
                   progress_dialog: WaterLevelProgressDialog = None,
                   check_mode: str = 'double') -> Dict:
        """Only scan and organize files, no processing
        
        Args:
            folder_path: Path to scan for XLE files
            include_subfolders: Whether to include subfolders in scan
            progress_dialog: Optional progress dialog for updates
            check_mode: 'single' for serial number only, 'double' for serial number and CAE
        """
        try:
            if progress_dialog:
                progress_dialog.log_message(f"Scanning folder: {folder_path}")
                progress_dialog.log_message(f"Check mode: {check_mode}")

            # Get all XLE files
            all_files = []
            if include_subfolders:
                for file_path in folder_path.rglob('*.xle'):
                    all_files.append(file_path)
            else:
                for file_path in folder_path.glob('*.xle'):
                    all_files.append(file_path)

            if not all_files:
                return {'error': "No .xle files found in folder"}

            # Sort files by date
            all_files.sort()

            # Get well mapping
            well_mapping = self._get_well_mapping()
            if not well_mapping:
                return {'error': "Could not get well mapping"}

            # Get transducer mapping for single check mode
            transducer_mapping = self._get_transducer_mapping() if check_mode == 'single' else {}

            # Track unique files to avoid duplicates
            unique_files = {}
            results = defaultdict(lambda: {
                'files': [],
                'segments': [],
                'well_info': None,
                'time_range': None,
                'has_been_processed': False,
                'metadata': None,  # Initialize metadata field
                'has_overlap': False,  # Initialize overlap flag
                'overlap_range': None  # Initialize overlap range
            })

            if progress_dialog:
                progress_dialog.log_message(f"\nFound {len(all_files)} XLE files to process")
                progress_dialog.update_progress(0, len(all_files))
                progress_dialog.update_status("Scanning files...")

            processed_files = 0
            for file_path in all_files:
                if progress_dialog and progress_dialog.was_canceled():
                    return {'error': "Operation canceled by user"}

                try:
                    # Get metadata from file
                    metadata, _ = self.solinst_reader.get_file_metadata(file_path)
                    
                    # Skip barologgers
                    if self.solinst_reader.is_barologger(metadata):
                        if progress_dialog:
                            progress_dialog.log_message(f"Skipping barologger file: {file_path.name}")
                        continue

                    # Create unique identifier for this file
                    file_id = (metadata.serial_number, 
                             metadata.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                             metadata.stop_time.strftime('%Y-%m-%d %H:%M:%S'),
                             metadata.location)
                    
                    # If we've seen this file before, skip it
                    if file_id in unique_files:
                        if progress_dialog:
                            progress_dialog.log_message(f"Skipping duplicate file: {file_path.name}")
                        continue
                    
                    well_number = None
                    if check_mode == 'double':
                        # Double check mode - match CAE and validate transducer
                        well_number = self._match_well_location(metadata.location, well_mapping)
                        if not well_number:
                            if progress_dialog:
                                progress_dialog.log_message(f"Could not match CAE {metadata.location} to any well - File: {file_path.name}")
                            continue
                            
                        # Validate transducer
                        valid, status, details = self.processor.validate_transducer(well_number, metadata.serial_number)
                        if not valid:
                            if progress_dialog:
                                progress_dialog.log_message(f"Invalid transducer for {file_path.name}: {status}")
                            continue
                    else:
                        # Single check mode - match by serial number only
                        well_number = transducer_mapping.get(metadata.serial_number)
                        if not well_number:
                            if progress_dialog:
                                progress_dialog.log_message(f"Could not match transducer {metadata.serial_number} to any well - File: {file_path.name}")
                            continue

                    # Get well info if we haven't already
                    if not results[well_number]['well_info']:
                        results[well_number]['well_info'] = self.processor.get_well_info(well_number)
                        if progress_dialog:
                            progress_dialog.log_message(f"\nProcessing well {well_number} (CAE: {metadata.location})")

                    # Store file info and metadata
                    unique_files[file_id] = file_path
                    results[well_number]['files'].append(file_path)
                    if not results[well_number]['metadata']:  # Store first file's metadata
                        results[well_number]['metadata'] = metadata

                    # Update time range
                    if not results[well_number]['time_range']:
                        results[well_number]['time_range'] = [metadata.start_time, metadata.stop_time]
                        if progress_dialog:
                            progress_dialog.log_message(f"Initial time range: {metadata.start_time} to {metadata.stop_time}")
                    else:
                        old_start = results[well_number]['time_range'][0]
                        old_end = results[well_number]['time_range'][1]
                        results[well_number]['time_range'][0] = min(old_start, metadata.start_time)
                        results[well_number]['time_range'][1] = max(old_end, metadata.stop_time)
                        if progress_dialog and (old_start != results[well_number]['time_range'][0] or 
                                             old_end != results[well_number]['time_range'][1]):
                            progress_dialog.log_message(f"Updated time range: {results[well_number]['time_range'][0]} to {results[well_number]['time_range'][1]}")

                    processed_files += 1
                    if progress_dialog:
                        progress_dialog.update_progress(processed_files, len(all_files))
                        if processed_files % 5 == 0 or processed_files == len(all_files):  # Log every 5 files and the last one
                            progress_dialog.log_message(f"Processed {processed_files} of {len(all_files)} files")

                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    if progress_dialog:
                        progress_dialog.log_message(f"Error processing {file_path.name}: {str(e)}")
                    continue

            # Check for overlaps with existing data
            if progress_dialog:
                progress_dialog.log_message("\nChecking for data overlaps...")

            for well_number, info in results.items():
                if not info['time_range']:
                    continue

                start_time, end_time = info['time_range']
                existing_data = self.processor._get_existing_data(well_number, (start_time, end_time))

                if not existing_data.empty:
                    existing_data['timestamp_utc'] = pd.to_datetime(existing_data['timestamp_utc'])
                    overlap_mask = (
                        (existing_data['timestamp_utc'] >= start_time) &
                        (existing_data['timestamp_utc'] <= end_time)
                    )
                    
                    if overlap_mask.any():
                        info['has_overlap'] = True
                        overlap_start = existing_data.loc[overlap_mask, 'timestamp_utc'].min()
                        overlap_end = existing_data.loc[overlap_mask, 'timestamp_utc'].max()
                        info['overlap_range'] = (overlap_start, overlap_end)
                        
                        if progress_dialog:
                            progress_dialog.log_message(
                                f"\nOverlap detected for well {well_number}:"
                                f"\n  Start: {overlap_start}"
                                f"\n  End: {overlap_end}"
                            )

            # Final summary
            if progress_dialog:
                progress_dialog.log_message(f"\n=== Scan Summary ===")
                progress_dialog.log_message(f"Total files processed: {processed_files}")
                progress_dialog.log_message(f"Wells found: {len(results)}")
                for well_number, info in results.items():
                    progress_dialog.log_message(f"\nWell {well_number}:")
                    progress_dialog.log_message(f"  Files: {len(info['files'])}")
                    if info['time_range']:
                        progress_dialog.log_message(f"  Time Range: {info['time_range'][0]} to {info['time_range'][1]}")
                    if info['has_overlap']:
                        progress_dialog.log_message(f"  Has overlapping data: Yes")
                        progress_dialog.log_message(f"  Overlap Range: {info['overlap_range'][0]} to {info['overlap_range'][1]}")

            return results

        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
            if progress_dialog:
                progress_dialog.log_message(f"Error scanning folder: {str(e)}")
            return {'error': str(e)}

    def process_files(self, file_map: Dict, progress_dialog: WaterLevelProgressDialog = None) -> Dict:
        """Process scanned files"""
        try:
            if progress_dialog:
                progress_dialog.log_message("\n=== Starting File Processing ===")
                
            processed_wells = 0
            total_wells = len(file_map)
            total_files = sum(len(info['files']) for info in file_map.values())
            processed_files = 0
            
            if progress_dialog:
                progress_dialog.log_message(f"Found {total_wells} wells with {total_files} total files")
                progress_dialog.update_progress(0, total_files)
            
            # Create file organizer - moved inside the loop to ensure fresh instance
            from ..utils.file_organizer import XLEFileOrganizer
            app_root_dir = Path(__file__).parent.parent.parent.parent
            
            logger.info(f"FILE_ORG: App root directory: {app_root_dir}")
            if progress_dialog:
                progress_dialog.log_message("File organizer will be initialized per well")

            for well_number, well_data in file_map.items():
                if progress_dialog and progress_dialog.was_canceled():
                    return file_map

                if not well_data['files']:
                    continue

                try:
                    progress_dialog.log_message(f"\n=== Processing Well {well_number} ===")
                    progress_dialog.log_message(f"Files to Process: {len(well_data['files'])}")
                    progress_dialog.log_message(f"Time Range: {well_data['time_range'][0]} to {well_data['time_range'][1]}")

                    # Get full time range
                    start_time = well_data['time_range'][0]
                    end_time = well_data['time_range'][1]
                    
                    # Get reference data
                    progress_dialog.log_message("Getting existing data...")
                    existing_data = self.processor._get_existing_data(well_number, (start_time, end_time))
                    if not existing_data.empty:
                        progress_dialog.log_message(f"Found {len(existing_data)} existing readings")
                    
                    progress_dialog.log_message("Getting manual readings...")
                    manual_readings = self.processor._get_manual_readings(well_number, (start_time, end_time))
                    if not manual_readings.empty:
                        progress_dialog.log_message(f"Found {len(manual_readings)} manual readings")
                    
                    # NEW: Check barometric coverage once for the entire well's time range
                    progress_dialog.log_message("Checking barometric coverage for entire time range...")
                    baro_coverage = self.processor._check_baro_coverage((start_time, end_time))
                    if baro_coverage['type'] == 'master' and baro_coverage['complete']:
                        progress_dialog.log_message("Using MASTER barometric data for this well")
                    else:
                        progress_dialog.log_message("Using STANDARD atmospheric pressure for this well")
                    
                    # Store barometric data in well_data for reuse with each file
                    well_data['baro_coverage'] = baro_coverage
                    
                    new_data_vector = pd.DataFrame()
                    
                    # Initialize organizer fresh for each well
                    organizer = XLEFileOrganizer(app_root_dir)
                    logger.info(f"FILE_ORG: Initialized organizer for well {well_number}")
                    progress_dialog.log_message(f"File organizer initialized for well {well_number}")

                    # Process files in chronological order
                    for idx, file_path in enumerate(well_data['files'], 1):
                        if progress_dialog and progress_dialog.was_canceled():
                            return file_map
                            
                        file_start_time = pd.Timestamp.now()
                        progress_dialog.update_status(f"Processing file {idx} of {len(well_data['files'])}: {file_path.name}")
                        progress_dialog.log_message(f"\n=== Processing {file_path.name} ===")
                        
                        try:
                            # Read raw data
                            progress_dialog.log_message("Reading XLE file...")
                            df, metadata = self.solinst_reader.read_xle(file_path)
                            progress_dialog.log_message(f"Found {len(df)} readings")
                            
                            # MODIFIED: Pass the pre-checked barometric coverage to the processor
                            # by modifying the process_data call to include the baro_coverage
                            progress_dialog.log_message("Processing readings...")
                            
                            # Ensure timestamp_utc is datetime
                            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                            
                            # Calculate water pressure with appropriate compensation using the
                            # well-level baro_coverage rather than checking per-file
                            if baro_coverage['type'] == 'master' and baro_coverage['complete']:
                                # Use master barometric data
                                progress_dialog.log_message("Using master barometric data...")
                                baro_df = baro_coverage['data']
                                
                                # Interpolate barometric pressure
                                baro_df['timestamp_utc'] = pd.to_datetime(baro_df['timestamp_utc'])
                                baro_pressure = np.interp(
                                    df['timestamp_utc'].values.astype('datetime64[ns]').astype(float),
                                    baro_df['timestamp_utc'].values.astype('datetime64[ns]').astype(float),
                                    baro_df['pressure'].values
                                )
                                df['water_pressure'] = df['pressure'] - baro_pressure
                                df['baro_source'] = 'master_baro'
                                df['baro_flag'] = 'master'
                            else:
                                # Use standard atmospheric pressure
                                progress_dialog.log_message("Using standard atmospheric pressure...")
                                df['water_pressure'] = df['pressure'] - self.processor.STANDARD_ATMOS_PRESSURE
                                df['baro_source'] = 'standard_pressure'
                                df['baro_flag'] = 'standard'
                            
                            # Process the data using core processor but skip the baro compensation part
                            # by passing our pre-processed DataFrame
                            # For folder import, we want to ensure proper leveling between segments:
                            # - For first file: use manual readings and existing data from database
                            # - For subsequent files: use manual readings and already processed data segments
                            
                            # Combine existing data from database with already processed segments
                            combined_reference_data = existing_data.copy() if not existing_data.empty else pd.DataFrame()
                            
                            if not new_data_vector.empty:
                                # If we've already processed some files, use them as reference too
                                if combined_reference_data.empty:
                                    combined_reference_data = new_data_vector
                                else:
                                    combined_reference_data = pd.concat([combined_reference_data, new_data_vector])
                                    combined_reference_data = combined_reference_data.sort_values('timestamp_utc')
                            
                            # This ensures the processor will first check manual readings within the segment,
                            # then prior existing data (which now includes previously processed segments)
                            df = self.processor.process_data(
                                df, 
                                well_data['well_info'],
                                manual_readings,
                                combined_reference_data,
                                is_folder_import=True
                            )
                            
                            # Add to processed data
                            new_data_vector = pd.concat([new_data_vector, df])
                            new_data_vector = new_data_vector.sort_values('timestamp_utc')
                            
                            processing_time = (pd.Timestamp.now() - file_start_time).total_seconds()
                            progress_dialog.log_message(f"Processed {len(df)} readings in {processing_time:.1f} seconds")
                            if 'water_level' in df.columns:
                                progress_dialog.log_message(
                                    f"Water Level Range: {df['water_level'].min():.2f} to {df['water_level'].max():.2f} ft"
                                )
                            
                            processed_files += 1
                            progress_dialog.update_progress(processed_files, total_files)
                            
                        except Exception as e:
                            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
                            progress_dialog.log_message(f"Error processing file: {str(e)}")
                            continue
                    
                    # Store processed data
                    if not new_data_vector.empty:
                        well_data['processed_data'] = new_data_vector
                        well_data['has_been_processed'] = True
                        processed_wells += 1
                        
                        progress_dialog.log_message(f"\n=== Well Processing Complete ===")
                        progress_dialog.log_message(f"Total readings: {len(new_data_vector)}")
                        if 'water_level' in new_data_vector.columns:
                            progress_dialog.log_message(
                                f"Final Water Level Range: "
                                f"{new_data_vector['water_level'].min():.2f} to "
                                f"{new_data_vector['water_level'].max():.2f} ft"
                            )
                            
                        # KEY FIX: Remove file organization from here since it happens in import_selected
                        # File organization should NOT happen during processing, only during actual import
                        # The code below is removed to prevent duplicate file organization

                except Exception as e:
                    logger.error(f"Error processing well {well_number}: {e}", exc_info=True)
                    progress_dialog.log_message(f"Error processing well {well_number}: {str(e)}")
                    continue

            # Final summary
            if progress_dialog:
                progress_dialog.log_message(f"\n=== Processing Complete ===")
                progress_dialog.log_message(f"Successfully processed {processed_wells} of {total_wells} wells")
                progress_dialog.log_message(f"Total files processed: {processed_files} of {total_files}")
                progress_dialog.log_message(f"Files were organized to: {app_root_dir / 'imported_xle_files'}")
                
                # Show details for each processed well
                for well_number, info in file_map.items():
                    if info.get('has_been_processed'):
                        progress_dialog.log_message(f"\nWell {well_number}:")
                        progress_dialog.log_message(f"  Files: {len(info['files'])}")
                        if 'processed_data' in info:
                            progress_dialog.log_message(f"  Readings: {len(info['processed_data'])}")
                            if 'water_level' in info['processed_data'].columns:
                                progress_dialog.log_message(
                                    f"  Water Level Range: "
                                    f"{info['processed_data']['water_level'].min():.2f} to "
                                    f"{info['processed_data']['water_level'].max():.2f} ft"
                                )

            return file_map

        except Exception as e:
            logger.error(f"Error processing files: {e}", exc_info=True)
            if progress_dialog:
                progress_dialog.log_message(f"Error processing files: {str(e)}")
            return file_map

    def _get_well_mapping(self) -> Dict[str, str]:
        """Get mapping of CAE numbers to well numbers"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT cae_number, well_number FROM wells WHERE cae_number IS NOT NULL")
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Error getting well mapping: {e}")
            return {}

    def _match_well_location(self, location: str, well_mapping: Dict[str, str]) -> Optional[str]:
        """Match location to well number using CAE mapping"""
        try:
            # Try exact match first
            if location in well_mapping:
                return well_mapping[location]
            
            # Try without leading zeros
            location_no_zeros = location.lstrip('0')
            for cae, well in well_mapping.items():
                if cae.lstrip('0') == location_no_zeros:
                    return well
            
            return None
        except Exception as e:
            logger.error(f"Error matching well location: {e}")
            return None

    def _get_transducer_mapping(self) -> Dict[str, str]:
        """Get mapping of transducer serial numbers to well numbers"""
        try:
            with sqlite3.connect(self.water_level_model.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, well_number 
                    FROM transducers 
                    WHERE serial_number IS NOT NULL
                    AND is_active = 1
                """)
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Error getting transducer mapping: {e}")
            return {}
