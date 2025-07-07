"""
Version Choice Dialog

Dialog for choosing between using local cache or downloading fresh from cloud.
Shows version comparison and recommendations.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QButtonGroup, QRadioButton, QGroupBox, QScrollArea
)
from ..utils.dialog_utils import DialogUtils
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class VersionChoiceDialog(QDialog):
    """Dialog for choosing between local cache and cloud download"""
    
    def __init__(self, project_name: str, version_comparison: dict, parent=None):
        super().__init__(parent)
        
        self.project_name = project_name
        self.version_comparison = version_comparison
        self.choice = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Version Choice - {self.project_name}")
        
        # Use responsive dialog setup
        DialogUtils.setup_responsive_dialog(self, min_width=700, min_height=550)
        
        # Set white background
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #333333;
            }
            QRadioButton {
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
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
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Icon based on version status
        status = self.version_comparison.get('status', 'unknown')
        if status == 'current':
            icon = "✅"
            title_color = "#2e7d32"
        elif status == 'outdated':
            icon = "⚠️"
            title_color = "#f57c00"
        else:
            icon = "📦"
            title_color = "#1976d2"
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Choose Database Version")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {title_color}; margin-left: 10px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Main message with clearer status
        status = self.version_comparison.get('status', 'unknown')
        message_text = f"Project: <b>{self.project_name}</b><br/>"
        
        if status == 'current':
            message_text += "Status: <span style='color: #4caf50; font-weight: bold;'>✅ You have the latest version</span>"
        elif status == 'outdated':
            time_diff = self.version_comparison.get('time_diff', 0)
            if time_diff < 60:
                time_desc = f"{time_diff} minutes"
            elif time_diff < 1440:
                time_desc = f"{time_diff // 60} hours"
            else:
                time_desc = f"{time_diff // 1440} days"
            message_text += f"Status: <span style='color: #ff9800; font-weight: bold;'>⚠️ Your cache is {time_desc} behind</span>"
        elif status == 'newer':
            message_text += "Status: <span style='color: #2196f3; font-weight: bold;'>🔄 Your local version is newer (unusual)</span>"
        else:
            message_text += f"Status: {self.version_comparison.get('message', 'Unknown')}"
        
        message = QLabel(message_text)
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                font-size: 14px; 
                color: #495057;
                margin: 10px 0;
                line-height: 1.4;
            }
        """)
        main_layout.addWidget(message)
        
        # Version details
        version_group = self.create_version_details()
        main_layout.addWidget(version_group)
        
        # Options
        options_group = self.create_options()
        main_layout.addWidget(options_group)
        
        main_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.addStretch()
        
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
        """)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-width: 80px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        ok_button.clicked.connect(self.accept_choice)
        ok_button.setDefault(True)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        main_layout.addLayout(button_layout)
        
    def create_version_details(self):
        """Create version details section with scrollable content"""
        group = QGroupBox("Version Details")
        layout = QVBoxLayout(group)
        
        # Create scroll area for the content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMaximumHeight(150)  # Limit height to ensure scrolling
        scroll_area.setMinimumHeight(100)  # Minimum height for readability
        
        # Content widget inside scroll area
        content_widget = QFrame()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Local version info
        local_time = self.version_comparison.get('local_time', 'None')
        cloud_time = self.version_comparison.get('cloud_time', 'Unknown')
        file_size = self.version_comparison.get('file_size_mb', 0)
        
        try:
            if local_time and local_time != 'None':
                local_dt = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
                local_formatted = local_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                local_formatted = 'No local cache'
                
            if cloud_time != 'Unknown':
                cloud_dt = datetime.fromisoformat(cloud_time.replace('Z', '+00:00'))
                cloud_formatted = cloud_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                cloud_formatted = 'Unknown'
        except:
            local_formatted = local_time
            cloud_formatted = cloud_time
        
        # Determine database type for better display
        db_type = self.version_comparison.get('db_type', 'cache')
        if db_type in ['working', 'working_outdated']:
            local_icon = "💼"
            local_label = "WORKING DATABASE"
            local_desc = "(Preserved from previous upload)"
        else:
            local_icon = "💾"
            local_label = "LOCAL CACHE"
            local_desc = "(Downloaded copy)"
        
        details_text = f"""
{local_icon} {local_label}:
• Version: {local_formatted}
• Size: {file_size} MB
• Type: {local_desc}
• Exists: {'✅ Yes' if self.version_comparison.get('local_db_exists', False) else '❌ No'}

