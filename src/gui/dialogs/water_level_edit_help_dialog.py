"""
Water Level Edit Dialog Help System

Provides comprehensive guidance for using the water level edit dialog,
including step-by-step instructions for all editing tools and data processing logic.

Created as a pilot implementation for individual dialog help systems.
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QTabWidget, QWidget, QMessageBox, QScrollArea, QSplitter,
    QTreeWidget, QTreeWidgetItem, QStackedWidget
)
from PyQt5.QtCore import pyqtSignal, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QBrush
from ..utils.button_styles import ButtonStyles

logger = logging.getLogger(__name__)


class WaterLevelEditHelpDialog(QDialog):
    """
    Comprehensive help dialog specifically for the Water Level Edit Dialog.
    
    Provides detailed guidance on:
    - Dialog purpose and overview
    - Each button function and workflow
    - Data processing logic and algorithms
    - Step-by-step user instructions
    - Best practices and troubleshooting
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        
        self.setWindowTitle("Water Level Edit Dialog - Help & User Guide")
        self.setModal(False)
        self.resize(1600, 900)  # Even wider to better use screen space
        self.setMinimumSize(1200, 700)  # Larger minimum size for better readability
        
        # Apply blue background styling consistent with the application
        self.setStyleSheet("""
            QDialog {
                background-color: #f6fafd;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the help dialog UI with navigation and content."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Consistent margins
        layout.setSpacing(10)  # Consistent spacing
        
        # Header (fixed size)
        self.create_header(layout)
        
        # Main content with navigation (expandable)
        self.create_main_content(layout)
        
        # Footer with close button (fixed size)
        self.create_footer(layout)
        
    def create_header(self, layout):
        """Create compact header section with title and overview."""
        header_frame = QFrame()
        header_frame.setFixedHeight(80)  # Even more compact height
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border: 2px solid #1976d2;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)  # Further reduced margins
        header_layout.setSpacing(3)  # Minimal spacing
        
        # Main title - smaller font
        title = QLabel("Water Level Edit Dialog - Complete User Guide")
        title_font = QFont()
        title_font.setPointSize(14)  # Further reduced from 16
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1976d2; margin: 0px; padding: 0px;")
        
        # Subtitle - smaller
        subtitle = QLabel("Master the tools for manual water level data correction and quality improvement")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #424242; font-size: 11px; font-style: italic; margin: 0px; padding: 0px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_frame)
        
    def create_main_content(self, layout):
        """Create main content area with navigation tree and content panels."""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(0, 0)  # Navigation tree doesn't stretch
        splitter.setStretchFactor(1, 1)  # Content area stretches
        
        # Navigation tree
        self.nav_tree = self.create_navigation_tree()
        splitter.addWidget(self.nav_tree)
        
        # Content area wrapper with proper sizing
        content_wrapper = QWidget()
        content_wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.create_content_pages()
        content_wrapper_layout.addWidget(self.content_stack)
        
        splitter.addWidget(content_wrapper)
        
        # Set proportional sizes (15% navigation, 85% content) 
        # This gives more space to content and scales with window size
        splitter.setSizes([200, 1400])  # Initial sizes that maintain proportion
        splitter.setCollapsible(0, False)  # Prevent navigation from being collapsed
        splitter.setCollapsible(1, False)  # Prevent content from being collapsed
        
        layout.addWidget(splitter)
        
    def create_navigation_tree(self):
        """Create navigation tree widget."""
        tree = QTreeWidget()
        tree.setHeaderLabel("Help Topics")
        tree.setMinimumWidth(180)  # Smaller minimum width
        tree.setMaximumWidth(280)  # More flexible maximum width
        tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Style the tree
        tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eeeeee;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        # Create navigation items
        self.nav_items = {}
        
        # 1. Overview & Purpose
        overview_item = QTreeWidgetItem(["1. Overview & Purpose"])
        overview_item.setData(0, Qt.UserRole, "overview")
        tree.addTopLevelItem(overview_item)
        self.nav_items["overview"] = 0
        
        # 2. Getting Started
        getting_started = QTreeWidgetItem(["2. Getting Started"])
        getting_started.setData(0, Qt.UserRole, "getting_started")
        tree.addTopLevelItem(getting_started)
        self.nav_items["getting_started"] = 1
        
        # 3. Data Filters & Display
        filters_item = QTreeWidgetItem(["3. Data Filters & Display"])
        filters_item.setData(0, Qt.UserRole, "filters")
        tree.addTopLevelItem(filters_item)
        self.nav_items["filters"] = 2
        
        # 4. Edit Tools
        tools_item = QTreeWidgetItem(["4. Edit Tools"])
        
        # Sub-items for edit tools
        spike_item = QTreeWidgetItem(["4.1 Fix Spikes"])
        spike_item.setData(0, Qt.UserRole, "spike_fixing")
        tools_item.addChild(spike_item)
        self.nav_items["spike_fixing"] = 3
        
        comp_item = QTreeWidgetItem(["4.2 Compensation"])
        comp_item.setData(0, Qt.UserRole, "compensation")
        tools_item.addChild(comp_item)
        self.nav_items["compensation"] = 4
        
        baseline_item = QTreeWidgetItem(["4.3 Baseline Adjustment"])
        baseline_item.setData(0, Qt.UserRole, "baseline")
        tools_item.addChild(baseline_item)
        self.nav_items["baseline"] = 5
        
        tree.addTopLevelItem(tools_item)
        tools_item.setExpanded(True)  # Expand by default
        
        # 5. Data Processing Logic
        logic_item = QTreeWidgetItem(["5. Data Processing Logic"])
        logic_item.setData(0, Qt.UserRole, "processing_logic")
        tree.addTopLevelItem(logic_item)
        self.nav_items["processing_logic"] = 6
        
        # 6. Best Practices & Tips
        tips_item = QTreeWidgetItem(["6. Best Practices & Tips"])
        tips_item.setData(0, Qt.UserRole, "best_practices")
        tree.addTopLevelItem(tips_item)
        self.nav_items["best_practices"] = 7
        
        # 7. Troubleshooting
        trouble_item = QTreeWidgetItem(["7. Troubleshooting"])
        trouble_item.setData(0, Qt.UserRole, "troubleshooting")
        tree.addTopLevelItem(trouble_item)
        self.nav_items["troubleshooting"] = 8
        
        # Connect selection change
        tree.itemSelectionChanged.connect(self.on_navigation_changed)
        
        return tree
        
    def create_content_pages(self):
        """Create all content pages for the help system."""
        
        # Page 0: Overview & Purpose
        self.content_stack.addWidget(self.create_overview_page())
        
        # Page 1: Getting Started
        self.content_stack.addWidget(self.create_getting_started_page())
        
        # Page 2: Data Filters & Display
        self.content_stack.addWidget(self.create_filters_page())
        
        # Page 3: Spike Fixing
        self.content_stack.addWidget(self.create_spike_fixing_page())
        
        # Page 4: Compensation
        self.content_stack.addWidget(self.create_compensation_page())
        
        # Page 5: Baseline Adjustment
        self.content_stack.addWidget(self.create_baseline_page())
        
        # Page 6: Data Processing Logic
        self.content_stack.addWidget(self.create_processing_logic_page())
        
        # Page 7: Best Practices
        self.content_stack.addWidget(self.create_best_practices_page())
        
        # Page 8: Troubleshooting
        self.content_stack.addWidget(self.create_troubleshooting_page())
        
    def create_overview_page(self):
        """Create the overview and purpose page."""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Page title
        title = QLabel("Water Level Edit Dialog - Overview & Purpose")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Main purpose section
        purpose_group = QGroupBox("Main Purpose")
        purpose_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_layout = QVBoxLayout(purpose_group)
        
        purpose_text = QTextEdit()
        purpose_text.setReadOnly(True)
        purpose_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_text.setMaximumHeight(150)
        purpose_text.setHtml("""
        <p>The <strong>Water Level Edit Dialog</strong> is designed to help users manually correct and improve water level data that may contain errors, artifacts, or quality issues that automated processing couldn't handle.</p>
        
        <p><strong>Key Functions:</strong></p>
        <ul>
        <li>Correct erroneous data points caused by sensor malfunctions or environmental interference</li>
        <li>Fix spikes and anomalies in the data using sophisticated interpolation methods</li>
        <li>Apply barometric compensation when automated processing failed</li>
        <li>Adjust baseline levels to match field measurements and calibration data</li>
        <li>Visualize data gaps and quality issues to make informed corrections</li>
        </ul>
        """)
        purpose_layout.addWidget(purpose_text)
        layout.addWidget(purpose_group)
        
        # When to use section
        when_group = QGroupBox("When to Use This Dialog")
        when_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        when_layout = QVBoxLayout(when_group)
        
        when_text = QTextEdit()
        when_text.setReadOnly(True)
        when_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        when_text.setMaximumHeight(130)
        when_text.setHtml("""
        <p>Use this dialog when you encounter:</p>
        <ul>
        <li><strong>Data spikes:</strong> Sudden, unrealistic jumps in water level readings</li>
        <li><strong>Calibration issues:</strong> Levels that don't match manual field measurements</li>
        <li><strong>Barometric compensation errors:</strong> Incorrect atmospheric pressure corrections</li>
        <li><strong>Sensor drift:</strong> Gradual shifts in readings over time</li>
        <li><strong>Quality control flags:</strong> Data points marked for manual review</li>
        </ul>
        """)
        when_layout.addWidget(when_text)
        layout.addWidget(when_group)
        
        # Dialog components overview
        components_group = QGroupBox("Dialog Components Overview")
        components_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        components_layout = QVBoxLayout(components_group)
        
        components_text = QTextEdit()
        components_text.setReadOnly(True)
        components_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        components_text.setMaximumHeight(180)
        components_text.setHtml("""
        <p><strong>Data Filters:</strong> Control which data elements are visible (Master Baro, Flags, Data Gaps)</p>
        <p><strong>Interactive Plot:</strong> Visualize data with zoom, pan, and selection capabilities</p>
        <p><strong>Edit Tools:</strong> Three specialized tools for different types of corrections:</p>
        <ul>
        <li><strong>Fix Spikes:</strong> Remove anomalous data points using linear interpolation</li>
        <li><strong>Compensation:</strong> Apply barometric compensation to selected data ranges</li>
        <li><strong>Baseline Adjustment:</strong> Adjust level baselines using field measurements</li>
        </ul>
        <p><strong>Date Controls:</strong> Select specific time ranges for targeted editing</p>
        <p><strong>Action Buttons:</strong> Apply changes, save modifications, or cancel operations</p>
        """)
        components_layout.addWidget(components_text)
        layout.addWidget(components_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_getting_started_page(self):
        """Create the getting started guide page."""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Getting Started - Quick Setup Guide")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Basic workflow
        workflow_group = QGroupBox("Basic Workflow")
        workflow_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        workflow_layout = QVBoxLayout(workflow_group)
        
        workflow_text = QTextEdit()
        workflow_text.setReadOnly(True)
        workflow_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        workflow_text.setMaximumHeight(220)
        workflow_text.setHtml("""
        <p><strong>Step-by-Step Process:</strong></p>
        <ol>
        <li><strong>Data Review:</strong> Examine the plot for obvious issues (spikes, gaps, drift)</li>
        <li><strong>Filter Setup:</strong> Enable relevant data filters (gaps, flags) to identify problem areas</li>
        <li><strong>Tool Selection:</strong> Choose the appropriate edit tool based on the type of issue</li>
        <li><strong>Data Selection:</strong> Select the specific data points or time range to modify</li>
        <li><strong>Parameter Configuration:</strong> Set tool parameters in the helper dialog</li>
        <li><strong>Preview & Apply:</strong> Review changes and apply when satisfied</li>
        <li><strong>Verification:</strong> Check the results and make additional corrections if needed</li>
        <li><strong>Save Changes:</strong> Apply final changes to the database</li>
        </ol>
        """)
        workflow_layout.addWidget(workflow_text)
        layout.addWidget(workflow_group)
        
        # Navigation tips
        nav_group = QGroupBox("Navigation & Plot Interaction")
        nav_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        nav_layout = QVBoxLayout(nav_group)
        
        nav_text = QTextEdit()
        nav_text.setReadOnly(True)
        nav_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        nav_text.setMaximumHeight(150)
        nav_text.setHtml("""
        <p><strong>Plot Controls:</strong></p>
        <ul>
        <li><strong>Zoom:</strong> Use mouse wheel or toolbar zoom tools</li>
        <li><strong>Pan:</strong> Click and drag to move around the plot</li>
        <li><strong>Select Data:</strong> Click and drag to select time ranges for editing</li>
        <li><strong>Reset View:</strong> Use Home button to return to full data view</li>
        <li><strong>Date Selectors:</strong> Use date/time controls for precise range selection</li>
        </ul>
        """)
        nav_layout.addWidget(nav_text)
        layout.addWidget(nav_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_filters_page(self):
        """Create the data filters and display options page."""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Data Filters & Display Options")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Checkbox controls
        checkbox_group = QGroupBox("Filter Checkboxes")
        checkbox_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        checkbox_layout = QVBoxLayout(checkbox_group)
        
        checkbox_text = QTextEdit()
        checkbox_text.setReadOnly(True)
        checkbox_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        checkbox_text.setMaximumHeight(280)
        checkbox_text.setHtml("""
        <p><strong>Master Baro:</strong> Shows/hides master barometric pressure data overlay</p>
        <ul>
        <li>Useful for understanding atmospheric pressure effects on water levels</li>
        <li>Helps identify periods where barometric compensation may be needed</li>
        <li>Displayed as secondary y-axis with different color</li>
        </ul>
        
        <p><strong>Baro Flags:</strong> Shows/hides barometric quality flags</p>
        <ul>
        <li>Color-coded indicators showing barometric data quality</li>
        <li>Helps identify periods with poor barometric compensation</li>
        </ul>
        
        <p><strong>Level Flags:</strong> Shows/hides water level quality flags</p>
        <ul>
        <li>Indicates data quality and processing status</li>
        <li>Essential for identifying data that needs manual review</li>
        </ul>
        
        <p><strong>Show Data Gaps:</strong> Highlights missing data periods</p>
        <ul>
        <li>Red background areas indicate gaps > 20 minutes</li>
        <li>Critical for understanding data continuity issues</li>
        <li>Helps plan interpolation or infill strategies</li>
        </ul>
        """)
        checkbox_layout.addWidget(checkbox_text)
        layout.addWidget(checkbox_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_spike_fixing_page(self):
        """Create the spike fixing tool page."""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Fix Spikes Tool - Linear Interpolation")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Purpose and when to use
        purpose_group = QGroupBox("Purpose & When to Use")
        purpose_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_layout = QVBoxLayout(purpose_group)
        
        purpose_text = QTextEdit()
        purpose_text.setReadOnly(True)
        purpose_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_text.setMaximumHeight(120)
        purpose_text.setHtml("""
        <p>The <strong>Fix Spikes</strong> tool removes anomalous data points by replacing them with linearly interpolated values between user-selected start and end points.</p>
        
        <p><strong>Use for:</strong> Sudden spikes, sensor malfunctions, electrical interference, physically impossible readings</p>
        <p><strong>Avoid for:</strong> Gradual trends, seasonal variations, or legitimate rapid changes</p>
        """)
        purpose_layout.addWidget(purpose_text)
        layout.addWidget(purpose_group)
        
        # Step-by-step instructions
        steps_group = QGroupBox("Step-by-Step Instructions")
        steps_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        steps_layout = QVBoxLayout(steps_group)
        
        steps_text = QTextEdit()
        steps_text.setReadOnly(True)
        steps_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        steps_text.setMaximumHeight(280)
        steps_text.setHtml("""
        <ol>
        <li><strong>Click 'Fix Spikes'</strong> to open the Spike Fix Helper dialog</li>
        <li><strong>Read the instructions</strong> carefully in the dialog</li>
        <li><strong>Click 'Start Selection'</strong> to begin point selection mode</li>
        <li><strong>Select Start Point:</strong> Click on the plot just before the spike begins</li>
        <li><strong>Select End Point:</strong> Click on the plot just after the spike ends</li>
        <li><strong>Review the pair:</strong> The selected points will be listed in the dialog</li>
        <li><strong>Add more pairs:</strong> Repeat steps 4-5 for additional spikes</li>
        <li><strong>Remove mistakes:</strong> Use 'Remove Last Pair' if needed</li>
        <li><strong>Preview results:</strong> Green lines show the interpolated replacement</li>
        <li><strong>Apply changes:</strong> Click 'Apply' when satisfied with the selection</li>
        </ol>
        
        <p><strong>Tips:</strong></p>
        <ul>
        <li>Select points as close to "normal" data as possible</li>
        <li>Zoom in for precise point selection</li>
        <li>ESC cancels selection mode</li>
        </ul>
        """)
        steps_layout.addWidget(steps_text)
        layout.addWidget(steps_group)
        
        # Technical details
        tech_group = QGroupBox("Technical Processing Details")
        tech_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tech_layout = QVBoxLayout(tech_group)
        
        tech_text = QTextEdit()
        tech_text.setReadOnly(True)
        tech_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tech_text.setMaximumHeight(150)
        tech_text.setHtml("""
        <p><strong>Algorithm:</strong> Linear interpolation between selected points</p>
        <p><strong>Sampling Interval:</strong> 15-minute intervals (configurable)</p>
        <p><strong>Data Column:</strong> Updates 'water_level_spike_corrected' column</p>
        <p><strong>Flag Updates:</strong> Sets 'spike_flag' to 'spike_corrected'</p>
        <p><strong>Preservation:</strong> Original data remains unchanged in base columns</p>
        """)
        tech_layout.addWidget(tech_text)
        layout.addWidget(tech_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_compensation_page(self):
        """Create the compensation tool page."""
        page = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        title = QLabel("Compensation Tool - Barometric Correction")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Purpose and theory
        purpose_group = QGroupBox("Purpose & Theory")
        purpose_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_layout = QVBoxLayout(purpose_group)
        
        purpose_text = QTextEdit()
        purpose_text.setReadOnly(True)
        purpose_text.setMaximumHeight(130)
        purpose_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_text.setHtml("""
        <p><strong>Barometric compensation</strong> removes the effects of atmospheric pressure changes on water level measurements.</p>
        
        <p><strong>Why it's needed:</strong></p>
        <ul>
        <li>Atmospheric pressure affects water levels in wells</li>
        <li>Pressure changes can mask or exaggerate real water level changes</li>
        <li>Compensation reveals true aquifer responses to pumping, recharge, etc.</li>
        </ul>
        
        <p><strong>Use when:</strong> Automatic compensation failed or was incomplete</p>
        """)
        purpose_layout.addWidget(purpose_text)
        layout.addWidget(purpose_group)
        
        # Instructions
        instructions_group = QGroupBox("How to Use")
        instructions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setMaximumHeight(180)
        instructions_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        instructions_text.setHtml("""
        <ol>
        <li><strong>Enable Master Baro display</strong> to see atmospheric pressure data</li>
        <li><strong>Identify uncompensated periods:</strong> Look for inverse correlation between baro and water level</li>
        <li><strong>Select the time range</strong> that needs compensation using date controls or plot selection</li>
        <li><strong>Click 'Compensation'</strong> to open the helper dialog</li>
        <li><strong>Choose compensation mode:</strong>
            <ul>
            <li><strong>Apply to Missing Ranges:</strong> Compensate gaps in automatic processing</li>
            <li><strong>Apply to Selection:</strong> Compensate your selected time range (future feature)</li>
            </ul>
        </li>
        <li><strong>Apply compensation:</strong> Click 'Apply' to process the selected data</li>
        </ol>
        
        <p><strong>Visual Indicators:</strong> Compensated data will show reduced correlation with barometric pressure</p>
        """)
        instructions_layout.addWidget(instructions_text)
        layout.addWidget(instructions_group)
        
        # Technical details
        tech_group = QGroupBox("Technical Details")
        tech_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tech_layout = QVBoxLayout(tech_group)
        
        tech_text = QTextEdit()
        tech_text.setReadOnly(True)
        tech_text.setMaximumHeight(90)
        tech_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tech_text.setHtml("""
        <p><strong>Algorithm:</strong> Applies barometric efficiency factor to remove pressure effects</p>
        <p><strong>Data Source:</strong> Uses master barologger data for compensation</p>
        <p><strong>Flag Updates:</strong> Sets flags to indicate compensated data</p>
        <p><strong>Quality Control:</strong> Validates compensation effectiveness</p>
        """)
        tech_layout.addWidget(tech_text)
        layout.addWidget(tech_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_baseline_page(self):
        """Create the baseline adjustment tool page."""
        page = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        title = QLabel("Baseline Adjustment Tool - Level Calibration")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Purpose
        purpose_group = QGroupBox("Purpose & Applications")
        purpose_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_layout = QVBoxLayout(purpose_group)
        
        purpose_text = QTextEdit()
        purpose_text.setReadOnly(True)
        purpose_text.setMaximumHeight(110)
        purpose_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        purpose_text.setHtml("""
        <p><strong>Baseline adjustment</strong> corrects systematic offsets in water level data to match field measurements and known reference elevations.</p>
        
        <p><strong>Common uses:</strong></p>
        <ul>
        <li>Calibrate transducer data to manual measurements</li>
        <li>Correct for sensor installation depth errors</li>
        <li>Adjust for reference datum changes</li>
        <li>Fix systematic offsets discovered during QC</li>
        </ul>
        """)
        purpose_layout.addWidget(purpose_text)
        layout.addWidget(purpose_group)
        
        # Methods
        methods_group = QGroupBox("Adjustment Methods")
        methods_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        methods_layout = QVBoxLayout(methods_group)
        
        methods_text = QTextEdit()
        methods_text.setReadOnly(True)
        methods_text.setMaximumHeight(130)
        methods_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        methods_text.setHtml("""
        <p><strong>Manual Measurements Mode:</strong></p>
        <ul>
        <li>Uses existing manual reading data for calibration</li>
        <li>Automatically calculates optimal adjustment</li>
        <li>Best for routine calibration workflows</li>
        </ul>
        
        <p><strong>Free Leveling Mode:</strong></p>
        <ul>
        <li>Manual entry of adjustment value</li>
        <li>Supports difference calculation between two elevation points</li>
        <li>Includes sign toggle button (±) for easy sign correction</li>
        <li>Best for custom adjustments and datum corrections</li>
        </ul>
        """)
        methods_layout.addWidget(methods_text)
        layout.addWidget(methods_group)
        
        # Step-by-step for Free Leveling
        steps_group = QGroupBox("Free Leveling - Step by Step")
        steps_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        steps_layout = QVBoxLayout(steps_group)
        
        steps_text = QTextEdit()
        steps_text.setReadOnly(True)
        steps_text.setMaximumHeight(180)
        steps_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        steps_text.setHtml("""
        <ol>
        <li><strong>Select time range</strong> for the adjustment (entire dataset or specific period)</li>
        <li><strong>Click 'Baseline Adjustment'</strong> to open the helper dialog</li>
        <li><strong>Choose 'Free Leveling'</strong> mode (default)</li>
        <li><strong>Enter adjustment value</strong> directly, OR:</li>
        <li><strong>Use difference calculation:</strong>
            <ul>
            <li>Check "Calculate adjustment from two elevation points"</li>
            <li>Enter Point 1 elevation (current/incorrect value)</li>
            <li>Enter Point 2 elevation (target/correct value)</li>
            <li>Click "Calculate Difference" to compute adjustment</li>
            </ul>
        </li>
        <li><strong>Toggle sign if needed:</strong> Use the ± button next to the adjustment value</li>
        <li><strong>Apply the adjustment:</strong> Click 'Apply' to modify the data</li>
        </ol>
        
        <p><strong>Note:</strong> The adjustment value box is now located at the bottom of the dialog for better workflow.</p>
        """)
        steps_layout.addWidget(steps_text)
        layout.addWidget(steps_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_processing_logic_page(self):
        """Create the data processing logic explanation page."""
        page = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        title = QLabel("Data Processing Logic & Priority System")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Column priority system
        priority_group = QGroupBox("Data Column Priority System")
        priority_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        priority_layout = QVBoxLayout(priority_group)
        
        priority_text = QTextEdit()
        priority_text.setReadOnly(True)
        priority_text.setMaximumHeight(160)
        priority_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        priority_text.setHtml("""
        <p>The system maintains multiple data columns and uses a priority system to determine which values to display and save:</p>
        
        <p><strong>Priority Order (Highest to Lowest):</strong></p>
        <ol>
        <li><strong>water_level_master_corrected:</strong> Used when baro_flag_mod = 'master_mod'</li>
        <li><strong>water_level_level_corrected:</strong> Used when level_flag_mod = 'level_mod'</li>
        <li><strong>water_level_spike_corrected:</strong> Used when spike_flag = 'spike_corrected'</li>
        <li><strong>water_level:</strong> Original, unmodified data (fallback)</li>
        </ol>
        
        <p><strong>Why this matters:</strong> The plot automatically shows the most processed version of your data, ensuring you always see the results of your latest corrections.</p>
        """)
        priority_layout.addWidget(priority_text)
        layout.addWidget(priority_group)
        
        # Flag system
        flags_group = QGroupBox("Quality Flag System")
        flags_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        flags_layout = QVBoxLayout(flags_group)
        
        flags_text = QTextEdit()
        flags_text.setReadOnly(True)
        flags_text.setMaximumHeight(130)
        flags_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        flags_text.setHtml("""
        <p><strong>Barometric Flags:</strong></p>
        <ul>
        <li><strong>master:</strong> Compensated using master barologger</li>
        <li><strong>standard:</strong> Normal atmospheric pressure conditions</li>
        <li><strong>master_corrected:</strong> Manually corrected compensation</li>
        </ul>
        
        <p><strong>Level Flags:</strong></p>
        <ul>
        <li><strong>level_corrected:</strong> Manually adjusted baseline</li>
        <li><strong>spike_corrected:</strong> Spike removal applied</li>
        <li><strong>manual_reading:</strong> Field measurement data</li>
        <li><strong>predicted:</strong> Interpolated or estimated values</li>
        </ul>
        """)
        flags_layout.addWidget(flags_text)
        layout.addWidget(flags_group)
        
        # Change tracking
        tracking_group = QGroupBox("Change Tracking & Audit Trail")
        tracking_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tracking_layout = QVBoxLayout(tracking_group)
        
        tracking_text = QTextEdit()
        tracking_text.setReadOnly(True)
        tracking_text.setMaximumHeight(110)
        tracking_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tracking_text.setHtml("""
        <p>All modifications are tracked for audit and quality control:</p>
        <ul>
        <li><strong>Original data preservation:</strong> Base columns never modified</li>
        <li><strong>Change timestamps:</strong> When modifications were made</li>
        <li><strong>User tracking:</strong> Who made the changes</li>
        <li><strong>Method tracking:</strong> Which tool/algorithm was used</li>
        <li><strong>Parameter logging:</strong> Settings and values used</li>
        </ul>
        """)
        tracking_layout.addWidget(tracking_text)
        layout.addWidget(tracking_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_best_practices_page(self):
        """Create the best practices and tips page."""
        page = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        title = QLabel("Best Practices & Professional Tips")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Quality control practices
        qc_group = QGroupBox("Quality Control Best Practices")
        qc_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        qc_layout = QVBoxLayout(qc_group)
        
        qc_text = QTextEdit()
        qc_text.setReadOnly(True)
        qc_text.setMaximumHeight(180)
        qc_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        qc_text.setHtml("""
        <p><strong>Before Making Changes:</strong></p>
        <ul>
        <li>Review the entire dataset for patterns and context</li>
        <li>Check field notes and maintenance logs for explanation of anomalies</li>
        <li>Enable all visualization filters to see the complete picture</li>
        <li>Look for systematic issues that might require different approaches</li>
        </ul>
        
        <p><strong>During Editing:</strong></p>
        <ul>
        <li>Make small, targeted corrections rather than large wholesale changes</li>
        <li>Always preview changes before applying them</li>
        <li>Document the reasoning behind significant modifications</li>
        <li>Cross-reference with nearby wells or regional data when possible</li>
        </ul>
        
        <p><strong>After Editing:</strong></p>
        <ul>
        <li>Review the modified data for unintended consequences</li>
        <li>Check that trends and patterns remain hydrologically reasonable</li>
        <li>Verify that manual measurements still align with corrected data</li>
        </ul>
        """)
        qc_layout.addWidget(qc_text)
        layout.addWidget(qc_group)
        
        # Tool-specific tips
        tips_group = QGroupBox("Tool-Specific Tips")
        tips_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tips_layout = QVBoxLayout(tips_group)
        
        tips_text = QTextEdit()
        tips_text.setReadOnly(True)
        tips_text.setMaximumHeight(160)
        tips_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tips_text.setHtml("""
        <p><strong>Spike Fixing Tips:</strong></p>
        <ul>
        <li>Select anchor points in stable, representative data</li>
        <li>Avoid fixing spikes during pumping tests or other legitimate rapid changes</li>
        <li>Use zoom for precise point selection</li>
        <li>Consider the hydrogeological context - not all spikes are errors</li>
        </ul>
        
        <p><strong>Compensation Tips:</strong></p>
        <ul>
        <li>Verify master baro data quality before applying compensation</li>
        <li>Look for inverse correlation patterns between baro and water level</li>
        <li>Apply compensation to contiguous time periods for best results</li>
        </ul>
        
        <p><strong>Baseline Adjustment Tips:</strong></p>
        <ul>
        <li>Use recent, high-quality manual measurements for calibration</li>
        <li>Consider seasonal variations when selecting reference measurements</li>
        <li>Double-check calculation signs - elevation differences can be confusing</li>
        </ul>
        """)
        tips_layout.addWidget(tips_text)
        layout.addWidget(tips_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_troubleshooting_page(self):
        """Create the troubleshooting and common issues page."""
        page = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        title = QLabel("Troubleshooting & Common Issues")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 8px; padding: 0px;")
        layout.addWidget(title)
        
        # Common problems
        problems_group = QGroupBox("Common Problems & Solutions")
        problems_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        problems_layout = QVBoxLayout(problems_group)
        
        problems_text = QTextEdit()
        problems_text.setReadOnly(True)
        problems_text.setMaximumHeight(220)
        problems_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        problems_text.setHtml("""
        <p><strong>Problem:</strong> "I can't see my spike corrections in the plot"</p>
        <p><strong>Solution:</strong> This was fixed! The plot now properly shows spike-corrected data. Refresh the plot if you still don't see changes.</p>
        
        <p><strong>Problem:</strong> "The baseline adjustment went the wrong direction"</p>
        <p><strong>Solution:</strong> Use the ± button next to the adjustment value to toggle the sign, or recalculate using Point 1 = current value, Point 2 = target value.</p>
        
        <p><strong>Problem:</strong> "I selected the wrong points for spike fixing"</p>
        <p><strong>Solution:</strong> Use "Remove Last Pair" button or press ESC to cancel selection mode and start over.</p>
        
        <p><strong>Problem:</strong> "The compensation didn't work as expected"</p>
        <p><strong>Solution:</strong> Check that master baro data is available and high quality for the selected time period. Verify the time range selection.</p>
        
        <p><strong>Problem:</strong> "Data gaps are not showing"</p>
        <p><strong>Solution:</strong> Ensure "Show Data Gaps" checkbox is enabled. Gaps only appear when time intervals exceed 20 minutes.</p>
        
        <p><strong>Problem:</strong> "Changes aren't being saved"</p>
        <p><strong>Solution:</strong> Make sure to click "Apply Changes" after making modifications. Check database permissions if issues persist.</p>
        """)
        problems_layout.addWidget(problems_text)
        layout.addWidget(problems_group)
        
        # Error messages
        errors_group = QGroupBox("Understanding Error Messages")
        errors_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        errors_layout = QVBoxLayout(errors_group)
        
        errors_text = QTextEdit()
        errors_text.setReadOnly(True)
        errors_text.setMaximumHeight(110)
        errors_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        errors_text.setHtml("""
        <p><strong>"No data selected":</strong> You need to select a time range or data points before using edit tools</p>
        <p><strong>"Insufficient data for processing":</strong> The selected range doesn't contain enough data points for the operation</p>
        <p><strong>"Master baro data not available":</strong> Barometric compensation requires master barologger data for the selected period</p>
        <p><strong>"Invalid adjustment value":</strong> Check that numeric inputs are properly formatted and within reasonable ranges</p>
        """)
        errors_layout.addWidget(errors_text)
        layout.addWidget(errors_group)
        
        # Getting help
        help_group = QGroupBox("Getting Additional Help")
        help_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        help_layout = QVBoxLayout(help_group)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(75)
        help_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        help_text.setHtml("""
        <p>If you continue to experience issues:</p>
        <ul>
        <li>Check the application logs for detailed error information</li>
        <li>Consult with your system administrator about database permissions</li>
        <li>Review the main application help system for broader context</li>
        <li>Contact the development team with specific error messages and steps to reproduce</li>
        </ul>
        """)
        help_layout.addWidget(help_text)
        layout.addWidget(help_group)
        
        layout.addStretch()
        page.setWidget(content)
        page.setMinimumWidth(800)
        return page
        
    def create_footer(self, layout):
        """Create footer with close button."""
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(ButtonStyles.get_cancel_button_style())
        close_btn.clicked.connect(self.close)
        footer_layout.addWidget(close_btn)
        
        layout.addLayout(footer_layout)
        
    def on_navigation_changed(self):
        """Handle navigation tree selection changes."""
        try:
            current_item = self.nav_tree.currentItem()
            if current_item:
                topic = current_item.data(0, Qt.UserRole)
                if topic and topic in self.nav_items:
                    page_index = self.nav_items[topic]
                    self.content_stack.setCurrentIndex(page_index)
        except Exception as e:
            logger.error(f"Error handling navigation change: {e}")
            
    def show_topic(self, topic_name):
        """Show a specific topic by name."""
        if topic_name in self.nav_items:
            page_index = self.nav_items[topic_name]
            self.content_stack.setCurrentIndex(page_index)
            
            # Also select the item in the tree
            for i in range(self.nav_tree.topLevelItemCount()):
                item = self.nav_tree.topLevelItem(i)
                if item.data(0, Qt.UserRole) == topic_name:
                    self.nav_tree.setCurrentItem(item)
                    break
                # Check child items
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.data(0, Qt.UserRole) == topic_name:
                        self.nav_tree.setCurrentItem(child)
                        item.setExpanded(True)
                        break