# -*- coding: utf-8 -*-
"""
Enhanced Plot Dialog - Professional plot viewer with advanced features
Based on DataExportVisualizerDialog but simplified for plot viewing
"""

import logging
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.backend_bases import MouseButton
from matplotlib.patches import Rectangle, Patch
import matplotlib.dates as mdates
from datetime import timedelta
from typing import List, Tuple
import itertools
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSplitter, QWidget, QShortcut, QStatusBar,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence

logger = logging.getLogger(__name__)

class EnhancedPlotDialog(QDialog):
    """Enhanced plot viewer dialog with professional features and theming."""
    
    def __init__(self, parent=None, plot_data=None, plot_title="Enhanced Plot View"):
        super().__init__(parent)
        self.plot_data = plot_data
        self.plot_title = plot_title
        self.theme = "light"
        
        # Gap highlighting settings (copied from main plot handler)
        self.gap_highlight_enabled = True
        self.gap_color = "#FFEBEE"  # Light red background for gaps
        self.gap_threshold = timedelta(minutes=20)  # Gap threshold (> 20 min sample interval)
        self.gap_alpha = 0.6
        
        # Interactive features
        self.selected_point_annotation = None
        
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_plot_interaction()
        
        if plot_data is not None:
            self.update_plot()
    
    def setup_ui(self):
        """Setup the enhanced plot dialog UI."""
        self.setWindowTitle("Enhanced Plot View")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create splitter for resizable layout
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create plot area (left side)
        plot_widget = self.create_plot_area()
        splitter.addWidget(plot_widget)
        
        # Create controls panel (right side)
        controls_widget = self.create_controls_panel()
        splitter.addWidget(controls_widget)
        
        # Set splitter proportions (plot takes most space)
        splitter.setSizes([1000, 300])
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready | F11: Fullscreen | Ctrl+E: Export | Ctrl+T: Toggle Theme")
        main_layout.addWidget(self.status_bar)
        
        # Apply initial theme
        self.apply_theme()
    
    def create_plot_area(self):
        """Create the main plot area with navigation."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, widget)
        
        # Customize toolbar
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                spacing: 2px;
                padding: 4px;
            }
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
                margin: 1px;
            }
            QToolButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QToolButton:pressed {
                background-color: #dee2e6;
            }
        """)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        return widget
    
    def create_controls_panel(self):
        """Create the controls panel for plot customization."""
        widget = QWidget()
        widget.setMaximumWidth(300)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 0, 0, 0)
        
        # Plot settings group
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Theme selection
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Blue", "Earth"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addLayout(theme_layout)
        
        # Grid options
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self.toggle_grid)
        settings_layout.addWidget(self.grid_checkbox)
        
        # Data gaps
        self.gaps_checkbox = QCheckBox("Highlight Data Gaps")
        self.gaps_checkbox.setChecked(True)
        self.gaps_checkbox.toggled.connect(self.toggle_gaps)
        settings_layout.addWidget(self.gaps_checkbox)
        
        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_spinbox = QSpinBox()
        self.font_spinbox.setRange(8, 20)
        self.font_spinbox.setValue(10)
        self.font_spinbox.valueChanged.connect(self.update_font_size)
        font_layout.addWidget(self.font_spinbox)
        settings_layout.addLayout(font_layout)
        
        # Line width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Line Width:"))
        self.width_spinbox = QDoubleSpinBox()
        self.width_spinbox.setRange(0.5, 5.0)
        self.width_spinbox.setValue(1.0)
        self.width_spinbox.setSingleStep(0.5)
        self.width_spinbox.valueChanged.connect(self.update_line_width)
        width_layout.addWidget(self.width_spinbox)
        settings_layout.addLayout(width_layout)
        
        layout.addWidget(settings_group)
        
        # Export group
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        self.export_btn = QPushButton("Export Plot")
        self.export_btn.clicked.connect(self.export_plot)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        export_layout.addWidget(self.export_btn)
        
        layout.addWidget(export_group)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        return widget
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Fullscreen toggle
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        
        # Export shortcut
        self.export_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.export_shortcut.activated.connect(self.export_plot)
        
        # Theme toggle
        self.theme_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.theme_shortcut.activated.connect(self.cycle_theme)
    
    def setup_plot_interaction(self):
        """Set up interactive features for the plot"""
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
    
    def color_cycle(self):
        """Return an iterator over a list of colors (copied from main plot handler)."""
        return itertools.cycle(['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'])
    
    def identify_data_gaps(self, df: pd.DataFrame) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
        """Identify gaps in time series data where the interval between samples exceeds the threshold."""
        if df is None or df.empty or 'timestamp' not in df.columns:
            return []
            
        # Sort by timestamp to ensure chronological order
        sorted_df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate time differences between consecutive points
        time_diffs = sorted_df['timestamp'].diff()
        
        # Find indices where the time difference exceeds the threshold
        gap_indices = time_diffs[time_diffs > self.gap_threshold].index.tolist()
        
        gaps = []
        for idx in gap_indices:
            gap_start = sorted_df.loc[idx-1, 'timestamp']
            gap_end = sorted_df.loc[idx, 'timestamp']
            gaps.append((gap_start, gap_end))
            
        return gaps
    
    def highlight_data_gaps(self, ax, gaps: List[Tuple[pd.Timestamp, pd.Timestamp]], y_min: float, y_max: float):
        """Add background highlighting for data gaps."""
        if not gaps or not self.gap_highlight_enabled or not self.gaps_checkbox.isChecked():
            return
            
        for gap_start, gap_end in gaps:
            # Add a rectangle spanning the gap with a distinctive color
            rect = Rectangle(
                (mdates.date2num(gap_start), y_min),
                mdates.date2num(gap_end) - mdates.date2num(gap_start),
                y_max - y_min,
                color=self.gap_color,
                alpha=self.gap_alpha,
                zorder=-100  # Place behind other plot elements
            )
            ax.add_patch(rect)
    
    def update_plot(self):
        """Update the plot with current data and settings (enhanced with gap detection and professional styling)."""
        if self.plot_data is None:
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Clear any existing annotations
        if self.selected_point_annotation:
            self.selected_point_annotation = None
        
        colors = self.color_cycle()
        legend_handles = []
        legend_labels = []
        all_gaps = []
        all_times = []
        all_levels = []
        
        # Plot data for each well
        for well_id, data in self.plot_data.items():
            if not isinstance(data, pd.DataFrame) or data.empty:
                continue
                
            color = next(colors)
            
            # Convert timestamp to datetime if needed
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            elif 'date_time' in data.columns:
                data['timestamp'] = pd.to_datetime(data['date_time'])
                data = data.rename(columns={'date_time': 'timestamp'})
            else:
                continue
            
            # Get y data column name
            y_column = None
            if 'water_level' in data.columns:
                y_column = 'water_level'
            elif 'pressure' in data.columns:
                y_column = 'pressure'
            else:
                continue
            
            # Separate transducer and manual data if source_type exists
            if 'source_type' in data.columns:
                transducer_data = data[data['source_type'] == 'transducer'].copy()
                manual_data = data[data['source_type'] == 'manual'].copy()
                
                # Plot transducer data as line
                if not transducer_data.empty:
                    # Detect gaps in transducer data
                    gaps = self.identify_data_gaps(transducer_data)
                    all_gaps.extend(gaps)
                    
                    line_width = self.width_spinbox.value()
                    line, = ax.plot(transducer_data['timestamp'], transducer_data[y_column], 
                                   color=color, linewidth=line_width, alpha=0.8, 
                                   label=f"{well_id} (Transducer)")
                    legend_handles.append(line)
                    legend_labels.append(f"{well_id} (Transducer)")
                    
                    # Collect data for scaling
                    all_times.extend(transducer_data['timestamp'].tolist())
                    all_levels.extend(transducer_data[y_column].tolist())
                
                # Plot manual data as scatter points
                if not manual_data.empty:
                    scatter = ax.scatter(manual_data['timestamp'], manual_data[y_column],
                                       color=color, marker='o', s=50, alpha=0.9,
                                       edgecolor='black', linewidth=1.2, zorder=10,
                                       label=f"{well_id} (Manual)")
                    legend_handles.append(scatter)
                    legend_labels.append(f"{well_id} (Manual)")
                    
                    # Collect data for scaling
                    all_times.extend(manual_data['timestamp'].tolist())
                    all_levels.extend(manual_data[y_column].tolist())
            else:
                # Plot as single dataset (assume transducer data for gap detection)
                gaps = self.identify_data_gaps(data)
                all_gaps.extend(gaps)
                
                line_width = self.width_spinbox.value()
                line, = ax.plot(data['timestamp'], data[y_column], 
                               color=color, linewidth=line_width, alpha=0.8, 
                               label=well_id)
                legend_handles.append(line)
                legend_labels.append(well_id)
                
                # Collect data for scaling
                all_times.extend(data['timestamp'].tolist())
                all_levels.extend(data[y_column].tolist())
        
        # Apply gap highlighting if we have data and gaps
        if all_times and all_levels and all_gaps:
            y_min, y_max = min(all_levels), max(all_levels)
            y_range = y_max - y_min
            y_margin = y_range * 0.05  # 5% margin
            self.highlight_data_gaps(ax, all_gaps, y_min - y_margin, y_max + y_margin)
        
        # Format the plot
        ax.set_title(self.plot_title, fontsize=self.font_spinbox.value() + 2, fontweight='bold')
        ax.set_xlabel('Date/Time', fontsize=self.font_spinbox.value())
        
        # Determine y-axis label based on data type
        if any('pressure' in str(data.columns) for data in self.plot_data.values()):
            ax.set_ylabel('Pressure (PSI)', fontsize=self.font_spinbox.value())
        else:
            ax.set_ylabel('Water Level (ft)', fontsize=self.font_spinbox.value())
        
        # Apply grid if enabled
        if self.grid_checkbox.isChecked():
            ax.grid(True, linestyle='--', alpha=0.7)
        
        # Format date axis
        self.format_date_axis(ax)
        
        # Create enhanced legend with gap information
        if legend_handles:
            # Add gap patch to legend if gaps exist and highlighting is enabled
            if all_gaps and self.gaps_checkbox.isChecked():
                gap_patch = Patch(facecolor=self.gap_color, alpha=self.gap_alpha, 
                                label=f'Data Gaps (>{self.gap_threshold.total_seconds()/60:.0f}min)')
                legend_handles.append(gap_patch)
                legend_labels.append(f'Data Gaps (>{self.gap_threshold.total_seconds()/60:.0f}min)')
            
            # Create draggable legend
            legend = ax.legend(handles=legend_handles, labels=legend_labels, 
                             loc='best', fontsize=self.font_spinbox.value() - 1)
            legend.set_draggable(True)
        
        # Tight layout
        self.figure.tight_layout()
        self.canvas.draw()
    
    def format_date_axis(self, ax):
        """Apply intelligent date formatting (same as main plots)."""
        import matplotlib.dates as mdates
        
        try:
            # Get the current x-axis limits to determine data range
            xlim = ax.get_xlim()
            date_range_days = xlim[1] - xlim[0]  # Range in matplotlib date units (days)
            
            # Determine appropriate tick spacing and format based on data range
            if date_range_days <= 7:  # Less than a week
                try:
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                except TypeError:
                    # Fallback for older matplotlib versions
                    ax.xaxis.set_major_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                try:
                    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                except TypeError:
                    ax.xaxis.set_minor_locator(mdates.HourLocator())
            elif date_range_days <= 30:  # Less than a month
                interval = max(1, int(date_range_days / 6))  # ~6 ticks maximum
                try:
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                except TypeError:
                    # Fallback for older matplotlib versions
                    ax.xaxis.set_major_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_minor_locator(mdates.DayLocator())
            elif date_range_days <= 365:  # Less than a year
                interval = max(1, int(date_range_days / 180))  # ~6 ticks maximum
                try:
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
                except TypeError:
                    # Fallback for older matplotlib versions
                    ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
                ax.xaxis.set_minor_locator(mdates.MonthLocator())
            elif date_range_days <= 1095:  # Less than 3 years
                try:
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                except TypeError:
                    # Fallback for older matplotlib versions
                    ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
                ax.xaxis.set_minor_locator(mdates.MonthLocator())
            else:  # More than 3 years
                interval = max(1, int(date_range_days / 1825))  # ~6 ticks maximum
                try:
                    ax.xaxis.set_major_locator(mdates.YearLocator(interval=interval))
                except TypeError:
                    # Fallback for older matplotlib versions
                    ax.xaxis.set_major_locator(mdates.YearLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
                try:
                    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=6))
                except TypeError:
                    ax.xaxis.set_minor_locator(mdates.MonthLocator())
        except Exception as e:
            logger.warning(f"Error formatting date axis, using default formatting: {e}")
            # Fallback to basic date formatting
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
        
        # Format labels
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=self.font_spinbox.value())
    
    def apply_theme(self):
        """Apply the selected theme to the dialog."""
        themes = {
            "light": {
                "bg": "#ffffff", 
                "fg": "#333333",
                "plot_bg": "#ffffff",
                "grid": "#dddddd"
            },
            "dark": {
                "bg": "#2b2b2b", 
                "fg": "#ffffff",
                "plot_bg": "#3c3c3c",
                "grid": "#666666"
            },
            "blue": {
                "bg": "#f8f9fa", 
                "fg": "#1a365d",
                "plot_bg": "#ffffff",
                "grid": "#bee5ff"
            },
            "earth": {
                "bg": "#f7f5f3", 
                "fg": "#5a3e2b",
                "plot_bg": "#fefefe",
                "grid": "#d4c4a8"
            }
        }
        
        theme_colors = themes.get(self.theme, themes["light"])
        
        # Apply dialog styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_colors['bg']};
                color: {theme_colors['fg']};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 6px;
                padding-top: 6px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        
        # Apply plot styling
        if hasattr(self, 'figure'):
            self.figure.patch.set_facecolor(theme_colors['plot_bg'])
            self.canvas.draw()
    
    def change_theme(self, theme_name):
        """Change the current theme."""
        self.theme = theme_name.lower()
        self.apply_theme()
        self.update_plot()
    
    def cycle_theme(self):
        """Cycle through themes with keyboard shortcut."""
        themes = ["light", "dark", "blue", "earth"]
        current_index = themes.index(self.theme)
        next_index = (current_index + 1) % len(themes)
        new_theme = themes[next_index]
        
        self.theme_combo.setCurrentText(new_theme.title())
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.status_bar.showMessage("Exited fullscreen mode | F11: Fullscreen | Ctrl+E: Export | Ctrl+T: Toggle Theme")
        else:
            self.showFullScreen()
            self.status_bar.showMessage("Fullscreen mode | F11: Exit Fullscreen | Ctrl+E: Export | Ctrl+T: Toggle Theme")
    
    def toggle_grid(self, checked):
        """Toggle grid display."""
        self.update_plot()
    
    def toggle_gaps(self, checked):
        """Toggle data gaps highlighting."""
        self.update_plot()
    
    def update_font_size(self):
        """Update plot font size."""
        self.update_plot()
    
    def update_line_width(self):
        """Update plot line width."""
        self.update_plot()
    
    def export_plot(self):
        """Export the current plot."""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            f"enhanced_plot_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG files (*.png);;JPEG files (*.jpg);;PDF files (*.pdf);;SVG files (*.svg)"
        )
        
        if file_path:
            try:
                # Get DPI for high quality export
                dpi = 300 if file_path.lower().endswith('.pdf') else 150
                self.figure.savefig(file_path, dpi=dpi, bbox_inches='tight', 
                                  facecolor='white', edgecolor='none')
                self.status_bar.showMessage(f"Plot exported to: {file_path}", 5000)
            except Exception as e:
                self.status_bar.showMessage(f"Export failed: {str(e)}", 5000)
    
    def on_plot_click(self, event):
        """Handle click events on plot (copied and adapted from main plot handler)"""
        if event.inaxes is None or event.button != MouseButton.LEFT:
            return
            
        # Remove existing annotation
        if self.selected_point_annotation:
            self.selected_point_annotation.remove()
            self.selected_point_annotation = None
            
        ax = event.inaxes
        click_x, click_y = event.xdata, event.ydata
        
        if click_x is None or click_y is None:
            return
            
        # Find closest point across all plotted data
        closest_point = None
        closest_well = None
        min_dist = float('inf')
        
        for line in ax.get_lines():
            x_data = line.get_xdata()
            y_data = line.get_ydata()
            
            if len(x_data) == 0 or len(y_data) == 0:
                continue
                
            # Convert matplotlib date numbers to timestamps for distance calculation
            x_timestamps = [mdates.num2date(x) for x in x_data]
            
            for i, (x_val, y_val) in enumerate(zip(x_timestamps, y_data)):
                # Calculate distance in plot coordinates
                x_plot = mdates.date2num(x_val)
                dist = ((x_plot - click_x) ** 2 + (y_val - click_y) ** 2) ** 0.5
                
                if dist < min_dist:
                    min_dist = dist
                    closest_point = (x_val, y_val)
                    closest_well = line.get_label()
        
        # Check scatter plots (manual readings)
        for collection in ax.collections:
            if hasattr(collection, 'get_offsets'):
                offsets = collection.get_offsets()
                if len(offsets) == 0:
                    continue
                    
                for offset in offsets:
                    x_val, y_val = offset
                    x_timestamp = mdates.num2date(x_val)
                    
                    # Calculate distance
                    dist = ((x_val - click_x) ** 2 + (y_val - click_y) ** 2) ** 0.5
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_point = (x_timestamp, y_val)
                        closest_well = collection.get_label()
        
        # Show annotation if click is close enough to a point
        if closest_point and min_dist < 50:  # Threshold for "close enough"
            # Get data source from label
            data_source = "Unknown"
            if "(" in closest_well and ")" in closest_well:
                data_source = closest_well.split('(')[-1].rstrip(')')
            
            # Format the annotation text
            text = (f"{closest_well}\n"
                   f"Date: {closest_point[0].strftime('%Y-%m-%d %H:%M')} UTC\n"
                   f"Level: {closest_point[1]:.2f} ft\n"
                   f"Source: {data_source}")
            
            # Create annotation
            self.selected_point_annotation = ax.annotate(
                text,
                xy=(mdates.date2num(closest_point[0]), closest_point[1]),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                fontsize=9
            )
            
            self.canvas.draw()