☁️ CLOUD VERSION:
• Version: {cloud_formatted}
• Status: {self.version_comparison.get('message', 'Unknown')}
        """.strip()
        
        details_label = QLabel(details_text)
        details_label.setWordWrap(True)
        details_label.setStyleSheet("""
            QLabel {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 12px;
                font-size: 12px;
                color: #333;
                font-family: monospace;
                line-height: 1.4;
            }
        """)
        
        content_layout.addWidget(details_label)
        scroll_area.setWidget(content_widget)
        
        # Style the scroll area
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
        """)
        
        layout.addWidget(scroll_area)
        
        return group
    
    def create_options(self):
        """Create options section"""
        group = QGroupBox("Choose Action")
        layout = QVBoxLayout(group)
        
        # Radio button group
        self.button_group = QButtonGroup()
        
        status = self.version_comparison.get('status', 'unknown')
        needs_download = self.version_comparison.get('needs_download', True)
        has_local = self.version_comparison.get('local_db_exists', False)
        
        # Option 1: Use local database (working database or cache)
        if has_local:
            db_type = self.version_comparison.get('db_type', 'cache')
            
            # Customize text based on database type
            if db_type in ['working', 'working_outdated']:
                db_icon = "💼"
                db_label = "Working Database"
            else:
                db_icon = "💾"
                db_label = "Local Cache"
            
            if status == 'current':
                self.cache_radio = QRadioButton(f"{db_icon} Use {db_label} (Recommended)")
                self.cache_radio.setStyleSheet("color: #4caf50; font-weight: bold;")
                if db_type in ['working', 'working_outdated']:
                    cache_desc = "⚡ Continue with your preserved working database - fully up-to-date"
                else:
                    cache_desc = "⚡ Instant loading - Your cached version is up-to-date"
                self.cache_radio.setChecked(True)  # Default for current versions
            elif status == 'outdated':
                self.cache_radio = QRadioButton(f"{db_icon} Use {db_label}")
                self.cache_radio.setStyleSheet("color: #ff9800; font-weight: bold;")
                if db_type == 'working_outdated':
                    cache_desc = "⚠️ Continue with your working database (outdated) - you may miss recent changes by others"
                else:
                    cache_desc = "⚠️ Instant loading - Your cached version is older than the cloud version"
            else:
                self.cache_radio = QRadioButton(f"{db_icon} Use {db_label}")
                self.cache_radio.setStyleSheet("color: #2196f3; font-weight: bold;")
                cache_desc = "⚡ Fast loading with existing local version"
            
            self.button_group.addButton(self.cache_radio, 1)
            layout.addWidget(self.cache_radio)
            
            cache_desc_label = QLabel(cache_desc)
            cache_desc_label.setWordWrap(True)  # Enable text wrapping
            cache_desc_label.setStyleSheet("""
                margin-left: 25px; 
                color: #666; 
                font-size: 12px;
                line-height: 1.3;
                padding: 2px 0;
            """)
            layout.addWidget(cache_desc_label)
            
            layout.addSpacing(10)
        
        # Option 2: Download fresh
        if needs_download and status == 'outdated':
            self.download_radio = QRadioButton("☁️ Download Fresh from Cloud (Recommended)")
            self.download_radio.setStyleSheet("color: #4caf50; font-weight: bold;")
            download_desc = "🔄 Download the latest version with all recent changes"
            if not has_local:
                self.download_radio.setChecked(True)  # Default when no local cache
        else:
            self.download_radio = QRadioButton("☁️ Download Fresh from Cloud")
            self.download_radio.setStyleSheet("color: #2196f3; font-weight: bold;")
            if status == 'current':
                download_desc = "🔄 Re-download identical version (ensures perfect synchronization)"
            else:
                download_desc = "🔄 Download latest version from cloud (slower)"
            if not has_local:
                self.download_radio.setChecked(True)  # Default when no local cache
        
        self.button_group.addButton(self.download_radio, 2)
        layout.addWidget(self.download_radio)
        
        download_desc_label = QLabel(download_desc)
        download_desc_label.setWordWrap(True)  # Enable text wrapping
        download_desc_label.setStyleSheet("""
            margin-left: 25px; 
            color: #666; 
            font-size: 12px;
            line-height: 1.3;
            padding: 2px 0;
        """)
        layout.addWidget(download_desc_label)
        
        return group
    
    def accept_choice(self):
        """Accept the selected choice"""
        selected_id = self.button_group.checkedId()
        
        if selected_id == 1:
            self.choice = "use_cache"
        elif selected_id == 2:
            self.choice = "download_fresh"
        else:
            # Default to download if nothing selected
            self.choice = "download_fresh"
        
        self.accept()
    
    def get_choice(self):
        """Get the user's choice"""
        return self.choice