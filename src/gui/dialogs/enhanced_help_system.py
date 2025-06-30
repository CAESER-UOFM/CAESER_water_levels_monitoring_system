"""
Enhanced Help System with Better UX
- Interactive tooltips and popups
- Visual flowcharts and examples
- Progressive disclosure
- Search functionality
- Better navigation
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QTabWidget, QWidget, QMessageBox, QScrollArea, QLineEdit,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QDesktopServices, QCursor, QPainter, QPixmap
import webbrowser

logger = logging.getLogger(__name__)


class EnhancedHelpSystem(QDialog):
    """
    Enhanced help system with better UX and visual elements.
    """
    
    def __init__(self, parent=None, initial_topic=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.initial_topic = initial_topic
        
        self.setWindowTitle("Water Levels Help - Enhanced")
        self.setModal(False)
        self.resize(1400, 900)
        
        self.setup_ui()
        self.setup_content()
        
        if initial_topic:
            self.navigate_to_topic(initial_topic)
        
    def setup_ui(self):
        """Setup enhanced UI with search and navigation."""
        layout = QVBoxLayout(self)
        
        # Header with search
        header_layout = QHBoxLayout()
        
        title = QLabel("💧 Water Levels Help & Documentation")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Search functionality
        search_label = QLabel("🔍 Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search help topics...")
        self.search_box.textChanged.connect(self.search_content)
        
        header_layout.addWidget(search_label)
        header_layout.addWidget(self.search_box)
        
        layout.addLayout(header_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Navigation tree (left side)
        self.create_navigation_tree(splitter)
        
        # Content area (right side)
        self.create_content_area(splitter)
        
        # Set splitter proportions
        splitter.setSizes([300, 1100])
        layout.addWidget(splitter)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        
        self.forward_btn = QPushButton("Forward →")
        self.forward_btn.clicked.connect(self.go_forward)
        self.forward_btn.setEnabled(False)
        
        bottom_layout.addWidget(self.back_btn)
        bottom_layout.addWidget(self.forward_btn)
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
        
        # Navigation history
        self.navigation_history = []
        self.history_index = -1
    
    def create_navigation_tree(self, parent):
        """Create navigation tree with organized topics."""
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderLabel("Help Topics")
        self.nav_tree.itemClicked.connect(self.on_topic_selected)
        
        # Quick Start section
        quick_start = QTreeWidgetItem(["🚀 Quick Start"])
        quick_start.addChild(QTreeWidgetItem(["First Time Setup"]))
        quick_start.addChild(QTreeWidgetItem(["Import Your First Data"]))
        quick_start.addChild(QTreeWidgetItem(["5-Minute Tutorial"]))
        self.nav_tree.addTopLevelItem(quick_start)
        
        # How It Works section  
        how_works = QTreeWidgetItem(["⚙️ How It Works"])
        how_works.addChild(QTreeWidgetItem(["Data Processing Pipeline"]))
        how_works.addChild(QTreeWidgetItem(["Barometric Compensation"]))
        how_works.addChild(QTreeWidgetItem(["Quality Control Logic"]))
        how_works.addChild(QTreeWidgetItem(["File Format Guide"]))
        self.nav_tree.addTopLevelItem(how_works)
        
        # Application Tabs section
        app_tabs = QTreeWidgetItem(["📊 Application Tabs"])
        app_tabs.addChild(QTreeWidgetItem(["Database Tab"]))
        app_tabs.addChild(QTreeWidgetItem(["Barologger Tab"]))
        app_tabs.addChild(QTreeWidgetItem(["Water Level Tab"]))
        app_tabs.addChild(QTreeWidgetItem(["Recharge Tab"]))
        app_tabs.addChild(QTreeWidgetItem(["Runs Tab"]))
        self.nav_tree.addTopLevelItem(app_tabs)
        
        # Advanced Topics section
        advanced = QTreeWidgetItem(["🔬 Advanced Topics"])
        advanced.addChild(QTreeWidgetItem(["Recharge Calculations"]))
        advanced.addChild(QTreeWidgetItem(["Cloud Collaboration"]))
        advanced.addChild(QTreeWidgetItem(["API Integration"]))
        advanced.addChild(QTreeWidgetItem(["Custom Sensors"]))
        self.nav_tree.addTopLevelItem(advanced)
        
        # Troubleshooting section
        troubleshoot = QTreeWidgetItem(["🔧 Troubleshooting"])
        troubleshoot.addChild(QTreeWidgetItem(["Common Issues"]))
        troubleshoot.addChild(QTreeWidgetItem(["Data Import Problems"]))
        troubleshoot.addChild(QTreeWidgetItem(["Performance Tips"]))
        troubleshoot.addChild(QTreeWidgetItem(["Error Messages"]))
        self.nav_tree.addTopLevelItem(troubleshoot)
        
        parent.addWidget(self.nav_tree)
    
    def create_content_area(self, parent):
        """Create main content display area."""
        self.content_stack = QStackedWidget()
        
        # Default welcome page
        welcome_page = self.create_welcome_page()
        self.content_stack.addWidget(welcome_page)
        
        parent.addWidget(self.content_stack)
    
    def create_welcome_page(self):
        """Create an engaging welcome page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        content = QTextEdit()
        content.setHtml(self.get_welcome_content())
        content.setReadOnly(True)
        layout.addWidget(content)
        
        return widget
    
    def get_welcome_content(self):
        """Get welcome page content with better UX."""
        return """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="color: #2c5aa0; text-align: center;">
                🌊 Welcome to Water Levels Help
            </h1>
            
            <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                        padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h2 style="margin-top: 0;">🎯 What do you want to do?</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                    
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="color: #1976d2; margin-top: 0;">🚀 First Time User</h3>
                        <p>New to the app? Start here for a quick tutorial and setup guide.</p>
                        <button style="background: #4caf50; color: white; border: none; padding: 8px 16px; 
                                       border-radius: 4px; cursor: pointer;">
                            Start Tutorial →
                        </button>
                    </div>
                    
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="color: #1976d2; margin-top: 0;">📁 Import Data</h3>
                        <p>Need to import XLE files or other data? Get step-by-step guidance.</p>
                        <button style="background: #2196f3; color: white; border: none; padding: 8px 16px; 
                                       border-radius: 4px; cursor: pointer;">
                            Import Guide →
                        </button>
                    </div>
                    
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="color: #1976d2; margin-top: 0;">⚙️ How It Works</h3>
                        <p>Understand the technical details and processing behind the scenes.</p>
                        <button style="background: #ff9800; color: white; border: none; padding: 8px 16px; 
                                       border-radius: 4px; cursor: pointer;">
                            Learn More →
                        </button>
                    </div>
                    
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="color: #1976d2; margin-top: 0;">🔧 Having Issues?</h3>
                        <p>Something not working? Check our troubleshooting guide.</p>
                        <button style="background: #f44336; color: white; border: none; padding: 8px 16px; 
                                       border-radius: 4px; cursor: pointer;">
                            Fix Problems →
                        </button>
                    </div>
                </div>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;">
                <h3 style="margin-top: 0; color: #e65100;">💡 Pro Tip</h3>
                <p>Use the search box above to quickly find specific topics. Try searching for 
                "import", "barometric", or "recharge" to jump straight to what you need!</p>
            </div>
            
            <div style="margin-top: 30px; text-align: center; color: #666;">
                <p>Built by groundwater nerds, for groundwater nerds. 
                <br>Questions? Check the troubleshooting section or contact support.</p>
            </div>
        </div>
        """
    
    def get_data_processing_content(self):
        """Technical content about how data processing works."""
        return """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="color: #2c5aa0;">⚙️ How Data Processing Works</h1>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">🔄 Data Processing Pipeline</h3>
                <p>Understanding how your XLE files become beautiful, corrected water level data:</p>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">1️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">File Import & Validation</h4>
                    <p style="margin: 5px 0;">XLE files are parsed, metadata extracted, timestamps validated</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">2️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Quality Control</h4>
                    <p style="margin: 5px 0;">Automatic detection of outliers, gaps, and sensor issues</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">3️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Barometric Compensation</h4>
                    <p style="margin: 5px 0;">Removes atmospheric pressure effects using barologger data</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">4️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Water Level Calculation</h4>
                    <p style="margin: 5px 0;">Converts pressure to elevation using well reference points</p>
                </div>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #e65100;">🧮 The Math Behind Barometric Compensation</h3>
                <p><strong>Why we need it:</strong> Atmospheric pressure changes affect the pressure readings 
                from your transducers. A storm system can make it look like water levels changed when they didn't!</p>
                
                <div style="background: white; padding: 10px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    Water Pressure = Total Pressure - Atmospheric Pressure<br>
                    Water Level = (Water Pressure × 2.31) + Reference Elevation
                </div>
                
                <p><strong>What the app does:</strong></p>
                <ul>
                    <li>Finds the nearest barometric reading in time</li>
                    <li>Subtracts it from your transducer pressure</li>
                    <li>Converts the result to feet of water</li>
                    <li>Adds your well's reference elevation</li>
                </ul>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">🔍 Quality Control Logic</h3>
                <p>The app automatically flags data that might be problematic:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Flag</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">What It Means</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Action</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">🟢 Good</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Data passes all checks</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Use confidently</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">🟡 Questionable</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Possible sensor drift or outlier</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Review manually</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">🔴 Error</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Clear data problem</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Exclude from analysis</td>
                    </tr>
                </table>
            </div>
        </div>
        """
    
    def setup_content(self):
        """Setup all content pages."""
        # Add different content pages to the stack
        
        # Data processing page
        processing_page = QWidget()
        layout = QVBoxLayout(processing_page)
        content = QTextEdit()
        content.setHtml(self.get_data_processing_content())
        content.setReadOnly(True)
        layout.addWidget(content)
        self.content_stack.addWidget(processing_page)
    
    def on_topic_selected(self, item, column):
        """Handle topic selection from navigation tree."""
        topic = item.text(0)
        self.navigate_to_topic(topic)
    
    def navigate_to_topic(self, topic):
        """Navigate to specific topic."""
        # Add to history
        if self.history_index < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[:self.history_index + 1]
        
        self.navigation_history.append(topic)
        self.history_index = len(self.navigation_history) - 1
        
        # Update navigation buttons
        self.back_btn.setEnabled(self.history_index > 0)
        self.forward_btn.setEnabled(False)
        
        # Load content based on topic
        if "Data Processing Pipeline" in topic:
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_stack.setCurrentIndex(0)
    
    def go_back(self):
        """Go back in navigation history."""
        if self.history_index > 0:
            self.history_index -= 1
            topic = self.navigation_history[self.history_index]
            self.navigate_to_topic_without_history(topic)
            
            self.back_btn.setEnabled(self.history_index > 0)
            self.forward_btn.setEnabled(True)
    
    def go_forward(self):
        """Go forward in navigation history."""
        if self.history_index < len(self.navigation_history) - 1:
            self.history_index += 1
            topic = self.navigation_history[self.history_index]
            self.navigate_to_topic_without_history(topic)
            
            self.forward_btn.setEnabled(self.history_index < len(self.navigation_history) - 1)
            self.back_btn.setEnabled(True)
    
    def navigate_to_topic_without_history(self, topic):
        """Navigate without adding to history."""
        if "Data Processing Pipeline" in topic:
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_stack.setCurrentIndex(0)
    
    def search_content(self, search_text):
        """Search through help content."""
        if not search_text:
            return
        
        # Simple search implementation
        # In a real implementation, you'd search through all content
        # and highlight matches
        
        search_results = []
        if "import" in search_text.lower():
            search_results.append("Import Your First Data")
        if "barometric" in search_text.lower():
            search_results.append("Barometric Compensation")
        if "recharge" in search_text.lower():
            search_results.append("Recharge Calculations")
        
        # Update navigation tree to show search results
        # This is a simplified version - you'd want more sophisticated search
        pass


# Tooltip helper for context-sensitive help
class ContextualTooltip:
    """
    Enhanced tooltip system for providing context-sensitive help.
    """
    
    @staticmethod
    def add_help_tooltip(widget, help_text, help_type="info"):
        """Add enhanced tooltip with help content."""
        
        if help_type == "info":
            icon = "ℹ️"
            color = "#2196f3"
        elif help_type == "warning":
            icon = "⚠️"
            color = "#ff9800"
        elif help_type == "tip":
            icon = "💡"
            color = "#4caf50"
        else:
            icon = "❓"
            color = "#9e9e9e"
        
        tooltip_html = f"""
        <div style="padding: 10px; max-width: 300px; font-family: Arial, sans-serif;">
            <div style="color: {color}; font-weight: bold; margin-bottom: 5px;">
                {icon} Help
            </div>
            <div style="color: #333; line-height: 1.4;">
                {help_text}
            </div>
        </div>
        """
        
        widget.setToolTip(tooltip_html)