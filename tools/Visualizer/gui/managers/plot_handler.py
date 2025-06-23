from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backend_bases import MouseButton
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal, Qt
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import sqlite3
import os
import traceback
import json
import shutil

logger = logging.getLogger(__name__)

class PlotHandler(QObject):
    """Handles all plotting functionality for the water level visualizer."""
    
    # Signals
    plot_updated = pyqtSignal()  # Emitted when the plot is updated
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    point_clicked = pyqtSignal(dict)  # Emitted when a point is clicked with data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.canvas)
        self.ax = self.figure.add_subplot(111)
        self.well_data = {}  # Dictionary to store well data
        self.well_data_full = {}  # Dictionary to store full well data (unsampled)
        self.well_styles = {}  # Dictionary to store well styles
        
        # Comprehensive dictionary to store all well properties
        self.well_properties = {}  # Structure: {well_name: {'line': {styles}, 'manual': {styles}, 'trend': {styles}}}
        
        # Dictionary to store common properties for multi-well selections
        self.common_properties = {
            'labels': {
                'title': {'text': 'Water Level Data', 'font_size': 14, 'weight': 'normal'},
                'x_axis': {'text': 'Date', 'font_size': 12, 'weight': 'normal'},
                'y_axis': {'text': 'Water Level (ft)', 'font_size': 12, 'weight': 'normal'}
            },
            'legend': {
                'position': 'best',
                'font_size': 10,
                'draggable': True
            },
            'grid': True,
            'theme': 'light'
        }
        
        self.selected_point_annotation = None
        self.show_temperature = False
        self._legend_position = 0  # Default legend position
        self._draggable_legend = True  # Default draggable legend
        self.show_water_year_highlight = False  # Default water year highlight setting
        self.water_year_patches = []  # Store water year patches
        self.show_gaps_highlight = False  # Default gaps highlight setting
        self.gap_patches = []  # Store gap patches
                
        self.setup_plot()
        self.setup_plot_interaction()
    
    def setup_plot_interaction(self):
        """Set up interactive features for the plot"""
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
    
    def setup_plot(self):
        """Set up the initial plot configuration."""
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('Water Level (ft)')
        self.ax.grid(True)
        self.figure.tight_layout()
        self.format_date_axis()
    
    def format_date_axis(self):
        """Format the date axis for better readability."""
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
    
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
        
        if closest_point and min_dist < 50:
            point_data = {
                'well': closest_well,
                'date': closest_point[0],
                'value': closest_point[1],
                'temperature': None
            }
            
            # Check for temperature data if showing temperature
            if self.show_temperature:
                for line in ax.get_lines():
                    if line.get_label() == 'Temperature':
                        temp_idx = (abs(line.get_xdata() - closest_point[0])).argmin()
                        point_data['temperature'] = line.get_ydata()[temp_idx]
            
            # Create annotation text
            text = (f"{closest_well}\n"
                   f"Date: {closest_point[0].strftime('%Y-%m-%d %H:%M')} UTC\n"
                   f"{'Temperature' if self.show_temperature else 'Level'}: "
                   f"{closest_point[1]:.2f} {'°C' if self.show_temperature else 'ft'}")
            
            if point_data['temperature'] is not None:
                text += f"\nTemperature: {point_data['temperature']:.2f}°C"
            
            self.selected_point_annotation = ax.annotate(
                text,
                xy=closest_point,
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
            
            self.canvas.draw()
            self.point_clicked.emit(point_data)
    
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
    
    def toggle_temperature(self, show: bool):
        """Toggle temperature display"""
        self.show_temperature = show
        if show:
            self.ax.set_ylabel('Temperature (°C)')
        else:
            self.ax.set_ylabel('Water Level (ft)')
        self.canvas.draw()
    
    def get_widget(self):
        """Get the plot widget for adding to the layout."""
        return self.canvas
    
    def get_toolbar(self):
        """Get the navigation toolbar for adding to the layout."""
        return self.toolbar
    
    def clear_plot(self):
        """Clear the current plot."""
        self.ax.clear()
        self.setup_plot()
        self.canvas.draw()
    
    def initialize_plot(self):
        """Initialize the plot to its default state."""
        # Reset data
        self.well_data = {}
        self.well_data_full = {}
        self.well_styles = {}
        self.selected_point_annotation = None
        
        # Apply default settings
        self.ax.set_title(self.common_properties['labels']['title']['text'])
        self.ax.set_xlabel(self.common_properties['labels']['x_axis']['text'])
        self.ax.set_ylabel(self.common_properties['labels']['y_axis']['text'])
        self.ax.grid(self.common_properties['grid'])
        
        # Redraw canvas
        self.format_date_axis()
        self.figure.tight_layout()
        self.canvas.draw()
        
        # Emit signal
        self.plot_updated.emit()
    
    def update_plot(self, wells, date_range, show_manual=False, data_type='water_level', db_path=None, downsample_method='none'):
        """Update the plot with the specified wells and date range."""
        try:
            logger.info("Starting plot update")
            logger.info(f"Updating plot for wells: {wells}")
            logger.info(f"Date range: {date_range}")
            logger.info(f"Show manual: {show_manual}")
            logger.info(f"Data type: {data_type}")
            logger.info(f"Downsampling method: {downsample_method}")
            logger.info(f"Database path: {db_path}")
            
            # Create plot update key to detect duplicate updates
            update_key = f"{','.join(wells)}|{date_range}|{show_manual}|{data_type}|{downsample_method}"
            if hasattr(self, '_last_update_key') and self._last_update_key == update_key:
                logger.info("Skipping duplicate plot update")
                return
            self._last_update_key = update_key
            
            # Store the date range and db_path for use in set_well_style method
            self._current_date_range = date_range
            self.db_path = db_path
            
            logger.info("Clearing plot")
            self.clear_plot()
            
            if not wells:
                logger.warning("No wells selected for plotting")
                return
            
            # Display loading message - BEFORE we start fetching and processing data
            loading_text = self.ax.text(0.5, 0.5, "Loading data...",
                         ha='center', va='center', 
                         transform=self.ax.transAxes,
                         fontsize=14, color='gray',
                         bbox=dict(boxstyle='round,pad=0.5', 
                               fc='white', ec='gray', alpha=0.8))
            self.canvas.draw()
            self.canvas.flush_events()  # Force update to show loading message immediately
            
            # Set y-axis label based on data type
            ylabel = 'Temperature (°C)' if data_type == 'temperature' else 'Water Level (ft)'
            self.ax.set_ylabel(ylabel)
            
            # Apply common properties for labels and appearance
            if hasattr(self, 'common_properties'):
                # Apply grid
                self.ax.grid(self.common_properties.get('grid', True))
                
                # Apply labels
                if 'labels' in self.common_properties:
                    labels = self.common_properties['labels']
                    
                    # Title
                    if 'title' in labels:
                        title = labels['title']
                        self.ax.set_title(
                            title.get('text', 'Water Level Data'),
                            fontsize=title.get('font_size', 14),
                            weight=title.get('weight', 'normal')
                        )
                    
                    # X-axis
                    if 'x_axis' in labels:
                        x_axis = labels['x_axis']
                        self.ax.set_xlabel(
                            x_axis.get('text', 'Date'),
                            fontsize=x_axis.get('font_size', 12),
                            weight=x_axis.get('weight', 'normal')
                        )
                    
                    # Y-axis (override with data type if needed)
                    if 'y_axis' in labels:
                        y_axis = labels['y_axis']
                        self.ax.set_ylabel(
                            ylabel,  # Use the data type appropriate label
                            fontsize=y_axis.get('font_size', 12),
                            weight=y_axis.get('weight', 'normal')
                        )
            
            # Create color cycle for multiple wells
            colors = plt.cm.tab10(np.linspace(0, 1, len(wells)))
            
            # Track whether we have any plottable data
            has_plottable_data = False
            legend_handles = []
            legend_labels = []
            
            # Store well info for title
            well_info_dict = {}
            
            # Map downsampling methods to a numeric "detail level" for comparison
            detail_levels = {
                'none': 100,
                'No Downsampling': 100,
                '30 Minutes': 90,
                '1 Hour': 80,
                '2 Hours': 70,
                '6 Hours': 60,
                '12 Hours': 50,
                '1 Day': 40,
                '1 Week': 30,
                '1 Month': 20
            }
            
            # Get the detail level of the requested downsampling
            requested_detail = detail_levels.get(downsample_method, 100)
            
            # Plot each well
            for i, well in enumerate(wells):
                logger.info(f"Processing well: {well}")
                
                # Get well info for title - do this first to have info for all wells
                if db_path:
                    well_info = self.get_well_info(well, db_path)
                    if well_info:
                        well_info_dict[well] = well_info
                
                # Choose data source based on requested detail and what's available
                df = None
                
                # Check if we need to use the full data instead of predownsampled data
                if requested_detail > 30 and well in self.well_data_full:
                    # The user wants more detail than weekly, so use the full dataset
                    logger.info(f"Using full dataset for well {well} (requested detail level: {requested_detail})")
                    df = self.well_data_full[well]
                elif well in self.well_data:
                    # Otherwise use the predownsampled data
                    logger.info(f"Using predownsampled dataset for well {well}")
                    df = self.well_data[well]
                else:
                    logger.warning(f"No data found for well {well}")
                    continue
                    
                if df.empty:
                    logger.warning(f"Empty dataframe for well {well}")
                    continue
                
                logger.info(f"DataFrame shape for well {well}: {df.shape}")
                
                # Apply date filtering
                if date_range and date_range.get('start') and date_range.get('end'):
                    # Convert the date range to pandas datetime if they are strings
                    start = date_range['start']
                    end = date_range['end']
                    
                    if isinstance(start, str):
                        start = pd.to_datetime(start)
                    if isinstance(end, str):
                        end = pd.to_datetime(end)
                    
                    # Add time to end date to include all data from that day
                    if hasattr(end, 'replace'):
                        try:
                            # If it's a date object, add time to include the full day
                            end = end.replace(hour=23, minute=59, second=59)
                        except (AttributeError, TypeError):
                            # If it's already a datetime with time or something else, leave it
                            pass
                    
                    if df.index.name == 'timestamp_utc':
                        # The timestamp is the index
                        df_filtered = df[(df.index >= start) & (df.index <= end)]
                    else:
                        # The timestamp is a column
                        df_filtered = df[(df['timestamp_utc'] >= start) & (df['timestamp_utc'] <= end)]
                    
                    logger.info(f"Filtered DataFrame shape: {df_filtered.shape}")
                else:
                    df_filtered = df
                
                if df_filtered.empty:
                    logger.warning(f"No data in date range for well {well}")
                    continue
                
                # Apply user-selected downsampling if specified
                # Always apply downsampling if requested, regardless of detail level
                if downsample_method != 'none' and downsample_method != 'No Downsampling':
                    df_filtered = self.downsample_data(df_filtered, method=downsample_method)
                    logger.info(f"Applied downsampling to {len(df_filtered)} points with method: {downsample_method}")
                
                logger.info(f"Plotting {len(df_filtered)} points for well {well}")
                
                # Initialize or get properties for this well
                # Use the color cycle index to assign a unique color if properties don't exist
                color = plt.cm.colors.to_hex(colors[i])
                
                if well not in self.well_properties:
                    self.initialize_well_properties(well, color)
                
                # Get the style for this well
                style = self.well_properties[well]['line']
                
                # Update the well_styles dictionary for backward compatibility
                self.well_styles[well] = style
                
                # Get color from the style
                color = style.get('color', color)
                
                # Plot the main data
                logger.info(f"Creating plot line for well {well}")
                
                # Ensure timestamp_utc is in the right format
                if df_filtered.index.name == 'timestamp_utc':
                    x_data = df_filtered.index
                else:
                    x_data = df_filtered['timestamp_utc']
                
                line = self.ax.plot(
                    x_data,
                    df_filtered[data_type],
                    label=well,
                    color=color,
                    linewidth=style.get('line_width', 1.5),
                    linestyle=style.get('line_style', '-'),
                    zorder=5
                )[0]
                legend_handles.append(line)
                legend_labels.append(well)
                has_plottable_data = True
                
                # Plot manual readings if requested
                if show_manual and db_path:
                    try:
                        logger.info(f"Getting manual readings for well {well}")
                        logger.info(f"Database path: {db_path}")
                        logger.info(f"Date range: {date_range}")
                        manual_data = self.get_manual_readings(well, db_path)
                        logger.info(f"Retrieved {len(manual_data)} manual readings before filtering")
                        
                        # Apply date range filter only if both start and end dates are specified
                        if not manual_data.empty and date_range and date_range.get('start') and date_range.get('end'):
                            # Filter to date range
                            start = date_range['start']
                            end = date_range['end']
                            logger.info(f"Filtering manual data to date range: {start} to {end}")
                            
                            if isinstance(start, str):
                                start = pd.to_datetime(start)
                            if isinstance(end, str):
                                end = pd.to_datetime(end)
                                
                            if hasattr(end, 'replace'):
                                try:
                                    end = end.replace(hour=23, minute=59, second=59)
                                except (AttributeError, TypeError):
                                    pass
                                    
                            manual_data = manual_data[
                                (manual_data['measurement_date_utc'] >= start) & 
                                (manual_data['measurement_date_utc'] <= end)
                            ]
                            logger.info(f"After filtering: {len(manual_data)} manual readings remain")
                        elif not manual_data.empty:
                            logger.info(f"No date range specified, showing all {len(manual_data)} manual readings")
                        
                        if not manual_data.empty:
                            logger.info(f"Plotting {len(manual_data)} manual reading points for well {well}")
                            
                            # Get manual style from the properties
                            manual_style = self.well_properties[well]['manual']
                            
                            # If manual style doesn't have color, use the line color
                            if 'color' not in manual_style:
                                manual_style['color'] = color
                            
                            marker_size = manual_style.get('marker_size', 80)
                            # Ensure marker_size is a valid number
                            try:
                                marker_size = float(marker_size)
                                # Use a reasonable size for matplotlib (original size is too large)
                                if marker_size > 200:  # If it's from the spinner (20-200 range)
                                    marker_size = marker_size / 6  # Scale it down for matplotlib
                            except (TypeError, ValueError) as e:
                                logger.error(f"Invalid marker size: {e}")
                                marker_size = 80  # Default if error
                            
                            # Get marker type with fallback
                            marker_type = manual_style.get('marker', 'o')
                            if not marker_type or marker_type not in ['o', 's', '^', 'd', 'x', '+']:
                                marker_type = 'o'  # Default to circle if invalid
                            
                            # Use manual color if specified, otherwise use the same as the line
                            manual_color = manual_style.get('color', color)
                            
                            # Plot manual data points
                            scatter = self.ax.scatter(
                                manual_data['measurement_date_utc'],
                                manual_data['water_level'],
                                label=f"{well}_manual",
                                color=manual_color,
                                marker=marker_type,
                                s=marker_size,
                                alpha=1.0,
                                edgecolor='black',
                                linewidth=0.5,
                                zorder=10
                            )
                            
                            # Add to legend unless it's already there
                            if f"{well}_manual" not in legend_labels:
                                legend_handles.append(scatter)
                                legend_labels.append(f"{well}_manual")
                    except Exception as e:
                        logger.error(f"Error plotting manual data for well {well}: {e}")
                        logger.error(traceback.format_exc())
            
            # Remove loading text if present
            try:
                if loading_text:
                    loading_text.remove()
            except:
                pass  # Ignore errors - the text might have been cleared with the plot
            
            # Check if there's any data to plot after filtering
            if not has_plottable_data:
                self.ax.text(0.5, 0.5, "No data available for selected criteria",
                            ha='center', va='center', 
                            transform=self.ax.transAxes,
                            fontsize=14, color='gray',
                            bbox=dict(boxstyle='round,pad=0.5', 
                                fc='white', ec='gray', alpha=0.8))
                self.canvas.draw()
                return
            
            # Set the title based on well selection
            if len(wells) == 1:
                # Single well title
                well = wells[0]
                title = f"Well {well}"
                
                # Add well info to title if available
                well_info = well_info_dict.get(well)
                if well_info:
                    if 'cae_number' in well_info and well_info['cae_number']:
                        title += f" (CAE: {well_info['cae_number']})"
                    if 'aquifer' in well_info and well_info['aquifer']:
                        title += f" - {well_info['aquifer']} Aquifer"
                
                self.ax.set_title(title)
            else:
                # Multiple wells title - group by aquifer if possible
                aquifers = set()
                well_count = len(wells)
                
                for well, info in well_info_dict.items():
                    if 'aquifer' in info and info['aquifer']:
                        aquifers.add(info['aquifer'])
                
                if len(aquifers) == 1:
                    # All wells from same aquifer
                    aquifer = list(aquifers)[0]
                    self.ax.set_title(f"{aquifer} Aquifer - {well_count} Wells")
                else:
                    # Multiple aquifers
                    self.ax.set_title(f"Water Level Data - {well_count} Wells")
            
            # Set up the legend
            if legend_handles:
                # Use common properties for legend if available
                if hasattr(self, 'common_properties') and 'legend' in self.common_properties:
                    legend_props = self.common_properties['legend']
                    position = legend_props.get('position', 'best')
                    font_size = legend_props.get('font_size', 10)
                    draggable = legend_props.get('draggable', True)
                    
                    # Map position string to integer if needed
                    if isinstance(position, str):
                        position_map = {
                            'best': 0, 'upper right': 1, 'upper left': 2, 
                            'lower left': 3, 'lower right': 4, 'right': 5,
                            'center left': 6, 'center right': 7, 'lower center': 8, 
                            'upper center': 9, 'center': 10
                        }
                        position = position_map.get(position, 0)
                else:
                    position = self._legend_position
                    font_size = 10
                    draggable = self._draggable_legend
                
                legend = self.ax.legend(
                    handles=legend_handles, 
                    labels=legend_labels, 
                    loc=position,
                    fontsize=font_size,
                    draggable=draggable
                )
            
            # Format the date axis
            self.format_date_axis()
            
            # Adjust the figure layout
            self.figure.tight_layout()
            
            # Update the canvas
            self.canvas.draw()
            
            # Re-apply highlighting if enabled
            if hasattr(self, 'show_water_year_highlight') and self.show_water_year_highlight:
                self.highlight_water_years()
                
            if hasattr(self, 'show_gaps_highlight') and self.show_gaps_highlight:
                self.highlight_gaps()
            
            # Emit signal that plot was updated successfully
            self.plot_updated.emit()
            
            # Log completion message
            logger.info("Plot update completed successfully")
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            logger.error(traceback.format_exc())
            
            # Clear any temporary elements
            try:
                if 'loading_text' in locals() and loading_text:
                    loading_text.remove()
            except:
                pass
            
            # Show error on plot
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"Error updating plot: {str(e)}",
                        ha='center', va='center', 
                        transform=self.ax.transAxes,
                        fontsize=12, color='red',
                        bbox=dict(boxstyle='round,pad=0.5', 
                            fc='white', ec='red', alpha=0.8),
                        wrap=True)
            self.canvas.draw()
            
            # Emit error signal
            self.error_occurred.emit(f"Error updating plot: {str(e)}")
    
    def set_well_data(self, well_number, data, downsample_initial=True):
        """Set the data for a specific well.
        
        Args:
            well_number: Well identifier
            data: DataFrame with well data
            downsample_initial: Whether to downsample initially for display (no longer used)
        """
        # Store the data without initial downsampling
        self.well_data_full[well_number] = data
        self.well_data[well_number] = data
        
        # Log the number of data points for this well
        logger.info(f"Stored {len(data)} data points for well {well_number}")
    
    def initialize_well_properties(self, well_number, color=None):
        """Initialize default properties for a well when first selected.
        
        Args:
            well_number: The well identifier
            color: Optional initial color to use (if None, a default will be assigned)
        
        Returns:
            The initialized property dictionary for the well
        """
        # Check if properties already exist for this well
        if well_number in self.well_properties:
            return self.well_properties[well_number]
            
        # If no color provided, use a default color (matplotlib blue)
        if color is None:
            color = "#1f77b4"  # Default matplotlib blue
            
        # Create default property structure for this well
        self.well_properties[well_number] = {
            'line': {
                'color': color,
                'line_width': 1.5,
                'line_style': '-'
            },
            'manual': {
                'color': color,  # Default to same color
                'marker': 'o',
                'marker_size': 80
            },
            'trend': {
                'color': '#ff7f0e',  # Default orange
                'line_width': 1.5,
                'line_style': '--'
            }
        }
        
        # Also maintain backward compatibility with well_styles
        self.well_styles[well_number] = self.well_properties[well_number]['line']
        
        logger.info(f"Initialized properties for well {well_number}")
        return self.well_properties[well_number]
    
    def set_well_style(self, well_number, style_dict):
        """Set the style for a specific well."""
        # Maintain backward compatibility with existing code
        self.well_styles[well_number] = style_dict
        
        # Determine if this is a manual reading style or a line style or trend style
        style_type = 'line'  # Default to line style
        base_well = well_number
        
        if well_number.endswith('_manual'):
            style_type = 'manual'
            base_well = well_number[:-7]  # Remove '_manual' suffix
        elif well_number.endswith('_trend'):
            style_type = 'trend'
            base_well = well_number[:-6]  # Remove '_trend' suffix
        
        # Initialize the well in the properties dictionary if it doesn't exist
        if base_well not in self.well_properties:
            self.initialize_well_properties(base_well)
        
        # Update only the properties that were specified in style_dict
        for key, value in style_dict.items():
            self.well_properties[base_well][style_type][key] = value
        
        logger.info(f"Updated {style_type} style for well {base_well}: {style_dict}")
        
        # If we've loaded data for this well, update the plot with the new style
        if base_well in self.well_data and not self.well_data[base_well].empty:
            try:
                # Get the data for this well
                df = self.well_data[base_well]
                
                # Get current lines and markers
                legend_handles = []
                legend_labels = []
                
                for line in self.ax.lines:
                    # Keep lines that aren't for this well
                    if line.get_label() != base_well and not line.get_label().startswith(f"{base_well}_"):
                        legend_handles.append(line)
                        legend_labels.append(line.get_label())
                
                # Handle manual or trend style updates separately
                if style_type == 'manual':
                    # Clear existing manual markers for this well
                    for i, scatter in enumerate(self.ax.collections):
                        if hasattr(scatter, 'get_label') and scatter.get_label() == f"{base_well}_manual":
                            scatter.remove()
                    
                    # Get manual properties
                    manual_style = self.well_properties[base_well]['manual']
                    manual_color = manual_style.get('color', self.well_properties[base_well]['line'].get('color', '#1f77b4'))
                    marker_type = manual_style.get('marker', 'o')
                    marker_size = manual_style.get('marker_size', 80)
                    
                    # Ensure numeric marker size
                    try:
                        marker_size = float(marker_size)
                        if marker_size > 200:  # Scale down if using the spinner range
                            marker_size = marker_size / 6  # Scale it down for matplotlib
                    except (TypeError, ValueError):
                        marker_size = 80 / 6  # Default scaled for matplotlib
                    
                    # Get manual data if db_path is set
                    if hasattr(self, 'db_path') and self.db_path:
                        manual_data = self.get_manual_readings(base_well, self.db_path)
                        if not manual_data.empty:
                            # Check for date filtering
                            if hasattr(self, '_current_date_range') and self._current_date_range:
                                start = self._current_date_range.get('start')
                                end = self._current_date_range.get('end')
                                if start and end:
                                    manual_data = manual_data[
                                        (manual_data['measurement_date_utc'] >= start) & 
                                        (manual_data['measurement_date_utc'] <= end)
                                    ]
                            
                            if not manual_data.empty:
                                # Plot the manual data
                                scatter = self.ax.scatter(
                                    manual_data['measurement_date_utc'],
                                    manual_data['water_level'],
                                    label=f"{base_well}_manual",
                                    marker=marker_type,
                                    s=marker_size,
                                    color=manual_color,
                                    zorder=10
                                )
                else:
                    # Handle transducer data style update
                    # Clear existing lines for this well
                    for line in self.ax.lines:
                        if line.get_label() == base_well:
                            line.remove()
                    
                    # Get the complete line style from the properties dictionary
                    line_style = self.well_properties[base_well]['line']
                    
                    # Plot with new style
                    if df.index.name == 'timestamp_utc':
                        x_data = df.index
                    else:
                        x_data = df['timestamp_utc']
                        
                    line = self.ax.plot(
                        x_data,
                        df['water_level'],
                        label=base_well,
                        color=line_style.get('color', '#1f77b4'),
                        linewidth=line_style.get('line_width', 1.5),
                        linestyle=line_style.get('line_style', '-'),
                        zorder=5
                    )[0]
                    
                    # Add to legend
                    legend_handles.append(line)
                    legend_labels.append(base_well)
                
                # Update the legend
                if legend_handles:
                    # Use the common properties for legend if available
                    if hasattr(self, 'common_properties') and 'legend' in self.common_properties:
                        legend_props = self.common_properties['legend']
                        position = legend_props.get('position', 'best')
                        draggable = legend_props.get('draggable', True)
                        
                        # Map position string to integer if needed
                        if isinstance(position, str):
                            position_map = {
                                'best': 0, 'upper right': 1, 'upper left': 2, 
                                'lower left': 3, 'lower right': 4, 'right': 5,
                                'center left': 6, 'center right': 7, 'lower center': 8, 
                                'upper center': 9, 'center': 10
                            }
                            position = position_map.get(position, 0)
                    else:
                        position = self._legend_position
                        draggable = getattr(self, '_draggable_legend', True)
                        
                    self.ax.legend(handles=legend_handles, labels=legend_labels, 
                                  loc=position, 
                                  draggable=draggable)
                
                # Update the canvas
                self.canvas.draw()
            except Exception as e:
                logger.error(f"Error updating plot style: {e}")
                logger.error(traceback.format_exc())
                self.error_occurred.emit(f"Error updating plot: {str(e)}")
    
    def get_plot_figure(self):
        """Get the current plot figure."""
        return self.figure
    
    def get_plot_axes(self):
        """Get the current plot axes."""
        return self.ax
    
    def apply_theme(self, theme_colors):
        """Apply theme colors to the plot."""
        try:
            # Set figure and axes colors
            self.figure.patch.set_facecolor(theme_colors['figure_facecolor'])
            self.ax.set_facecolor(theme_colors['axes_facecolor'])
            
            # Set text colors
            self.ax.tick_params(colors=theme_colors['text_color'])
            self.ax.xaxis.label.set_color(theme_colors['label_color'])
            self.ax.yaxis.label.set_color(theme_colors['label_color'])
            
            # Set title color if exists
            if self.ax.get_title():
                self.ax.title.set_color(theme_colors['title_color'])
            
            # Set spine colors
            for spine in self.ax.spines.values():
                spine.set_color(theme_colors['spine_color'])
            
            # Set grid color
            self.ax.grid(True, color=theme_colors['grid_color'], linestyle='--', alpha=0.3)
            
            # Update legend colors if exists
            if self.ax.get_legend():
                for text in self.ax.get_legend().get_texts():
                    text.set_color(theme_colors['text_color'])
            
            # Update toolbar colors
            self.toolbar.setStyleSheet(f"""
                QToolBar {{
                    background-color: {theme_colors['figure_facecolor']};
                    color: {theme_colors['text_color']};
                }}
                QToolButton {{
                    background-color: {theme_colors['axes_facecolor']};
                    color: {theme_colors['text_color']};
                    border: 1px solid {theme_colors['spine_color']};
                    border-radius: 4px;
                }}
                QToolButton:hover {{
                    background-color: {theme_colors['grid_color']};
                }}
            """)
            
            # Update the canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
            self.error_occurred.emit(f"Error applying theme: {str(e)}")
    
    def save_plot(self, filepath, dpi=300):
        """Save the current plot to a file."""
        try:
            self.figure.savefig(filepath, dpi=dpi, bbox_inches='tight')
            return True
        except Exception as e:
            self.error_occurred.emit(f"Error saving plot: {str(e)}")
            return False
    
    def get_well_info(self, well_number: str, db_path: str) -> dict:
        """Get well information from database with improved error handling for schema differences."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # First, check which columns exist in the wells table
                cursor.execute("PRAGMA table_info(wells)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Create a dynamic query based on available columns
                available_columns = ['well_number']  # Always include well_number
                
                # Add optional columns if they exist
                optional_columns = ['aquifer', 'status', 'data_source', 'latitude', 'longitude', 
                                   'cae_number', 'caesar_number', 'wellfield', 'toc']
                
                for col in optional_columns:
                    if col in columns:
                        available_columns.append(col)
                
                # Create the query with only available columns
                query = f"SELECT {', '.join(available_columns)} FROM wells WHERE well_number = ?"
                cursor.execute(query, (well_number,))
                result = cursor.fetchone()
                
                if result:
                    # Create a dictionary with column names and values
                    well_info = dict(zip(available_columns, result))
                    
                    # Add default values for common missing columns
                    if 'data_source' not in well_info:
                        well_info['data_source'] = 'transducer'
                    if 'aquifer' not in well_info:
                        well_info['aquifer'] = 'Unknown'
                    if 'status' not in well_info:
                        well_info['status'] = 'Active'
                        
                    return well_info
                return None
        except Exception as e:
            logger.error(f"Error getting well info: {e}")
            return None

    def get_well_data(self, well_number: str, db_path: str, date_range=None) -> pd.DataFrame:
        """Get well data from database with improved schema compatibility."""
        try:
            # First get the well info with our improved method that handles schema differences
            well_info = self.get_well_info(well_number, db_path)
            if not well_info:
                logger.warning(f"No information found for well {well_number}")
                return pd.DataFrame()
            
            # Get data source, defaulting to transducer if not found
            data_source = well_info.get('data_source', 'transducer')
            logger.debug(f"Well {well_number} has data source: {data_source}")
            
            with sqlite3.connect(db_path) as conn:
                # Check if the necessary tables exist
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [table[0] for table in cursor.fetchall()]
                
                # Build date range filter if provided
                date_filter = ""
                params = [well_number]
                
                # Only add date filter if both start and end dates are valid
                if date_range:
                    # Improved validation for date parameters
                    valid_start = False
                    valid_end = False
                    
                    if date_range.get('start'):
                        try:
                            # Convert to string format for SQLite
                            start_date = pd.Timestamp(date_range['start']).strftime('%Y-%m-%d %H:%M:%S')
                            valid_start = True
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Invalid start date: {e}")
                    
                    if date_range.get('end'):
                        try:
                            # Convert to string format for SQLite
                            end_date = pd.Timestamp(date_range['end']).strftime('%Y-%m-%d %H:%M:%S')
                            valid_end = True
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Invalid end date: {e}")
                    
                    # Add date filter based on what's valid
                    if valid_start and valid_end:
                        date_filter = "AND timestamp_utc BETWEEN ? AND ?"
                        params.extend([start_date, end_date])
                        logger.debug(f"Using date filter: {start_date} to {end_date}")
                    elif valid_start:
                        date_filter = "AND timestamp_utc >= ?"
                        params.append(start_date)
                        logger.debug(f"Using start date filter: {start_date}")
                    elif valid_end:
                        date_filter = "AND timestamp_utc <= ?"
                        params.append(end_date)
                        logger.debug(f"Using end date filter: {end_date}")
                    else:
                        logger.debug("No valid date range provided, fetching all data")
                
                # Query based on data source and available tables
                if data_source == 'telemetry' and 'telemetry_level_readings' in tables:
                    # Check which columns exist in telemetry_level_readings
                    cursor.execute("PRAGMA table_info(telemetry_level_readings)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Build a query with only existing columns
                    select_cols = ['timestamp_utc']
                    for col in ['water_level', 'temperature']:
                        if col in columns:
                            select_cols.append(col)
                    
                    query = f"""
                        SELECT {', '.join(select_cols)},
                               'telemetry' as source_type
                        FROM telemetry_level_readings
                        WHERE well_number = ? {date_filter}
                        ORDER BY timestamp_utc
                    """
                elif 'water_level_readings' in tables:
                    # Check which columns exist in water_level_readings
                    cursor.execute("PRAGMA table_info(water_level_readings)")
                    reading_columns = [col[1] for col in cursor.fetchall()]
                    
                    # Build a query with only existing columns
                    select_cols = ['r.timestamp_utc']
                    for col in ['water_level', 'temperature']:
                        if col in reading_columns:
                            select_cols.append(f'r.{col}')
                    
                    # Check if wells table has cae_number
                    cursor.execute("PRAGMA table_info(wells)")
                    well_columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'cae_number' in well_columns:
                        select_cols.append('wells.cae_number as cae')
                    elif 'caesar_number' in well_columns:
                        select_cols.append('wells.caesar_number as cae')
                    
                    query = f"""
                        SELECT {', '.join(select_cols)},
                               'transducer' as source_type
                        FROM water_level_readings r
                        JOIN wells ON r.well_number = wells.well_number
                        WHERE r.well_number = ? {date_filter}
                        ORDER BY r.timestamp_utc
                    """
                else:
                    logger.error(f"No suitable data table found for well {well_number}")
                    return pd.DataFrame()
                
                # Execute query with defensive error handling
                try:
                    logger.debug(f"Executing query with params: {params}")
                    df = pd.read_sql_query(query, conn, params=params)
                except sqlite3.OperationalError as e:
                    logger.error(f"Database query error: {e}")
                    # Attempt an even simpler fallback query
                    simple_query = f"""
                        SELECT timestamp_utc, water_level
                        FROM {"telemetry_level_readings" if data_source == 'telemetry' else "water_level_readings"}
                        WHERE well_number = ?
                        ORDER BY timestamp_utc
                    """
                    try:
                        logger.debug("Attempting fallback query")
                        df = pd.read_sql_query(simple_query, conn, params=[well_number])
                    except Exception as e2:
                        logger.error(f"Fallback query also failed: {e2}")
                        return pd.DataFrame()
                
                if not df.empty:
                    # Convert timestamp to datetime
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    
                    # Set index to timestamp_utc
                    df.set_index('timestamp_utc', inplace=True)
                    
                    # Add default value for missing temperature column
                    if 'temperature' not in df.columns:
                        df['temperature'] = np.nan
                    
                    # Add computed columns for corrections if they don't exist
                    if 'water_level_corrected' not in df.columns:
                        df['water_level_corrected'] = df['water_level']
                    
                    logger.debug(f"Retrieved {len(df)} readings for well {well_number}")
                    
                return df
                
        except Exception as e:
            logger.error(f"Error getting well data: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_master_baro_data(self, db_path: str, date_range=None) -> pd.DataFrame:
        """Get master barometric data from database."""
        try:
            with sqlite3.connect(db_path) as conn:
                # Build query with optional date filter
                query = """
                    SELECT timestamp_utc, pressure
                    FROM master_baro_readings
                """
                params = []
                
                # Enhanced date validation for barometric data
                if date_range:
                    valid_start = False
                    valid_end = False
                    
                    if date_range.get('start'):
                        try:
                            start_date = pd.Timestamp(date_range['start'])
                            if pd.notna(start_date):
                                valid_start = True
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Invalid start date for baro data: {e}")
                    
                    if date_range.get('end'):
                        try:
                            end_date = pd.Timestamp(date_range['end'])
                            if pd.notna(end_date):
                                valid_end = True
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Invalid end date for baro data: {e}")
                    
                    # Add date filter based on what's valid
                    if valid_start and valid_end:
                        query += " WHERE timestamp_utc BETWEEN ? AND ?"
                        params.extend([start_date, end_date])
                        logger.debug(f"Using baro date filter: {start_date} to {end_date}")
                    elif valid_start:
                        query += " WHERE timestamp_utc >= ?"
                        params.append(start_date)
                        logger.debug(f"Using baro start date filter: {start_date}")
                    elif valid_end:
                        query += " WHERE timestamp_utc <= ?"
                        params.append(end_date)
                        logger.debug(f"Using baro end date filter: {end_date}")
                    else:
                        logger.debug("No valid date range for baro query, fetching all data")
                
                query += " ORDER BY timestamp_utc"
                
                df = pd.read_sql_query(query, conn, params=params)
                if not df.empty:
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    df.set_index('timestamp_utc', inplace=True)
                return df
                
        except Exception as e:
            logger.error(f"Error getting master baro data: {e}")
            return pd.DataFrame()

    def downsample_data(self, df, method='none', bin_size=None):
        """Downsample data for more efficient plotting of large datasets.
        
        Args:
            df: DataFrame to downsample
            method: Downsampling method ('none', '30min', '1h', '2h', '6h', '12h', '1d', '1w', '1M')
            bin_size: Custom bin size for resampling
            
        Returns:
            Downsampled DataFrame
        """
        if df.empty or method == 'none' or method == 'No Downsampling':
            return df
            
        # Map method names to pandas resample rule
        method_map = {
            '30min': '30T',
            '30 Minutes': '30T',
            '1h': 'H',
            '1 Hour': 'H',
            '2h': '2H',
            '2 Hours': '2H',
            '6h': '6H',
            '6 Hours': '6H',
            '12h': '12H',
            '12 Hours': '12H',
            '1d': 'D',
            '1 Day': 'D',
            '1w': 'W-MON',  # Changed from 'W' to 'W-MON' to ensure consistent weekly intervals
            '1 Week': 'W-MON',  # Changed from 'W' to 'W-MON'
            '1m': 'MS',  # Changed from 'M' to 'MS' (month start) for consistent monthly intervals
            '1 Month': 'MS'  # Changed from 'M' to 'MS'
        }
        
        if bin_size:
            rule = bin_size
        else:
            rule = method_map.get(method)
            if not rule:
                logger.warning(f"Unknown downsample method: {method}, using original data")
                return df
        
        logger.info(f"Downsampling data from {len(df)} points using {rule} rule")
        
        # Make sure timestamp is the index
        if 'timestamp_utc' in df.columns:
            df = df.set_index('timestamp_utc')
        
        # Store columns for later
        columns = df.columns.tolist()
        
        # Apply aggregation based on data type
        try:
            # For each column, apply appropriate aggregation
            result_dict = {}
            
            for col in columns:
                if col.startswith('water_level') or col == 'temperature' or col == 'pressure':
                    # Numerical data - apply aggregation method based on user selection
                    agg_method = self.get_aggregation_method()
                    result_dict[col] = getattr(df[col].resample(rule), agg_method)()
                else:
                    # Non-numerical data - use first value
                    result_dict[col] = df[col].resample(rule).first()
            
            # Combine results
            result = pd.DataFrame(result_dict)
            
            # Reset index if needed to match original format
            if 'timestamp_utc' not in columns:
                result = result.reset_index()
                
            logger.info(f"Downsampled to {len(result)} points")
            return result
            
        except Exception as e:
            logger.error(f"Error downsampling data: {e}")
            return df
    
    def get_aggregation_method(self):
        """Get aggregation method from UI or use default."""
        # If there's a forced aggregation method set, use that
        if hasattr(self, '_forced_agg_method') and self._forced_agg_method:
            return self._forced_agg_method
            
        # Check if parent has aggregate_combo attribute
        if self.parent() and hasattr(self.parent(), 'aggregate_combo'):
            method_text = self.parent().aggregate_combo.currentText().lower()
            if method_text == 'median':
                return 'median'
            elif method_text == 'min':
                return 'min'
            elif method_text == 'max':
                return 'max'
            else:
                return 'mean'  # Default to mean
        return 'mean'  # Default if no parent UI control

    # Add methods for interactive legend and plot title/font management
    
    def set_title(self, title_text, font_size=14):
        """Set the plot title and font size."""
        if title_text:
            self.ax.set_title(title_text, fontsize=font_size)
        else:
            self.ax.set_title("")
        self.canvas.draw()
        
    def set_axis_font_size(self, font_size=10):
        """Set font size for axis labels."""
        self.ax.tick_params(axis='both', which='major', labelsize=font_size)
        self.ax.xaxis.label.set_fontsize(font_size)
        self.ax.yaxis.label.set_fontsize(font_size)
        self.canvas.draw()
    
    def set_legend_position(self, position='best'):
        """Set the legend position."""
        # Map position strings to matplotlib location codes
        position_map = {
            'best': 0,
            'upper_right': 1,
            'upper_left': 2,
            'lower_left': 3,
            'lower_right': 4,
            'center_left': 6,
            'center_right': 7,
            'lower_center': 8,
            'upper_center': 9,
            'center': 10
        }
        
        # Get the numeric position code
        loc = position_map.get(position, 0)
        
        # Store for use in update_plot
        self._legend_position = loc
        
        # Update legend if it exists
        if self.ax.get_legend():
            self.ax.legend(loc=loc, draggable=getattr(self, '_draggable_legend', True))
            self.canvas.draw()
    
    def set_draggable_legend(self, draggable=True):
        """Make the legend draggable or not."""
        self._draggable_legend = draggable
        
        # Update legend if it exists
        if self.ax.get_legend():
            legend = self.ax.get_legend()
            legend.set_draggable(draggable)
            self.canvas.draw()
    
    def set_grid(self, show_grid=True):
        """Show or hide the grid."""
        self.ax.grid(show_grid)
        self.canvas.draw()
    
    def cleanup(self):
        """Clean up resources."""
        plt.close(self.figure)
        self.canvas = None
        self.figure = None
    
    def save_properties(self, filepath=None):
        """Save well properties and common properties to a JSON file.
        
        Args:
            filepath: Path to save the properties. If None, uses a default path.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Default filepath if none provided
            if filepath is None:
                # Get application data directory
                app_data_dir = os.path.join(os.path.expanduser("~"), ".water_level_visualizer")
                
                # Create directory if it doesn't exist
                if not os.path.exists(app_data_dir):
                    os.makedirs(app_data_dir)
                    
                filepath = os.path.join(app_data_dir, "well_properties.json")
            
            # Prepare data to save
            data = {
                'well_properties': self.well_properties,
                'common_properties': self.common_properties
            }
            
            # Convert any non-serializable objects to strings
            def sanitize_for_json(obj):
                if isinstance(obj, dict):
                    return {k: sanitize_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize_for_json(i) for i in obj]
                elif isinstance(obj, (int, float, str, bool, type(None))):
                    return obj
                else:
                    return str(obj)
            
            data = sanitize_for_json(data)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved well properties to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving properties: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def load_properties(self, filepath=None):
        """Load well properties and common properties from a JSON file.
        
        Args:
            filepath: Path to load the properties from. If None, uses a default path.
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Default filepath if none provided
            if filepath is None:
                app_data_dir = os.path.join(os.path.expanduser("~"), ".water_level_visualizer")
                filepath = os.path.join(app_data_dir, "well_properties.json")
            
            # Check if file exists
            if not os.path.exists(filepath):
                logger.info(f"Properties file not found: {filepath}")
                return False
            
            # Load from file
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Update properties
            if 'well_properties' in data:
                self.well_properties = data['well_properties']
                
                # Also update well_styles for backward compatibility
                for well, props in self.well_properties.items():
                    if 'line' in props:
                        self.well_styles[well] = props['line']
            
            if 'common_properties' in data:
                self.common_properties = data['common_properties']
                
            logger.info(f"Loaded well properties from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading properties: {e}")
            logger.error(traceback.format_exc())
            return False

    def set_axis_labels(self, x_label=None, y_label=None):
        """Set the axis labels for the plot.
        
        Args:
            x_label: Custom X-axis label. If None, use the default 'Date'
            y_label: Custom Y-axis label. If None, use the appropriate default based on data type
        """
        # Set x-axis label if provided, otherwise keep current
        if x_label:
            self.ax.set_xlabel(x_label)
        
        # Set y-axis label if provided, otherwise keep current
        if y_label:
            self.ax.set_ylabel(y_label)
            
        # Update the plot
        self.canvas.draw()

    def set_label_weight(self, which='both', bold=True):
        """Set the font weight for axis labels.
        
        Args:
            which: Which axis to affect ('x', 'y', or 'both')
            bold: Whether to use bold font
        """
        weight = 'bold' if bold else 'normal'
        
        if which in ['x', 'both']:
            self.ax.xaxis.label.set_weight(weight)
        
        if which in ['y', 'both']:
            self.ax.yaxis.label.set_weight(weight)
        
        # Update the plot
        self.canvas.draw()

    def set_title_weight(self, bold=True):
        """Set the font weight for the plot title.
        
        Args:
            bold: Whether to use bold font
        """
        if self.ax.get_title():
            weight = 'bold' if bold else 'normal'
            self.ax.title.set_weight(weight)
            
            # Update the plot
            self.canvas.draw()

    def set_legend_font_size(self, font_size=10):
        """Set the font size for legend text.
        
        Args:
            font_size: Font size to use for legend text
        """
        legend = self.ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_fontsize(font_size)
            
            # Update the plot
            self.canvas.draw()

    def apply_trend_analysis(self, wells, trend_type="linear", degree=1, style=None):
        """Apply trend analysis to the selected wells."""
        logger.info(f"[PLOT_TREND_DEBUG] apply_trend_analysis called with wells={wells}, type={trend_type}, style={style}")
        
        # First remove any existing trend lines
        self.remove_trend_lines()
        
        # Store these trend lines separately
        self.trend_lines = []
        
        # Default style if none provided
        if style is None:
            style = {
                'color': '#ff7f0e',  # Default orange
                'line_width': 1.5,
                'line_style': '--'
            }
        
        logger.info(f"[PLOT_TREND_DEBUG] Using style: {style}")
        
        # Process each well
        for well in wells:
            logger.info(f"[PLOT_TREND_DEBUG] Processing well: {well}")
            
            # Skip if well data not available
            if well not in self.well_data:
                logger.warning(f"[PLOT_TREND_DEBUG] Well {well} not in well_data")
                continue
                
            # Get the data
            df = self.well_data[well]
            logger.info(f"[PLOT_TREND_DEBUG] Well {well} has {len(df)} data points")
            
            # Skip if empty
            if df.empty:
                logger.warning(f"[PLOT_TREND_DEBUG] Well {well} has empty data")
                continue
            
            # Create a copy of the style for this well
            well_style = style.copy()
            
            # Get well-specific trend style if available (but prioritize dialog settings)
            if well in self.well_properties and 'trend' in self.well_properties[well]:
                saved_style = self.well_properties[well]['trend']
                # Only use saved settings for keys not provided by dialog
                for key, value in saved_style.items():
                    if key not in well_style:
                        well_style[key] = value
            
            logger.info(f"[PLOT_TREND_DEBUG] Final style for {well}: {well_style}")
            
            # Ensure timestamp is index or convert to datetime for proper fit
            if 'timestamp_utc' in df.columns:
                x_data = pd.to_datetime(df['timestamp_utc']).map(lambda x: x.timestamp())
            else:
                x_data = df.index.map(lambda x: x.timestamp())
            
            # Get y data (always use water_level for trend analysis)
            y_data = df['water_level'].values
            
            # Filter out NaN values
            mask = ~pd.isna(y_data)
            x_filtered = x_data[mask]
            y_filtered = y_data[mask]
            
            # Skip if not enough data points
            if len(y_filtered) < 2:
                continue
            
            try:
                if trend_type == 'linear':
                    # Simple linear regression
                    fit = np.polyfit(x_filtered, y_filtered, 1)
                    y_fit = np.polyval(fit, x_filtered)
                    
                    logger.info(f"[PLOT_TREND_DEBUG] Creating linear trend line for {well} with color={well_style.get('color', '#ff7f0e')}, width={well_style.get('line_width', 1.5)}, style={well_style.get('line_style', '--')}")
                    
                    # Add trend line
                    trend_line = self.ax.plot(
                        pd.to_datetime(x_filtered, unit='s'),
                        y_fit,
                        label=f"{well} (Trend)",
                        color=well_style.get('color', '#ff7f0e'),
                        linewidth=well_style.get('line_width', 1.5),
                        linestyle=well_style.get('line_style', '--'),
                        zorder=10
                    )[0]
                    
                    # Store the trend line
                    self.trend_lines.append(trend_line)
                    logger.info(f"[PLOT_TREND_DEBUG] Trend line created and stored for {well}")
                    
                elif trend_type == 'polynomial':
                    # Polynomial fit of specified degree
                    fit = np.polyfit(x_filtered, y_filtered, degree)
                    y_fit = np.polyval(fit, x_filtered)
                    
                    logger.info(f"[PLOT_TREND_DEBUG] Creating polynomial trend line for {well} with color={well_style.get('color', '#ff7f0e')}, width={well_style.get('line_width', 1.5)}, style={well_style.get('line_style', '--')}")
                    
                    # Add trend line
                    trend_line = self.ax.plot(
                        pd.to_datetime(x_filtered, unit='s'),
                        y_fit,
                        label=f"{well} (Poly {degree})",
                        color=well_style.get('color', '#ff7f0e'),
                        linewidth=well_style.get('line_width', 1.5),
                        linestyle=well_style.get('line_style', '--'),
                        zorder=10
                    )[0]
                    
                    # Store the trend line
                    self.trend_lines.append(trend_line)
                    
                elif trend_type == 'moving avg' or trend_type == 'moving':
                    # Moving average (rolling mean)
                    if len(y_filtered) <= degree:
                        # Not enough data for specified window
                        continue
                        
                    # Create a dataframe for rolling calculation
                    temp_df = pd.DataFrame({'y': y_filtered}, index=pd.to_datetime(x_filtered, unit='s'))
                    
                    # Calculate moving average
                    rolling = temp_df['y'].rolling(window=max(2, degree), min_periods=1).mean()
                    
                    logger.info(f"[PLOT_TREND_DEBUG] Creating moving average trend line for {well} with color={well_style.get('color', '#ff7f0e')}, width={well_style.get('line_width', 1.5)}, style={well_style.get('line_style', '--')}")
                    
                    # Add trend line
                    trend_line = self.ax.plot(
                        rolling.index,
                        rolling.values,
                        label=f"{well} (MA {degree})",
                        color=well_style.get('color', '#ff7f0e'),
                        linewidth=well_style.get('line_width', 1.5),
                        linestyle=well_style.get('line_style', '--'),
                        zorder=10
                    )[0]
                    
                    # Store the trend line
                    self.trend_lines.append(trend_line)
            
            except Exception as e:
                logger.error(f"Error applying trend analysis to well {well}: {e}")
                continue
        
        # Update the legend to include trend lines
        if hasattr(self, 'trend_lines') and self.trend_lines:
            try:
                # Get all current handles and labels to create a fresh legend
                handles, labels = self.ax.get_legend_handles_labels()
                
                # Create a dictionary to track which labels we've seen to avoid duplicates
                unique_items = {}
                for handle, label in zip(handles, labels):
                    unique_items[label] = handle
                    
                # Create final lists of handles and labels without duplicates
                legend_handles = list(unique_items.values())
                legend_labels = list(unique_items.keys())
                
                # Update legend
                self.ax.legend(handles=legend_handles, labels=legend_labels, 
                              loc=self._legend_position, 
                              draggable=getattr(self, '_draggable_legend', True))
            except Exception as e:
                logger.error(f"Error updating legend with trend lines: {e}")
        
        # Update the plot
        self.canvas.draw()
    
    def remove_trend_lines(self):
        """Remove any existing trend lines from the plot."""
        if hasattr(self, 'trend_lines') and self.trend_lines:
            for line in self.trend_lines:
                try:
                    line.remove()
                except Exception as e:
                    logger.error(f"Error removing trend line: {e}")
            
            # Clear the list
            self.trend_lines = []
            
            # Update the legend - safely get handles and labels
            handles = []
            labels = []
            
            if self.ax.get_legend():
                try:
                    # Get handles and labels safely
                    handles, labels = self.ax.get_legend_handles_labels()
                    
                    # Filter out trend lines
                    filtered_handles = []
                    filtered_labels = []
                    for handle, label in zip(handles, labels):
                        if not label.endswith("(Trend)") and not label.endswith("(Poly") and not label.endswith("(MA"):
                            filtered_handles.append(handle)
                            filtered_labels.append(label)
                    
                    # Update legend if we have items
                    if filtered_handles:
                        self.ax.legend(handles=filtered_handles, labels=filtered_labels, 
                                      loc=self._legend_position, 
                                      draggable=getattr(self, '_draggable_legend', True))
                except Exception as e:
                    logger.error(f"Error updating legend: {e}")
            
            # Update the plot
            self.canvas.draw()

    def get_well_properties(self, well_number):
        """Get all properties for a specific well.
        
        Args:
            well_number: The well identifier
            
        Returns:
            Dictionary of well properties or None if not found
        """
        if well_number in self.well_properties:
            return self.well_properties[well_number]
        return None
    
    def get_common_properties(self):
        """Get common properties for multiple wells.
        
        Returns:
            Dictionary of common properties
        """
        return self.common_properties
    
    def set_common_property(self, property_path, value):
        """Set a common property value.
        
        Args:
            property_path: Path to property (e.g. 'labels.title.font_size')
            value: Value to set
        """
        parts = property_path.split('.')
        target = self.common_properties
        
        # Navigate to the deepest dictionary
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
            
        # Set the value
        target[parts[-1]] = value
        logger.info(f"Set common property {property_path} to {value}")

    def highlight_water_years(self, enable=None):
        """
        Add background colors to visualize water years in the plot.
        Water years start on October 1st and end on September 30th of the following year.
        
        Args:
            enable (bool, optional): Whether to enable water year highlighting. If None, use the class attribute.
        """
        try:
            # Use the provided parameter or fall back to the class attribute
            if enable is None:
                enable = self.show_water_year_highlight
            else:
                self.show_water_year_highlight = enable
                
            # Clear any existing water year patches
            if hasattr(self, 'water_year_patches'):
                for patch in self.water_year_patches:
                    try:
                        patch.remove()
                    except:
                        pass  # Ignore if already removed
            
            self.water_year_patches = []
            
            if not enable:
                # Update the canvas and return
                self.canvas.draw()
                return
                
            # Get current x-axis limits
            xmin, xmax = self.ax.get_xlim()
            
            # Convert to Python datetime objects
            xmin_date = mdates.num2date(xmin).replace(tzinfo=None)
            xmax_date = mdates.num2date(xmax).replace(tzinfo=None)
            
            # Find the starting water year
            if xmin_date.month >= 10:  # Oct-Dec
                start_year = xmin_date.year
            else:  # Jan-Sep
                start_year = xmin_date.year - 1
                
            # Generate a list of water year boundaries
            water_year_starts = []
            current_year = start_year
            
            while True:
                # Create timezone-naive datetime 
                water_year_start = datetime(current_year, 10, 1)
                
                if water_year_start > xmax_date:
                    break
                    
                water_year_starts.append(water_year_start)
                current_year += 1
            
            # If no water years found, return
            if not water_year_starts:
                return
                
            # Get y-axis limits
            ymin, ymax = self.ax.get_ylim()
            
            # Add colored patches for each water year
            colors = ['#e6f7ff', '#d9eeff', '#ccddff', '#c4d8ff', '#b8e0ff']  # Light blues alternating
            
            for i, start_date in enumerate(water_year_starts):
                # Create end date with Python's datetime (timezone-naive)
                end_date = datetime(start_date.year + 1, 9, 30)
                
                # Skip if the water year is completely outside the plot
                if end_date < xmin_date or start_date > xmax_date:
                    continue
                
                color = colors[i % len(colors)]
                water_year_label = f"WY {start_date.year}-{start_date.year+1}"
                
                # Create the patch
                rect = plt.Rectangle(
                    (mdates.date2num(start_date), ymin),
                    mdates.date2num(end_date) - mdates.date2num(start_date),
                    ymax - ymin,
                    color=color,
                    alpha=0.3,
                    zorder=-1,  # Put behind data
                    label=water_year_label
                )
                
                self.ax.add_patch(rect)
                self.water_year_patches.append(rect)
                
                # Add a text label in the center of the patch
                text_x = mdates.date2num(start_date) + (mdates.date2num(end_date) - mdates.date2num(start_date)) / 2
                text = self.ax.text(
                    text_x,
                    ymax - (ymax - ymin) * 0.05,  # Near the top
                    water_year_label,
                    ha='center',
                    va='top',
                    fontsize=9,
                    color='gray',
                    alpha=0.7,
                    zorder=-1
                )
                self.water_year_patches.append(text)
            
            # Update the canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error highlighting water years: {e}")
            logger.error(traceback.format_exc())

    def set_water_year_highlight(self, enable=False):
        """Enable or disable water year highlighting.
        
        Args:
            enable (bool): Whether to enable water year highlighting
        """
        self.show_water_year_highlight = enable
        self.highlight_water_years(enable)
        
    def set_gaps_highlight(self, enable=False):
        """Enable or disable data gaps highlighting.
        
        Args:
            enable (bool): Whether to enable gaps highlighting
        """
        self.show_gaps_highlight = enable
        self.highlight_gaps(enable)
        
    def highlight_gaps(self, enable=None):
        """
        Add semi-transparent highlights for gaps in the data sampling larger than 15 minutes.
        The color matches the well line color with 80% transparency.
        
        Args:
            enable (bool, optional): Whether to enable gaps highlighting. If None, use the class attribute.
        """
        try:
            # Use the provided parameter or fall back to the class attribute
            if enable is None:
                enable = getattr(self, 'show_gaps_highlight', False)
            else:
                self.show_gaps_highlight = enable
                
            # Clear any existing gap patches
            if hasattr(self, 'gap_patches'):
                for patch in self.gap_patches:
                    try:
                        patch.remove()
                    except:
                        pass  # Ignore if already removed
            
            self.gap_patches = []
            
            if not enable:
                # Update the canvas and return
                self.canvas.draw()
                return
                
            # Get current x-axis limits
            xmin, xmax = self.ax.get_xlim()
            ymin, ymax = self.ax.get_ylim()
            
            # Loop through each line in the plot
            for line in self.ax.get_lines():
                # Skip non-well data lines (skip manual readings, trend lines, etc.)
                if not line.get_label().startswith('Well') and not line.get_label().startswith('TN') and not line.get_label().startswith('MS'):
                    continue
                
                # Get the line data and color
                xdata = line.get_xdata()
                line_color = line.get_color()
                well_name = line.get_label()
                
                # Skip if not enough data points
                if len(xdata) < 2:
                    continue
                    
                # Check for gaps (timestamps more than 15 minutes apart)
                gap_threshold = pd.Timedelta(minutes=15)
                gap_ranges = []
                
                # Convert to pandas datetime if not already
                xdata_pd = pd.Series(xdata)
                
                # Calculate time differences
                time_diffs = xdata_pd.diff()
                
                # Find gaps
                for i in range(1, len(xdata_pd)):
                    if time_diffs.iloc[i] > gap_threshold:
                        # Found a gap - record the start and end time
                        gap_start = xdata_pd.iloc[i-1]
                        gap_end = xdata_pd.iloc[i]
                        gap_ranges.append((gap_start, gap_end))
                
                # Create patches for each gap
                for gap_start, gap_end in gap_ranges:
                    # Convert to matplotlib date numbers if needed
                    gap_start_num = mdates.date2num(gap_start) if not isinstance(gap_start, float) else gap_start
                    gap_end_num = mdates.date2num(gap_end) if not isinstance(gap_end, float) else gap_end
                    
                    # Create a semi-transparent rectangle for the gap
                    # Use the same color as the line with 80% transparency (alpha=0.2)
                    rect = plt.Rectangle(
                        (gap_start_num, ymin),
                        gap_end_num - gap_start_num,
                        ymax - ymin,
                        color=line_color,
                        alpha=0.2,
                        zorder=-1,  # Put behind data
                        label=f"{well_name} gap"
                    )
                    
                    self.ax.add_patch(rect)
                    self.gap_patches.append(rect)
            
            # Update the canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error highlighting gaps: {e}")
            logger.error(traceback.format_exc())