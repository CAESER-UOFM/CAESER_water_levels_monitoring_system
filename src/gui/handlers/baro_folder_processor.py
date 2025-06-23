import logging
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime
import sqlite3
from .baro_import_handler import BaroFileProcessor
from .solinst_reader import SolinstReader, SolinstMetadata
from collections import defaultdict
from ..dialogs.baro_progress_dialog import BaroProgressDialog
from ..utils.file_organizer import XLEFileOrganizer  # Import the new utility

logger = logging.getLogger(__name__)

class BaroFolderProcessor:
    def __init__(self, baro_model):
        self.baro_model = baro_model
        self.processor = BaroFileProcessor(baro_model)
        self.solinst_reader = SolinstReader()
        self._scanned_data = {}  # Cache for scanned file data
        # Initialize file organizer with app root directory (parent of database path)
        self.file_organizer = XLEFileOrganizer(Path(baro_model.db_path).parent, db_name=Path(baro_model.db_path).stem)

    def scan_folder(self, folder_path: Path, include_subfolders: bool = False, 
                   progress_dialog: BaroProgressDialog = None) -> Dict:
        """Scan folder for barologger files with progress tracking"""
        try:
            if progress_dialog:
                progress_dialog.log_message("=== Starting Folder Scan ===")
                progress_dialog.log_message(f"Scanning folder: {folder_path}")
                if include_subfolders:
                    progress_dialog.log_message("Including subfolders in scan")
            
            # Get list of all XLE files
            pattern = "**/*.xle" if include_subfolders else "*.xle"
            all_files = list(folder_path.glob(pattern))
            
            if not all_files:
                return {'error': "No XLE files found in folder"}
                
            if progress_dialog:
                progress_dialog.log_message(f"\nFound {len(all_files)} XLE files")
                progress_dialog.update_progress(0, len(all_files))
            
            # Initialize data structures
            barologger_files = defaultdict(list)  # serial -> [files]
            metadata_cache = {}  # file -> metadata
            processed_files = 0
            
            # First pass: Group files by serial number and collect metadata
            for i, file_path in enumerate(all_files):
                if progress_dialog:
                    if progress_dialog.was_canceled():
                        return {'error': "Operation canceled by user"}
                    progress_dialog.update_progress(i + 1, len(all_files))
                    progress_dialog.update_status(f"Processing: {file_path.name}")

                try:
                    # Read and validate file, storing data for reuse
                    df, metadata = self.solinst_reader.read_xle(file_path)
                    
                    if not self.solinst_reader.is_barologger(metadata):
                        if progress_dialog:
                            progress_dialog.log_message(f"Skipping non-barologger file: {file_path.name}")
                        continue
                        
                    serial = metadata.serial_number
                    
                    # Check if barologger exists in database
                    if not self.baro_model.barologger_exists(serial):
                        if progress_dialog:
                            progress_dialog.log_message(
                                f"Warning: Barologger {serial} not registered in database"
                            )
                        continue
                    
                    if progress_dialog:
                        progress_dialog.log_message(
                            f"Found barologger file: {file_path.name}"
                            f"\n  Serial: {serial}"
                            f"\n  Location: {metadata.location}"
                            f"\n  Time Range: {metadata.start_time} to {metadata.stop_time}"
                            f"\n  Readings: {len(df)}"
                        )
                    
                    # Store both metadata and data for reuse
                    self._scanned_data[file_path] = {
                        'data': df,
                        'metadata': metadata,
                        'time_range': (metadata.start_time, metadata.stop_time)
                    }
                    
                    metadata_cache[file_path] = {
                        'metadata': metadata,
                        'time_range': (metadata.start_time, metadata.stop_time)
                    }
                    barologger_files[serial].append(file_path)
                    processed_files += 1
                    
                except Exception as e:
                    if progress_dialog:
                        progress_dialog.log_message(f"Error processing {file_path.name}: {e}")
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue

            # Process each barologger's files
            if progress_dialog:
                progress_dialog.log_message("\n=== Processing Results ===")
            
            processed_data = {}
            for serial, files in barologger_files.items():
                if progress_dialog:
                    progress_dialog.log_message(f"\nBarologger {serial}:")
                    progress_dialog.log_message(f"  Found {len(files)} files")

                # Sort files by start time
                files.sort(key=lambda f: metadata_cache[f]['time_range'][0])
                
                # Remove duplicates
                unique_files = self._remove_duplicates(files, metadata_cache)
                
                if unique_files:
                    if progress_dialog and len(unique_files) != len(files):
                        progress_dialog.log_message(
                            f"  Removed {len(files) - len(unique_files)} duplicate files"
                        )
                    
                    processed_data[serial] = {
                        'files': unique_files,
                        'metadata': metadata_cache[unique_files[0]]['metadata'],
                        'time_ranges': [metadata_cache[f]['time_range'] for f in unique_files]
                    }
                    
                    if progress_dialog:
                        time_ranges = processed_data[serial]['time_ranges']
                        overall_start = min(r[0] for r in time_ranges)
                        overall_end = max(r[1] for r in time_ranges)
                        progress_dialog.log_message(
                            f"  Final files: {len(unique_files)}"
                            f"\n  Overall time range: {overall_start} to {overall_end}"
                        )

            if not processed_data:
                return {'error': "No valid barologger files found after processing."}

            # Final summary
            if progress_dialog:
                progress_dialog.log_message(f"\n=== Scan Summary ===")
                progress_dialog.log_message(f"Total XLE files found: {len(all_files)}")
                progress_dialog.log_message(f"Valid barologger files: {processed_files}")
                progress_dialog.log_message(f"Barologgers found: {len(processed_data)}")
                progress_dialog.update_status("Scan complete")
                progress_dialog.finish_operation()

            return {
                'barologgers': processed_data,
                'file_count': len(all_files),
                'processed_count': processed_files
            }

        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
            if progress_dialog:
                progress_dialog.log_message(f"Error scanning folder: {str(e)}")
            return {'error': str(e)}

    def _remove_duplicates(self, files: List[Path], metadata_cache: Dict) -> List[Path]:
        """
        Remove duplicate files based on time ranges and data content
        """
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

    def process_barologger_files(self, serial_number: str, files: List[Path]) -> Dict:
        """
        Process all files for a single barologger
        """
        try:
            all_data = []
            # Organize each file as we process it
            location = self.processor.get_logger_location(serial_number)
            
            for file_path in files:
                # Use cached data if available, otherwise read file
                if file_path in self._scanned_data:
                    df = self._scanned_data[file_path]['data']
                    metadata = self._scanned_data[file_path]['metadata']
                else:
                    # Fallback to reading file if not in cache
                    df, metadata = self.solinst_reader.read_xle(file_path)
                
                # Add to our combined dataset
                all_data.append(df)

            # Combine all data
            if not all_data:
                return None

            combined_df = pd.concat(all_data)
            combined_df = combined_df.sort_values('timestamp_utc')

            # Get existing data for comparison
            existing_data = self.processor.get_existing_data(serial_number)

            return {
                'data': combined_df,
                'existing_data': existing_data,
                'has_overlap': self._check_overlap(combined_df, existing_data)
            }

        except Exception as e:
            logger.error(f"Error processing files for {serial_number}: {e}")
            return None

    def _check_overlap(self, new_data: pd.DataFrame, existing_data: pd.DataFrame) -> bool:
        """Check for overlapping data between new and existing data"""
        if existing_data.empty or new_data.empty:
            return False

        new_range = (new_data['timestamp_utc'].min(), new_data['timestamp_utc'].max())
        existing_range = (existing_data['timestamp_utc'].min(), existing_data['timestamp_utc'].max())

        return not (new_range[1] < existing_range[0] or new_range[0] > existing_range[1])
