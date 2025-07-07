# -*- coding: utf-8 -*-
"""
Database Setup Dialog with CSV Pre-population

Allows users to create a new database and optionally pre-populate it with CSV data
from exported tables of previous projects.

@author: claude
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QGroupBox, QCheckBox, QMessageBox, QScrollArea,
    QWidget, QProgressBar, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

class CSVImportWorker(QThread):
    """Worker thread for CSV import processing"""
    progress_updated = pyqtSignal(int, str)
    import_completed = pyqtSignal(bool, str)
    
    def __init__(self, db_path: str, csv_files: Dict[str, str]):
        super().__init__()
        self.db_path = db_path
        self.csv_files = csv_files
        
    def run(self):
        """Import CSV files into database"""
        try:
            total_files = len(self.csv_files)
            current_file = 0
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for table_type, csv_path in self.csv_files.items():
                    current_file += 1
                    progress = int((current_file / total_files) * 100)
                    self.progress_updated.emit(progress, f"Importing {table_type}...")
                    
                    success, message = self._import_csv_to_table(cursor, table_type, csv_path)
                    if not success:
                        self.import_completed.emit(False, f"Failed to import {table_type}: {message}")
                        return
                
                conn.commit()
                
            self.import_completed.emit(True, f"Successfully imported {total_files} CSV files")
            
        except Exception as e:
            logger.error(f"CSV import error: {e}")
            self.import_completed.emit(False, f"Import failed: {str(e)}")
    
    def _import_csv_to_table(self, cursor: sqlite3.Cursor, table_type: str, csv_path: str) -> Tuple[bool, str]:
        """Import a specific CSV file into its corresponding table"""
        try:
            df = pd.read_csv(csv_path)
            
            if table_type == "wells":
                return self._import_wells(cursor, df)
            elif table_type == "barologgers":
                return self._import_barologgers(cursor, df)
            elif table_type == "barologger_locations":
                return self._import_barologger_locations(cursor, df)
            else:
                return False, f"Unknown table type: {table_type}"
                
        except Exception as e:
            return False, str(e)
    
    def _import_wells(self, cursor: sqlite3.Cursor, df: pd.DataFrame) -> Tuple[bool, str]:
        """Import wells CSV with automatic column mapping"""
        # Apply column mapping for exported format
        column_mapping = {
            'well_number': 'WN',
            'latitude': 'LAT', 
            'longitude': 'LON',
            'top_of_casing': 'TOC',
            'aquifer': 'AQ',
            'cae_number': 'CAE'
        }
        
        # Rename columns if they match exported format
        columns_to_rename = {}
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                columns_to_rename[old_col] = new_col
        
        if columns_to_rename:
            df = df.rename(columns=columns_to_rename)
        
        # Validate required columns
        required_columns = ['WN', 'LAT', 'LON', 'TOC', 'AQ']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {', '.join(missing_cols)}"
        
        # Import wells
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO wells (
                        well_number, cae_number, latitude, longitude, 
                        top_of_casing, aquifer, min_distance_to_stream,
                        well_field, cluster, county, picture_path,
                        data_source, url, parking_instructions,
                        access_requirements, safety_notes, special_instructions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['WN'],
                    row.get('CAE', row.get('cae_number')),
                    float(row['LAT']),
                    float(row['LON']),
                    float(row['TOC']),
                    row['AQ'],
                    float(row.get('min_distance_to_stream', 0)) if 'min_distance_to_stream' in row else None,
                    row.get('well_field', row.get('WF')),
                    row.get('cluster', row.get('CT')),
                    row.get('county', row.get('County')),
                    'default_well.jpg',
                    row.get('data_source', 'transducer'),
                    row.get('url'),
                    row.get('parking_instructions'),
                    row.get('access_requirements'),
                    row.get('safety_notes'),
                    row.get('special_instructions')
                ))
            except Exception as e:
                logger.warning(f"Failed to import well {row.get('WN', 'unknown')}: {e}")
                continue
                
        return True, f"Imported {len(df)} wells"
    
    def _import_barologgers(self, cursor: sqlite3.Cursor, df: pd.DataFrame) -> Tuple[bool, str]:
        """Import barologgers CSV"""
        required_columns = ['serial_number']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {', '.join(missing_cols)}"
        
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO barologgers (
                        serial_number, location_description, installation_date, status, notes
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    row['serial_number'],
                    row.get('location_description'),
                    row.get('installation_date'),
                    row.get('status', 'active'),
                    row.get('notes')
                ))
            except Exception as e:
                logger.warning(f"Failed to import barologger {row.get('serial_number', 'unknown')}: {e}")
                continue
                
        return True, f"Imported {len(df)} barologgers"
    
    def _import_barologger_locations(self, cursor: sqlite3.Cursor, df: pd.DataFrame) -> Tuple[bool, str]:
        """Import barologger locations CSV"""
        required_columns = ['serial_number']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {', '.join(missing_cols)}"
        
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO barologger_locations (
                        serial_number, location_description, start_date, end_date, notes
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    row['serial_number'],
                    row.get('location_description'),
                    row.get('start_date'),
                    row.get('end_date'),
                    row.get('notes')
                ))
            except Exception as e:
                logger.warning(f"Failed to import barologger location for {row.get('serial_number', 'unknown')}: {e}")
                continue
                
        return True, f"Imported {len(df)} barologger locations"


class DatabaseSetupDialog(QDialog):
    """Dialog for creating a new database with optional CSV pre-population"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.csv_files = {}  # Store selected CSV files
        self.parent_window = parent  # Store reference to main window for settings access
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Create New Database with Optional CSV Import")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Database Setup Wizard")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Create a new database and optionally pre-populate it with data from exported CSV files.\n"
            "This is useful for setting up new projects with wells, barologgers, and locations from previous projects."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(desc)
        
        # CSV Import Section
        csv_group = QGroupBox("Optional: Pre-populate with CSV Data")
        csv_layout = QVBoxLayout(csv_group)
        
        # Enable CSV import checkbox
        self.enable_csv_checkbox = QCheckBox("Import CSV data during database creation")
        self.enable_csv_checkbox.stateChanged.connect(self.toggle_csv_options)
        csv_layout.addWidget(self.enable_csv_checkbox)
        
        # CSV file selection area
        self.csv_widget = QWidget()
        csv_files_layout = QVBoxLayout(self.csv_widget)
        
        # Wells CSV
        wells_group = self._create_csv_file_group(
            "Wells", 
            "wells",
            "CSV file with wells data (columns: WN, LAT, LON, TOC, AQ or exported format)"
        )
        csv_files_layout.addWidget(wells_group)
        
        # Barologgers CSV
        baro_group = self._create_csv_file_group(
            "Barologgers",
            "barologgers", 
            "CSV file with barologger data (columns: serial_number, location_description, etc.)"
        )
        csv_files_layout.addWidget(baro_group)
        
        # Barologger Locations CSV
        baro_loc_group = self._create_csv_file_group(
            "Barologger Locations",
            "barologger_locations",
            "CSV file with barologger location history (columns: serial_number, location_description, start_date, etc.)"
        )
        csv_files_layout.addWidget(baro_loc_group)
        
        self.csv_widget.setEnabled(False)
        csv_layout.addWidget(self.csv_widget)
        
        layout.addWidget(csv_group)
        
        # Progress section (hidden initially)
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        
        self.progress_label = QLabel("Processing...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_log = QTextEdit()
        self.progress_log.setMaximumHeight(100)
        self.progress_log.setReadOnly(True)
        progress_layout.addWidget(self.progress_log)
        
        self.progress_widget.setVisible(False)
        layout.addWidget(self.progress_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.create_button = QPushButton("Create Database")
        self.create_button.clicked.connect(self.create_database)
        self.create_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.create_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def _create_csv_file_group(self, title: str, table_type: str, description: str) -> QGroupBox:
        """Create a CSV file selection group"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # File selection
        file_layout = QHBoxLayout()
        
        file_label = QLabel("No file selected")
        file_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; background: #f9f9f9;")
        file_layout.addWidget(file_label)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(lambda: self._select_csv_file(table_type, file_label))
        file_layout.addWidget(browse_button)
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(lambda: self._clear_csv_file(table_type, file_label))
        file_layout.addWidget(clear_button)
        
        layout.addLayout(file_layout)
        
        return group
    
    def _select_csv_file(self, table_type: str, file_label: QLabel):
        """Select a CSV file for the given table type"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {table_type.replace('_', ' ').title()} CSV File",
            "",
            "CSV files (*.csv)"
        )
        
        if file_path:
            self.csv_files[table_type] = file_path
            file_label.setText(Path(file_path).name)
            file_label.setStyleSheet("padding: 4px; border: 1px solid #4CAF50; background: #f0fff0;")
        
    def _clear_csv_file(self, table_type: str, file_label: QLabel):
        """Clear the selected CSV file"""
        if table_type in self.csv_files:
            del self.csv_files[table_type]
        file_label.setText("No file selected")
        file_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; background: #f9f9f9;")
    
    def toggle_csv_options(self, state):
        """Toggle the CSV import options"""
        self.csv_widget.setEnabled(state == Qt.Checked)
        
    def create_database(self):
        """Create the database with optional CSV import"""
        # Default to databases directory for consistency
        # Use app directory instead of current working directory
        app_dir = Path(__file__).parent.parent.parent.parent
        databases_dir = app_dir / "databases"
        databases_dir.mkdir(exist_ok=True)  # Ensure databases directory exists
        default_directory = str(databases_dir)
        
        # Get database file path with proper default directory
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Database",
            default_directory,  # Use configured database directory as default
            "Database files (*.db)"
        )
        
        if not file_path:
            return
            
        try:
            # Show loading progress
            self.progress_widget.setVisible(True)
            self.create_button.setEnabled(False)
            self.progress_label.setText("Creating database...")
            self.progress_bar.setValue(10)
            
            # Process events to update UI
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Import database initializer
            from ...database.initializer import DatabaseInitializer
            
            # Create and initialize database
            self.progress_label.setText("Initializing database structure...")
            self.progress_bar.setValue(30)
            QApplication.processEvents()
            
            db_path = Path(file_path)
            initializer = DatabaseInitializer(db_path)
            
            self.progress_label.setText("Creating database tables...")
            self.progress_bar.setValue(70)
            QApplication.processEvents()
            
            initializer.initialize_database()
            
            self.progress_label.setText("Database creation completed!")
            self.progress_bar.setValue(100)
            QApplication.processEvents()
            
            # Store the created database path
            self._created_db_path = str(db_path)
            
            # If CSV import is enabled, import the files
            if self.enable_csv_checkbox.isChecked() and self.csv_files:
                self._import_csv_files(str(db_path))
            else:
                # Hide progress and show success
                self.progress_widget.setVisible(False)
                self.create_button.setEnabled(True)
                QMessageBox.information(self, "Success", "Database created successfully!")
                self.accept()
                
        except Exception as e:
            # Reset UI state on error
            self.progress_widget.setVisible(False)
            self.create_button.setEnabled(True)
            logger.error(f"Database creation failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")
    
    def _import_csv_files(self, db_path: str):
        """Import CSV files using worker thread"""
        self.progress_widget.setVisible(True)
        self.create_button.setEnabled(False)
        
        # Start CSV import worker
        self.csv_worker = CSVImportWorker(db_path, self.csv_files)
        self.csv_worker.progress_updated.connect(self._update_progress)
        self.csv_worker.import_completed.connect(self._import_finished)
        self.csv_worker.start()
    
    def _update_progress(self, value: int, message: str):
        """Update progress display"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        self.progress_log.append(message)
    
    def _import_finished(self, success: bool, message: str):
        """Handle import completion"""
        self.progress_log.append(f"\n{'✅ Success!' if success else '❌ Error!'} {message}")
        
        if success:
            QMessageBox.information(self, "Success", "Database created and CSV data imported successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Import Warning", f"Database created but CSV import failed:\n{message}")
            # Still accept the dialog since database was created
            self.accept()
    
    def get_database_path(self) -> Optional[str]:
        """Get the created database path (if any)"""
        # This would be set during the creation process
        return getattr(self, '_created_db_path', None)