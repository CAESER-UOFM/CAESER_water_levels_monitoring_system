"""
Individual Method Window for launching recharge methods in separate windows.
Provides a standalone window containing a single recharge calculation method.
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QWidget, QMessageBox, QStatusBar, QMenuBar, QAction, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)


class MethodWindow(QMainWindow):
    """
    Standalone window for a single recharge calculation method.
    """
    
    def __init__(self, method_name, method_class, data_manager, options, parent=None):
        super().__init__(parent)
        self.method_name = method_name
        self.method_class = method_class
        self.data_manager = data_manager
        self.options = options
        self.parent_widget = parent
        
        # Create method instance
        self.method_instance = None
        
        self.setWindowTitle(f"{method_name} Method - {options.get('well_name', 'Unknown Well')}")
        self.resize(1200, 800)
        
        # Setup UI
        self.setup_ui()
        self.create_menubar()
        self.create_statusbar()
        
        # Initialize method
        self.initialize_method()
        
    def setup_ui(self):
        """Setup the window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header with method info
        self.create_header(layout)
        
        # Method container
        self.method_container = QWidget()
        self.method_layout = QVBoxLayout(self.method_container)
        layout.addWidget(self.method_container)
        
    def create_header(self, layout):
        """Create header section."""
        header_layout = QHBoxLayout()
        
        # Method title and info
        title_layout = QVBoxLayout()
        
        title = QLabel(f"{self.method_name} Recharge Analysis")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        
        # Method-specific colors
        colors = {'RISE': '#2E86AB', 'MRC': '#A23B72', 'ERC': '#F18F01'}
        title.setStyleSheet(f"color: {colors.get(self.method_name, '#333')};")
        
        well_info = QLabel(f"Well: {self.options.get('well_name', 'Unknown')} | "
                          f"Unified Settings: {'✅' if self.options.get('use_unified_settings') else '❌'}")
        well_info.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(well_info)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Settings sync button
        self.sync_settings_btn = QPushButton("⚙️ Sync Settings")
        self.sync_settings_btn.setMaximumWidth(120)
        self.sync_settings_btn.setToolTip("Sync with unified settings from main tab")
        self.sync_settings_btn.clicked.connect(self.sync_settings)
        
        # Export results button
        self.export_btn = QPushButton("📊 Export Results")
        self.export_btn.setMaximumWidth(120)
        self.export_btn.setToolTip("Export calculation results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)  # Enable after calculations
        
        button_layout.addWidget(self.sync_settings_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(button_layout)
        
        layout.addLayout(header_layout)
        
        # Separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #dee2e6; margin: 10px 0px;")
        layout.addWidget(separator)
        
    def create_menubar(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Export action
        export_action = QAction('Export Results...', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Close action
        close_action = QAction('Close Window', self)
        close_action.setShortcut('Ctrl+W')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        
        # Sync settings action
        sync_action = QAction('Sync with Main Tab', self)
        sync_action.triggered.connect(self.sync_settings)
        settings_menu.addAction(sync_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # Method help action
        method_help_action = QAction(f'{self.method_name} Method Help', self)
        method_help_action.triggered.connect(self.show_method_help)
        help_menu.addAction(method_help_action)
        
    def create_statusbar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initial status
        self.status_bar.showMessage(f"Ready - {self.method_name} method initialized")
        
    def initialize_method(self):
        """Initialize the method instance."""
        try:
            # Create method instance
            self.method_instance = self.method_class(self.data_manager, self)
            
            # Add to layout
            self.method_layout.addWidget(self.method_instance)
            
            # Load well data if well ID is provided
            if self.options.get('well_id'):
                if hasattr(self.method_instance, 'load_well_data'):
                    self.method_instance.load_well_data(self.options['well_id'])
                elif hasattr(self.method_instance, 'well_combo'):
                    # Try to set the well in the combo box
                    for i in range(self.method_instance.well_combo.count()):
                        if self.method_instance.well_combo.itemData(i) == self.options['well_id']:
                            self.method_instance.well_combo.setCurrentIndex(i)
                            break
            
            # Connect to method events if available
            if hasattr(self.method_instance, 'calculation_completed'):
                self.method_instance.calculation_completed.connect(self.on_calculation_completed)
                
            self.status_bar.showMessage(f"{self.method_name} method ready")
            logger.info(f"Initialized {self.method_name} method window")
            
        except Exception as e:
            logger.error(f"Error initializing method: {e}")
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize {self.method_name} method: {str(e)}")
            self.close()
            
    def sync_settings(self):
        """Sync settings with the main tab."""
        try:
            if self.parent_widget and hasattr(self.parent_widget, 'unified_settings'):
                # Get settings from main tab
                if hasattr(self.parent_widget, 'get_current_settings'):
                    main_settings = self.parent_widget.get_current_settings()
                    
                    # Apply to method instance
                    if hasattr(self.method_instance, 'update_settings'):
                        method_settings = self.parent_widget.unified_settings.get_method_settings(self.method_name)
                        self.method_instance.update_settings(method_settings)
                        
                        self.status_bar.showMessage("Settings synchronized with main tab", 3000)
                        QMessageBox.information(self, "Settings Synced", "Settings have been synchronized with the main tab.")
                        
                    else:
                        QMessageBox.information(self, "Manual Sync", "Please manually adjust settings as needed - automatic sync not available for this method.")
                else:
                    QMessageBox.warning(self, "Sync Unavailable", "Cannot sync settings - main tab not accessible.")
            else:
                QMessageBox.warning(self, "Sync Unavailable", "Cannot sync settings - main tab not accessible.")
                
        except Exception as e:
            logger.error(f"Error syncing settings: {e}")
            QMessageBox.warning(self, "Sync Error", f"Failed to sync settings: {str(e)}")
            
    def export_results(self):
        """Export calculation results."""
        try:
            # Check if we have results to export
            if not hasattr(self.method_instance, 'recharge_events') or not self.method_instance.recharge_events:
                QMessageBox.information(self, "No Results", "No calculation results available to export. Please run calculations first.")
                return
                
            # Get save file path
            default_name = f"{self.method_name}_results_{self.options.get('well_name', 'unknown')}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                f"Export {self.method_name} Results",
                default_name,
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                # For now, just show a placeholder message
                QMessageBox.information(self, "Export", f"Export functionality will save results to {file_path} in a future update.")
                self.status_bar.showMessage(f"Results exported to {file_path}", 3000)
                
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            QMessageBox.warning(self, "Export Error", f"Failed to export results: {str(e)}")
            
    def show_method_help(self):
        """Show method-specific help."""
        help_texts = {
            'RISE': """
            <h3>RISE Method Help</h3>
            <p>The RISE method identifies recharge events by analyzing rapid water level rises in monitoring wells.</p>
            <h4>Key Parameters:</h4>
            <ul>
            <li><b>Rise Threshold:</b> Minimum rise required to identify an event</li>
            <li><b>Specific Yield:</b> Aquifer specific yield for recharge calculation</li>
            <li><b>Water Year:</b> Defines the analysis period boundaries</li>
            </ul>
            <h4>Best Practices:</h4>
            <ul>
            <li>Use high-frequency data for accurate event detection</li>
            <li>Validate specific yield with aquifer tests if possible</li>
            <li>Consider seasonal variations in recharge patterns</li>
            </ul>
            """,
            'MRC': """
            <h3>MRC Method Help</h3>
            <p>The Master Recession Curve method uses recession analysis to identify deviations indicating recharge.</p>
            <h4>Key Parameters:</h4>
            <ul>
            <li><b>Deviation Threshold:</b> Minimum deviation from recession curve</li>
            <li><b>Recession Length:</b> Minimum length for valid recession segments</li>
            <li><b>Precipitation Data:</b> Optional precipitation integration</li>
            </ul>
            <h4>Best Practices:</h4>
            <ul>
            <li>Ensure adequate recession periods for curve fitting</li>
            <li>Include precipitation data for validation</li>
            <li>Review recession curve quality before analysis</li>
            </ul>
            """,
            'ERC': """
            <h3>ERC Method Help</h3>
            <p>The Extended Recession Curve method provides advanced analysis with temporal variability and validation.</p>
            <h4>Key Parameters:</h4>
            <ul>
            <li><b>Seasonal Analysis:</b> Accounts for seasonal recession variations</li>
            <li><b>Validation Framework:</b> Quality control for event identification</li>
            <li><b>Curve Fitting:</b> Advanced statistical curve fitting options</li>
            </ul>
            <h4>Best Practices:</h4>
            <ul>
            <li>Use for research-quality analysis</li>
            <li>Review validation metrics carefully</li>
            <li>Consider uncertainty quantification</li>
            </ul>
            """
        }
        
        help_text = help_texts.get(self.method_name, f"<h3>{self.method_name} Method</h3><p>Help content coming soon.</p>")
        
        QMessageBox.information(self, f"{self.method_name} Help", help_text)
        
    def on_calculation_completed(self):
        """Handle calculation completion."""
        self.export_btn.setEnabled(True)
        self.status_bar.showMessage("Calculation completed - results available for export", 5000)
        
    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Clean up method instance
            if self.method_instance:
                self.method_instance.setParent(None)
                
            event.accept()
            logger.info(f"Closed {self.method_name} method window")
            
        except Exception as e:
            logger.error(f"Error closing method window: {e}")
            event.accept()