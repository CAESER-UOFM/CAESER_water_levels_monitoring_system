"""
Folder Scanner Dialog

Dialog for scanning folders for new XLE files and integrating them
into the organized collection. Designed to work with SMOO cloud storage.
"""

import sys
import os
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QTextEdit, QProgressBar,
                           QGroupBox, QListWidget, QCheckBox, QComboBox,
                           QFileDialog, QMessageBox, QTabWidget, QWidget,
                           QTableWidget, QTableWidgetItem, QSplitter,
                           QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSortFilterProxyModel
from PyQt5.QtGui import QFont, QIcon, QStandardItemModel, QStandardItem

# Import SMOO path management
from ...config.smoo_paths import get_smoo_path, is_smoo_available

# Import universal scanner using direct file import to avoid package conflicts
try:
    # Direct import that works reliably
    import importlib.util
    scanner_path = Path(__file__).parent.parent / "handlers" / "universal_folder_scanner.py"
    spec = importlib.util.spec_from_file_location("universal_folder_scanner", scanner_path)
    scanner_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner_module)
    UniversalXLEScanner = scanner_module.UniversalXLEScanner
    print("✅ Successfully imported UniversalXLEScanner in dialog")
except ImportError as e:
    # Fallback for when the scanner isn't available
    print(f"❌ Failed to import UniversalXLEScanner: {e}")
    print(f"❌ Current working directory: {os.getcwd()}")
    print(f"❌ Scanner path: {Path(__file__).parent.parent / 'handlers' / 'universal_folder_scanner.py'}")
    import traceback
    traceback.print_exc()
    UniversalXLEScanner = None
except Exception as e:
    print(f"❌ Unexpected error importing UniversalXLEScanner: {e}")
    import traceback
    traceback.print_exc()
    UniversalXLEScanner = None


