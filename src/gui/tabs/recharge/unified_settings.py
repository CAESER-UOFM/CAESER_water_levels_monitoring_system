"""
Unified settings system for all recharge calculation methods.
This centralizes shared parameters while maintaining method-specific options.
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QDoubleSpinBox, QPushButton, QGroupBox, 
                             QCheckBox, QSpinBox, QTabWidget, QWidget,
                             QDialogButtonBox, QFormLayout, QSlider, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
import json

logger = logging.getLogger(__name__)


class UnifiedRechargeSettings(QDialog):
    """Unified settings dialog for all recharge calculation methods."""
    
    settings_changed = pyqtSignal(dict)  # Emit when settings change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recharge Analysis Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        # Default settings
        self.settings = self.get_default_settings()
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for organized settings
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Common settings tab
        self.tabs.addTab(self.create_common_tab(), "Common Settings")
        
        # Data preprocessing tab
        self.tabs.addTab(self.create_preprocessing_tab(), "Data Preprocessing")
        
        # Method-specific tabs
        self.tabs.addTab(self.create_rise_tab(), "RISE Specific")
        self.tabs.addTab(self.create_mrc_tab(), "MRC Specific")
        self.tabs.addTab(self.create_emr_tab(), "EMR Specific")
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(button_box)
        
    def create_common_tab(self):
        """Create the common settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Well and site settings
        site_group = QGroupBox("Site Settings")
        site_layout = QFormLayout(site_group)
        
        self.specific_yield = QDoubleSpinBox()
        self.specific_yield.setRange(0.001, 0.5)
        self.specific_yield.setSingleStep(0.01)
        self.specific_yield.setDecimals(3)
        self.specific_yield.setSuffix(" (dimensionless)")
        site_layout.addRow("Specific Yield:", self.specific_yield)
        
        layout.addWidget(site_group)
        
        # Water year settings
        water_year_group = QGroupBox("Water Year Definition")
        water_year_layout = QFormLayout(water_year_group)
        
        self.water_year_month = QSpinBox()
        self.water_year_month.setRange(1, 12)
        water_year_layout.addRow("Start Month:", self.water_year_month)
        
        self.water_year_day = QSpinBox()
        self.water_year_day.setRange(1, 31)
        water_year_layout.addRow("Start Day:", self.water_year_day)
        
        note_label = QLabel("Standard water year: October 1 - September 30")
        note_label.setStyleSheet("font-style: italic; color: #666;")
        water_year_layout.addRow(note_label)
        
        layout.addWidget(water_year_group)
        
        # Analysis settings
        analysis_group = QGroupBox("Analysis Settings")
        analysis_layout = QFormLayout(analysis_group)
        
        self.confidence_level = QComboBox()
        self.confidence_level.addItems(["90%", "95%", "99%"])
        self.confidence_level.setCurrentText("95%")
        analysis_layout.addRow("Confidence Level:", self.confidence_level)
        
        self.units = QComboBox()
        self.units.addItems(["feet", "meters"])
        self.units.setCurrentText("feet")
        analysis_layout.addRow("Elevation Units:", self.units)
        
        layout.addWidget(analysis_group)
        layout.addStretch()
        
        return widget
        
    def create_preprocessing_tab(self):
        """Create the data preprocessing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Downsampling settings
        downsample_group = QGroupBox("Data Downsampling")
        downsample_layout = QFormLayout(downsample_group)
        
        self.downsample_frequency = QComboBox()
        self.downsample_frequency.addItems([
            "None (use original frequency)",
            "Hourly (1h)",
            "Daily (1D) - Recommended",
            "Weekly (1W)"
        ])
        self.downsample_frequency.setCurrentIndex(2)
        downsample_layout.addRow("Frequency:", self.downsample_frequency)
        
        self.downsample_method = QComboBox()
        self.downsample_method.addItems([
            "Mean (general use)",
            "Median (for pumped wells) - Recommended",
            "End-of-period (USGS compatibility)"
        ])
        self.downsample_method.setCurrentIndex(1)
        downsample_layout.addRow("Method:", self.downsample_method)
        
        layout.addWidget(downsample_group)
        
        # Smoothing settings
        smoothing_group = QGroupBox("Data Smoothing")
        smoothing_layout = QFormLayout(smoothing_group)
        
        self.enable_smoothing = QCheckBox("Enable data smoothing")
        self.enable_smoothing.setChecked(True)
        smoothing_layout.addRow(self.enable_smoothing)
        
        self.smoothing_window = QSpinBox()
        self.smoothing_window.setRange(2, 14)
        self.smoothing_window.setValue(3)
        self.smoothing_window.setSuffix(" days")
        smoothing_layout.addRow("Window Size:", self.smoothing_window)
        
        self.smoothing_type = QComboBox()
        self.smoothing_type.addItems(["Moving Average", "Gaussian", "Savitzky-Golay"])
        smoothing_layout.addRow("Smoothing Type:", self.smoothing_type)
        
        layout.addWidget(smoothing_group)
        
        # Quality control
        qc_group = QGroupBox("Quality Control")
        qc_layout = QFormLayout(qc_group)
        
        self.remove_outliers = QCheckBox("Remove statistical outliers")
        self.remove_outliers.setChecked(True)
        qc_layout.addRow(self.remove_outliers)
        
        self.outlier_threshold = QDoubleSpinBox()
        self.outlier_threshold.setRange(1.0, 5.0)
        self.outlier_threshold.setValue(3.0)
        self.outlier_threshold.setSuffix(" standard deviations")
        qc_layout.addRow("Outlier Threshold:", self.outlier_threshold)
        
        layout.addWidget(qc_group)
        layout.addStretch()
        
        return widget
        
    def create_rise_tab(self):
        """Create RISE-specific settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # RISE parameters
        rise_group = QGroupBox("RISE Method Parameters")
        rise_layout = QFormLayout(rise_group)
        
        self.rise_threshold = QDoubleSpinBox()
        self.rise_threshold.setRange(0.01, 10.0)
        self.rise_threshold.setValue(0.2)
        self.rise_threshold.setSuffix(" ft")
        self.rise_threshold.setDecimals(2)
        rise_layout.addRow("Rise Threshold:", self.rise_threshold)
        
        self.window_type = QComboBox()
        self.window_type.addItems(["Trailing (recommended)", "Centered"])
        rise_layout.addRow("Smoothing Window Type:", self.window_type)
        
        layout.addWidget(rise_group)
        
        # Event filtering
        event_group = QGroupBox("Event Filtering")
        event_layout = QFormLayout(event_group)
        
        self.min_time_between_events = QSpinBox()
        self.min_time_between_events.setRange(0, 30)
        self.min_time_between_events.setValue(1)
        self.min_time_between_events.setSuffix(" days")
        event_layout.addRow("Min Time Between Events:", self.min_time_between_events)
        
        self.max_rise_rate = QDoubleSpinBox()
        self.max_rise_rate.setRange(0.1, 50.0)
        self.max_rise_rate.setValue(10.0)
        self.max_rise_rate.setSuffix(" ft/day")
        event_layout.addRow("Max Rise Rate:", self.max_rise_rate)
        
        layout.addWidget(event_group)
        layout.addStretch()
        
        return widget
        
    def create_mrc_tab(self):
        """Create MRC-specific settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Recession identification
        recession_group = QGroupBox("Recession Identification")
        recession_layout = QFormLayout(recession_group)
        
        self.min_recession_length = QSpinBox()
        self.min_recession_length.setRange(5, 30)
        self.min_recession_length.setValue(10)
        self.min_recession_length.setSuffix(" days")
        recession_layout.addRow("Min Recession Length:", self.min_recession_length)
        
        self.fluctuation_tolerance = QDoubleSpinBox()
        self.fluctuation_tolerance.setRange(0.0, 0.1)
        self.fluctuation_tolerance.setValue(0.01)
        self.fluctuation_tolerance.setSuffix(" ft")
        self.fluctuation_tolerance.setDecimals(3)
        recession_layout.addRow("Fluctuation Tolerance:", self.fluctuation_tolerance)
        
        layout.addWidget(recession_group)
        
        # Recharge calculation
        recharge_group = QGroupBox("Recharge Calculation")
        recharge_layout = QFormLayout(recharge_group)
        
        self.mrc_deviation_threshold = QDoubleSpinBox()
        self.mrc_deviation_threshold.setRange(0.01, 5.0)
        self.mrc_deviation_threshold.setValue(0.1)
        self.mrc_deviation_threshold.setSuffix(" ft")
        recharge_layout.addRow("Deviation Threshold:", self.mrc_deviation_threshold)
        
        layout.addWidget(recharge_group)
        
        # Precipitation settings
        precip_group = QGroupBox("Precipitation Filtering (Optional)")
        precip_layout = QFormLayout(precip_group)
        
        self.use_precipitation = QCheckBox("Filter recessions by precipitation")
        precip_layout.addRow(self.use_precipitation)
        
        self.precip_threshold = QDoubleSpinBox()
        self.precip_threshold.setRange(0.0, 1.0)
        self.precip_threshold.setValue(0.1)
        self.precip_threshold.setSuffix(" inches")
        precip_layout.addRow("Max Precipitation:", self.precip_threshold)
        
        self.precip_lag = QSpinBox()
        self.precip_lag.setRange(0, 7)
        self.precip_lag.setValue(2)
        self.precip_lag.setSuffix(" days")
        precip_layout.addRow("Post-Precip Lag:", self.precip_lag)
        
        layout.addWidget(precip_group)
        layout.addStretch()
        
        return widget
        
    def create_emr_tab(self):
        """Create EMR-specific settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Curve fitting
        fitting_group = QGroupBox("Curve Fitting")
        fitting_layout = QFormLayout(fitting_group)
        
        self.curve_type = QComboBox()
        self.curve_type.addItems([
            "Exponential (recommended)",
            "Power Law",
            "Polynomial",
            "Multi-Segment"
        ])
        fitting_layout.addRow("Curve Type:", self.curve_type)
        
        self.r_squared_threshold = QDoubleSpinBox()
        self.r_squared_threshold.setRange(0.1, 1.0)
        self.r_squared_threshold.setValue(0.7)
        self.r_squared_threshold.setDecimals(2)
        fitting_layout.addRow("Min R² Threshold:", self.r_squared_threshold)
        
        self.validation_split = QDoubleSpinBox()
        self.validation_split.setRange(0.1, 0.5)
        self.validation_split.setValue(0.2)
        self.validation_split.setDecimals(2)
        fitting_layout.addRow("Validation Split:", self.validation_split)
        
        layout.addWidget(fitting_group)
        
        # Seasonal analysis
        seasonal_group = QGroupBox("Seasonal Analysis")
        seasonal_layout = QFormLayout(seasonal_group)
        
        self.enable_seasonal = QCheckBox("Enable seasonal analysis")
        seasonal_layout.addRow(self.enable_seasonal)
        
        self.seasonal_periods = QComboBox()
        self.seasonal_periods.addItems(["4 Seasons", "12 Months", "Growing/Non-growing"])
        seasonal_layout.addRow("Seasonal Periods:", self.seasonal_periods)
        
        layout.addWidget(seasonal_group)
        
        # Recharge detection
        detection_group = QGroupBox("Recharge Detection")
        detection_layout = QFormLayout(detection_group)
        
        self.emr_deviation_threshold = QDoubleSpinBox()
        self.emr_deviation_threshold.setRange(0.001, 1.0)
        self.emr_deviation_threshold.setValue(0.05)
        self.emr_deviation_threshold.setSuffix(" ft")
        self.emr_deviation_threshold.setDecimals(3)
        detection_layout.addRow("Deviation Threshold:", self.emr_deviation_threshold)
        
        layout.addWidget(detection_group)
        layout.addStretch()
        
        return widget
        
    def get_default_settings(self):
        """Get default settings for all methods."""
        return {
            # Common settings
            'specific_yield': 0.2,
            'water_year_month': 10,
            'water_year_day': 1,
            'confidence_level': '95%',
            'units': 'feet',
            
            # Preprocessing
            'downsample_frequency': 'Daily (1D) - Recommended',
            'downsample_method': 'Median (for pumped wells) - Recommended',
            'enable_smoothing': True,
            'smoothing_window': 3,
            'smoothing_type': 'Moving Average',
            'remove_outliers': True,
            'outlier_threshold': 3.0,
            
            # RISE specific
            'rise_threshold': 0.2,
            'window_type': 'Trailing (recommended)',
            'min_time_between_events': 1,
            'max_rise_rate': 10.0,
            
            # MRC specific
            'min_recession_length': 10,
            'fluctuation_tolerance': 0.01,
            'mrc_deviation_threshold': 0.1,
            'use_precipitation': False,
            'precip_threshold': 0.1,
            'precip_lag': 2,
            
            # EMR specific
            'curve_type': 'Exponential (recommended)',
            'r_squared_threshold': 0.7,
            'validation_split': 0.2,
            'enable_seasonal': False,
            'seasonal_periods': '4 Seasons',
            'emr_deviation_threshold': 0.05
        }
        
    def load_settings(self):
        """Load settings into UI controls."""
        self.specific_yield.setValue(self.settings['specific_yield'])
        self.water_year_month.setValue(self.settings['water_year_month'])
        self.water_year_day.setValue(self.settings['water_year_day'])
        self.confidence_level.setCurrentText(self.settings['confidence_level'])
        self.units.setCurrentText(self.settings['units'])
        
        # Preprocessing
        self.downsample_frequency.setCurrentText(self.settings['downsample_frequency'])
        self.downsample_method.setCurrentText(self.settings['downsample_method'])
        self.enable_smoothing.setChecked(self.settings['enable_smoothing'])
        self.smoothing_window.setValue(self.settings['smoothing_window'])
        self.smoothing_type.setCurrentText(self.settings['smoothing_type'])
        self.remove_outliers.setChecked(self.settings['remove_outliers'])
        self.outlier_threshold.setValue(self.settings['outlier_threshold'])
        
        # RISE
        self.rise_threshold.setValue(self.settings['rise_threshold'])
        self.window_type.setCurrentText(self.settings['window_type'])
        self.min_time_between_events.setValue(self.settings['min_time_between_events'])
        self.max_rise_rate.setValue(self.settings['max_rise_rate'])
        
        # MRC
        self.min_recession_length.setValue(self.settings['min_recession_length'])
        self.fluctuation_tolerance.setValue(self.settings['fluctuation_tolerance'])
        self.mrc_deviation_threshold.setValue(self.settings['mrc_deviation_threshold'])
        self.use_precipitation.setChecked(self.settings['use_precipitation'])
        self.precip_threshold.setValue(self.settings['precip_threshold'])
        self.precip_lag.setValue(self.settings['precip_lag'])
        
        # EMR
        self.curve_type.setCurrentText(self.settings['curve_type'])
        self.r_squared_threshold.setValue(self.settings['r_squared_threshold'])
        self.validation_split.setValue(self.settings['validation_split'])
        self.enable_seasonal.setChecked(self.settings['enable_seasonal'])
        self.seasonal_periods.setCurrentText(self.settings['seasonal_periods'])
        self.emr_deviation_threshold.setValue(self.settings['emr_deviation_threshold'])
        
    def save_settings(self):
        """Save settings from UI controls."""
        # Get current value from UI control
        ui_min_recession = self.min_recession_length.value()
        logger.info(f"[SAVE_SETTINGS_DEBUG] UI control min_recession_length value: {ui_min_recession}")
        
        old_min_recession = self.settings.get('min_recession_length', 'NOT_SET')
        logger.info(f"[SAVE_SETTINGS_DEBUG] Previous settings min_recession_length: {old_min_recession}")
        
        self.settings.update({
            # Common
            'specific_yield': self.specific_yield.value(),
            'water_year_month': self.water_year_month.value(),
            'water_year_day': self.water_year_day.value(),
            'confidence_level': self.confidence_level.currentText(),
            'units': self.units.currentText(),
            
            # Preprocessing
            'downsample_frequency': self.downsample_frequency.currentText(),
            'downsample_method': self.downsample_method.currentText(),
            'enable_smoothing': self.enable_smoothing.isChecked(),
            'smoothing_window': self.smoothing_window.value(),
            'smoothing_type': self.smoothing_type.currentText(),
            'remove_outliers': self.remove_outliers.isChecked(),
            'outlier_threshold': self.outlier_threshold.value(),
            
            # RISE
            'rise_threshold': self.rise_threshold.value(),
            'window_type': self.window_type.currentText(),
            'min_time_between_events': self.min_time_between_events.value(),
            'max_rise_rate': self.max_rise_rate.value(),
            
            # MRC
            'min_recession_length': self.min_recession_length.value(),
            'fluctuation_tolerance': self.fluctuation_tolerance.value(),
            'mrc_deviation_threshold': self.mrc_deviation_threshold.value(),
            'use_precipitation': self.use_precipitation.isChecked(),
            'precip_threshold': self.precip_threshold.value(),
            'precip_lag': self.precip_lag.value(),
            
            # EMR
            'curve_type': self.curve_type.currentText(),
            'r_squared_threshold': self.r_squared_threshold.value(),
            'validation_split': self.validation_split.value(),
            'enable_seasonal': self.enable_seasonal.isChecked(),
            'seasonal_periods': self.seasonal_periods.currentText(),
            'emr_deviation_threshold': self.emr_deviation_threshold.value()
        })
        
        new_min_recession = self.settings.get('min_recession_length', 'NOT_SET')
        logger.info(f"[SAVE_SETTINGS_DEBUG] New settings min_recession_length: {new_min_recession}")
        logger.info(f"[SAVE_SETTINGS_DEBUG] Settings updated successfully")
        
    def accept_settings(self):
        """Accept and apply settings."""
        self.save_settings()
        self.settings_changed.emit(self.settings)
        self.accept()
        
    def restore_defaults(self):
        """Restore default settings."""
        self.settings = self.get_default_settings()
        self.load_settings()
        
    def get_method_settings(self, method):
        """Get settings specific to a method."""
        common_keys = [
            'specific_yield', 'water_year_month', 'water_year_day',
            'confidence_level', 'units', 'downsample_frequency',
            'downsample_method', 'enable_smoothing', 'smoothing_window',
            'smoothing_type', 'remove_outliers', 'outlier_threshold'
        ]
        
        method_keys = {
            'RISE': ['rise_threshold', 'window_type', 'min_time_between_events', 'max_rise_rate'],
            'MRC': ['min_recession_length', 'fluctuation_tolerance', 'mrc_deviation_threshold',
                    'use_precipitation', 'precip_threshold', 'precip_lag'],
            'EMR': ['curve_type', 'r_squared_threshold', 'validation_split', 
                    'enable_seasonal', 'seasonal_periods', 'emr_deviation_threshold']
        }
        
        settings = {key: self.settings[key] for key in common_keys}
        if method in method_keys:
            settings.update({key: self.settings[key] for key in method_keys[method]})
            
        return settings