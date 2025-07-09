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
        
        # System Features section
        system_features = QTreeWidgetItem(["🔧 System Features"])
        system_features.addChild(QTreeWidgetItem(["System Feedback & Documentation"]))
        system_features.addChild(QTreeWidgetItem(["Master Baro Concept"]))
        system_features.addChild(QTreeWidgetItem(["User Flag Comments"]))
        system_features.addChild(QTreeWidgetItem(["Protocol & Well Notes"]))
        self.nav_tree.addTopLevelItem(system_features)
        
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
        
        # System Feedback page
        feedback_page = QWidget()
        layout = QVBoxLayout(feedback_page)
        content = QTextEdit()
        content.setHtml(self.get_system_feedback_content())
        content.setReadOnly(True)
        layout.addWidget(content)
        self.content_stack.addWidget(feedback_page)
        
        # Master Baro page
        master_baro_page = QWidget()
        layout = QVBoxLayout(master_baro_page)
        content = QTextEdit()
        content.setHtml(self.get_master_baro_content())
        content.setReadOnly(True)
        layout.addWidget(content)
        self.content_stack.addWidget(master_baro_page)
        
        # User Flag Comments page
        user_flags_page = QWidget()
        layout = QVBoxLayout(user_flags_page)
        content = QTextEdit()
        content.setHtml(self.get_user_flags_content())
        content.setReadOnly(True)
        layout.addWidget(content)
        self.content_stack.addWidget(user_flags_page)
        
        # Protocol & Well Notes page
        notes_page = QWidget()
        layout = QVBoxLayout(notes_page)
        content = QTextEdit()
        content.setHtml(self.get_protocol_notes_content())
        content.setReadOnly(True)
        layout.addWidget(content)
        self.content_stack.addWidget(notes_page)
    
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
        elif "System Feedback & Documentation" in topic:
            self.content_stack.setCurrentIndex(2)
        elif "Master Baro Concept" in topic:
            self.content_stack.setCurrentIndex(3)
        elif "User Flag Comments" in topic:
            self.content_stack.setCurrentIndex(4)
        elif "Protocol & Well Notes" in topic:
            self.content_stack.setCurrentIndex(5)
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
        elif "System Feedback & Documentation" in topic:
            self.content_stack.setCurrentIndex(2)
        elif "Master Baro Concept" in topic:
            self.content_stack.setCurrentIndex(3)
        elif "User Flag Comments" in topic:
            self.content_stack.setCurrentIndex(4)
        elif "Protocol & Well Notes" in topic:
            self.content_stack.setCurrentIndex(5)
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

    def get_system_feedback_content(self):
        """Content about system feedback mechanisms."""
        return """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="color: #2c5aa0;">📝 System Feedback & Documentation</h1>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">🎯 Overview</h3>
                <p>The CAESER system provides multiple ways to document your work, communicate with collaborators, 
                and track data quality decisions. Understanding these feedback mechanisms helps you work more effectively 
                and maintain clear documentation.</p>
            </div>
            
            <h2 style="color: #1976d2;">🔄 Types of System Feedback</h2>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">📢</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">General Feedback (Main Window)</h4>
                    <p style="margin: 5px 0;"><strong>Purpose:</strong> Real-time system status and operation feedback</p>
                    <p style="margin: 5px 0;"><strong>Storage:</strong> Local application logs (not synchronized)</p>
                    <p style="margin: 5px 0;"><strong>Examples:</strong> Import progress, processing status, error messages</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">🚩</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">User Flag Comments (Water Level Tab)</h4>
                    <p style="margin: 5px 0;"><strong>Purpose:</strong> Quality control flags for wells</p>
                    <p style="margin: 5px 0;"><strong>Storage:</strong> Database (cloud synchronized)</p>
                    <p style="margin: 5px 0;"><strong>How to use:</strong> Click flag icons in wells table to cycle through states</p>
                    <p style="margin: 5px 0;"><strong>States:</strong> 🔘 Not checked, 🔴 Error found, 🟢 Approved</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">📋</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Protocol Feedback (Edit Dialog)</h4>
                    <p style="margin: 5px 0;"><strong>Purpose:</strong> Document data processing decisions and methods</p>
                    <p style="margin: 5px 0;"><strong>Storage:</strong> Database (cloud synchronized)</p>
                    <p style="margin: 5px 0;"><strong>How to use:</strong> Add notes in the Protocol section of the Edit Water Levels dialog</p>
                    <p style="margin: 5px 0;"><strong>Best for:</strong> Processing methods, correction decisions, quality control notes</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">📝</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Well Notes (Edit Dialog)</h4>
                    <p style="margin: 5px 0;"><strong>Purpose:</strong> Well-specific observations and context</p>
                    <p style="margin: 5px 0;"><strong>Storage:</strong> Database (cloud synchronized)</p>
                    <p style="margin: 5px 0;"><strong>How to use:</strong> Add notes in the Notes section of the Edit Water Levels dialog</p>
                    <p style="margin: 5px 0;"><strong>Best for:</strong> Location context, environmental conditions, field observations</p>
                </div>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #e65100;">💾 Storage & Synchronization</h3>
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Feedback Type</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Storage Location</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Cloud Sync</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">General Feedback</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Local logs</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">❌ No</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">User Flag Comments</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Database</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">✅ Yes</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">Protocol Feedback</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Database</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">✅ Yes</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">Well Notes</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Database</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">✅ Yes</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">💡 Best Practices</h3>
                <ul>
                    <li><strong>Use User Flags systematically</strong> for quality control workflow</li>
                    <li><strong>Document Protocol decisions</strong> to maintain processing transparency</li>
                    <li><strong>Include Well Notes context</strong> for location-specific observations</li>
                    <li><strong>Regular synchronization</strong> keeps team members informed</li>
                    <li><strong>Backup feedback data</strong> along with measurement data</li>
                </ul>
            </div>
        </div>
        """

    def get_master_baro_content(self):
        """Content about Master Baro concept."""
        return """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="color: #2c5aa0;">🌡️ Master Baro Concept</h1>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">🎯 What is Master Baro?</h3>
                <p>The <strong>Master Barometric Data (Master Baro)</strong> is a core concept developed for the CAESER system 
                that ensures consistent atmospheric pressure compensation across all water level calculations.</p>
            </div>
            
            <h2 style="color: #1976d2;">🔧 Key Principles</h2>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">🎯</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Unified Compensation</h4>
                    <p style="margin: 5px 0;">All water level compensations use the Master Baro, not individual barologgers. 
                    This ensures consistency across your entire monitoring network.</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">🔗</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Multi-Source Integration</h4>
                    <p style="margin: 5px 0;">Combines data from multiple barologgers to create a single, 
                    high-quality atmospheric pressure record using weighted averaging.</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">📊</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Quality Optimization</h4>
                    <p style="margin: 5px 0;">Prioritizes high-quality data sources and fills gaps intelligently. 
                    Even with only one barologger, the system creates a Master Baro for consistency.</p>
                </div>
            </div>
            
            <h2 style="color: #1976d2;">⚙️ How It Works</h2>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #e65100;">🔄 Master Baro Workflow</h3>
                <ol>
                    <li><strong>Import Individual Barologgers:</strong> Import XLE files from all available atmospheric pressure loggers</li>
                    <li><strong>Quality Assessment:</strong> Review individual barologger quality and coverage</li>
                    <li><strong>Master Baro Configuration:</strong> Use the Edit Master Baro dialog to define contributing loggers</li>
                    <li><strong>Master Baro Generation:</strong> System automatically creates the Master Barometric record</li>
                    <li><strong>Quality Validation:</strong> Review Master Baro quality and coverage</li>
                    <li><strong>Water Level Compensation:</strong> All water level calculations use the Master Baro</li>
                </ol>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">⚙️ Edit Master Baro Dialog</h3>
                <p>Use this dialog to configure your Master Baro:</p>
                <ul>
                    <li><strong>Barologger Selection:</strong> Choose which barologgers contribute</li>
                    <li><strong>Weight Assignment:</strong> Set relative importance of each barologger</li>
                    <li><strong>Quality Thresholds:</strong> Define minimum quality requirements</li>
                    <li><strong>Gap Management:</strong> Configure intelligent interpolation parameters</li>
                </ul>
                <p><em>Access via: Barologger Tab → Edit Master Baro button</em></p>
            </div>
            
            <h2 style="color: #1976d2;">🚀 Benefits</h2>
            
            <div style="background: #f1f8e9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #388e3c;">✅ Consistency Benefits</h3>
                <ul>
                    <li><strong>Uniform Compensation:</strong> All wells use the same atmospheric pressure reference</li>
                    <li><strong>Reproducible Results:</strong> Consistent results across different analysis runs</li>
                    <li><strong>Standardized Processing:</strong> Eliminates well-to-well compensation variations</li>
                    <li><strong>Quality Assurance:</strong> Systematic approach to atmospheric pressure management</li>
                </ul>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #e65100;">🔮 Future Enhancements</h3>
                <p><em>The Master Baro concept is planned for enhancement in future versions:</em></p>
                <ul>
                    <li><strong>Well-Specific Baro Assignment:</strong> Allow individual wells to use specific barologgers</li>
                    <li><strong>Regional Baro Networks:</strong> Support multiple Master Baros for different geographic regions</li>
                    <li><strong>Advanced Quality Weighting:</strong> More sophisticated algorithms for barologger prioritization</li>
                    <li><strong>Automatic Baro Selection:</strong> Intelligent selection of optimal barologger for each well</li>
                </ul>
                <p><em>These enhancements will provide more flexibility while maintaining the consistency benefits 
                of the Master Baro approach.</em></p>
            </div>
        </div>
        """

    def get_user_flags_content(self):
        """Content about User Flag Comments."""
        return """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="color: #2c5aa0;">🚩 User Flag Comments</h1>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">🎯 Purpose</h3>
                <p>User Flag Comments provide a quick and visual way to track quality control decisions for wells 
                in your monitoring network. They help you and your team keep track of which wells have been reviewed, 
                which need attention, and which are approved for analysis.</p>
            </div>
            
            <h2 style="color: #1976d2;">📍 Location & Access</h2>
            <p><strong>Where to find:</strong> Water Level Tab → Wells Table → User Flag column (first column)</p>
            
            <h2 style="color: #1976d2;">🔄 How to Use</h2>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">1️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Navigate to Water Level Tab</h4>
                    <p style="margin: 5px 0;">Open the Water Level Tab and locate the wells table</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">2️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Click Flag Icon</h4>
                    <p style="margin: 5px 0;">Click on any flag icon in the User Flag column to cycle through states</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #f8f9fa; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">3️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Automatic Save</h4>
                    <p style="margin: 5px 0;">Status changes are automatically saved to the database</p>
                </div>
            </div>
            
            <h2 style="color: #1976d2;">🎨 Flag States</h2>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Icon</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Status</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Meaning</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">When to Use</th>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">🔘</td>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Not Checked</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Well hasn't been reviewed yet</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Default state for new wells</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">🔴</td>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Error Found</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Issues identified that need attention</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Data problems, sensor issues, processing errors</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">🟢</td>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Approved</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Well data is good for analysis</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Quality control passed, ready for use</td>
                    </tr>
                </table>
            </div>
            
            <h2 style="color: #1976d2;">💾 Storage & Sync</h2>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">💾 Data Storage</h3>
                <ul>
                    <li><strong>Database Storage:</strong> Flags are stored in the local SQLite database</li>
                    <li><strong>Cloud Synchronization:</strong> Automatically synced when using cloud databases</li>
                    <li><strong>Persistence:</strong> Flags are maintained across application sessions</li>
                    <li><strong>Team Sharing:</strong> Cloud databases allow team members to see flag states</li>
                </ul>
            </div>
            
            <h2 style="color: #1976d2;">🔄 Workflow Integration</h2>
            
            <div style="background: #f1f8e9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #388e3c;">✅ Quality Control Workflow</h3>
                <ol>
                    <li><strong>Data Import:</strong> Import water level data (all wells start as "Not Checked")</li>
                    <li><strong>Initial Review:</strong> Review each well's data quality</li>
                    <li><strong>Flag Decisions:</strong> Mark wells as "Error" or "Approved" based on review</li>
                    <li><strong>Problem Resolution:</strong> Address wells flagged with errors</li>
                    <li><strong>Final Approval:</strong> Change resolved wells from "Error" to "Approved"</li>
                    <li><strong>Analysis:</strong> Proceed with analysis using only "Approved" wells</li>
                </ol>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #e65100;">💡 Best Practices</h3>
                <ul>
                    <li><strong>Systematic Review:</strong> Work through wells systematically rather than randomly</li>
                    <li><strong>Document Issues:</strong> Use Protocol Feedback to document specific problems found</li>
                    <li><strong>Team Coordination:</strong> Use flags to communicate QC status with team members</li>
                    <li><strong>Regular Updates:</strong> Update flags as data processing progresses</li>
                    <li><strong>Final Check:</strong> Review all flags before major analysis or reporting</li>
                </ul>
            </div>
        </div>
        """

    def get_protocol_notes_content(self):
        """Content about Protocol Feedback and Well Notes."""
        return """
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="color: #2c5aa0;">📋 Protocol & Well Notes</h1>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">🎯 Overview</h3>
                <p>Protocol Feedback and Well Notes provide detailed documentation capabilities within the 
                Edit Water Levels dialog. These tools help you maintain comprehensive records of data 
                processing decisions and well-specific context information.</p>
            </div>
            
            <h2 style="color: #1976d2;">📍 Location & Access</h2>
            <p><strong>Where to find:</strong> Water Level Tab → Select a well → Click "Edit Water Levels" → 
            Protocol section and Notes section</p>
            
            <h2 style="color: #1976d2;">📋 Protocol Feedback</h2>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">🎯 Purpose</h3>
                <p>Document data processing decisions, methodological choices, and quality control steps. 
                This creates a transparent record of how data was processed and why specific decisions were made.</p>
                
                <h4 style="color: #1976d2;">Best Uses:</h4>
                <ul>
                    <li><strong>Processing Methods:</strong> Document correction algorithms and parameters used</li>
                    <li><strong>Quality Control Records:</strong> Track data validation steps and results</li>
                    <li><strong>Decision Documentation:</strong> Explain why certain data was accepted or rejected</li>
                    <li><strong>Methodology Notes:</strong> Record processing protocols for reproducibility</li>
                </ul>
            </div>
            
            <h2 style="color: #1976d2;">📝 Well Notes</h2>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">🎯 Purpose</h3>
                <p>Record well-specific observations, environmental context, and location-specific information 
                that affects data interpretation. These notes provide valuable context for understanding data patterns.</p>
                
                <h4 style="color: #1976d2;">Best Uses:</h4>
                <ul>
                    <li><strong>Location Context:</strong> Environmental conditions affecting the well</li>
                    <li><strong>Field Observations:</strong> Notes from site visits and maintenance</li>
                    <li><strong>Installation Details:</strong> Well construction and instrumentation notes</li>
                    <li><strong>Historical Information:</strong> Past events or changes at the site</li>
                </ul>
            </div>
            
            <h2 style="color: #1976d2;">🔄 How to Use</h2>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #e3f2fd; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">1️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Select a Well</h4>
                    <p style="margin: 5px 0;">In the Water Level Tab, click on a well in the wells table to select it</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #e3f2fd; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">2️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Open Edit Dialog</h4>
                    <p style="margin: 5px 0;">Click the "Edit Water Levels" button to open the editing dialog</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #e3f2fd; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">3️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Navigate to Sections</h4>
                    <p style="margin: 5px 0;">Find the Protocol and Notes sections within the edit dialog</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #e3f2fd; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">4️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Add Documentation</h4>
                    <p style="margin: 5px 0;">Add your protocol notes and well-specific observations</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; padding: 15px; 
                        background: #e3f2fd; border-radius: 8px;">
                <div style="font-size: 24px; margin-right: 15px;">5️⃣</div>
                <div>
                    <h4 style="margin: 0; color: #1976d2;">Save Changes</h4>
                    <p style="margin: 5px 0;">Save the dialog to preserve your notes in the database</p>
                </div>
            </div>
            
            <h2 style="color: #1976d2;">💾 Storage & Synchronization</h2>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Note Type</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Storage Location</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Cloud Sync</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Accessibility</th>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Protocol Feedback</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Database tables</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">✅ Yes</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">All team members</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Well Notes</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Wells table</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">✅ Yes</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">All team members</td>
                    </tr>
                </table>
            </div>
            
            <h2 style="color: #1976d2;">📚 Documentation Examples</h2>
            
            <div style="background: #f1f8e9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #388e3c;">📋 Protocol Feedback Examples</h3>
                <ul>
                    <li><em>"Applied spike correction to remove 3 outliers on 2024-01-15 due to sensor malfunction"</em></li>
                    <li><em>"Used linear interpolation for 4-hour gap from 2024-02-10 08:00 to 12:00"</em></li>
                    <li><em>"Excluded data from 2024-03-01 to 2024-03-05 due to well maintenance activities"</em></li>
                    <li><em>"Applied custom barometric compensation using nearest weather station data"</em></li>
                </ul>
            </div>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">📝 Well Notes Examples</h3>
                <ul>
                    <li><em>"Well located in agricultural area, possible irrigation effects during summer months"</em></li>
                    <li><em>"Transducer installed at 15 ft depth, total well depth 45 ft, screened interval 25-40 ft"</em></li>
                    <li><em>"Site accessible only during dry weather due to dirt road conditions"</em></li>
                    <li><em>"Historical pumping test conducted in 2019, results available in project files"</em></li>
                </ul>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #e65100;">💡 Best Practices</h3>
                <ul>
                    <li><strong>Be Specific:</strong> Include dates, times, and specific parameter values</li>
                    <li><strong>Explain Reasoning:</strong> Document why decisions were made, not just what was done</li>
                    <li><strong>Regular Updates:</strong> Add notes as processing progresses, not just at the end</li>
                    <li><strong>Team Communication:</strong> Write notes that other team members can understand</li>
                    <li><strong>Version Control:</strong> Note when significant changes are made to data or processing</li>
                    <li><strong>Reference Standards:</strong> Cite relevant standards or procedures when applicable</li>
                </ul>
            </div>
        </div>
        """


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