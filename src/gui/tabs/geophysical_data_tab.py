# src/gui/tabs/geophysical_data_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
import logging

logger = logging.getLogger(__name__)

class GeophysicalDataTab(QWidget):
    """Tab for managing geophysical data including well logs and neutron probe data."""
    
    def __init__(self, db_manager):
        """Initialize the geophysical data tab."""
        super().__init__()
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface for the geophysical data tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Geophysical Data Management")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2C3E50;
                padding: 10px;
                border-bottom: 2px solid #3498DB;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Create sub-tabs
        self.sub_tab_widget = QTabWidget()
        self.sub_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #ECF0F1;
                border: 1px solid #BDC3C7;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
                color: #2C3E50;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
                color: #3498DB;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #D5DBDB;
            }
        """)
        
        # Add well logs tab
        self.well_logs_tab = self._create_well_logs_tab()
        self.sub_tab_widget.addTab(self.well_logs_tab, "Well Logs")
        
        # Add neutron probe tab
        self.neutron_probe_tab = self._create_neutron_probe_tab()
        self.sub_tab_widget.addTab(self.neutron_probe_tab, "Neutron Probe")
        
        layout.addWidget(self.sub_tab_widget)
        
    def _create_well_logs_tab(self):
        """Create the well logs sub-tab with HTML placeholder."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create web view for HTML content
        web_view = QWebEngineView()
        web_view.setHtml(self._get_well_logs_html())
        
        layout.addWidget(web_view)
        return widget
        
    def _create_neutron_probe_tab(self):
        """Create the neutron probe sub-tab with HTML placeholder."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create web view for HTML content
        web_view = QWebEngineView()
        web_view.setHtml(self._get_neutron_probe_html())
        
        layout.addWidget(web_view)
        return widget
        
    def _get_well_logs_html(self):
        """Return HTML content for well logs placeholder."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Well Logs - Coming Soon</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                }
                .container {
                    background: white;
                    border-radius: 15px;
                    padding: 40px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    width: 100%;
                }
                .icon {
                    font-size: 4em;
                    margin-bottom: 20px;
                    color: #3498db;
                }
                h1 {
                    color: #2c3e50;
                    margin-bottom: 20px;
                    font-size: 2.5em;
                    font-weight: 300;
                }
                .subtitle {
                    color: #7f8c8d;
                    font-size: 1.2em;
                    margin-bottom: 30px;
                    line-height: 1.6;
                }
                .feature-list {
                    text-align: left;
                    margin: 30px 0;
                    background: #f8f9fa;
                    padding: 25px;
                    border-radius: 10px;
                    border-left: 4px solid #3498db;
                }
                .feature-item {
                    margin: 12px 0;
                    display: flex;
                    align-items: center;
                }
                .feature-item::before {
                    content: "✓";
                    color: #27ae60;
                    font-weight: bold;
                    margin-right: 10px;
                    background: #d4edda;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                }
                .version-badge {
                    display: inline-block;
                    background: #e74c3c;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: bold;
                    margin-top: 20px;
                }
                .chart-preview {
                    width: 100%;
                    height: 200px;
                    background: linear-gradient(45deg, #f39c12, #e67e22);
                    border-radius: 10px;
                    margin: 20px 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 1.1em;
                    font-weight: bold;
                    opacity: 0.8;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📊</div>
                <h1>Well Logs Analysis</h1>
                <p class="subtitle">
                    Advanced geophysical logging data management and visualization system
                </p>
                
                <div class="chart-preview">
                    Interactive Log Visualization Preview
                </div>
                
                <div class="feature-list">
                    <h3 style="margin-top: 0; color: #2c3e50;">Planned Features:</h3>
                    <div class="feature-item">Import and manage lithological logs</div>
                    <div class="feature-item">Geophysical log visualization (gamma, resistivity, SP)</div>
                    <div class="feature-item">Stratigraphic correlation tools</div>
                    <div class="feature-item">Well log data export and reporting</div>
                    <div class="feature-item">Integration with well construction data</div>
                    <div class="feature-item">Automated log interpretation utilities</div>
                </div>
                
                <div class="version-badge">Coming in Next Release</div>
            </div>
        </body>
        </html>
        """
        
    def _get_neutron_probe_html(self):
        """Return HTML content for neutron probe placeholder."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Neutron Probe - Coming Soon</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 40px;
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    color: #333;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                }
                .container {
                    background: white;
                    border-radius: 15px;
                    padding: 40px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    width: 100%;
                }
                .icon {
                    font-size: 4em;
                    margin-bottom: 20px;
                    color: #27ae60;
                }
                h1 {
                    color: #2c3e50;
                    margin-bottom: 20px;
                    font-size: 2.5em;
                    font-weight: 300;
                }
                .subtitle {
                    color: #7f8c8d;
                    font-size: 1.2em;
                    margin-bottom: 30px;
                    line-height: 1.6;
                }
                .feature-list {
                    text-align: left;
                    margin: 30px 0;
                    background: #f8f9fa;
                    padding: 25px;
                    border-radius: 10px;
                    border-left: 4px solid #27ae60;
                }
                .feature-item {
                    margin: 12px 0;
                    display: flex;
                    align-items: center;
                }
                .feature-item::before {
                    content: "⚡";
                    color: #f39c12;
                    font-weight: bold;
                    margin-right: 10px;
                    background: #fff3cd;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                }
                .version-badge {
                    display: inline-block;
                    background: #27ae60;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: bold;
                    margin-top: 20px;
                }
                .probe-preview {
                    width: 100%;
                    height: 200px;
                    background: linear-gradient(45deg, #16a085, #27ae60);
                    border-radius: 10px;
                    margin: 20px 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 1.1em;
                    font-weight: bold;
                    opacity: 0.9;
                    position: relative;
                    overflow: hidden;
                }
                .probe-preview::after {
                    content: "📡";
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    font-size: 2em;
                    opacity: 0.3;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⚛️</div>
                <h1>Neutron Probe Data</h1>
                <p class="subtitle">
                    Comprehensive neutron moisture logging and soil analysis system
                </p>
                
                <div class="probe-preview">
                    Neutron Moisture Profile Visualization
                </div>
                
                <div class="feature-list">
                    <h3 style="margin-top: 0; color: #2c3e50;">Planned Features:</h3>
                    <div class="feature-item">Neutron probe data import and management</div>
                    <div class="feature-item">Soil moisture profile visualization</div>
                    <div class="feature-item">Depth-calibrated moisture content analysis</div>
                    <div class="feature-item">Time-series moisture monitoring</div>
                    <div class="feature-item">Probe calibration and quality control</div>
                    <div class="feature-item">Export capabilities for scientific reporting</div>
                </div>
                
                <div class="version-badge">Coming in Next Release</div>
            </div>
        </body>
        </html>
        """
    
    def refresh_data(self):
        """Refresh the data in the tab when needed."""
        # Placeholder for future data refresh functionality
        self.logger.debug("Geophysical data tab refresh requested (placeholder)")
        pass
        
    def enable_tab(self, enabled=True):
        """Enable or disable the tab functionality."""
        # Placeholder for future enable/disable functionality
        self.setEnabled(enabled)
        
    def get_current_database(self):
        """Get the current database connection."""
        return self.db_manager.current_db if self.db_manager else None