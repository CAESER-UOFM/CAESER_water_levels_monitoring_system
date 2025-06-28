"""
Draft Selection Dialog

Dialog for choosing between loading a draft or downloading fresh from cloud.
Shows version comparison and expandable change details.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QTextEdit, QFrame, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette

logger = logging.getLogger(__name__)


class CollapsibleSection(QWidget):
    """A collapsible section widget"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                font-weight: bold;
                padding: 12px;
                background-color: #f8f9fa;
                color: #495057;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:checked {
                background-color: #e3f2fd;
                border-color: #2196f3;
                color: #1976d2;
            }
        """)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_area.setVisible(False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)
        
        self.toggle_button.clicked.connect(self.toggle_content)
    
    def toggle_content(self):
        """Toggle the visibility of content"""
        is_visible = self.content_area.isVisible()
        self.content_area.setVisible(not is_visible)
        arrow = "▼" if not is_visible else "▶"
        text = self.toggle_button.text()
        if text.startswith("▶") or text.startswith("▼"):
            text = text[2:]
        self.toggle_button.setText(f"{arrow} {text}")
    
    def add_widget(self, widget):
        """Add widget to content area"""
        self.content_layout.addWidget(widget)
    
    def set_expanded(self, expanded=True):
        """Set expanded state"""
        if expanded != self.content_area.isVisible():
            self.toggle_content()


class DraftSelectionDialog(QDialog):
    """Dialog for selecting between draft and cloud download"""
    
    def __init__(self, project_name: str, draft_info: dict, cloud_info: dict, parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.draft_info = draft_info
        self.cloud_info = cloud_info
        self.selection = None  # 'draft' or 'cloud'
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Draft Available - {self.project_name}")
        self.setMinimumWidth(650)
        self.setMaximumWidth(800)
        self.setMinimumHeight(500)
        self.setMaximumHeight(700)
        self.resize(700, 550)
        
        # Set light background for better readability on macOS
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #333333;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 8px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
                background-color: #ffffff;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Warning icon
        icon_label = QLabel("📝")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Local Draft Available")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2e7d32;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Main message
        message = QLabel(
            f"You have a local draft for '<b>{self.project_name}</b>' with unsaved changes.\n"
            f"Choose how you want to proceed:"
        )
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                font-size: 14px; 
                color: #495057;
                margin: 10px 0;
                line-height: 1.4;
            }
        """)
        layout.addWidget(message)
        
        # Version comparison section
        version_section = self.create_version_comparison()
        layout.addWidget(version_section)
        
        # Changes details section (collapsible)
        changes_section = self.create_changes_section()
        layout.addWidget(changes_section)
        
        # Options section
        options_section = self.create_options_section()
        layout.addWidget(options_section)
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Buttons outside scroll area (always visible)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(15, 10, 15, 10)
        button_layout.addStretch()
        
        self.draft_button = QPushButton("Continue with Draft")
        self.draft_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-width: 140px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.draft_button.clicked.connect(self.select_draft)
        
        self.cloud_button = QPushButton("Download Fresh")
        self.cloud_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-width: 140px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
        """)
        self.cloud_button.clicked.connect(self.select_cloud)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #6c757d;
                border: 2px solid #dee2e6;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                min-width: 80px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
                color: #495057;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.cloud_button)
        button_layout.addWidget(self.draft_button)
        main_layout.addLayout(button_layout)
    
    def create_version_comparison(self):
        """Create version comparison section"""
        group = QGroupBox("Version Information")
        layout = QVBoxLayout(group)
        
        # Draft version info
        draft_created = self.draft_info.get('draft_created_at', 'Unknown')
        original_version = self.draft_info.get('original_download_time', 'Unknown')
        
        try:
            if draft_created != 'Unknown':
                draft_dt = datetime.fromisoformat(draft_created)
                draft_formatted = draft_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                draft_formatted = 'Unknown'
                
            if original_version != 'Unknown':
                orig_dt = datetime.fromisoformat(original_version.replace('Z', '+00:00'))
                orig_formatted = orig_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                orig_formatted = 'Unknown'
        except:
            draft_formatted = draft_created
            orig_formatted = original_version
        
        # Current cloud version
        current_cloud = self.cloud_info.get('modified_time', 'Unknown')
        try:
            if current_cloud != 'Unknown':
                cloud_dt = datetime.fromisoformat(current_cloud.replace('Z', '+00:00'))
                cloud_formatted = cloud_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                cloud_formatted = 'Unknown'
        except:
            cloud_formatted = current_cloud
        
        # Check if cloud version changed
        version_changed = (original_version != 'Unknown' and 
                          current_cloud != 'Unknown' and 
                          original_version != current_cloud)
        
        # Simple text-based information without HTML complications
        info_text = f"""
