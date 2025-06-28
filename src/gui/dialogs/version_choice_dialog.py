"""
Version Choice Dialog

Dialog for choosing between using local cache or downloading fresh from cloud.
Shows version comparison and recommendations.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QButtonGroup, QRadioButton, QGroupBox
)
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
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        self.resize(650, 500)
        
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
        
        # Main message
        message = QLabel(
            f"Project: <b>{self.project_name}</b><br/>"
            f"Status: {self.version_comparison.get('message', 'Unknown')}"
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
        """Create version details section"""
        group = QGroupBox("Version Details")
        layout = QVBoxLayout(group)
        
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
        
        details_text = f"""
💾 LOCAL CACHE:
• Version: {local_formatted}
• Size: {file_size} MB
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
        layout.addWidget(details_label)
        
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
        
        # Option 1: Use local cache (if available and reasonable)
        if has_local:
            if status == 'current':
                self.cache_radio = QRadioButton("💾 Use Local Cache (Recommended)")
                self.cache_radio.setStyleSheet("color: #4caf50; font-weight: bold;")
                cache_desc = "✅ Use cached version - it's current and fast"
                self.cache_radio.setChecked(True)  # Default for current versions
            elif status == 'outdated':
                self.cache_radio = QRadioButton("💾 Use Local Cache")
                self.cache_radio.setStyleSheet("color: #ff9800; font-weight: bold;")
                cache_desc = "⚠️ Use older cached version (you may miss recent changes)"
            else:
                self.cache_radio = QRadioButton("💾 Use Local Cache")
                self.cache_radio.setStyleSheet("color: #2196f3; font-weight: bold;")
                cache_desc = "Use existing cached version"
            
            self.button_group.addButton(self.cache_radio, 1)
            layout.addWidget(self.cache_radio)
            
            cache_desc_label = QLabel(cache_desc)
            cache_desc_label.setStyleSheet("margin-left: 25px; color: #666; font-size: 11px;")
            layout.addWidget(cache_desc_label)
            
            layout.addSpacing(10)
        
        # Option 2: Download fresh
        if needs_download and status == 'outdated':
            self.download_radio = QRadioButton("☁️ Download Fresh from Cloud (Recommended)")
            self.download_radio.setStyleSheet("color: #4caf50; font-weight: bold;")
            download_desc = "✅ Download latest version with recent changes"
            if not has_local:
                self.download_radio.setChecked(True)  # Default when no local cache
        else:
            self.download_radio = QRadioButton("☁️ Download Fresh from Cloud")
            self.download_radio.setStyleSheet("color: #2196f3; font-weight: bold;")
            if status == 'current':
                download_desc = "Re-download same version (slower but ensures consistency)"
            else:
                download_desc = "Download latest version from cloud"
            if not has_local:
                self.download_radio.setChecked(True)  # Default when no local cache
        
        self.button_group.addButton(self.download_radio, 2)
        layout.addWidget(self.download_radio)
        
        download_desc_label = QLabel(download_desc)
        download_desc_label.setStyleSheet("margin-left: 25px; color: #666; font-size: 11px;")
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