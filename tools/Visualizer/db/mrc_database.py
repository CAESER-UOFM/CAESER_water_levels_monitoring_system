"""
MRC (Master Recession Curve) database management for the water level visualizer.
Handles storage and retrieval of MRC curves and recharge calculations.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MrcDatabase:
    """Database manager for MRC calculations and curves."""
    
    def __init__(self, db_path: str):
        """
        Initialize the MRC database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        logger.info(f"Initializing MRC database at: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def create_tables(self) -> bool:
        """
        Create the MRC database tables if they don't exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Only drop and recreate if tables don't exist or have wrong schema
                # Check if mrc_curves table exists with correct schema
                cursor.execute("""
                    SELECT sql FROM sqlite_master 
                    WHERE type='table' AND name='mrc_curves'
                """)
                result = cursor.fetchone()
                
                needs_recreation = False
                if result:
                    # Check if the schema has the old 'well_id' column
                    if 'well_id' in result[0]:
                        needs_recreation = True
                        logger.info("Found old schema with well_id, will recreate tables")
                else:
                    needs_recreation = True
                    logger.info("MRC tables don't exist, will create them")
                
                if needs_recreation:
                    # Drop and recreate all MRC tables to fix schema issues
                    cursor.execute("DROP TABLE IF EXISTS mrc_yearly_summaries")
                    cursor.execute("DROP TABLE IF EXISTS mrc_recharge_events")
                    cursor.execute("DROP TABLE IF EXISTS mrc_calculations")
                    cursor.execute("DROP TABLE IF EXISTS mrc_recession_segments")
                    cursor.execute("DROP TABLE IF EXISTS mrc_curves")
                    
                    logger.info("Dropped existing MRC tables to recreate with correct schema")
                
                # Create mrc_curves table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mrc_curves (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        well_number TEXT NOT NULL,
                        well_name TEXT NOT NULL,
                        creation_date TEXT NOT NULL,
                        curve_type TEXT NOT NULL,  -- 'exponential', 'power_law', '2-segment'
                        curve_parameters TEXT NOT NULL,  -- JSON with fitting parameters
                        curve_coefficients TEXT NOT NULL,  -- JSON with a, b, intercept, etc.
                        r_squared REAL,
                        data_start_date TEXT,
                        data_end_date TEXT,
                        recession_segments INTEGER,
                        min_recession_length INTEGER,
                        description TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        version INTEGER DEFAULT 1,
                        parent_curve_id INTEGER,  -- For tracking curve updates
                        FOREIGN KEY (parent_curve_id) REFERENCES mrc_curves(id)
                    )
                """)
                
                # Create mrc_calculations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mrc_calculations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        curve_id INTEGER NOT NULL,
                        well_number TEXT NOT NULL,
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
                        total_recharge REAL NOT NULL,
                        annual_rate REAL NOT NULL,
                        data_start_date TEXT,
                        data_end_date TEXT,
                        notes TEXT,
                        FOREIGN KEY (curve_id) REFERENCES mrc_curves(id)
                    )
                """)
                
                # Create mrc_recharge_events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mrc_recharge_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        calculation_id INTEGER NOT NULL,
                        event_date TEXT NOT NULL,
                        water_year TEXT NOT NULL,
                        water_level REAL NOT NULL,
                        predicted_level REAL NOT NULL,
                        deviation REAL NOT NULL,
                        recharge_value REAL NOT NULL,
                        FOREIGN KEY (calculation_id) REFERENCES mrc_calculations(id)
                    )
                """)
                
                # Create mrc_yearly_summaries table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mrc_yearly_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        calculation_id INTEGER NOT NULL,
                        water_year TEXT NOT NULL,
                        total_recharge REAL NOT NULL,
                        num_events INTEGER NOT NULL,
                        annual_rate REAL NOT NULL,
                        max_deviation REAL,
                        avg_deviation REAL,
                        FOREIGN KEY (calculation_id) REFERENCES mrc_calculations(id)
                    )
                """)
                
                # Create recession_segments table for storing identified recession periods
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mrc_recession_segments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        well_number TEXT NOT NULL,
                        curve_id INTEGER,
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        duration_days INTEGER NOT NULL,
                        start_level REAL,
                        end_level REAL,
                        recession_rate REAL NOT NULL,
                        segment_data TEXT,
                        selected BOOLEAN DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (well_number) REFERENCES wells (well_number),
                        FOREIGN KEY (curve_id) REFERENCES mrc_curves(id)
                    )
                """)
                
                # Create indices for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrc_curves_well ON mrc_curves(well_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrc_calculations_curve ON mrc_calculations(curve_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrc_calculations_well ON mrc_calculations(well_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrc_recharge_events_calc ON mrc_recharge_events(calculation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrc_yearly_summaries_calc ON mrc_yearly_summaries(calculation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrc_recession_segments_well ON mrc_recession_segments(well_number)")
                
                conn.commit()
                logger.info("MRC database tables created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error creating MRC tables: {e}")
            return False
    
    def get_segments_for_well(self, well_number: str) -> List[Dict]:
        """Get all recession segments for a specific well."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM mrc_recession_segments 
                    WHERE well_number = ? 
                    ORDER BY start_date DESC
                """, (well_number,))
                
                segments = []
                for row in cursor.fetchall():
                    segment = dict(row)
                    # Parse segment_data JSON if present
                    if segment.get('segment_data'):
                        try:
                            parsed_data = json.loads(segment['segment_data'])
                            segment['segment_data'] = parsed_data
                            logger.debug(f"Successfully parsed segment_data: {type(parsed_data)}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse segment_data JSON: {e}")
                            logger.warning(f"Raw segment_data: {segment['segment_data'][:100]}...")
                            segment['segment_data'] = None
                        except Exception as e:
                            logger.warning(f"Unexpected error parsing segment_data: {e}")
                            segment['segment_data'] = None
                    segments.append(segment)
                
                return segments
        except Exception as e:
            logger.error(f"Error retrieving segments for well {well_number}: {e}")
            return []
    
    def clear_segments_for_well(self, well_number: str) -> bool:
        """Clear all segments for a well (useful for regenerating with new format)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM mrc_recession_segments WHERE well_number = ?", (well_number,))
                conn.commit()
                logger.info(f"Cleared all segments for well {well_number}")
                return True
        except Exception as e:
            logger.error(f"Error clearing segments for well {well_number}: {e}")
            return False
    
    def get_segments_for_curve(self, curve_id: int) -> List[Dict]:
        """Get all recession segments for a specific curve."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM mrc_recession_segments 
                    WHERE curve_id = ? 
                    ORDER BY start_date ASC
                """, (curve_id,))
                
                segments = []
                rows = cursor.fetchall()
                none_count = 0
                
                for row in rows:
                    segment = dict(row)
                    # Debug: check what the raw segment_data looks like
                    raw_segment_data = segment.get('segment_data')
                    if raw_segment_data is None:
                        none_count += 1
                        logger.debug(f"Segment {segment.get('id', 'unknown')} has None segment_data")
                    else:
                        logger.debug(f"Segment {segment.get('id', 'unknown')} has segment_data type: {type(raw_segment_data)}")
                    
                    # Parse segment_data JSON if present
                    if segment.get('segment_data'):
                        try:
                            parsed_data = json.loads(segment['segment_data'])
                            segment['segment_data'] = parsed_data
                            logger.debug(f"Successfully parsed segment_data for curve {curve_id}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse segment_data JSON for curve {curve_id}: {e}")
                            segment['segment_data'] = None
                        except Exception as e:
                            logger.warning(f"Unexpected error parsing segment_data for curve {curve_id}: {e}")
                            segment['segment_data'] = None
                    segments.append(segment)
                
                if none_count > 0:
                    logger.warning(f"Found {none_count} out of {len(rows)} segments with None segment_data for curve {curve_id}")
                
                logger.info(f"Retrieved {len(segments)} segments for curve {curve_id}")
                return segments
        except Exception as e:
            logger.error(f"Error retrieving segments for curve {curve_id}: {e}")
            return []
    
    def get_all_segments_for_well(self, well_number: str) -> List[Dict]:
        """Get all segments from all curves for a specific well for dropdown population."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        s.curve_id,
                        c.creation_date,
                        c.curve_type,
                        c.description,
                        COUNT(s.id) as segment_count,
                        c.r_squared
                    FROM mrc_recession_segments s
                    JOIN mrc_curves c ON s.curve_id = c.id
                    WHERE s.well_number = ? AND c.is_active = 1
                    GROUP BY s.curve_id, c.creation_date, c.curve_type, c.description, c.r_squared
                    ORDER BY c.creation_date DESC
                """, (well_number,))
                
                segment_sets = []
                for row in cursor.fetchall():
                    segment_set = {
                        'curve_id': row['curve_id'],
                        'creation_date': row['creation_date'],
                        'curve_type': row['curve_type'],
                        'description': row['description'],
                        'segment_count': row['segment_count'],
                        'r_squared': row['r_squared']
                    }
                    segment_sets.append(segment_set)
                
                logger.info(f"Retrieved {len(segment_sets)} segment sets for well {well_number}")
                return segment_sets
        except Exception as e:
            logger.error(f"Error retrieving segment sets for well {well_number}: {e}")
            return []
    
    def delete_curves_and_segments(self, curve_ids: List[int]) -> bool:
        """Delete curves and their associated segments (cascade delete)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for curve_id in curve_ids:
                    # Delete segments first (foreign key constraint)
                    cursor.execute("DELETE FROM mrc_recession_segments WHERE curve_id = ?", (curve_id,))
                    # Delete curve
                    cursor.execute("DELETE FROM mrc_curves WHERE id = ?", (curve_id,))
                
                conn.commit()
                logger.info(f"Deleted {len(curve_ids)} curves and their associated segments")
                return True
        except Exception as e:
            logger.error(f"Error deleting curves and segments: {e}")
            return False
    
    def save_segments_for_well(self, well_number: str, segments: List[Dict]) -> bool:
        """Save recession segments for a well."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear existing segments for this well
                cursor.execute("DELETE FROM mrc_recession_segments WHERE well_number = ?", (well_number,))
                
                # Insert new segments
                for segment in segments:
                    # Convert DataFrame to JSON-serializable format
                    data = segment.get('data')
                    if data is not None and hasattr(data, 'to_dict'):
                        # Convert DataFrame to dictionary format that can be reconstructed
                        # Handle datetime columns properly
                        data_copy = data.copy()
                        for col in data_copy.columns:
                            if data_copy[col].dtype.name.startswith('datetime'):
                                data_copy[col] = data_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                        segment_data_json = json.dumps(data_copy.to_dict('records'))
                    else:
                        segment_data_json = json.dumps(data) if data else None
                    
                    cursor.execute("""
                        INSERT INTO mrc_recession_segments 
                        (well_number, start_date, end_date, duration_days, recession_rate, 
                         segment_data, selected, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        well_number,
                        segment['start_date'].strftime('%Y-%m-%d') if hasattr(segment['start_date'], 'strftime') else str(segment['start_date']),
                        segment['end_date'].strftime('%Y-%m-%d') if hasattr(segment['end_date'], 'strftime') else str(segment['end_date']),
                        segment.get('duration_days', 0),
                        segment.get('recession_rate', 0.0),
                        segment_data_json,
                        segment.get('selected', True),
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                logger.info(f"Saved {len(segments)} recession segments for well {well_number}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving segments for well {well_number}: {e}")
            return False
    
    def check_segments_exist(self, well_number: str) -> bool:
        """Check if segments exist for a well."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM mrc_recession_segments WHERE well_number = ?", (well_number,))
                result = cursor.fetchone()
                return result['count'] > 0 if result else False
        except Exception as e:
            logger.error(f"Error checking segments for well {well_number}: {e}")
            return False

    def save_curve(self, **kwargs) -> Optional[int]:
        """
        Save a new MRC curve to the database.
        
        Returns:
            Optional[int]: The ID of the saved curve, or None if failed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert dictionaries to JSON strings
                curve_parameters = json.dumps(kwargs.get('curve_parameters', {}))
                curve_coefficients = json.dumps(kwargs.get('curve_coefficients', {}))
                
                cursor.execute("""
                    INSERT INTO mrc_curves (
                        well_number, well_name, creation_date, curve_type,
                        curve_parameters, curve_coefficients, r_squared,
                        data_start_date, data_end_date, recession_segments,
                        min_recession_length, description, version, parent_curve_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs['well_number'],
                    kwargs['well_name'],
                    datetime.now().isoformat(),
                    kwargs['curve_type'],
                    curve_parameters,
                    curve_coefficients,
                    kwargs.get('r_squared'),
                    kwargs.get('data_start_date'),
                    kwargs.get('data_end_date'),
                    kwargs.get('recession_segments', 0),
                    kwargs.get('min_recession_length', 10),
                    kwargs.get('description', ''),
                    kwargs.get('version', 1),
                    kwargs.get('parent_curve_id')
                ))
                
                curve_id = cursor.lastrowid
                
                # Save recession segments if provided
                if 'recession_segments_data' in kwargs:
                    for segment in kwargs['recession_segments_data']:
                        # Handle segment data serialization if present
                        segment_data_json = None
                        if 'data' in segment and segment['data'] is not None:
                            data = segment['data']
                            if hasattr(data, 'to_dict'):
                                # Convert DataFrame to dictionary format that can be reconstructed
                                data_copy = data.copy()
                                for col in data_copy.columns:
                                    if data_copy[col].dtype.name.startswith('datetime'):
                                        data_copy[col] = data_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                                segment_data_json = json.dumps(data_copy.to_dict('records'))
                            else:
                                segment_data_json = json.dumps(data)
                                
                        cursor.execute("""
                            INSERT INTO mrc_recession_segments (
                                well_number, curve_id, start_date, end_date, duration_days,
                                start_level, end_level, recession_rate, segment_data, selected
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            kwargs['well_number'],
                            curve_id,
                            segment['start_date'],
                            segment['end_date'],
                            segment['duration_days'],
                            segment['start_level'],
                            segment['end_level'],
                            segment['recession_rate'],
                            segment_data_json,
                            segment.get('selected', True)
                        ))
                
                conn.commit()
                logger.info(f"Saved MRC curve with ID: {curve_id}")
                return curve_id
                
        except Exception as e:
            logger.error(f"Error saving MRC curve: {e}")
            return None
    
    def get_curves_for_well(self, well_number: str) -> List[Dict[str, Any]]:
        """
        Get all MRC curves for a specific well.
        
        Args:
            well_number: The well identifier
            
        Returns:
            List of curve dictionaries
        """
        try:
            logger.info(f"[CURVE_LOAD_DEBUG] Searching for curves with well_number = '{well_number}'")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, let's see what wells are actually in the database
                cursor.execute("SELECT DISTINCT well_number FROM mrc_curves")
                existing_wells = [row[0] for row in cursor.fetchall()]
                logger.info(f"[CURVE_LOAD_DEBUG] Wells in database: {existing_wells}")
                
                cursor.execute("""
                    SELECT id, creation_date, curve_type, r_squared,
                           description, version, is_active,
                           data_start_date, data_end_date,
                           recession_segments, well_number
                    FROM mrc_curves
                    WHERE well_number = ? AND is_active = 1
                    ORDER BY creation_date DESC
                """, (well_number,))
                
                curves = []
                rows = cursor.fetchall()
                logger.info(f"[CURVE_LOAD_DEBUG] Found {len(rows)} rows from query")
                
                for i, row in enumerate(rows):
                    logger.info(f"[CURVE_LOAD_DEBUG] Row {i}: {dict(row)}")
                    curves.append({
                        'id': row['id'],
                        'creation_date': row['creation_date'],
                        'curve_type': row['curve_type'],
                        'r_squared': row['r_squared'],
                        'description': row['description'],
                        'version': row['version'],
                        'data_start_date': row['data_start_date'],
                        'data_end_date': row['data_end_date'],
                        'recession_segments': row['recession_segments']
                    })
                
                logger.info(f"[CURVE_LOAD_DEBUG] Returning {len(curves)} curves")
                return curves
                
        except Exception as e:
            logger.error(f"Error getting curves for well {well_number}: {e}")
            return []
    
    def get_curve_details(self, curve_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific curve.
        
        Args:
            curve_id: The curve ID
            
        Returns:
            Dictionary with curve details, or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM mrc_curves WHERE id = ?", (curve_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Convert row to dictionary
                curve_data = dict(row)
                
                # Parse JSON fields
                curve_data['curve_parameters'] = json.loads(curve_data['curve_parameters'])
                curve_data['curve_coefficients'] = json.loads(curve_data['curve_coefficients'])
                
                # Get recession segments
                cursor.execute("""
                    SELECT * FROM mrc_recession_segments
                    WHERE curve_id = ?
                    ORDER BY start_date
                """, (curve_id,))
                
                segments = []
                for seg_row in cursor.fetchall():
                    segments.append(dict(seg_row))
                
                curve_data['recession_segments_data'] = segments
                
                return curve_data
                
        except Exception as e:
            logger.error(f"Error getting curve details for ID {curve_id}: {e}")
            return None
    
    def save_calculation(self, **kwargs) -> Optional[int]:
        """
        Save an MRC recharge calculation to the database.
        
        Returns:
            Optional[int]: The ID of the saved calculation, or None if failed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert main calculation record
                cursor.execute("""
                    INSERT INTO mrc_calculations (
                        curve_id, well_number, well_name, calculation_date,
                        specific_yield, deviation_threshold,
                        water_year_start_month, water_year_start_day,
                        downsample_rule, downsample_method,
                        filter_type, filter_window,
                        total_recharge, annual_rate,
                        data_start_date, data_end_date, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs['curve_id'],
                    kwargs['well_number'],
                    kwargs['well_name'],
                    datetime.now().isoformat(),
                    kwargs['specific_yield'],
                    kwargs['deviation_threshold'],
                    kwargs['water_year_start_month'],
                    kwargs['water_year_start_day'],
                    kwargs.get('downsample_rule'),
                    kwargs.get('downsample_method'),
                    kwargs.get('filter_type'),
                    kwargs.get('filter_window'),
                    kwargs['total_recharge'],
                    kwargs['annual_rate'],
                    kwargs.get('data_start_date'),
                    kwargs.get('data_end_date'),
                    kwargs.get('notes', '')
                ))
                
                calculation_id = cursor.lastrowid
                
                # Insert recharge events
                if 'recharge_events' in kwargs:
                    for event in kwargs['recharge_events']:
                        cursor.execute("""
                            INSERT INTO mrc_recharge_events (
                                calculation_id, event_date, water_year,
                                water_level, predicted_level, deviation,
                                recharge_value
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            calculation_id,
                            event['event_date'],
                            event['water_year'],
                            event['water_level'],
                            event['predicted_level'],
                            event['deviation'],
                            event['recharge_value']
                        ))
                
                # Insert yearly summaries
                if 'yearly_summaries' in kwargs:
                    for summary in kwargs['yearly_summaries']:
                        cursor.execute("""
                            INSERT INTO mrc_yearly_summaries (
                                calculation_id, water_year, total_recharge,
                                num_events, annual_rate, max_deviation, avg_deviation
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            calculation_id,
                            summary['water_year'],
                            summary['total_recharge'],
                            summary['num_events'],
                            summary['annual_rate'],
                            summary.get('max_deviation'),
                            summary.get('avg_deviation')
                        ))
                
                conn.commit()
                logger.info(f"Saved MRC calculation with ID: {calculation_id}")
                return calculation_id
                
        except Exception as e:
            logger.error(f"Error saving MRC calculation: {e}")
            return None
    
    def get_calculations_for_curve(self, curve_id: int) -> List[Dict[str, Any]]:
        """
        Get all calculations that used a specific curve.
        
        Args:
            curve_id: The curve ID
            
        Returns:
            List of calculation dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT c.*, 
                           COUNT(DISTINCT e.id) as event_count
                    FROM mrc_calculations c
                    LEFT JOIN mrc_recharge_events e ON c.id = e.calculation_id
                    WHERE c.curve_id = ?
                    GROUP BY c.id
                    ORDER BY c.calculation_date DESC
                """, (curve_id,))
                
                calculations = []
                for row in cursor.fetchall():
                    calc_dict = dict(row)
                    calculations.append(calc_dict)
                
                return calculations
                
        except Exception as e:
            logger.error(f"Error getting calculations for curve {curve_id}: {e}")
            return []
    
    def get_calculation_details(self, calculation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific calculation.
        
        Args:
            calculation_id: The calculation ID
            
        Returns:
            Dictionary with calculation details, or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get main calculation data
                cursor.execute("SELECT * FROM mrc_calculations WHERE id = ?", (calculation_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                calc_data = dict(row)
                
                # Get recharge events
                cursor.execute("""
                    SELECT * FROM mrc_recharge_events
                    WHERE calculation_id = ?
                    ORDER BY event_date
                """, (calculation_id,))
                
                events = []
                for event_row in cursor.fetchall():
                    events.append(dict(event_row))
                
                calc_data['recharge_events'] = events
                
                # Get yearly summaries
                cursor.execute("""
                    SELECT * FROM mrc_yearly_summaries
                    WHERE calculation_id = ?
                    ORDER BY water_year
                """, (calculation_id,))
                
                summaries = []
                for summary_row in cursor.fetchall():
                    summaries.append(dict(summary_row))
                
                calc_data['yearly_summaries'] = summaries
                
                return calc_data
                
        except Exception as e:
            logger.error(f"Error getting calculation details for ID {calculation_id}: {e}")
            return None
    
    def update_curve_version(self, old_curve_id: int, new_curve_id: int) -> bool:
        """
        Update curve versioning when a curve is recalculated.
        
        Args:
            old_curve_id: The ID of the previous curve version
            new_curve_id: The ID of the new curve version
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Deactivate old curve
                cursor.execute("""
                    UPDATE mrc_curves
                    SET is_active = 0
                    WHERE id = ?
                """, (old_curve_id,))
                
                # Update new curve's parent reference
                cursor.execute("""
                    UPDATE mrc_curves
                    SET parent_curve_id = ?
                    WHERE id = ?
                """, (old_curve_id, new_curve_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating curve version: {e}")
            return False
    
    def compare_curves(self, curve_ids: List[int]) -> Dict[str, Any]:
        """
        Compare multiple curves and their statistics.
        
        Args:
            curve_ids: List of curve IDs to compare
            
        Returns:
            Dictionary with comparison data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                comparison_data = {'curves': []}
                
                for curve_id in curve_ids:
                    # Get curve details
                    curve_data = self.get_curve_details(curve_id)
                    if curve_data:
                        # Get calculation statistics for this curve
                        cursor.execute("""
                            SELECT 
                                COUNT(*) as calculation_count,
                                AVG(total_recharge) as avg_recharge,
                                MIN(total_recharge) as min_recharge,
                                MAX(total_recharge) as max_recharge,
                                AVG(annual_rate) as avg_annual_rate
                            FROM mrc_calculations
                            WHERE curve_id = ?
                        """, (curve_id,))
                        
                        stats = cursor.fetchone()
                        curve_data['statistics'] = dict(stats) if stats else {}
                        
                        comparison_data['curves'].append(curve_data)
                
                return comparison_data
                
        except Exception as e:
            logger.error(f"Error comparing curves: {e}")
            return {'curves': []}
    
    def diagnose_segment_data_issues(self, well_number: str = None) -> Dict[str, Any]:
        """Diagnose segment data issues for debugging."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Base query
                if well_number:
                    query = """
                        SELECT c.id as curve_id, c.well_number, c.creation_date, c.curve_type,
                               COUNT(s.id) as total_segments,
                               COUNT(CASE WHEN s.segment_data IS NULL THEN 1 END) as null_segments,
                               COUNT(CASE WHEN s.segment_data IS NOT NULL THEN 1 END) as valid_segments
                        FROM mrc_curves c
                        LEFT JOIN mrc_recession_segments s ON c.id = s.curve_id
                        WHERE c.well_number = ? AND c.is_active = 1
                        GROUP BY c.id, c.well_number, c.creation_date, c.curve_type
                        ORDER BY c.creation_date DESC
                    """
                    cursor.execute(query, (well_number,))
                else:
                    query = """
                        SELECT c.id as curve_id, c.well_number, c.creation_date, c.curve_type,
                               COUNT(s.id) as total_segments,
                               COUNT(CASE WHEN s.segment_data IS NULL THEN 1 END) as null_segments,
                               COUNT(CASE WHEN s.segment_data IS NOT NULL THEN 1 END) as valid_segments
                        FROM mrc_curves c
                        LEFT JOIN mrc_recession_segments s ON c.id = s.curve_id
                        WHERE c.is_active = 1
                        GROUP BY c.id, c.well_number, c.creation_date, c.curve_type
                        ORDER BY c.creation_date DESC
                    """
                    cursor.execute(query)
                
                curves_info = []
                for row in cursor.fetchall():
                    curve_info = dict(row)
                    curve_info['has_issues'] = curve_info['null_segments'] > 0
                    curves_info.append(curve_info)
                
                # Summary statistics
                total_curves = len(curves_info)
                curves_with_issues = len([c for c in curves_info if c['has_issues']])
                total_segments = sum(c['total_segments'] for c in curves_info)
                null_segments = sum(c['null_segments'] for c in curves_info)
                
                return {
                    'curves': curves_info,
                    'summary': {
                        'total_curves': total_curves,
                        'curves_with_issues': curves_with_issues,
                        'total_segments': total_segments,
                        'null_segments': null_segments,
                        'percent_null': (null_segments / total_segments * 100) if total_segments > 0 else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Error diagnosing segment data issues: {e}")
            return {'curves': [], 'summary': {}}