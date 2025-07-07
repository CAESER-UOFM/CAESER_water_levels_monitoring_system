"""
Method Launcher for Recharge Calculation Methods.
Provides a button-based interface for selecting and launching recharge calculation methods
as an alternative to the traditional tabbed interface.
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QSpacerItem, QMessageBox, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QPalette

logger = logging.getLogger(__name__)


class MethodLauncher(QDialog):
    """
    Launcher dialog for recharge calculation methods.
    Provides an alternative button-based interface to the tabbed system.
    """
    
    # Signals for method selection
    method_selected = pyqtSignal(str, dict)  # method_name, options
    comparison_requested = pyqtSignal(list, dict)  # methods_list, options
    
    def __init__(self, data_manager, parent=None, selected_wells=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent_widget = parent
        self.selected_wells = selected_wells or []
        
        self.setWindowTitle("Recharge Method Launcher")
        self.setModal(False)
        self.resize(800, 600)
        
        # Available methods configuration
        self.methods = {
            'RISE': {
                'name': 'RISE (Rise-Rate Calculation)',
                'description': 'Calculates recharge from rapid water level rises.\nBest for wells with clear recharge signals.',
                'icon': '📈',
                'color': '#2E86AB',
                'strengths': ['Quick setup', 'Clear results', 'Well documented'],
                'use_cases': ['Rapid infiltration events', 'Storm response analysis']
            },
            'MRC': {
                'name': 'MRC (Master Recession Curve)',
                'description': 'Uses recession curve analysis to identify recharge events.\nExcellent for consistent recession patterns.',
                'icon': '📉',
                'color': '#A23B72',
                'strengths': ['Robust analysis', 'Statistical validation', 'Precipitation integration'],
                'use_cases': ['Long-term analysis', 'Seasonal patterns', 'Climate studies']
            },
            'ERC': {
                'name': 'ERC (Extended Recession Curve)',
                'description': 'Advanced method with temporal variability analysis.\nBest for complex hydrogeological settings.',
                'icon': '🔬',
                'color': '#F18F01',
                'strengths': ['Seasonal analysis', 'Validation framework', 'Uncertainty quantification'],
                'use_cases': ['Research applications', 'Complex aquifers', 'Method validation']
            }
        }
        
        self.setup_ui()
        self.load_well_data()
    
    def update_selected_wells(self, selected_wells):
        """Update the selected wells and reload the combo box."""
        self.selected_wells = selected_wells or []
        self.load_well_data()
        
    def setup_ui(self):
        """Setup the launcher user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.create_header(layout)
        
        # Well selection
        self.create_well_selection(layout)
        
        # Method selection buttons
        self.create_method_buttons(layout)
        
        # Comparison section
        self.create_comparison_section(layout)
        
        # Options and actions
        self.create_options_section(layout)
        
        # Action buttons
        self.create_action_buttons(layout)
        
    def create_header(self, layout):
        """Create the header section."""
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
        
        # Title
        title = QLabel("Recharge Method Launcher")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        # Subtitle
        subtitle = QLabel("Select a recharge calculation method or compare multiple methods")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_frame)
        
    def create_well_selection(self, layout):
        """Create well selection section."""
        well_group = QGroupBox("Well Selection")
        well_layout = QHBoxLayout(well_group)
        
        well_layout.addWidget(QLabel("Select Well:"))
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        well_layout.addWidget(self.well_combo)
        
        # Add refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setToolTip("Reload available wells")
        refresh_btn.clicked.connect(self.load_well_data)
        well_layout.addWidget(refresh_btn)
        
        well_layout.addStretch()
        layout.addWidget(well_group)
        
    def create_method_buttons(self, layout):
        """Create method selection buttons."""
        methods_group = QGroupBox("Recharge Calculation Methods")
        methods_layout = QGridLayout(methods_group)
        methods_layout.setSpacing(15)
        
        self.method_buttons = {}
        row = 0
        
        for method_key, method_info in self.methods.items():
            button_frame = self.create_method_button(method_key, method_info)
            methods_layout.addWidget(button_frame, row // 2, row % 2)
            row += 1
            
        layout.addWidget(methods_group)
        
    def create_method_button(self, method_key, method_info):
        """Create an individual method button with information."""
        frame = QFrame()
        frame.setFixedSize(350, 180)
        frame.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {method_info['color']};
                border-radius: 12px;
                background-color: white;
                margin: 5px;
            }}
            QFrame:hover {{
                background-color: #f8f9fa;
                border-color: {method_info['color']};
                border-width: 3px;
            }}
        """)
        frame.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with icon and name
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(method_info['icon'])
        icon_label.setStyleSheet("font-size: 24px;")
        
        name_label = QLabel(method_info['name'])
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {method_info['color']};")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        
        # Description
        desc_label = QLabel(method_info['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #495057; font-size: 10px; margin: 5px 0px;")
        
        # Strengths
        strengths_text = "• " + "\n• ".join(method_info['strengths'])
        strengths_label = QLabel(strengths_text)
        strengths_label.setStyleSheet("color: #28a745; font-size: 9px; margin-top: 5px;")
        
        layout.addLayout(header_layout)
        layout.addWidget(desc_label)
        layout.addWidget(strengths_label)
        layout.addStretch()
        
        # Store reference and connect click
        self.method_buttons[method_key] = frame
        frame.mousePressEvent = lambda event, m=method_key: self.method_button_clicked(m)
        
        return frame
        
    def create_comparison_section(self, layout):
        """Create method comparison section."""
        comp_group = QGroupBox("Method Comparison")
        comp_layout = QVBoxLayout(comp_group)
        
        # Description
        desc = QLabel("Compare multiple methods side-by-side to evaluate results and select the best approach for your data.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6c757d; font-size: 11px; margin-bottom: 10px;")
        comp_layout.addWidget(desc)
        
        # Checkboxes for methods to compare
        checkbox_layout = QHBoxLayout()
        self.comparison_checkboxes = {}
        
        for method_key, method_info in self.methods.items():
            checkbox = QCheckBox(method_info['name'].split('(')[0].strip())
            checkbox.setStyleSheet(f"color: {method_info['color']};")
            self.comparison_checkboxes[method_key] = checkbox
            checkbox_layout.addWidget(checkbox)
            
        checkbox_layout.addStretch()
        comp_layout.addLayout(checkbox_layout)
        
        # Compare button
        self.compare_button = QPushButton("🔍 Compare Selected Methods")
        self.compare_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.compare_button.clicked.connect(self.launch_comparison)
        comp_layout.addWidget(self.compare_button)
        
        layout.addWidget(comp_group)
        
    def create_options_section(self, layout):
        """Create options section."""
        options_group = QGroupBox("Launch Options")
        options_layout = QHBoxLayout(options_group)
        
        self.new_window_checkbox = QCheckBox("Open in new window")
        self.new_window_checkbox.setChecked(True)
        self.new_window_checkbox.setToolTip("Launch methods in separate windows instead of replacing current tab")
        
        self.auto_settings_checkbox = QCheckBox("Use unified settings")
        self.auto_settings_checkbox.setChecked(True)
        self.auto_settings_checkbox.setToolTip("Apply unified settings to launched methods")
        
        options_layout.addWidget(self.new_window_checkbox)
        options_layout.addWidget(self.auto_settings_checkbox)
        options_layout.addStretch()
        
        layout.addWidget(options_group)
        
    def create_action_buttons(self, layout):
        """Create action buttons."""
        button_layout = QHBoxLayout()
        
        # Help button
        help_button = QPushButton("❓ Help & Recommendations")
        help_button.clicked.connect(self.show_help)
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        button_layout.addWidget(help_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
    def load_well_data(self):
        """Load available wells into the combo box."""
        try:
            self.well_combo.clear()
            logger.info("Loading well data into launcher...")
            
            # Debug: print detailed information about what we have
            logger.info(f"Selected wells count: {len(self.selected_wells) if self.selected_wells else 0}")
            logger.info(f"Selected wells type: {type(self.selected_wells)}")
            logger.info(f"Selected wells content: {self.selected_wells}")
            
            # First, try to use selected wells from main interface
            if self.selected_wells:
                logger.info(f"Processing {len(self.selected_wells)} selected wells")
                
                for i, well_data in enumerate(self.selected_wells):
                    logger.info(f"Processing well {i}: {well_data} (type: {type(well_data)})")
                    
                    well_id = None
                    well_name = None
                    
                    # Handle the standard format used by the other tabs: (well_id, well_name)
                    if isinstance(well_data, (list, tuple)) and len(well_data) >= 2:
                        well_id, well_name = well_data[0], well_data[1]
                        logger.info(f"Standard tuple format - ID: '{well_id}', Name: '{well_name}'")
                        
                        # Check if the well_name is meaningful
                        if well_name == 'Unknown' or not well_name or str(well_name).strip() == '':
                            logger.warning(f"Well {well_id} has no meaningful name ('{well_name}'), using ID")
                            well_name = f"Well {well_id}"
                    
                    # Handle dictionary format (backup)
                    elif isinstance(well_data, dict):
                        well_id = well_data.get('well_id', well_data.get('id'))
                        well_name = well_data.get('well_name', well_data.get('name'))
                        logger.info(f"Dict format - ID: '{well_id}', Name: '{well_name}'")
                        
                        # Try alternative keys if primary ones don't work
                        if well_name is None or well_name == 'Unknown':
                            well_name = well_data.get('location_id', well_data.get('location_name'))
                        
                        if well_name is None or well_name == 'Unknown':
                            well_name = f"Well {well_id}"
                    
                    # Handle single value (assume it's well_id)
                    elif isinstance(well_data, (str, int)):
                        well_id = well_data
                        well_name = f"Well {well_id}"
                        logger.info(f"Single value format - ID: '{well_id}', Generated Name: '{well_name}'")
                    
                    else:
                        logger.warning(f"Unexpected well data format: {well_data} (type: {type(well_data)})")
                        continue
                    
                    # Validate we have at least an ID
                    if well_id is None or str(well_id).strip() == '':
                        logger.warning(f"Could not extract valid well ID from: {well_data}")
                        continue
                    
                    # Create display name (use the same format as the other tabs)
                    if well_name and well_name != 'Unknown' and str(well_name).strip():
                        # Format: "WellName (ID)" to match other tabs
                        display_name = f"{str(well_name).strip()} ({well_id})"
                    else:
                        display_name = f"Well {well_id}"
                    
                    # Add to combo box
                    self.well_combo.addItem(display_name, well_id)
                    logger.info(f"Added well: '{display_name}' (ID: {well_id})")
            else:
                # Fallback: try to get all wells from data manager
                logger.info("No selected wells, trying to load all available wells")
                logger.info(f"Data manager type: {type(self.data_manager)}")
                logger.info(f"Data manager has get_wells: {hasattr(self.data_manager, 'get_wells')}")
                
                try:
                    if hasattr(self.data_manager, 'get_wells'):
                        wells = self.data_manager.get_wells()
                        logger.info(f"Data manager returned: {wells} (type: {type(wells)})")
                        
                        if wells:
                            for well in wells:
                                logger.info(f"Processing well from data manager: {well} (type: {type(well)})")
                                
                                well_id = None
                                well_name = None
                                
                                if hasattr(well, 'get'):  # Dictionary-like
                                    well_id = well.get('well_id', well.get('id'))
                                    well_name = well.get('well_name', well.get('name'))
                                elif hasattr(well, 'well_id'):  # Object with attributes
                                    well_id = getattr(well, 'well_id', None)
                                    well_name = getattr(well, 'well_name', None)
                                else:
                                    logger.warning(f"Unknown well format from data manager: {well}")
                                    continue
                                
                                if well_id is None:
                                    logger.warning(f"Well missing ID: {well}")
                                    continue
                                    
                                display_name = well_name if well_name and well_name != 'Unknown' else f"Well {well_id}"
                                self.well_combo.addItem(display_name, well_id)
                                logger.info(f"Added well from data manager: {display_name} (ID: {well_id})")
                        else:
                            # No wells available - add placeholder
                            self.well_combo.addItem("No wells available - please select wells in main interface", None)
                            logger.warning("No wells available from data manager")
                    else:
                        logger.warning("Data manager does not have get_wells method")
                        self.well_combo.addItem("Please select wells in main interface first", None)
                        
                except Exception as e:
                    logger.error(f"Error getting wells from data manager: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    self.well_combo.addItem("Error loading wells from data manager", None)
            
            # Set default selection if wells are available
            if self.well_combo.count() > 0 and self.well_combo.itemData(0) is not None:
                self.well_combo.setCurrentIndex(0)
                logger.info(f"Set default well selection: {self.well_combo.currentText()}")
            else:
                logger.warning("No valid wells available for selection")
                # Add helpful message for user
                if self.well_combo.count() == 0:
                    self.well_combo.addItem("No wells available - please select wells in main interface first", None)
                
            # Log final status
            logger.info(f"Well combo box populated with {self.well_combo.count()} items")
            for i in range(self.well_combo.count()):
                item_text = self.well_combo.itemText(i)
                item_data = self.well_combo.itemData(i)
                logger.info(f"  Item {i}: '{item_text}' (data: {item_data})")
                
        except Exception as e:
            logger.error(f"Error loading wells: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.well_combo.clear()
            self.well_combo.addItem("Error loading wells", None)
            
    def method_button_clicked(self, method_key):
        """Handle method button click."""
        # Check if a well is selected
        current_well_id = self.well_combo.currentData()
        current_well_name = self.well_combo.currentText()
        
        logger.info(f"Method button clicked: {method_key}")
        logger.info(f"Current well selection - ID: {current_well_id}, Name: '{current_well_name}'")
        
        # Check for invalid selections
        invalid_selections = [
            "No wells available", "Error loading wells", 
            "Please select wells in main interface first",
            "No wells available - please select wells in main interface first"
        ]
        
        if current_well_id is None or current_well_name in invalid_selections:
            # Provide detailed error message based on the situation
            if not self.selected_wells:
                error_msg = (
                    "No wells are selected in the main interface.\n\n"
                    "To fix this:\n"
                    "1. Go to the main 'Available Wells' table\n"
                    "2. Select one or more wells for analysis\n"
                    "3. Return to this launcher and try again\n\n"
                    "Note: Wells must be selected in the main interface before using the launcher."
                )
            else:
                error_msg = (
                    f"Well data issue detected.\n\n"
                    f"Selected wells data: {self.selected_wells}\n"
                    f"Current selection: '{current_well_name}'\n\n"
                    "Try:\n"
                    "1. Click the '🔄 Refresh' button to reload wells\n"
                    "2. Check that wells have proper names in the main interface\n"
                    "3. Reselect wells in the main interface if needed"
                )
            
            QMessageBox.warning(self, "No Well Selected", error_msg)
            return
            
        logger.info(f"Launching {method_key} method for well: {current_well_name} (ID: {current_well_id})")
        
        # Get launch options
        options = {
            'well_id': current_well_id,
            'well_name': current_well_name,
            'new_window': self.new_window_checkbox.isChecked(),
            'use_unified_settings': self.auto_settings_checkbox.isChecked()
        }
        
        # Emit signal to launch method
        self.method_selected.emit(method_key, options)
        
        if not self.new_window_checkbox.isChecked():
            self.close()
            
    def launch_comparison(self):
        """Launch method comparison."""
        selected_methods = []
        
        for method_key, checkbox in self.comparison_checkboxes.items():
            if checkbox.isChecked():
                selected_methods.append(method_key)
                
        if len(selected_methods) < 2:
            QMessageBox.warning(self, "Insufficient Selection", "Please select at least 2 methods to compare.")
            return
            
        if self.well_combo.currentData() is None:
            QMessageBox.warning(self, "No Well Selected", "Please select a well before launching comparison.")
            return
            
        # Get comparison options
        options = {
            'well_id': self.well_combo.currentData(),
            'well_name': self.well_combo.currentText(),
            'new_window': True,  # Comparisons always open in new window
            'use_unified_settings': self.auto_settings_checkbox.isChecked()
        }
        
        # Emit signal to launch comparison
        self.comparison_requested.emit(selected_methods, options)
        
    def show_help(self):
        """Show help and method recommendations."""
        help_dialog = MethodRecommendationDialog(self)
        help_dialog.exec_()


class MethodRecommendationDialog(QDialog):
    """Dialog providing help and method recommendations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Method Help & Recommendations")
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Recharge Method Selection Guide")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Help content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>🎯 Quick Selection Guide</h3>
        <p><b>New to recharge analysis?</b> Start with <span style="color: #2E86AB;"><b>RISE</b></span> method for its simplicity and clear results.</p>
        <p><b>Need robust statistical analysis?</b> Use <span style="color: #A23B72;"><b>MRC</b></span> method for precipitation integration and validation.</p>
        <p><b>Research or complex sites?</b> Choose <span style="color: #F18F01;"><b>ERC</b></span> method for advanced analysis and uncertainty quantification.</p>
        
        <h3>📊 Method Comparison</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f8f9fa;">
            <th>Aspect</th><th>RISE</th><th>MRC</th><th>ERC</th>
        </tr>
        <tr>
            <td><b>Setup Time</b></td>
            <td>⭐⭐⭐ Fast</td>
            <td>⭐⭐ Moderate</td>
            <td>⭐ Detailed</td>
        </tr>
        <tr>
            <td><b>Data Requirements</b></td>
            <td>⭐⭐ Basic</td>
            <td>⭐⭐⭐ Enhanced</td>
            <td>⭐⭐⭐ Comprehensive</td>
        </tr>
        <tr>
            <td><b>Statistical Rigor</b></td>
            <td>⭐⭐ Good</td>
            <td>⭐⭐⭐ Excellent</td>
            <td>⭐⭐⭐ Research-grade</td>
        </tr>
        <tr>
            <td><b>Precipitation Integration</b></td>
            <td>❌ No</td>
            <td>✅ Yes</td>
            <td>✅ Advanced</td>
        </tr>
        </table>
        
        <h3>🏗️ Best Practices</h3>
        <ul>
        <li><b>Start Simple:</b> Begin with RISE to understand your data, then advance to MRC/ERC if needed</li>
        <li><b>Compare Methods:</b> Use the comparison feature to validate results across different approaches</li>
        <li><b>Unified Settings:</b> Configure parameters once and apply across all methods for consistency</li>
        <li><b>Data Quality:</b> Ensure good water level data quality before analysis - garbage in, garbage out!</li>
        </ul>
        
        <h3>⚠️ Common Pitfalls</h3>
        <ul>
        <li>Using inappropriate time periods (ensure adequate data coverage)</li>
        <li>Ignoring seasonal patterns in recharge calculations</li>
        <li>Not validating results with independent methods</li>
        <li>Overcomplicating analysis when simpler methods would suffice</li>
        </ul>
        """)
        layout.addWidget(help_text)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)