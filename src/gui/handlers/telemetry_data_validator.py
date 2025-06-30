#!/usr/bin/env python3
"""
Telemetry Data Validator

This module validates telemetry data and ensures consistent reference points
between manual and telemetry measurements.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TelemetryDataValidator:
    """Validates telemetry data against manual readings and ensures consistent reference points"""
    
    def __init__(self):
        self.tolerance_ft = 2.0  # Acceptable difference in feet between manual and telemetry
        
    def validate_telemetry_reference(self, telemetry_df: pd.DataFrame, 
                                   manual_readings: pd.DataFrame,
                                   well_info: Dict) -> Dict:
        """
        Validate telemetry data reference point by comparing with manual readings.
        
        Args:
            telemetry_df: DataFrame with telemetry readings (columns: timestamp_utc, water_level, dtw)
            manual_readings: DataFrame with manual readings (columns: measurement_date_utc, water_level, dtw_avg)
            well_info: Dict with well information (top_of_casing, ground_elevation)
            
        Returns:
            Dict with validation results and suggested corrections
        """
        if telemetry_df.empty or manual_readings.empty:
            return {
                'status': 'insufficient_data',
                'message': 'Insufficient data for validation',
                'corrections': {}
            }
            
        try:
            # Find overlapping time periods (±6 hours)
            validation_results = []
            
            for _, manual_row in manual_readings.iterrows():
                manual_time = pd.to_datetime(manual_row['measurement_date_utc'])
                manual_water_level = manual_row['water_level']
                manual_dtw = manual_row['dtw_avg']
                
                # Find closest telemetry reading within 6 hours
                time_window = timedelta(hours=6)
                nearby_telemetry = telemetry_df[
                    abs(pd.to_datetime(telemetry_df['timestamp_utc']) - manual_time) <= time_window
                ]
                
                if nearby_telemetry.empty:
                    continue
                    
                # Get closest telemetry reading
                time_diffs = abs(pd.to_datetime(nearby_telemetry['timestamp_utc']) - manual_time)
                closest_idx = time_diffs.idxmin()
                telemetry_row = nearby_telemetry.loc[closest_idx]
                
                telemetry_water_level = telemetry_row['water_level']
                telemetry_dtw = telemetry_row.get('dtw', None)
                
                # Calculate differences
                water_level_diff = abs(telemetry_water_level - manual_water_level)
                
                validation_results.append({
                    'manual_time': manual_time,
                    'manual_water_level': manual_water_level,
                    'manual_dtw': manual_dtw,
                    'telemetry_time': pd.to_datetime(telemetry_row['timestamp_utc']),
                    'telemetry_water_level': telemetry_water_level,
                    'telemetry_dtw': telemetry_dtw,
                    'water_level_diff': water_level_diff,
                    'time_diff_hours': time_diffs.loc[closest_idx].total_seconds() / 3600
                })
                
            if not validation_results:
                return {
                    'status': 'no_overlapping_data',
                    'message': 'No overlapping manual and telemetry data found',
                    'corrections': {}
                }
                
            # Analyze validation results
            avg_diff = np.mean([r['water_level_diff'] for r in validation_results])
            max_diff = np.max([r['water_level_diff'] for r in validation_results])
            
            # Check if telemetry might be using wrong reference point
            toc = well_info.get('top_of_casing', 0)
            ground_elevation = well_info.get('ground_elevation', toc - 5)  # Default 5 ft below TOC
            reference_offset = toc - ground_elevation
            
            # Test if applying reference offset improves agreement
            corrected_diffs = []
            for result in validation_results:
                # Test correction: telemetry + reference_offset
                corrected_telemetry = result['telemetry_water_level'] + reference_offset
                corrected_diff = abs(corrected_telemetry - result['manual_water_level'])
                corrected_diffs.append(corrected_diff)
                
            avg_corrected_diff = np.mean(corrected_diffs)
            
            # Determine status and corrections
            if avg_diff <= self.tolerance_ft:
                status = 'good'
                message = f'Telemetry and manual readings agree within {avg_diff:.2f} ft'
                corrections = {}
            elif avg_corrected_diff < avg_diff and avg_corrected_diff <= self.tolerance_ft:
                status = 'reference_correction_needed'
                message = f'Telemetry appears to use different reference point. Correction: +{reference_offset:.2f} ft'
                corrections = {
                    'apply_offset': reference_offset,
                    'reason': 'telemetry_uses_ground_reference_instead_of_toc'
                }
            else:
                status = 'poor_agreement'
                message = f'Poor agreement between telemetry and manual readings (avg diff: {avg_diff:.2f} ft)'
                corrections = {
                    'manual_review_required': True,
                    'suggested_actions': [
                        'Check telemetry sensor calibration',
                        'Verify reference point documentation',
                        'Compare with nearby manual readings'
                    ]
                }
                
            return {
                'status': status,
                'message': message,
                'corrections': corrections,
                'validation_details': {
                    'num_comparisons': len(validation_results),
                    'avg_difference_ft': avg_diff,
                    'max_difference_ft': max_diff,
                    'avg_corrected_difference_ft': avg_corrected_diff,
                    'reference_offset_ft': reference_offset,
                    'comparisons': validation_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating telemetry reference: {e}")
            return {
                'status': 'error',
                'message': f'Validation error: {str(e)}',
                'corrections': {}
            }
    
    def apply_telemetry_corrections(self, telemetry_df: pd.DataFrame, 
                                  corrections: Dict) -> pd.DataFrame:
        """
        Apply corrections to telemetry data based on validation results.
        
        Args:
            telemetry_df: Original telemetry DataFrame
            corrections: Corrections dictionary from validate_telemetry_reference
            
        Returns:
            Corrected telemetry DataFrame
        """
        if telemetry_df.empty or not corrections:
            return telemetry_df
            
        corrected_df = telemetry_df.copy()
        
        # Apply offset correction if needed
        if 'apply_offset' in corrections:
            offset = corrections['apply_offset']
            corrected_df['water_level'] = corrected_df['water_level'] + offset
            
            # Update DTW if available
            if 'dtw' in corrected_df.columns:
                corrected_df['dtw'] = corrected_df['dtw'] - offset
                
            # Add correction metadata
            corrected_df['correction_applied'] = f'reference_offset_{offset:.2f}ft'
            corrected_df['correction_reason'] = corrections.get('reason', 'unknown')
            
            logger.info(f"Applied telemetry correction: +{offset:.2f} ft to water levels")
            
        return corrected_df
    
    def create_validation_report(self, validation_results: Dict, 
                               output_file: Optional[str] = None) -> str:
        """
        Create a human-readable validation report.
        
        Args:
            validation_results: Results from validate_telemetry_reference
            output_file: Optional file path to save report
            
        Returns:
            Report text
        """
        report_lines = [
            "TELEMETRY DATA VALIDATION REPORT",
            "=" * 50,
            f"Status: {validation_results['status']}",
            f"Message: {validation_results['message']}",
            ""
        ]
        
        if 'validation_details' in validation_results:
            details = validation_results['validation_details']
            report_lines.extend([
                "VALIDATION DETAILS:",
                f"  Number of comparisons: {details['num_comparisons']}",
                f"  Average difference: {details['avg_difference_ft']:.3f} ft",
                f"  Maximum difference: {details['max_difference_ft']:.3f} ft",
                f"  Reference offset tested: {details['reference_offset_ft']:.3f} ft",
                ""
            ])
            
            if 'comparisons' in details:
                report_lines.append("INDIVIDUAL COMPARISONS:")
                for i, comp in enumerate(details['comparisons'][:5]):  # Show first 5
                    report_lines.append(
                        f"  {i+1}. Manual: {comp['manual_water_level']:.2f} ft, "
                        f"Telemetry: {comp['telemetry_water_level']:.2f} ft, "
                        f"Diff: {comp['water_level_diff']:.2f} ft"
                    )
                if len(details['comparisons']) > 5:
                    report_lines.append(f"  ... and {len(details['comparisons']) - 5} more")
                report_lines.append("")
        
        if validation_results['corrections']:
            report_lines.extend([
                "RECOMMENDED CORRECTIONS:",
                str(validation_results['corrections']),
                ""
            ])
            
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
                
        return report_text