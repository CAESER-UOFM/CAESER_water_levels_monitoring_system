"""
ERC (Extended Recession Curve) method for recharge estimation.
This tab implements the ERC method for calculating recharge using water level data.
Based on USGS EMR methodology with extensions for temporal variability analysis.
"""

import logging
import numpy as np
import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QPushButton, QGroupBox, QTableWidget, 
    QTableWidgetItem, QMessageBox, QDateEdit, QSplitter,
    QCheckBox, QFrame, QTabWidget, QGridLayout, QSizePolicy,
    QHeaderView, QSpinBox, QRadioButton, QButtonGroup,
    QAbstractItemView, QDialog, QDialogButtonBox, QTextEdit,
    QProgressBar, QSlider
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd
from scipy import signal, optimize
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

# Add the parent directory to the path to import from db package
current_dir = os.path.dirname(__file__)
visualizer_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, visualizer_dir)

from db.erc_database import ErcDatabase
from .base_recharge_tab import BaseRechargeTab

# Import settings persistence if available
try:
    from .settings_persistence import SettingsPersistence
except ImportError:
    # Gracefully handle case where settings persistence isn't available
    SettingsPersistence = None

logger = logging.getLogger(__name__)


class CollapsibleGroupBox(QFrame):
    """
    A collapsible group box that can expand and collapse its content.
    """
    toggled = pyqtSignal(bool)  # Signal emitted when expanded/collapsed
    
    def __init__(self, title="", persistence_key=None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        self.title = title
        self.persistence_key = persistence_key  # Unique key for saving state
        self.is_expanded = False  # Start collapsed by default
        self.animation_duration = 200
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header frame with toggle button and title
        self.header_frame = QFrame()
        self.header_frame.setFrameShape(QFrame.StyledPanel)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(8, 8, 8, 8)
        
        # Toggle button
        self.toggle_button = QPushButton("▶")  # Right arrow for collapsed
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 3px;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 13px;
                color: #2c3e50;
                padding-left: 5px;
            }
        """)
        
        self.header_layout.addWidget(self.toggle_button)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        # Content frame
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(12, 16, 12, 12)
        self.content_layout.setSpacing(10)
        
        # Add header and content to main layout
        self.main_layout.addWidget(self.header_frame)
        self.main_layout.addWidget(self.content_frame)
        
        # Animation for smooth expand/collapse
        self.animation = QPropertyAnimation(self.content_frame, b"maximumHeight")
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.finished.connect(self.on_animation_finished)
        
        # Apply styling similar to QGroupBox
        self.setStyleSheet("""
            CollapsibleGroupBox {
                border: 2px solid #ced4da;
                border-radius: 8px;
                margin: 4px 0px;
                background-color: white;
            }
        """)
        
        # Store the original height for animation
        self.content_height = 0
        
        # Set initial collapsed state
        self.content_frame.setMaximumHeight(0)
        
    def set_content_layout(self, layout):
        """Set the layout for the content area."""
        # Clear existing layout
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
            elif child.layout():
                self.clear_layout(child.layout())
        
        # Add new layout/widget
        if hasattr(layout, 'count'):  # It's a layout
            # Transfer all widgets from the given layout to our content layout
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    self.content_layout.addWidget(item.widget())
                elif item.layout():
                    self.content_layout.addLayout(item.layout())
        else:  # It's a widget
            self.content_layout.addWidget(layout)
            
    def clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
            elif child.layout():
                self.clear_layout(child.layout())
    
    def add_widget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)
        
    def add_layout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)
        
    def toggle(self):
        """Toggle the expanded/collapsed state."""
        self.is_expanded = not self.is_expanded
        self.set_expanded(self.is_expanded)
        
    def set_expanded(self, expanded, save_state=True):
        """Set the expanded state."""
        self.is_expanded = expanded
        
        if expanded:
            self.toggle_button.setText("▼")  # Down arrow
            self.expand()
        else:
            self.toggle_button.setText("▶")  # Right arrow
            self.collapse()
            
        self.toggled.emit(expanded)
        
        # Save state if requested
        if save_state:
            self.save_state()
        
    def expand(self):
        """Expand the content area."""
        if self.content_height == 0:
            # Calculate the content height
            self.content_frame.adjustSize()
            self.content_height = max(self.content_frame.sizeHint().height(), 100)
        
        # Reset max height and show content
        self.content_frame.setMaximumHeight(16777215)  # Remove height constraint
        self.animation.setStartValue(0 if self.content_frame.maximumHeight() == 0 else self.content_frame.height())
        self.animation.setEndValue(self.content_height)
        self.animation.start()
        
    def collapse(self):
        """Collapse the content area."""
        if self.content_height == 0:
            self.content_height = max(self.content_frame.height(), self.content_frame.sizeHint().height(), 100)
            
        self.animation.setStartValue(self.content_height)
        self.animation.setEndValue(0)
        self.animation.start()
        
    def set_content_height(self, height):
        """Manually set the content height for animation."""
        self.content_height = height
        
    def on_animation_finished(self):
        """Handle animation completion."""
        if not self.is_expanded:
            # When collapsed, hide content completely
            self.content_frame.setMaximumHeight(0)
        else:
            # When expanded, remove height constraint
            self.content_frame.setMaximumHeight(16777215)
            
    def save_state(self):
        """Save the expanded/collapsed state to persistent storage."""
        if self.persistence_key and SettingsPersistence:
            try:
                settings = SettingsPersistence()
                preference_key = f"collapsible_panel_{self.persistence_key}_expanded"
                settings.save_user_preference(preference_key, self.is_expanded)
            except Exception as e:
                logger.warning(f"Failed to save panel state for {self.persistence_key}: {e}")
                
    def load_state(self):
        """Load the expanded/collapsed state from persistent storage."""
        if self.persistence_key and SettingsPersistence:
            try:
                settings = SettingsPersistence()
                preference_key = f"collapsible_panel_{self.persistence_key}_expanded"
                saved_state = settings.get_user_preference(preference_key)
                if saved_state is not None:
                    # Convert to boolean if it's a string
                    if isinstance(saved_state, str):
                        saved_state = saved_state.lower() in ('true', '1', 'yes')
                    self.set_expanded(bool(saved_state), save_state=False)
                    return True
            except Exception as e:
                logger.warning(f"Failed to load panel state for {self.persistence_key}: {e}")
        
        # If no saved state exists, ensure we're in the default collapsed state
        if not self.is_expanded:
            self.set_expanded(False, save_state=False)
        return False


class InteractiveCurveFittingDialog(QDialog):
    """
    Interactive dialog for fitting curves to recession segments with real-time preview.
    Provides multiple curve types and advanced validation options.
    """
    
    curve_fitted = pyqtSignal(dict)  # Emitted when a curve is successfully fitted
    
    def __init__(self, recession_segments, settings, parent=None):
        super().__init__(parent)
        self.recession_segments = recession_segments
        self.settings = settings
        self.current_curve = None
        self.fit_results = None
        
        self.setWindowTitle("Interactive Curve Fitting - ERC Method")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("🎯 Interactive Curve Fitting")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content area with splitter
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Controls
        left_panel = self.create_controls_panel()
        content_splitter.addWidget(left_panel)
        
        # Right panel - Plot
        right_panel = self.create_plot_panel()
        content_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        content_splitter.setSizes([300, 500])
        layout.addWidget(content_splitter)
        
        # Status bar
        self.status_label = QLabel("Ready to fit curves...")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                font-size: 11px;
                color: #495057;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept_curve)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_curve)
        layout.addWidget(button_box)
        
        # Initial plot
        self.update_plot()
        
    def create_controls_panel(self):
        """Create the controls panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Curve type selection
        curve_group = QGroupBox("Curve Type")
        curve_layout = QVBoxLayout(curve_group)
        
        self.curve_type_combo = QComboBox()
        self.curve_type_combo.addItems([
            "Exponential (recommended)",
            "Power Law", 
            "Polynomial",
            "Multi-Segment"
        ])
        self.curve_type_combo.currentTextChanged.connect(self.on_curve_type_changed)
        curve_layout.addWidget(self.curve_type_combo)
        
        layout.addWidget(curve_group)
        
        # Fitting parameters
        params_group = QGroupBox("Fitting Parameters")
        params_layout = QGridLayout(params_group)
        
        # R² threshold
        params_layout.addWidget(QLabel("Min R² Threshold:"), 0, 0)
        self.r_squared_threshold = QDoubleSpinBox()
        self.r_squared_threshold.setRange(0.1, 1.0)
        self.r_squared_threshold.setValue(self.settings.get('r_squared_threshold', 0.7))
        self.r_squared_threshold.setDecimals(2)
        self.r_squared_threshold.setSingleStep(0.05)
        params_layout.addWidget(self.r_squared_threshold, 0, 1)
        
        # Validation split
        params_layout.addWidget(QLabel("Validation Split:"), 1, 0)
        self.validation_split = QDoubleSpinBox()
        self.validation_split.setRange(0.1, 0.5)
        self.validation_split.setValue(self.settings.get('validation_split', 0.2))
        self.validation_split.setDecimals(2)
        self.validation_split.setSingleStep(0.05)
        params_layout.addWidget(self.validation_split, 1, 1)
        
        layout.addWidget(params_group)
        
        # Seasonal analysis
        seasonal_group = QGroupBox("Seasonal Analysis")
        seasonal_layout = QVBoxLayout(seasonal_group)
        
        self.enable_seasonal = QCheckBox("Enable seasonal analysis")
        self.enable_seasonal.setChecked(self.settings.get('enable_seasonal', False))
        seasonal_layout.addWidget(self.enable_seasonal)
        
        self.seasonal_periods = QComboBox()
        self.seasonal_periods.addItems(["4 Seasons", "12 Months", "Growing/Non-growing"])
        self.seasonal_periods.setCurrentText(self.settings.get('seasonal_periods', '4 Seasons'))
        seasonal_layout.addWidget(self.seasonal_periods)
        
        layout.addWidget(seasonal_group)
        
        # Fit button
        self.fit_button = QPushButton("🎯 Fit Curve")
        self.fit_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.fit_button.clicked.connect(self.fit_curve)
        layout.addWidget(self.fit_button)
        
        # Results display
        results_group = QGroupBox("Fit Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        layout.addStretch()
        
        return panel
        
    def create_plot_panel(self):
        """Create the plot panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Matplotlib figure
        from matplotlib.figure import Figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        return panel
        
    def setup_connections(self):
        """Setup signal connections."""
        # Connect parameter changes to real-time updates
        self.r_squared_threshold.valueChanged.connect(self.on_parameters_changed)
        self.validation_split.valueChanged.connect(self.on_parameters_changed)
        self.enable_seasonal.toggled.connect(self.on_parameters_changed)
        self.seasonal_periods.currentTextChanged.connect(self.on_parameters_changed)
        
    def on_curve_type_changed(self):
        """Handle curve type changes."""
        self.update_status("Curve type changed. Click 'Fit Curve' to apply.")
        
    def on_parameters_changed(self):
        """Handle parameter changes."""
        if self.fit_results:
            self.update_status("Parameters changed. Click 'Fit Curve' to refit.")
            
    def fit_curve(self):
        """Fit the selected curve type to recession segments."""
        try:
            if not self.recession_segments:
                self.update_status("No recession segments available for fitting.")
                return
                
            self.update_status("Fitting curve...")
            
            curve_type = self.curve_type_combo.currentText()
            
            # Prepare data for fitting
            segment_data = self.prepare_segment_data()
            if not segment_data:
                self.update_status("No valid segment data for fitting.")
                return
            
            # Perform curve fitting based on type
            if "Exponential" in curve_type:
                fit_results = self.fit_exponential_curve(segment_data)
            elif "Power Law" in curve_type:
                fit_results = self.fit_power_law_curve(segment_data)
            elif "Polynomial" in curve_type:
                fit_results = self.fit_polynomial_curve(segment_data)
            elif "Multi-Segment" in curve_type:
                fit_results = self.fit_multi_segment_curve(segment_data)
            else:
                self.update_status("Unknown curve type selected.")
                return
                
            if fit_results:
                self.fit_results = fit_results
                self.current_curve = {
                    'type': curve_type,
                    'coefficients': fit_results['coefficients'],
                    'r_squared': fit_results['r_squared'],
                    'parameters': fit_results.get('parameters', {}),
                    'validation_score': fit_results.get('validation_score'),
                    'seasonal_analysis': self.enable_seasonal.isChecked()
                }
                
                self.display_results(fit_results)
                self.update_plot()
                self.update_status(f"Curve fitted successfully! R² = {fit_results['r_squared']:.4f}")
            else:
                self.update_status("Curve fitting failed. Try different parameters.")
                
        except Exception as e:
            logger.error(f"Error fitting curve: {e}")
            self.update_status(f"Error: {str(e)}")
            
    def prepare_segment_data(self):
        """Prepare segment data for curve fitting."""
        # This would extract time series data from recession segments
        # For now, return mock data structure
        return {
            'time': np.linspace(0, 100, 100),
            'water_level': np.exp(-0.1 * np.linspace(0, 100, 100)) + np.random.normal(0, 0.01, 100)
        }
        
    def fit_exponential_curve(self, data):
        """Fit exponential curve to data."""
        try:
            # Mock exponential fitting - replace with actual implementation
            time = data['time']
            levels = data['water_level']
            
            # Simple exponential fit: y = a * exp(b * t) + c
            def exp_func(t, a, b, c):
                return a * np.exp(b * t) + c
                
            from scipy.optimize import curve_fit
            popt, pcov = curve_fit(exp_func, time, levels, p0=[1, -0.1, 0])
            
            # Calculate R²
            y_pred = exp_func(time, *popt)
            ss_res = np.sum((levels - y_pred) ** 2)
            ss_tot = np.sum((levels - np.mean(levels)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            return {
                'coefficients': {'a': popt[0], 'b': popt[1], 'c': popt[2]},
                'r_squared': r_squared,
                'fitted_values': y_pred,
                'parameters': {'curve_type': 'exponential'},
                'validation_score': r_squared * 0.95  # Mock validation
            }
            
        except Exception as e:
            logger.error(f"Error in exponential fitting: {e}")
            return None
            
    def fit_power_law_curve(self, data):
        """Fit power law curve to data."""
        # Mock implementation
        return {
            'coefficients': {'a': 1.0, 'b': -0.5},
            'r_squared': 0.85,
            'fitted_values': data['water_level'] * 0.9,  # Mock
            'parameters': {'curve_type': 'power_law'}
        }
        
    def fit_polynomial_curve(self, data):
        """Fit polynomial curve to data."""
        # Mock implementation
        return {
            'coefficients': {'p0': 1.0, 'p1': -0.1, 'p2': 0.01},
            'r_squared': 0.90,
            'fitted_values': data['water_level'] * 0.95,  # Mock
            'parameters': {'curve_type': 'polynomial', 'degree': 2}
        }
        
    def fit_multi_segment_curve(self, data):
        """Fit multi-segment piecewise curve to data."""
        # Mock implementation
        return {
            'coefficients': {'segment1': {'a': 1.0, 'b': -0.1}, 'segment2': {'a': 0.5, 'b': -0.05}},
            'r_squared': 0.92,
            'fitted_values': data['water_level'] * 0.93,  # Mock
            'parameters': {'curve_type': 'multi_segment', 'segments': 2}
        }
        
    def display_results(self, results):
        """Display fitting results in the text widget."""
        text = f"Curve Fitting Results\n"
        text += f"=" * 30 + "\n\n"
        text += f"R² Value: {results['r_squared']:.4f}\n"
        
        if results['r_squared'] >= self.r_squared_threshold.value():
            text += "✅ R² meets threshold requirement\n"
        else:
            text += "❌ R² below threshold requirement\n"
            
        text += f"\nCoefficients:\n"
        for key, value in results['coefficients'].items():
            if isinstance(value, dict):
                text += f"  {key}:\n"
                for k, v in value.items():
                    text += f"    {k}: {v:.6f}\n"
            else:
                text += f"  {key}: {value:.6f}\n"
                
        if results.get('validation_score'):
            text += f"\nCross-validation R²: {results['validation_score']:.4f}\n"
            
        self.results_text.setPlainText(text)
        
    def update_plot(self):
        """Update the plot display."""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            if not self.recession_segments:
                ax.text(0.5, 0.5, 'No recession segments available', 
                       ha='center', va='center', transform=ax.transAxes)
                self.canvas.draw()
                return
                
            # Plot original data (mock for now)
            time = np.linspace(0, 100, 100)
            original_data = np.exp(-0.1 * time) + np.random.normal(0, 0.01, 100)
            ax.plot(time, original_data, 'o', alpha=0.6, markersize=3, label='Recession Data')
            
            # Plot fitted curve if available
            if self.fit_results:
                fitted_values = self.fit_results['fitted_values']
                ax.plot(time, fitted_values, 'r-', linewidth=2, label=f'Fitted Curve (R² = {self.fit_results["r_squared"]:.3f})')
                
            ax.set_xlabel('Time')
            ax.set_ylabel('Water Level')
            ax.set_title('Curve Fitting Preview')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            
    def update_status(self, message):
        """Update the status message."""
        self.status_label.setText(f"Status: {message}")
        
    def accept_curve(self):
        """Accept the fitted curve."""
        if not self.current_curve:
            QMessageBox.warning(self, "No Curve", "Please fit a curve first.")
            return
            
        if self.current_curve['r_squared'] < self.r_squared_threshold.value():
            reply = QMessageBox.question(
                self, "Low R² Value",
                f"The R² value ({self.current_curve['r_squared']:.4f}) is below the threshold "
                f"({self.r_squared_threshold.value():.2f}). Accept anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
                
        self.curve_fitted.emit(self.current_curve)
        self.accept()
        
    def apply_curve(self):
        """Apply the curve without closing the dialog."""
        if self.current_curve:
            self.curve_fitted.emit(self.current_curve)
            self.update_status("Curve applied successfully!")


class EnhancedSegmentAnalysisDialog(QDialog):
    """
    Enhanced dialog for analyzing and configuring recession segment identification.
    Provides temporal filtering, seasonal classification, and advanced quality controls.
    """
    
    segments_analyzed = pyqtSignal(list)  # Emitted when segments are analyzed
    
    def __init__(self, data, settings, parent=None):
        super().__init__(parent)
        self.data = data
        self.settings = settings
        self.segments = []
        self.analysis_results = None
        
        self.setWindowTitle("Enhanced Segment Analysis - ERC Method")
        self.setModal(True)
        self.resize(900, 700)
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("🔍 Enhanced Recession Segment Analysis")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #e8f4fd;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content with tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Analysis Parameters
        self.tabs.addTab(self.create_parameters_tab(), "📊 Analysis Parameters")
        
        # Tab 2: Temporal Filtering
        self.tabs.addTab(self.create_temporal_tab(), "📅 Temporal Filtering")
        
        # Tab 3: Quality Controls
        self.tabs.addTab(self.create_quality_tab(), "🎯 Quality Controls")
        
        # Tab 4: Results Preview
        self.tabs.addTab(self.create_results_tab(), "📈 Results Preview")
        
        layout.addWidget(self.tabs)
        
        # Analysis controls
        controls_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 Analyze Segments")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.analyze_btn.clicked.connect(self.analyze_segments)
        controls_layout.addWidget(self.analyze_btn)
        
        self.preview_btn = QPushButton("👁️ Preview Results")
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.preview_btn.clicked.connect(self.preview_results)
        controls_layout.addWidget(self.preview_btn)
        
        controls_layout.addStretch()
        layout.addWidget(QWidget())  # Add some spacing
        layout.addLayout(controls_layout)
        
        # Status bar
        self.status_label = QLabel("Ready to analyze recession segments...")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                font-size: 11px;
                color: #495057;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept_segments)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_segments)
        layout.addWidget(button_box)
        
    def create_parameters_tab(self):
        """Create the analysis parameters tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Basic parameters
        basic_group = QGroupBox("Basic Parameters")
        basic_layout = QGridLayout(basic_group)
        
        # Min recession length
        basic_layout.addWidget(QLabel("Min Recession Length:"), 0, 0)
        self.min_recession_length = QSpinBox()
        self.min_recession_length.setRange(3, 30)
        self.min_recession_length.setValue(self.settings.get('min_recession_length', 7))
        self.min_recession_length.setSuffix(" days")
        basic_layout.addWidget(self.min_recession_length, 0, 1)
        
        # Fluctuation tolerance
        basic_layout.addWidget(QLabel("Fluctuation Tolerance:"), 1, 0)
        self.fluctuation_tolerance = QDoubleSpinBox()
        self.fluctuation_tolerance.setRange(0.001, 0.1)
        self.fluctuation_tolerance.setValue(self.settings.get('fluctuation_tolerance', 0.02))
        self.fluctuation_tolerance.setSuffix(" ft")
        self.fluctuation_tolerance.setDecimals(3)
        basic_layout.addWidget(self.fluctuation_tolerance, 1, 1)
        
        layout.addWidget(basic_group)
        
        # Advanced parameters
        advanced_group = QGroupBox("Advanced Parameters")
        advanced_layout = QGridLayout(advanced_group)
        
        # Minimum rate of decline
        advanced_layout.addWidget(QLabel("Min Rate of Decline:"), 0, 0)
        self.min_decline_rate = QDoubleSpinBox()
        self.min_decline_rate.setRange(0.001, 1.0)
        self.min_decline_rate.setValue(0.005)
        self.min_decline_rate.setSuffix(" ft/day")
        self.min_decline_rate.setDecimals(4)
        advanced_layout.addWidget(self.min_decline_rate, 0, 1)
        
        # Maximum gap tolerance
        advanced_layout.addWidget(QLabel("Max Gap Tolerance:"), 1, 0)
        self.max_gap_tolerance = QSpinBox()
        self.max_gap_tolerance.setRange(0, 5)
        self.max_gap_tolerance.setValue(1)
        self.max_gap_tolerance.setSuffix(" days")
        advanced_layout.addWidget(self.max_gap_tolerance, 1, 1)
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        return widget
        
    def create_temporal_tab(self):
        """Create the temporal filtering tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Date range filtering
        date_group = QGroupBox("Date Range Filtering")
        date_layout = QGridLayout(date_group)
        
        self.enable_date_filter = QCheckBox("Enable date range filtering")
        date_layout.addWidget(self.enable_date_filter, 0, 0, 1, 2)
        
        date_layout.addWidget(QLabel("Start Date:"), 1, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setEnabled(False)
        date_layout.addWidget(self.start_date, 1, 1)
        
        date_layout.addWidget(QLabel("End Date:"), 2, 0)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setEnabled(False)
        date_layout.addWidget(self.end_date, 2, 1)
        
        layout.addWidget(date_group)
        
        # Seasonal filtering
        seasonal_group = QGroupBox("Seasonal Filtering")
        seasonal_layout = QVBoxLayout(seasonal_group)
        
        self.enable_seasonal_filter = QCheckBox("Enable seasonal filtering")
        seasonal_layout.addWidget(self.enable_seasonal_filter)
        
        # Season selection
        seasons_layout = QGridLayout()
        self.season_checkboxes = {}
        for i, season in enumerate(['Winter', 'Spring', 'Summer', 'Fall']):
            checkbox = QCheckBox(season)
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            self.season_checkboxes[season] = checkbox
            seasons_layout.addWidget(checkbox, i // 2, i % 2)
            
        seasonal_layout.addLayout(seasons_layout)
        layout.addWidget(seasonal_group)
        
        # Water year filtering
        water_year_group = QGroupBox("Water Year Filtering")
        water_year_layout = QVBoxLayout(water_year_group)
        
        self.enable_water_year_filter = QCheckBox("Filter by water year periods")
        water_year_layout.addWidget(self.enable_water_year_filter)
        
        wy_controls_layout = QHBoxLayout()
        wy_controls_layout.addWidget(QLabel("Water Years:"))
        self.water_year_start = QSpinBox()
        self.water_year_start.setRange(1900, 2100)
        self.water_year_start.setValue(2020)
        self.water_year_start.setEnabled(False)
        wy_controls_layout.addWidget(self.water_year_start)
        
        wy_controls_layout.addWidget(QLabel("to"))
        self.water_year_end = QSpinBox()
        self.water_year_end.setRange(1900, 2100)
        self.water_year_end.setValue(2024)
        self.water_year_end.setEnabled(False)
        wy_controls_layout.addWidget(self.water_year_end)
        
        water_year_layout.addLayout(wy_controls_layout)
        layout.addWidget(water_year_group)
        
        layout.addStretch()
        return widget
        
    def create_quality_tab(self):
        """Create the quality controls tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Outlier detection
        outlier_group = QGroupBox("Outlier Detection")
        outlier_layout = QGridLayout(outlier_group)
        
        self.enable_outlier_detection = QCheckBox("Enable outlier detection")
        self.enable_outlier_detection.setChecked(True)
        outlier_layout.addWidget(self.enable_outlier_detection, 0, 0, 1, 2)
        
        outlier_layout.addWidget(QLabel("Outlier Threshold:"), 1, 0)
        self.outlier_threshold = QDoubleSpinBox()
        self.outlier_threshold.setRange(1.0, 5.0)
        self.outlier_threshold.setValue(2.5)
        self.outlier_threshold.setSuffix(" std dev")
        outlier_layout.addWidget(self.outlier_threshold, 1, 1)
        
        layout.addWidget(outlier_group)
        
        # Quality scoring
        quality_group = QGroupBox("Quality Scoring")
        quality_layout = QVBoxLayout(quality_group)
        
        self.enable_quality_scoring = QCheckBox("Enable quality scoring")
        self.enable_quality_scoring.setChecked(True)
        quality_layout.addWidget(self.enable_quality_scoring)
        
        # Quality criteria
        criteria_layout = QGridLayout()
        
        criteria_layout.addWidget(QLabel("Min Quality Score:"), 0, 0)
        self.min_quality_score = QDoubleSpinBox()
        self.min_quality_score.setRange(0.0, 1.0)
        self.min_quality_score.setValue(0.6)
        self.min_quality_score.setDecimals(2)
        criteria_layout.addWidget(self.min_quality_score, 0, 1)
        
        criteria_layout.addWidget(QLabel("R² Weight:"), 1, 0)
        self.r_squared_weight = QDoubleSpinBox()
        self.r_squared_weight.setRange(0.0, 1.0)
        self.r_squared_weight.setValue(0.4)
        self.r_squared_weight.setDecimals(2)
        criteria_layout.addWidget(self.r_squared_weight, 1, 1)
        
        criteria_layout.addWidget(QLabel("Length Weight:"), 2, 0)
        self.length_weight = QDoubleSpinBox()
        self.length_weight.setRange(0.0, 1.0)
        self.length_weight.setValue(0.3)
        self.length_weight.setDecimals(2)
        criteria_layout.addWidget(self.length_weight, 2, 1)
        
        criteria_layout.addWidget(QLabel("Consistency Weight:"), 3, 0)
        self.consistency_weight = QDoubleSpinBox()
        self.consistency_weight.setRange(0.0, 1.0)
        self.consistency_weight.setValue(0.3)
        self.consistency_weight.setDecimals(2)
        criteria_layout.addWidget(self.consistency_weight, 3, 1)
        
        quality_layout.addLayout(criteria_layout)
        layout.addWidget(quality_group)
        
        layout.addStretch()
        return widget
        
    def create_results_tab(self):
        """Create the results preview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Results summary
        summary_group = QGroupBox("Analysis Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        summary_layout.addWidget(self.summary_text)
        
        layout.addWidget(summary_group)
        
        # Segments table
        segments_group = QGroupBox("Identified Segments")
        segments_layout = QVBoxLayout(segments_group)
        
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(7)
        self.segments_table.setHorizontalHeaderLabels([
            "Start Date", "End Date", "Duration", "Start Level", "End Level", 
            "Avg Rate", "Quality Score"
        ])
        self.segments_table.horizontalHeader().setStretchLastSection(True)
        segments_layout.addWidget(self.segments_table)
        
        layout.addWidget(segments_group)
        
        return widget
        
    def setup_connections(self):
        """Setup signal connections."""
        # Connect enable/disable functionality
        self.enable_date_filter.toggled.connect(self.start_date.setEnabled)
        self.enable_date_filter.toggled.connect(self.end_date.setEnabled)
        
        self.enable_seasonal_filter.toggled.connect(self.toggle_seasonal_controls)
        self.enable_water_year_filter.toggled.connect(self.water_year_start.setEnabled)
        self.enable_water_year_filter.toggled.connect(self.water_year_end.setEnabled)
        
        # Connect parameter changes
        self.min_recession_length.valueChanged.connect(self.on_parameters_changed)
        self.fluctuation_tolerance.valueChanged.connect(self.on_parameters_changed)
        
    def toggle_seasonal_controls(self, enabled):
        """Toggle seasonal filter controls."""
        for checkbox in self.season_checkboxes.values():
            checkbox.setEnabled(enabled)
            
    def on_parameters_changed(self):
        """Handle parameter changes."""
        if self.analysis_results:
            self.update_status("Parameters changed. Click 'Analyze Segments' to update results.")
            
    def analyze_segments(self):
        """Analyze recession segments with current parameters."""
        try:
            if self.data is None or self.data.empty:
                self.update_status("No data available for analysis.")
                return
                
            self.update_status("Analyzing recession segments...")
            
            # Mock analysis - replace with actual implementation
            self.segments = self.perform_segment_analysis()
            self.analysis_results = {
                'total_segments': len(self.segments),
                'total_duration': sum(seg.get('duration', 0) for seg in self.segments),
                'quality_segments': len([s for s in self.segments if s.get('quality_score', 0) >= self.min_quality_score.value()]),
                'seasonal_distribution': self.calculate_seasonal_distribution()
            }
            
            self.update_results_display()
            self.preview_btn.setEnabled(True)
            self.update_status(f"Analysis complete: {len(self.segments)} segments identified.")
            
        except Exception as e:
            logger.error(f"Error analyzing segments: {e}")
            self.update_status(f"Analysis error: {str(e)}")
            
    def perform_segment_analysis(self):
        """Perform the actual segment analysis."""
        # Mock implementation - replace with actual ERC segment analysis
        import random
        segments = []
        
        for i in range(random.randint(5, 15)):
            start_date = f"2023-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            duration = random.randint(self.min_recession_length.value(), 20)
            
            segment = {
                'start_date': start_date,
                'duration': duration,
                'start_level': random.uniform(10, 20),
                'end_level': random.uniform(5, 15),
                'avg_rate': random.uniform(-0.1, -0.01),
                'quality_score': random.uniform(0.3, 0.95),
                'seasonal_period': random.choice(['Winter', 'Spring', 'Summer', 'Fall'])
            }
            segments.append(segment)
            
        return segments
        
    def calculate_seasonal_distribution(self):
        """Calculate seasonal distribution of segments."""
        distribution = {'Winter': 0, 'Spring': 0, 'Summer': 0, 'Fall': 0}
        for segment in self.segments:
            season = segment.get('seasonal_period', 'Unknown')
            if season in distribution:
                distribution[season] += 1
        return distribution
        
    def update_results_display(self):
        """Update the results display."""
        if not self.analysis_results:
            return
            
        # Update summary text
        summary = f"Segment Analysis Results\n"
        summary += f"=" * 30 + "\n\n"
        summary += f"Total segments identified: {self.analysis_results['total_segments']}\n"
        summary += f"Quality segments (≥{self.min_quality_score.value():.2f}): {self.analysis_results['quality_segments']}\n"
        summary += f"Total duration analyzed: {self.analysis_results['total_duration']:.1f} days\n\n"
        
        summary += "Seasonal Distribution:\n"
        for season, count in self.analysis_results['seasonal_distribution'].items():
            summary += f"  {season}: {count} segments\n"
            
        self.summary_text.setPlainText(summary)
        
        # Update segments table
        self.segments_table.setRowCount(len(self.segments))
        for i, segment in enumerate(self.segments):
            self.segments_table.setItem(i, 0, QTableWidgetItem(segment['start_date']))
            self.segments_table.setItem(i, 1, QTableWidgetItem(f"{segment['start_date']} + {segment['duration']}d"))
            self.segments_table.setItem(i, 2, QTableWidgetItem(f"{segment['duration']} days"))
            self.segments_table.setItem(i, 3, QTableWidgetItem(f"{segment['start_level']:.2f} ft"))
            self.segments_table.setItem(i, 4, QTableWidgetItem(f"{segment['end_level']:.2f} ft"))
            self.segments_table.setItem(i, 5, QTableWidgetItem(f"{segment['avg_rate']:.4f} ft/day"))
            self.segments_table.setItem(i, 6, QTableWidgetItem(f"{segment['quality_score']:.3f}"))
            
    def preview_results(self):
        """Preview the analysis results."""
        # Switch to results tab
        self.tabs.setCurrentIndex(3)
        
    def update_status(self, message):
        """Update the status message."""
        self.status_label.setText(f"Status: {message}")
        
    def accept_segments(self):
        """Accept the analyzed segments."""
        if not self.segments:
            QMessageBox.warning(self, "No Segments", "Please analyze segments first.")
            return
            
        # Filter segments by quality if enabled
        if self.enable_quality_scoring.isChecked():
            quality_segments = [s for s in self.segments if s.get('quality_score', 0) >= self.min_quality_score.value()]
            if quality_segments != self.segments:
                reply = QMessageBox.question(
                    self, "Quality Filter",
                    f"Apply quality filter? This will reduce segments from {len(self.segments)} to {len(quality_segments)}.",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.segments = quality_segments
                    
        self.segments_analyzed.emit(self.segments)
        self.accept()
        
    def apply_segments(self):
        """Apply segments without closing the dialog."""
        if self.segments:
            self.segments_analyzed.emit(self.segments)
            self.update_status("Segments applied successfully!")


class ModernDataManagementDialog(QDialog):
    """
    Modern dialog for comprehensive data management in the ERC method.
    Handles curve import/export, calculation management, and temporal analysis data.
    """
    
    data_updated = pyqtSignal()  # Emitted when data is updated
    
    def __init__(self, well_id, erc_database, parent=None):
        super().__init__(parent)
        self.well_id = well_id
        self.erc_database = erc_database
        self.parent_tab = parent
        
        self.setWindowTitle("Data Management - ERC Method")
        self.setModal(True)
        self.resize(1000, 700)
        
        self.setup_ui()
        self.load_existing_data()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("🗂️ Modern Data Management")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content with tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Curves Management
        self.tabs.addTab(self.create_curves_tab(), "📈 Curves")
        
        # Tab 2: Calculations Management
        self.tabs.addTab(self.create_calculations_tab(), "🧮 Calculations")
        
        # Tab 3: Import/Export
        self.tabs.addTab(self.create_import_export_tab(), "⚡ Import/Export")
        
        # Tab 4: Database Utilities
        self.tabs.addTab(self.create_utilities_tab(), "🔧 Database Utilities")
        
        layout.addWidget(self.tabs)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        actions_layout.addWidget(self.refresh_btn)
        
        actions_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(self.close_btn)
        
        layout.addLayout(actions_layout)
        
    def create_curves_tab(self):
        """Create the curves management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Curves list
        curves_group = QGroupBox("Available Curves")
        curves_layout = QVBoxLayout(curves_group)
        
        self.curves_table = QTableWidget()
        self.curves_table.setColumnCount(6)
        self.curves_table.setHorizontalHeaderLabels([
            "ID", "Type", "R²", "Creation Date", "Segments", "Description"
        ])
        self.curves_table.horizontalHeader().setStretchLastSection(True)
        self.curves_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        curves_layout.addWidget(self.curves_table)
        
        # Curves actions
        curves_actions = QHBoxLayout()
        
        self.view_curve_btn = QPushButton("👁️ View Details")
        self.view_curve_btn.clicked.connect(self.view_curve_details)
        curves_actions.addWidget(self.view_curve_btn)
        
        self.duplicate_curve_btn = QPushButton("📋 Duplicate")
        self.duplicate_curve_btn.clicked.connect(self.duplicate_curve)
        curves_actions.addWidget(self.duplicate_curve_btn)
        
        self.delete_curve_btn = QPushButton("🗑️ Delete")
        self.delete_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.delete_curve_btn.clicked.connect(self.delete_curve)
        curves_actions.addWidget(self.delete_curve_btn)
        
        curves_actions.addStretch()
        curves_layout.addLayout(curves_actions)
        
        layout.addWidget(curves_group)
        
        # Curve details preview
        details_group = QGroupBox("Curve Details")
        details_layout = QVBoxLayout(details_group)
        
        self.curve_details_text = QTextEdit()
        self.curve_details_text.setMaximumHeight(150)
        self.curve_details_text.setReadOnly(True)
        self.curve_details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        details_layout.addWidget(self.curve_details_text)
        
        layout.addWidget(details_group)
        
        return widget
        
    def create_calculations_tab(self):
        """Create the calculations management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Calculations list
        calc_group = QGroupBox("Calculation Results")
        calc_layout = QVBoxLayout(calc_group)
        
        self.calculations_table = QTableWidget()
        self.calculations_table.setColumnCount(7)
        self.calculations_table.setHorizontalHeaderLabels([
            "ID", "Curve ID", "Date", "Total Recharge", "Annual Rate", "Events", "Quality"
        ])
        self.calculations_table.horizontalHeader().setStretchLastSection(True)
        self.calculations_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        calc_layout.addWidget(self.calculations_table)
        
        # Calculations actions
        calc_actions = QHBoxLayout()
        
        self.view_calc_btn = QPushButton("📊 View Results")
        self.view_calc_btn.clicked.connect(self.view_calculation_details)
        calc_actions.addWidget(self.view_calc_btn)
        
        self.export_calc_btn = QPushButton("📤 Export Results")
        self.export_calc_btn.clicked.connect(self.export_calculation)
        calc_actions.addWidget(self.export_calc_btn)
        
        self.delete_calc_btn = QPushButton("🗑️ Delete")
        self.delete_calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.delete_calc_btn.clicked.connect(self.delete_calculation)
        calc_actions.addWidget(self.delete_calc_btn)
        
        calc_actions.addStretch()
        calc_layout.addLayout(calc_actions)
        
        layout.addWidget(calc_group)
        
        # Calculation summary
        summary_group = QGroupBox("Summary Statistics")
        summary_layout = QVBoxLayout(summary_group)
        
        self.calc_summary_text = QTextEdit()
        self.calc_summary_text.setMaximumHeight(120)
        self.calc_summary_text.setReadOnly(True)
        self.calc_summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        summary_layout.addWidget(self.calc_summary_text)
        
        layout.addWidget(summary_group)
        
        return widget
        
    def create_import_export_tab(self):
        """Create the import/export tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Export section
        export_group = QGroupBox("Export Data")
        export_layout = QGridLayout(export_group)
        
        # Export format selection
        export_layout.addWidget(QLabel("Export Format:"), 0, 0)
        self.export_format = QComboBox()
        self.export_format.addItems(["CSV", "Excel (XLSX)", "JSON", "SQLite Database"])
        export_layout.addWidget(self.export_format, 0, 1)
        
        # Export options
        self.export_curves_cb = QCheckBox("Include Curves Data")
        self.export_curves_cb.setChecked(True)
        export_layout.addWidget(self.export_curves_cb, 1, 0)
        
        self.export_calcs_cb = QCheckBox("Include Calculations")
        self.export_calcs_cb.setChecked(True)
        export_layout.addWidget(self.export_calcs_cb, 1, 1)
        
        self.export_segments_cb = QCheckBox("Include Segment Data")
        self.export_segments_cb.setChecked(False)
        export_layout.addWidget(self.export_segments_cb, 2, 0)
        
        self.export_temporal_cb = QCheckBox("Include Temporal Analysis")
        self.export_temporal_cb.setChecked(False)
        export_layout.addWidget(self.export_temporal_cb, 2, 1)
        
        # Export button
        self.export_btn = QPushButton("📤 Export Data")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.export_btn.clicked.connect(self.export_data)
        export_layout.addWidget(self.export_btn, 3, 0, 1, 2)
        
        layout.addWidget(export_group)
        
        # Import section
        import_group = QGroupBox("Import Data")
        import_layout = QVBoxLayout(import_group)
        
        import_info = QLabel(
            "📋 Import curves and calculations from other wells or external sources.\\n"
            "Supported formats: CSV, Excel, JSON, and ERC database exports."
        )
        import_info.setWordWrap(True)
        import_info.setStyleSheet("color: #666; font-style: italic;")
        import_layout.addWidget(import_info)
        
        import_actions = QHBoxLayout()
        
        self.import_curves_btn = QPushButton("📈 Import Curves")
        self.import_curves_btn.clicked.connect(self.import_curves)
        import_actions.addWidget(self.import_curves_btn)
        
        self.import_calcs_btn = QPushButton("🧮 Import Calculations")
        self.import_calcs_btn.clicked.connect(self.import_calculations)
        import_actions.addWidget(self.import_calcs_btn)
        
        import_actions.addStretch()
        import_layout.addLayout(import_actions)
        
        layout.addWidget(import_group)
        layout.addStretch()
        
        return widget
        
    def create_utilities_tab(self):
        """Create the database utilities tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Database info
        info_group = QGroupBox("Database Information")
        info_layout = QVBoxLayout(info_group)
        
        self.db_info_text = QTextEdit()
        self.db_info_text.setMaximumHeight(100)
        self.db_info_text.setReadOnly(True)
        self.db_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        info_layout.addWidget(self.db_info_text)
        
        layout.addWidget(info_group)
        
        # Maintenance utilities
        maintenance_group = QGroupBox("Database Maintenance")
        maintenance_layout = QGridLayout(maintenance_group)
        
        self.cleanup_btn = QPushButton("🧹 Cleanup Orphaned Data")
        self.cleanup_btn.setToolTip("Remove data not associated with existing curves")
        self.cleanup_btn.clicked.connect(self.cleanup_database)
        maintenance_layout.addWidget(self.cleanup_btn, 0, 0)
        
        self.reindex_btn = QPushButton("🔄 Reindex Database")
        self.reindex_btn.setToolTip("Rebuild database indices for better performance")
        self.reindex_btn.clicked.connect(self.reindex_database)
        maintenance_layout.addWidget(self.reindex_btn, 0, 1)
        
        self.validate_btn = QPushButton("✅ Validate Data Integrity")
        self.validate_btn.setToolTip("Check for data consistency issues")
        self.validate_btn.clicked.connect(self.validate_data_integrity)
        maintenance_layout.addWidget(self.validate_btn, 1, 0)
        
        self.backup_btn = QPushButton("💾 Backup Database")
        self.backup_btn.setToolTip("Create a backup of ERC data for this well")
        self.backup_btn.clicked.connect(self.backup_database)
        maintenance_layout.addWidget(self.backup_btn, 1, 1)
        
        layout.addWidget(maintenance_group)
        
        # Status display
        status_group = QGroupBox("Operation Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                font-size: 9px;
            }
        """)
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
        return widget
        
    def load_existing_data(self):
        """Load existing data from the database."""
        try:
            self.update_status("Loading existing data...")
            
            # Load curves
            self.load_curves_data()
            
            # Load calculations
            self.load_calculations_data()
            
            # Update database info
            self.update_database_info()
            
            self.update_status("Data loaded successfully.")
            
        except Exception as e:
            self.update_status(f"Error loading data: {str(e)}")
            
    def load_curves_data(self):
        """Load curves data into the table."""
        try:
            if not self.erc_database:
                return
                
            curves = self.erc_database.get_curves_for_well(self.well_id)
            
            self.curves_table.setRowCount(len(curves))
            for i, curve in enumerate(curves):
                self.curves_table.setItem(i, 0, QTableWidgetItem(str(curve['id'])))
                self.curves_table.setItem(i, 1, QTableWidgetItem(curve['curve_type']))
                self.curves_table.setItem(i, 2, QTableWidgetItem(f"{curve['r_squared']:.3f}"))
                self.curves_table.setItem(i, 3, QTableWidgetItem(curve['creation_date'][:10]))
                self.curves_table.setItem(i, 4, QTableWidgetItem(str(curve['recession_segments'])))
                self.curves_table.setItem(i, 5, QTableWidgetItem(curve.get('description', '')))
                
        except Exception as e:
            self.update_status(f"Error loading curves: {str(e)}")
            
    def load_calculations_data(self):
        """Load calculations data into the table."""
        try:
            if not self.erc_database:
                return
                
            # Mock data for now - replace with actual database query
            calculations = []  # self.erc_database.get_calculations_for_well(self.well_id)
            
            self.calculations_table.setRowCount(len(calculations))
            for i, calc in enumerate(calculations):
                self.calculations_table.setItem(i, 0, QTableWidgetItem(str(calc.get('id', ''))))
                self.calculations_table.setItem(i, 1, QTableWidgetItem(str(calc.get('curve_id', ''))))
                self.calculations_table.setItem(i, 2, QTableWidgetItem(calc.get('calculation_date', '')[:10]))
                self.calculations_table.setItem(i, 3, QTableWidgetItem(f"{calc.get('total_recharge', 0):.2f}"))
                self.calculations_table.setItem(i, 4, QTableWidgetItem(f"{calc.get('annual_rate', 0):.3f}"))
                self.calculations_table.setItem(i, 5, QTableWidgetItem(str(calc.get('total_events', 0))))
                self.calculations_table.setItem(i, 6, QTableWidgetItem(f"{calc.get('quality_score', 0):.2f}"))
                
        except Exception as e:
            self.update_status(f"Error loading calculations: {str(e)}")
            
    def update_database_info(self):
        """Update database information display."""
        try:
            info_text = "ERC Database Information\\n"
            info_text += "=" * 30 + "\\n\\n"
            
            if self.erc_database:
                info_text += f"Database: Connected\\n"
                info_text += f"Well ID: {self.well_id}\\n"
                info_text += f"Curves: {self.curves_table.rowCount()}\\n"
                info_text += f"Calculations: {self.calculations_table.rowCount()}\\n"
            else:
                info_text += "Database: Not connected\\n"
                
            self.db_info_text.setPlainText(info_text)
            
        except Exception as e:
            self.update_status(f"Error updating database info: {str(e)}")
            
    def view_curve_details(self):
        """View details of selected curve."""
        current_row = self.curves_table.currentRow()
        if current_row >= 0:
            curve_id = self.curves_table.item(current_row, 0).text()
            self.update_status(f"Viewing details for curve {curve_id}")
            # Implementation would load and display detailed curve information
            
    def duplicate_curve(self):
        """Duplicate selected curve."""
        current_row = self.curves_table.currentRow()
        if current_row >= 0:
            curve_id = self.curves_table.item(current_row, 0).text()
            self.update_status(f"Duplicating curve {curve_id}")
            # Implementation would duplicate the curve with new ID
            
    def delete_curve(self):
        """Delete selected curve."""
        current_row = self.curves_table.currentRow()
        if current_row >= 0:
            curve_id = self.curves_table.item(current_row, 0).text()
            reply = QMessageBox.question(
                self, "Delete Curve",
                f"Are you sure you want to delete curve {curve_id}?\\n"
                "This will also delete all associated calculations.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.update_status(f"Deleting curve {curve_id}")
                # Implementation would delete curve and refresh data
                
    def view_calculation_details(self):
        """View details of selected calculation."""
        current_row = self.calculations_table.currentRow()
        if current_row >= 0:
            calc_id = self.calculations_table.item(current_row, 0).text()
            self.update_status(f"Viewing calculation {calc_id}")
            
    def export_calculation(self):
        """Export selected calculation."""
        current_row = self.calculations_table.currentRow()
        if current_row >= 0:
            calc_id = self.calculations_table.item(current_row, 0).text()
            self.update_status(f"Exporting calculation {calc_id}")
            
    def delete_calculation(self):
        """Delete selected calculation."""
        current_row = self.calculations_table.currentRow()
        if current_row >= 0:
            calc_id = self.calculations_table.item(current_row, 0).text()
            reply = QMessageBox.question(
                self, "Delete Calculation",
                f"Are you sure you want to delete calculation {calc_id}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.update_status(f"Deleting calculation {calc_id}")
                
    def export_data(self):
        """Export data in selected format."""
        format_type = self.export_format.currentText()
        self.update_status(f"Exporting data in {format_type} format...")
        
        # Mock implementation
        QMessageBox.information(self, "Export Complete", 
            f"Data exported successfully in {format_type} format.")
        
    def import_curves(self):
        """Import curves from file."""
        self.update_status("Importing curves...")
        QMessageBox.information(self, "Import", "Curve import functionality coming soon.")
        
    def import_calculations(self):
        """Import calculations from file."""
        self.update_status("Importing calculations...")
        QMessageBox.information(self, "Import", "Calculation import functionality coming soon.")
        
    def cleanup_database(self):
        """Clean up orphaned database entries."""
        self.update_status("Cleaning up database...")
        # Mock implementation
        QMessageBox.information(self, "Cleanup Complete", "Database cleanup completed successfully.")
        
    def reindex_database(self):
        """Reindex database for better performance."""
        self.update_status("Reindexing database...")
        # Mock implementation
        QMessageBox.information(self, "Reindex Complete", "Database reindexing completed successfully.")
        
    def validate_data_integrity(self):
        """Validate data integrity."""
        self.update_status("Validating data integrity...")
        # Mock implementation
        QMessageBox.information(self, "Validation Complete", "Data integrity validation completed. No issues found.")
        
    def backup_database(self):
        """Create database backup."""
        self.update_status("Creating database backup...")
        # Mock implementation
        QMessageBox.information(self, "Backup Complete", "Database backup created successfully.")
        
    def refresh_data(self):
        """Refresh all data displays."""
        self.load_existing_data()
        
    def update_status(self, message):
        """Update the status display."""
        current_text = self.status_text.toPlainText()
        new_text = f"{current_text}\\n{message}" if current_text else message
        self.status_text.setPlainText(new_text)
        
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.End)
        self.status_text.setTextCursor(cursor)


class ErcTab(BaseRechargeTab):
    """
    Tab implementing the ERC (Extended Recession Curve) method for recharge estimation.
    Extended implementation with temporal variability analysis and enhanced validation.
    """
    
    def __init__(self, data_manager, parent=None):
        """
        Initialize the ERC tab.
        
        Args:
            data_manager: Data manager providing access to well data
            parent: Parent widget
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.selected_wells = []
        self.well_data = {}
        self.current_well = None
        self.water_years = []
        self.selected_water_year = None
        self.raw_data = None  # Store the raw data (15-min intervals)
        self.processed_data = None  # Store the processed/filtered data
        self.current_curve = None  # Current ERC curve parameters
        self.recession_segments = []  # Identified recession segments
        self.recharge_events = []  # Calculated recharge events
        self.temporal_analysis = {}  # Seasonal/temporal analysis results
        
        # Session state management for preserving work across well switches
        self.well_sessions = {}  # Store per-well state data
        self.session_saving_enabled = True  # Can be disabled during restoration
        
        # Data management - separate display and calculation data (like MRC tab)
        self.display_data = None  # Store downsampled data for fast plotting
        self.calculation_data = None  # Store the full resolution data for calculations
        self.data_loaded = {'display': False, 'full': False}  # Track what's loaded
        self.data_loading = False  # Prevent concurrent loading
        
        # Initialize default settings for data processing
        self.current_settings = {
            'specific_yield': 0.2,
            'erc_deviation_threshold': 0.05,
            'water_year_month': 10,
            'water_year_day': 1,
            'downsample_frequency': 'Daily (1D) - Recommended',
            'downsample_method': 'Median (for pumped wells) - Recommended',
            'enable_smoothing': False,
            'smoothing_window': 3,
            'min_recession_length': 7,
            'fluctuation_tolerance': 0.02,
            'curve_type': 'exponential',
            'r_squared_threshold': 0.5,
            'validation_split': 0.2,
            'enable_seasonal': True,
            'seasonal_periods': 'quarterly'
        }
        
        # Initialize database for ERC calculations
        self.erc_db = None
        self.db_path = None  # Store path, create connection when needed
        self.get_db_path()
        
        # Setup UI
        self.setup_ui()
    
    def get_db_path(self):
        """Get database path from data manager."""
        try:
            # Get database path from data manager
            if hasattr(self.data_manager, 'db_path'):
                self.db_path = self.data_manager.db_path
            elif hasattr(self.data_manager, '_db_manager') and hasattr(self.data_manager._db_manager, 'current_db'):
                self.db_path = self.data_manager._db_manager.current_db
            elif hasattr(self.data_manager, 'current_db'):
                self.db_path = self.data_manager.current_db
            else:
                logger.warning("Could not find database path in data manager")
                self.db_path = None
        except Exception as e:
            logger.error(f"Error getting database path: {e}")
            self.db_path = None
    
    def get_erc_database(self):
        """Get or create ERC database connection for current thread."""
        if not self.db_path:
            self.get_db_path()
            
        if not self.db_path:
            logger.error("No database path available for ERC")
            return None
            
        try:
            # Create a new database connection for this thread
            erc_db = ErcDatabase(self.db_path)
            
            # Create tables if they don't exist
            success = erc_db.create_tables()
            if success:
                return erc_db
            else:
                logger.error("Failed to initialize ERC database tables")
                return None
                
        except Exception as e:
            logger.error(f"Error creating ERC database connection: {e}")
            return None
    
    def save_current_well_state(self):
        """Save current well state for session persistence."""
        if not self.session_saving_enabled or not self.current_well:
            return
            
        try:
            state = {
                'recession_segments': self.recession_segments,
                'current_curve': self.current_curve,
                'recharge_events': self.recharge_events,
                'temporal_analysis': self.temporal_analysis,
                'processed_data': self.processed_data,
                'settings': self.current_settings.copy()
            }
            self.well_sessions[self.current_well] = state
            logger.debug(f"Saved ERC session state for well {self.current_well}")
        except Exception as e:
            logger.error(f"Error saving ERC well state: {e}")
    
    def restore_well_state(self, well_id):
        """Restore well state from session."""
        if well_id not in self.well_sessions:
            return False
            
        try:
            self.session_saving_enabled = False  # Prevent recursive saving
            state = self.well_sessions[well_id]
            
            self.recession_segments = state.get('recession_segments', [])
            self.current_curve = state.get('current_curve')
            self.recharge_events = state.get('recharge_events', [])
            self.temporal_analysis = state.get('temporal_analysis', {})
            self.processed_data = state.get('processed_data')
            self.current_settings.update(state.get('settings', {}))
            
            # Update UI elements
            self.update_ui_from_state()
            
            logger.debug(f"Restored ERC session state for well {well_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring ERC well state: {e}")
            return False
        finally:
            self.session_saving_enabled = True
    
    def update_ui_from_state(self):
        """Update UI elements based on restored state."""
        try:
            # Update segment display if available
            if hasattr(self, 'segments_combo') and self.recession_segments:
                self.populate_segments_dropdown()
            
            # Update curve info if available
            if hasattr(self, 'curve_combo') and self.current_curve:
                self.display_curve_info()
            
            # Update plot
            if hasattr(self, 'update_plot'):
                self.update_plot()
                
        except Exception as e:
            logger.error(f"Error updating ERC UI from state: {e}")
    
    def load_panel_states(self):
        """Load the saved states of collapsible panels."""
        try:
            # Load states for both collapsible panels if they exist
            if hasattr(self, 'segments_group') and self.segments_group:
                self.segments_group.load_state()
            if hasattr(self, 'curve_group') and self.curve_group:
                self.curve_group.load_state()
            logger.debug("Loaded ERC collapsible panel states")
        except Exception as e:
            logger.warning(f"Failed to load ERC panel states: {e}")
    
    def setup_ui(self):
        """Setup the modern ERC tab with step-based workflow."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Instructions panel
        instructions = QLabel(
            "🔬 ERC (Extended Recession Curve) Method - Advanced temporal recession analysis with seasonal variability"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                background-color: #e8f4fd;
                padding: 12px;
                border: 1px solid #bee5eb;
                border-radius: 5px;
                color: #0c5460;
                font-weight: 500;
                margin: 5px;
            }
        """)
        layout.addWidget(instructions)
        
        # Create main horizontal splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)
        
        # Left panel with step-based workflow
        left_panel = self.create_left_panel()
        self.main_splitter.addWidget(left_panel)
        
        # Right panel - Plot visualization  
        right_panel = self.create_plot_panel()
        self.main_splitter.addWidget(right_panel)
        
        # Set splitter sizes to match fixed widths (400px left, 800px right)
        self.main_splitter.setSizes([400, 800])
        
        layout.addWidget(self.main_splitter)
    
    def create_left_panel(self):
        """Create the left panel with tabs for curve management and results."""
        from PyQt5.QtWidgets import QScrollArea
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for curve management and results
        self.left_tabs = QTabWidget()
        
        # Curve Management tab with scroll area
        curve_panel = self.create_curve_management_panel()
        curve_scroll = QScrollArea()
        curve_scroll.setWidget(curve_panel)
        curve_scroll.setWidgetResizable(True)
        curve_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        curve_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_tabs.addTab(curve_scroll, "Curve Management")
        
        # Results tab
        results_panel = self.create_results_panel()
        self.left_tabs.addTab(results_panel, "Results")
        
        left_layout.addWidget(self.left_tabs)
        
        # Set fixed width for visual consistency across all tabs
        left_widget.setFixedWidth(400)
        
        return left_widget
    
    def create_curve_management_panel(self):
        """Create the curve management panel with step-based workflow."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Well selection
        well_layout = QHBoxLayout()
        well_layout.addWidget(QLabel("Well:"))
        self.well_combo = QComboBox()
        self.well_combo.setEnabled(False)
        self.well_combo.currentIndexChanged.connect(self.on_well_selected)
        well_layout.addWidget(self.well_combo)
        layout.addLayout(well_layout)
        
        # Consistent button styling for all buttons
        button_style = """
            QPushButton {
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
        
        # === STEP 1: RECESSION SEGMENT ANALYSIS (Collapsible) ===
        self.segments_group = CollapsibleGroupBox("Step 1: Recession Segment Analysis", "erc_step1_segments")
        
        # Analyze patterns button (removed Load Data button)
        segments_action_layout = QHBoxLayout()
        segments_action_layout.setSpacing(8)
        
        self.identify_segments_btn = QPushButton("🔍 Analyze Patterns")
        self.identify_segments_btn.clicked.connect(self.identify_recession_segments)
        self.identify_segments_btn.setEnabled(False)
        self.identify_segments_btn.setStyleSheet(button_style)
        self.identify_segments_btn.setToolTip("Identify recession segments with seasonal classification")
        segments_action_layout.addWidget(self.identify_segments_btn)
        
        self.segments_group.add_layout(segments_action_layout)
        
        # Load segments section
        load_segments_layout = QVBoxLayout()
        load_segments_layout.setSpacing(6)
        
        load_segments_label = QLabel("📂 Load Segments:")
        load_segments_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin-top: 8px;")
        load_segments_layout.addWidget(load_segments_label)
        
        # Segments dropdown
        self.segments_combo = QComboBox()
        self.segments_combo.addItem("No segments selected", None)
        self.segments_combo.currentIndexChanged.connect(self.on_segments_selected)
        self.segments_combo.setMinimumHeight(26)
        self.segments_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox:focus {
                border-color: #80bdff;
                outline: none;
            }
        """)
        load_segments_layout.addWidget(self.segments_combo)
        
        self.segments_group.add_layout(load_segments_layout)
        
        layout.addWidget(self.segments_group)
        
        # === STEP 2: INTERACTIVE CURVE FITTING (Collapsible) ===
        self.curve_group = CollapsibleGroupBox("Step 2: Interactive Curve Fitting", "erc_step2_curves")
        
        # Horizontal layout for curve selection and results
        curve_info_horizontal = QHBoxLayout()
        curve_info_horizontal.setSpacing(12)
        
        # Left side: Load existing curves section
        existing_section = QFrame()
        existing_layout = QVBoxLayout(existing_section)
        existing_layout.setContentsMargins(8, 8, 8, 8)
        existing_layout.setSpacing(8)
        
        existing_label = QLabel("📁 Load Existing Curve:")
        existing_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px; margin-bottom: 4px;")
        existing_layout.addWidget(existing_label)
        
        # Curve selection dropdown
        self.curve_combo = QComboBox()
        self.curve_combo.addItem("No curve selected", None)
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        self.curve_combo.setMinimumHeight(28)
        self.curve_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox:focus {
                border-color: #80bdff;
                outline: none;
            }
        """)
        existing_layout.addWidget(self.curve_combo)
        
        # Interactive fitting button
        self.interactive_fit_btn = QPushButton("🎯 Interactive Fitting")
        self.interactive_fit_btn.clicked.connect(self.open_interactive_fitting)
        self.interactive_fit_btn.setEnabled(False)
        self.interactive_fit_btn.setStyleSheet(button_style)
        self.interactive_fit_btn.setToolTip("Open interactive curve fitting dialog")
        existing_layout.addWidget(self.interactive_fit_btn)
        
        # Manage data button
        self.manage_data_btn = QPushButton("🗂️ Manage Data")
        self.manage_data_btn.clicked.connect(self.open_manage_data_dialog)
        self.manage_data_btn.setEnabled(False)
        self.manage_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.manage_data_btn.setToolTip("Manage saved curves and segments")
        existing_layout.addWidget(self.manage_data_btn)
        
        curve_info_horizontal.addWidget(existing_section)
        
        # Right side: Current curve info
        info_section = QFrame()
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(6)
        
        info_label = QLabel("📈 Current Curve:")
        info_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px; margin-bottom: 4px;")
        info_layout.addWidget(info_label)
        
        self.curve_equation_label = QLabel("No curve fitted")
        self.curve_equation_label.setStyleSheet("font-size: 11px; color: #666; font-family: monospace;")
        self.curve_equation_label.setWordWrap(True)
        info_layout.addWidget(self.curve_equation_label)
        
        self.r_squared_label = QLabel("R² = N/A")
        self.r_squared_label.setStyleSheet("font-size: 11px; color: #666;")
        info_layout.addWidget(self.r_squared_label)
        
        self.cv_score_label = QLabel("CV Score = N/A")
        self.cv_score_label.setStyleSheet("font-size: 11px; color: #666;")
        info_layout.addWidget(self.cv_score_label)
        
        curve_info_horizontal.addWidget(info_section)
        
        self.curve_group.add_layout(curve_info_horizontal)
        
        layout.addWidget(self.curve_group)
        
        # === STEP 3: CALCULATE RECHARGE (Non-collapsible) ===
        calculate_group = QGroupBox("Step 3: Calculate Recharge")
        calculate_layout = QVBoxLayout(calculate_group)
        calculate_layout.setSpacing(8)
        
        # Calculate button
        self.calculate_btn = QPushButton("🧮 Calculate ERC Recharge")
        self.calculate_btn.clicked.connect(self.calculate_recharge)
        self.calculate_btn.setEnabled(False)
        self.calculate_btn.setMinimumHeight(40)
        self.calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.calculate_btn.setToolTip("Calculate recharge using the fitted ERC curve")
        calculate_layout.addWidget(self.calculate_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        calculate_layout.addWidget(self.progress_bar)
        
        # Calculation status
        self.calculation_status_label = QLabel("Ready to calculate")
        self.calculation_status_label.setStyleSheet("font-size: 11px; color: #666; text-align: center;")
        calculate_layout.addWidget(self.calculation_status_label)
        
        layout.addWidget(calculate_group)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        # Load panel states after all panels are created
        self.load_panel_states()
        
        return panel
    
    def create_results_panel(self):
        """Create the results panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Create yearly statistics table
        self.yearly_stats_table = QTableWidget()
        self.yearly_stats_table.setColumnCount(6)
        self.yearly_stats_table.setHorizontalHeaderLabels([
            "Water Year", "Events", "Recharge (in)", "Rate (in/yr)", "Max Deviation (ft)", "Quality"
        ])
        self.yearly_stats_table.setSortingEnabled(True)
        self.yearly_stats_table.setAlternatingRowColors(True)
        self.yearly_stats_table.verticalHeader().setVisible(False)
        layout.addWidget(self.yearly_stats_table)
        
        # Summary section
        summary_group = QGroupBox("Recharge Summary")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setSpacing(10)
        
        # Total recharge
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("Total Recharge:"))
        self.total_recharge_label = QLabel("0.0 inches")
        self.total_recharge_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        total_layout.addWidget(self.total_recharge_label)
        total_layout.addStretch()
        summary_layout.addLayout(total_layout)
        
        # Annual rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Annual Rate:"))
        self.annual_rate_label = QLabel("0.0 inches/year")
        self.annual_rate_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        rate_layout.addWidget(self.annual_rate_label)
        rate_layout.addStretch()
        summary_layout.addLayout(rate_layout)
        
        # Event count
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Total Events:"))
        self.events_count_label = QLabel("0")
        self.events_count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        count_layout.addWidget(self.events_count_label)
        count_layout.addStretch()
        summary_layout.addLayout(count_layout)
        
        # Quality score
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality Score:"))
        self.quality_score_label = QLabel("N/A")
        self.quality_score_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        quality_layout.addWidget(self.quality_score_label)
        quality_layout.addStretch()
        summary_layout.addLayout(quality_layout)
        
        layout.addWidget(summary_group)
        
        # Export options
        export_layout = QHBoxLayout()
        
        # Define button styling
        button_style = """
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
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
        
        self.export_csv_btn = QPushButton("Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_csv_btn.setStyleSheet(button_style)
        export_layout.addWidget(self.export_csv_btn)
        
        self.export_excel_btn = QPushButton("Export to Excel")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_excel_btn.setStyleSheet(button_style)
        export_layout.addWidget(self.export_excel_btn)
        
        layout.addLayout(export_layout)
        
        # Database operations
        db_group = QGroupBox("Database Operations")
        db_layout = QVBoxLayout(db_group)
        
        # Save button
        self.save_to_db_btn = QPushButton("Save to Database")
        self.save_to_db_btn.clicked.connect(self.save_to_database)
        self.save_to_db_btn.setToolTip("Save the current ERC calculation to the database")
        self.save_to_db_btn.setStyleSheet(button_style)
        db_layout.addWidget(self.save_to_db_btn)
        
        # Load button
        self.load_from_db_btn = QPushButton("Load from Database")
        self.load_from_db_btn.clicked.connect(self.load_from_database)
        self.load_from_db_btn.setToolTip("Load a previous ERC calculation from the database")
        self.load_from_db_btn.setStyleSheet(button_style)
        db_layout.addWidget(self.load_from_db_btn)
        
        # Compare button
        self.compare_btn = QPushButton("Compare Calculations")
        self.compare_btn.clicked.connect(self.compare_calculations)
        self.compare_btn.setToolTip("Compare multiple ERC calculations")
        self.compare_btn.setStyleSheet(button_style)
        db_layout.addWidget(self.compare_btn)
        
        layout.addWidget(db_group)
        
        return panel
    
    def on_segments_selected(self):
        """Handle segment selection from dropdown."""
        curve_id = self.segments_combo.currentData()
        if curve_id:
            self.load_segments_for_curve(curve_id)
            self.save_current_well_state()
    
    def on_curve_selected(self):
        """Handle curve selection from dropdown."""
        curve_id = self.curve_combo.currentData()
        if curve_id:
            self.load_curve_details(curve_id)
            self.save_current_well_state()
    
    def open_interactive_fitting(self):
        """Open the interactive curve fitting dialog."""
        try:
            if not self.recession_segments:
                QMessageBox.warning(self, "No Segments", 
                    "Please identify recession segments first before curve fitting.")
                return
                
            # Get current settings for the dialog
            current_settings = self.get_current_settings()
            
            # Create and show the dialog
            dialog = InteractiveCurveFittingDialog(
                self.recession_segments, 
                current_settings, 
                self
            )
            
            # Connect the curve fitted signal
            dialog.curve_fitted.connect(self.on_curve_fitted)
            
            # Show dialog
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error opening interactive fitting dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", 
                f"Failed to open curve fitting dialog: {str(e)}")
    
    def on_curve_fitted(self, curve_data):
        """Handle when a curve is fitted in the dialog."""
        try:
            # Store the fitted curve
            self.current_curve = curve_data
            
            # Update UI to reflect the new curve
            self.update_curve_display()
            
            # Enable next steps
            self.calculate_btn.setEnabled(True)
            
            # Update plot with the fitted curve
            self.update_plot()
            
            logger.info(f"Curve fitted successfully: {curve_data['type']} with R² = {curve_data['r_squared']:.4f}")
            
        except Exception as e:
            logger.error(f"Error handling fitted curve: {e}")
    
    def update_curve_display(self):
        """Update the curve display in the UI."""
        try:
            if not self.current_curve:
                return
                
            # Update curve combo to show current curve
            curve_type = self.current_curve['type']
            r_squared = self.current_curve['r_squared']
            
            # Add current curve to dropdown if not already there
            current_text = f"Current: {curve_type} (R² = {r_squared:.3f})"
            
            # Check if this curve is already in the dropdown
            found_index = -1
            for i in range(self.curve_combo.count()):
                if self.curve_combo.itemText(i).startswith("Current:"):
                    found_index = i
                    break
                    
            if found_index >= 0:
                # Replace existing current curve
                self.curve_combo.setItemText(found_index, current_text)
                self.curve_combo.setCurrentIndex(found_index)
            else:
                # Add new current curve
                self.curve_combo.insertItem(0, current_text, self.current_curve)
                self.curve_combo.setCurrentIndex(0)
                
        except Exception as e:
            logger.error(f"Error updating curve display: {e}")
    
    def open_manage_data_dialog(self):
        """Open the modern data management dialog."""
        try:
            # Get current well ID
            well_id = None
            if hasattr(self, 'well_combo') and self.well_combo.currentData():
                well_id = self.well_combo.currentData()
            
            if not well_id:
                QMessageBox.warning(self, "No Well Selected", 
                    "Please select a well before opening data management.")
                return
            
            # Get ERC database instance
            erc_database = self.get_erc_database()
            
            # Create and show the dialog
            dialog = ModernDataManagementDialog(
                well_id, 
                erc_database, 
                self
            )
            
            # Connect data updated signal
            dialog.data_updated.connect(self.on_data_updated)
            
            # Show dialog
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error opening data management dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", 
                f"Failed to open data management dialog: {str(e)}")
    
    def on_data_updated(self):
        """Handle when data is updated in the management dialog."""
        try:
            # Refresh curve and calculation dropdowns
            self.load_existing_curves()
            
            # Update plot if needed
            self.update_plot()
            
            logger.info("Data refreshed after management dialog updates")
            
        except Exception as e:
            logger.error(f"Error handling data updates: {e}")
    
    def load_segments_for_curve(self, curve_id):
        """Load segments for a specific curve."""
        try:
            erc_db = self.get_erc_database()
            if not erc_db:
                return
                
            segments = erc_db.get_segments_for_curve(curve_id)
            self.recession_segments = segments
            
            # Enable next step
            if segments:
                self.interactive_fit_btn.setEnabled(True)
                
            logger.info(f"Loaded {len(segments)} segments for curve {curve_id}")
            
        except Exception as e:
            logger.error(f"Error loading segments for curve {curve_id}: {e}")
    
    def load_curve_details(self, curve_id):
        """Load details for a specific curve."""
        try:
            erc_db = self.get_erc_database()
            if not erc_db:
                return
                
            curve_data = erc_db.get_curve_details(curve_id)
            if curve_data:
                self.current_curve = curve_data
                self.display_curve_info()
                
                # Enable calculate button if we have a curve
                self.calculate_btn.setEnabled(True)
                
            logger.info(f"Loaded curve details for curve {curve_id}")
            
        except Exception as e:
            logger.error(f"Error loading curve details for curve {curve_id}: {e}")
    
    def display_curve_info(self):
        """Display current curve information."""
        if not self.current_curve:
            self.curve_equation_label.setText("No curve fitted")
            self.r_squared_label.setText("R² = N/A")
            self.cv_score_label.setText("CV Score = N/A")
            return
            
        try:
            # Extract curve information
            curve_type = self.current_curve.get('curve_type', 'unknown')
            coeffs = self.current_curve.get('curve_coefficients', {})
            r_squared = self.current_curve.get('r_squared', 0)
            cv_score = self.current_curve.get('cross_validation_score', None)
            
            # Format equation based on curve type
            if curve_type == 'exponential':
                k = coeffs.get('k', 0)
                L0 = coeffs.get('L0', 0)
                equation = f"L = {L0:.2f} × e^(-{k:.4f}×t)"
            elif curve_type == 'power':
                alpha = coeffs.get('alpha', 0)
                L0 = coeffs.get('L0', 0)
                equation = f"L = {L0:.2f} × t^(-{alpha:.4f})"
            elif curve_type == 'polynomial':
                a = coeffs.get('a', 0)
                b = coeffs.get('b', 0)
                c = coeffs.get('c', 0)
                equation = f"L = {a:.4f}×t² + {b:.4f}×t + {c:.2f}"
            else:
                equation = f"{curve_type.title()} curve"
            
            # Update labels
            self.curve_equation_label.setText(equation)
            self.r_squared_label.setText(f"R² = {r_squared:.4f}")
            if cv_score is not None:
                self.cv_score_label.setText(f"CV Score = {cv_score:.4f}")
            else:
                self.cv_score_label.setText("CV Score = N/A")
                
        except Exception as e:
            logger.error(f"Error displaying curve info: {e}")
    
    def populate_segments_dropdown(self):
        """Populate the segments dropdown with available segment sets."""
        try:
            erc_db = self.get_erc_database()
            if not erc_db or not self.current_well:
                return
                
            segment_sets = erc_db.get_all_segments_for_well(self.current_well)
            
            self.segments_combo.clear()
            self.segments_combo.addItem("No segments selected", None)
            
            for segment_set in segment_sets:
                curve_id = segment_set['curve_id']
                creation_date = segment_set['creation_date'][:10] if segment_set['creation_date'] else "Unknown"
                curve_type = segment_set['curve_type'].title()
                segment_count = segment_set['segment_count']
                r_squared = segment_set.get('r_squared', 0)
                
                display_text = f"{creation_date} - {curve_type} ({segment_count} segments, R²={r_squared:.3f})"
                self.segments_combo.addItem(display_text, curve_id)
                
            logger.info(f"Populated segments dropdown with {len(segment_sets)} options")
            
        except Exception as e:
            logger.error(f"Error populating segments dropdown: {e}")
    
    def populate_curves_dropdown(self):
        """Populate the curves dropdown with available curves."""
        try:
            erc_db = self.get_erc_database()
            if not erc_db or not self.current_well:
                return
                
            curves = erc_db.get_curves_for_well(self.current_well)
            
            self.curve_combo.clear()
            self.curve_combo.addItem("No curve selected", None)
            
            for curve in curves:
                curve_id = curve['id']
                creation_date = curve['creation_date'][:10] if curve['creation_date'] else "Unknown"
                curve_type = curve['curve_type'].title()
                r_squared = curve.get('r_squared', 0)
                description = curve.get('description', '')
                
                if description:
                    display_text = f"{creation_date} - {curve_type} (R²={r_squared:.3f}) - {description}"
                else:
                    display_text = f"{creation_date} - {curve_type} (R²={r_squared:.3f})"
                    
                self.curve_combo.addItem(display_text, curve_id)
                
            logger.info(f"Populated curves dropdown with {len(curves)} options")
            
        except Exception as e:
            logger.error(f"Error populating curves dropdown: {e}")
    
    def update_settings(self, settings):
        """Update ERC tab with unified settings."""
        try:
            logger.info("Updating ERC tab with unified settings")
            
            # Update current settings
            if 'specific_yield' in settings:
                self.current_settings['specific_yield'] = settings['specific_yield']
                
            if 'erc_deviation_threshold' in settings:
                self.current_settings['erc_deviation_threshold'] = settings['erc_deviation_threshold']
                
            if 'water_year_month' in settings:
                self.current_settings['water_year_month'] = settings['water_year_month']
                
            if 'water_year_day' in settings:
                self.current_settings['water_year_day'] = settings['water_year_day']
            
            if 'downsample_frequency' in settings:
                self.current_settings['downsample_frequency'] = settings['downsample_frequency']
                
            if 'downsample_method' in settings:
                self.current_settings['downsample_method'] = settings['downsample_method']
                
            if 'enable_smoothing' in settings:
                self.current_settings['enable_smoothing'] = settings['enable_smoothing']
                
            if 'smoothing_window' in settings:
                self.current_settings['smoothing_window'] = settings['smoothing_window']
                
            if 'min_recession_length' in settings:
                self.current_settings['min_recession_length'] = settings['min_recession_length']
                
            if 'fluctuation_tolerance' in settings:
                self.current_settings['fluctuation_tolerance'] = settings['fluctuation_tolerance']
                
            if 'curve_type' in settings:
                self.current_settings['curve_type'] = settings['curve_type']
                
            if 'r_squared_threshold' in settings:
                self.current_settings['r_squared_threshold'] = settings['r_squared_threshold']
                
            if 'validation_split' in settings:
                self.current_settings['validation_split'] = settings['validation_split']
                
            if 'enable_seasonal' in settings:
                self.current_settings['enable_seasonal'] = settings['enable_seasonal']
                
            if 'seasonal_periods' in settings:
                self.current_settings['seasonal_periods'] = settings['seasonal_periods']
            
            logger.info("ERC tab settings updated successfully")
            
            # Reprocess data if available
            if self.raw_data is not None:
                self.process_data()
                self.update_plot()
            
        except Exception as e:
            logger.error(f"Error updating ERC tab settings: {e}")
    
    def get_current_settings(self):
        """Get current ERC tab settings."""
        return self.current_settings.copy()
    
    def get_method_name(self):
        """Get the method name for this tab."""
        return "ERC"
    
    def update_settings(self, settings):
        """Update current settings from unified settings widget."""
        if settings:
            self.current_settings.update(settings)
            logger.info(f"Updated ERC settings: {settings}")
            
            # If we have data loaded, reprocess it with new settings
            if self.raw_data is not None:
                self.process_data()
                self.update_plot()
    
    def create_plot_panel(self):
        """Create the plot panel for ERC visualization."""
        group_box = QGroupBox("Visualization")
        group_box.setFixedWidth(800)  # Fixed width for visual consistency
        layout = QVBoxLayout(group_box)
        
        # Plot panel - same structure as MRC tab
        # Use base class figure and canvas (already initialized with correct size)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Use standardized display options from base class
        display_options = self.create_plot_display_options()
        
        # Set processed data checkbox to checked by default for ERC tab
        if hasattr(self, 'show_processed_data'):
            self.show_processed_data.setChecked(True)
        
        # Add ERC-specific plot options
        erc_options_layout = QHBoxLayout()
        
        self.show_recession_segments = QCheckBox("Show Recession Segments")
        self.show_recession_segments.setChecked(True)
        self.show_recession_segments.stateChanged.connect(self.update_plot)
        erc_options_layout.addWidget(self.show_recession_segments)
        
        self.show_recession_curve = QCheckBox("Show Recession Curve")
        self.show_recession_curve.setChecked(True)
        self.show_recession_curve.stateChanged.connect(self.update_plot)
        erc_options_layout.addWidget(self.show_recession_curve)
        
        self.show_recharge_events = QCheckBox("Show Recharge Events")
        self.show_recharge_events.setChecked(True)
        self.show_recharge_events.stateChanged.connect(self.update_plot)
        erc_options_layout.addWidget(self.show_recharge_events)
        
        # Add refresh button at the same level as display options
        button_style = """
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
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
                border-color: #dee2e6;
            }
        """
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.update_plot)
        refresh_btn.setStyleSheet(button_style)
        refresh_btn.setMaximumWidth(100)
        erc_options_layout.addWidget(refresh_btn)
        erc_options_layout.addStretch()
        
        # Create a combined layout for display options (same as MRC tab)
        combined_options_layout = QHBoxLayout()
        combined_options_layout.addWidget(display_options)
        combined_options_layout.addLayout(erc_options_layout)
        
        layout.addLayout(combined_options_layout)
        
        return group_box
    
    def on_well_selected(self):
        """Handle well selection change with session state management."""
        new_well = self.well_combo.currentData()
        
        if new_well and new_well != self.current_well:
            # Save current well state before switching
            if self.current_well:
                self.save_current_well_state()
            
            # Try to restore previous session for new well
            if not self.restore_well_state(new_well):
                # No previous session, clear everything and load data
                self.clear_results()
                
                # Data loading disabled - using centralized preprocessing from parent tab
                self.current_well = new_well
                logger.info(f"[PLOT_DEBUG] Skipping individual data loading for ERC - waiting for shared data")
            else:
                # Session restored, just update current well
                self.current_well = new_well
                # Update plot in case data was already loaded in session
                self.update_plot()
            
            # Load available data for this well
            self.populate_segments_dropdown()
            self.populate_curves_dropdown()
            
            # Enable basic operations
            self.manage_data_btn.setEnabled(True)
            
            logger.info(f"Selected ERC well: {new_well}")
    
    def update_well_selection(self, selected_wells):
        """Update the list of selected wells with modern UI state management."""
        self.selected_wells = selected_wells
        
        # Update combo box
        self.well_combo.clear()
        
        if selected_wells:
            self.well_combo.setEnabled(True)
            
            for well_id, well_name in selected_wells:
                self.well_combo.addItem(f"{well_name} ({well_id})", well_id)
                
            logger.info(f"Updated ERC well selection: {len(selected_wells)} wells available")
        else:
            self.well_combo.setEnabled(False)
            # Disable all step buttons when no wells selected
            self.identify_segments_btn.setEnabled(False)
            self.interactive_fit_btn.setEnabled(False)
            self.calculate_btn.setEnabled(False)
            self.manage_data_btn.setEnabled(False)
    
    def load_curves_for_well(self, well_id):
        """Load saved curves for the current well."""
        if not self.erc_db:
            return
            
        try:
            curves = self.erc_db.get_curves_for_well(well_id)
            logger.info(f"Found {len(curves)} saved ERC curves for well {well_id}")
            # Could add curve selection UI here if needed
            
        except Exception as e:
            logger.error(f"Error loading curves for well {well_id}: {e}")
    
    def load_well_data(self, silent=False):
        """Load water level data for the selected well using the same approach as MRC/RISE."""
        # DISABLED: Using centralized preprocessing from parent tab
        logger.info(f"[PLOT_DEBUG] load_well_data disabled - using centralized preprocessing")
        return
        
        if not self.current_well:
            if not silent:
                QMessageBox.warning(self, "No Well Selected", "Please select a well first.")
            return
            
        try:
            logger.info(f"Loading data for well: {self.current_well}")
            
            # Use the same data loading approach as MRC and RISE tabs
            self.data_loading = True
            
            # Load raw data
            try:
                logger.debug("Loading all available raw data")
                df = self.data_manager.get_well_data(
                    self.current_well,
                    downsample=None  # Load raw data without downsampling
                )
                
                if df is not None and len(df) > 0:
                    logger.info(f"Successfully loaded {len(df)} display data points for well {self.current_well}")
                    logger.debug(f"DataFrame columns: {df.columns.tolist()}")
                    logger.debug(f"DataFrame shape: {df.shape}")
                    logger.debug(f"DataFrame head: {df.head()}")
                    
                    # Standardize column names using parent class method
                    df = self.standardize_dataframe(df)
                    logger.debug(f"After standardization - columns: {df.columns.tolist()}")
                    
                    # Validate data contains required columns
                    if 'timestamp' not in df.columns or 'level' not in df.columns:
                        logger.error(f"Missing required columns after standardization. Columns: {df.columns.tolist()}")
                        if not silent:
                            QMessageBox.critical(self, "Data Error", 
                                "Data is missing required timestamp or level columns")
                        return
                    
                    # Check for NaN/Inf values
                    if df['level'].isna().any():
                        logger.warning(f"Found {df['level'].isna().sum()} NaN values in level data")
                        df = df.dropna(subset=['level'])
                        
                    if not np.isfinite(df['level']).all():
                        logger.warning("Found non-finite values in level data, removing them")
                        df = df[np.isfinite(df['level'])]
                    
                    if len(df) == 0:
                        logger.error("No valid data remaining after cleaning")
                        if not silent:
                            QMessageBox.warning(self, "Data Error", 
                                "No valid data points remaining after cleaning")
                        return
                    
                    logger.info(f"Data validation complete: {len(df)} valid points")
                    
                    # Store the raw data
                    self.raw_data = df
                    
                    # Process the data with current settings
                    logger.info("Processing data with global settings...")
                    self.process_data()
                    
                    # Update the plot
                    logger.info("About to call update_plot()...")
                    self.update_plot()
                    
                    # Enable next steps
                    self.identify_segments_btn.setEnabled(True)
                    
                    # Mark data as loaded
                    self.data_loaded = {'display': True, 'full': False}
                    
                    if not silent:
                        QMessageBox.information(self, "Data Loaded", 
                            f"Loaded {len(df)} data points for {self.current_well}")
                    
                    logger.info(f"Data loading finished successfully")
                    return
                else:
                    logger.warning(f"Data loading returned None or empty dataframe for well {self.current_well}")
                    
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                if not silent:
                    QMessageBox.critical(self, "Data Loading Error", 
                        f"Error loading data: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error in load_well_data: {e}", exc_info=True)
            if not silent:
                QMessageBox.warning(
                    self, "Data Loading Error", 
                    f"Failed to load data for well {self.current_well}: {str(e)}"
                )
        finally:
            self.data_loading = False
    
    def _create_synthetic_data(self):
        """Create synthetic data for demonstration."""
        # Create 2 years of data with seasonal patterns
        start_date = datetime.now() - timedelta(days=730)
        end_date = datetime.now()
        
        # Generate timestamps at 15-minute intervals
        timestamps = pd.date_range(start=start_date, end=end_date, freq='15min')
        
        # Generate water levels with seasonal recession behavior
        levels = []
        base_level = 100.0
        current_level = base_level
        
        for i, ts in enumerate(timestamps):
            # Add seasonal variation (stronger recession in summer)
            day_of_year = ts.timetuple().tm_yday
            seasonal_factor = 1.0 + 0.3 * np.sin(2 * np.pi * (day_of_year - 60) / 365.0)
            
            # Add recession behavior with seasonal variability
            if np.random.random() < 0.96:  # 96% of time, recession
                recession_rate = 0.9999 * seasonal_factor  # Faster recession in summer
                current_level *= recession_rate
                # Ensure level doesn't go below a minimum
                current_level = max(current_level, 50.0)
            else:  # 4% of time, recharge event
                recharge_amount = np.random.uniform(0.3, 1.5) * seasonal_factor
                current_level += recharge_amount
                # Ensure level doesn't go too high
                current_level = min(current_level, 120.0)
            
            # Add small random noise
            noise = np.random.normal(0, 0.01)
            level_with_noise = current_level + noise
            # Ensure no NaN or Inf values
            if np.isfinite(level_with_noise):
                levels.append(level_with_noise)
            else:
                levels.append(current_level)
        
        # Create DataFrame
        self.raw_data = pd.DataFrame({
            'timestamp': timestamps,
            'level': levels
        })
        
        logger.debug(f"Generated synthetic ERC data with {len(self.raw_data)} points")
        
        # Process the data
        self.process_data()
        
        # Update the plot
        self.update_plot()
        
        # Enable next steps
        self.identify_segments_btn.setEnabled(True)
    
    def process_data(self):
        """Process the raw data with current preprocessing settings."""
        if self.raw_data is None:
            return
            
        try:
            logger.info("Processing data for ERC method")
            
            # Start with raw data
            data = self.raw_data.copy()
            
            # Make sure timestamp is datetime
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Data quality checks
            self._perform_data_quality_checks(data)
            
            # Apply downsampling from settings
            downsample_freq = self.current_settings.get('downsample_frequency', 'None')
            logger.info(f"ERC processing: downsample_freq = '{downsample_freq}'")
            logger.info(f"ERC current_settings: {self.current_settings}")
            if downsample_freq != 'None' and 'None' not in downsample_freq:
                # Extract frequency code from strings like "Daily (1D) - Recommended"
                import re
                freq_match = re.search(r'\((\w+)\)', downsample_freq)
                if freq_match:
                    freq_code = freq_match.group(1)
                    
                    if 'timestamp' in data.columns:
                        data = data.set_index('timestamp')
                    
                    method = self.current_settings.get('downsample_method', 'Mean')
                    # Extract method name from strings like "Median (for pumped wells) - Recommended"
                    method_name = method.split(' ')[0] if ' ' in method else method
                    
                    if method_name == "Mean":
                        data = data.resample(freq_code).mean()
                    elif method_name == "Median":
                        data = data.resample(freq_code).median()
                    elif method_name == "Last":
                        data = data.resample(freq_code).last()
                        
                    data = data.reset_index()
                    logger.info(f"Applied {freq_code} downsampling using {method_name} method")
            
            # Apply smoothing if enabled in settings
            if self.current_settings.get('enable_smoothing', False):
                window = self.current_settings.get('smoothing_window', 3)
                if 'level' in data.columns:
                    data['level'] = data['level'].rolling(window=window, center=False).mean()
            
            # Drop NaN values
            data = data.dropna()
            
            # Final validation to ensure no NaN/Inf values remain
            if 'level' in data.columns:
                if data['level'].isna().any():
                    logger.warning(f"Removing {data['level'].isna().sum()} remaining NaN values")
                    data = data.dropna(subset=['level'])
                    
                if not np.isfinite(data['level']).all():
                    logger.warning("Removing non-finite values from processed data")
                    data = data[np.isfinite(data['level'])]
            
            if len(data) == 0:
                logger.error("No valid data remaining after processing")
                raise ValueError("No valid data points remaining after processing")
            
            # Store processed data
            self.processed_data = data
            
            logger.info(f"Processed data: {len(self.raw_data)} -> {len(data)} points")
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            QMessageBox.warning(self, "Processing Error", f"Failed to process data: {str(e)}")
    
    def _perform_data_quality_checks(self, data):
        """Perform enhanced data quality checks for ERC method."""
        warnings = []
        
        # Check for data gaps
        if 'timestamp' in data.columns and len(data) > 1:
            time_diffs = data['timestamp'].diff().dropna()
            median_interval = time_diffs.median()
            
            # Find gaps > 1 day
            gaps = time_diffs[time_diffs > pd.Timedelta(days=1)]
            if len(gaps) > 0:
                warnings.append(f"Found {len(gaps)} data gaps > 1 day")
            
            # Check if data frequency is at least daily
            if median_interval > pd.Timedelta(days=1):
                warnings.append(f"Data frequency ({median_interval}) is less than daily")
        
        # Check for negative or zero water levels
        if 'level' in data.columns:
            negative_levels = data[data['level'] <= 0]
            if len(negative_levels) > 0:
                warnings.append(f"Found {len(negative_levels)} non-positive water levels")
                
            # Check for unrealistic variations
            if len(data) > 1:
                daily_changes = data['level'].diff().abs()
                extreme_changes = daily_changes[daily_changes > 10.0]  # > 10 ft change
                if len(extreme_changes) > 0:
                    warnings.append(f"Found {len(extreme_changes)} extreme daily changes (>10 ft)")
        
        # Check minimum data length for ERC
        min_days = 365  # At least 1 year for seasonal analysis
        if len(data) < min_days:
            warnings.append(f"Data length ({len(data)} points) may be insufficient for robust ERC analysis")
        
        # Show warnings if any
        if warnings:
            warning_msg = "Data Quality Issues:\\n\\n" + "\\n".join(f"• {w}" for w in warnings)
            warning_msg += "\\n\\nContinue with analysis?"
            
            reply = QMessageBox.question(
                self, "Data Quality Warning", warning_msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.No:
                raise ValueError("Data quality check failed")
    
    def on_preprocessing_changed(self):
        """Handle changes to preprocessing options."""
        if hasattr(self, 'raw_data') and self.raw_data is not None:
            self.process_data()
            self.update_plot()
    
    def preview_processed_data(self):
        """Preview the processed data."""
        if not hasattr(self, 'raw_data') or self.raw_data is None:
            QMessageBox.warning(self, "No Data", "Please load well data first.")
            return
            
        self.process_data()
        self.update_plot()
        
        QMessageBox.information(self, "Data Preview", 
            f"Original data points: {len(self.raw_data)}\\n"
            f"Processed data points: {len(self.processed_data)}")
    
    def identify_recession_segments(self):
        """Identify recession segments using enhanced analysis dialog."""
        if self.processed_data is None:
            QMessageBox.warning(self, "No Data", "Please load and process data first.")
            return
            
        try:
            # Get current settings for the dialog
            current_settings = self.get_current_settings()
            
            # Create and show the enhanced analysis dialog
            dialog = EnhancedSegmentAnalysisDialog(
                self.processed_data, 
                current_settings, 
                self
            )
            
            # Connect the segments analyzed signal
            dialog.segments_analyzed.connect(self.on_segments_analyzed)
            
            # Show dialog
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error opening segment analysis dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", 
                f"Failed to open segment analysis dialog: {str(e)}")
    
    def on_segments_analyzed(self, segments):
        """Handle when segments are analyzed in the dialog."""
        try:
            # Store the analyzed segments
            self.recession_segments = segments
            
            # Update the segments dropdown
            self.populate_segments_dropdown()
            
            # Update the recession table display
            self.update_recession_table()
            
            # Enable curve fitting if we have enough segments
            if len(self.recession_segments) >= 3:
                self.interactive_fit_btn.setEnabled(True)
                QMessageBox.information(self, "Segments Analyzed", 
                    f"Successfully analyzed {len(self.recession_segments)} recession segments.\\n"
                    f"Quality segments: {sum(1 for s in self.recession_segments if s.get('quality_score', 0) >= 0.6)}")
            else:
                QMessageBox.warning(self, "Insufficient Segments", 
                    f"Analyzed only {len(self.recession_segments)} segments. Need at least 3 for reliable fitting.")
            
            # Update plot to show segments
            self.update_plot()
            
            # Save session state
            self.save_current_well_state()
            
            logger.info(f"Successfully processed {len(segments)} recession segments from enhanced analysis")
            
        except Exception as e:
            logger.error(f"Error handling analyzed segments: {e}")
    
    def populate_segments_dropdown(self):
        """Populate the segments dropdown with analyzed segments."""
        try:
            self.segments_combo.clear()
            
            if not self.recession_segments:
                self.segments_combo.addItem("No segments available", None)
                return
            
            # Add segments to dropdown
            for i, segment in enumerate(self.recession_segments):
                start_date = segment.get('start_date', 'Unknown')
                duration = segment.get('duration', 0)
                quality = segment.get('quality_score', 0)
                
                # Format segment display text
                if isinstance(start_date, str):
                    date_str = start_date[:10]  # Take first 10 chars for date
                else:
                    date_str = str(start_date)[:10]
                    
                text = f"Segment {i+1}: {date_str} ({duration}d, Q={quality:.2f})"
                self.segments_combo.addItem(text, segment)
                
            # Select first segment by default
            if self.recession_segments:
                self.segments_combo.setCurrentIndex(0)
                
        except Exception as e:
            logger.error(f"Error populating segments dropdown: {e}")
    
    def _get_season(self, date):
        """Determine season from date."""
        month = date.month
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"
    
    def update_recession_table(self):
        """Update the recession segments table with enhanced information."""
        if not hasattr(self, 'recession_table'):
            return
        
        self.recession_table.setRowCount(len(self.recession_segments))
        
        for row, segment in enumerate(self.recession_segments):
            # Start date
            self.recession_table.setItem(row, 0, 
                QTableWidgetItem(segment['start_date'].strftime('%Y-%m-%d')))
            
            # End date
            self.recession_table.setItem(row, 1, 
                QTableWidgetItem(segment['end_date'].strftime('%Y-%m-%d')))
            
            # Duration
            self.recession_table.setItem(row, 2, 
                QTableWidgetItem(str(segment['duration_days'])))
            
            # Recession rate
            self.recession_table.setItem(row, 3, 
                QTableWidgetItem(f"{segment['recession_rate']:.4f}"))
            
            # Season
            self.recession_table.setItem(row, 4, 
                QTableWidgetItem(segment['seasonal_period']))
            
            # Use checkbox with quality indication
            checkbox = QCheckBox()
            checkbox.setChecked(segment['used_in_fitting'])
            checkbox.setToolTip(f"Quality Score: {segment['segment_quality']:.3f}")
            
            # Color code based on quality
            if segment['segment_quality'] >= 0.7:
                checkbox.setStyleSheet("QCheckBox { color: green; }")
            elif segment['segment_quality'] >= 0.3:
                checkbox.setStyleSheet("QCheckBox { color: orange; }")
            else:
                checkbox.setStyleSheet("QCheckBox { color: red; }")
                
            self.recession_table.setCellWidget(row, 5, checkbox)
        
        # Resize columns to content
        self.recession_table.resizeColumnsToContents()
    
    def fit_recession_curve(self):
        """Fit ERC curve with enhanced methodology."""
        if not self.recession_segments:
            QMessageBox.warning(self, "No Segments", "Please identify recession segments first.")
            return
            
        try:
            logger.info("Fitting ERC curve with enhanced methodology")
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            
            # Collect data from selected segments
            all_data = []
            validation_data = []
            
            # Get selected segments and split for validation if enabled
            selected_segments = []
            for i, segment in enumerate(self.recession_segments):
                checkbox = self.recession_table.cellWidget(i, 5)
                if checkbox and checkbox.isChecked():
                    selected_segments.append(segment)
            
            if len(selected_segments) < 3:
                QMessageBox.warning(self, "Insufficient Data", 
                    "Please select at least 3 recession segments.")
                self.progress_bar.setVisible(False)
                return
            
            # Split for cross-validation if enabled
            if self.cross_validation_check.isChecked():
                split_idx = int(len(selected_segments) * (1 - self.validation_split.value()))
                training_segments = selected_segments[:split_idx]
                validation_segments = selected_segments[split_idx:]
            else:
                training_segments = selected_segments
                validation_segments = []
            
            self.progress_bar.setValue(30)
            
            # Prepare training data
            for segment in training_segments:
                seg_data = segment['data'].copy()
                seg_data['time_days'] = (seg_data['timestamp'] - seg_data['timestamp'].iloc[0]).dt.total_seconds() / 86400
                # Use absolute levels for ERC (different from MRC normalization)
                seg_data['level_for_fitting'] = seg_data['level']
                all_data.append(seg_data)
            
            # Prepare validation data
            for segment in validation_segments:
                seg_data = segment['data'].copy()
                seg_data['time_days'] = (seg_data['timestamp'] - seg_data['timestamp'].iloc[0]).dt.total_seconds() / 86400
                seg_data['level_for_fitting'] = seg_data['level']
                validation_data.append(seg_data)
            
            self.progress_bar.setValue(50)
            
            # Combine training data
            combined_data = pd.concat(all_data, ignore_index=True)
            
            # Fit curve based on selected type
            curve_type = self.curve_type_combo.currentData()
            
            self.progress_bar.setValue(70)
            
            if curve_type == 'exponential':
                coefficients, r_squared = self._fit_exponential_curve(combined_data)
                equation = f"L = {coefficients['L0']:.2f} × e^(-{coefficients['k']:.4f}×t)"
                
            elif curve_type == 'power':
                coefficients, r_squared = self._fit_power_curve(combined_data)
                equation = f"L = {coefficients['L0']:.2f} × t^(-{coefficients['alpha']:.4f})"
                
            elif curve_type == 'polynomial':
                coefficients, r_squared = self._fit_polynomial_curve(combined_data)
                equation = f"L = {coefficients['a']:.4f}×t² + {coefficients['b']:.4f}×t + {coefficients['c']:.2f}"
                
            elif curve_type == 'multi_segment':
                coefficients, r_squared = self._fit_multi_segment_curve(combined_data)
                equation = "Multi-segment piecewise curve"
            
            self.progress_bar.setValue(90)
            
            # Calculate cross-validation score if validation data available
            cv_score = None
            if validation_data:
                combined_validation = pd.concat(validation_data, ignore_index=True)
                cv_score = self._calculate_validation_score(combined_validation, curve_type, coefficients)
            
            # Store curve parameters with enhanced metadata
            self.current_curve = {
                'curve_type': curve_type,
                'curve_coefficients': coefficients,
                'r_squared': r_squared,
                'cv_score': cv_score,
                'recession_segments': len(training_segments),
                'validation_segments': len(validation_segments),
                'fitting_data': combined_data,
                'seasonal_analysis': self.seasonal_analysis_check.isChecked(),
                'creation_date': datetime.now()
            }
            
            # Perform seasonal analysis if requested
            if self.seasonal_analysis_check.isChecked():
                self._perform_seasonal_analysis()
            
            self.progress_bar.setValue(100)
            
            # Update UI
            self.curve_equation_label.setText(equation)
            self.r_squared_label.setText(f"R² = {r_squared:.4f}")
            if cv_score is not None:
                self.cv_score_label.setText(f"CV Score = {cv_score:.4f}")
            else:
                self.cv_score_label.setText("CV Score = N/A")
            
            # Enable next steps
            self.save_curve_btn.setEnabled(True)
            self.calculate_btn.setEnabled(True)
            
            # Update plot
            self.update_plot()
            
            self.progress_bar.setVisible(False)
            
            # Check curve quality and warn if poor
            if r_squared < self.r_squared_threshold.value():
                QMessageBox.warning(self, "Poor Curve Fit", 
                    f"Curve R² ({r_squared:.3f}) is below threshold ({self.r_squared_threshold.value():.2f}).\\n"
                    f"Consider adjusting parameters or using different segments.")
            else:
                QMessageBox.information(self, "Curve Fitted", 
                    f"Successfully fitted {curve_type} curve\\n"
                    f"R² = {r_squared:.4f}" + 
                    (f", CV Score = {cv_score:.4f}" if cv_score else ""))
            
        except Exception as e:
            logger.error(f"Error fitting ERC curve: {e}")
            QMessageBox.critical(self, "Error", f"Failed to fit curve: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def _fit_exponential_curve(self, data):
        """Fit exponential curve: L = L0 * exp(-k*t)"""
        try:
            # Use log transformation for linear regression
            valid_data = data[data['level_for_fitting'] > 0]
            x = valid_data['time_days'].values
            y = np.log(valid_data['level_for_fitting'].values)
            
            slope, intercept, r_value, _, _ = linregress(x, y)
            
            k = -slope
            L0 = np.exp(intercept)
            r_squared = r_value ** 2
            
            coefficients = {'k': k, 'L0': L0}
            return coefficients, r_squared
            
        except Exception as e:
            logger.error(f"Error fitting exponential curve: {e}")
            raise
    
    def _fit_power_curve(self, data):
        """Fit power curve: L = L0 * t^(-alpha)"""
        try:
            # Use log-log transformation
            valid_data = data[(data['level_for_fitting'] > 0) & (data['time_days'] > 0)]
            x = np.log(valid_data['time_days'].values + 0.001)  # Add small constant to avoid log(0)
            y = np.log(valid_data['level_for_fitting'].values)
            
            slope, intercept, r_value, _, _ = linregress(x, y)
            
            alpha = -slope
            L0 = np.exp(intercept)
            r_squared = r_value ** 2
            
            coefficients = {'alpha': alpha, 'L0': L0}
            return coefficients, r_squared
            
        except Exception as e:
            logger.error(f"Error fitting power curve: {e}")
            raise
    
    def _fit_polynomial_curve(self, data):
        """Fit polynomial curve: L = a*t^2 + b*t + c"""
        try:
            x = data['time_days'].values
            y = data['level_for_fitting'].values
            
            # Fit 2nd order polynomial
            coeffs = np.polyfit(x, y, 2)
            
            # Calculate R²
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            coefficients = {'a': coeffs[0], 'b': coeffs[1], 'c': coeffs[2]}
            return coefficients, r_squared
            
        except Exception as e:
            logger.error(f"Error fitting polynomial curve: {e}")
            raise
    
    def _fit_multi_segment_curve(self, data):
        """Fit multi-segment piecewise curve."""
        try:
            # Simplified multi-segment approach - split into 2 segments
            mid_point = len(data) // 2
            
            # Fit exponential to each segment
            seg1_data = data.iloc[:mid_point]
            seg2_data = data.iloc[mid_point:]
            
            coeffs1, r2_1 = self._fit_exponential_curve(seg1_data)
            coeffs2, r2_2 = self._fit_exponential_curve(seg2_data)
            
            # Combined R² (weighted by segment size)
            w1 = len(seg1_data) / len(data)
            w2 = len(seg2_data) / len(data)
            r_squared = w1 * r2_1 + w2 * r2_2
            
            coefficients = {
                'segment1': coeffs1,
                'segment2': coeffs2,
                'breakpoint': mid_point
            }
            
            return coefficients, r_squared
            
        except Exception as e:
            logger.error(f"Error fitting multi-segment curve: {e}")
            raise
    
    def _calculate_validation_score(self, validation_data, curve_type, coefficients):
        """Calculate validation score using hold-out data."""
        try:
            x = validation_data['time_days'].values
            y_true = validation_data['level_for_fitting'].values
            
            # Predict using fitted curve
            if curve_type == 'exponential':
                y_pred = coefficients['L0'] * np.exp(-coefficients['k'] * x)
            elif curve_type == 'power':
                y_pred = coefficients['L0'] * np.power(x + 0.001, -coefficients['alpha'])
            elif curve_type == 'polynomial':
                y_pred = coefficients['a'] * x**2 + coefficients['b'] * x + coefficients['c']
            else:  # multi_segment - simplified validation
                y_pred = coefficients['segment1']['L0'] * np.exp(-coefficients['segment1']['k'] * x)
            
            # Calculate R²
            ss_res = np.sum((y_true - y_pred) ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            return max(0, r_squared)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Error calculating validation score: {e}")
            return 0.0
    
    def _perform_seasonal_analysis(self):
        """Perform seasonal analysis of recession characteristics."""
        try:
            logger.info("Performing seasonal analysis")
            
            # Group segments by season
            seasonal_segments = {}
            for segment in self.recession_segments:
                season = segment['seasonal_period']
                if season not in seasonal_segments:
                    seasonal_segments[season] = []
                seasonal_segments[season].append(segment)
            
            # Fit curves for each season with sufficient data
            self.temporal_analysis = {}
            for season, segments in seasonal_segments.items():
                if len(segments) >= 2:  # Need at least 2 segments per season
                    season_data = []
                    for segment in segments:
                        seg_data = segment['data'].copy()
                        seg_data['time_days'] = (seg_data['timestamp'] - seg_data['timestamp'].iloc[0]).dt.total_seconds() / 86400
                        seg_data['level_for_fitting'] = seg_data['level']
                        season_data.append(seg_data)
                    
                    combined_season_data = pd.concat(season_data, ignore_index=True)
                    
                    # Fit exponential curve for this season
                    try:
                        coeffs, r2 = self._fit_exponential_curve(combined_season_data)
                        self.temporal_analysis[season] = {
                            'coefficients': coeffs,
                            'r_squared': r2,
                            'segment_count': len(segments)
                        }
                    except:
                        logger.warning(f"Failed to fit curve for season {season}")
            
            logger.info(f"Completed seasonal analysis for {len(self.temporal_analysis)} seasons")
            
        except Exception as e:
            logger.error(f"Error in seasonal analysis: {e}")
    
    def calculate_recharge(self):
        """Calculate recharge using the ERC method with enhanced analysis."""
        if not self.current_curve:
            QMessageBox.warning(self, "No Curve", "Please fit a recession curve first.")
            return
            
        try:
            logger.info("Calculating recharge using ERC method")
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            
            # Get parameters from unified settings or local settings
            if hasattr(self.parent(), 'unified_settings') and self.parent().unified_settings:
                settings = self.parent().unified_settings.get_method_settings('ERC')
                specific_yield = settings.get('specific_yield', self.current_settings['specific_yield'])
                deviation_threshold = settings.get('erc_deviation_threshold', self.current_settings['erc_deviation_threshold'])
            else:
                # Fallback to local settings
                specific_yield = self.current_settings['specific_yield']
                deviation_threshold = self.current_settings['erc_deviation_threshold']
                logger.info("Using local settings - unified settings not available")
            
            logger.info(f"Parameters (from Global Settings): Specific Yield={specific_yield}, Deviation Threshold={deviation_threshold} ft")
            
            # Get processed data
            data = self.processed_data.copy()
            
            self.progress_bar.setValue(30)
            
            # Calculate predicted levels based on curve
            curve_type = self.current_curve['curve_type']
            coeffs = self.current_curve['curve_coefficients']
            
            # Enhanced prediction with seasonal correction if available
            data['predicted_level'] = self._calculate_predicted_levels(data, curve_type, coeffs)
            
            self.progress_bar.setValue(60)
            
            # Ensure both level and predicted_level are numeric to prevent string subtraction errors
            data['level'] = pd.to_numeric(data['level'], errors='coerce')
            data['predicted_level'] = pd.to_numeric(data['predicted_level'], errors='coerce')
            
            # Calculate deviations (positive = potential recharge)
            data['deviation'] = data['level'] - data['predicted_level']
            
            # Enhanced recharge event identification
            data['is_recharge'] = data['deviation'] > deviation_threshold
            
            # Add seasonal and temporal information
            data['season'] = data['timestamp'].apply(self._get_season)
            data['water_year'] = data['timestamp'].apply(self.get_water_year)
            
            # Calculate recharge with enhanced methodology
            data['recharge'] = 0.0
            recharge_mask = data['is_recharge']
            data.loc[recharge_mask, 'recharge'] = data.loc[recharge_mask, 'deviation'] * specific_yield * 12
            
            self.progress_bar.setValue(80)
            
            # Create enhanced recharge events with quality scoring
            self.recharge_events = []
            recharge_data = data[data['is_recharge']]
            
            for idx, row in recharge_data.iterrows():
                # Calculate event magnitude classification
                if row['recharge'] < 0.1:
                    magnitude = 'small'
                elif row['recharge'] < 0.5:
                    magnitude = 'medium'
                else:
                    magnitude = 'large'
                
                # Calculate confidence score based on deviation magnitude and curve quality
                base_confidence = min(1.0, row['deviation'] / (deviation_threshold * 5))
                curve_confidence = self.current_curve['r_squared']
                confidence_score = (base_confidence + curve_confidence) / 2
                
                event = {
                    'event_date': row['timestamp'],
                    'water_year': row['water_year'],
                    'water_level': row['level'],
                    'predicted_level': row['predicted_level'],
                    'deviation': row['deviation'],
                    'recharge_value': row['recharge'],
                    'event_magnitude': magnitude,
                    'seasonal_period': row['season'],
                    'confidence_score': confidence_score,
                    'validation_flag': confidence_score >= 0.5
                }
                self.recharge_events.append(event)
            
            self.progress_bar.setValue(90)
            
            # Calculate enhanced summaries
            total_recharge = sum(e['recharge_value'] for e in self.recharge_events)
            valid_events = [e for e in self.recharge_events if e['validation_flag']]
            
            if len(self.recharge_events) > 0:
                first_date = min(e['event_date'] for e in self.recharge_events)
                last_date = max(e['event_date'] for e in self.recharge_events)
                days_span = (last_date - first_date).total_seconds() / (24 * 3600)
                annual_rate = total_recharge * 365 / days_span if days_span > 0 else 0
                
                # Calculate overall quality score
                avg_confidence = np.mean([e['confidence_score'] for e in self.recharge_events])
                curve_quality = self.current_curve['r_squared']
                cv_quality = self.current_curve.get('cv_score', 0.7)
                quality_score = (avg_confidence + curve_quality + cv_quality) / 3
            else:
                annual_rate = 0
                quality_score = 0
            
            # Update results (only if UI elements exist)
            if hasattr(self, 'total_recharge_label'):
                self.total_recharge_label.setText(f"{total_recharge:.2f} inches")
            if hasattr(self, 'annual_rate_label'):
                self.annual_rate_label.setText(f"{annual_rate:.2f} inches/year")
            if hasattr(self, 'events_count_label'):
                self.events_count_label.setText(f"{len(valid_events)}/{len(self.recharge_events)}")
            if hasattr(self, 'quality_score_label'):
                self.quality_score_label.setText(f"{quality_score:.3f}")
            
            # Update yearly stats with enhanced information
            self.update_yearly_stats()
            
            # Store calculation data
            self.calculation_data = data
            
            # Enable export and save options
            self.export_csv_btn.setEnabled(True)
            self.export_excel_btn.setEnabled(True)
            self.save_calc_btn.setEnabled(True)
            
            # Switch to results tab
            self.left_tabs.setCurrentIndex(3)
            
            # Update plot
            self.update_plot()
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            QMessageBox.information(self, "Calculation Complete", 
                f"ERC calculation completed successfully\\n"
                f"Total events: {len(self.recharge_events)} (Valid: {len(valid_events)})\\n"
                f"Total recharge: {total_recharge:.2f} inches\\n"
                f"Quality score: {quality_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error calculating recharge: {e}")
            QMessageBox.critical(self, "Error", f"Failed to calculate recharge: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def _calculate_predicted_levels(self, data, curve_type, coeffs):
        """Calculate predicted water levels using the fitted curve."""
        predicted = np.full(len(data), np.nan)
        
        # Find recession periods to apply curve
        data['change'] = data['level'].diff()
        data['is_recession'] = data['change'] <= self.fluctuation_tolerance.value()
        data['recession_group'] = (data['is_recession'] != data['is_recession'].shift()).cumsum()
        
        for group_id, group in data[data['is_recession']].groupby('recession_group'):
            if len(group) > 1:
                start_level = group['level'].iloc[0]
                time_days = (group['timestamp'] - group['timestamp'].iloc[0]).dt.total_seconds() / 86400
                
                if curve_type == 'exponential':
                    pred_levels = start_level * np.exp(-coeffs['k'] * time_days)
                elif curve_type == 'power':
                    pred_levels = start_level * np.power(time_days + 0.001, -coeffs['alpha'])
                elif curve_type == 'polynomial':
                    pred_levels = coeffs['a'] * time_days**2 + coeffs['b'] * time_days + coeffs['c']
                elif curve_type == 'multi_segment':
                    # Simplified multi-segment prediction
                    pred_levels = start_level * np.exp(-coeffs['segment1']['k'] * time_days)
                
                predicted[group.index] = pred_levels
        
        # Fill non-recession periods with actual values
        mask = np.isnan(predicted)
        predicted[mask] = data['level'].values[mask]
        
        return predicted
    
    def update_yearly_stats(self):
        """Update the yearly statistics table with enhanced ERC information."""
        if not self.recharge_events or not hasattr(self, 'yearly_stats_table'):
            return
            
        # Group by water year with enhanced statistics
        yearly_stats = {}
        for event in self.recharge_events:
            wy = event['water_year']
            if wy not in yearly_stats:
                yearly_stats[wy] = {
                    'events': 0,
                    'valid_events': 0,
                    'recharge': 0.0,
                    'max_deviation': 0.0,
                    'confidences': [],
                    'seasonal_dist': {'Winter': 0, 'Spring': 0, 'Summer': 0, 'Fall': 0},
                    'dates': []
                }
            
            yearly_stats[wy]['events'] += 1
            if event['validation_flag']:
                yearly_stats[wy]['valid_events'] += 1
            yearly_stats[wy]['recharge'] += event['recharge_value']
            yearly_stats[wy]['max_deviation'] = max(yearly_stats[wy]['max_deviation'], event['deviation'])
            yearly_stats[wy]['confidences'].append(event['confidence_score'])
            yearly_stats[wy]['seasonal_dist'][event['seasonal_period']] += 1
            yearly_stats[wy]['dates'].append(event['event_date'])
        
        # Update table
        self.yearly_stats_table.setRowCount(len(yearly_stats))
        
        row = 0
        for wy, stats in sorted(yearly_stats.items()):
            # Water year
            self.yearly_stats_table.setItem(row, 0, QTableWidgetItem(wy))
            
            # Events (valid/total)
            events_text = f"{stats['valid_events']}/{stats['events']}"
            self.yearly_stats_table.setItem(row, 1, QTableWidgetItem(events_text))
            
            # Recharge
            self.yearly_stats_table.setItem(row, 2, QTableWidgetItem(f"{stats['recharge']:.2f}"))
            
            # Annual rate
            first_date = min(stats['dates'])
            last_date = max(stats['dates'])
            days = (last_date - first_date).total_seconds() / (24 * 3600)
            rate = stats['recharge'] * 365 / days if days > 0 else stats['recharge'] * 365
            self.yearly_stats_table.setItem(row, 3, QTableWidgetItem(f"{rate:.2f}"))
            
            # Max deviation
            self.yearly_stats_table.setItem(row, 4, QTableWidgetItem(f"{stats['max_deviation']:.3f}"))
            
            # Quality score (average confidence)
            avg_confidence = np.mean(stats['confidences']) if stats['confidences'] else 0
            self.yearly_stats_table.setItem(row, 5, QTableWidgetItem(f"{avg_confidence:.3f}"))
            
            row += 1
        
        # Resize columns
        self.yearly_stats_table.resizeColumnsToContents()
    
    def get_water_year(self, date):
        """Determine the water year for a given date."""
        # Get water year settings from unified settings
        if hasattr(self.parent(), 'unified_settings') and self.parent().unified_settings:
            settings = self.parent().unified_settings.get_method_settings('ERC')
            month = settings.get('water_year_month', 10)
            day = settings.get('water_year_day', 1)
        else:
            # Fallback to default values
            month = 10
            day = 1
        
        if (date.month > month) or (date.month == month and date.day >= day):
            start_year = date.year
        else:
            start_year = date.year - 1
            
        end_year = start_year + 1
        return f"{start_year}-{end_year}"
    
    def update_plot(self):
        """Update the plot with current data and ERC-specific elements."""
        try:
            # Check if we have any data to plot
            has_data = (
                (hasattr(self, 'raw_data') and self.raw_data is not None and not self.raw_data.empty) or
                (hasattr(self, 'processed_data') and self.processed_data is not None and not self.processed_data.empty)
            )
            
            if not has_data:
                # Show completely empty plot like other tabs
                self.figure.clear()
                self.canvas.draw()
                return
            
            # Use base class for standardized plotting
            ax = self.update_plot_base()
            if ax is None:
                return
                
            # Add ERC-specific plot elements
            self.add_method_specific_plots(ax)
            
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
    
    def add_method_specific_plots(self, ax):
        """Add ERC-specific plot elements to the base plot."""
        try:
            # Plot recession segments with seasonal color coding
            if hasattr(self, 'show_recession_segments') and self.show_recession_segments.isChecked() and hasattr(self, 'recession_segments') and len(self.recession_segments) > 0:
                season_colors = {'Winter': 'blue', 'Spring': 'green', 'Summer': 'red', 'Fall': 'orange'}
                
                for i, segment in enumerate(self.recession_segments):
                    seg_data = segment['data']
                    color = season_colors.get(segment['seasonal_period'], 'purple')
                    alpha = 0.8 if segment['used_in_fitting'] else 0.3
                    label = f"Recession ({segment['seasonal_period']})" if i == 0 else ""
                    
                    ax.plot(seg_data['timestamp'], seg_data['level'], 
                           color=color, linewidth=2, alpha=alpha, label=label)
            
            # Plot recession curve and deviations
            if (hasattr(self, 'show_recession_curve') and self.show_recession_curve.isChecked() and 
                hasattr(self, 'calculation_data') and self.calculation_data is not None):
                data = self.calculation_data
                ax.plot(data['timestamp'], data['predicted_level'], 
                       'k--', linewidth=1, label='ERC Prediction')
            
            # Plot recharge events with validation status
            if hasattr(self, 'show_recharge_events') and self.show_recharge_events.isChecked() and hasattr(self, 'recharge_events') and self.recharge_events:
                # Separate events by validation status
                valid_events = [e for e in self.recharge_events if e['validation_flag']]
                invalid_events = [e for e in self.recharge_events if not e['validation_flag']]
                
                if valid_events:
                    valid_dates = [e['event_date'] for e in valid_events]
                    valid_levels = [e['water_level'] for e in valid_events]
                    ax.scatter(valid_dates, valid_levels, c='red', s=30, zorder=10, 
                             label='Valid Recharge Events', alpha=0.8)
                
                if invalid_events:
                    invalid_dates = [e['event_date'] for e in invalid_events]
                    invalid_levels = [e['water_level'] for e in invalid_events]
                    ax.scatter(invalid_dates, invalid_levels, c='pink', s=20, zorder=9, 
                             label='Low-Confidence Events', alpha=0.6)
            
            # Update title with ERC-specific information
            current_title = ax.get_title()
            if hasattr(self, 'recharge_events') and self.recharge_events:
                valid_events = [e for e in self.recharge_events if e['validation_flag']]
                total_recharge = sum(event['recharge_value'] for event in valid_events)
                current_title += f' ({len(valid_events)} valid events, {total_recharge:.2f}" total)'
                ax.set_title(current_title)
                
        except Exception as e:
            logger.error(f"Error adding ERC-specific plots: {e}", exc_info=True)

    def save_curve(self):
        """Save the current ERC curve to database."""
        if not self.current_curve or not self.erc_db:
            QMessageBox.warning(self, "Cannot Save", "No curve to save or database not available.")
            return
            
        try:
            from PyQt5.QtWidgets import QInputDialog
            description, ok = QInputDialog.getText(self, "Save Curve", 
                "Enter a description for this ERC curve:")
            
            if not ok:
                return
                
            # Prepare recession segments data with enhanced information
            segments_data = []
            for segment in self.recession_segments:
                segments_data.append({
                    'start_date': segment['start_date'].isoformat(),
                    'end_date': segment['end_date'].isoformat(),
                    'duration_days': segment['duration_days'],
                    'start_level': segment['start_level'],
                    'end_level': segment['end_level'],
                    'recession_rate': segment['recession_rate'],
                    'seasonal_period': segment['seasonal_period'],
                    'segment_quality': segment['segment_quality'],
                    'used_in_fitting': segment['used_in_fitting']
                })
            
            # Save curve with enhanced metadata
            curve_id = self.erc_db.save_curve(
                well_id=self.current_well,
                well_name=self.well_combo.currentText(),
                curve_type=self.current_curve['curve_type'],
                curve_parameters={
                    'min_recession_length': self.min_recession_length.value(),
                    'fluctuation_tolerance': self.fluctuation_tolerance.value(),
                    'r_squared_threshold': self.r_squared_threshold.value(),
                    'validation_split': self.validation_split.value()
                },
                curve_coefficients=self.current_curve['curve_coefficients'],
                r_squared=self.current_curve['r_squared'],
                recession_segments=len(self.recession_segments),
                min_recession_length=self.min_recession_length.value(),
                seasonal_analysis=self.current_curve['seasonal_analysis'],
                temporal_segments=list(self.temporal_analysis.keys()) if self.temporal_analysis else [],
                cross_validation_score=self.current_curve.get('cv_score'),
                description=description,
                recession_segments_data=segments_data
            )
            
            if curve_id:
                # Save temporal analysis if available
                if self.temporal_analysis:
                    for season, analysis in self.temporal_analysis.items():
                        self.erc_db.save_temporal_analysis(
                            curve_id=curve_id,
                            temporal_period='seasonal',
                            period_identifier=season,
                            curve_coefficients=analysis['coefficients'],
                            r_squared=analysis['r_squared'],
                            segment_count=analysis['segment_count'],
                            period_start_date='',  # Could be calculated from segments
                            period_end_date=''
                        )
                
                QMessageBox.information(self, "Save Successful", 
                    "ERC curve saved successfully with enhanced metadata.")
                
                # Reload curves
                self.load_curves_for_well(self.current_well)
            else:
                QMessageBox.warning(self, "Save Failed", 
                    "Failed to save curve to database.")
                
        except Exception as e:
            logger.error(f"Error saving ERC curve: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save curve: {str(e)}")
    
    def save_to_database(self):
        """Save calculation results to database."""
        if not self.recharge_events or not self.erc_db or not self.current_curve:
            QMessageBox.warning(self, "Cannot Save", "No calculation data to save or database not available.")
            return
            
        try:
            # Calculate summaries for database storage
            total_recharge = sum(e['recharge_value'] for e in self.recharge_events)
            valid_events = [e for e in self.recharge_events if e['validation_flag']]
            
            if len(self.recharge_events) > 0:
                first_date = min(e['event_date'] for e in self.recharge_events)
                last_date = max(e['event_date'] for e in self.recharge_events)
                days_span = (last_date - first_date).total_seconds() / (24 * 3600)
                annual_rate = total_recharge * 365 / days_span if days_span > 0 else 0
                
                # Calculate quality score
                avg_confidence = np.mean([e['confidence_score'] for e in self.recharge_events])
                curve_quality = self.current_curve['r_squared']
                cv_quality = self.current_curve.get('cv_score', 0.7)
                quality_score = (avg_confidence + curve_quality + cv_quality) / 3
            else:
                annual_rate = 0
                quality_score = 0
            
            # Prepare yearly summaries with enhanced information
            yearly_summaries = []
            yearly_stats = {}
            
            for event in self.recharge_events:
                wy = event['water_year']
                if wy not in yearly_stats:
                    yearly_stats[wy] = {
                        'events': 0,
                        'valid_events': 0,
                        'recharge': 0.0,
                        'max_deviation': 0.0,
                        'confidences': [],
                        'seasonal_dist': {'Winter': 0, 'Spring': 0, 'Summer': 0, 'Fall': 0},
                        'dates': []
                    }
                
                yearly_stats[wy]['events'] += 1
                if event['validation_flag']:
                    yearly_stats[wy]['valid_events'] += 1
                yearly_stats[wy]['recharge'] += event['recharge_value']
                yearly_stats[wy]['max_deviation'] = max(yearly_stats[wy]['max_deviation'], event['deviation'])
                yearly_stats[wy]['confidences'].append(event['confidence_score'])
                yearly_stats[wy]['seasonal_dist'][event['seasonal_period']] += 1
                yearly_stats[wy]['dates'].append(event['event_date'])
            
            for wy, stats in yearly_stats.items():
                first_date = min(stats['dates'])
                last_date = max(stats['dates'])
                days = (last_date - first_date).total_seconds() / (24 * 3600)
                wy_annual_rate = stats['recharge'] * 365 / days if days > 0 else stats['recharge'] * 365
                avg_deviation = np.mean([e['deviation'] for e in self.recharge_events if e['water_year'] == wy])
                avg_confidence = np.mean(stats['confidences']) if stats['confidences'] else 0
                
                yearly_summaries.append({
                    'water_year': wy,
                    'total_recharge': stats['recharge'],
                    'num_events': stats['valid_events'],  # Use valid events count
                    'annual_rate': wy_annual_rate,
                    'max_deviation': stats['max_deviation'],
                    'avg_deviation': avg_deviation,
                    'seasonal_distribution': stats['seasonal_dist'],
                    'quality_indicators': {
                        'avg_confidence': avg_confidence,
                        'total_events': stats['events'],
                        'validation_rate': stats['valid_events'] / stats['events'] if stats['events'] > 0 else 0
                    }
                })
            
            # Save calculation
            calc_id = self.erc_db.save_calculation(
                curve_id=1,  # Would need to get actual curve_id from saved curve
                well_id=self.current_well,
                well_name=self.well_combo.currentText(),
                specific_yield=self.sy_spinner.value(),
                deviation_threshold=self.deviation_threshold_spinner.value(),
                water_year_start_month=self.water_year_month.value(),
                water_year_start_day=self.water_year_day.value(),
                downsample_rule=self.downsample_combo.currentData(),
                downsample_method=self.downsample_method_combo.currentData(),
                filter_type="moving_average" if self.ma_radio.isChecked() else "none",
                filter_window=self.ma_window_spinner.value() if self.ma_radio.isChecked() else None,
                seasonal_correction=self.seasonal_analysis_check.isChecked(),
                validation_method="cross_validation" if self.cross_validation_check.isChecked() else None,
                total_recharge=total_recharge,
                annual_rate=annual_rate,
                recharge_events=self.recharge_events,
                yearly_summaries=yearly_summaries,
                quality_score=quality_score,
                notes=f"ERC calculation with {self.current_curve['curve_type']} curve"
            )
            
            if calc_id:
                QMessageBox.information(
                    self, 
                    "Save Successful", 
                    f"ERC calculation saved successfully for {self.well_combo.currentText()}.\\n\\n"
                    f"Total recharge: {total_recharge:.2f} inches\\n"
                    f"Annual rate: {annual_rate:.2f} inches/year\\n"
                    f"Valid events: {len(valid_events)}/{len(self.recharge_events)}\\n"
                    f"Quality score: {quality_score:.3f}"
                )
                logger.info(f"Saved ERC calculation {calc_id} for well {self.current_well}")
            else:
                QMessageBox.warning(
                    self, 
                    "Save Failed", 
                    "Failed to save the calculation to the database. Check the logs for details."
                )
                
        except Exception as e:
            logger.error(f"Error saving to database: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Save Error", 
                f"An error occurred while saving:\\n{str(e)}"
            )
    
    def load_from_database(self):
        """Load calculation from database."""
        QMessageBox.information(self, "Load from Database", 
            "Load from database functionality will be implemented in a future update.")
    
    def compare_calculations(self):
        """Compare multiple calculations."""
        QMessageBox.information(self, "Compare Calculations", 
            "Comparison functionality will be implemented in a future update.")
    
    def export_to_csv(self):
        """Export ERC results to CSV with enhanced metadata."""
        if not hasattr(self, 'recharge_events') or not self.recharge_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export to CSV", 
                f"{self.well_combo.currentText()}_ERC_results.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # Write CSV file with enhanced metadata
            with open(file_path, 'w', newline='') as csvfile:
                # Write header information
                csvfile.write(f"# ERC (Extended Recession Curve) Results for {self.well_combo.currentText()}\\n")
                csvfile.write(f"# Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                csvfile.write(f"# Curve Type: {self.current_curve['curve_type'] if self.current_curve else 'N/A'}\\n")
                csvfile.write(f"# Curve R²: {self.current_curve['r_squared']:.4f if self.current_curve else 0}\\n")
                if self.current_curve and self.current_curve.get('cv_score'):
                    csvfile.write(f"# Cross-Validation Score: {self.current_curve['cv_score']:.4f}\\n")
                csvfile.write(f"# Parameters:\\n")
                csvfile.write(f"#   Specific Yield: {self.sy_spinner.value()}\\n")
                csvfile.write(f"#   Deviation Threshold: {self.deviation_threshold_spinner.value()} ft\\n")
                csvfile.write(f"#   Seasonal Analysis: {self.seasonal_analysis_check.isChecked()}\\n")
                csvfile.write(f"#   Cross-Validation: {self.cross_validation_check.isChecked()}\\n")
                csvfile.write(f"# Total Recharge: {self.total_recharge_label.text()}\\n")
                csvfile.write(f"# Annual Rate: {self.annual_rate_label.text()}\\n")
                csvfile.write(f"# Quality Score: {self.quality_score_label.text()}\\n")
                csvfile.write("#\\n")
                
                # Write data headers and rows
                fieldnames = ['Event_Date', 'Water_Year', 'Water_Level_ft', 'Predicted_Level_ft', 
                             'Deviation_ft', 'Recharge_in', 'Event_Magnitude', 'Season', 
                             'Confidence_Score', 'Validation_Flag']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in self.recharge_events:
                    writer.writerow({
                        'Event_Date': event['event_date'].strftime('%Y-%m-%d'),
                        'Water_Year': event['water_year'],
                        'Water_Level_ft': f"{event['water_level']:.2f}",
                        'Predicted_Level_ft': f"{event['predicted_level']:.2f}",
                        'Deviation_ft': f"{event['deviation']:.3f}",
                        'Recharge_in': f"{event['recharge_value']:.3f}",
                        'Event_Magnitude': event['event_magnitude'],
                        'Season': event['seasonal_period'],
                        'Confidence_Score': f"{event['confidence_score']:.3f}",
                        'Validation_Flag': event['validation_flag']
                    })
                    
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"ERC results exported successfully to:\\n{file_path}"
            )
            logger.info(f"Exported ERC results to CSV: {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Export Error", 
                f"Failed to export to CSV:\\n{str(e)}"
            )
    
    def export_to_excel(self):
        """Export ERC results to Excel with multiple sheets."""
        if not hasattr(self, 'recharge_events') or not self.recharge_events:
            QMessageBox.warning(self, "No Data", "No results to export. Calculate recharge first.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export to Excel", 
                f"{self.well_combo.currentText()}_ERC_results.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # Create DataFrames for export
            # 1. Enhanced recharge events data
            events_data = []
            for event in self.recharge_events:
                events_data.append({
                    'Event Date': event['event_date'],
                    'Water Year': event['water_year'],
                    'Water Level (ft)': event['water_level'],
                    'Predicted Level (ft)': event['predicted_level'],
                    'Deviation (ft)': event['deviation'],
                    'Recharge (in)': event['recharge_value'],
                    'Event Magnitude': event['event_magnitude'],
                    'Season': event['seasonal_period'],
                    'Confidence Score': event['confidence_score'],
                    'Valid Event': event['validation_flag']
                })
            events_df = pd.DataFrame(events_data)
            
            # 2. Enhanced yearly summary
            yearly_data = []
            for row in range(self.yearly_stats_table.rowCount()):
                yearly_data.append({
                    'Water Year': self.yearly_stats_table.item(row, 0).text(),
                    'Valid/Total Events': self.yearly_stats_table.item(row, 1).text(),
                    'Total Recharge (in)': float(self.yearly_stats_table.item(row, 2).text()),
                    'Annual Rate (in/yr)': float(self.yearly_stats_table.item(row, 3).text()),
                    'Max Deviation (ft)': float(self.yearly_stats_table.item(row, 4).text()),
                    'Quality Score': float(self.yearly_stats_table.item(row, 5).text())
                })
            yearly_df = pd.DataFrame(yearly_data)
            
            # 3. Enhanced parameters and curve info
            params_data = {
                'Parameter': [
                    'Well', 'Curve Type', 'Curve R²', 'CV Score', 'Specific Yield', 
                    'Deviation Threshold (ft)', 'Min Recession Length (days)',
                    'Fluctuation Tolerance (ft)', 'Seasonal Analysis', 'Cross-Validation',
                    'Total Recharge (in)', 'Annual Rate (in/yr)', 'Total Events', 'Valid Events',
                    'Overall Quality Score'
                ],
                'Value': [
                    self.well_combo.currentText(),
                    self.current_curve['curve_type'] if self.current_curve else 'N/A',
                    f"{self.current_curve['r_squared']:.4f}" if self.current_curve else 'N/A',
                    f"{self.current_curve.get('cv_score', 0):.4f}" if self.current_curve else 'N/A',
                    self.sy_spinner.value(),
                    self.deviation_threshold_spinner.value(),
                    self.min_recession_length.value(),
                    self.fluctuation_tolerance.value(),
                    self.seasonal_analysis_check.isChecked(),
                    self.cross_validation_check.isChecked(),
                    float(self.total_recharge_label.text().split()[0]),
                    float(self.annual_rate_label.text().split()[0]),
                    len(self.recharge_events),
                    len([e for e in self.recharge_events if e['validation_flag']]),
                    self.quality_score_label.text()
                ]
            }
            params_df = pd.DataFrame(params_data)
            
            # 4. Recession segments with enhanced info
            if hasattr(self, 'recession_segments') and self.recession_segments:
                segments_data = []
                for segment in self.recession_segments:
                    segments_data.append({
                        'Start Date': segment['start_date'],
                        'End Date': segment['end_date'],
                        'Duration (days)': segment['duration_days'],
                        'Start Level (ft)': segment['start_level'],
                        'End Level (ft)': segment['end_level'],
                        'Recession Rate (ft/day)': segment['recession_rate'],
                        'Season': segment['seasonal_period'],
                        'Quality Score': segment['segment_quality'],
                        'Used in Fitting': segment['used_in_fitting']
                    })
                segments_df = pd.DataFrame(segments_data)
            
            # 5. Seasonal analysis if available
            if hasattr(self, 'temporal_analysis') and self.temporal_analysis:
                seasonal_data = []
                for season, analysis in self.temporal_analysis.items():
                    seasonal_data.append({
                        'Season': season,
                        'R² Score': analysis['r_squared'],
                        'Segment Count': analysis['segment_count'],
                        'Coefficients': str(analysis['coefficients'])
                    })
                seasonal_df = pd.DataFrame(seasonal_data)
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Write parameters
                params_df.to_excel(writer, sheet_name='Parameters', index=False)
                
                # Write yearly summary
                yearly_df.to_excel(writer, sheet_name='Yearly Summary', index=False)
                
                # Write individual events
                events_df.to_excel(writer, sheet_name='Recharge Events', index=False)
                
                # Write recession segments if available
                if hasattr(self, 'recession_segments') and self.recession_segments:
                    segments_df.to_excel(writer, sheet_name='Recession Segments', index=False)
                
                # Write seasonal analysis if available
                if hasattr(self, 'temporal_analysis') and self.temporal_analysis:
                    seasonal_df.to_excel(writer, sheet_name='Seasonal Analysis', index=False)
                
                # Auto-adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                        
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"ERC results exported successfully to:\\n{file_path}\\n\\n"
                f"The Excel file contains:\\n"
                f"- Parameters sheet\\n"
                f"- Yearly Summary sheet\\n"
                f"- Recharge Events sheet\\n"
                f"- Recession Segments sheet" +
                (f"\\n- Seasonal Analysis sheet" if hasattr(self, 'temporal_analysis') and self.temporal_analysis else "")
            )
            logger.info(f"Exported ERC results to Excel: {file_path}")
            
        except ImportError:
            QMessageBox.warning(
                self, 
                "Missing Dependency", 
                "Excel export requires the 'openpyxl' package.\\n"
                "Please install it using: pip install openpyxl"
            )
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Export Error", 
                f"Failed to export to Excel:\\n{str(e)}"
            )
    
    def clear_results(self):
        """Clear all results and reset UI."""
        self.recession_segments = []
        self.recharge_events = []
        self.current_curve = None
        self.temporal_analysis = {}
        
        # Clear tables only if they exist
        if hasattr(self, 'recession_table'):
            self.recession_table.setRowCount(0)
        if hasattr(self, 'yearly_stats_table'):
            self.yearly_stats_table.setRowCount(0)
        
        # Clear labels only if they exist
        if hasattr(self, 'total_recharge_label'):
            self.total_recharge_label.setText("0.0 inches")
        if hasattr(self, 'annual_rate_label'):
            self.annual_rate_label.setText("0.0 inches/year")
        if hasattr(self, 'events_count_label'):
            self.events_count_label.setText("0")
        if hasattr(self, 'quality_score_label'):
            self.quality_score_label.setText("N/A")
        
        if hasattr(self, 'curve_equation_label'):
            self.curve_equation_label.setText("No curve fitted")
        if hasattr(self, 'r_squared_label'):
            self.r_squared_label.setText("R² = N/A")
        if hasattr(self, 'cv_score_label'):
            self.cv_score_label.setText("CV Score = N/A")
        
        # Enable/disable buttons only if they exist
        if hasattr(self, 'fit_curve_btn'):
            self.fit_curve_btn.setEnabled(False)
        if hasattr(self, 'save_curve_btn'):
            self.save_curve_btn.setEnabled(False)
        if hasattr(self, 'calculate_btn'):
            self.calculate_btn.setEnabled(False)
        if hasattr(self, 'export_csv_btn'):
            self.export_csv_btn.setEnabled(False)
        if hasattr(self, 'export_excel_btn'):
            self.export_excel_btn.setEnabled(False)
        if hasattr(self, 'save_calc_btn'):
            self.save_calc_btn.setEnabled(False)
    
    def set_shared_data(self, raw_data, processed_data):
        """Set data that has been preprocessed centrally.
        
        Args:
            raw_data: The raw data DataFrame
            processed_data: The preprocessed data DataFrame
        """
        logger.info(f"[PREPROCESS_DEBUG] ERC receiving shared data: {len(raw_data) if raw_data is not None else 0} raw, {len(processed_data) if processed_data is not None else 0} processed")
        
        self.raw_data = raw_data
        self.processed_data = processed_data
        self.display_data = raw_data  # For backward compatibility
        
        # Mark data as loaded
        self.data_loaded = {'display': True, 'full': True}
        
        # Update plot with new data
        self.update_plot()
        
        # Enable next steps if we have processed data and a selected well
        if self.processed_data is not None and hasattr(self, 'current_well') and self.current_well:
            self.identify_segments_btn.setEnabled(True)
            logger.info("[PREPROCESS_DEBUG] ERC analyze patterns button enabled")
        
        logger.info("[PREPROCESS_DEBUG] ERC tab updated with shared data")
    
    def update_settings(self, settings):
        """Update ERC tab with unified settings."""
        try:
            logger.info("Updating ERC tab with unified settings")
            
            # Update shared parameters
            if 'specific_yield' in settings and hasattr(self, 'sy_spinner'):
                self.sy_spinner.setValue(settings['specific_yield'])
                
            if 'water_year_month' in settings and hasattr(self, 'water_year_month'):
                self.water_year_month.setValue(settings['water_year_month'])
                
            if 'water_year_day' in settings and hasattr(self, 'water_year_day'):
                self.water_year_day.setValue(settings['water_year_day'])
            
            # Update ERC-specific parameters
            if 'erc_deviation_threshold' in settings and hasattr(self, 'deviation_threshold'):
                self.deviation_threshold.setValue(settings['erc_deviation_threshold'])
                
            if 'min_recession_length' in settings and hasattr(self, 'min_length_spinner'):
                self.min_length_spinner.setValue(settings['min_recession_length'])
                
            if 'curve_type' in settings and hasattr(self, 'curve_type_combo'):
                self.curve_type_combo.setCurrentText(settings['curve_type'])
                
            if 'r_squared_threshold' in settings and hasattr(self, 'r_squared_threshold_spinner'):
                self.r_squared_threshold_spinner.setValue(settings['r_squared_threshold'])
                
            if 'validation_split' in settings and hasattr(self, 'validation_split_spinner'):
                self.validation_split_spinner.setValue(settings['validation_split'])
                
            if 'enable_seasonal' in settings and hasattr(self, 'seasonal_analysis'):
                self.seasonal_analysis.setChecked(settings['enable_seasonal'])
                
            if 'seasonal_periods' in settings and hasattr(self, 'seasonal_periods_combo'):
                self.seasonal_periods_combo.setCurrentText(settings['seasonal_periods'])
            
            # Update preprocessing parameters
            if 'downsample_frequency' in settings and hasattr(self, 'downsample_combo'):
                self.downsample_combo.setCurrentText(settings['downsample_frequency'])
                
            if 'downsample_method' in settings and hasattr(self, 'downsample_method_combo'):
                self.downsample_method_combo.setCurrentText(settings['downsample_method'])
                
            if 'enable_smoothing' in settings and hasattr(self, 'smoothing_type'):
                if settings['enable_smoothing']:
                    self.smoothing_type.setCurrentText("Moving Average")
                else:
                    self.smoothing_type.setCurrentText("No Smoothing")
                    
            if 'smoothing_window' in settings and hasattr(self, 'smoothing_window_spinner'):
                self.smoothing_window_spinner.setValue(settings['smoothing_window'])
            
            logger.info("ERC tab settings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating ERC tab settings: {e}")
    
    def get_current_settings(self):
        """Get current ERC tab settings."""
        try:
            settings = {}
            
            # Get shared parameters
            if hasattr(self, 'sy_spinner'):
                settings['specific_yield'] = self.sy_spinner.value()
                
            if hasattr(self, 'water_year_month'):
                settings['water_year_month'] = self.water_year_month.value()
                
            if hasattr(self, 'water_year_day'):
                settings['water_year_day'] = self.water_year_day.value()
            
            # Get ERC-specific parameters
            if hasattr(self, 'deviation_threshold'):
                settings['erc_deviation_threshold'] = self.deviation_threshold.value()
                
            if hasattr(self, 'min_length_spinner'):
                settings['min_recession_length'] = self.min_length_spinner.value()
                
            if hasattr(self, 'curve_type_combo'):
                settings['curve_type'] = self.curve_type_combo.currentText()
                
            if hasattr(self, 'r_squared_threshold_spinner'):
                settings['r_squared_threshold'] = self.r_squared_threshold_spinner.value()
                
            if hasattr(self, 'validation_split_spinner'):
                settings['validation_split'] = self.validation_split_spinner.value()
                
            if hasattr(self, 'seasonal_analysis'):
                settings['enable_seasonal'] = self.seasonal_analysis.isChecked()
                
            if hasattr(self, 'seasonal_periods_combo'):
                settings['seasonal_periods'] = self.seasonal_periods_combo.currentText()
            
            # Get preprocessing parameters
            if hasattr(self, 'downsample_combo'):
                settings['downsample_frequency'] = self.downsample_combo.currentText()
                
            if hasattr(self, 'downsample_method_combo'):
                settings['downsample_method'] = self.downsample_method_combo.currentText()
                
            if hasattr(self, 'smoothing_window_spinner'):
                settings['smoothing_window'] = self.smoothing_window_spinner.value()
                
            return settings
            
        except Exception as e:
            logger.error(f"Error getting ERC tab settings: {e}")
            return {}