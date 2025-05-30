"""
Handler for water level plotting functionality.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.backend_bases import MouseButton
import matplotlib.dates as mdates
import pandas as pd
import sqlite3
from typing import Dict, List, Optional, Tuple
import logging
from datetime import timedelta
import numpy as np

logger = logging.getLogger(__name__)

class WaterLevelPlotHandler:
    def __init__(self, figure: Figure, canvas: FigureCanvasQTAgg):
        self.figure = figure
        self.canvas = canvas
        self.selected_point_annotation = None
        self.show_temperature = False
        self.gap_highlight_enabled = True  # Flag to enable/disable gap highlighting
        self.gap_color = "#FFEBEE"  # Light red background for gaps
        self.gap_threshold = timedelta(minutes=20)  # Gap threshold (> 15 min sample interval)
        self.gap_alpha = 0.6  # Increased opacity (reduced transparency) from 0.3 to 0.6
        self.setup_plot_interaction()

    def setup_plot_interaction(self):
        """Set up interactive features for the plot"""
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
    
    def clear_plot(self):
        """Clear the current plot."""
        self.figure.clear()
        self.selected_point_annotation = None
    
    def add_axes(self):
        """Add axes to the plot."""
        self.ax = self.figure.add_subplot(111)

    def color_cycle(self):
        """Return an iterator over a list of colors."""
        import itertools
        return itertools.cycle(['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'])

    def identify_data_gaps(self, df: pd.DataFrame) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
        """
        Identify gaps in time series data where the interval between samples exceeds the threshold.
        
        Args:
            df: DataFrame with a 'timestamp_utc' column
            
        Returns:
            List of (start_time, end_time) tuples representing gaps
        """
        if df is None or df.empty or 'timestamp_utc' not in df.columns:
            return []
            
        # Sort by timestamp to ensure chronological order
        sorted_df = df.sort_values('timestamp_utc').reset_index(drop=True)
        
        # Calculate time differences between consecutive points
        time_diffs = sorted_df['timestamp_utc'].diff()
        
        # Find indices where the time difference exceeds the threshold
        gap_indices = time_diffs[time_diffs > self.gap_threshold].index.tolist()
        
        gaps = []
        for idx in gap_indices:
            gap_start = sorted_df.loc[idx-1, 'timestamp_utc']
            gap_end = sorted_df.loc[idx, 'timestamp_utc']
            gaps.append((gap_start, gap_end))
            
        return gaps
    
    def highlight_data_gaps(self, gaps: List[Tuple[pd.Timestamp, pd.Timestamp]], y_min: float, y_max: float):
        """
        Add background highlighting for data gaps.
        
        Args:
            gaps: List of (start_time, end_time) tuples representing gaps
            y_min: Minimum y value for the plot
            y_max: Maximum y value for the plot
        """
        if not gaps or not self.gap_highlight_enabled:
            return
            
        for gap_start, gap_end in gaps:
            # Add a rectangle spanning the gap with a distinctive color
            rect = plt.Rectangle(
                (mdates.date2num(gap_start), y_min),
                mdates.date2num(gap_end) - mdates.date2num(gap_start),
                y_max - y_min,
                color=self.gap_color,
                alpha=self.gap_alpha,  # Use the opacity from class variable
                zorder=-100  # Place behind other plot elements
            )
            self.ax.add_patch(rect)
            
            # Removed the text label code for gap duration

    def update_plot(self, well_numbers, water_level_model, db_path):
        """Update the plot with the given well numbers."""
        try:
            if not well_numbers:
                self.clear_plot()
                return

            self.clear_plot()
            self.add_axes()

            # Create color cycle for multiple wells
            colors = self.color_cycle()
            
            # Track whether we have any plottable data
            has_plottable_data = False
            
            # Track all data ranges for proper scaling
            all_times = []
            all_levels = []
            manual_times = []
            manual_levels = []
            transducer_times = []
            transducer_levels = []
            
            legend_handles = []
            legend_labels = []
            
            # Track data gaps for all wells
            all_gaps = []

            # Plot each well
            for i, well_number in enumerate(well_numbers):
                color = next(colors)

                # Plot line data (transducer or telemetry) if available
                df = water_level_model.get_readings(well_number)
                if df is not None and not df.empty:
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    
                    # Identify gaps in this well's data
                    if not self.show_temperature:
                        gaps = self.identify_data_gaps(df)
                        all_gaps.extend(gaps)
                    
                    if self.show_temperature:
                        line, = self.ax.plot(
                            df['timestamp_utc'], df['temperature'],
                            color=color, label=f"{well_number}", linewidth=1.5
                        )
                    else:
                        line, = self.ax.plot(
                            df['timestamp_utc'], df['water_level'],
                            color=color, label=f"{well_number}", linewidth=1.5
                        )
                        # Collect transducer data for scaling
                        transducer_times.extend(df['timestamp_utc'].tolist())
                        transducer_levels.extend(df['water_level'].tolist())
                        all_times.extend(df['timestamp_utc'].tolist())
                        all_levels.extend(df['water_level'].tolist())
                    
                    legend_handles.append(line)
                    legend_labels.append(f"{well_number}")
                    has_plottable_data = True

                # Plot manual measurements (always, regardless of df)
                manual_df = self.get_manual_readings(well_number, db_path)
                if manual_df is not None and not manual_df.empty and not self.show_temperature:
                    manual_df['measurement_date_utc'] = pd.to_datetime(manual_df['measurement_date_utc'])
                    # collect for manual-only scaling
                    manual_times.extend(manual_df['measurement_date_utc'].tolist())
                    manual_levels.extend(manual_df['water_level'].tolist())
                    # Add to combined data for overall scaling
                    all_times.extend(manual_df['measurement_date_utc'].tolist())
                    all_levels.extend(manual_df['water_level'].tolist())
                    
                    scatter = self.ax.scatter(
                        manual_df['measurement_date_utc'], manual_df['water_level'],
                        color=color, marker='o', s=50, alpha=0.9,
                        edgecolor='black', linewidth=1.2, zorder=10
                    )
                    legend_handles.append(scatter)
                    legend_labels.append(f"{well_number} (Manual)")
                    has_plottable_data = True

            # Set axis labels and title
            if self.show_temperature:
                self.ax.set_ylabel('Temperature (°C)')
                self.ax.set_title('Well Temperature Data')
            else:
                self.ax.set_ylabel('Water Level (ft)')
                self.ax.set_title('Well Water Level Data')

            self.ax.set_xlabel('Date/Time (UTC)')
            
            # Add grid
            self.ax.grid(True, linestyle='--', alpha=0.7)
            
            # Set appropriate plot scaling based on available data
            if all_times:
                # We have some data (either manual, transducer, or both)
                x_min = min(all_times)
                x_max = max(all_times)
                
                # Set x limits
                self.ax.set_xlim(x_min, x_max)
                
                # Y-axis scaling needs to consider both datasets
                if all_levels:
                    y_min = min(all_levels)
                    y_max = max(all_levels)
                    
                    # Add a margin
                    margin = (y_max - y_min) * 0.1 if (y_max > y_min) else 1.0
                    y_min_plot = y_min - margin
                    y_max_plot = y_max + margin
                    self.ax.set_ylim(y_min_plot, y_max_plot)
                    
                    # Highlight data gaps (only for water level plots)
                    if not self.show_temperature and all_gaps:
                        self.highlight_data_gaps(all_gaps, y_min_plot, y_max_plot)
                else:
                    # Fallback if somehow we have no levels
                    self.ax.relim()
                    self.ax.autoscale_view(scaley=True)
            else:
                # No data at all - use default autoscale
                self.ax.relim()
                self.ax.autoscale_view()
            
            # Format dates on x-axis
            self.format_date_axis()
            
            # Add legend only if we have items to show
            if has_plottable_data and legend_handles:
                legend = self.ax.legend(handles=legend_handles, labels=legend_labels, loc='best')
                legend.set_draggable(True)  # Make the legend draggable
                
            # Create a custom legend entry for gaps
            if all_gaps and not self.show_temperature:
                from matplotlib.patches import Patch
                gap_patch = Patch(facecolor=self.gap_color, alpha=self.gap_alpha, label='Data Gaps (>20min)')
                
                # Fix: Get existing legend handles and labels properly
                if self.ax.get_legend():
                    # Use the existing legend handles and labels
                    handles, labels = self.ax.get_legend_handles_labels()
                    
                    # Add gap patch
                    handles.append(gap_patch)
                    labels.append('Data Gaps (>20min)')
                    
                    # Create new legend with all items and make it draggable
                    legend = self.ax.legend(handles=handles, labels=labels, loc='best')
                    legend.set_draggable(True)
                else:
                    # No existing legend, just create one with the gap patch
                    legend = self.ax.legend(handles=[gap_patch], labels=['Data Gaps (>20min)'], loc='best')
                    legend.set_draggable(True)
                
            # Adjust layout to prevent labels from being cut off
            self.figure.tight_layout()
            
            # Update canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            self.clear_plot()
            self.add_axes()
            self.ax.text(0.5, 0.5, f"Error: {str(e)}",
                       ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()

    def on_plot_click(self, event):
        """Handle click events on plot"""
        if event.inaxes is None or event.button != MouseButton.LEFT:
            return
            
        if self.selected_point_annotation:
            self.selected_point_annotation.remove()
            self.selected_point_annotation = None
            
        ax = event.inaxes
        min_dist = float('inf')
        closest_point = None
        closest_well = None
        closest_line = None
        
        for line in ax.get_lines():
            if not line.get_label().startswith('Well') and not line.get_label().startswith('Water Level'):
                continue
                
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            
            x_pixels = ax.transData.transform(list(zip(xdata, ydata)))[:, 0]
            y_pixels = ax.transData.transform(list(zip(xdata, ydata)))[:, 1]
            click_pixels = ax.transData.transform((event.xdata, event.ydata))
            
            distances = ((x_pixels - click_pixels[0])**2 + (y_pixels - click_pixels[1])**2)
            
            idx = distances.argmin()
            dist = distances[idx]
            
            if dist < min_dist:
                min_dist = dist
                closest_point = (xdata[idx], ydata[idx])
                closest_well = line.get_label()
                closest_line = line
        
        if closest_point and min_dist < 50:
            temp_text = ""
            if len(ax.get_lines()) <= 2 and self.show_temperature:  # Single well with possible temperature
                for line in ax.get_lines():
                    if line.get_label() == 'Temperature':
                        temp_idx = (abs(line.get_xdata() - closest_point[0])).argmin()
                        temp = line.get_ydata()[temp_idx]
                        temp_text = f"\nTemperature: {temp:.2f}°C"
            
            # Get data source from label
            data_source = closest_well.split('(')[-1].rstrip(')')
            
            text = (f"{closest_well}\n"
                   f"Date: {closest_point[0].strftime('%Y-%m-%d %H:%M')} UTC\n"
                   f"Level: {closest_point[1]:.2f} ft\n"
                   f"Source: {data_source}{temp_text}")
            
            self.selected_point_annotation = ax.annotate(
                text,
                xy=closest_point,
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
            
            self.canvas.draw()

    def toggle_temperature(self, show: bool):
        """Toggle temperature display"""
        self.show_temperature = show

    def get_manual_readings(self, well_number: str, db_path: str) -> pd.DataFrame:
        """Get manual readings from database."""
        try:
            with sqlite3.connect(db_path) as conn:
                query = """
                    SELECT measurement_date_utc, water_level
                    FROM manual_level_readings
                    WHERE well_number = ?
                    ORDER BY measurement_date_utc
                """
                df = pd.read_sql_query(query, conn, params=(well_number,))
                if not df.empty:
                    df['measurement_date_utc'] = pd.to_datetime(df['measurement_date_utc'])
                return df
        except Exception as e:
            logger.error(f"Error getting manual readings: {e}")
            return pd.DataFrame()

    def format_date_axis(self):
        """Format the date axis."""
        # Set the format of the x-axis to show dates nicely
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # Set the major locator to auto adjust based on the date range
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # Rotate the x-axis labels for better readability
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')

    def _get_well_info(self, well_number: str, db_path: str) -> Dict:
        """Get well information from database"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM wells WHERE well_number = ?", (well_number,))
                result = cursor.fetchone()
                if result:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"Error getting well info: {e}")
        return None 

    def get_plot_data(self, selected_wells, water_level_model, db_path, well_handler=None, include_master_baro=False):
        """
        Get data for plotting, separated by data type.
        This function is designed for a single well selection.
        
        OPTIMIZATION: Master barometric data is only fetched when explicitly requested using
        include_master_baro=True. This significantly improves performance for normal plotting
        operations where master baro data isn't needed.
        
        Args:
            selected_wells: List containing a single well number
            water_level_model: Database model for water level operations
            db_path: Path to the SQLite database
            well_handler: Optional well data handler for additional well info
            include_master_baro: Whether to fetch master barometric data (defaults to False)
            
        Returns:
            Dictionary containing separate DataFrames for different data types
        """
        try:
            if not selected_wells:
                return None
            
            # We expect only one well for the edit dialog
            well_number = selected_wells[0]
            logger.debug(f"Getting plot data for well: {well_number}")
            
            # Create empty DataFrames
            transducer_data = pd.DataFrame()
            manual_data = pd.DataFrame()
            master_baro_data = pd.DataFrame()
            
            # Connect to database directly for better query control
            conn = sqlite3.connect(db_path)
            
            # First determine the well's data source
            cursor = conn.cursor()
            cursor.execute("""
                SELECT data_source FROM wells 
                WHERE well_number = ?
            """, (well_number,))
            
            result = cursor.fetchone()
            data_source = result[0] if result else 'transducer'  # Default to transducer
            logger.debug(f"Well {well_number} has data source: {data_source}")
            
            # Fetch appropriate data based on data source
            if data_source == 'telemetry':
                # Get telemetry readings
                telemetry_query = """
                    SELECT t.*,
                           'telemetry' as source_type,
                           'standard' as baro_flag,
                           'telemetry' as level_flag
                    FROM telemetry_level_readings t
                    WHERE t.well_number = ?
                    ORDER BY t.julian_timestamp
                """
                transducer_data = pd.read_sql_query(telemetry_query, conn, params=(well_number,))
            else:
                # Get transducer readings
                transducer_query = """
                    SELECT r.*, wells.cae_number as cae
                    FROM water_level_readings r
                    JOIN wells ON r.well_number = wells.well_number
                    WHERE r.well_number = ?
                    ORDER BY r.julian_timestamp
                """
                transducer_data = pd.read_sql_query(transducer_query, conn, params=(well_number,))
            
            # Add correction columns if they don't exist
            if not transducer_data.empty:
                transducer_data['timestamp_utc'] = pd.to_datetime(transducer_data['timestamp_utc'])
                
                # Add computed columns for corrections
                if 'water_level_master_corrected' not in transducer_data.columns:
                    transducer_data['water_level_master_corrected'] = transducer_data['water_level']
                
                if 'water_level_level_corrected' not in transducer_data.columns:
                    transducer_data['water_level_level_corrected'] = transducer_data['water_level']
                
                if 'water_level_spike_corrected' not in transducer_data.columns:
                    transducer_data['water_level_spike_corrected'] = transducer_data['water_level']
                
                # For compatibility with existing code
                if 'corrected_water_level_level' not in transducer_data.columns:
                    transducer_data['corrected_water_level_level'] = transducer_data['water_level']
                
                if 'baro_compensated_level' not in transducer_data.columns:
                    transducer_data['baro_compensated_level'] = transducer_data['water_level']
                
                # Add spike flag if it doesn't exist
                if 'spike_flag' not in transducer_data.columns:
                    transducer_data['spike_flag'] = 'none'
                
                # Only get master baro data for transducer wells when explicitly requested
                if include_master_baro and data_source != 'telemetry':
                    # Get time range for master baro data
                    min_date = transducer_data['timestamp_utc'].min()
                    max_date = transducer_data['timestamp_utc'].max()
                    
                    # Convert datetime objects to string format for SQLite
                    min_date_str = min_date.strftime('%Y-%m-%d %H:%M:%S')
                    max_date_str = max_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Get master barometric data from master_baro_readings
                    master_baro_query = """
                        SELECT timestamp_utc, pressure
                        FROM master_baro_readings
                        WHERE timestamp_utc BETWEEN ? AND ?
                        ORDER BY julian_timestamp
                    """
                    master_baro_data = pd.read_sql_query(master_baro_query, conn, params=(min_date_str, max_date_str))
                    
                    if not master_baro_data.empty:
                        master_baro_data['timestamp_utc'] = pd.to_datetime(master_baro_data['timestamp_utc'])
                        logger.debug(f"Retrieved {len(master_baro_data)} master barometric readings")
                    else:
                        logger.debug("No master barometric data found for the time range")
            
            # Get manual readings (common for all data sources)
            manual_query = """
                SELECT well_number, measurement_date_utc, water_level, data_source
                FROM manual_level_readings
                WHERE well_number = ?
                ORDER BY measurement_date_utc
            """
            manual_data = pd.read_sql_query(manual_query, conn, params=(well_number,))
            
            if not manual_data.empty:
                manual_data['timestamp_utc'] = pd.to_datetime(manual_data['measurement_date_utc'])
            
            # Close connection
            conn.close()
            
            logger.debug(f"Retrieved data for well {well_number}: "
                        f"{len(transducer_data)} readings, "
                        f"{len(manual_data)} manual readings")
            
            # Return dictionary of separated data
            return {
                'transducer_data': transducer_data,
                'manual_data': manual_data,
                'master_baro_data': master_baro_data
            }
        
        except Exception as e:
            logger.error(f"Error getting plot data: {e}", exc_info=True)
            return None

    def toggle_gap_highlighting(self, enabled: bool):
        """Enable or disable the gap highlighting feature"""
        self.gap_highlight_enabled = enabled