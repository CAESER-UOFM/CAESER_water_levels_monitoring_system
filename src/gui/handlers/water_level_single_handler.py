# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 10:43:40 2025

@author: bledesma
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
from .water_level_processor import WaterLevelProcessor

logger = logging.getLogger(__name__)

class WaterLevelHandler:
    def __init__(self, water_level_model):
        self.water_level_model = water_level_model
        self.processor = WaterLevelProcessor(water_level_model)

    def validate_file(self, file_path: Path, well_number: str) -> Tuple[bool, str, Dict]:
        """Validate a single file before processing"""
        try:
            # Read file metadata
            df, metadata = self.processor.solinst_reader.read_xle(file_path)
            
            # Validate transducer
            valid, status, details = self.processor.validate_transducer(well_number, metadata.serial_number)
            if not valid:
                return False, status, None

            # Get well info
            well_info = self.processor.get_well_info(well_number)
            if not well_info:
                return False, f"Well {well_number} not found", None

            return True, "File is valid", {
                'metadata': metadata,
                'preview_data': df,
                'well_info': well_info
            }

        except Exception as e:
            logger.error(f"Error validating file: {e}", exc_info=True)
            return False, str(e), None

    def process_file(self, file_path: Path, well_number: str) -> Tuple[bool, str, Dict]:
        """Process a single water level file"""
        try:
            # Validate file first
            valid, status, details = self.validate_file(file_path, well_number)
            if not valid:
                return False, status, None

            # Get data from validation
            df = details['preview_data']
            well_info = details['well_info']

            # Get time range for reference data
            time_range = (df['timestamp_utc'].min(), df['timestamp_utc'].max())
            
            # Get reference data
            manual_readings = self.processor._get_manual_readings(well_number, time_range)
            existing_data = self.processor._get_existing_data(well_number, time_range)

            # Correct boundary readings before processing
            df = self.processor.correct_boundary_readings(df)

            # Process the data using core processor
            processed_data = self.processor.process_data(
                df, 
                well_info,
                manual_readings,
                existing_data,
                is_folder_import=False
            )

            return True, "File processed successfully", {
                'processed_data': processed_data,
                'metadata': details['metadata'],
                'well_info': well_info,
                'manual_readings': manual_readings,
                'existing_data': existing_data
            }

        except Exception as e:
            logger.error(f"Error processing file: {e}", exc_info=True)
            return False, str(e), None