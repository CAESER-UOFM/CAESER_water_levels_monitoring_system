"""
Recharge Estimates Tab for the Water Level Visualizer.
This tab provides tools for estimating aquifer recharge using various methods.
"""

import logging
import numpy as np
import pandas as pd
import re
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QMessageBox,
    QSplitter, QHBoxLayout, QGroupBox, QPushButton, QDialog,
    QProgressDialog, QApplication, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal

# Import the individual recharge method tabs
from .rise_tab import RiseTab
from .mrc_tab import MrcTab
from .emr_tab import EmrTab
# Import unified settings
from .unified_settings import UnifiedRechargeSettings
# Import Phase 5 components
from .settings_persistence import SettingsPersistence
from .user_preferences import UserPreferencesDialog
# from .help_system import RechargeHelpSystem  # Now handled by main app help

logger = logging.getLogger(__name__)

class RechargeTab(QWidget):
    """
    Tab for recharge estimation using water table fluctuation methods.
    Contains sub-tabs for different methods: RISE, MRC, and EMR.
    """
    
    def __init__(self, db_manager, parent=None):
        """
        Initialize the recharge tab.
        
        Args:
            db_manager: Database manager providing access to well data
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_wells = []
        
        # Initialize unified settings
        self.unified_settings = UnifiedRechargeSettings()
        self.settings = self.unified_settings.get_default_settings()
        
        # Initialize Phase 5 components
        self.settings_persistence = SettingsPersistence()
        self.user_preferences = {}
        
        # Initialize centralized data storage
        self.current_well_id = None
        self.raw_data = None
        self.processed_data = None
        self.preprocessing_timestamp = None
        
        
        # Load saved settings and preferences
        self._load_saved_settings()
        
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI for the recharge tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with info and settings button
        header_layout = QHBoxLayout()
        
        # Info label at the top
        info_label = QLabel(
            "Select a well below to analyze for recharge estimation. "
            "Unconfined aquifer wells are recommended for water table fluctuation methods."
        )
        info_label.setWordWrap(True)
        header_layout.addWidget(info_label)
        
        # Settings button
        self.settings_btn = QPushButton("Global Settings")
        self.settings_btn.setMaximumWidth(120)
        self.settings_btn.setToolTip("Configure shared parameters for all recharge methods")
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        header_layout.addWidget(self.settings_btn)
        
        
        # Preferences button removed - using global settings instead
        # Help button removed - now handled by main application help system
        
        layout.addLayout(header_layout)
        
        # Add well selection controls
        well_selection = self.create_well_selection()
        layout.addWidget(well_selection)
        
        # Create recharge methods tabs
        recharge_methods = self.create_recharge_methods()
        layout.addWidget(recharge_methods)
    
    def create_well_selection(self):
        """Create well selection controls."""
        from PyQt5.QtWidgets import QComboBox, QHBoxLayout
        import sqlite3
        
        group_box = QGroupBox("Well Selection")
        layout = QVBoxLayout(group_box)
        
        # Create horizontal layout for dropdowns
        selection_layout = QHBoxLayout()
        
        # Aquifer filter dropdown
        aquifer_label = QLabel("Filter by Aquifer:")
        selection_layout.addWidget(aquifer_label)
        
        self.aquifer_combo = QComboBox()
        self.aquifer_combo.setMinimumWidth(150)
        self.aquifer_combo.currentTextChanged.connect(self.on_aquifer_filter_changed)
        selection_layout.addWidget(self.aquifer_combo)
        
        # Well selection dropdown
        well_label = QLabel("Select Well:")
        selection_layout.addWidget(well_label)
        
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        self.well_combo.currentTextChanged.connect(self.on_well_selected)
        selection_layout.addWidget(self.well_combo)
        
        # Add stretch to push everything to the left
        selection_layout.addStretch()
        
        layout.addLayout(selection_layout)
        
        # Load initial data
        self.load_aquifer_filters()
        self.load_wells()
        
        return group_box
    
    def load_aquifer_filters(self):
        """Load aquifer options for filtering."""
        if not self.db_manager or not self.db_manager.current_db:
            return
            
        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT aquifer FROM wells WHERE aquifer IS NOT NULL ORDER BY aquifer")
                aquifers = cursor.fetchall()
                
                self.aquifer_combo.clear()
                self.aquifer_combo.addItem("All Aquifers", None)
                
                for aquifer in aquifers:
                    self.aquifer_combo.addItem(aquifer[0], aquifer[0])
                    
        except Exception as e:
            logger.error(f"Error loading aquifer filters: {e}")
    
    def load_wells(self, aquifer_filter=None):
        """Load wells for selection, optionally filtered by aquifer."""
        if not self.db_manager or not self.db_manager.current_db:
            return
            
        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                
                if aquifer_filter:
                    cursor.execute("""
                        SELECT well_number, aquifer, latitude, longitude 
                        FROM wells 
                        WHERE aquifer = ? 
                        ORDER BY well_number
                    """, (aquifer_filter,))
                else:
                    cursor.execute("""
                        SELECT well_number, aquifer, latitude, longitude 
                        FROM wells 
                        ORDER BY well_number
                    """)
                    
                wells = cursor.fetchall()
                
                self.well_combo.clear()
                self.well_combo.addItem("-- Select Well --", None)
                
                for well in wells:
                    well_number, aquifer, lat, lng = well
                    display_text = f"{well_number}"
                    if aquifer:
                        display_text += f" ({aquifer})"
                    self.well_combo.addItem(display_text, well_number)
                    
        except Exception as e:
            logger.error(f"Error loading wells: {e}")
    
    def on_aquifer_filter_changed(self, aquifer_text):
        """Handle aquifer filter change."""
        aquifer_value = self.aquifer_combo.currentData()
        self.load_wells(aquifer_value)
    
    def on_well_selected(self, well_text):
        """Handle well selection."""
        well_number = self.well_combo.currentData()
        if well_number:
            logger.info(f"Selected well: {well_number}")
            self.load_well_data(well_number)
        else:
            # Clear data when no well selected
            self.current_well_id = None
            self.raw_data = None
            self.processed_data = None
            
            # Clear well selection in method tabs
            if hasattr(self, 'rise_tab'):
                self.rise_tab.update_well_selection([])
            if hasattr(self, 'mrc_tab'):
                self.mrc_tab.update_well_selection([])
            if hasattr(self, 'emr_tab'):
                self.emr_tab.update_well_selection([])
    
    def load_well_data(self, well_number):
        """Load and process data for the selected well."""
        try:
            # Store current well
            self.current_well_id = well_number
            
            # Get well data using database manager
            if hasattr(self.db_manager, 'water_level_model') and self.db_manager.water_level_model:
                # Use the water level model to get data
                readings_df = self.db_manager.water_level_model.get_readings(well_number)
                if readings_df is not None and not readings_df.empty:
                    # Store the DataFrame directly
                    self.raw_data = readings_df
                    
                    # Trigger data processing
                    self.process_well_data()
                    logger.info(f"Loaded {len(readings_df)} readings for well {well_number}")
                else:
                    logger.warning(f"No water level data found for well {well_number}")
                    QMessageBox.warning(self, "No Data", f"No water level data found for well {well_number}")
                    # Clear data
                    self.raw_data = None
                    self.processed_data = None
            else:
                logger.error("Water level model not available")
                QMessageBox.critical(self, "Error", "Database connection not available")
                
        except Exception as e:
            logger.error(f"Error loading well data: {e}")
            QMessageBox.critical(self, "Error", f"Error loading well data: {str(e)}")
    
    def process_well_data(self):
        """Process the loaded well data and update all method tabs."""
        if self.raw_data is None or self.raw_data.empty:
            return
            
        try:
            # Apply comprehensive preprocessing based on current settings
            logger.info(f"[PREPROCESS_DEBUG] Applying comprehensive processing with settings")
            self.processed_data = self._comprehensive_process_data(self.raw_data.copy())
            
            # Update all method tabs with the selected well
            # Format the well as expected by the existing interface: list of (well_id, well_name) tuples
            selected_wells = [(self.current_well_id, self.current_well_id)]
            
            if hasattr(self, 'rise_tab'):
                self.rise_tab.update_well_selection(selected_wells)
                # Share the processed data
                if hasattr(self.rise_tab, 'set_shared_data'):
                    self.rise_tab.set_shared_data(self.raw_data.copy(), self.processed_data.copy() if self.processed_data is not None else None)
            
            if hasattr(self, 'mrc_tab'):
                self.mrc_tab.update_well_selection(selected_wells)
                # Share the processed data
                if hasattr(self.mrc_tab, 'set_shared_data'):
                    self.mrc_tab.set_shared_data(self.raw_data.copy(), self.processed_data.copy() if self.processed_data is not None else None)
            
            if hasattr(self, 'emr_tab'):
                self.emr_tab.update_well_selection(selected_wells)
                # Share the processed data
                if hasattr(self.emr_tab, 'set_shared_data'):
                    self.emr_tab.set_shared_data(self.raw_data.copy(), self.processed_data.copy() if self.processed_data is not None else None)
                
            logger.info(f"Processed data for well {self.current_well_id}: {len(self.processed_data)} records")
            
        except Exception as e:
            logger.error(f"Error processing well data: {e}")
    
    def preprocess_data(self, raw_data):
        """Apply preprocessing to raw well data based on current settings."""
        # This is a simplified version - you may want to implement more sophisticated preprocessing
        # based on the settings from the unified settings dialog
        
        processed = raw_data.copy()
        
        # Basic preprocessing steps
        # 1. Remove NaN values
        processed = processed.dropna()
        
        # 2. Sort by timestamp
        if 'timestamp_utc' in processed.columns:
            processed = processed.sort_values('timestamp_utc')
        elif 'timestamp' in processed.columns:
            processed = processed.sort_values('timestamp')
            
        return processed
    
    def sync_database_selection(self, db_name: str):
        """Handle database selection changes from main app."""
        logger.debug(f"Recharge tab syncing to database: {db_name}")
        
        # Reload well data when database changes
        if hasattr(self, 'aquifer_combo') and hasattr(self, 'well_combo'):
            self.load_aquifer_filters()
            self.load_wells()
        
        # Clear current selection
        self.current_well_id = None
        self.raw_data = None
        self.processed_data = None
    
    def create_recharge_methods(self):
        """Create the tab widget for different recharge methods."""
        group_box = QGroupBox("Recharge Estimation Methods")
        layout = QVBoxLayout(group_box)
        
        # Create tab widget
        self.methods_tab = QTabWidget()
        
        # Create tabs for each method
        self.rise_tab = RiseTab(self.db_manager, self)
        self.mrc_tab = MrcTab(self.db_manager, self)
        self.emr_tab = EmrTab(self.db_manager, self)
        
        # Initialize tabs with current settings
        self.propagate_settings_to_tabs()
        
        # Add tabs
        self.methods_tab.addTab(self.rise_tab, "RISE Method")
        self.methods_tab.addTab(self.mrc_tab, "MRC Method")
        self.methods_tab.addTab(self.emr_tab, "EMR Method")
        
        layout.addWidget(self.methods_tab)
        
        return group_box
    
    def update_well_selection(self, selected_wells):
        """
        Update selected wells based on the main window's well table selection.
        
        Args:
            selected_wells: List of tuples (well_id, well_name) selected in the main window
        """
        self.selected_wells = selected_wells
        
        # Update UI elements in all tabs (combo boxes, buttons, etc.) but NOT data loading
        self.rise_tab.update_well_selection(self.selected_wells)
        self.mrc_tab.update_well_selection(self.selected_wells)
        self.emr_tab.update_well_selection(self.selected_wells)
        
        # Convert to list of well IDs for centralized processing
        well_ids = [well[0] if isinstance(well, (list, tuple)) else well for well in selected_wells]
        
        # Use centralized preprocessing instead of individual tab loading
        self.on_well_selection_changed(well_ids)
        
        logger.debug(f"Recharge tab updated with wells: {self.selected_wells}")
    
    def open_settings_dialog(self):
        """Open the unified settings dialog."""
        try:
            # Create and configure settings dialog
            settings_dialog = UnifiedRechargeSettings(self)
            settings_dialog.settings = self.settings.copy()
            settings_dialog.load_settings()
            
            # Show dialog and handle result
            if settings_dialog.exec_() == QDialog.Accepted:
                # Debug what we're getting back
                old_min_recession = self.settings.get('min_recession_length', 'NOT_SET')
                dialog_min_recession = settings_dialog.settings.get('min_recession_length', 'NOT_SET')
                logger.info(f"[DIALOG_RESULT_DEBUG] Parent settings min_recession_length: {old_min_recession}")
                logger.info(f"[DIALOG_RESULT_DEBUG] Dialog settings min_recession_length: {dialog_min_recession}")
                
                # Update settings
                self.settings.update(settings_dialog.settings)
                
                new_min_recession = self.settings.get('min_recession_length', 'NOT_SET')
                logger.info(f"[DIALOG_RESULT_DEBUG] Updated parent settings min_recession_length: {new_min_recession}")
                
                # Update unified_settings object too
                self.unified_settings.settings.update(settings_dialog.settings)
                unified_min_recession = self.unified_settings.settings.get('min_recession_length', 'NOT_SET')
                logger.info(f"[DIALOG_RESULT_DEBUG] Updated unified_settings min_recession_length: {unified_min_recession}")
                
                
                # Propagate settings to all method tabs
                self.propagate_settings_to_tabs()
                
                logger.info("Global settings updated and propagated to all tabs")
                
        except Exception as e:
            logger.error(f"Error opening settings dialog: {e}")
            QMessageBox.critical(self, "Settings Error", f"Failed to open settings: {str(e)}")
    
    
    
    def preprocess_data_centrally(self, well_id, force_reload=False, progress_dialog=None):
        """Centrally preprocess data once for all tabs to share.
        
        Args:
            well_id: The well ID to load and process data for
            force_reload: Force reload even if well_id hasn't changed
            progress_dialog: Optional progress dialog to update during processing
            
        Returns:
            tuple: (raw_data, processed_data) or (None, None) if no data
        """
        try:
            logger.info(f"[PREPROCESS_DEBUG] Centralized preprocessing for well {well_id}")
            
            # Check if we need to reload data
            if not force_reload and well_id == self.current_well_id and self.raw_data is not None:
                logger.info(f"[PREPROCESS_DEBUG] Using cached data for well {well_id}")
                if progress_dialog:
                    self._update_progress(progress_dialog, 4, "Using cached data", "Data already processed")
                return self.raw_data, self.processed_data
            
            # Update progress - loading data
            if progress_dialog:
                self._update_progress(progress_dialog, 1, "Loading raw data...", f"Fetching data for well {well_id}")
            
            # Load raw data
            logger.info(f"[PREPROCESS_DEBUG] Loading raw data for well {well_id}")
            raw_data = self.db_manager.get_well_data(well_id, downsample=None)
            
            if raw_data is None or raw_data.empty:
                logger.warning(f"[PREPROCESS_DEBUG] No data found for well {well_id}")
                self.raw_data = None
                self.processed_data = None
                self.current_well_id = well_id
                return None, None
            
            # Update progress - standardizing data
            if progress_dialog:
                self._update_progress(progress_dialog, 2, "Standardizing data format...", 
                                    f"Loaded {len(raw_data)} data points")
            
            # Standardize column names
            if 'timestamp_utc' in raw_data.columns:
                raw_data = raw_data.rename(columns={
                    'timestamp_utc': 'timestamp',
                    'water_level': 'level'
                })
            
            self.raw_data = raw_data
            self.current_well_id = well_id
            
            # Update progress - validation
            if progress_dialog:
                self._update_progress(progress_dialog, 3, "Validating data quality...", 
                                    "Checking data requirements and method suitability")
            
            # Validate data for recharge analysis
            logger.info(f"[VALIDATION_DEBUG] Validating data for recharge analysis")
            validation_results = self._validate_data_for_recharge_analysis(raw_data.copy())
            
            # Log validation results
            if not validation_results['success']:
                logger.warning(f"[VALIDATION_DEBUG] Data validation failed: {validation_results['errors']}")
                for error in validation_results['errors']:
                    logger.warning(f"[VALIDATION_DEBUG] Error: {error}")
            
            if validation_results['warnings']:
                for warning in validation_results['warnings']:
                    logger.info(f"[VALIDATION_DEBUG] Warning: {warning}")
            
            # Log method suitability
            for method, suitability in validation_results['method_suitability'].items():
                if not suitability['suitable']:
                    logger.warning(f"[VALIDATION_DEBUG] {method} method not suitable for this data")
                if suitability['messages']:
                    for msg in suitability['messages']:
                        logger.info(f"[VALIDATION_DEBUG] {method}: {msg}")
            
            # Store validation results for later use
            self.last_validation_results = validation_results
            
            # Update progress - processing data
            if progress_dialog:
                processing_steps = []
                if self.settings.get('downsample_frequency', 'None') != 'None':
                    processing_steps.append("downsampling")
                if self.settings.get('enable_smoothing', False):
                    processing_steps.append("smoothing")
                if self.settings.get('remove_outliers', False):
                    processing_steps.append("outlier removal")
                
                steps_text = ", ".join(processing_steps) if processing_steps else "basic filtering"
                self._update_progress(progress_dialog, 4, "Processing data...", 
                                    f"Applying {steps_text}")
            
            # Process data with current settings
            logger.info(f"[PREPROCESS_DEBUG] Processing data with settings: {list(self.settings.keys())}")
            self.processed_data = self._comprehensive_process_data(raw_data.copy())
            self.preprocessing_timestamp = datetime.now()
            
            logger.info(f"[PREPROCESS_DEBUG] Preprocessing complete: {len(raw_data)} raw -> {len(self.processed_data) if self.processed_data is not None else 0} processed")
            
            return self.raw_data, self.processed_data
            
        except Exception as e:
            logger.error(f"[PREPROCESS_DEBUG] Error in centralized preprocessing: {e}")
            return None, None
    
    def _comprehensive_process_data(self, raw_data):
        """Apply comprehensive preprocessing based on global settings."""
        if raw_data is None or raw_data.empty:
            return None
            
        try:
            import pandas as pd
            import numpy as np
            import re
            
            data = raw_data.copy()
            
            # Standardize column names first
            if 'timestamp_utc' in data.columns and 'water_level' in data.columns:
                data = data.rename(columns={
                    'timestamp_utc': 'timestamp',
                    'water_level': 'level'
                })
                logger.info(f"[PREPROCESS_DEBUG] Renamed columns: timestamp_utc->timestamp, water_level->level")
            elif 'timestamp' not in data.columns or 'level' not in data.columns:
                logger.error("Required columns (timestamp, level) not found in data")
                return raw_data.copy()
            
            # Make sure timestamp is datetime
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Apply downsampling
            downsample_freq = self.settings.get('downsample_frequency', 'No Downsampling')
            logger.info(f"[PREPROCESS_DEBUG] Downsampling with: {downsample_freq}")
            
            if downsample_freq and downsample_freq != 'No Downsampling':
                # Extract frequency code from string like "Daily (1D) - Recommended"
                match = re.search(r'\((\w+)\)', downsample_freq)
                if match:
                    freq_code = match.group(1)
                    method = self.settings.get('downsample_method', 'Median')
                    
                    # Extract method name
                    if 'Mean' in method:
                        agg_func = 'mean'
                    elif 'Max' in method:
                        agg_func = 'max'
                    elif 'Min' in method:
                        agg_func = 'min'
                    else:
                        agg_func = 'median'
                    
                    data = data.set_index('timestamp').resample(freq_code).agg({'level': agg_func}).reset_index()
                    data = data.dropna()
                    logger.info(f"[PREPROCESS_DEBUG] Applied {freq_code} downsampling using {agg_func}")
            
            # Apply smoothing
            if self.settings.get('enable_smoothing', False):
                window = self.settings.get('smoothing_window', 3)
                smoothing_type = self.settings.get('smoothing_type', 'Moving Average')
                
                if smoothing_type == 'Moving Average':
                    data['level'] = data['level'].rolling(window=window, center=True).mean()
                
                data = data.dropna()
                logger.info(f"[PREPROCESS_DEBUG] Applied {smoothing_type} smoothing with window {window}")
            
            # Remove outliers if enabled
            if self.settings.get('remove_outliers', False):
                threshold = self.settings.get('outlier_threshold', 3.0)
                z_scores = np.abs((data['level'] - data['level'].mean()) / data['level'].std())
                data = data[z_scores < threshold]
                logger.info(f"[PREPROCESS_DEBUG] Removed outliers with threshold {threshold}")
            
            # Final validation
            data = data.dropna()
            data = data[~data['level'].isin([np.inf, -np.inf])]
            
            logger.info(f"[PREPROCESS_DEBUG] Preprocessing complete: {len(data)} points")
            return data
            
        except Exception as e:
            logger.error(f"[PREPROCESS_DEBUG] Error in preprocessing: {e}")
            return raw_data.copy()

    def propagate_settings_to_tabs(self):
        """Propagate unified settings to all method tabs."""
        try:
            logger.info("[PREPROCESS_DEBUG] Propagating settings to tabs")
            
            # If we have a current well, reprocess data centrally
            if self.current_well_id:
                logger.info(f"[PREPROCESS_DEBUG] Reprocessing data for well {self.current_well_id}")
                raw_data, processed_data = self.preprocess_data_centrally(self.current_well_id, force_reload=True)
            else:
                raw_data, processed_data = None, None
            
            # Update each method tab with relevant settings AND shared data
            if hasattr(self, 'rise_tab'):
                rise_settings = self.unified_settings.get_method_settings('RISE')
                if hasattr(self.rise_tab, 'update_settings'):
                    self.rise_tab.update_settings(rise_settings)
                if hasattr(self.rise_tab, 'set_shared_data') and raw_data is not None:
                    self.rise_tab.set_shared_data(raw_data.copy(), processed_data.copy() if processed_data is not None else None)
                    
            if hasattr(self, 'mrc_tab'):
                mrc_settings = self.unified_settings.get_method_settings('MRC')
                if hasattr(self.mrc_tab, 'update_settings'):
                    self.mrc_tab.update_settings(mrc_settings)
                if hasattr(self.mrc_tab, 'set_shared_data') and raw_data is not None:
                    self.mrc_tab.set_shared_data(raw_data.copy(), processed_data.copy() if processed_data is not None else None)
                    
            if hasattr(self, 'emr_tab'):
                emr_settings = self.unified_settings.get_method_settings('EMR')
                if hasattr(self.emr_tab, 'update_settings'):
                    self.emr_tab.update_settings(emr_settings)
                if hasattr(self.emr_tab, 'set_shared_data') and raw_data is not None:
                    self.emr_tab.set_shared_data(raw_data.copy(), processed_data.copy() if processed_data is not None else None)
            
                    
        except Exception as e:
            logger.error(f"Error propagating settings to tabs: {e}")
    
    def on_well_selection_changed(self, selected_wells):
        """Handle well selection changes from the main interface.
        
        Args:
            selected_wells: List of selected well IDs
        """
        try:
            logger.info(f"[PREPROCESS_DEBUG] Well selection changed: {selected_wells}")
            
            if selected_wells and len(selected_wells) > 0:
                well_id = selected_wells[0]  # Use first selected well
                logger.info(f"[PREPROCESS_DEBUG] Processing data for well: {well_id}")
                
                # Preprocess data centrally and share with all tabs
                raw_data, processed_data = self.preprocess_data_centrally(well_id)
                
                # Update well selection for all tabs first
                # Use the original selected_wells data that was passed to update_well_selection
                # This preserves the correct CAE number information
                well_selection = self.selected_wells
                
                if hasattr(self, 'rise_tab') and hasattr(self.rise_tab, 'update_well_selection'):
                    self.rise_tab.update_well_selection(well_selection)
                
                if hasattr(self, 'mrc_tab') and hasattr(self.mrc_tab, 'update_well_selection'):
                    self.mrc_tab.update_well_selection(well_selection)
                
                if hasattr(self, 'emr_tab') and hasattr(self.emr_tab, 'update_well_selection'):
                    self.emr_tab.update_well_selection(well_selection)
                
                # Share data with all tabs
                if hasattr(self, 'rise_tab') and hasattr(self.rise_tab, 'set_shared_data'):
                    if raw_data is not None:
                        self.rise_tab.set_shared_data(raw_data.copy(), processed_data.copy() if processed_data is not None else None)
                    else:
                        self.rise_tab.set_shared_data(None, None)
                
                if hasattr(self, 'mrc_tab') and hasattr(self.mrc_tab, 'set_shared_data'):
                    if raw_data is not None:
                        self.mrc_tab.set_shared_data(raw_data.copy(), processed_data.copy() if processed_data is not None else None)
                    else:
                        self.mrc_tab.set_shared_data(None, None)
                
                if hasattr(self, 'emr_tab') and hasattr(self.emr_tab, 'set_shared_data'):
                    if raw_data is not None:
                        self.emr_tab.set_shared_data(raw_data.copy(), processed_data.copy() if processed_data is not None else None)
                    else:
                        self.emr_tab.set_shared_data(None, None)
                        
            else:
                # No wells selected - clear data from all tabs
                logger.info("[PREPROCESS_DEBUG] No wells selected, clearing data")
                self.current_well_id = None
                self.raw_data = None
                self.processed_data = None
                
                # Clear well selection for all tabs
                if hasattr(self, 'rise_tab') and hasattr(self.rise_tab, 'update_well_selection'):
                    self.rise_tab.update_well_selection([])
                if hasattr(self, 'mrc_tab') and hasattr(self.mrc_tab, 'update_well_selection'):
                    self.mrc_tab.update_well_selection([])
                if hasattr(self, 'emr_tab') and hasattr(self.emr_tab, 'update_well_selection'):
                    self.emr_tab.update_well_selection([])
                
                # Clear data from all tabs
                if hasattr(self, 'rise_tab') and hasattr(self.rise_tab, 'set_shared_data'):
                    self.rise_tab.set_shared_data(None, None)
                if hasattr(self, 'mrc_tab') and hasattr(self.mrc_tab, 'set_shared_data'):
                    self.mrc_tab.set_shared_data(None, None)
                if hasattr(self, 'emr_tab') and hasattr(self.emr_tab, 'set_shared_data'):
                    self.emr_tab.set_shared_data(None, None)
                    
        except Exception as e:
            logger.error(f"[PREPROCESS_DEBUG] Error handling well selection change: {e}")
    
    def get_current_settings(self):
        """Get current unified settings."""
        return self.settings.copy()
    
    def update_unified_settings(self, new_settings):
        """Update unified settings and propagate to tabs."""
        self.settings.update(new_settings)
        self.propagate_settings_to_tabs()
    
    def _load_saved_settings(self):
        """Load saved settings and preferences from persistence layer."""
        try:
            # Load saved unified settings
            saved_settings = self.settings_persistence.get_unified_settings()
            if saved_settings:
                self.settings.update(saved_settings)
                logger.info("Loaded saved unified settings")
                
            # Load user preferences
            preference_keys = [
                'interface_mode', 'default_method', 'show_launcher_button',
                'auto_apply_unified_settings', 'save_settings_on_change'
            ]
            
            for key in preference_keys:
                value = self.settings_persistence.get_user_preference(key)
                if value is not None:
                    self.user_preferences[key] = value
                    
        except Exception as e:
            logger.error(f"Error loading saved settings: {e}")
            
    def _save_current_settings(self):
        """Save current settings to persistence layer."""
        try:
            # Save unified settings
            self.settings_persistence.save_unified_settings(self.settings)
            
            # Save user preferences
            for key, value in self.user_preferences.items():
                self.settings_persistence.save_user_preference(key, value)
                
            logger.debug("Saved current settings and preferences")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    
    
    
    def _validate_data_for_recharge_analysis(self, raw_data):
        """Comprehensive validation of data for recharge analysis.
        
        Args:
            raw_data: DataFrame with timestamp and level columns
            
        Returns:
            dict: Validation results with success flag and detailed messages
        """
        validation_results = {
            'success': True,
            'warnings': [],
            'errors': [],
            'method_suitability': {
                'RISE': {'suitable': True, 'messages': []},
                'MRC': {'suitable': True, 'messages': []},
                'EMR': {'suitable': True, 'messages': []}
            },
            'data_stats': {}
        }
        
        try:
            if raw_data is None or raw_data.empty:
                validation_results['success'] = False
                validation_results['errors'].append("No data available for analysis")
                return validation_results
            
            # Basic data quality checks
            data_points = len(raw_data)
            validation_results['data_stats']['total_points'] = data_points
            
            # Check minimum data requirements
            if data_points < 100:
                validation_results['errors'].append(f"Insufficient data points ({data_points}). At least 100 points recommended for reliable analysis.")
                validation_results['success'] = False
            elif data_points < 365:
                validation_results['warnings'].append(f"Limited data points ({data_points}). At least 365 points (1 year) recommended for seasonal analysis.")
            
            # Check for required columns
            required_columns = ['timestamp', 'level']
            missing_columns = [col for col in required_columns if col not in raw_data.columns]
            if missing_columns:
                validation_results['errors'].append(f"Missing required columns: {missing_columns}")
                validation_results['success'] = False
                return validation_results
            
            # Check data types and quality
            if not pd.api.types.is_datetime64_any_dtype(raw_data['timestamp']):
                try:
                    raw_data['timestamp'] = pd.to_datetime(raw_data['timestamp'])
                except:
                    validation_results['errors'].append("Cannot convert timestamp column to datetime format")
                    validation_results['success'] = False
                    return validation_results
            
            # Check for numeric water level data
            if not pd.api.types.is_numeric_dtype(raw_data['level']):
                validation_results['errors'].append("Water level column must contain numeric data")
                validation_results['success'] = False
                return validation_results
            
            # Calculate date range
            date_range = raw_data['timestamp'].max() - raw_data['timestamp'].min()
            validation_results['data_stats']['date_range_days'] = date_range.days
            validation_results['data_stats']['start_date'] = raw_data['timestamp'].min().strftime('%Y-%m-%d')
            validation_results['data_stats']['end_date'] = raw_data['timestamp'].max().strftime('%Y-%m-%d')
            
            # Check for sufficient time span
            if date_range.days < 90:
                validation_results['errors'].append(f"Insufficient time span ({date_range.days} days). At least 90 days recommended.")
                validation_results['success'] = False
            elif date_range.days < 365:
                validation_results['warnings'].append(f"Limited time span ({date_range.days} days). At least 1 year recommended for seasonal analysis.")
            
            # Check for data gaps
            raw_data_sorted = raw_data.sort_values('timestamp')
            time_diffs = raw_data_sorted['timestamp'].diff().dt.total_seconds() / 3600  # Convert to hours
            large_gaps = time_diffs[time_diffs > 168]  # Gaps larger than 1 week
            if len(large_gaps) > 0:
                max_gap_days = large_gaps.max() / 24
                validation_results['warnings'].append(f"Found {len(large_gaps)} data gaps larger than 1 week (max: {max_gap_days:.1f} days)")
            
            # Check for valid water level range
            level_stats = raw_data['level'].describe()
            validation_results['data_stats']['level_stats'] = level_stats.to_dict()
            
            # Check for outliers or unrealistic values
            level_range = level_stats['max'] - level_stats['min']
            if level_range > 100:  # More than 100 ft variation
                validation_results['warnings'].append(f"Large water level variation ({level_range:.1f} ft). Check for data quality issues.")
            
            # Method-specific validation
            self._validate_method_requirements(raw_data, validation_results)
            
            return validation_results
            
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"Error in data validation: {e}")
            return validation_results
    
    def _validate_method_requirements(self, raw_data, validation_results):
        """Validate method-specific requirements for recharge analysis methods."""
        try:
            data_points = len(raw_data)
            date_range_days = validation_results['data_stats']['date_range_days']
            
            # RISE method validation
            rise_settings = self.unified_settings.get_method_settings('RISE')
            min_time_between = rise_settings.get('min_time_between_events', 7)  # days
            
            if date_range_days < 30:
                validation_results['method_suitability']['RISE']['suitable'] = False
                validation_results['method_suitability']['RISE']['messages'].append("RISE method requires at least 30 days of data for event detection")
            elif data_points < 200:
                validation_results['method_suitability']['RISE']['messages'].append("RISE method works best with frequent measurements (hourly/daily)")
            
            # MRC method validation
            mrc_settings = self.unified_settings.get_method_settings('MRC')
            min_recession_length = mrc_settings.get('min_recession_length', 10)  # days
            
            if date_range_days < min_recession_length * 3:
                validation_results['method_suitability']['MRC']['suitable'] = False
                validation_results['method_suitability']['MRC']['messages'].append(f"MRC method requires at least {min_recession_length * 3} days for reliable recession analysis")
            elif date_range_days < 180:
                validation_results['method_suitability']['MRC']['messages'].append("MRC method works best with seasonal data (6+ months) to capture multiple recession events")
            
            # EMR method validation
            emr_settings = self.unified_settings.get_method_settings('EMR')
            seasonal_periods = erc_settings.get('seasonal_periods', 4)
            
            if date_range_days < 365:
                validation_results['method_suitability']['EMR']['suitable'] = False
                validation_results['method_suitability']['EMR']['messages'].append("EMR method requires at least 1 year of data for storm-recharge correlation analysis")
            elif date_range_days < 365 * 2:
                validation_results['method_suitability']['EMR']['messages'].append("EMR method works best with multi-year data for robust storm-recharge analysis")
            
        except Exception as e:
            logger.error(f"Error in method-specific validation: {e}")
    
    def _create_progress_dialog(self, title="Processing Data", max_steps=5):
        """Create and configure a progress dialog for data processing operations."""
        try:
            progress_dialog = QProgressDialog(title, "Cancel", 0, max_steps, self)
            progress_dialog.setWindowTitle("Recharge Data Processing")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(500)  # Show after 500ms
            progress_dialog.setAutoClose(True)
            progress_dialog.setAutoReset(True)
            progress_dialog.resize(400, 120)
            
            # Style the progress dialog
            progress_dialog.setStyleSheet("""
                QProgressDialog {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                }
                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #f8f9fa;
                }
                QProgressBar::chunk {
                    background-color: #17a2b8;
                    border-radius: 3px;
                }
                QPushButton {
                    padding: 5px 15px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f8f9fa;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """)
            
            return progress_dialog
            
        except Exception as e:
            logger.error(f"Error creating progress dialog: {e}")
            return None
    
    def _update_progress(self, progress_dialog, step, message, details=""):
        """Update progress dialog with current step and message."""
        if progress_dialog is None:
            return
            
        try:
            progress_dialog.setValue(step)
            
            # Update the label text
            if details:
                progress_dialog.setLabelText(f"{message}\n{details}")
            else:
                progress_dialog.setLabelText(message)
            
            # Process events to keep UI responsive
            QApplication.processEvents()
            
            # Check if user cancelled
            if progress_dialog.wasCanceled():
                logger.info("User cancelled data processing")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            return True  # Continue processing even if progress update fails
    
    def _show_error_with_recovery(self, title, error_message, error_type="general", suggestions=None):
        """Show an enhanced error dialog with recovery suggestions and actions."""
        try:
            from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QHBoxLayout, QDialogButtonBox
            
            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(title)
            dialog.setModal(True)
            dialog.resize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Error message
            error_label = QLabel(f"<b>Error:</b> {error_message}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            # Suggestions based on error type
            if suggestions is None:
                suggestions = self._get_error_suggestions(error_type, error_message)
            
            if suggestions:
                suggestions_label = QLabel("<b>Suggested Solutions:</b>")
                layout.addWidget(suggestions_label)
                
                suggestions_text = QTextEdit()
                suggestions_text.setReadOnly(True)
                suggestions_text.setMaximumHeight(150)
                suggestions_text.setPlainText("\n".join([f"• {s}" for s in suggestions]))
                layout.addWidget(suggestions_text)
            
            # Recovery actions
            actions_layout = QHBoxLayout()
            
            # Default buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok, dialog)
            button_box.accepted.connect(dialog.accept)
            
            # Add recovery action buttons based on error type
            if error_type == "data_loading":
                retry_btn = QPushButton("Retry Loading")
                retry_btn.clicked.connect(lambda: self._retry_data_loading(dialog))
                actions_layout.addWidget(retry_btn)
                
                settings_btn = QPushButton("Check Settings")
                settings_btn.clicked.connect(lambda: self._open_settings_for_recovery(dialog))
                actions_layout.addWidget(settings_btn)
                
            elif error_type == "validation":
                settings_btn = QPushButton("Adjust Settings")
                settings_btn.clicked.connect(lambda: self._open_settings_for_recovery(dialog))
                actions_layout.addWidget(settings_btn)
                
                info_btn = QPushButton("Data Requirements")
                info_btn.clicked.connect(lambda: self._show_data_requirements(dialog))
                actions_layout.addWidget(info_btn)
                
            elif error_type == "processing":
                reset_btn = QPushButton("Reset to Defaults")
                reset_btn.clicked.connect(lambda: self._reset_settings_to_defaults(dialog))
                actions_layout.addWidget(reset_btn)
                
                settings_btn = QPushButton("Adjust Settings")
                settings_btn.clicked.connect(lambda: self._open_settings_for_recovery(dialog))
                actions_layout.addWidget(settings_btn)
            
            actions_layout.addWidget(button_box)
            layout.addLayout(actions_layout)
            
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing enhanced error dialog: {e}")
            # Fallback to simple message box
            QMessageBox.critical(self, title, error_message)
    
    def _get_error_suggestions(self, error_type, error_message):
        """Get contextual suggestions based on error type and message."""
        suggestions = []
        
        if error_type == "data_loading":
            suggestions.extend([
                "Verify the well ID is correct and exists in the database",
                "Check your database connection and permissions",
                "Ensure the selected well has water level data available",
                "Try refreshing the well list in the main interface"
            ])
            
        elif error_type == "validation":
            if "Insufficient data points" in error_message:
                suggestions.extend([
                    "Select a well with more comprehensive data (at least 100 points)",
                    "Check if there are other wells with longer monitoring periods",
                    "Consider using a different time range if available"
                ])
            elif "time span" in error_message:
                suggestions.extend([
                    "Select a well with a longer monitoring period",
                    "For reliable analysis, at least 90 days of data is recommended",
                    "Seasonal analysis requires at least 1 year of data"
                ])
            elif "method" in error_message:
                suggestions.extend([
                    "Try a different recharge analysis method that suits your data",
                    "RISE method: Good for frequent measurements (hourly/daily)",
                    "MRC method: Requires seasonal data with recession periods",
                    "EMR method: Needs at least 1 year for storm-recharge analysis"
                ])
            else:
                suggestions.extend([
                    "Check data quality and ensure water level measurements are valid",
                    "Verify that timestamp and water level columns contain proper data",
                    "Review data for large gaps or unrealistic values"
                ])
                
        elif error_type == "processing":
            suggestions.extend([
                "Check preprocessing settings for invalid combinations",
                "Reduce smoothing window size if it's too large for your dataset",
                "Adjust outlier detection threshold if it's too restrictive",
                "Try simpler processing settings (disable advanced features)",
                "Reset settings to defaults and gradually adjust as needed"
            ])
            
        else:  # general
            suggestions.extend([
                "Check the application logs for detailed error information",
                "Try restarting the application if the issue persists",
                "Verify your data files and database connections",
                "Contact support if the problem continues"
            ])
        
        return suggestions
    
    def _retry_data_loading(self, dialog):
        """Retry loading data for the current well."""
        try:
            dialog.accept()
            if self.current_well_id:
                # Force reload data for current well
                self.propagate_settings_to_tabs()
        except Exception as e:
            logger.error(f"Error retrying data loading: {e}")
    
    def _open_settings_for_recovery(self, dialog):
        """Open settings dialog for error recovery."""
        try:
            dialog.accept()
            self.open_settings_dialog()
        except Exception as e:
            logger.error(f"Error opening settings for recovery: {e}")
    
    def _show_data_requirements(self, dialog):
        """Show detailed data requirements for recharge analysis."""
        try:
            requirements_text = """
Data Requirements for Recharge Analysis:

GENERAL REQUIREMENTS:
• Minimum 100 data points (more is better)
• At least 90 days of monitoring (1+ years recommended)
• Water level measurements in numeric format
• Valid timestamps for all measurements
• Unconfined aquifer wells work best

METHOD-SPECIFIC REQUIREMENTS:

RISE METHOD:
• Frequent measurements (hourly/daily preferred)
• At least 30 days of data for event detection
• Clear water level rises following precipitation

MRC METHOD:
• Seasonal data (6+ months) with recession periods
• Multiple recession events for curve fitting
• Clear recession patterns following peaks

EMR METHOD:
• At least 1 year of data for seasonal analysis
• Multiple years preferred for robust analysis
• Seasonal variation in recession patterns

DATA QUALITY TIPS:
• Remove obvious outliers and erroneous readings
• Fill small gaps if possible, note larger gaps
• Ensure consistent measurement frequency
• Verify units and datum consistency
            """
            
            QMessageBox.information(dialog.parent(), "Data Requirements", requirements_text.strip())
            
        except Exception as e:
            logger.error(f"Error showing data requirements: {e}")
    
    def _reset_settings_to_defaults(self, dialog):
        """Reset preprocessing settings to safe defaults."""
        try:
            dialog.accept()
            
            # Reset to conservative defaults
            default_settings = {
                'downsample_frequency': 'Daily (1D) - Recommended',
                'downsample_method': 'Median (for pumped wells) - Recommended',
                'enable_smoothing': True,
                'smoothing_window': 3,
                'smoothing_type': 'Moving Average',
                'remove_outliers': True,
                'outlier_threshold': 3.0
            }
            
            # Update settings
            self.settings.update(default_settings)
            self.unified_settings.settings.update(default_settings)
            
            
            QMessageBox.information(
                self, "Settings Reset", 
                "Preprocessing settings have been reset to safe defaults.\n\n"
                "You can now try reprocessing your data or adjust settings as needed."
            )
            
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            
    def open_preferences_dialog(self):
        """Open user preferences dialog."""
        try:
            # Create preferences dialog
            preferences_dialog = UserPreferencesDialog(self)
            
            # Connect preference change signals
            preferences_dialog.preferences_changed.connect(self.on_preferences_changed)
            preferences_dialog.interface_mode_changed.connect(self.on_interface_mode_changed)
            
            # Show dialog
            preferences_dialog.exec_()
            
            logger.info("User preferences dialog opened")
            
        except Exception as e:
            logger.error(f"Error opening preferences dialog: {e}")
            QMessageBox.critical(self, "Preferences Error", f"Failed to open preferences: {str(e)}")
            
    # open_help_system method removed - now handled by main application help system
    
    def on_preferences_changed(self, preferences):
        """Handle preference changes."""
        try:
            # Update internal preferences
            self.user_preferences.update(preferences)
            
            # Apply immediate changes
            if preferences.get('auto_apply_unified_settings', True):
                self.propagate_settings_to_tabs()
                
            # Save if auto-save is enabled
            if preferences.get('save_settings_on_change', True):
                self._save_current_settings()
                
            # Update UI based on preferences
            self._apply_preference_changes(preferences)
            
            logger.info("User preferences updated and applied")
            
        except Exception as e:
            logger.error(f"Error applying preference changes: {e}")
            
    def on_interface_mode_changed(self, mode):
        """Handle interface mode changes."""
        try:
            self.user_preferences['interface_mode'] = mode
            logger.info(f"Interface mode changed to: {mode}")
            
        except Exception as e:
            logger.error(f"Error changing interface mode: {e}")
            
    def _apply_preference_changes(self, preferences):
        """Apply preference changes to the UI."""
        try:
            # Apply UI preferences as needed
            pass
            
        except Exception as e:
            logger.error(f"Error applying UI preference changes: {e}")
            
    def closeEvent(self, event):
        """Handle tab close event."""
        try:
            # Save current state before closing
            if self.user_preferences.get('auto_save_sessions', True):
                session_data = {
                    'settings': self.settings,
                    'selected_wells': self.selected_wells,
                    'current_tab': getattr(self, 'methods_tab', None) and self.methods_tab.currentIndex()
                }
                self.settings_persistence.save_session_history(session_data)
                
            # Close persistence connection
            self.settings_persistence.close()
            
            event.accept()
            logger.info("Recharge tab closed and state saved")
            
        except Exception as e:
            logger.error(f"Error closing recharge tab: {e}")
            event.accept()