📝 YOUR LOCAL DRAFT:
• Created: {draft_formatted}
• Based on cloud version: {orig_formatted}
• Has unsaved changes: Yes

☁️ CURRENT CLOUD VERSION:
• Last modified: {cloud_formatted}
• Status: {'⚠️ Updated since your draft started' if version_changed else '✅ Unchanged since your draft started'}
        """.strip()
        
        if version_changed:
            info_text += "\n\n⚠️ WARNING: The cloud version has been updated since you started your draft!"
        else:
            info_text += "\n\n✅ GOOD: Cloud version unchanged since you started your draft."
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #f9f9f9;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                color: #333;
                font-family: monospace;
            }
        """)
        layout.addWidget(info_label)
        
        return group
    
    def create_changes_section(self):
        """Create collapsible changes section"""
        changes_section = CollapsibleSection("▶ View Changes Details")
        
        # Get changes description
        changes_desc = self.draft_info.get('changes_description', 'No description available')
        
        # Limit the display length
        if len(changes_desc) > 200:
            short_desc = changes_desc[:200] + "..."
            full_desc = changes_desc
        else:
            short_desc = changes_desc
            full_desc = changes_desc
        
        # Summary
        summary_label = QLabel(f"<b>Changes Summary:</b> {short_desc}")
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("""
            QLabel {
                margin: 8px; 
                font-size: 12px;
                color: #495057;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        changes_section.add_widget(summary_label)
        
        # Full details in scrollable area if long
        if len(changes_desc) > 200:
            details_text = QTextEdit()
            details_text.setPlainText(full_desc)
            details_text.setMaximumHeight(120)
            details_text.setReadOnly(True)
            details_text.setStyleSheet("""
                QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    font-size: 11px;
                    color: #495057;
                    padding: 8px;
                }
            """)
            changes_section.add_widget(details_text)
        
        return changes_section
    
    def create_options_section(self):
        """Create options explanation section"""
        group = QGroupBox("Your Options")
        layout = QVBoxLayout(group)
        
        # Simple text-based options without HTML complications
        options_text = """
📝 CONTINUE WITH DRAFT (RECOMMENDED):
• Loads instantly (no download required)
• Preserves your unsaved changes
• Work offline and save locally
• Can upload to cloud later when ready

☁️ DOWNLOAD FRESH FROM CLOUD:
• Downloads the latest version (slower)
• Your draft changes will be lost
• Gets any updates made by others
• Requires internet connection
        """.strip()
        
        options_label = QLabel(options_text)
        options_label.setWordWrap(True)
        options_label.setStyleSheet("""
            QLabel {
                background-color: #f9f9f9;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                color: #333;
                font-family: monospace;
            }
        """)
        layout.addWidget(options_label)
        
        return group
    
    def select_draft(self):
        """User chose to continue with draft"""
        self.selection = 'draft'
        self.accept()
    
    def select_cloud(self):
        """User chose to download fresh from cloud"""
        self.selection = 'cloud'
        self.accept()
    
    def get_selection(self):
        """Get the user's selection"""
        return self.selection