class FolderScanThread(QThread):
    """Background thread for folder scanning operations"""
    
    progress_updated = pyqtSignal(int, str)  # progress, message
    scan_completed = pyqtSignal(dict)  # results
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, scanner, folder_path, apply_changes=False):
        super().__init__()
        self.scanner = scanner
        self.folder_path = folder_path
        self.apply_changes = apply_changes
    
    def run(self):
        try:
            # Phase 1: Scan folder
            self.progress_updated.emit(20, "Scanning folder for XLE files...")
            scan_results = self.scanner.scan_folder(self.folder_path)
            
            # Phase 2: Process unique files if any found
            if scan_results['unique_files'] > 0:
                self.progress_updated.emit(60, f"Processing {scan_results['unique_files']} unique files...")
                process_results = self.scanner.process_unique_files(scan_results, self.apply_changes)
                
                # Combine results
                final_results = {**scan_results, **process_results}
            else:
                final_results = scan_results
                final_results.update({'processed': 0, 'corrected': 0, 'unmatched': 0})
            
            self.progress_updated.emit(100, "Scan completed successfully!")
            self.scan_completed.emit(final_results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class FolderScannerDialog(QDialog):
    """Main dialog for the folder scanning system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = None
        self.scan_thread = None
        self.last_scan_results = None
        
        self.setWindowTitle("XLE Folder Scanner & Integrator")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        self.init_ui()
        self.init_scanner()
        
        # Load database records and scan history after initialization
        QTimer.singleShot(100, self.load_database_records)
        QTimer.singleShot(200, self.load_scan_history)
        QTimer.singleShot(300, self.update_collection_summary)
    
    def init_scanner(self):
        """Initialize the universal scanner"""
        if UniversalXLEScanner is None:
            error_msg = ("Universal scanner not available.\n\n"
                        "This could be due to:\n"
                        "• Missing dependencies in the universal_folder_scanner module\n"
                        "• Import path issues\n"
                        "• Missing universal_folder_scanner.py file\n\n"
                        "Check the console output for detailed error information.")
            self.show_error(error_msg)
            return
        
        try:
            # Set up paths using SMOO integration with local fallbacks
            if is_smoo_available():
                # Use SMOO paths for organized collection
                smoo_base = get_smoo_path("base")
                corrected_dir = Path(smoo_base) / "universal_xle_files" / "corrected"
                unmatched_dir = Path(smoo_base) / "universal_xle_files" / "unmatched"
                databases_dir = Path(smoo_base) / "universal_xle_files"  # DB in universal folder
            else:
                # Fallback to local test_scripts paths for development
                current_dir = Path(__file__).parent.parent.parent.parent
                corrected_dir = current_dir / "test_scripts" / "corrected_xle_files" / "corrected"
                unmatched_dir = current_dir / "test_scripts" / "corrected_xle_files" / "unmatched"
                databases_dir = current_dir / "test_scripts" / "corrected_xle_files"  # DB in same folder
            
            self.scanner = UniversalXLEScanner(corrected_dir, unmatched_dir, databases_dir)
            self.update_collection_summary()
            
        except Exception as e:
            self.show_error(f"Failed to initialize scanner: {e}")
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Tab 1: Folder Scanner
        self.init_scanner_tab()
        
        # Tab 2: Scan History
        self.init_history_tab()
        
        # Tab 3: Collection Overview
        self.init_overview_tab()
        
        # Tab 4: Database Browser
        self.init_database_browser_tab()
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def init_scanner_tab(self):
        """Initialize the main scanner tab"""
        scanner_widget = QWidget()
        layout = QVBoxLayout(scanner_widget)
        
        # Folder selection section
        folder_group = QGroupBox("Select Folder to Scan")
        folder_layout = QVBoxLayout(folder_group)
        
        # Folder path input
        path_layout = QHBoxLayout()
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Select folder containing XLE files...")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(QLabel("Folder Path:"))
        path_layout.addWidget(self.folder_path_edit)
        path_layout.addWidget(self.browse_button)
        folder_layout.addLayout(path_layout)
        
        # Note: Scanning always does preview first - no confusing dry run checkbox needed
        
        layout.addWidget(folder_group)
        
        # Scan controls
        controls_layout = QHBoxLayout()
        self.scan_button = QPushButton("🔍 Preview")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setMinimumHeight(35)
        self.scan_button.setMaximumWidth(120)  # Make button more compact
        self.scan_button.setToolTip("Preview XLE files in folder - no files will be moved")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.progress_bar)
        
        layout.addLayout(controls_layout)
        
        # Summary section (compact header-style)
        summary_layout = QHBoxLayout()
        
        # Scan results info (left side)
        self.summary_label = QLabel("No scan performed yet")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("QLabel { font-size: 11px; background-color: #f5f5f5; padding: 8px; border-radius: 4px; }")
        summary_layout.addWidget(self.summary_label)
        
        # Add stretch to push button to right
        summary_layout.addStretch()
        
        # Add files button (compact, right side)
        self.apply_button = QPushButton("📥 Add Files")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setVisible(False)
        self.apply_button.setMinimumHeight(30)
        self.apply_button.setMaximumHeight(35)
        self.apply_button.setMaximumWidth(120)  # Keep button compact
        self.apply_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; font-size: 11px; }")
        self.apply_button.setToolTip("Import the unique files found during scan into your collection")
        summary_layout.addWidget(self.apply_button)
        
        layout.addLayout(summary_layout)
        
        # File Details Table (takes up main space)
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["File", "Status", "Serial", "Location", "Project", "Well (CAE)"])
        
        # Enable smooth column resizing
        header = self.results_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # File column
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Status column
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Serial column
        header.setSectionResizeMode(3, QHeaderView.Interactive)  # Location column
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Project column
        header.setSectionResizeMode(5, QHeaderView.Interactive)  # Well column
        
        # Set minimum column widths for better usability
        header.setMinimumSectionSize(80)
        self.results_tree.setColumnWidth(0, 200)  # File column wider by default
        
        # Style the table like the Database Browser
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setSortingEnabled(True)
        
        layout.addWidget(self.results_tree)
        
        self.tab_widget.addTab(scanner_widget, "📁 Folder Scanner")
    
    def init_history_tab(self):
        """Initialize the scan history tab"""
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Scan Date", "Folder Path", "Files Found", "Unique Added", "Status"
        ])
        
        layout.addWidget(QLabel("Scan History:"))
        layout.addWidget(self.history_table)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_button = QPushButton("🔄 Refresh History")
        refresh_button.clicked.connect(self.load_scan_history)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        
        layout.addLayout(refresh_layout)
        
        self.tab_widget.addTab(history_widget, "📊 Scan History")
    
    def init_overview_tab(self):
        """Initialize the collection overview tab"""
        overview_widget = QWidget()
        layout = QVBoxLayout(overview_widget)
        
        # Collection stats
        stats_group = QGroupBox("Current Collection Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.collection_stats_label = QLabel("Loading collection statistics...")
        stats_layout.addWidget(self.collection_stats_label)
        
        layout.addWidget(stats_group)
        
        # Recent activity
        activity_group = QGroupBox("Recent Scanning Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_list = QListWidget()
        activity_layout.addWidget(self.activity_list)
        
        layout.addWidget(activity_group)
        
        self.tab_widget.addTab(overview_widget, "📈 Overview")
    
    def init_database_browser_tab(self):
        """Initialize the database browser tab"""
        browser_widget = QWidget()
        layout = QVBoxLayout(browser_widget)
        
        # Filter controls section
        filter_group = QGroupBox("Database Filters & Search")
        filter_layout = QVBoxLayout(filter_group)
        
        # Row 1: Search and Refresh
        row1_layout = QHBoxLayout()
        
        # Search box (still useful for free-text search)
        row1_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search filename, serial number, or location...")
        self.search_input.textChanged.connect(self.filter_database_records)
        row1_layout.addWidget(self.search_input)
        
        # Refresh button
        self.refresh_db_button = QPushButton("🔄 Refresh")
        self.refresh_db_button.clicked.connect(self.load_database_records)
        row1_layout.addWidget(self.refresh_db_button)
        
        filter_layout.addLayout(row1_layout)
        
        # Row 2: Cascading filter dropdowns
        row2_layout = QHBoxLayout()
        
        # Project filter (primary filter)
        row2_layout.addWidget(QLabel("Project:"))
        self.project_filter = QComboBox()
        self.project_filter.currentTextChanged.connect(self.on_project_filter_changed)
        row2_layout.addWidget(self.project_filter)
        
        # CAE number filter (updates based on project)
        row2_layout.addWidget(QLabel("CAE #:"))
        self.cae_filter = QComboBox()
        self.cae_filter.setMinimumWidth(120)
        self.cae_filter.currentTextChanged.connect(self.on_cae_filter_changed)
        row2_layout.addWidget(self.cae_filter)
        
        # Clear filters button
        self.clear_filters_button = QPushButton("🗑️ Clear Filters")
        self.clear_filters_button.clicked.connect(self.clear_database_filters)
        row2_layout.addWidget(self.clear_filters_button)
        
        filter_layout.addLayout(row2_layout)
        
        # Row 3: Secondary cascading filters
        row3_layout = QHBoxLayout()
        
        # Serial number filter (updates based on previous filters)
        row3_layout.addWidget(QLabel("Serial #:"))
        self.serial_filter = QComboBox()
        self.serial_filter.setMinimumWidth(100)
        self.serial_filter.currentTextChanged.connect(self.on_serial_filter_changed)
        row3_layout.addWidget(self.serial_filter)
        
        # Device type filter (updates based on previous filters)
        row3_layout.addWidget(QLabel("Device:"))
        self.device_filter = QComboBox()
        self.device_filter.currentTextChanged.connect(self.on_device_filter_changed)
        row3_layout.addWidget(self.device_filter)
        
        # Status filter (moved here for better layout)
        row3_layout.addWidget(QLabel("Status:"))
        self.status_secondary = QComboBox()
        self.status_secondary.currentTextChanged.connect(self.filter_database_records)
        row3_layout.addWidget(self.status_secondary)
        
        filter_layout.addLayout(row2_layout)
        filter_layout.addLayout(row3_layout)
        layout.addWidget(filter_group)
        
        # Statistics row
        stats_layout = QHBoxLayout()
        self.db_stats_label = QLabel("Loading database records...")
        stats_layout.addWidget(self.db_stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Database records table
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(11)
        self.db_table.setHorizontalHeaderLabels([
            "Filename", "CAE #", "Project", "Serial #", "Device Type", 
            "Status", "Size (KB)", "Processing Date", "Location", "Signature", "Path"
        ])
        
        # Configure table
        header = self.db_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Filename
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # CAE #
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Project
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Serial #
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Device Type
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status  
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Size
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # Location
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Signature
        header.setSectionResizeMode(10, QHeaderView.Stretch)  # Path
        
        self.db_table.setAlternatingRowColors(True)
        self.db_table.setSortingEnabled(True)
        self.db_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.db_table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.export_results_button = QPushButton("📊 Export Results")
        self.export_results_button.clicked.connect(self.export_database_results)
        action_layout.addWidget(self.export_results_button)
        
        self.show_file_info_button = QPushButton("🔍 Show File Info")
        self.show_file_info_button.clicked.connect(self.show_selected_file_info)
        action_layout.addWidget(self.show_file_info_button)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.tab_widget.addTab(browser_widget, "🗄️ Database Browser")
    
    def get_database_path(self) -> Path:
        """Get the path to the database file - must match scanner's path"""
        if self.scanner and hasattr(self.scanner, 'db') and self.scanner.db:
            # Use the exact same path the scanner is using
            return Path(self.scanner.db.db_path)
        else:
            # Fallback - try to match scanner's default path
            if is_smoo_available():
                smoo_base = get_smoo_path("base")
                return Path(smoo_base) / "universal_xle_files" / "folder_scan_tracking.db"
            else:
                # Use current working directory like the scanner does
                return Path.cwd() / "folder_scan_tracking.db"
    
    def load_database_records(self):
        """Load all records from the database"""
        db_path = self.get_database_path()
        
        if not db_path.exists():
            self.db_stats_label.setText("❌ Database not found")
            self.db_table.setRowCount(0)
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all records with enhanced metadata
            cursor.execute("""
                SELECT 
                    filename, cae_number, project_name, serial_number, instrument_type,
                    status, file_size, processing_date, original_path, file_signature
                FROM processed_files 
                ORDER BY processing_date DESC
            """)
            
            records = cursor.fetchall()
            conn.close()
            
            # Store original records for filtering
            self.all_db_records = records
            
            # Populate filter dropdowns with available data
            self.populate_filter_dropdowns()
            
            # Display records
            self.display_database_records(records)
            
            # Update statistics
            total_records = len(records)
            corrected_count = len([r for r in records if r[5] == 'corrected'])  # status is at index 5
            unmatched_count = len([r for r in records if r[5] == 'unmatched'])
            
            self.db_stats_label.setText(
                f"📊 Total: {total_records:,} files | "
                f"✅ Corrected: {corrected_count:,} | "
                f"⚠️ Unmatched: {unmatched_count:,}"
            )
            
        except Exception as e:
            self.db_stats_label.setText(f"❌ Error loading database: {e}")
            self.db_table.setRowCount(0)
    
    def display_database_records(self, records):
        """Display database records in the table"""
        self.db_table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            filename, cae_number, project_name, serial_number, instrument_type, status, file_size, processing_date, original_path, file_signature = record
            
            # Extract location from filename or path (fallback)
            location = self.extract_location_from_filename(filename)
            
            # Format file size
            size_kb = f"{file_size / 1024:.1f}" if file_size else "N/A"
            
            # Format processing date
            try:
                from datetime import datetime
                if processing_date:
                    date_obj = datetime.fromisoformat(processing_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                else:
                    formatted_date = "N/A"
            except:
                formatted_date = processing_date or "N/A"
            
            # Set table items with enhanced metadata and fallbacks for legacy records  
            display_cae = cae_number or self.extract_cae_from_filename(filename) or ""
            display_project = project_name or ("Legacy Corrected" if status == 'corrected' else "Legacy Unmatched" if status == 'unmatched' else "")
            display_device = instrument_type or ("L5_LT" if filename and 'L5' in filename.upper() else "Levellogger" if filename and 'LEVEL' in filename.upper() else "")
            
            # Don't duplicate location - Location column should show file path location, not CAE
            display_location = location if location != display_cae else ""
            
            self.db_table.setItem(row, 0, QTableWidgetItem(filename or ""))
            self.db_table.setItem(row, 1, QTableWidgetItem(display_cae))  # CAE #
            self.db_table.setItem(row, 2, QTableWidgetItem(display_project))  # Project
            self.db_table.setItem(row, 3, QTableWidgetItem(serial_number or ""))  # Serial #
            self.db_table.setItem(row, 4, QTableWidgetItem(display_device))  # Device Type
            self.db_table.setItem(row, 5, QTableWidgetItem(status or ""))  # Status
            self.db_table.setItem(row, 6, QTableWidgetItem(size_kb))  # Size
            self.db_table.setItem(row, 7, QTableWidgetItem(formatted_date))  # Date
            self.db_table.setItem(row, 8, QTableWidgetItem(display_location))  # Location (avoid duplication with CAE)
            self.db_table.setItem(row, 9, QTableWidgetItem(file_signature[:16] + "..." if len(file_signature) > 16 else file_signature))  # Signature
            self.db_table.setItem(row, 10, QTableWidgetItem(str(original_path) if original_path else ""))  # Path
    
    def extract_location_from_filename(self, filename):
        """Extract location/project identifier from filename"""
        if not filename:
            return ""
        
        try:
            # Try to extract CAE number or location from filename
            # Common patterns: HAA001, P226, SC-MW1, etc.
            patterns = [
                r'^([A-Z]{2,3}-?\w+)',  # HAA001, SC-MW1, P226
                r'^(\d+_[A-Z]\w+)',     # 1034480_1T4
                r'^([A-Z]+\d+)',        # HAA001, CVL2
            ]
            
            for pattern in patterns:
                match = re.match(pattern, filename)
                if match:
                    return match.group(1)
            
            # Fallback: first part before underscore
            return filename.split('_')[0]
            
        except:
            return ""
    
    def extract_cae_from_filename(self, filename):
        """Extract CAE number from filename for legacy records"""
        if not filename:
            return None
        
        # Reuse the same logic as extract_location_from_filename
        location = self.extract_location_from_filename(filename)
        return location if location else None
    
    def filter_database_records(self):
        """Filter database records based on current filter values"""
        if not hasattr(self, 'all_db_records'):
            return
        
        # Get filter values from dropdowns and search
        search_text = self.search_input.text().lower()
        project_filter = self.project_filter.currentText()
        cae_filter = self.cae_filter.currentText() 
        serial_filter = self.serial_filter.currentText()
        device_filter = self.device_filter.currentText()
        status_filter = self.status_secondary.currentText().lower()
        
        # Filter records
        filtered_records = []
        for record in self.all_db_records:
            filename, cae_number, project_name, serial_number, instrument_type, status, file_size, processing_date, original_path, file_signature = record
            
            # Apply project filter
            if project_filter != "All Projects" and project_name != project_filter:
                continue
            
            # Apply CAE number filter
            if cae_filter != "All CAE Numbers" and cae_number != cae_filter:
                continue
            
            # Apply serial number filter
            if serial_filter != "All Serial Numbers" and serial_number != serial_filter:
                continue
            
            # Apply device type filter
            if device_filter != "All Devices" and instrument_type != device_filter:
                continue
            
            # Apply status filter
            if status_filter != "all" and status.lower() != status_filter:
                continue
            
            # Apply general search filter (still useful for free-text search)
            if search_text:
                searchable_text = f"{filename} {cae_number} {project_name} {serial_number} {instrument_type} {original_path}".lower()
                if search_text not in searchable_text:
                    continue
            
            filtered_records.append(record)
        
        # Display filtered results
        self.display_database_records(filtered_records)
        
        # Update statistics
        total_filtered = len(filtered_records)
        corrected_filtered = len([r for r in filtered_records if r[5] == 'corrected'])  # status is at index 5
        unmatched_filtered = len([r for r in filtered_records if r[5] == 'unmatched'])
        total_all = len(self.all_db_records)
        
        self.db_stats_label.setText(
            f"📊 Showing: {total_filtered:,} of {total_all:,} files | "
            f"✅ Corrected: {corrected_filtered:,} | "
            f"⚠️ Unmatched: {unmatched_filtered:,}"
        )
    
    def clear_database_filters(self):
        """Clear all database filters"""
        self.search_input.clear()
        self.project_filter.setCurrentText("All Projects")
        self.cae_filter.setCurrentText("All CAE Numbers")
        self.serial_filter.setCurrentText("All Serial Numbers")
        self.device_filter.setCurrentText("All Devices") 
        self.status_secondary.setCurrentText("All")
        self.populate_filter_dropdowns()  # Repopulate with all data
        self.filter_database_records()  # Apply cleared filters
    
    def populate_filter_dropdowns(self, filtered_data=None):
        """Populate filter dropdowns based on available data"""
        if not hasattr(self, 'all_db_records'):
            return
        
        # Use filtered data if provided, otherwise use all data
        data_to_use = filtered_data if filtered_data is not None else self.all_db_records
        
        # Block signals to prevent recursive filtering
        self.project_filter.blockSignals(True)
        self.cae_filter.blockSignals(True) 
        self.serial_filter.blockSignals(True)
        self.device_filter.blockSignals(True)
        self.status_secondary.blockSignals(True)
        
        # Extract unique values from data (format: filename, cae_number, project_name, serial_number, instrument_type, status, ...)
        projects = set()
        cae_numbers = set()
        serial_numbers = set()
        devices = set()
        statuses = set()
        
        for record in data_to_use:
            filename, cae_number, project_name, serial_number, instrument_type, status = record[:6]
            
            # Handle legacy records - add meaningful fallbacks
            if project_name: 
                projects.add(project_name)
            elif status == 'corrected':
                projects.add("Legacy Corrected")
            elif status == 'unmatched':
                projects.add("Legacy Unmatched")
                
            if cae_number: 
                cae_numbers.add(cae_number)
            elif serial_number and status == 'corrected':
                # Try to extract CAE from filename for legacy records
                cae_from_filename = self.extract_cae_from_filename(filename)
                if cae_from_filename:
                    cae_numbers.add(cae_from_filename)
                    
            if serial_number: serial_numbers.add(serial_number)
            
            if instrument_type: 
                devices.add(instrument_type)
            elif filename:  # Try to infer from filename for legacy records
                if 'L5' in filename.upper():
                    devices.add("L5_LT")
                elif 'LEVEL' in filename.upper():
                    devices.add("Levelogger")
                    
            if status: statuses.add(status)
        
        # Update dropdowns while preserving current selection if valid
        current_project = self.project_filter.currentText()
        current_cae = self.cae_filter.currentText()
        current_serial = self.serial_filter.currentText()
        current_device = self.device_filter.currentText()
        current_status = self.status_secondary.currentText()
        
        # Populate project dropdown
        self.project_filter.clear()
        self.project_filter.addItem("All Projects")
        for project in sorted(projects):
            if project:
                self.project_filter.addItem(project)
        
        # Populate CAE dropdown  
        self.cae_filter.clear()
        self.cae_filter.addItem("All CAE Numbers")
        for cae in sorted(cae_numbers):
            if cae:
                self.cae_filter.addItem(cae)
        
        # Populate serial number dropdown
        self.serial_filter.clear()
        self.serial_filter.addItem("All Serial Numbers")
        for serial in sorted(serial_numbers):
            if serial:
                self.serial_filter.addItem(serial)
        
        # Populate device type dropdown
        self.device_filter.clear()
        self.device_filter.addItem("All Devices")
        for device in sorted(devices):
            if device:
                self.device_filter.addItem(device)
        
        # Populate status dropdown
        self.status_secondary.clear()
        self.status_secondary.addItem("All")
        for status in sorted(statuses):
            if status:
                self.status_secondary.addItem(status.title())
        
        # Restore selections if still valid
        if current_project in [self.project_filter.itemText(i) for i in range(self.project_filter.count())]:
            self.project_filter.setCurrentText(current_project)
        if current_cae in [self.cae_filter.itemText(i) for i in range(self.cae_filter.count())]:
            self.cae_filter.setCurrentText(current_cae)
        if current_serial in [self.serial_filter.itemText(i) for i in range(self.serial_filter.count())]:
            self.serial_filter.setCurrentText(current_serial)
        if current_device in [self.device_filter.itemText(i) for i in range(self.device_filter.count())]:
            self.device_filter.setCurrentText(current_device)
        if current_status in [self.status_secondary.itemText(i) for i in range(self.status_secondary.count())]:
            self.status_secondary.setCurrentText(current_status)
        
        # Re-enable signals
        self.project_filter.blockSignals(False)
        self.cae_filter.blockSignals(False)
        self.serial_filter.blockSignals(False)
        self.device_filter.blockSignals(False)
        self.status_secondary.blockSignals(False)
    
    def on_project_filter_changed(self):
        """Handle project filter change - updates other dropdowns based on selected project"""
        if not hasattr(self, 'all_db_records'):
            return
        
        project_selection = self.project_filter.currentText()
        
        # Filter data based on project selection
        if project_selection == "All Projects":
            project_filtered_data = self.all_db_records
        else:
            project_filtered_data = [
                record for record in self.all_db_records 
                if record[2] == project_selection  # project_name is at index 2
            ]
        
        # Update other dropdowns based on filtered data
        self.populate_secondary_filters(project_filtered_data)
        
        # Apply the filter
        self.filter_database_records()
    
    def on_cae_filter_changed(self):
        """Handle CAE filter change - updates remaining dropdowns"""
        self.cascade_filter_update()
    
    def on_serial_filter_changed(self):
        """Handle serial filter change - updates remaining dropdowns"""
        self.cascade_filter_update()
    
    def on_device_filter_changed(self):
        """Handle device filter change - apply filtering"""
        self.filter_database_records()
    
    def populate_secondary_filters(self, filtered_data):
        """Update CAE, serial, device dropdowns based on project-filtered data"""
        # Block signals to prevent recursive updates
        self.cae_filter.blockSignals(True)
        self.serial_filter.blockSignals(True) 
        self.device_filter.blockSignals(True)
        self.status_secondary.blockSignals(True)
        
        # Extract unique values from filtered data
        cae_numbers = set()
        serial_numbers = set()
        devices = set()
        statuses = set()
        
        for record in filtered_data:
            filename, cae_number, project_name, serial_number, instrument_type, status = record[:6]
            
            if cae_number: cae_numbers.add(cae_number)
            if serial_number: serial_numbers.add(serial_number)
            if instrument_type: devices.add(instrument_type)
            if status: statuses.add(status)
        
        # Update CAE dropdown
        current_cae = self.cae_filter.currentText()
        self.cae_filter.clear()
        self.cae_filter.addItem("All CAE Numbers")
        for cae in sorted(cae_numbers):
            if cae:
                self.cae_filter.addItem(cae)
        
        # Update serial dropdown
        current_serial = self.serial_filter.currentText()
        self.serial_filter.clear()
        self.serial_filter.addItem("All Serial Numbers")
        for serial in sorted(serial_numbers):
            if serial:
                self.serial_filter.addItem(serial)
        
        # Update device dropdown
        current_device = self.device_filter.currentText()
        self.device_filter.clear()
        self.device_filter.addItem("All Devices")
        for device in sorted(devices):
            if device:
                self.device_filter.addItem(device)
        
        # Update status dropdown
        current_status = self.status_secondary.currentText()
        self.status_secondary.clear()
        self.status_secondary.addItem("All")
        for status in sorted(statuses):
            if status:
                self.status_secondary.addItem(status.title())
        
        # Re-enable signals
        self.cae_filter.blockSignals(False)
        self.serial_filter.blockSignals(False)
        self.device_filter.blockSignals(False)
        self.status_secondary.blockSignals(False)
    
    def cascade_filter_update(self):
        """Handle cascading filter updates when CAE or serial filter changes"""
        if not hasattr(self, 'all_db_records'):
            return
        
        # Get current filter selections
        project_selection = self.project_filter.currentText()
        cae_selection = self.cae_filter.currentText()
        serial_selection = self.serial_filter.currentText()
        
        # Apply cumulative filtering
        filtered_data = self.all_db_records
        
        # Filter by project
        if project_selection != "All Projects":
            filtered_data = [record for record in filtered_data if record[2] == project_selection]
        
        # Filter by CAE
        if cae_selection != "All CAE Numbers":
            filtered_data = [record for record in filtered_data if record[1] == cae_selection]
        
        # Filter by serial (if CAE hasn't been selected yet)
        if serial_selection != "All Serial Numbers":
            filtered_data = [record for record in filtered_data if record[3] == serial_selection]
        
        # Update remaining dropdowns based on this filtered data
        self.update_remaining_filters(filtered_data)
        
        # Apply the filter
        self.filter_database_records()
    
    def update_remaining_filters(self, filtered_data):
        """Update device and status dropdowns based on cumulative filtering"""
        self.device_filter.blockSignals(True)
        self.status_secondary.blockSignals(True)
        
        devices = set()
        statuses = set()
        
        for record in filtered_data:
            filename, cae_number, project_name, serial_number, instrument_type, status = record[:6]
            
            if instrument_type: devices.add(instrument_type)
            if status: statuses.add(status)
        
        # Update device dropdown
        current_device = self.device_filter.currentText()
        self.device_filter.clear()
        self.device_filter.addItem("All Devices")
        for device in sorted(devices):
            if device:
                self.device_filter.addItem(device)
        
        # Update status dropdown
        current_status = self.status_secondary.currentText()
        self.status_secondary.clear()
        self.status_secondary.addItem("All")
        for status in sorted(statuses):
            if status:
                self.status_secondary.addItem(status.title())
        
        self.device_filter.blockSignals(False)
        self.status_secondary.blockSignals(False)
    
    def export_database_results(self):
        """Export current filtered results to CSV"""
        if self.db_table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No records to export")
            return
        
        from PyQt5.QtWidgets import QFileDialog
        import csv
        
        # Get export file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Database Results", 
            f"universal_xle_database_export.csv",
            "CSV files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers
                headers = [self.db_table.horizontalHeaderItem(i).text() 
                          for i in range(self.db_table.columnCount())]
                writer.writerow(headers)
                
                # Write data
                for row in range(self.db_table.rowCount()):
                    row_data = []
                    for col in range(self.db_table.columnCount()):
                        item = self.db_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(
                self, "Export Complete", 
                f"Exported {self.db_table.rowCount()} records to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{e}")
    
    def show_selected_file_info(self):
        """Show detailed information about selected file"""
        current_row = self.db_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "File Info", "Please select a file first")
            return
        
        # Get file information from table (enhanced columns)
        filename = self.db_table.item(current_row, 0).text()
        cae_number = self.db_table.item(current_row, 1).text()
        project = self.db_table.item(current_row, 2).text()
        serial = self.db_table.item(current_row, 3).text()
        device_type = self.db_table.item(current_row, 4).text()
        status = self.db_table.item(current_row, 5).text()
        size = self.db_table.item(current_row, 6).text()
        date = self.db_table.item(current_row, 7).text()
        location = self.db_table.item(current_row, 8).text()
        signature = self.db_table.item(current_row, 9).text()
        path = self.db_table.item(current_row, 10).text()
        
        # Create enhanced info dialog
        info_text = f"""
<b>📄 File Information:</b><br><br>
<b>Filename:</b> {filename}<br>
<b>🏷️ CAE Number:</b> {cae_number}<br>
<b>📁 Project:</b> {project}<br>
<b>🔢 Serial Number:</b> {serial}<br>
<b>🔧 Device Type:</b> {device_type}<br>
<b>✅ Status:</b> {status}<br>
<b>📊 File Size:</b> {size} KB<br>
<b>📅 Processing Date:</b> {date}<br>
<b>📍 Location:</b> {location}<br>
<b>🔐 File Signature:</b> {signature}<br>
<b>💾 Original Path:</b> {path}<br>
"""
        
        QMessageBox.information(self, f"File Info: {filename}", info_text)

    def browse_folder(self):
        """Open folder selection dialog"""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Folder to Scan for XLE Files",
            str(Path.home())
        )
        
        if folder_path:
            self.folder_path_edit.setText(folder_path)
    
    def start_scan(self):
        """Start the folder scanning process"""
        folder_path = self.folder_path_edit.text().strip()
        
        if not folder_path:
            self.show_error("Please select a folder to scan")
            return
        
        if not Path(folder_path).exists():
            self.show_error("Selected folder does not exist")
            return
        
        if not self.scanner:
            self.show_error("Scanner not initialized")
            return
        
        # Update UI for scanning
        self.scan_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.apply_button.setVisible(False)
        
        # Start background scan - ALWAYS in preview mode first
        apply_changes = False  # Never apply changes during initial scan
        self.scan_thread = FolderScanThread(self.scanner, folder_path, apply_changes)
        self.scan_thread.progress_updated.connect(self.update_progress)
        self.scan_thread.scan_completed.connect(self.handle_scan_completed)
        self.scan_thread.error_occurred.connect(self.handle_scan_error)
        self.scan_thread.start()
    
    def update_progress(self, value, message):
        """Update progress bar and status"""
        self.progress_bar.setValue(value)
        # You could add a status label here if needed
    
    def handle_scan_completed(self, results):
        """Handle completed scan results"""
        self.last_scan_results = results
        
        # Update UI
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Update summary
        self.update_scan_summary(results)
        
        # Update detailed results
        self.update_results_tree(results)
        
        # Show apply button if there are files to process (scanning is always preview)
        if results.get('unique_files', 0) > 0:
            self.apply_button.setVisible(True)
        
        # Refresh other tabs
        self.load_scan_history()
        self.update_collection_summary()
        
        # Show completion message
        total_unique = results.get('unique_files', 0)
        if total_unique > 0:
            QMessageBox.information(
                self,
                "Preview Complete",
                f"Preview completed successfully!\\n\\n"
                f"📁 Folder: {results['folder_path']}\\n"
                f"📊 Total files found: {results['total_files']}\\n"
                f"🆕 Unique files: {total_unique}\\n"
                f"🔄 Duplicates: {results['duplicates']}\\n"
                f"❌ Errors: {results['errors']}\\n\\n"
                f"Click 'Add Files' button to import the {total_unique} unique files."
            )
        else:
            QMessageBox.information(
                self,
                "Scan Complete", 
                f"Scan completed - no new unique files found.\\n\\n"
                f"📁 Folder: {results['folder_path']}\\n"
                f"📊 Total files: {results['total_files']}\\n"
                f"🔄 Duplicates: {results['duplicates']}"
            )
    
    def handle_scan_error(self, error_message):
        """Handle scan errors"""
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.show_error(f"Scan failed: {error_message}")
    
    def apply_changes(self):
        """Apply changes from the last dry run"""
        if not self.last_scan_results:
            return
        
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Apply Changes",
            f"This will process {self.last_scan_results.get('unique_files', 0)} unique files\\n"
            f"and integrate them into your collection.\\n\\n"
            f"Are you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Re-run scan with apply_changes=True
            folder_path = self.folder_path_edit.text().strip()
            
            self.apply_button.setVisible(False)
            self.scan_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            self.scan_thread = FolderScanThread(self.scanner, folder_path, apply_changes=True)
            self.scan_thread.progress_updated.connect(self.update_progress)
            self.scan_thread.scan_completed.connect(self.handle_scan_completed)
            self.scan_thread.error_occurred.connect(self.handle_scan_error)
            self.scan_thread.start()
    
    def update_scan_summary(self, results):
        """Update the scan results summary"""
        summary_text = f"""
<b>Scan Results:</b><br>
📁 Folder: {results['folder_path']}<br>
📊 Total XLE files found: {results['total_files']}<br>
🆕 New unique files: {results['unique_files']}<br>
🔄 Duplicates (already processed): {results['duplicates']}<br>
❌ Files with errors: {results['errors']}<br>
<br>
"""
        
        if results.get('processed', 0) > 0:
            action = "Would be" if results.get('dry_run', False) else "Were"
            summary_text += f"""
<b>Processing Results:</b><br>
📋 Files processed: {results['processed']}<br>
✅ Added to corrected collection: {results.get('corrected', 0)}<br>
⚠️ Added to unmatched collection: {results.get('unmatched', 0)}<br>
"""
        
        self.summary_label.setText(summary_text)
    
    def update_results_tree(self, results):
        """Update the detailed results tree"""
        self.results_tree.clear()
        
        if results.get('unique_files_list'):
            unique_root = QTreeWidgetItem(self.results_tree, ["New Unique Files", "", "", "", "", ""])
            unique_root.setExpanded(True)
            
            for file_info in results['unique_files_list']:
                file_path = Path(file_info['file_path'])
                metadata = file_info['metadata']
                
                # Get matching information if available
                match_info = file_info.get('match_info', {})
                project_name = match_info.get('project', 'Unmatched')
                well_cae = match_info.get('cae_number', 'N/A')
                status = "Matched" if project_name != 'Unmatched' else "Unmatched"
                
                item = QTreeWidgetItem(unique_root, [
                    file_path.name,
                    status,
                    metadata.get('serial_number', 'N/A'),
                    metadata.get('location', 'N/A'),
                    project_name,
                    well_cae
                ])
        
        if results.get('duplicates_list'):
            dup_root = QTreeWidgetItem(self.results_tree, ["Duplicate Files", "", "", "", "", ""])
            dup_root.setExpanded(False)
            
            for dup_info in results['duplicates_list'][:20]:  # Limit display
                file_path = Path(dup_info['file_path'])
                item = QTreeWidgetItem(dup_root, [
                    file_path.name,
                    f"Duplicate ({dup_info['reason']})",
                    "",
                    "",
                    "",
                    ""
                ])
        
        if results.get('errors_list'):
            error_root = QTreeWidgetItem(self.results_tree, ["Files with Errors", "", "", "", "", ""])
            error_root.setExpanded(False)
            
            for error_info in results['errors_list']:
                file_path = Path(error_info['file_path'])
                item = QTreeWidgetItem(error_root, [
                    file_path.name,
                    f"Error ({error_info['reason']})",
                    "",
                    "",
                    "",
                    ""
                ])
    
    def load_scan_history(self):
        """Load and display scan history directly from database"""
        try:
            db_path = self.get_database_path()
            
            if not db_path.exists():
                self.history_table.setRowCount(0)
                return
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Load scan history directly from database
            cursor.execute("""
                SELECT folder_path, last_scan_date, files_found, unique_files_added, scan_metadata
                FROM scanned_folders 
                ORDER BY last_scan_date DESC 
                LIMIT 50
            """)
            
            history_rows = cursor.fetchall()
            conn.close()
            
            self.history_table.setRowCount(len(history_rows))
            
            for row, (folder_path, scan_date, files_found, unique_added, metadata) in enumerate(history_rows):
                # Format date nicely
                try:
                    date_obj = datetime.fromisoformat(scan_date)
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    formatted_date = scan_date or "N/A"
                
                self.history_table.setItem(row, 0, QTableWidgetItem(formatted_date))
                self.history_table.setItem(row, 1, QTableWidgetItem(folder_path or "N/A"))
                self.history_table.setItem(row, 2, QTableWidgetItem(str(files_found or 0)))
                self.history_table.setItem(row, 3, QTableWidgetItem(str(unique_added or 0)))
                self.history_table.setItem(row, 4, QTableWidgetItem("Completed"))
            
            self.history_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error loading scan history: {e}")
            self.history_table.setRowCount(0)
    
    def update_collection_summary(self):
        """Update the collection overview"""
        if not self.scanner:
            return
        
        try:
            summary = self.scanner.get_scan_summary()
            
            stats_text = f"""
<b>Current Collection Size:</b><br>
✅ Corrected files: {summary['current_collection_size']['corrected']:,}<br>
⚠️ Unmatched files: {summary['current_collection_size']['unmatched']:,}<br>
📊 Total files: {summary['current_collection_size']['corrected'] + summary['current_collection_size']['unmatched']:,}<br>
<br>
<b>Scanning Activity:</b><br>
🔍 Total scans performed: {summary['total_scans']}<br>
📁 Total files examined: {summary['total_files_found']:,}<br>
🆕 Unique files added: {summary['total_unique_added']:,}<br>
"""
            
            self.collection_stats_label.setText(stats_text)
            
            # Update activity list
            self.activity_list.clear()
            for scan in summary.get('recent_scans', [])[:10]:
                activity_text = f"{scan['last_scan_date']}: {scan['unique_files_added']} files from {Path(scan['folder_path']).name}"
                self.activity_list.addItem(activity_text)
                
        except Exception as e:
            print(f"Error updating collection summary: {e}")
    
    def show_error(self, message):
        """Show error message to user"""
        QMessageBox.critical(self, "Error", message)
    
    def closeEvent(self, event):
        """Handle dialog closing"""
        # Stop any running scan thread
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.terminate()
            self.scan_thread.wait()
        
        event.accept()


def main():
    """Test the dialog standalone"""
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = FolderScannerDialog()
    dialog.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()