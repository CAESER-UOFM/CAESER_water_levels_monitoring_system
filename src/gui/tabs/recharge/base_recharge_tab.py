"""Base class for recharge calculation tabs with standardized plotting."""

import logging
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSplitter, QGroupBox, QCheckBox)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BaseRechargeTab(QWidget):
    """Base class for all recharge calculation tabs with standardized plotting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.data_manager = None
        self.raw_data = None
        self.processed_data = None
        self.display_data = None
        self.current_well_id = None
        
        # Initialize plotting components
        self._init_plot_components()
        
    def _init_plot_components(self):
        """Initialize matplotlib figure and canvas."""
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        
    def create_plot_display_options(self):
        """Create standardized plot display options for all tabs with compact layout."""
        options_group = QGroupBox("Display Options")
        options_layout = QHBoxLayout(options_group)  # Changed to horizontal layout
        options_layout.setContentsMargins(8, 8, 8, 8)  # Reduce margins
        options_layout.setSpacing(12)  # Consistent spacing between items
        
        # Checkboxes for display options - arranged in two rows
        left_column = QVBoxLayout()
        left_column.setSpacing(4)  # Tight vertical spacing
        
        self.show_raw_data = QCheckBox("Show Raw Data")
        self.show_raw_data.setChecked(True)
        self.show_raw_data.stateChanged.connect(self.update_plot)
        left_column.addWidget(self.show_raw_data)
        
        self.show_processed_data = QCheckBox("Show Processed Data")
        self.show_processed_data.setChecked(False)
        self.show_processed_data.stateChanged.connect(self.update_plot)
        left_column.addWidget(self.show_processed_data)
        
        right_column = QVBoxLayout()
        right_column.setSpacing(4)  # Tight vertical spacing
        
        self.show_grid = QCheckBox("Show Grid")
        self.show_grid.setChecked(True)
        self.show_grid.stateChanged.connect(self.update_plot)
        right_column.addWidget(self.show_grid)
        
        self.show_legend = QCheckBox("Show Legend")
        self.show_legend.setChecked(True)
        self.show_legend.stateChanged.connect(self.update_plot)
        right_column.addWidget(self.show_legend)
        
        # Add columns to main layout
        options_layout.addLayout(left_column)
        options_layout.addLayout(right_column)
        options_layout.addStretch()  # Push everything to the left
        
        # Set maximum height to keep it compact
        options_group.setMaximumHeight(70)
        
        return options_group
        
    def update_plot_base(self):
        """Base plotting method that creates a standardized raw data visualization.
        
        This method should be called by child classes' update_plot() method
        to ensure consistent base plotting across all tabs.
        """
        try:
            # Clear the figure
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Set up the plot with professional styling
            ax.set_facecolor('#f8f9fa')
            self.figure.patch.set_facecolor('white')
            
            # Plot raw data if available and checkbox is checked
            if (hasattr(self, 'show_raw_data') and self.show_raw_data.isChecked() and 
                self.raw_data is not None and not self.raw_data.empty):
                
                # Use the standardized column names (after processing)
                if 'timestamp_utc' in self.raw_data.columns:
                    timestamps = pd.to_datetime(self.raw_data['timestamp_utc'])
                    levels = self.raw_data['water_level']
                else:
                    timestamps = pd.to_datetime(self.raw_data['timestamp'])
                    levels = self.raw_data['water_level']
                
                # Plot with professional styling
                ax.plot(timestamps, levels, 
                       color='#1f77b4',  # Professional blue
                       linewidth=1.0,
                       alpha=0.8,
                       label='Raw Water Level Data',
                       zorder=1)
                       
            # Plot processed data if available and checkbox is checked
            if (hasattr(self, 'show_processed_data') and self.show_processed_data.isChecked() and 
                self.processed_data is not None and not self.processed_data.empty):
                
                # Handle different column formats
                if 'timestamp_utc' in self.processed_data.columns:
                    proc_timestamps = pd.to_datetime(self.processed_data['timestamp_utc'])
                    proc_levels = self.processed_data['water_level']
                elif 'timestamp' in self.processed_data.columns:
                    proc_timestamps = pd.to_datetime(self.processed_data['timestamp'])
                    proc_levels = self.processed_data['water_level']
                else:
                    # If timestamp is the index
                    proc_timestamps = self.processed_data.index
                    proc_levels = self.processed_data.iloc[:, 0]
                
                # Plot processed data with different style
                ax.plot(proc_timestamps, proc_levels,
                       color='#2ca02c',  # Professional green
                       linewidth=2.0,
                       alpha=0.9,
                       label='Processed Data',
                       zorder=2)
            
            # Set labels and title
            ax.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax.set_ylabel('Water Level (ft)', fontsize=12, fontweight='bold')
            
            # Get well name for title
            well_name = "Unknown Well"
            if hasattr(self, 'well_combo') and self.well_combo.currentText():
                well_name = self.well_combo.currentText()
            
            method_name = self.get_method_name()  # Child classes should implement this
            ax.set_title(f'{method_name} Analysis - {well_name}', 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Configure grid
            if hasattr(self, 'show_grid') and self.show_grid.isChecked():
                ax.grid(True, linestyle='--', alpha=0.3, color='gray')
                ax.set_axisbelow(True)
            
            # Configure legend
            if hasattr(self, 'show_legend') and self.show_legend.isChecked():
                legend = ax.legend(loc='best', frameon=True, fancybox=True, 
                                 shadow=True, fontsize=10)
                legend.get_frame().set_alpha(0.9)
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # Rotate date labels for better readability
            self.figure.autofmt_xdate(rotation=45, ha='right')
            
            # Set y-axis to show water levels with proper range
            if self.raw_data is not None and not self.raw_data.empty:
                y_min = self.raw_data['water_level'].min()
                y_max = self.raw_data['water_level'].max()
                y_range = y_max - y_min
                ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)
            
            # Add subtle box around plot
            for spine in ax.spines.values():
                spine.set_edgecolor('#cccccc')
                spine.set_linewidth(1)
            
            # Ensure tight layout with padding for title
            self.figure.tight_layout(pad=3.0)
            
            # Draw the canvas
            self.canvas.draw()
            
            return ax  # Return axes for child classes to add their specific elements
            
        except Exception as e:
            logger.error(f"Error in base plot update: {e}")
            self._show_error_plot(str(e))
            return None
            
    def _show_error_plot(self, error_message="An error occurred"):
        """Show an error message on the plot."""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'Error: {error_message}', 
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes,
                   fontsize=12,
                   color='red')
            ax.set_xlabel('Date')
            ax.set_ylabel('Water Level (ft)')
            self.canvas.draw()
        except Exception as e:
            logger.error(f"Error showing error plot: {e}")
            
    def _show_empty_plot(self, message="No data available"):
        """Show an empty plot with a message."""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Set up the plot with professional styling
            ax.set_facecolor('#f8f9fa')
            self.figure.patch.set_facecolor('white')
            
            # Add message
            ax.text(0.5, 0.5, message, 
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes,
                   fontsize=14,
                   color='#666666')
                   
            # Set labels
            ax.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax.set_ylabel('Water Level (ft)', fontsize=12, fontweight='bold')
            
            method_name = self.get_method_name() if hasattr(self, 'get_method_name') else "Recharge"
            ax.set_title(f'{method_name} Analysis', fontsize=14, fontweight='bold', pad=20)
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.3, color='gray')
            ax.set_axisbelow(True)
            
            # Add subtle box around plot
            for spine in ax.spines.values():
                spine.set_edgecolor('#cccccc')
                spine.set_linewidth(1)
                
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error showing empty plot: {e}")
            
    def get_method_name(self):
        """Get the method name for this tab. Should be overridden by child classes."""
        return "Recharge"
        
    def update_plot(self):
        """Update the plot - calls base plotting and allows child classes to add specifics."""
        ax = self.update_plot_base()
        if ax:
            # Child classes can override this to add their specific plotting elements
            self.add_method_specific_plots(ax)
            
    def add_method_specific_plots(self, ax):
        """Override this in child classes to add method-specific plotting elements."""
        pass
        
    def standardize_dataframe(self, df):
        """Standardize dataframe column names and formats."""
        # Check column names and rename if necessary
        if 'timestamp_utc' in df.columns and 'water_level' in df.columns:
            df = df.rename(columns={
                'timestamp_utc': 'timestamp'
                # Keep 'water_level' as is - don't rename to 'level'
            })
        
        # Make sure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df