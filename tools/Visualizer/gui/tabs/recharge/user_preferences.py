"""
User Preferences System for Recharge Analysis.
Provides a comprehensive interface for managing user preferences,
interface modes, and application behavior customization.
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QSlider,
    QTabWidget, QWidget, QMessageBox, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QSplitter, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette
import json
from datetime import datetime

from .settings_persistence import SettingsPersistence

logger = logging.getLogger(__name__)


class UserPreferencesDialog(QDialog):
    """
    Comprehensive user preferences dialog for recharge analysis system.
    """
    
    # Signals for preference changes
    preferences_changed = pyqtSignal(dict)
    interface_mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.settings_persistence = SettingsPersistence()
        
        # Current preferences
        self.preferences = self._load_default_preferences()
        
        self.setWindowTitle("User Preferences")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.load_preferences()
        
    def _load_default_preferences(self):
        """Load default preferences."""
        return {
            # Interface preferences
            'interface_mode': 'tabs',  # 'tabs', 'launcher', 'mixed'
            'default_method': 'RISE',
            'show_launcher_button': True,
            'auto_open_methods_in_new_window': False,
            'remember_window_positions': True,
            
            # Analysis preferences
            'auto_apply_unified_settings': True,
            'save_settings_on_change': True,
            'auto_save_sessions': True,
            'show_calculation_progress': True,
            'enable_method_recommendations': True,
            
            # Visualization preferences
            'default_plot_style': 'professional',
            'show_grid_by_default': True,
            'default_plot_colors': 'standard',
            'auto_format_dates': True,
            'plot_dpi': 100,
            
            # Data preferences
            'default_water_year_start': 10,  # October
            'default_specific_yield': 0.2,
            'auto_detect_data_frequency': True,
            'preferred_units': 'imperial',  # 'imperial', 'metric'
            
            # Advanced preferences
            'enable_debug_logging': False,
            'max_session_history': 50,
            'auto_backup_settings': True,
            'check_for_updates': True,
            'send_usage_statistics': False
        }
        
    def setup_ui(self):
        """Setup the preferences dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        self.create_header(layout)
        
        # Main preferences tabs
        self.create_preferences_tabs(layout)
        
        # Action buttons
        self.create_action_buttons(layout)
        
    def create_header(self, layout):
        """Create header section."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("User Preferences")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Customize your recharge analysis experience")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_frame)
        
    def create_preferences_tabs(self, layout):
        """Create tabbed preferences interface."""
        self.tabs = QTabWidget()
        
        # Interface tab
        self.create_interface_tab()
        
        # Analysis tab
        self.create_analysis_tab()
        
        # Visualization tab
        self.create_visualization_tab()
        
        # Data tab
        self.create_data_tab()
        
        # Advanced tab
        self.create_advanced_tab()
        
        layout.addWidget(self.tabs)
        
    def create_interface_tab(self):
        """Create interface preferences tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Interface mode group
        mode_group = QGroupBox("Interface Mode")
        mode_layout = QGridLayout(mode_group)
        
        mode_layout.addWidget(QLabel("Default Interface:"), 0, 0)
        self.interface_mode_combo = QComboBox()
        self.interface_mode_combo.addItems([
            ("Traditional Tabs", "tabs"),
            ("Method Launcher", "launcher"), 
            ("Mixed Mode", "mixed")
        ])
        self.interface_mode_combo.currentTextChanged.connect(self.on_interface_mode_changed)
        mode_layout.addWidget(self.interface_mode_combo, 0, 1)
        
        mode_layout.addWidget(QLabel("Default Method:"), 1, 0)
        self.default_method_combo = QComboBox()
        self.default_method_combo.addItems(["RISE", "MRC", "ERC"])
        mode_layout.addWidget(self.default_method_combo, 1, 1)
        
        # Interface options
        self.show_launcher_button_check = QCheckBox("Show launcher button in tab interface")
        self.auto_new_window_check = QCheckBox("Open methods in new windows by default")
        self.remember_positions_check = QCheckBox("Remember window positions")
        
        mode_layout.addWidget(self.show_launcher_button_check, 2, 0, 1, 2)
        mode_layout.addWidget(self.auto_new_window_check, 3, 0, 1, 2)
        mode_layout.addWidget(self.remember_positions_check, 4, 0, 1, 2)
        
        layout.addWidget(mode_group)
        
        # Interface description
        self.interface_description = QLabel()
        self.interface_description.setWordWrap(True)
        self.interface_description.setStyleSheet("""
            QLabel {
                background-color: #e7f3ff;
                border: 1px solid #bee5eb;
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(self.interface_description)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Interface")
        
    def create_analysis_tab(self):
        """Create analysis preferences tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Settings management
        settings_group = QGroupBox("Settings Management")
        settings_layout = QGridLayout(settings_group)
        
        self.auto_unified_settings_check = QCheckBox("Automatically apply unified settings to new methods")
        self.save_on_change_check = QCheckBox("Save settings automatically when changed")
        self.auto_save_sessions_check = QCheckBox("Automatically save analysis sessions")
        
        settings_layout.addWidget(self.auto_unified_settings_check, 0, 0, 1, 2)
        settings_layout.addWidget(self.save_on_change_check, 1, 0, 1, 2)
        settings_layout.addWidget(self.auto_save_sessions_check, 2, 0, 1, 2)
        
        layout.addWidget(settings_group)
        
        # Calculation preferences
        calc_group = QGroupBox("Calculation Preferences")
        calc_layout = QGridLayout(calc_group)
        
        self.show_progress_check = QCheckBox("Show calculation progress dialogs")
        self.enable_recommendations_check = QCheckBox("Enable method recommendations")
        
        calc_layout.addWidget(self.show_progress_check, 0, 0, 1, 2)
        calc_layout.addWidget(self.enable_recommendations_check, 1, 0, 1, 2)
        
        layout.addWidget(calc_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Analysis")
        
    def create_visualization_tab(self):
        """Create visualization preferences tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Plot style
        style_group = QGroupBox("Plot Style")
        style_layout = QGridLayout(style_group)
        
        style_layout.addWidget(QLabel("Default Style:"), 0, 0)
        self.plot_style_combo = QComboBox()
        self.plot_style_combo.addItems([
            "Professional", "Scientific", "Publication", "Presentation"
        ])
        style_layout.addWidget(self.plot_style_combo, 0, 1)
        
        style_layout.addWidget(QLabel("Color Scheme:"), 1, 0)
        self.color_scheme_combo = QComboBox()
        self.color_scheme_combo.addItems([
            "Standard", "High Contrast", "Colorblind Friendly", "Grayscale"
        ])
        style_layout.addWidget(self.color_scheme_combo, 1, 1)
        
        self.show_grid_check = QCheckBox("Show grid by default")
        self.auto_format_dates_check = QCheckBox("Auto-format date axes")
        
        style_layout.addWidget(self.show_grid_check, 2, 0, 1, 2)
        style_layout.addWidget(self.auto_format_dates_check, 3, 0, 1, 2)
        
        # Plot DPI
        style_layout.addWidget(QLabel("Plot Resolution (DPI):"), 4, 0)
        self.plot_dpi_spin = QSpinBox()
        self.plot_dpi_spin.setRange(50, 300)
        self.plot_dpi_spin.setValue(100)
        style_layout.addWidget(self.plot_dpi_spin, 4, 1)
        
        layout.addWidget(style_group)
        layout.addStretch()
        self.tabs.addTab(tab, "Visualization")
        
    def create_data_tab(self):
        """Create data preferences tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Default values
        defaults_group = QGroupBox("Default Values")
        defaults_layout = QGridLayout(defaults_group)
        
        defaults_layout.addWidget(QLabel("Water Year Start Month:"), 0, 0)
        self.water_year_combo = QComboBox()
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        self.water_year_combo.addItems(months)
        self.water_year_combo.setCurrentIndex(9)  # October
        defaults_layout.addWidget(self.water_year_combo, 0, 1)
        
        defaults_layout.addWidget(QLabel("Default Specific Yield:"), 1, 0)
        self.specific_yield_spin = QDoubleSpinBox()
        self.specific_yield_spin.setRange(0.01, 0.99)
        self.specific_yield_spin.setDecimals(3)
        self.specific_yield_spin.setSingleStep(0.01)
        self.specific_yield_spin.setValue(0.200)
        defaults_layout.addWidget(self.specific_yield_spin, 1, 1)
        
        defaults_layout.addWidget(QLabel("Preferred Units:"), 2, 0)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["Imperial (feet, inches)", "Metric (meters, mm)"])
        defaults_layout.addWidget(self.units_combo, 2, 1)
        
        self.auto_detect_frequency_check = QCheckBox("Auto-detect data frequency")
        defaults_layout.addWidget(self.auto_detect_frequency_check, 3, 0, 1, 2)
        
        layout.addWidget(defaults_group)
        layout.addStretch()
        self.tabs.addTab(tab, "Data")
        
    def create_advanced_tab(self):
        """Create advanced preferences tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # System preferences
        system_group = QGroupBox("System")
        system_layout = QGridLayout(system_group)
        
        self.debug_logging_check = QCheckBox("Enable debug logging")
        self.auto_backup_check = QCheckBox("Automatically backup settings")
        self.check_updates_check = QCheckBox("Check for application updates")
        self.usage_stats_check = QCheckBox("Send anonymous usage statistics")
        
        system_layout.addWidget(self.debug_logging_check, 0, 0, 1, 2)
        system_layout.addWidget(self.auto_backup_check, 1, 0, 1, 2)
        system_layout.addWidget(self.check_updates_check, 2, 0, 1, 2)
        system_layout.addWidget(self.usage_stats_check, 3, 0, 1, 2)
        
        system_layout.addWidget(QLabel("Max Session History:"), 4, 0)
        self.max_sessions_spin = QSpinBox()
        self.max_sessions_spin.setRange(10, 200)
        self.max_sessions_spin.setValue(50)
        system_layout.addWidget(self.max_sessions_spin, 4, 1)
        
        layout.addWidget(system_group)
        
        # Import/Export section
        import_export_group = QGroupBox("Settings Import/Export")
        import_export_layout = QHBoxLayout(import_export_group)
        
        export_btn = QPushButton("Export Settings...")
        export_btn.clicked.connect(self.export_settings)
        import_btn = QPushButton("Import Settings...")
        import_btn.clicked.connect(self.import_settings)
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        
        import_export_layout.addWidget(export_btn)
        import_export_layout.addWidget(import_btn)
        import_export_layout.addWidget(reset_btn)
        
        layout.addWidget(import_export_group)
        layout.addStretch()
        self.tabs.addTab(tab, "Advanced")
        
    def create_action_buttons(self, layout):
        """Create action buttons."""
        button_layout = QHBoxLayout()
        
        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_preferences)
        
        # OK button
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_preferences)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def on_interface_mode_changed(self):
        """Update interface description when mode changes."""
        mode = self.interface_mode_combo.currentData() or self.interface_mode_combo.currentText().lower()
        
        descriptions = {
            'tabs': "Traditional tabbed interface with all methods in one window. Familiar and space-efficient.",
            'launcher': "Card-based method launcher for selecting and opening methods in separate windows. Modern and flexible.",
            'mixed': "Combination of tabs and launcher - tabs are default with launcher available as option."
        }
        
        self.interface_description.setText(descriptions.get(mode, ""))
        
    def load_preferences(self):
        """Load preferences from persistence layer."""
        try:
            # Load each preference from database
            for key, default_value in self.preferences.items():
                value = self.settings_persistence.get_user_preference(key, default_value)
                self.preferences[key] = value
                
            # Update UI controls
            self._update_ui_from_preferences()
            
        except Exception as e:
            logger.error(f"Error loading preferences: {e}")
            QMessageBox.warning(self, "Load Error", f"Failed to load preferences: {str(e)}")
            
    def _update_ui_from_preferences(self):
        """Update UI controls from current preferences."""
        # Interface tab
        interface_mode = self.preferences.get('interface_mode', 'tabs')
        for i in range(self.interface_mode_combo.count()):
            if self.interface_mode_combo.itemData(i) == interface_mode:
                self.interface_mode_combo.setCurrentIndex(i)
                break
                
        default_method = self.preferences.get('default_method', 'RISE')
        self.default_method_combo.setCurrentText(default_method)
        
        self.show_launcher_button_check.setChecked(self.preferences.get('show_launcher_button', True))
        self.auto_new_window_check.setChecked(self.preferences.get('auto_open_methods_in_new_window', False))
        self.remember_positions_check.setChecked(self.preferences.get('remember_window_positions', True))
        
        # Analysis tab
        self.auto_unified_settings_check.setChecked(self.preferences.get('auto_apply_unified_settings', True))
        self.save_on_change_check.setChecked(self.preferences.get('save_settings_on_change', True))
        self.auto_save_sessions_check.setChecked(self.preferences.get('auto_save_sessions', True))
        self.show_progress_check.setChecked(self.preferences.get('show_calculation_progress', True))
        self.enable_recommendations_check.setChecked(self.preferences.get('enable_method_recommendations', True))
        
        # Visualization tab
        plot_style = self.preferences.get('default_plot_style', 'professional')
        self.plot_style_combo.setCurrentText(plot_style.title())
        
        color_scheme = self.preferences.get('default_plot_colors', 'standard')
        self.color_scheme_combo.setCurrentText(color_scheme.title())
        
        self.show_grid_check.setChecked(self.preferences.get('show_grid_by_default', True))
        self.auto_format_dates_check.setChecked(self.preferences.get('auto_format_dates', True))
        self.plot_dpi_spin.setValue(self.preferences.get('plot_dpi', 100))
        
        # Data tab
        water_year_start = self.preferences.get('default_water_year_start', 10) - 1  # Convert to 0-based
        self.water_year_combo.setCurrentIndex(water_year_start)
        self.specific_yield_spin.setValue(self.preferences.get('default_specific_yield', 0.2))
        
        units = self.preferences.get('preferred_units', 'imperial')
        self.units_combo.setCurrentIndex(0 if units == 'imperial' else 1)
        self.auto_detect_frequency_check.setChecked(self.preferences.get('auto_detect_data_frequency', True))
        
        # Advanced tab
        self.debug_logging_check.setChecked(self.preferences.get('enable_debug_logging', False))
        self.auto_backup_check.setChecked(self.preferences.get('auto_backup_settings', True))
        self.check_updates_check.setChecked(self.preferences.get('check_for_updates', True))
        self.usage_stats_check.setChecked(self.preferences.get('send_usage_statistics', False))
        self.max_sessions_spin.setValue(self.preferences.get('max_session_history', 50))
        
        # Update interface description
        self.on_interface_mode_changed()
        
    def _update_preferences_from_ui(self):
        """Update preferences from UI controls."""
        # Interface tab
        interface_mode_data = self.interface_mode_combo.currentData()
        if interface_mode_data:
            self.preferences['interface_mode'] = interface_mode_data
        else:
            # Fallback to text-based mapping
            text = self.interface_mode_combo.currentText().lower()
            if 'launcher' in text:
                self.preferences['interface_mode'] = 'launcher'
            elif 'mixed' in text:
                self.preferences['interface_mode'] = 'mixed'
            else:
                self.preferences['interface_mode'] = 'tabs'
                
        self.preferences['default_method'] = self.default_method_combo.currentText()
        self.preferences['show_launcher_button'] = self.show_launcher_button_check.isChecked()
        self.preferences['auto_open_methods_in_new_window'] = self.auto_new_window_check.isChecked()
        self.preferences['remember_window_positions'] = self.remember_positions_check.isChecked()
        
        # Analysis tab
        self.preferences['auto_apply_unified_settings'] = self.auto_unified_settings_check.isChecked()
        self.preferences['save_settings_on_change'] = self.save_on_change_check.isChecked()
        self.preferences['auto_save_sessions'] = self.auto_save_sessions_check.isChecked()
        self.preferences['show_calculation_progress'] = self.show_progress_check.isChecked()
        self.preferences['enable_method_recommendations'] = self.enable_recommendations_check.isChecked()
        
        # Visualization tab
        self.preferences['default_plot_style'] = self.plot_style_combo.currentText().lower()
        self.preferences['default_plot_colors'] = self.color_scheme_combo.currentText().lower()
        self.preferences['show_grid_by_default'] = self.show_grid_check.isChecked()
        self.preferences['auto_format_dates'] = self.auto_format_dates_check.isChecked()
        self.preferences['plot_dpi'] = self.plot_dpi_spin.value()
        
        # Data tab
        self.preferences['default_water_year_start'] = self.water_year_combo.currentIndex() + 1  # Convert to 1-based
        self.preferences['default_specific_yield'] = self.specific_yield_spin.value()
        self.preferences['preferred_units'] = 'imperial' if self.units_combo.currentIndex() == 0 else 'metric'
        self.preferences['auto_detect_data_frequency'] = self.auto_detect_frequency_check.isChecked()
        
        # Advanced tab
        self.preferences['enable_debug_logging'] = self.debug_logging_check.isChecked()
        self.preferences['auto_backup_settings'] = self.auto_backup_check.isChecked()
        self.preferences['check_for_updates'] = self.check_updates_check.isChecked()
        self.preferences['send_usage_statistics'] = self.usage_stats_check.isChecked()
        self.preferences['max_session_history'] = self.max_sessions_spin.value()
        
    def apply_preferences(self):
        """Apply current preferences."""
        try:
            # Update preferences from UI
            self._update_preferences_from_ui()
            
            # Save to persistence layer
            for key, value in self.preferences.items():
                self.settings_persistence.save_user_preference(key, value)
                
            # Emit signals for immediate application
            self.preferences_changed.emit(self.preferences.copy())
            
            # Check for interface mode change
            interface_mode = self.preferences.get('interface_mode', 'tabs')
            self.interface_mode_changed.emit(interface_mode)
            
            QMessageBox.information(self, "Preferences Applied", "Your preferences have been saved and applied.")
            
        except Exception as e:
            logger.error(f"Error applying preferences: {e}")
            QMessageBox.critical(self, "Apply Error", f"Failed to apply preferences: {str(e)}")
            
    def accept_preferences(self):
        """Accept and close dialog."""
        self.apply_preferences()
        self.accept()
        
    def export_settings(self):
        """Export all user settings."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Settings", 
                f"recharge_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                settings_data = self.settings_persistence.export_user_settings()
                
                with open(file_path, 'w') as f:
                    json.dump(settings_data, f, indent=2)
                    
                QMessageBox.information(self, "Export Complete", f"Settings exported to {file_path}")
                
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export settings: {str(e)}")
            
    def import_settings(self):
        """Import user settings."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Settings", "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'r') as f:
                    settings_data = json.load(f)
                    
                # Ask about overwriting existing settings
                reply = QMessageBox.question(
                    self, "Import Settings",
                    "Do you want to overwrite existing settings?\n\n"
                    "Yes: Replace all current settings\n"
                    "No: Only import new settings",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    return
                    
                overwrite = reply == QMessageBox.Yes
                
                self.settings_persistence.import_user_settings(settings_data, overwrite=overwrite)
                
                # Reload preferences
                self.load_preferences()
                
                QMessageBox.information(self, "Import Complete", "Settings imported successfully.")
                
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            QMessageBox.critical(self, "Import Error", f"Failed to import settings: {str(e)}")
            
    def reset_to_defaults(self):
        """Reset all preferences to defaults."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Are you sure you want to reset all preferences to default values?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Reset preferences to defaults
                self.preferences = self._load_default_preferences()
                
                # Update UI
                self._update_ui_from_preferences()
                
                QMessageBox.information(self, "Reset Complete", "All preferences have been reset to default values.")
                
            except Exception as e:
                logger.error(f"Error resetting preferences: {e}")
                QMessageBox.critical(self, "Reset Error", f"Failed to reset preferences: {str(e)}")
                
    def closeEvent(self, event):
        """Handle dialog close event."""
        try:
            self.settings_persistence.close()
            event.accept()
        except Exception as e:
            logger.error(f"Error closing preferences dialog: {e}")
            event.accept()