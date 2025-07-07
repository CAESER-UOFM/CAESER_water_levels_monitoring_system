"""
ERC (Extended Recession Curve) Database Manager

This module manages database operations for the ERC method, including:
- Extended recession curves with multiple segments
- Temporal variability analysis
- Cross-validation data
- Enhanced calculation storage

Based on USGS EMR methodology with extensions for temporal analysis.
"""

import logging
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ErcDatabase:
    """Database manager for ERC (Extended Recession Curve) calculations."""
    
    def __init__(self, db_path: str):
        """
        Initialize the ERC database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        logger.info(f"Initialized ERC database manager with path: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def create_tables(self) -> bool:
        """
        Create the ERC database tables if they don't exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create erc_curves table - Extended with temporal analysis
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erc_curves (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        well_id TEXT NOT NULL,
                        well_name TEXT NOT NULL,
                        creation_date TEXT NOT NULL,
                        curve_type TEXT NOT NULL,  -- 'exponential', 'power_law', 'polynomial', 'multi_segment'
                        curve_parameters TEXT NOT NULL,  -- JSON with fitting parameters
                        curve_coefficients TEXT NOT NULL,  -- JSON with a, b, intercept, polynomial coeffs, etc.
                        r_squared REAL,
                        data_start_date TEXT,
                        data_end_date TEXT,
                        recession_segments INTEGER,
                        min_recession_length INTEGER,
                        seasonal_analysis BOOLEAN DEFAULT 0,  -- Whether seasonal analysis was performed
                        temporal_segments TEXT,  -- JSON array of temporal periods analyzed
                        cross_validation_score REAL,  -- Cross-validation R² score
                        description TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        version INTEGER DEFAULT 1,
                        parent_curve_id INTEGER,  -- For tracking curve updates
                        FOREIGN KEY (parent_curve_id) REFERENCES erc_curves(id)
                    )
                """)
                
                # Create erc_calculations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erc_calculations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        curve_id INTEGER NOT NULL,
                        well_id TEXT NOT NULL,
                        well_name TEXT NOT NULL,
                        calculation_date TEXT NOT NULL,
                        specific_yield REAL NOT NULL,
                        deviation_threshold REAL NOT NULL,
                        water_year_start_month INTEGER NOT NULL,
                        water_year_start_day INTEGER NOT NULL,
                        downsample_rule TEXT,
                        downsample_method TEXT,
                        filter_type TEXT,
                        filter_window INTEGER,
                        seasonal_correction BOOLEAN DEFAULT 0,  -- Whether seasonal correction applied
                        validation_method TEXT,  -- Cross-validation approach used
                        total_recharge REAL NOT NULL,
                        annual_rate REAL NOT NULL,
                        total_events INTEGER NOT NULL,
                        calculation_period_start TEXT NOT NULL,
                        calculation_period_end TEXT NOT NULL,
                        quality_score REAL,  -- Overall quality assessment
                        notes TEXT,
                        FOREIGN KEY (curve_id) REFERENCES erc_curves(id)
                    )
                """)
                
                # Create erc_recharge_events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erc_recharge_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        calculation_id INTEGER NOT NULL,
                        event_date TEXT NOT NULL,
                        water_year TEXT NOT NULL,
                        water_level REAL NOT NULL,
                        predicted_level REAL NOT NULL,
                        deviation REAL NOT NULL,
                        recharge_value REAL NOT NULL,
                        event_magnitude TEXT,  -- 'small', 'medium', 'large'
                        seasonal_period TEXT,  -- 'winter', 'spring', 'summer', 'fall'
                        validation_flag BOOLEAN DEFAULT 1,  -- Whether event passed validation
                        confidence_score REAL,  -- Event confidence (0-1)
                        FOREIGN KEY (calculation_id) REFERENCES erc_calculations(id)
                    )
                """)
                
                # Create erc_yearly_summaries table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erc_yearly_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        calculation_id INTEGER NOT NULL,
                        water_year TEXT NOT NULL,
                        total_recharge REAL NOT NULL,
                        num_events INTEGER NOT NULL,
                        annual_rate REAL NOT NULL,
                        max_deviation REAL NOT NULL,
                        avg_deviation REAL NOT NULL,
                        seasonal_distribution TEXT,  -- JSON with seasonal breakdown
                        quality_indicators TEXT,  -- JSON with quality metrics
                        FOREIGN KEY (calculation_id) REFERENCES erc_calculations(id)
                    )
                """)
                
                # Create erc_recession_segments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erc_recession_segments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        curve_id INTEGER NOT NULL,
                        segment_number INTEGER NOT NULL,
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        duration_days INTEGER NOT NULL,
                        start_level REAL NOT NULL,
                        end_level REAL NOT NULL,
                        recession_rate REAL NOT NULL,
                        seasonal_period TEXT,  -- Season when recession occurred
                        segment_quality REAL,  -- Individual segment quality score
                        used_in_fitting BOOLEAN DEFAULT 1,  -- Whether used in curve fitting
                        FOREIGN KEY (curve_id) REFERENCES erc_curves(id)
                    )
                """)
                
                # Create erc_temporal_analysis table - NEW for extended analysis
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erc_temporal_analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        curve_id INTEGER NOT NULL,
                        temporal_period TEXT NOT NULL,  -- 'annual', 'seasonal', 'monthly'
                        period_identifier TEXT NOT NULL,  -- Year, season name, month name
                        curve_coefficients TEXT NOT NULL,  -- JSON with period-specific coefficients
                        r_squared REAL,
                        segment_count INTEGER,
                        period_start_date TEXT NOT NULL,
                        period_end_date TEXT NOT NULL,
                        FOREIGN KEY (curve_id) REFERENCES erc_curves(id)
                    )
                """)
                
                # Create indices for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_curves_well ON erc_curves(well_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_calculations_curve ON erc_calculations(curve_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_calculations_well ON erc_calculations(well_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_recharge_events_calc ON erc_recharge_events(calculation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_yearly_summaries_calc ON erc_yearly_summaries(calculation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_recession_segments_curve ON erc_recession_segments(curve_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_erc_temporal_analysis_curve ON erc_temporal_analysis(curve_id)")
                
                conn.commit()
                logger.info("ERC database tables created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error creating ERC database tables: {e}", exc_info=True)
            return False
    
    def save_curve(self, well_id: str, well_name: str, curve_type: str,
                   curve_parameters: Dict, curve_coefficients: Dict, r_squared: float,
                   recession_segments: int, min_recession_length: int = 10,
                   seasonal_analysis: bool = False, temporal_segments: List = None,
                   cross_validation_score: float = None, description: str = "",
                   recession_segments_data: List = None) -> Optional[int]:
        """
        Save an ERC curve to the database.
        
        Args:
            well_id: Well identifier
            well_name: Well name
            curve_type: Type of curve ('exponential', 'power_law', 'polynomial', 'multi_segment')
            curve_parameters: Dictionary of fitting parameters
            curve_coefficients: Dictionary of curve coefficients
            r_squared: R-squared value
            recession_segments: Number of recession segments used
            min_recession_length: Minimum recession length used
            seasonal_analysis: Whether seasonal analysis was performed
            temporal_segments: List of temporal periods analyzed
            cross_validation_score: Cross-validation R² score
            description: Description of the curve
            recession_segments_data: List of recession segment data
            
        Returns:
            int: Curve ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Determine data period from segments
                data_start_date = None
                data_end_date = None
                if recession_segments_data:
                    dates = []
                    for seg in recession_segments_data:
                        dates.extend([seg['start_date'], seg['end_date']])
                    data_start_date = min(dates)
                    data_end_date = max(dates)
                
                # Insert curve
                cursor.execute("""
                    INSERT INTO erc_curves (
                        well_id, well_name, creation_date, curve_type, curve_parameters,
                        curve_coefficients, r_squared, data_start_date, data_end_date,
                        recession_segments, min_recession_length, seasonal_analysis,
                        temporal_segments, cross_validation_score, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    well_id, well_name, datetime.now().isoformat(), curve_type,
                    json.dumps(curve_parameters), json.dumps(curve_coefficients),
                    r_squared, data_start_date, data_end_date, recession_segments,
                    min_recession_length, seasonal_analysis,
                    json.dumps(temporal_segments or []), cross_validation_score, description
                ))
                
                curve_id = cursor.lastrowid
                
                # Save recession segments if provided
                if recession_segments_data and curve_id:
                    for i, segment in enumerate(recession_segments_data):
                        cursor.execute("""
                            INSERT INTO erc_recession_segments (
                                curve_id, segment_number, start_date, end_date,
                                duration_days, start_level, end_level, recession_rate,
                                seasonal_period, segment_quality, used_in_fitting
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            curve_id, i + 1, segment['start_date'], segment['end_date'],
                            segment['duration_days'], segment['start_level'],
                            segment['end_level'], segment['recession_rate'],
                            segment.get('seasonal_period'), segment.get('segment_quality', 1.0),
                            segment.get('used_in_fitting', True)
                        ))
                
                conn.commit()
                logger.info(f"Saved ERC curve {curve_id} for well {well_id}")
                return curve_id
                
        except Exception as e:
            logger.error(f"Error saving ERC curve: {e}", exc_info=True)
            return None
    
    def get_curves_for_well(self, well_id: str) -> List[Dict]:
        """
        Get all ERC curves for a specific well.
        
        Args:
            well_id: Well identifier
            
        Returns:
            List of curve dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM erc_curves 
                    WHERE well_id = ? AND is_active = 1
                    ORDER BY creation_date DESC
                """, (well_id,))
                
                curves = []
                for row in cursor.fetchall():
                    curve = dict(row)
                    # Parse JSON fields
                    curve['curve_parameters'] = json.loads(curve['curve_parameters'])
                    curve['curve_coefficients'] = json.loads(curve['curve_coefficients'])
                    curve['temporal_segments'] = json.loads(curve['temporal_segments'] or '[]')
                    curves.append(curve)
                
                return curves
                
        except Exception as e:
            logger.error(f"Error getting ERC curves for well {well_id}: {e}", exc_info=True)
            return []
    
    def save_calculation(self, curve_id: int, well_id: str, well_name: str,
                        specific_yield: float, deviation_threshold: float,
                        water_year_start_month: int, water_year_start_day: int,
                        downsample_rule: str = None, downsample_method: str = None,
                        filter_type: str = None, filter_window: int = None,
                        seasonal_correction: bool = False, validation_method: str = None,
                        total_recharge: float = 0, annual_rate: float = 0,
                        recharge_events: List = None, yearly_summaries: List = None,
                        quality_score: float = None, notes: str = "") -> Optional[int]:
        """
        Save an ERC calculation to the database.
        
        Args:
            curve_id: Associated curve ID
            well_id: Well identifier
            well_name: Well name
            specific_yield: Specific yield value
            deviation_threshold: Deviation threshold
            water_year_start_month: Water year start month
            water_year_start_day: Water year start day
            downsample_rule: Downsampling rule applied
            downsample_method: Downsampling method used
            filter_type: Filter type applied
            filter_window: Filter window size
            seasonal_correction: Whether seasonal correction was applied
            validation_method: Cross-validation method used
            total_recharge: Total recharge calculated
            annual_rate: Annual recharge rate
            recharge_events: List of recharge events
            yearly_summaries: List of yearly summaries
            quality_score: Overall quality assessment
            notes: Additional notes
            
        Returns:
            int: Calculation ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Determine calculation period
                calc_start = calc_end = None
                if recharge_events:
                    dates = [event['event_date'] for event in recharge_events]
                    calc_start = min(dates).isoformat() if dates else None
                    calc_end = max(dates).isoformat() if dates else None
                
                # Insert calculation
                cursor.execute("""
                    INSERT INTO erc_calculations (
                        curve_id, well_id, well_name, calculation_date, specific_yield,
                        deviation_threshold, water_year_start_month, water_year_start_day,
                        downsample_rule, downsample_method, filter_type, filter_window,
                        seasonal_correction, validation_method, total_recharge, annual_rate,
                        total_events, calculation_period_start, calculation_period_end,
                        quality_score, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    curve_id, well_id, well_name, datetime.now().isoformat(),
                    specific_yield, deviation_threshold, water_year_start_month,
                    water_year_start_day, downsample_rule, downsample_method,
                    filter_type, filter_window, seasonal_correction, validation_method,
                    total_recharge, annual_rate, len(recharge_events or []),
                    calc_start, calc_end, quality_score, notes
                ))
                
                calc_id = cursor.lastrowid
                
                # Save recharge events
                if recharge_events and calc_id:
                    for event in recharge_events:
                        cursor.execute("""
                            INSERT INTO erc_recharge_events (
                                calculation_id, event_date, water_year, water_level,
                                predicted_level, deviation, recharge_value, event_magnitude,
                                seasonal_period, validation_flag, confidence_score
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            calc_id, event['event_date'].isoformat(), event['water_year'],
                            event['water_level'], event['predicted_level'], event['deviation'],
                            event['recharge_value'], event.get('event_magnitude'),
                            event.get('seasonal_period'), event.get('validation_flag', True),
                            event.get('confidence_score')
                        ))
                
                # Save yearly summaries
                if yearly_summaries and calc_id:
                    for summary in yearly_summaries:
                        cursor.execute("""
                            INSERT INTO erc_yearly_summaries (
                                calculation_id, water_year, total_recharge, num_events,
                                annual_rate, max_deviation, avg_deviation,
                                seasonal_distribution, quality_indicators
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            calc_id, summary['water_year'], summary['total_recharge'],
                            summary['num_events'], summary['annual_rate'],
                            summary['max_deviation'], summary['avg_deviation'],
                            json.dumps(summary.get('seasonal_distribution', {})),
                            json.dumps(summary.get('quality_indicators', {}))
                        ))
                
                conn.commit()
                logger.info(f"Saved ERC calculation {calc_id} for curve {curve_id}")
                return calc_id
                
        except Exception as e:
            logger.error(f"Error saving ERC calculation: {e}", exc_info=True)
            return None
    
    def get_calculations_for_curve(self, curve_id: int) -> List[Dict]:
        """
        Get all calculations for a specific curve.
        
        Args:
            curve_id: Curve identifier
            
        Returns:
            List of calculation dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM erc_calculations 
                    WHERE curve_id = ?
                    ORDER BY calculation_date DESC
                """, (curve_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting ERC calculations for curve {curve_id}: {e}", exc_info=True)
            return []
    
    def get_calculation_details(self, calculation_id: int) -> Optional[Dict]:
        """
        Get detailed information for a specific calculation.
        
        Args:
            calculation_id: Calculation identifier
            
        Returns:
            Dictionary with calculation details including events and summaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get calculation info
                cursor.execute("SELECT * FROM erc_calculations WHERE id = ?", (calculation_id,))
                calc_row = cursor.fetchone()
                if not calc_row:
                    return None
                
                calc_data = dict(calc_row)
                
                # Get recharge events
                cursor.execute("""
                    SELECT * FROM erc_recharge_events 
                    WHERE calculation_id = ?
                    ORDER BY event_date
                """, (calculation_id,))
                calc_data['recharge_events'] = [dict(row) for row in cursor.fetchall()]
                
                # Get yearly summaries
                cursor.execute("""
                    SELECT * FROM erc_yearly_summaries 
                    WHERE calculation_id = ?
                    ORDER BY water_year
                """, (calculation_id,))
                summaries = []
                for row in cursor.fetchall():
                    summary = dict(row)
                    summary['seasonal_distribution'] = json.loads(summary['seasonal_distribution'] or '{}')
                    summary['quality_indicators'] = json.loads(summary['quality_indicators'] or '{}')
                    summaries.append(summary)
                calc_data['yearly_summaries'] = summaries
                
                return calc_data
                
        except Exception as e:
            logger.error(f"Error getting ERC calculation details for {calculation_id}: {e}", exc_info=True)
            return None
    
    def delete_curve(self, curve_id: int) -> bool:
        """
        Delete a curve and all associated data.
        
        Args:
            curve_id: Curve identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete in proper order to maintain referential integrity
                cursor.execute("DELETE FROM erc_yearly_summaries WHERE calculation_id IN (SELECT id FROM erc_calculations WHERE curve_id = ?)", (curve_id,))
                cursor.execute("DELETE FROM erc_recharge_events WHERE calculation_id IN (SELECT id FROM erc_calculations WHERE curve_id = ?)", (curve_id,))
                cursor.execute("DELETE FROM erc_calculations WHERE curve_id = ?", (curve_id,))
                cursor.execute("DELETE FROM erc_temporal_analysis WHERE curve_id = ?", (curve_id,))
                cursor.execute("DELETE FROM erc_recession_segments WHERE curve_id = ?", (curve_id,))
                cursor.execute("DELETE FROM erc_curves WHERE id = ?", (curve_id,))
                
                conn.commit()
                logger.info(f"Deleted ERC curve {curve_id} and all associated data")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting ERC curve {curve_id}: {e}", exc_info=True)
            return False
    
    def save_temporal_analysis(self, curve_id: int, temporal_period: str,
                              period_identifier: str, curve_coefficients: Dict,
                              r_squared: float, segment_count: int,
                              period_start_date: str, period_end_date: str) -> Optional[int]:
        """
        Save temporal analysis results for a curve.
        
        Args:
            curve_id: Associated curve ID
            temporal_period: Type of temporal period ('annual', 'seasonal', 'monthly')
            period_identifier: Specific period identifier
            curve_coefficients: Period-specific coefficients
            r_squared: R² for this period
            segment_count: Number of segments in this period
            period_start_date: Start date of the period
            period_end_date: End date of the period
            
        Returns:
            int: Temporal analysis ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO erc_temporal_analysis (
                        curve_id, temporal_period, period_identifier, curve_coefficients,
                        r_squared, segment_count, period_start_date, period_end_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    curve_id, temporal_period, period_identifier,
                    json.dumps(curve_coefficients), r_squared, segment_count,
                    period_start_date, period_end_date
                ))
                
                analysis_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Saved ERC temporal analysis {analysis_id} for curve {curve_id}")
                return analysis_id
                
        except Exception as e:
            logger.error(f"Error saving ERC temporal analysis: {e}", exc_info=True)
            return None
    
    def get_temporal_analysis(self, curve_id: int) -> List[Dict]:
        """
        Get all temporal analysis results for a curve.
        
        Args:
            curve_id: Curve identifier
            
        Returns:
            List of temporal analysis dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM erc_temporal_analysis 
                    WHERE curve_id = ?
                    ORDER BY temporal_period, period_identifier
                """, (curve_id,))
                
                analyses = []
                for row in cursor.fetchall():
                    analysis = dict(row)
                    analysis['curve_coefficients'] = json.loads(analysis['curve_coefficients'])
                    analyses.append(analysis)
                
                return analyses
                
        except Exception as e:
            logger.error(f"Error getting ERC temporal analysis for curve {curve_id}: {e}", exc_info=True)
            return []