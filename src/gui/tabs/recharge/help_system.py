"""
Enhanced Help System for Recharge Analysis Tab.
Provides comprehensive guidance on methods, parameters, and scientific background.
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QTabWidget, QWidget, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QDesktopServices, QCursor
import webbrowser

logger = logging.getLogger(__name__)


class RechargeHelpSystem(QDialog):
    """
    Comprehensive help system for recharge analysis methods.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        
        self.setWindowTitle("Recharge Analysis Help & Documentation")
        self.setModal(False)
        self.resize(1000, 700)
        
        self.setup_ui()
        
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
        
        title = QLabel("Recharge Analysis Help & Documentation")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Scientific methods for groundwater recharge estimation using water level data")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_frame)
        
    def create_help_content(self, layout):
        """Create help content tabs."""
        self.help_tabs = QTabWidget()
        
        # Quick Start tab
        self.create_quick_start_tab()
        
        # Method Overview tab
        self.create_method_overview_tab()
        
        # Parameter Guide tab
        self.create_parameter_guide_tab()
        
        # Scientific References tab
        self.create_references_tab()
        
        layout.addWidget(self.help_tabs)
        
    def create_quick_start_tab(self):
        """Create quick start guide tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Quick start content
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
        
        self.help_tabs.addTab(tab, "Quick Start")
        
    def create_method_overview_tab(self):
        """Create method overview tab."""
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
        
        self.help_tabs.addTab(tab, "Method Overview")
        
    def create_parameter_guide_tab(self):
        """Create parameter guide tab."""
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
        
        self.help_tabs.addTab(tab, "Parameter Guide")
        
    def create_references_tab(self):
        """Create scientific references tab."""
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
        
        # Make links clickable - QTextEdit doesn't have setOpenExternalLinks
        # Links are handled by anchorClicked signal instead
        
        scroll_layout.addWidget(content)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.help_tabs.addTab(tab, "Scientific References")
    
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