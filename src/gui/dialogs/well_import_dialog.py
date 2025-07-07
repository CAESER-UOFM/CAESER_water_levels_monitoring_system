# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 12:06:59 2025

@author: bledesma
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                           QPushButton, QTableWidget, QTableWidgetItem,
                           QCheckBox, QMessageBox, QLabel)
from PyQt5.QtCore import Qt
import pandas as pd
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class WellImportDialog(QDialog):
    def __init__(self, well_model, csv_path: str, parent=None):
        super().__init__(parent)
        self.well_model = well_model
        self.csv_path = csv_path
        self.df = None
        self.required_columns = ['WN', 'LAT', 'LON', 'TOC', 'AQ']
        self.optional_columns = ['data_source']  # Add this line to track optional columns
        
        # Column mapping for exported CSV files from the table export tool
        self.column_mapping = {
            'well_number': 'WN',
            'latitude': 'LAT', 
            'longitude': 'LON',
            'top_of_casing': 'TOC',
            'aquifer': 'AQ',
            'cae_number': 'CAE'  # Optional mapping
        }
        
        self.setup_ui()
        self.load_csv()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Import Wells from CSV")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        # Select All checkbox
        self.select_all = QCheckBox("Select All")
        self.select_all.setChecked(True)
        self.select_all.stateChanged.connect(self.toggle_all_rows)
        bottom_layout.addWidget(self.select_all)
        
        bottom_layout.addStretch()
        
        # Import and Cancel buttons
        import_btn = QPushButton("Import Selected")
        import_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        bottom_layout.addWidget(import_btn)
        bottom_layout.addWidget(cancel_btn)
        
        layout.addLayout(bottom_layout)
    
    def load_csv(self):
        """Load and validate CSV data"""
        try:
            self.df = pd.read_csv(self.csv_path)
            
            # Apply column mapping if the CSV uses exported table format
            columns_to_rename = {}
            for old_col, new_col in self.column_mapping.items():
                if old_col in self.df.columns:
                    columns_to_rename[old_col] = new_col
            
            if columns_to_rename:
                logger.info(f"Mapping columns from exported format: {columns_to_rename}")
                self.df = self.df.rename(columns=columns_to_rename)
            
            # Validate required columns
            missing_cols = [col for col in self.required_columns 
                          if col not in self.df.columns]
            if missing_cols:
                # Check if we can map any missing columns
                available_mappings = []
                for missing_col in missing_cols:
                    for old_col, new_col in self.column_mapping.items():
                        if new_col == missing_col and old_col in self.df.columns:
                            available_mappings.append(f"{old_col} → {new_col}")
                
                error_msg = f"Missing required columns: {', '.join(missing_cols)}"
                if available_mappings:
                    error_msg += f"\n\nNote: Found potential mappings: {', '.join(available_mappings)}"
                    error_msg += "\nPlease use column headers: WN, LAT, LON, TOC, AQ"
                else:
                    error_msg += "\n\nExpected column headers: WN (well number), LAT (latitude), LON (longitude), TOC (top of casing), AQ (aquifer)"
                
                raise ValueError(error_msg)
            
            # Setup table
            self.table.setRowCount(len(self.df))
            self.table.setColumnCount(len(self.df.columns) + 1)  # +1 for checkbox
            
            # Set headers
            headers = ['Select'] + list(self.df.columns)
            self.table.setHorizontalHeaderLabels(headers)
            
            # Fill data
            for row in range(len(self.df)):
                # Add checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                self.table.setCellWidget(row, 0, checkbox)
                
                # Add data
                for col in range(len(self.df.columns)):
                    item = QTableWidgetItem(str(self.df.iloc[row, col]))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, col + 1, item)
            
            self.status_label.setText(f"Found {len(self.df)} wells")
            self.status_label.setStyleSheet("color: green")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: red")
            logger.error(f"Error loading CSV: {e}")
    
    def toggle_all_rows(self, state):
        """Toggle all checkboxes"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.Checked)
    
    def get_selected_wells(self) -> List[Dict]:
        """Get data for selected wells"""
        selected_wells = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                well_data = {}
                for col in range(1, self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col).text()
                    item = self.table.item(row, col)
                    well_data[header] = item.text()
                selected_wells.append(well_data)
        return selected_wells
    
    def validate_data(self) -> bool:
        """Validate data before import"""
        try:
            selected_wells = self.get_selected_wells()
            if not selected_wells:
                raise ValueError("No wells selected for import")
            
            # Check numeric values
            for well in selected_wells:
                float(well['LAT'])  # Check latitude
                float(well['LON'])  # Check longitude
                float(well['TOC'])  # Check top of casing
                
                # Check coordinate ranges
                lat = float(well['LAT'])
                lon = float(well['LON'])
                if not (-90 <= lat <= 90):
                    raise ValueError(f"Invalid latitude for well {well['WN']}: {lat}")
                if not (-180 <= lon <= 180):
                    raise ValueError(f"Invalid longitude for well {well['WN']}: {lon}")
            
            return True
            
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Validation error: {str(e)}")
            return False
    
    def accept(self):
        """Handle dialog acceptance"""
        if not self.validate_data():
            return
            
        selected_wells = self.get_selected_wells()
        try:
            success, message = self.well_model.import_wells(selected_wells)
            if success:
                super().accept()
            else:
                QMessageBox.critical(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))