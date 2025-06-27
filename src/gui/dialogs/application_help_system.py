"""
Comprehensive Help System for Water Level Monitoring Application

Provides detailed guidance on all tabs, workflows, and features of the main application.
Designed to be consistent with the visualizer help system.
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QTabWidget, QWidget, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDesktopServices, QCursor
import webbrowser

logger = logging.getLogger(__name__)


class ApplicationHelpSystem(QDialog):
    """
    Comprehensive help system for the Water Level Monitoring application.
    """
    
    def __init__(self, parent=None, initial_tab=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.initial_tab = initial_tab
        
        self.setWindowTitle("Water Level Monitoring - Help & Documentation")
        self.setModal(False)
        self.resize(1200, 800)
        
        self.setup_ui()
        
        # Set initial tab if specified
        if initial_tab:
            self.set_initial_tab(initial_tab)
        
    def setup_ui(self):
        """Setup the help system UI."""
        layout = QVBoxLayout(self)
        
        # Header
        self.create_header(layout)
        
        # Main help content
        self.create_help_content(layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
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
        
        title = QLabel("Water Level Monitoring - Help & Documentation")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Complete guide to managing groundwater monitoring data and field operations")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_frame)
        
    def create_help_content(self, layout):
        """Create help content tabs."""
        self.help_tabs = QTabWidget()
        
        # Overview tab
        self.create_overview_tab()
        
        # Database tab help
        self.create_database_tab_help()
        
        # Barologger tab help
        self.create_barologger_tab_help()
        
        # Water Level tab help
        self.create_water_level_tab_help()
        
        # Water Level Runs tab help
        self.create_runs_tab_help()
        
        # Recharge tab help
        self.create_recharge_tab_help()
        
        # Auto Sync help
        self.create_auto_sync_help()
        
        # Cloud Features help
        self.create_cloud_features_help()
        
        layout.addWidget(self.help_tabs)
        
    def create_overview_tab(self):
        """Create application overview tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        overview_html = """
        <h2>🌊 Water Level Monitoring System Overview</h2>
        
        <p>The Water Level Monitoring System is a comprehensive application for managing groundwater monitoring data, 
        field operations, and cloud-based collaboration. It integrates data from multiple sources including automatic 
        transducers, manual field readings, and telemetry systems.</p>
        
        <h3>🎯 Main Application Workflow</h3>
        <ol>
        <li><b>Database Setup:</b> Create or select a project database</li>
        <li><b>Equipment Management:</b> Register wells, transducers, and barologgers</li>
        <li><b>Data Collection:</b> Import XLE files, fetch telemetry, enter manual readings</li>
        <li><b>Field Operations:</b> Create runs, manage field data collection</li>
        <li><b>Cloud Collaboration:</b> Sync with Google Drive, save changes to cloud</li>
        <li><b>Analysis:</b> Use integrated visualizer for data analysis and reporting</li>
        </ol>
        
        <h3>📊 Application Tabs</h3>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Tab</th>
            <th style="padding: 8px;">Purpose</th>
            <th style="padding: 8px;">Key Features</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Database</b></td>
            <td style="padding: 8px;">Database management and well visualization</td>
            <td style="padding: 8px;">Interactive map, database creation, well status overview</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Barologger</b></td>
            <td style="padding: 8px;">Barometric pressure data management</td>
            <td style="padding: 8px;">XLE import, master baro creation, pressure visualization</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Water Level</b></td>
            <td style="padding: 8px;">Water level data collection and analysis</td>
            <td style="padding: 8px;">Well management, data import, telemetry, gap analysis</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Water Level Runs</b></td>
            <td style="padding: 8px;">Field data collection coordination</td>
            <td style="padding: 8px;">Run creation, Google Drive sync, field data management</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Recharge</b></td>
            <td style="padding: 8px;">Groundwater recharge analysis</td>
            <td style="padding: 8px;">RISE and MRC methods, recharge quantification, scientific analysis</td>
        </tr>
        </table>
        
        <h3>🔧 Key Features</h3>
        <ul>
        <li><b>Multi-source Data Integration:</b> Handles transducer files (XLE), telemetry systems (MONET), and manual readings</li>
        <li><b>Cloud Collaboration:</b> Google Drive integration with service account authentication</li>
        <li><b>Real-time Status Tracking:</b> Visual indicators for data quality and collection status</li>
        <li><b>Automated Workflows:</b> Auto Sync for barologger and water level data</li>
        <li><b>Change Tracking:</b> Detailed logging of manual vs automatic modifications</li>
        <li><b>Field Operations Support:</b> Run management and GPS-enabled data collection</li>
        <li><b>Data Validation:</b> Gap detection, outlier identification, and quality flags</li>
        <li><b>Integrated Analysis:</b> Direct connection to visualization tools</li>
        </ul>
        
        <h3>🚀 Getting Started</h3>
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>For New Users:</b>
        <ol>
        <li>Start with the <b>Database tab</b> to create or select a project database</li>
        <li>Use the <b>Barologger tab</b> to import atmospheric pressure data (required for water level correction)</li>
        <li>Set up wells and transducers in the <b>Water Level tab</b></li>
        <li>Use <b>Water Level Runs</b> for organizing field data collection</li>
        <li>Access the <b>Auto Sync</b> menu for automated data updates</li>
        </ol>
        </div>
        
        <h3>🔄 Data Flow Overview</h3>
        <p><b>Raw Data Sources:</b></p>
        <ul>
        <li>XLE files from Solinst transducers and barologgers</li>
        <li>Telemetry data from MONET or other systems</li>
        <li>Manual field readings (CSV format)</li>
        <li>Cloud-based field data from Google Drive</li>
        </ul>
        
        <p><b>Processing Steps:</b></p>
        <ol>
        <li>Data validation and quality checking</li>
        <li>Barometric compensation for water levels</li>
        <li>Gap detection and flagging</li>
        <li>Integration with existing database records</li>
        <li>Status updates and change tracking</li>
        </ol>
        
        <p><b>Outputs:</b></p>
        <ul>
        <li>Corrected water level time series</li>
        <li>Quality assessment reports</li>
        <li>Field collection summaries</li>
        <li>Cloud-synchronized project databases</li>
        </ul>
        
        <h3>📖 Using This Help System</h3>
        <p>This help system is organized by application tabs. Each tab has its own dedicated help section with:</p>
        <ul>
        <li><b>Purpose & Overview:</b> What the tab is designed for</li>
        <li><b>Button Guide:</b> Detailed explanation of every button function</li>
        <li><b>Workflows:</b> Step-by-step processes for common tasks</li>
        <li><b>Tips & Best Practices:</b> Expert recommendations</li>
        <li><b>Troubleshooting:</b> Common issues and solutions</li>
        </ul>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>💡 Pro Tip:</b> You can access tab-specific help by clicking the "Help" button on each tab, 
        or use the main menu Help → Application Help to access this comprehensive guide.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(overview_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "📋 Overview")
        
    def create_database_tab_help(self):
        """Create Database tab help."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        database_help_html = """
        <h2>🗄️ Database Tab - Project Management & Well Visualization</h2>
        
        <h3>Purpose & Overview</h3>
        <p>The Database tab serves as the central hub for project management and provides an interactive 
        geographical overview of your monitoring network. It displays all wells on a map with color-coded 
        status indicators and provides tools for database management.</p>
        
        <h3>🎯 Main Features</h3>
        <ul>
        <li><b>Interactive Map:</b> Folium-based map showing all wells with clickable markers</li>
        <li><b>Status Visualization:</b> Color-coded well markers indicating data quality</li>
        <li><b>Database Management:</b> Create new databases and manage existing ones</li>
        <li><b>Data Visualizer Integration:</b> Direct access to analysis tools</li>
        </ul>
        
        <h3>🔘 Button Guide</h3>
        
        <h4>New Database</h4>
        <ul>
        <li><b>Function:</b> Creates a new SQLite database file for a monitoring project</li>
        <li><b>When to use:</b> Starting a new monitoring project or creating separate databases for different sites</li>
        <li><b>Process:</b> Select location → Enter filename → Database is created with standard schema</li>
        <li><b>Result:</b> New empty database ready for well and equipment registration</li>
        </ul>
        
        <h4>Refresh</h4>
        <ul>
        <li><b>Function:</b> Updates the map display and reloads well information</li>
        <li><b>When to use:</b> After adding new wells, importing data, or changing database</li>
        <li><b>Process:</b> Queries database for current well status → Updates map markers</li>
        <li><b>Result:</b> Map shows current well locations and status indicators</li>
        </ul>
        
        <h3>🗺️ Interactive Map Features</h3>
        
        <h4>Well Status Color Coding</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Color</th>
            <th style="padding: 8px;">Status</th>
            <th style="padding: 8px;">Meaning</th>
        </tr>
        <tr>
            <td style="padding: 8px; background-color: #28a745; color: white;"><b>Green</b></td>
            <td style="padding: 8px;">All Good</td>
            <td style="padding: 8px;">Has master baro assignment and recent data</td>
        </tr>
        <tr>
            <td style="padding: 8px; background-color: #dc3545; color: white;"><b>Red</b></td>
            <td style="padding: 8px;">Multiple Issues</td>
            <td style="padding: 8px;">Both barometric and level data problems</td>
        </tr>
        <tr>
            <td style="padding: 8px; background-color: #fd7e14; color: white;"><b>Orange</b></td>
            <td style="padding: 8px;">Baro Issues</td>
            <td style="padding: 8px;">Missing or problematic barometric pressure data</td>
        </tr>
        <tr>
            <td style="padding: 8px; background-color: #6f42c1; color: white;"><b>Purple</b></td>
            <td style="padding: 8px;">Level Issues</td>
            <td style="padding: 8px;">Missing or problematic water level data</td>
        </tr>
        <tr>
            <td style="padding: 8px; background-color: #007bff; color: white;"><b>Blue</b></td>
            <td style="padding: 8px;">No Data</td>
            <td style="padding: 8px;">Default values or no data available</td>
        </tr>
        </table>
        
        <h4>Well Marker Interactions</h4>
        <ul>
        <li><b>Click Well Marker:</b> Opens Data Visualizer with the selected well pre-loaded</li>
        <li><b>Hover:</b> Shows popup with well information (CAE number, status, data ranges)</li>
        <li><b>Zoom/Pan:</b> Standard map navigation controls available</li>
        </ul>
        
        <h3>📊 Workflows</h3>
        
        <h4>Creating a New Project Database</h4>
        <ol>
        <li>Click <b>"New Database"</b> button</li>
        <li>Navigate to desired save location</li>
        <li>Enter descriptive filename (e.g., "ProjectName_2025.db")</li>
        <li>Click Save - database is created with standard schema</li>
        <li>Database automatically becomes active and appears in dropdown</li>
        <li>Refresh to confirm database is empty (no wells on map)</li>
        </ol>
        
        <h4>Monitoring Well Network Status</h4>
        <ol>
        <li>Select project database from main dropdown</li>
        <li>Click <b>"Refresh"</b> to update map display</li>
        <li>Review well marker colors for status overview</li>
        <li>Click problem wells (red/orange/purple) to investigate issues</li>
        <li>Use other tabs to resolve data quality problems</li>
        <li>Return and refresh to verify status improvements</li>
        </ol>
        
        <h4>Accessing Data Analysis</h4>
        <ol>
        <li>Locate well of interest on map</li>
        <li>Click well marker to open popup</li>
        <li>Click in popup area to launch Data Visualizer</li>
        <li>Visualizer opens with selected well pre-loaded</li>
        <li>Perform analysis, create plots, export data</li>
        <li>Return to main application when finished</li>
        </ol>
        
        <h3>💡 Tips & Best Practices</h3>
        
        <h4>Database Organization</h4>
        <ul>
        <li><b>Use descriptive names:</b> Include project name and year in database filename</li>
        <li><b>One database per project:</b> Keep separate monitoring projects in different databases</li>
        <li><b>Regular backups:</b> Use cloud sync or manual backup for important projects</li>
        <li><b>Test database:</b> Create a test database for learning and experimentation</li>
        </ul>
        
        <h4>Map Usage</h4>
        <ul>
        <li><b>Regular monitoring:</b> Check map daily for status changes</li>
        <li><b>Visual network overview:</b> Use colors to quickly identify problem areas</li>
        <li><b>Field planning:</b> Identify wells needing attention before field visits</li>
        <li><b>Progress tracking:</b> Watch status improvements after data updates</li>
        </ul>
        
        <h3>🔧 Troubleshooting</h3>
        
        <h4>Map Not Loading</h4>
        <ul>
        <li><b>Check database:</b> Ensure a database is selected</li>
        <li><b>Verify well coordinates:</b> Wells need valid latitude/longitude</li>
        <li><b>Refresh display:</b> Click Refresh button to reload</li>
        <li><b>Check logs:</b> Look for error messages in application logs</li>
        </ul>
        
        <h4>Wrong Well Colors</h4>
        <ul>
        <li><b>Data lag:</b> Status indicators may not update immediately</li>
        <li><b>Missing assignments:</b> Wells need barologger assignments</li>
        <li><b>Import issues:</b> Check that data import completed successfully</li>
        <li><b>Manual refresh:</b> Click Refresh to update status calculations</li>
        </ul>
        
        <h4>Visualizer Won't Open</h4>
        <ul>
        <li><b>Installation check:</b> Ensure visualizer tools are properly installed</li>
        <li><b>Well selection:</b> Make sure you clicked directly on a well marker</li>
        <li><b>Data availability:</b> Visualizer requires wells with some data</li>
        <li><b>Permissions:</b> Check file permissions for visualizer executable</li>
        </ul>
        
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>💡 Expert Tip:</b> The Database tab map is your "command center" for monitoring operations. 
        Start each day by checking the map for status changes, then use other tabs to address any 
        issues identified by the color coding system.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(database_help_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "🗄️ Database")
        
    def create_barologger_tab_help(self):
        """Create Barologger tab help."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        barologger_help_html = """
        <h2>🌡️ Barologger Tab - Atmospheric Pressure Management</h2>
        
        <h3>Purpose & Overview</h3>
        <p>The Barologger tab manages atmospheric pressure data essential for accurate water level measurements. 
        Barometric pressure compensation is critical because changes in atmospheric pressure affect water levels 
        in monitoring wells. This tab handles barologger registration, data import, and master barometric 
        pressure dataset creation.</p>
        
        <h3>🎯 Key Concepts</h3>
        <ul>
        <li><b>Barometric Compensation:</b> Removes atmospheric pressure effects from water level readings</li>
        <li><b>Master Barologger:</b> Combined dataset from multiple barologgers for site-wide use</li>
        <li><b>Data Quality:</b> Gap detection and validation ensure reliable pressure data</li>
        <li><b>Temperature Monitoring:</b> Additional environmental data for quality assessment</li>
        </ul>
        
        <h3>🔘 Button Guide</h3>
        
        <h4>Equipment Management</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">When to Use</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Add Barologger</b></td>
            <td style="padding: 8px;">Register new barometric pressure sensor</td>
            <td style="padding: 8px;">When deploying new equipment</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Edit</b></td>
            <td style="padding: 8px;">Modify barologger information</td>
            <td style="padding: 8px;">Update location, status, or notes</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Delete</b></td>
            <td style="padding: 8px;">Remove barologger from database</td>
            <td style="padding: 8px;">Equipment permanently removed</td>
        </tr>
        </table>
        
        <h4>Data Import</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Process</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Import Single File</b></td>
            <td style="padding: 8px;">Import individual XLE file</td>
            <td style="padding: 8px;">Select file → Validate → Import to database</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Import Folder</b></td>
            <td style="padding: 8px;">Batch import multiple XLE files</td>
            <td style="padding: 8px;">Select folder → Process all XLE files</td>
        </tr>
        </table>
        
        <h4>Master Barologger</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Purpose</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Create Master Baro</b></td>
            <td style="padding: 8px;">Generate combined pressure dataset</td>
            <td style="padding: 8px;">Site-wide barometric compensation</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Edit Master Baro</b></td>
            <td style="padding: 8px;">Modify existing master dataset</td>
            <td style="padding: 8px;">Update after new data imports</td>
        </tr>
        </table>
        
        <h4>Visualization Controls</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Display</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Show Temperature</b></td>
            <td style="padding: 8px;">Toggle temperature data display</td>
            <td style="padding: 8px;">Temperature trends over time</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Show Pressure</b></td>
            <td style="padding: 8px;">Toggle pressure data display</td>
            <td style="padding: 8px;">Barometric pressure trends</td>
        </tr>
        </table>
        
        <h3>📊 Barologger Table Information</h3>
        
        <h4>Table Columns</h4>
        <ul>
        <li><b>Serial Number:</b> Unique identifier for each barologger</li>
        <li><b>Location:</b> Deployment site or descriptive name</li>
        <li><b>Status:</b> Active, Inactive, or Retired</li>
        <li><b>Installation Date:</b> When barologger was deployed</li>
        <li><b>Last Data Update:</b> Most recent data import timestamp</li>
        <li><b>Notes:</b> Additional information or maintenance records</li>
        </ul>
        
        <h4>Selection Features</h4>
        <ul>
        <li><b>Multi-selection:</b> Hold Ctrl/Cmd to select multiple barologgers</li>
        <li><b>Selection info:</b> Shows count of selected barologgers</li>
        <li><b>Visualization:</b> Selected barologgers appear in plot</li>
        <li><b>Color coding:</b> Each barologger gets unique plot color</li>
        </ul>
        
        <h3>📊 Workflows</h3>
        
        <h4>Setting Up New Barologger</h4>
        <ol>
        <li>Click <b>"Add Barologger"</b></li>
        <li>Enter serial number (from barologger label)</li>
        <li>Specify deployment location</li>
        <li>Set installation date</li>
        <li>Add descriptive notes</li>
        <li>Click Save to register in database</li>
        <li>Barologger appears in table as "Active"</li>
        </ol>
        
        <h4>Importing Barologger Data</h4>
        <ol>
        <li>Download XLE files from barologger</li>
        <li>Choose import method:
            <ul>
            <li><b>Single File:</b> For individual XLE files</li>
            <li><b>Folder:</b> For multiple files at once</li>
            </ul>
        </li>
        <li>Select file(s) or folder containing XLE files</li>
        <li>System validates files and checks for existing data</li>
        <li>Progress dialog shows import status</li>
        <li>Review import summary for any errors</li>
        <li>Verify data appears in visualization plot</li>
        </ol>
        
        <h4>Creating Master Barometric Pressure Dataset</h4>
        <ol>
        <li>Ensure all barologgers have current data imported</li>
        <li>Click <b>"Create Master Baro"</b></li>
        <li>System analyzes all available barologger data</li>
        <li>Configure parameters:
            <ul>
            <li>Time period for master dataset</li>
            <li>Gap filling preferences</li>
            <li>Averaging method</li>
            </ul>
        </li>
        <li>Review data quality statistics</li>
        <li>Confirm creation of master dataset</li>
        <li>Master baro becomes available for water level compensation</li>
        </ol>
        
        <h4>Data Quality Assessment</h4>
        <ol>
        <li>Select barologger(s) in table</li>
        <li>Review pressure plot for:
            <ul>
            <li>Data gaps (missing periods)</li>
            <li>Unusual spikes or drops</li>
            <li>Drift or sensor issues</li>
            </ul>
        </li>
        <li>Toggle temperature view to check environmental conditions</li>
        <li>Compare multiple barologgers for consistency</li>
        <li>Note any issues in barologger notes field</li>
        <li>Re-import or flag problematic data as needed</li>
        </ol>
        
        <h3>💡 Tips & Best Practices</h3>
        
        <h4>Equipment Management</h4>
        <ul>
        <li><b>Unique locations:</b> Deploy barologgers away from buildings and heat sources</li>
        <li><b>Redundancy:</b> Use multiple barologgers for important sites</li>
        <li><b>Regular downloads:</b> Collect data monthly to prevent loss</li>
        <li><b>Calibration tracking:</b> Record calibration dates in notes</li>
        </ul>
        
        <h4>Data Import</h4>
        <ul>
        <li><b>Batch processing:</b> Use folder import for efficiency</li>
        <li><b>Chronological order:</b> Import older data first</li>
        <li><b>Validation:</b> Always review import summaries</li>
        <li><b>Backup files:</b> Keep original XLE files archived</li>
        </ul>
        
        <h4>Master Barologger</h4>
        <ul>
        <li><b>Update regularly:</b> Regenerate after each data import</li>
        <li><b>Quality over quantity:</b> Exclude problematic data periods</li>
        <li><b>Documentation:</b> Record master baro creation settings</li>
        <li><b>Validation:</b> Compare with weather station data when available</li>
        </ul>
        
        <h3>🔧 Troubleshooting</h3>
        
        <h4>Import Failures</h4>
        <ul>
        <li><b>File format:</b> Ensure files are valid XLE format</li>
        <li><b>Serial number mismatch:</b> XLE serial must match registered barologger</li>
        <li><b>Date conflicts:</b> Check for overlapping time periods</li>
        <li><b>File corruption:</b> Re-download from barologger if needed</li>
        </ul>
        
        <h4>Missing Data in Plots</h4>
        <ul>
        <li><b>Selection:</b> Ensure barologger is selected in table</li>
        <li><b>Date range:</b> Zoom out to see full data range</li>
        <li><b>Import status:</b> Verify data was successfully imported</li>
        <li><b>Database connection:</b> Check that correct database is active</li>
        </ul>
        
        <h4>Master Barologger Issues</h4>
        <ul>
        <li><b>Insufficient data:</b> Need overlapping periods from multiple barologgers</li>
        <li><b>Quality problems:</b> Review individual barologger data first</li>
        <li><b>Gap filling:</b> Adjust gap tolerance settings</li>
        <li><b>Time synchronization:</b> Check for clock drift between instruments</li>
        </ul>
        
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>🎯 Critical Point:</b> Accurate barometric compensation is essential for meaningful water level data. 
        Always ensure your master barologger dataset covers the same time period as your water level measurements 
        and represents the atmospheric conditions at your monitoring site.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(barologger_help_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "🌡️ Barologger")
    
    def create_water_level_tab_help(self):
        """Create Water Level tab help."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        water_level_help_html = """
        <h2>🌊 Water Level Tab - Data Collection & Analysis</h2>
        
        <h3>Purpose & Overview</h3>
        <p>The Water Level tab is the primary interface for managing groundwater monitoring data. It handles 
        well registration, transducer management, data import from multiple sources, and provides tools for 
        data visualization and quality assessment. This tab integrates data from automatic transducers, 
        telemetry systems, and manual field measurements.</p>
        
        <h3>🎯 Key Concepts</h3>
        <ul>
        <li><b>Wells:</b> Physical monitoring points with location and construction details</li>
        <li><b>Transducers:</b> Automatic sensors that record water level and temperature</li>
        <li><b>Telemetry:</b> Remote data transmission systems (like MONET)</li>
        <li><b>Manual Readings:</b> Field measurements taken by technicians</li>
        <li><b>Data Gaps:</b> Missing data periods that need attention</li>
        <li><b>Status Flags:</b> Visual indicators for data quality issues</li>
        </ul>
        
        <h3>🔘 Button Guide</h3>
        
        <h4>Well Management</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Required Information</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Add Well</b></td>
            <td style="padding: 8px;">Register new monitoring well</td>
            <td style="padding: 8px;">Well number, coordinates, construction details</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Edit Well</b></td>
            <td style="padding: 8px;">Modify well information</td>
            <td style="padding: 8px;">Updated coordinates, construction, or notes</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Delete Well</b></td>
            <td style="padding: 8px;">Remove well from database</td>
            <td style="padding: 8px;">Confirmation (deletes all associated data)</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Import CSV</b></td>
            <td style="padding: 8px;">Bulk import well information</td>
            <td style="padding: 8px;">CSV file with well data columns</td>
        </tr>
        </table>
        
        <h4>Transducer Management</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Process</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Add Transducer</b></td>
            <td style="padding: 8px;">Register new sensor</td>
            <td style="padding: 8px;">Enter serial number and assign to well</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Edit Transducer</b></td>
            <td style="padding: 8px;">Modify sensor information</td>
            <td style="padding: 8px;">Update well assignment or calibration</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Delete Transducer</b></td>
            <td style="padding: 8px;">Remove sensor record</td>
            <td style="padding: 8px;">Confirm removal (keeps historical data)</td>
        </tr>
        </table>
        
        <h4>Data Import & Collection</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Data Source</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Import XLE Files</b></td>
            <td style="padding: 8px;">Import transducer data</td>
            <td style="padding: 8px;">Solinst XLE files from data loggers</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Fetch Telemetry</b></td>
            <td style="padding: 8px;">Download remote data</td>
            <td style="padding: 8px;">MONET or other telemetry systems</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Add Manual Reading</b></td>
            <td style="padding: 8px;">Enter field measurements</td>
            <td style="padding: 8px;">Manual tape measurements or CSV import</td>
        </tr>
        </table>
        
        <h4>Data Management & Visualization</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Purpose</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Edit Data</b></td>
            <td style="padding: 8px;">Modify water level readings</td>
            <td style="padding: 8px;">Correct erroneous data points</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Refresh Tab</b></td>
            <td style="padding: 8px;">Update all data displays</td>
            <td style="padding: 8px;">Reflect recent database changes</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Show Temperature</b></td>
            <td style="padding: 8px;">Toggle temperature display</td>
            <td style="padding: 8px;">View environmental conditions</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Show Data Gaps</b></td>
            <td style="padding: 8px;">Highlight missing data</td>
            <td style="padding: 8px;">Identify collection problems</td>
        </tr>
        </table>
        
        <h3>📊 Interface Elements</h3>
        
        <h4>Wells Table</h4>
        <p>The wells table shows all monitoring points with status indicators:</p>
        <ul>
        <li><b>Well Number:</b> Unique identifier (often includes site code)</li>
        <li><b>CAE Number:</b> State or agency well identification</li>
        <li><b>Location/Field:</b> Site description or coordinates</li>
        <li><b>Status Flags:</b> Green/red indicators for data quality:
            <ul>
            <li><b>Baro Flag:</b> Green = has master baro assignment</li>
            <li><b>Level Flag:</b> Green = recent data available</li>
            </ul>
        </li>
        <li><b>Last Reading:</b> Most recent data timestamp</li>
        <li><b>Notes:</b> Additional information or alerts</li>
        </ul>
        
        <h4>Transducers Table</h4>
        <p>Shows registered sensors and their assignments:</p>
        <ul>
        <li><b>Serial Number:</b> Manufacturer's unique identifier</li>
        <li><b>Well Assignment:</b> Which well the sensor is monitoring</li>
        <li><b>Installation Date:</b> When sensor was deployed</li>
        <li><b>Status:</b> Active, inactive, or maintenance</li>
        <li><b>Calibration Info:</b> Last calibration or verification</li>
        </ul>
        
        <h4>Data Visualization Plot</h4>
        <p>Interactive timeline showing:</p>
        <ul>
        <li><b>Water Level Trends:</b> Time series of corrected water levels</li>
        <li><b>Temperature Data:</b> Environmental conditions (optional)</li>
        <li><b>Data Gaps:</b> Highlighted periods with missing data</li>
        <li><b>Navigation Controls:</b> Zoom, pan, reset view</li>
        <li><b>Multi-well Display:</b> Compare multiple wells simultaneously</li>
        </ul>
        
        <h3>📊 Workflows</h3>
        
        <h4>Setting Up New Monitoring Well</h4>
        <ol>
        <li>Click <b>"Add Well"</b></li>
        <li>Enter required information:
            <ul>
            <li>Well number (unique identifier)</li>
            <li>CAE number (if applicable)</li>
            <li>Latitude and longitude coordinates</li>
            <li>Well construction details (depth, casing, screen)</li>
            <li>Site description and notes</li>
            </ul>
        </li>
        <li>Save well record</li>
        <li>Click <b>"Add Transducer"</b> to register sensor</li>
        <li>Assign transducer to the new well</li>
        <li>Well appears in table ready for data collection</li>
        </ol>
        
        <h4>Importing Transducer Data</h4>
        <ol>
        <li>Download XLE files from transducers</li>
        <li>Click <b>"Import XLE Files"</b></li>
        <li>Select file(s) or folder containing XLE data</li>
        <li>System validates files and matches to registered transducers</li>
        <li>Review import dialog:
            <ul>
            <li>Check detected transducer assignments</li>
            <li>Verify date ranges</li>
            <li>Confirm barometric compensation settings</li>
            </ul>
        </li>
        <li>Click Import to process data</li>
        <li>Monitor progress dialog for completion</li>
        <li>Review import summary for any errors</li>
        <li>Verify data appears in visualization plot</li>
        </ol>
        
        <h4>Telemetry Data Collection</h4>
        <ol>
        <li>Ensure telemetry wells are properly configured</li>
        <li>Click <b>"Fetch Telemetry"</b></li>
        <li>System connects to MONET or configured telemetry service</li>
        <li>Progress dialog shows data download status</li>
        <li>Review new data summary</li>
        <li>Data automatically appears in database and plots</li>
        <li>Check for any connection or data quality issues</li>
        </ol>
        
        <h4>Manual Reading Management</h4>
        <ol>
        <li>Collect field measurements using tape or other methods</li>
        <li>Choose data entry method:
            <ul>
            <li><b>Single entry:</b> Click "Add Manual Reading"</li>
            <li><b>Bulk entry:</b> Prepare CSV file and import</li>
            </ul>
        </li>
        <li>For single entry:
            <ul>
            <li>Select well from dropdown</li>
            <li>Enter measurement date and time</li>
            <li>Record water level depth</li>
            <li>Add measurement notes</li>
            </ul>
        </li>
        <li>For CSV import:
            <ul>
            <li>Format CSV with required columns</li>
            <li>Import and validate data</li>
            <li>Review and confirm entries</li>
            </ul>
        </li>
        <li>Manual readings appear on visualization plots</li>
        </ol>
        
        <h4>Data Quality Assessment</h4>
        <ol>
        <li>Select wells of interest in wells table</li>
        <li>Review visualization plot for:
            <ul>
            <li>Unusual spikes or drops</li>
            <li>Sensor drift or calibration issues</li>
            <li>Missing data periods</li>
            <li>Inconsistent trends</li>
            </ul>
        </li>
        <li>Click <b>"Show Data Gaps"</b> to highlight missing periods</li>
        <li>Toggle temperature view to check environmental conditions</li>
        <li>Use <b>"Edit Data"</b> to correct obvious errors</li>
        <li>Document findings in well notes</li>
        <li>Plan corrective actions (sensor maintenance, re-import, etc.)</li>
        </ol>
        
        <h3>💡 Tips & Best Practices</h3>
        
        <h4>Well Management</h4>
        <ul>
        <li><b>Consistent naming:</b> Use standardized well numbering system</li>
        <li><b>Accurate coordinates:</b> Use GPS for precise well locations</li>
        <li><b>Complete records:</b> Document all well construction details</li>
        <li><b>Regular updates:</b> Keep notes current with maintenance activities</li>
        </ul>
        
        <h4>Data Collection</h4>
        <ul>
        <li><b>Regular downloads:</b> Collect transducer data monthly</li>
        <li><b>Backup originals:</b> Archive original XLE files</li>
        <li><b>Validate imports:</b> Always review import summaries</li>
        <li><b>Multiple sources:</b> Use telemetry plus manual verification</li>
        </ul>
        
        <h4>Quality Control</h4>
        <ul>
        <li><b>Daily monitoring:</b> Check status flags regularly</li>
        <li><b>Gap awareness:</b> Identify and address missing data quickly</li>
        <li><b>Cross-validation:</b> Compare automatic and manual readings</li>
        <li><b>Environmental context:</b> Consider weather and seasonal patterns</li>
        </ul>
        
        <h3>🔧 Troubleshooting</h3>
        
        <h4>Import Problems</h4>
        <ul>
        <li><b>Serial number mismatch:</b> Ensure transducers are registered</li>
        <li><b>Date conflicts:</b> Check for overlapping time periods</li>
        <li><b>Missing barometric data:</b> Import barologger data first</li>
        <li><b>File corruption:</b> Re-download from instrument</li>
        </ul>
        
        <h4>Telemetry Issues</h4>
        <ul>
        <li><b>Connection failures:</b> Check network connectivity</li>
        <li><b>Authentication:</b> Verify MONET credentials</li>
        <li><b>No new data:</b> Confirm instrument is transmitting</li>
        <li><b>Incomplete downloads:</b> Retry or check instrument status</li>
        </ul>
        
        <h4>Visualization Problems</h4>
        <ul>
        <li><b>No data displayed:</b> Check well selection and date range</li>
        <li><b>Strange trends:</b> Verify barometric compensation</li>
        <li><b>Performance issues:</b> Use data aggregation for large datasets</li>
        <li><b>Missing recent data:</b> Check import status and dates</li>
        </ul>
        
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>🎯 Critical Success Factor:</b> Consistent data collection and quality control are essential 
        for reliable groundwater monitoring. Establish regular routines for data download, validation, 
        and gap identification to maintain high-quality datasets.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(water_level_help_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "🌊 Water Level")
        
    def create_runs_tab_help(self):
        """Create Water Level Runs tab help."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        runs_help_html = """
        <h2>📋 Water Level Runs Tab - Field Data Collection Management</h2>
        
        <h3>Purpose & Overview</h3>
        <p>The Water Level Runs tab coordinates field data collection activities by creating organized 
        "runs" that define which wells to visit and when. It integrates with Google Drive for cloud-based 
        field data management, automatically processes collected XLE files, and tracks the status of 
        data collection activities across your monitoring network.</p>
        
        <h3>🎯 Key Concepts</h3>
        <ul>
        <li><b>Field Run:</b> A planned collection event targeting specific wells on a particular date</li>
        <li><b>Cloud Integration:</b> Automatic sync with Google Drive for field data storage</li>
        <li><b>Status Tracking:</b> Visual indicators showing data collection progress</li>
        <li><b>Consolidated Folder:</b> Centralized cloud storage for all field data</li>
        <li><b>Run Coordination:</b> Ensures systematic coverage of monitoring network</li>
        </ul>
        
        <h3>🔘 Button Guide</h3>
        
        <h4>Run Management</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Process</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Create New Run</b></td>
            <td style="padding: 8px;">Generate new field collection schedule</td>
            <td style="padding: 8px;">Select date → Choose wells → Create run files</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Reload Run</b></td>
            <td style="padding: 8px;">Refresh run data from cloud storage</td>
            <td style="padding: 8px;">Download latest status and field data</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Sync Google Drive</b></td>
            <td style="padding: 8px;">Download and process new field data</td>
            <td style="padding: 8px;">Scan cloud folder → Import XLE files</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Update Monet Data</b></td>
            <td style="padding: 8px;">Fetch telemetry data for run wells</td>
            <td style="padding: 8px;">Connect to MONET → Download readings</td>
        </tr>
        </table>
        
        <h4>Well Selection (in New Run Dialog)</h4>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Button</th>
            <th style="padding: 8px;">Function</th>
            <th style="padding: 8px;">Effect</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Select All</b></td>
            <td style="padding: 8px;">Include all wells in run</td>
            <td style="padding: 8px;">Checks all wells for collection</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Deselect All</b></td>
            <td style="padding: 8px;">Remove all wells from run</td>
            <td style="padding: 8px;">Unchecks all wells</td>
        </tr>
        </table>
        
        <h3>📊 Interface Elements</h3>
        
        <h4>Run Selection Dropdown</h4>
        <p>Lists all available field runs by date and status:</p>
        <ul>
        <li><b>Date Format:</b> YYYY-MM-DD for easy chronological sorting</li>
        <li><b>Run Status:</b> Indicates completion level and data availability</li>
        <li><b>Well Count:</b> Shows number of wells included in each run</li>
        <li><b>Cloud Status:</b> Indicates if run data is cloud-synchronized</li>
        </ul>
        
        <h4>Wells Table View</h4>
        <p>Shows wells included in the selected run with detailed status:</p>
        <ul>
        <li><b>Include Checkbox:</b> Whether well is part of the run</li>
        <li><b>Transducer Status:</b> Indicator for automatic data collection</li>
        <li><b>Manual Status:</b> Indicator for field measurement collection</li>
        <li><b>Well Information:</b> Number, CAE, field, and location details</li>
        <li><b>Last Readings:</b> Most recent water level and manual measurements</li>
        <li><b>Notes:</b> Field observations and status updates</li>
        </ul>
        
        <h4>Map View</h4>
        <p>Interactive geographical display of run wells:</p>
        <ul>
        <li><b>Well Locations:</b> Precise GPS coordinates on interactive map</li>
        <li><b>Status Markers:</b> Color-coded indicators for collection status</li>
        <li><b>Route Planning:</b> Visual aid for efficient field visits</li>
        <li><b>Zoom Controls:</b> Navigate to specific areas or wells</li>
        <li><b>Layer Toggle:</b> Switch between different map views</li>
        </ul>
        
        <h4>Well Selection Dialog (for New Runs)</h4>
        <p>Comprehensive well selection interface:</p>
        <ul>
        <li><b>Multi-column Display:</b> All wells with detailed information</li>
        <li><b>Status Indicators:</b> Shows which wells have recent data</li>
        <li><b>Filtering Options:</b> Select wells by field, status, or data needs</li>
        <li><b>Bulk Operations:</b> Select/deselect groups of wells efficiently</li>
        <li><b>Preview:</b> Shows count of selected wells before creating run</li>
        </ul>
        
        <h3>📊 Workflows</h3>
        
        <h4>Creating a New Field Run</h4>
        <ol>
        <li>Click <b>"Create New Run"</b></li>
        <li>In the run creation dialog:
            <ul>
            <li>Select target date for field collection</li>
            <li>Review all available wells in selection table</li>
            <li>Check wells that need data collection</li>
            <li>Use status indicators to prioritize wells</li>
            <li>Consider geographical clustering for efficiency</li>
            </ul>
        </li>
        <li>Use selection tools:
            <ul>
            <li><b>"Select All"</b> for comprehensive runs</li>
            <li><b>"Deselect All"</b> to start fresh</li>
            <li>Individual checkboxes for specific wells</li>
            </ul>
        </li>
        <li>Review selection count and click OK</li>
        <li>System creates run and uploads to Google Drive</li>
        <li>New run appears in dropdown and is ready for field work</li>
        </ol>
        
        <h4>Managing Active Field Run</h4>
        <ol>
        <li>Select run from dropdown</li>
        <li>Review wells table for collection targets</li>
        <li>Use map view for route planning:
            <ul>
            <li>Identify well clusters</li>
            <li>Plan efficient travel routes</li>
            <li>Note access considerations</li>
            </ul>
        </li>
        <li>During field work:
            <ul>
            <li>Download transducer data to field devices</li>
            <li>Upload XLE files to Google Drive</li>
            <li>Take manual measurements as needed</li>
            </ul>
        </li>
        <li>Return to office and click <b>"Sync Google Drive"</b></li>
        <li>Review updated status indicators</li>
        </ol>
        
        <h4>Processing Field Data</h4>
        <ol>
        <li>After field collection, click <b>"Sync Google Drive"</b></li>
        <li>System scans consolidated cloud folder for new XLE files</li>
        <li>Progress dialog shows file discovery and processing</li>
        <li>Files are automatically:
            <ul>
            <li>Downloaded from cloud storage</li>
            <li>Validated for format and content</li>
            <li>Matched to registered transducers</li>
            <li>Imported to project database</li>
            <li>Organized by month in cloud folders</li>
            </ul>
        </li>
        <li>Review sync summary for any issues</li>
        <li>Click <b>"Reload Run"</b> to see updated status</li>
        <li>Verify data appears in other tabs</li>
        </ol>
        
        <h4>Telemetry Integration</h4>
        <ol>
        <li>Ensure telemetry wells are included in run</li>
        <li>Click <b>"Update Monet Data"</b></li>
        <li>System connects to MONET telemetry service</li>
        <li>Downloads latest readings for run wells</li>
        <li>Progress dialog shows download status</li>
        <li>New telemetry data appears in database</li>
        <li>Status indicators update to reflect new data</li>
        <li>Combine with field-collected data for complete picture</li>
        </ol>
        
        <h4>Run Status Monitoring</h4>
        <ol>
        <li>Select run from dropdown</li>
        <li>Review status indicators in wells table:
            <ul>
            <li><b>Green flags:</b> Recent data available</li>
            <li><b>Red flags:</b> Missing or outdated data</li>
            <li><b>Status columns:</b> Specific data collection types</li>
            </ul>
        </li>
        <li>Switch to map view for geographical overview</li>
        <li>Identify wells still needing attention</li>
        <li>Plan follow-up collection activities</li>
        <li>Document completion status in notes</li>
        </ol>
        
        <h3>💡 Tips & Best Practices</h3>
        
        <h4>Run Planning</h4>
        <ul>
        <li><b>Regular schedule:</b> Create runs on consistent intervals (monthly/quarterly)</li>
        <li><b>Geographic efficiency:</b> Group wells by location for travel efficiency</li>
        <li><b>Priority-based selection:</b> Focus on wells with oldest data first</li>
        <li><b>Weather considerations:</b> Plan around seasonal access limitations</li>
        </ul>
        
        <h4>Field Operations</h4>
        <ul>
        <li><b>Mobile connectivity:</b> Ensure field devices can upload to cloud</li>
        <li><b>Backup storage:</b> Keep local copies until cloud sync confirmed</li>
        <li><b>Systematic approach:</b> Follow planned routes and check off completed wells</li>
        <li><b>Documentation:</b> Note any issues or anomalies in field notes</li>
        </ul>
        
        <h4>Data Management</h4>
        <ul>
        <li><b>Timely processing:</b> Sync and import data within 24 hours</li>
        <li><b>Quality review:</b> Check imported data for obvious issues</li>
        <li><b>Status tracking:</b> Update run status as data is processed</li>
        <li><b>Archive runs:</b> Keep historical runs for reference and planning</li>
        </ul>
        
        <h3>🔧 Troubleshooting</h3>
        
        <h4>Google Drive Sync Issues</h4>
        <ul>
        <li><b>Authentication:</b> Verify service account credentials are valid</li>
        <li><b>Folder access:</b> Ensure consolidated folder exists and is accessible</li>
        <li><b>File permissions:</b> Check that field team can upload to shared folders</li>
        <li><b>Network connectivity:</b> Verify internet connection during sync</li>
        </ul>
        
        <h4>Missing Field Data</h4>
        <ul>
        <li><b>Upload verification:</b> Confirm files were uploaded to correct folder</li>
        <li><b>File naming:</b> Check that XLE files follow expected naming convention</li>
        <li><b>Date ranges:</b> Verify files contain data for expected time periods</li>
        <li><b>Transducer registration:</b> Ensure instruments are registered in database</li>
        </ul>
        
        <h4>Run Creation Problems</h4>
        <ul>
        <li><b>No wells available:</b> Check that wells are properly registered</li>
        <li><b>Cloud upload failure:</b> Verify Google Drive connectivity</li>
        <li><b>Date conflicts:</b> Ensure run date doesn't conflict with existing runs</li>
        <li><b>Selection issues:</b> Verify wells have required information (coordinates, etc.)</li>
        </ul>
        
        <h4>Status Indicator Problems</h4>
        <ul>
        <li><b>Outdated status:</b> Click "Reload Run" to refresh from database</li>
        <li><b>Import lag:</b> Allow time for data processing after sync</li>
        <li><b>Barometric assignment:</b> Ensure wells have master baro assignments</li>
        <li><b>Date thresholds:</b> Check if "recent data" settings need adjustment</li>
        </ul>
        
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>🎯 Field Operations Success:</b> The Runs tab transforms field data collection from 
        ad-hoc activities into systematic, trackable operations. Regular use ensures consistent 
        data collection across your entire monitoring network and provides clear visibility 
        into collection status and data gaps.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(runs_help_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "📋 Runs")
        
    def create_recharge_tab_help(self):
        """Create Recharge tab help with detailed sub-tabs."""
        # Create main recharge tab widget
        recharge_tab = QWidget()
        recharge_layout = QVBoxLayout(recharge_tab)
        
        # Header for recharge section
        header_label = QLabel("💧 Recharge Analysis - Scientific Methods for Groundwater Recharge Estimation")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;")
        header_label.setAlignment(Qt.AlignCenter)
        recharge_layout.addWidget(header_label)
        
        # Create sub-tabs for recharge help
        recharge_help_tabs = QTabWidget()
        
        # Quick Start tab
        self.create_recharge_quick_start_tab(recharge_help_tabs)
        
        # Method Overview tab  
        self.create_recharge_method_overview_tab(recharge_help_tabs)
        
        # Parameter Guide tab
        self.create_recharge_parameter_guide_tab(recharge_help_tabs)
        
        # Scientific References tab
        self.create_recharge_references_tab(recharge_help_tabs)
        
        recharge_layout.addWidget(recharge_help_tabs)
        
        self.help_tabs.addTab(recharge_tab, "💧 Recharge")
    
    def create_recharge_quick_start_tab(self, parent_tabs):
        """Create quick start guide for recharge analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        quick_start_html = """
        <h2>🚀 Quick Start Guide</h2>
        
        <h3>1. Getting Started</h3>
        <ol>
        <li><b>Select Wells:</b> Choose wells from the main 'Available Wells' table</li>
        <li><b>Configure Settings:</b> Click 'Global Settings' to set shared parameters</li>
        <li><b>Choose Method:</b> Select a tab based on your data and objectives</li>
        <li><b>Run Analysis:</b> Follow method-specific steps to calculate recharge</li>
        </ol>
        
        <h3>2. Which Method Should I Use?</h3>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Condition</th>
            <th style="padding: 8px;">Recommended Method</th>
            <th style="padding: 8px;">Why?</th>
        </tr>
        <tr>
            <td style="padding: 8px;">Need quick results, have clear water level rises</td>
            <td style="padding: 8px;"><b>RISE</b></td>
            <td style="padding: 8px;">Simple, fast, requires minimal parameters</td>
        </tr>
        <tr>
            <td style="padding: 8px;">Want statistical validation, have recession periods</td>
            <td style="padding: 8px;"><b>MRC</b></td>
            <td style="padding: 8px;">Robust analysis with curve fitting validation</td>
        </tr>
        <tr>
            <td style="padding: 8px;">Have rainfall data, need storm-specific recharge</td>
            <td style="padding: 8px;"><b>EMR</b> (coming soon)</td>
            <td style="padding: 8px;">Links recharge to specific rainfall events</td>
        </tr>
        </table>
        
        <h3>3. Essential Requirements</h3>
        <ul>
        <li><b>Well Type:</b> Unconfined aquifer (water table well)</li>
        <li><b>Data Frequency:</b> Hourly or better recommended</li>
        <li><b>Data Duration:</b> Minimum 90 days, preferably 1+ years</li>
        <li><b>Specific Yield:</b> Must be known or estimated (see Parameter Guide)</li>
        </ul>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>⚠️ Important:</b> These methods assume the well is in an unconfined aquifer where water level 
        rises directly represent recharge. They are NOT suitable for confined aquifers or wells 
        significantly affected by pumping.
        </div>
        
        <h3>4. Basic Workflow</h3>
        <ol>
        <li><b>Data Quality Check:</b> Ensure continuous, clean water level data</li>
        <li><b>Parameter Selection:</b> Set specific yield and method parameters</li>
        <li><b>Run Analysis:</b> Execute the chosen method</li>
        <li><b>Validate Results:</b> Compare recharge with precipitation patterns</li>
        <li><b>Export Results:</b> Save data and plots for reporting</li>
        </ol>
        """
        
        content = QTextEdit()
        content.setHtml(quick_start_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        parent_tabs.addTab(tab, "Quick Start")
    
    def create_recharge_method_overview_tab(self, parent_tabs):
        """Create method overview for recharge analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        method_overview_html = """
        <h2>📊 Method Overview & Comparison</h2>
        
        <p>All methods are based on the <b>Water Table Fluctuation (WTF)</b> principle: 
        water level rises in unconfined aquifers represent recharge events. The methods differ 
        in how they identify and quantify these rises.</p>
        
        <h3>🔵 RISE Method - Water Level Rise Detection</h3>
        <p><b>Principle:</b> Identifies rapid water level rises that exceed a threshold, 
        indicating recharge events.</p>
        <ul>
        <li><b>How it works:</b> Scans time series for rises > threshold over specified time windows</li>
        <li><b>Recharge calculation:</b> R = Sy × ΔH (rise magnitude)</li>
        <li><b>Best for:</b> Clear recharge signals, high-frequency data</li>
        <li><b>Advantages:</b> Simple, intuitive, fast computation</li>
        <li><b>Limitations:</b> Threshold-dependent, may miss gradual recharge</li>
        </ul>
        
        <h3>🟣 MRC Method - Master Recession Curve</h3>
        <p><b>Principle:</b> Fits a master recession curve to periods of groundwater decline, 
        then identifies deviations above this curve as recharge.</p>
        <ul>
        <li><b>How it works:</b> 
            <ol>
            <li>Identifies recession periods (continuous decline)</li>
            <li>Fits exponential curve: dH/dt = f(H)</li>
            <li>Detects when actual levels exceed predicted recession</li>
            </ol>
        </li>
        <li><b>Recharge calculation:</b> R = Sy × (H_actual - H_predicted)</li>
        <li><b>Best for:</b> Datasets with clear recession periods</li>
        <li><b>Advantages:</b> Statistically robust, handles variable data quality</li>
        <li><b>Limitations:</b> Requires adequate recession periods</li>
        </ul>
        
        <h3>🟠 EMR Method - Episodic Master Recession (Under Development)</h3>
        <p><b>Principle:</b> Extends MRC by linking each recharge event to specific rainfall episodes.</p>
        <ul>
        <li><b>How it works:</b> 
            <ol>
            <li>Uses MRC approach to identify recharge</li>
            <li>Correlates recharge events with antecedent rainfall</li>
            <li>Calculates lag time and recharge efficiency</li>
            </ol>
        </li>
        <li><b>Additional outputs:</b> 
            <ul>
            <li>Recharge per storm (mm recharge / mm rainfall)</li>
            <li>Lag time between rainfall and recharge</li>
            <li>Storm efficiency patterns</li>
            </ul>
        </li>
        <li><b>Requirements:</b> Precipitation time series data</li>
        <li><b>Status:</b> Coming soon - requires rainfall data integration</li>
        </ul>
        
        <h3>📈 Method Comparison Table</h3>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Feature</th>
            <th style="padding: 8px;">RISE</th>
            <th style="padding: 8px;">MRC</th>
            <th style="padding: 8px;">EMR</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Complexity</b></td>
            <td style="padding: 8px;">Low</td>
            <td style="padding: 8px;">Medium</td>
            <td style="padding: 8px;">High</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Data Requirements</b></td>
            <td style="padding: 8px;">Water levels only</td>
            <td style="padding: 8px;">Water levels only</td>
            <td style="padding: 8px;">Water levels + rainfall</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Computation Speed</b></td>
            <td style="padding: 8px;">Fast</td>
            <td style="padding: 8px;">Moderate</td>
            <td style="padding: 8px;">Moderate</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Best Data Frequency</b></td>
            <td style="padding: 8px;">Hourly or better</td>
            <td style="padding: 8px;">Daily acceptable</td>
            <td style="padding: 8px;">Hourly or better</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Validation Method</b></td>
            <td style="padding: 8px;">Visual inspection</td>
            <td style="padding: 8px;">R² of curve fit</td>
            <td style="padding: 8px;">Rainfall correlation</td>
        </tr>
        </table>
        
        <h3>🎯 Key Assumptions (All Methods)</h3>
        <ol>
        <li>Well is in an <b>unconfined aquifer</b> (not confined or perched)</li>
        <li>Water level rises are due to <b>vertical recharge</b> (not lateral flow)</li>
        <li><b>Specific yield</b> is constant and known</li>
        <li>Other influences (pumping, ET) are <b>negligible or accounted for</b></li>
        <li>Response to recharge is <b>relatively rapid</b> (hours to days)</li>
        </ol>
        """
        
        content = QTextEdit()
        content.setHtml(method_overview_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        parent_tabs.addTab(tab, "Method Overview")
        
    def create_recharge_parameter_guide_tab(self, parent_tabs):
        """Create parameter guide for recharge analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        parameter_guide_html = """
        <h2>⚙️ Parameter Guide</h2>
        
        <p>This guide explains all parameters used in recharge analysis, their typical values, 
        and how to determine appropriate values for your site.</p>
        
        <h3>🔑 Critical Parameters (All Methods)</h3>
        
        <h4>Specific Yield (Sy)</h4>
        <ul>
        <li><b>What it is:</b> The volume of water released from storage per unit surface area 
        per unit decline in water table (dimensionless)</li>
        <li><b>Typical values:</b>
            <table border="1" style="margin: 5px 0;">
            <tr><td style="padding: 5px;">Gravel</td><td style="padding: 5px;">0.15 - 0.30</td></tr>
            <tr><td style="padding: 5px;">Coarse sand</td><td style="padding: 5px;">0.20 - 0.35</td></tr>
            <tr><td style="padding: 5px;">Medium sand</td><td style="padding: 5px;">0.15 - 0.25</td></tr>
            <tr><td style="padding: 5px;">Fine sand</td><td style="padding: 5px;">0.10 - 0.20</td></tr>
            <tr><td style="padding: 5px;">Silt</td><td style="padding: 5px;">0.05 - 0.15</td></tr>
            <tr><td style="padding: 5px;">Clay</td><td style="padding: 5px;">0.01 - 0.10</td></tr>
            </table>
        </li>
        <li><b>Why it matters:</b> Directly proportional to recharge calculation (R = Sy × ΔH)</li>
        <li><b>How to determine:</b> 
            <ol>
            <li>Best: Aquifer pumping tests or slug tests</li>
            <li>Good: Laboratory analysis of soil samples</li>
            <li>Acceptable: Literature values for similar materials</li>
            </ol>
        </li>
        <li><b>Common pitfalls:</b> Using porosity instead of specific yield (Sy < porosity)</li>
        </ul>
        
        <h4>Water Year Definition</h4>
        <ul>
        <li><b>What it is:</b> Start date for annual recharge calculations</li>
        <li><b>Typical values:</b> 
            <ul>
            <li>US standard: October 1 (captures fall/winter recharge)</li>
            <li>Calendar year: January 1</li>
            <li>Site-specific: Based on local hydrology</li>
            </ul>
        </li>
        <li><b>Why it matters:</b> Affects annual recharge totals and seasonal patterns</li>
        <li><b>How to determine:</b> Consider when groundwater is typically at annual minimum</li>
        </ul>
        
        <h3>📈 RISE Method Parameters</h3>
        
        <h4>Rise Threshold</h4>
        <ul>
        <li><b>What it is:</b> Minimum water level rise (ft) to identify as recharge event</li>
        <li><b>Typical values:</b> 0.1 - 0.5 ft (adjust based on well sensitivity)</li>
        <li><b>Why it matters:</b> Too low = noise detected as recharge; Too high = miss small events</li>
        <li><b>How to determine:</b> 
            <ol>
            <li>Analyze background noise level in data</li>
            <li>Set threshold 2-3× above noise level</li>
            <li>Validate against known rainfall events</li>
            </ol>
        </li>
        </ul>
        
        <h4>Minimum Time Between Events</h4>
        <ul>
        <li><b>What it is:</b> Minimum days between separate recharge events</li>
        <li><b>Typical values:</b> 1-3 days</li>
        <li><b>Why it matters:</b> Prevents double-counting of single recharge events</li>
        </ul>
        
        <h3>📉 MRC Method Parameters</h3>
        
        <h4>Minimum Recession Length</h4>
        <ul>
        <li><b>What it is:</b> Minimum consecutive days of water level decline for valid recession</li>
        <li><b>Typical values:</b> 7-14 days</li>
        <li><b>Why it matters:</b> Shorter periods may not represent true groundwater recession</li>
        <li><b>How to determine:</b> Examine typical dry period durations in your data</li>
        </ul>
        
        <h4>Fluctuation Tolerance</h4>
        <ul>
        <li><b>What it is:</b> Maximum daily rise (ft) allowed during recession period</li>
        <li><b>Typical values:</b> 0.01 - 0.05 ft</li>
        <li><b>Why it matters:</b> Allows for measurement noise while maintaining recession integrity</li>
        </ul>
        
        <h4>Deviation Threshold</h4>
        <ul>
        <li><b>What it is:</b> Minimum deviation (ft) above recession curve to identify recharge</li>
        <li><b>Typical values:</b> 0.05 - 0.2 ft</li>
        <li><b>Why it matters:</b> Similar to rise threshold - balances sensitivity vs. noise</li>
        </ul>
        
        <h3>📊 Data Preprocessing Parameters</h3>
        
        <h4>Downsampling Frequency</h4>
        <ul>
        <li><b>Options:</b> None, Hourly, Daily, Weekly</li>
        <li><b>Recommendation:</b> Daily for most analyses</li>
        <li><b>Why it matters:</b> Reduces noise and computation time</li>
        </ul>
        
        <h4>Smoothing Window</h4>
        <ul>
        <li><b>What it is:</b> Number of data points for moving average</li>
        <li><b>Typical values:</b> 3-7 points</li>
        <li><b>Why it matters:</b> Reduces noise but may smooth out real events if too large</li>
        </ul>
        
        <h4>Outlier Threshold</h4>
        <ul>
        <li><b>What it is:</b> Standard deviations from mean to identify outliers</li>
        <li><b>Typical values:</b> 3.0 (removes ~0.3% of data)</li>
        <li><b>Why it matters:</b> Removes erroneous spikes that could be misidentified as recharge</li>
        </ul>
        
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>💡 Pro Tip:</b> Start with default values and adjust based on your results. If you're 
        getting too many small "recharge" events, increase thresholds. If missing known events, 
        decrease thresholds.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(parameter_guide_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        parent_tabs.addTab(tab, "Parameter Guide")
    
    def create_recharge_references_tab(self, parent_tabs):
        """Create scientific references for recharge analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add specific yield calculator button at top
        calc_layout = QHBoxLayout()
        calc_btn = QPushButton("🧮 Open Specific Yield Calculator")
        calc_btn.clicked.connect(self.open_sy_calculator)
        calc_layout.addWidget(calc_btn)
        calc_layout.addStretch()
        layout.addLayout(calc_layout)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        references_html = """
        <h2>📚 Scientific References & Resources</h2>
        
        <h3>Core Methods Papers</h3>
        
        <h4>Water Table Fluctuation Method</h4>
        <ul>
        <li><b>Healy, R.W. and Cook, P.G., 2002.</b> Using groundwater levels to estimate recharge. 
        <i>Hydrogeology Journal</i>, 10(1), pp.91-109. 
        <a href="#" onclick="return false;" style="color: #0066cc;">[DOI: 10.1007/s10040-001-0178-0]</a>
        <br><i>The foundational paper on WTF methods - comprehensive review of theory and applications</i></li>
        </ul>
        
        <h4>Episodic Master Recession (EMR) Method</h4>
        <ul>
        <li><b>Nimmo, J.R., Horowitz, C. and Mitchell, L., 2015.</b> Discrete-storm water-table 
        fluctuation method to estimate episodic recharge. <i>Groundwater</i>, 53(2), pp.282-292.
        <a href="#" onclick="return false;" style="color: #0066cc;">[DOI: 10.1111/gwat.12177]</a>
        <br><i>Original development of the EMR method linking recharge to specific storms</i></li>
        
        <li><b>Nimmo, J.R. and Perkins, K.S., 2018.</b> Episodic master recession evaluation of 
        groundwater and streamflow hydrographs for water-resource estimation. 
        <i>Vadose Zone Journal</i>, 17(1).
        <a href="#" onclick="return false;" style="color: #0066cc;">[DOI: 10.2136/vzj2018.03.0050]</a>
        <br><i>Updated EMR methodology with improved algorithms and applications</i></li>
        </ul>
        
        <h3>General Recharge Estimation</h3>
        <ul>
        <li><b>Scanlon, B.R., Healy, R.W. and Cook, P.G., 2002.</b> Choosing appropriate techniques 
        for quantifying groundwater recharge. <i>Hydrogeology Journal</i>, 10(1), pp.18-39.
        <a href="#" onclick="return false;" style="color: #0066cc;">[DOI: 10.1007/s10040-001-0176-2]</a>
        <br><i>Comprehensive review of recharge estimation methods and selection criteria</i></li>
        
        <li><b>Healy, R.W., 2010.</b> Estimating groundwater recharge. Cambridge University Press.
        <br><i>Comprehensive textbook on all aspects of groundwater recharge estimation</i></li>
        </ul>
        
        <h3>USGS Resources</h3>
        <ul>
        <li><b>USGS Water Table Fluctuation Method:</b><br>
        <a href="https://water.usgs.gov/ogw/gwrp/methods/wtf/" style="color: #0066cc;">
        https://water.usgs.gov/ogw/gwrp/methods/wtf/</a>
        <br><i>Official USGS guidance on WTF method implementation</i></li>
        
        <li><b>USGS EMR Method Software:</b><br>
        <a href="https://wwwrcamnl.wr.usgs.gov/uzf/EMR_Method/EMR.method.html" style="color: #0066cc;">
        https://wwwrcamnl.wr.usgs.gov/uzf/EMR_Method/EMR.method.html</a>
        <br><i>R-based implementation of EMR method with documentation</i></li>
        
        <li><b>USGS Groundwater Resources Program:</b><br>
        <a href="https://water.usgs.gov/ogw/gwrp/" style="color: #0066cc;">
        https://water.usgs.gov/ogw/gwrp/</a>
        <br><i>Comprehensive groundwater resources and methods</i></li>
        </ul>
        
        <h3>Specific Yield References</h3>
        <ul>
        <li><b>Johnson, A.I., 1967.</b> Specific yield - compilation of specific yields for various 
        materials. <i>U.S. Geological Survey Water Supply Paper</i> 1662-D, 74 p.</li>
        
        <li><b>Morris, D.A. and Johnson, A.I., 1967.</b> Summary of hydrologic and physical 
        properties of rock and soil materials as analyzed by the Hydrologic Laboratory of the 
        U.S. Geological Survey. <i>U.S. Geological Survey Water Supply Paper</i> 1839-D.</li>
        </ul>
        
        <h3>Method Limitations & Considerations</h3>
        <ul>
        <li><b>Crosbie, R.S., Binning, P. and Kalma, J.D., 2005.</b> A time series approach to 
        inferring groundwater recharge using the water table fluctuation method. 
        <i>Water Resources Research</i>, 41(1).
        <br><i>Addresses uncertainties and limitations in WTF methods</i></li>
        
        <li><b>Cuthbert, M.O., 2010.</b> An improved time series approach for estimating 
        groundwater recharge from groundwater level fluctuations. 
        <i>Water Resources Research</i>, 46(9).
        <br><i>Improvements to handle ET and other complicating factors</i></li>
        </ul>
        
        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>📖 Recommended Reading Order:</b>
        <ol>
        <li>Start with Healy & Cook (2002) for WTF method fundamentals</li>
        <li>Read Scanlon et al. (2002) for method selection guidance</li>
        <li>Refer to Nimmo papers for EMR method details (when needed)</li>
        <li>Consult USGS resources for practical implementation</li>
        </ol>
        </div>
        
        <h3>How to Access Papers</h3>
        <p>Many of these papers are available through:</p>
        <ul>
        <li>USGS Publications Warehouse (free): <a href="https://pubs.usgs.gov" style="color: #0066cc;">pubs.usgs.gov</a></li>
        <li>Journal websites (may require subscription)</li>
        <li>ResearchGate or Google Scholar (often have free versions)</li>
        <li>Your institution's library access</li>
        </ul>
        """
        
        content = QTextEdit()
        content.setHtml(references_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        parent_tabs.addTab(tab, "Scientific References")
    
    def open_sy_calculator(self):
        """Open specific yield calculator."""
        calculator = SpecificYieldCalculator(self)
        calculator.exec_()


class SpecificYieldCalculator(QDialog):
    """Enhanced specific yield calculator with estimation tools."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Specific Yield Calculator")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("🧮 Specific Yield Estimation Tool")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Tabs for different estimation methods
        tabs = QTabWidget()
        
        # Typical values tab
        typical_tab = QWidget()
        typical_layout = QVBoxLayout(typical_tab)
        
        typical_content = QTextEdit()
        typical_content.setHtml("""
        <h3>Typical Specific Yield Values by Material</h3>
        
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Material Type</th>
            <th style="padding: 8px;">Specific Yield Range</th>
            <th style="padding: 8px;">Typical Value</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Gravel</b></td>
            <td style="padding: 8px;">0.15 - 0.30</td>
            <td style="padding: 8px;">0.22</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Coarse sand</b></td>
            <td style="padding: 8px;">0.20 - 0.35</td>
            <td style="padding: 8px;">0.27</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Medium sand</b></td>
            <td style="padding: 8px;">0.15 - 0.25</td>
            <td style="padding: 8px;">0.20</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Fine sand</b></td>
            <td style="padding: 8px;">0.10 - 0.20</td>
            <td style="padding: 8px;">0.15</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Very fine sand</b></td>
            <td style="padding: 8px;">0.05 - 0.15</td>
            <td style="padding: 8px;">0.10</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Silt</b></td>
            <td style="padding: 8px;">0.03 - 0.15</td>
            <td style="padding: 8px;">0.08</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Sandy clay</b></td>
            <td style="padding: 8px;">0.03 - 0.10</td>
            <td style="padding: 8px;">0.06</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Clay</b></td>
            <td style="padding: 8px;">0.01 - 0.10</td>
            <td style="padding: 8px;">0.03</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Limestone (weathered)</b></td>
            <td style="padding: 8px;">0.10 - 0.30</td>
            <td style="padding: 8px;">0.15</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b>Sandstone</b></td>
            <td style="padding: 8px;">0.05 - 0.25</td>
            <td style="padding: 8px;">0.15</td>
        </tr>
        </table>
        
        <h4>Important Notes:</h4>
        <ul>
        <li><b>Specific yield ≠ Porosity:</b> Specific yield is always less than total porosity 
        because some water is retained by capillary forces</li>
        <li><b>Depth matters:</b> Specific yield may decrease with depth due to compaction</li>
        <li><b>Mixed materials:</b> Use weighted average based on layer thickness</li>
        <li><b>Field testing preferred:</b> These are general ranges - actual values vary significantly</li>
        </ul>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>⚠️ Uncertainty:</b> Specific yield is often the largest source of uncertainty in recharge 
        calculations. Consider using a range of values to bracket your estimates.
        </div>
        """)
        typical_content.setReadOnly(True)
        typical_layout.addWidget(typical_content)
        tabs.addTab(typical_tab, "Typical Values")
        
        # Estimation methods tab
        estimation_tab = QWidget()
        estimation_layout = QVBoxLayout(estimation_tab)
        
        estimation_content = QTextEdit()
        estimation_content.setHtml("""
        <h3>Methods for Determining Specific Yield</h3>
        
        <h4>1. Field Methods (Most Reliable)</h4>
        <ul>
        <li><b>Pumping Test Analysis:</b>
            <ul>
            <li>Analyze water level recovery after pumping</li>
            <li>Best for large-scale average Sy</li>
            <li>Requires observation wells</li>
            </ul>
        </li>
        <li><b>Slug Test Analysis:</b>
            <ul>
            <li>Rapid water level change in single well</li>
            <li>Good for local Sy estimate</li>
            <li>Less expensive than pumping test</li>
            </ul>
        </li>
        </ul>
        
        <h4>2. Laboratory Methods</h4>
        <ul>
        <li><b>Gravity Drainage:</b>
            <ul>
            <li>Saturate core sample, measure drainage</li>
            <li>Most direct measurement</li>
            <li>May not represent field conditions</li>
            </ul>
        </li>
        <li><b>Centrifuge Method:</b>
            <ul>
            <li>Faster than gravity drainage</li>
            <li>Good for fine-grained materials</li>
            </ul>
        </li>
        </ul>
        
        <h4>3. Empirical Relationships</h4>
        <ul>
        <li><b>From Grain Size:</b>
            <br>Sy ≈ 0.117 × d₁₀^0.125 (for sands)
            <br>where d₁₀ = grain size (mm) at 10% passing
        </li>
        <li><b>From Porosity (n):</b>
            <br>Coarse materials: Sy ≈ 0.8 × n
            <br>Fine materials: Sy ≈ 0.3 × n
        </li>
        </ul>
        
        <h4>4. Literature Values</h4>
        <p>Use published values for similar:</p>
        <ul>
        <li>Geologic material</li>
        <li>Depth range</li>
        <li>Geographic setting</li>
        <li>Degree of weathering/compaction</li>
        </ul>
        
        <h4>Recommended Approach</h4>
        <ol>
        <li>Start with literature values for initial estimates</li>
        <li>Conduct field tests if possible</li>
        <li>Use multiple methods to bracket uncertainty</li>
        <li>Document your rationale and sources</li>
        </ol>
        """)
        estimation_content.setReadOnly(True)
        estimation_layout.addWidget(estimation_content)
        tabs.addTab(estimation_tab, "Estimation Methods")
        
        # Simple calculator tab
        calc_tab = QWidget()
        calc_layout = QVBoxLayout(calc_tab)
        
        # Material selection
        from PyQt5.QtWidgets import QGroupBox, QDoubleSpinBox
        material_group = QGroupBox("Select Aquifer Material")
        material_layout = QVBoxLayout(material_group)
        
        self.material_combo = QComboBox()
        materials = [
            ("Gravel", 0.15, 0.30, 0.22),
            ("Coarse sand", 0.20, 0.35, 0.27),
            ("Medium sand", 0.15, 0.25, 0.20),
            ("Fine sand", 0.10, 0.20, 0.15),
            ("Very fine sand", 0.05, 0.15, 0.10),
            ("Silt", 0.03, 0.15, 0.08),
            ("Sandy clay", 0.03, 0.10, 0.06),
            ("Clay", 0.01, 0.10, 0.03),
            ("Weathered limestone", 0.10, 0.30, 0.15),
            ("Sandstone", 0.05, 0.25, 0.15),
            ("Custom", 0, 0, 0)
        ]
        for mat, _, _, _ in materials:
            self.material_combo.addItem(mat)
        self.material_combo.currentTextChanged.connect(self.update_sy_estimate)
        material_layout.addWidget(self.material_combo)
        
        # Sy range display
        self.sy_range_label = QLabel()
        self.sy_range_label.setStyleSheet("font-size: 14px; padding: 10px;")
        material_layout.addWidget(self.sy_range_label)
        
        # Custom input
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom Sy:"))
        self.custom_sy = QDoubleSpinBox()
        self.custom_sy.setRange(0.001, 0.5)
        self.custom_sy.setDecimals(3)
        self.custom_sy.setSingleStep(0.01)
        self.custom_sy.setValue(0.15)
        self.custom_sy.setEnabled(False)
        custom_layout.addWidget(self.custom_sy)
        custom_layout.addStretch()
        material_layout.addLayout(custom_layout)
        
        calc_layout.addWidget(material_group)
        
        # Recommendation
        self.recommendation_label = QLabel()
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("""
            QLabel {
                background-color: #d1ecf1;
                border: 1px solid #bee5eb;
                border-radius: 4px;
                padding: 10px;
                margin: 10px 0;
            }
        """)
        calc_layout.addWidget(self.recommendation_label)
        
        calc_layout.addStretch()
        
        # Initialize
        self.materials_data = materials
        self.update_sy_estimate()
        
        tabs.addTab(calc_tab, "Quick Calculator")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
    def update_sy_estimate(self):
        """Update Sy estimate based on material selection."""
        idx = self.material_combo.currentIndex()
        if idx < len(self.materials_data):
            material, min_sy, max_sy, typical = self.materials_data[idx]
            
            if material == "Custom":
                self.custom_sy.setEnabled(True)
                self.sy_range_label.setText("Enter custom specific yield value")
                self.recommendation_label.setText(
                    "Using custom specific yield value. Ensure this is based on "
                    "field testing or reliable literature sources for your specific site."
                )
            else:
                self.custom_sy.setEnabled(False)
                self.sy_range_label.setText(
                    f"Specific Yield Range: {min_sy:.2f} - {max_sy:.2f}\n"
                    f"Typical Value: {typical:.2f}"
                )
                self.recommendation_label.setText(
                    f"For {material.lower()}, we recommend starting with Sy = {typical:.2f}. "
                    f"Consider using the range {min_sy:.2f} - {max_sy:.2f} to evaluate "
                    f"uncertainty in your recharge estimates. Field testing is always "
                    f"preferred for site-specific values."
                )
        
    def create_auto_sync_help(self):
        """Create Auto Sync help."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        auto_sync_help_html = """
        <h2>🔄 Auto Sync - Automated Data Collection</h2>
        
        <h3>Purpose & Overview</h3>
        <p>Auto Sync provides automated data collection capabilities that scan your consolidated 
        Google Drive folder for new XLE files and automatically import them into your database. 
        This feature eliminates manual import processes and ensures your database stays current 
        with field-collected data.</p>
        
        <h3>🎯 Key Features</h3>
        <ul>
        <li><b>Automatic Detection:</b> Scans consolidated folder for new XLE files</li>
        <li><b>Smart Filtering:</b> Only processes files newer than existing data</li>
        <li><b>Dual Mode:</b> Separate sync for barologger and water level data</li>
        <li><b>Change Tracking:</b> Logs all auto-imported data for cloud databases</li>
        <li><b>Progress Monitoring:</b> Visual feedback during sync operations</li>
        </ul>
        
        <h3>📍 Auto Sync Menu Options</h3>
        
        <h4>Auto Sync Barologgers</h4>
        <ul>
        <li><b>Purpose:</b> Automatically import new barometric pressure data</li>
        <li><b>Process:</b>
            <ol>
            <li>Connects to Google Drive using service account</li>
            <li>Scans consolidated folder for XLE files</li>
            <li>Identifies files from registered barologgers</li>
            <li>Imports only data newer than last import</li>
            <li>Updates master barometric pressure dataset</li>
            </ol>
        </li>
        <li><b>When to use:</b> After field teams upload barologger XLE files</li>
        <li><b>Requirements:</b> Active barologgers registered in database</li>
        </ul>
        
        <h4>Auto Sync Water Levels</h4>
        <ul>
        <li><b>Purpose:</b> Automatically import new water level data</li>
        <li><b>Process:</b>
            <ol>
            <li>Connects to consolidated Google Drive folder</li>
            <li>Scans for XLE files from registered transducers</li>
            <li>Matches files to wells using CAE numbers</li>
            <li>Imports data newer than existing readings</li>
            <li>Applies barometric compensation</li>
            <li>Updates water level time series</li>
            </ol>
        </li>
        <li><b>When to use:</b> After field data collection and upload</li>
        <li><b>Requirements:</b> Registered wells and transducers with CAE numbers</li>
        </ul>
        
        <h3>🔧 How Auto Sync Works</h3>
        
        <h4>Authentication & Access</h4>
        <ul>
        <li><b>Service Account:</b> Uses Google service account for secure access</li>
        <li><b>Consolidated Folder:</b> Accesses the shared field data consolidation folder</li>
        <li><b>Folder Structure:</b> Organized by month (e.g., 2025-06, 2025-07)</li>
        <li><b>File Discovery:</b> Scans current and next month folders</li>
        </ul>
        
        <h4>Smart File Processing</h4>
        <ul>
        <li><b>Equipment Matching:</b> Links XLE files to registered equipment</li>
        <li><b>Date Comparison:</b> Only processes files with data newer than database</li>
        <li><b>Duplicate Prevention:</b> Avoids re-importing existing data</li>
        <li><b>Validation:</b> Checks file format and content before import</li>
        </ul>
        
        <h4>Progress & Feedback</h4>
        <ul>
        <li><b>Step-by-step Progress:</b> Shows each stage of sync process</li>
        <li><b>File Counts:</b> Reports number of files found and processed</li>
        <li><b>Success Summary:</b> Confirms successful imports</li>
        <li><b>Error Reporting:</b> Details any problems encountered</li>
        </ul>
        
        <h3>📊 Workflows</h3>
        
        <h4>Setting Up Auto Sync</h4>
        <ol>
        <li><b>Prerequisites:</b>
            <ul>
            <li>Google Drive service account configured</li>
            <li>Consolidated field data folder set up</li>
            <li>Equipment registered in database</li>
            <li>Field teams uploading to correct folders</li>
            </ul>
        </li>
        <li><b>Verification:</b>
            <ul>
            <li>Test Google Drive connectivity</li>
            <li>Confirm folder access permissions</li>
            <li>Verify equipment registrations</li>
            <li>Check folder structure is correct</li>
            </ul>
        </li>
        <li><b>First Sync:</b>
            <ul>
            <li>Start with smaller dataset for testing</li>
            <li>Run barologger sync first</li>
            <li>Then run water level sync</li>
            <li>Verify data appears correctly</li>
            </ul>
        </li>
        </ol>
        
        <h4>Regular Auto Sync Operations</h4>
        <ol>
        <li><b>Check for New Data:</b>
            <ul>
            <li>Monitor field team upload notifications</li>
            <li>Check consolidated folder for new files</li>
            <li>Note approximate upload times</li>
            </ul>
        </li>
        <li><b>Run Sync Process:</b>
            <ul>
            <li>Access Auto Sync menu</li>
            <li>Choose appropriate sync type</li>
            <li>Monitor progress dialog</li>
            <li>Review completion summary</li>
            </ul>
        </li>
        <li><b>Verify Results:</b>
            <ul>
            <li>Check relevant tabs for new data</li>
            <li>Verify import timestamps</li>
            <li>Review data quality indicators</li>
            <li>Note any processing errors</li>
            </ul>
        </li>
        </ol>
        
        <h4>Troubleshooting Sync Issues</h4>
        <ol>
        <li><b>No Files Found:</b>
            <ul>
            <li>Verify files are in consolidated folder</li>
            <li>Check folder month organization</li>
            <li>Confirm equipment is registered</li>
            <li>Verify file naming conventions</li>
            </ul>
        </li>
        <li><b>Authentication Errors:</b>
            <ul>
            <li>Check service account credentials</li>
            <li>Verify folder permissions</li>
            <li>Test Google Drive connectivity</li>
            <li>Refresh authentication if needed</li>
            </ul>
        </li>
        <li><b>Import Failures:</b>
            <ul>
            <li>Check XLE file validity</li>
            <li>Verify equipment registrations</li>
            <li>Review error messages</li>
            <li>Check database connections</li>
            </ul>
        </li>
        </ol>
        
        <h3>💡 Tips & Best Practices</h3>
        
        <h4>Scheduling & Timing</h4>
        <ul>
        <li><b>Regular schedule:</b> Run sync daily or after known field activities</li>
        <li><b>Off-peak timing:</b> Avoid sync during active field uploads</li>
        <li><b>Sequential processing:</b> Run barologger sync before water level sync</li>
        <li><b>Incremental approach:</b> Frequent small syncs better than large batch imports</li>
        </ul>
        
        <h4>Data Quality</h4>
        <ul>
        <li><b>Validation checks:</b> Review imported data for obvious issues</li>
        <li><b>Gap monitoring:</b> Check for expected vs actual data coverage</li>
        <li><b>Equipment health:</b> Monitor for instruments not contributing data</li>
        <li><b>Completeness verification:</b> Ensure all uploaded files were processed</li>
        </ul>
        
        <h4>System Maintenance</h4>
        <ul>
        <li><b>Folder organization:</b> Keep consolidated folder organized by month</li>
        <li><b>Archive management:</b> Periodically archive old month folders</li>
        <li><b>Equipment updates:</b> Keep registrations current with field deployments</li>
        <li><b>Sync monitoring:</b> Track sync performance and success rates</li>
        </ul>
        
        <h3>🔧 Troubleshooting</h3>
        
        <h4>Google Drive Connection Issues</h4>
        <ul>
        <li><b>Service account expired:</b> Check credential validity and refresh</li>
        <li><b>Folder access denied:</b> Verify folder sharing with service account</li>
        <li><b>Network connectivity:</b> Test internet connection and firewall settings</li>
        <li><b>API limits:</b> Check for Google Drive API usage limits</li>
        </ul>
        
        <h4>No Files Detected</h4>
        <ul>
        <li><b>Folder structure:</b> Verify month-based folder organization</li>
        <li><b>File naming:</b> Check XLE files follow expected naming conventions</li>
        <li><b>Equipment registration:</b> Ensure serial numbers match between files and database</li>
        <li><b>Upload completion:</b> Confirm field teams completed file uploads</li>
        </ul>
        
        <h4>Partial Import Success</h4>
        <ul>
        <li><b>File validation:</b> Some XLE files may be corrupted or incomplete</li>
        <li><b>Date conflicts:</b> Files with overlapping time periods may be skipped</li>
        <li><b>Equipment issues:</b> Unregistered instruments won't be processed</li>
        <li><b>Permission problems:</b> Individual files may have access restrictions</li>
        </ul>
        
        <h4>Performance Issues</h4>
        <ul>
        <li><b>Large file sets:</b> Break up massive imports into smaller batches</li>
        <li><b>Network speed:</b> Slow connections may cause timeouts</li>
        <li><b>Database performance:</b> Large datasets may slow import processing</li>
        <li><b>Concurrent operations:</b> Avoid running sync during other database activities</li>
        </ul>
        
        <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>✨ Automation Benefits:</b> Auto Sync transforms data management from manual, 
        error-prone processes into reliable, automated workflows. Regular use ensures your 
        database stays current with minimal effort while maintaining complete audit trails 
        of all data imports.
        </div>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>⚠️ Important:</b> Auto Sync requires proper setup of the consolidated Google Drive 
        folder system and service account authentication. Ensure these foundations are in 
        place before relying on automated sync operations.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(auto_sync_help_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "🔄 Auto Sync")
        
    def create_cloud_features_help(self):
        """Create Cloud Features help."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        cloud_help_html = """
        <h2>☁️ Cloud Features - Collaboration & Data Management</h2>
        
        <h3>Purpose & Overview</h3>
        <p>The cloud features enable team collaboration through Google Drive integration, 
        providing shared access to project databases, automatic change tracking, and coordinated 
        field data collection. These features transform individual database files into 
        collaborative, version-controlled project workspaces.</p>
        
        <h3>🎯 Key Cloud Capabilities</h3>
        <ul>
        <li><b>Cloud Databases:</b> Shared project databases stored in Google Drive</li>
        <li><b>Change Tracking:</b> Detailed logging of manual vs automatic modifications</li>
        <li><b>Version Control:</b> Automatic backup and change history</li>
        <li><b>Team Collaboration:</b> Multiple users working on same project</li>
        <li><b>Field Data Integration:</b> Automatic processing of field-collected data</li>
        <li><b>Audit Trail:</b> Complete record of who changed what and when</li>
        </ul>
        
        <h3>🗄️ Cloud Database System</h3>
        
        <h4>Database Structure</h4>
        <p>Cloud databases are organized in Google Drive with this structure:</p>
        <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
water_levels_monitoring/
├── Projects/
    ├── PROJECT_NAME/
        ├── databases/
        │   ├── PROJECT_NAME.db          (main database)
        │   ├── changes.json             (change log)
        │   ├── backup/                  (automatic backups)
        │   │   ├── PROJECT_NAME_20250622_1030_username.db
        │   │   └── PROJECT_NAME_20250621_1545_username.db
        │   └── changes/                 (detailed change tracking)
        │       ├── changes_20250622_103045.json
        │       └── changes_20250621_154530.json
        └── WATER_LEVEL_RUNS/           (field data)
            ├── 2025-06/
            └── 2025-07/
        </pre>
        
        <h4>Project Access</h4>
        <ul>
        <li><b>Database Dropdown:</b> Shows available cloud projects</li>
        <li><b>Download & Cache:</b> Projects downloaded to local cache for performance</li>
        <li><b>Change Detection:</b> Only downloads when cloud version is newer</li>
        <li><b>Save to Cloud:</b> Button appears when cloud database is loaded</li>
        </ul>
        
        <h3>🔄 Change Tracking System</h3>
        
        <h4>Automatic Change Detection</h4>
        <p>The system automatically tracks two types of changes:</p>
        <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="padding: 8px;">Change Type</th>
            <th style="padding: 8px;">Examples</th>
            <th style="padding: 8px;">Source</th>
        </tr>
        <tr>
            <td style="padding: 8px;"><b style="color: #2E7D32;">Manual</b></td>
            <td style="padding: 8px;">User flag changes, data corrections, well edits</td>
            <td style="padding: 8px;">Direct user interaction</td>
        </tr>
        <tr>
            <td style="padding: 8px;"><b style="color: #1976D2;">Automatic</b></td>
            <td style="padding: 8px;">XLE imports, telemetry updates, Auto Sync</td>
            <td style="padding: 8px;">System processes</td>
        </tr>
        </table>
        
        <h4>Change Details</h4>
        <p>Each tracked change includes:</p>
        <ul>
        <li><b>Timestamp:</b> Exact time of modification</li>
        <li><b>User:</b> Who made the change</li>
        <li><b>Type:</b> Manual vs automatic classification</li>
        <li><b>Action:</b> Insert, update, or delete</li>
        <li><b>Location:</b> Table and field affected</li>
        <li><b>Values:</b> Before and after values</li>
        <li><b>Context:</b> Additional information (file names, methods, etc.)</li>
        </ul>
        
        <h3>💾 Save to Cloud Process</h3>
        
        <h4>When Save to Cloud Button Appears</h4>
        <ul>
        <li><b>Cloud database loaded:</b> Working with a project from Google Drive</li>
        <li><b>Changes detected:</b> Manual or automatic modifications made</li>
        <li><b>Button state:</b> Green button becomes enabled</li>
        <li><b>Status indicator:</b> Cloud project name shows "(MODIFIED)"</li>
        </ul>
        
        <h4>Save Dialog Features</h4>
        <p>When you click "Save to Cloud", the dialog shows:</p>
        <ul>
        <li><b>Change Summary:</b> Count of manual vs automatic changes</li>
        <li><b>Detected Changes:</b> Auto-generated description of modifications</li>
        <li><b>Pre-filled Description:</b> Suggested text based on tracked changes</li>
        <li><b>Manual Description:</b> Space for additional context or notes</li>
        <li><b>User Information:</b> Current user making the save</li>
        </ul>
        
        <h4>Save Process Steps</h4>
        <ol>
        <li><b>Backup Creation:</b> Current database backed up with timestamp</li>
        <li><b>Database Upload:</b> New version uploaded to replace current</li>
        <li><b>Change Log Update:</b> User description added to changes.json</li>
        <li><b>Detailed Tracking:</b> Full change details saved to changes folder</li>
        <li><b>Cleanup:</b> Old backups removed (keeps 2 most recent)</li>
        <li><b>Lock Release:</b> Database becomes available for other users</li>
        </ol>
        
        <h3>👥 Team Collaboration</h3>
        
        <h4>Multi-User Access</h4>
        <ul>
        <li><b>Shared Projects:</b> Multiple team members can access same database</li>
        <li><b>User Identification:</b> All changes tagged with user name</li>
        <li><b>Lock System:</b> Prevents simultaneous editing conflicts</li>
        <li><b>Change Visibility:</b> All modifications tracked and visible</li>
        </ul>
        
        <h4>Collaboration Workflow</h4>
        <ol>
        <li><b>User A:</b> Downloads cloud database, makes changes</li>
        <li><b>Save Process:</b> User A saves changes with description</li>
        <li><b>User B:</b> Downloads updated database automatically</li>
        <li><b>Change Review:</b> User B can see what User A modified</li>
        <li><b>Continued Work:</b> User B makes additional changes</li>
        <li><b>Full History:</b> Complete audit trail maintained</li>
        </ol>
        
        <h4>Conflict Resolution</h4>
        <ul>
        <li><b>Lock Detection:</b> System prevents simultaneous editing</li>
        <li><b>Version Checking:</b> Alerts if cloud version is newer</li>
        <li><b>Backup System:</b> Previous versions always preserved</li>
        <li><b>Change Tracking:</b> Detailed record helps resolve conflicts</li>
        </ul>
        
        <h3>📊 Workflows</h3>
        
        <h4>Starting with Cloud Database</h4>
        <ol>
        <li>Select cloud project from database dropdown</li>
        <li>System downloads and caches database locally</li>
        <li>"Save to Cloud" button appears (initially disabled)</li>
        <li>Cloud project name shown in status area</li>
        <li>Change tracking begins automatically</li>
        <li>Work with database normally in all tabs</li>
        </ol>
        
        <h4>Making and Saving Changes</h4>
        <ol>
        <li>Perform normal operations (import data, edit flags, etc.)</li>
        <li>System tracks all changes automatically</li>
        <li>"Save to Cloud" button becomes enabled (green)</li>
        <li>Status shows project as "(MODIFIED)"</li>
        <li>Click "Save to Cloud" when ready to share changes</li>
        <li>Review and edit change description in dialog</li>
        <li>Confirm save to upload changes</li>
        <li>Button becomes disabled until next change</li>
        </ol>
        
        <h4>Reviewing Change History</h4>
        <ol>
        <li>Access project folder in Google Drive</li>
        <li>Open changes folder for detailed change logs</li>
        <li>Review changes.json for summary information</li>
        <li>Check backup folder for previous versions</li>
        <li>Use timestamps to track modification sequence</li>
        <li>Review user attributions for team coordination</li>
        </ol>
        
        <h3>💡 Tips & Best Practices</h3>
        
        <h4>Change Management</h4>
        <ul>
        <li><b>Frequent saves:</b> Save changes regularly to avoid loss</li>
        <li><b>Descriptive notes:</b> Provide clear change descriptions</li>
        <li><b>Logical grouping:</b> Save related changes together</li>
        <li><b>Coordination:</b> Communicate with team about major changes</li>
        </ul>
        
        <h4>Quality Control</h4>
        <ul>
        <li><b>Review before save:</b> Check changes make sense</li>
        <li><b>Change validation:</b> Verify automatic vs manual classification</li>
        <li><b>Backup awareness:</b> Know that previous versions are preserved</li>
        <li><b>Audit trail use:</b> Use change logs for quality assurance</li>
        </ul>
        
        <h4>Team Coordination</h4>
        <ul>
        <li><b>Communication:</b> Notify team of significant changes</li>
        <li><b>Work scheduling:</b> Coordinate intensive data entry periods</li>
        <li><b>Role clarity:</b> Define who makes what types of changes</li>
        <li><b>Regular reviews:</b> Periodically review change logs together</li>
        </ul>
        
        <h3>🔧 Troubleshooting</h3>
        
        <h4>Save to Cloud Button Not Appearing</h4>
        <ul>
        <li><b>Local database:</b> Feature only works with cloud databases</li>
        <li><b>Download issues:</b> Ensure cloud database downloaded successfully</li>
        <li><b>Authentication:</b> Verify Google Drive access is working</li>
        <li><b>Project configuration:</b> Check project folder structure</li>
        </ul>
        
        <h4>Button Not Enabling</h4>
        <ul>
        <li><b>No changes made:</b> Button only enables after modifications</li>
        <li><b>Change detection:</b> Some operations may not trigger change tracking</li>
        <li><b>System issue:</b> Restart application if tracking seems broken</li>
        <li><b>Database connection:</b> Verify cloud database is properly loaded</li>
        </ul>
        
        <h4>Save Failures</h4>
        <ul>
        <li><b>Network connectivity:</b> Check internet connection</li>
        <li><b>Google Drive access:</b> Verify service account permissions</li>
        <li><b>File locks:</b> Another user may have database locked</li>
        <li><b>Storage space:</b> Check Google Drive storage availability</li>
        </ul>
        
        <h4>Change Tracking Issues</h4>
        <ul>
        <li><b>Missing changes:</b> Some operations may not be tracked yet</li>
        <li><b>Wrong classification:</b> Contact support if manual/automatic is incorrect</li>
        <li><b>Incomplete details:</b> Some change context may be limited</li>
        <li><b>Performance impact:</b> Tracking adds minimal overhead</li>
        </ul>
        
        <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>🌟 Collaboration Power:</b> Cloud features transform individual database work into 
        team collaboration with full accountability, version control, and change transparency. 
        This enables distributed teams to work together effectively while maintaining data integrity.
        </div>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin: 10px 0;">
        <b>💾 Data Safety:</b> All cloud saves create automatic backups and maintain complete 
        change history. Your data is protected against accidental loss while providing full 
        transparency into all modifications.
        </div>
        """
        
        content = QTextEdit()
        content.setHtml(cloud_help_html)
        content.setReadOnly(True)
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "☁️ Cloud Features")
        
    def set_initial_tab(self, tab_name):
        """Set the initial tab to display."""
        tab_mapping = {
            "overview": 0,
            "database": 1,
            "barologger": 2,
            "water_level": 3,
            "runs": 4,
            "recharge": 5,
            "auto_sync": 6,
            "cloud": 7
        }
        
        if tab_name.lower() in tab_mapping:
            self.help_tabs.setCurrentIndex(tab_mapping[tab_name.lower()])