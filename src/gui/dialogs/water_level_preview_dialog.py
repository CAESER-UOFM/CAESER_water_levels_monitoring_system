# -*- coding: utf-8 -*-
"""
Created on Sun Feb  2 21:47:22 2025

@author: Benja
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QGroupBox, QTabWidget, QWidget, QTableWidget, 
                           QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg,
                                              NavigationToolbar2QT)  # Add this import
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class WaterLevelPreviewDialog(QDialog):
    def __init__(self, well_number: str, well_data: dict, parent=None):
        super().__init__(parent)
        self.well_number = well_number
        self.well_data = well_data
        self.setup_ui()
        self.populate_data()
        
    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle(f"Data Preview - Well {self.well_number}")
        self.resize(1200, 800)
        layout = QVBoxLayout(self)
        
        # Info section
        info_layout = QHBoxLayout()
        self.info_label = QLabel()
        info_layout.addWidget(self.info_label)
        layout.addLayout(info_layout)
        
        # Tab widget for different views
        tab_widget = QTabWidget()
        
        # Plot tab
        plot_tab = QWidget()
        plot_layout = QVBoxLayout()
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_tab.setLayout(plot_layout)
        tab_widget.addTab(plot_tab, "Visualization")
        
        # Data tab
        data_tab = QWidget()
        data_layout = QVBoxLayout()
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        data_layout.addWidget(self.data_table)
        data_tab.setLayout(data_layout)
        tab_widget.addTab(data_tab, "Data")
        
        layout.addWidget(tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
    def populate_data(self):
        """Populate dialog with well data"""
        try:
            # Update info label
            info_text = [
                f"Well: {self.well_number}",
                f"Files: {len(self.well_data['files'])}",
            ]
            
            if 'processed_data' in self.well_data:
                data = self.well_data['processed_data']
                info_text.extend([
                    f"Records: {len(data)}",
                    f"Time Range: {data['timestamp_utc'].min().strftime('%Y-%m-%d %H:%M')} to {data['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M')} (UTC)"
                ])
            
            self.info_label.setText(" | ".join(info_text))
            
            # Create plot
            self.plot_data()
            
            # Populate data table
            self.populate_table()
            
        except Exception as e:
            logger.error(f"Error populating preview: {e}")
            
    def plot_data(self):
        """Plot water level data with color-coded segments and overlaps"""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Plot existing data in black/gray first (for context)
            if 'existing_data' in self.well_data:
                existing = self.well_data['existing_data']
                if not existing.empty:
                    # Replace the data_source filtering with a single plot
                    ax.plot(existing['timestamp_utc'], existing['water_level'],
                           color='black', alpha=0.3, linewidth=1,
                           label='Existing Data')

            # Color palette for new data segments
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            
            # Plot each new file's data in a different color
            for idx, file_info in enumerate(self.well_data['files']):
                color = colors[idx % len(colors)]
                file_data = file_info['processed_data']
                
                # Plot the segment
                ax.plot(file_data['timestamp_utc'], file_data['water_level'],
                       color=color, linewidth=1.5,
                       label=f"File {idx+1}: {file_data['timestamp_utc'].min().strftime('%Y-%m-%d')} to {file_data['timestamp_utc'].max().strftime('%Y-%m-%d')}")
                
                # Highlight overlap regions if any
                if file_info.get('has_overlap'):
                    overlap_start, overlap_end = file_info['overlap_range']
                    ax.axvspan(overlap_start, overlap_end,
                             color='yellow', alpha=0.2)
                
                # Mark the beginning of each segment with a star
                if not file_data.empty:
                    start_point = file_data.iloc[0]
                    ax.scatter(start_point['timestamp_utc'], 
                             start_point['water_level'],
                             color='red', marker='*', s=100)

            # Formatting
            ax.set_title(f"Well {self.well_number} Water Levels")
            ax.set_xlabel('Time (UTC)')
            ax.set_ylabel('Water Level (ft)')
            ax.grid(True, linestyle='--', alpha=0.6)
            
            # Legend with custom placement
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left',
                     borderaxespad=0., title="Data Sources")
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error plotting data: {e}")
            
    def populate_table(self):
        """Populate the data table"""
        try:
            if 'processed_data' not in self.well_data:
                return
                
            df = self.well_data['processed_data']
            
            # Set up table
            self.data_table.setRowCount(len(df))
            headers = ['Timestamp (UTC)', 'Pressure', 'Water Level', 'Temperature',
                      'Level Method']
            self.data_table.setColumnCount(len(headers))
            self.data_table.setHorizontalHeaderLabels(headers)
            
            # Populate data
            for row, (_, data) in enumerate(df.iterrows()):
                self.data_table.setItem(row, 0, QTableWidgetItem(
                    data['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S')))
                self.data_table.setItem(row, 1, QTableWidgetItem(
                    f"{data['pressure']:.3f}"))
                self.data_table.setItem(row, 2, QTableWidgetItem(
                    f"{data['water_level']:.3f}"))
                self.data_table.setItem(row, 3, QTableWidgetItem(
                    f"{data['temperature']:.2f}"))
                self.data_table.setItem(row, 4, QTableWidgetItem(
                    str(data['level_flag'])))
                
        except Exception as e:
            logger.error(f"Error populating table: {e}")