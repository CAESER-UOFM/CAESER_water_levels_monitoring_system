from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QDialogButtonBox, QPushButton, QFrame,
                             QScrollArea, QWidget, QTabWidget, QGroupBox, QSplitter,
                             QProgressBar, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SaveToCloudDialog(QDialog):
    """Elegant Windows-optimized dialog for saving database changes to cloud with detailed change tracking"""
    
    def __init__(self, project_name, user_name, change_tracker=None, existing_description=None, parent=None):
        """
        Initialize the enhanced save to cloud dialog.
        
        Args:
            project_name: Name of the project being saved
            user_name: Name of the current user
            change_tracker: Optional ChangeTracker instance for showing tracked changes
            existing_description: Optional existing description from draft
            parent: Parent widget
        """
        super().__init__(parent)
        self.project_name = project_name
        self.user_name = user_name
        self.change_tracker = change_tracker
        self.existing_description = existing_description
        self.changes_description = ""
        
        # Windows optimization settings
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup elegant Windows-optimized dialog UI"""
        self.setWindowTitle(f"💾 Save to SMOO - {self.project_name}")
        self.setMinimumSize(900, 700)
        self.setMaximumSize(1200, 900)
        
        # Main layout with modern styling
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header section with gradient-like styling
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E3F2FD, stop:1 #BBDEFB);
                border: 1px solid #90CAF9;
                border-radius: 10px;
                margin: 5px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(8)
        
        # Title with icon
        title_layout = QHBoxLayout()
        title_label = QLabel("☁️ Save Changes to SMOO")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet("color: #1565C0; margin: 10px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Timestamp
        timestamp_label = QLabel(f"📅 {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        timestamp_label.setFont(QFont("Segoe UI", 9))
        timestamp_label.setStyleSheet("color: #424242;")
        title_layout.addWidget(timestamp_label)
        
        header_layout.addLayout(title_layout)
        
        # Project and user info in elegant cards
        info_layout = QHBoxLayout()
        
        # Project card
        project_card = self._create_info_card("🗂️ Project", self.project_name, "#4CAF50")
        info_layout.addWidget(project_card)
        
        # User card  
        user_card = self._create_info_card("👤 User", self.user_name, "#2196F3")
        info_layout.addWidget(user_card)
        
        header_layout.addLayout(info_layout)
        main_layout.addWidget(header_frame)
        
        # Content area with splitter for resizable sections
        content_splitter = QSplitter(Qt.Vertical)
        content_splitter.setChildrenCollapsible(False)
        
        # Changes analysis section
        changes_widget = self._create_changes_section()
        content_splitter.addWidget(changes_widget)
        
        # Description section
        description_widget = self._create_description_section()
        content_splitter.addWidget(description_widget)
        
        # Set initial splitter sizes (60% changes, 40% description)
        content_splitter.setSizes([420, 280])
        main_layout.addWidget(content_splitter)
        
        # Action buttons with modern styling
        self._create_action_buttons(main_layout)
        
        # Apply global Windows-optimized styling
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
                font-family: 'Segoe UI', 'Tahoma', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #E8F5E8;
            }
            QTextEdit {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
                font-size: 11px;
                line-height: 1.4;
                background-color: white;
            }
            QTextEdit:focus {
                border-color: #2196F3;
            }
            QScrollBar:vertical {
                background-color: #F5F5F5;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #BDBDBD;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9E9E9E;
            }
        """)
        
    def _create_info_card(self, title, value, color):
        """Create an elegant info card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {color};
                border-radius: 8px;
                padding: 10px;
                margin: 2px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        title_label.setStyleSheet(f"color: {color};")
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 11))
        value_label.setStyleSheet("color: #424242;")
        value_label.setWordWrap(True)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card
        
    def _create_changes_section(self):
        """Create the changes analysis section with tabs"""
        changes_group = QGroupBox("📊 Changes Analysis")
        changes_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        changes_layout = QVBoxLayout(changes_group)
        
        if not self.change_tracker or not self.change_tracker.changes:
            no_changes_label = QLabel("ℹ️ No changes detected in this session.")
            no_changes_label.setStyleSheet("""
                color: #666;
                font-size: 12px;
                padding: 20px;
                text-align: center;
                background-color: #F9F9F9;
                border-radius: 8px;
            """)
            no_changes_label.setAlignment(Qt.AlignCenter)
            changes_layout.addWidget(no_changes_label)
            return changes_group
            
        # Create tabbed view for different change types
        changes_tabs = QTabWidget()
        
        # Summary tab
        summary_widget = self._create_summary_tab()
        changes_tabs.addTab(summary_widget, "📈 Summary")
        
        # Detailed changes tab
        details_widget = self._create_details_tab()
        changes_tabs.addTab(details_widget, "📋 Details")
        
        # Timeline tab
        timeline_widget = self._create_timeline_tab()
        changes_tabs.addTab(timeline_widget, "⏱️ Timeline")
        
        changes_layout.addWidget(changes_tabs)
        return changes_group
        
    def _create_summary_tab(self):
        """Create summary tab with statistics and highlights"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        if not self.change_tracker or not self.change_tracker.changes:
            return widget
            
        changes_summary = self.change_tracker.get_changes_summary()
        
        # Statistics cards
        stats_layout = QHBoxLayout()
        
        # Total changes
        total_card = self._create_stat_card("📊 Total Changes", str(changes_summary['total']), "#FF9800")
        stats_layout.addWidget(total_card)
        
        # Manual changes
        manual_card = self._create_stat_card("✏️ Manual", str(changes_summary['manual']), "#4CAF50")
        stats_layout.addWidget(manual_card)
        
        # Automatic changes
        auto_card = self._create_stat_card("🤖 Auto-Sync", str(changes_summary['automatic']), "#2196F3")
        stats_layout.addWidget(auto_card)
        
        layout.addLayout(stats_layout)
        
        # Key changes highlight
        highlight_label = QLabel("🔍 Key Changes:")
        highlight_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(highlight_label)
        
        highlight_text = QTextEdit()
        highlight_text.setMaximumHeight(120)
        highlight_content = self.change_tracker.get_manual_changes_description() or "No manual changes detected"
        highlight_text.setPlainText(highlight_content)
        highlight_text.setReadOnly(True)
        layout.addWidget(highlight_text)
        
        return widget
        
    def _create_stat_card(self, title, value, color):
        """Create a statistics card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-left: 4px solid {color};
                border-radius: 6px;
                padding: 12px;
                margin: 4px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setStyleSheet("color: #666;")
        title_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        
        return card
        
    def _create_details_tab(self):
        """Create detailed changes tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        if self.change_tracker and self.change_tracker.changes:
            details_content = self._format_detailed_changes()
        else:
            details_content = "No changes to display."
            
        details_text.setPlainText(details_content)
        layout.addWidget(details_text)
        
        return widget
        
    def _create_timeline_tab(self):
        """Create timeline tab showing chronological changes"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        timeline_text = QTextEdit()
        timeline_text.setReadOnly(True)
        
        if self.change_tracker and self.change_tracker.changes:
            timeline_content = self._format_timeline_changes()
        else:
            timeline_content = "No timeline data available."
            
        timeline_text.setPlainText(timeline_content)
        layout.addWidget(timeline_text)
        
        return widget
        
    def _create_description_section(self):
        """Create the description input section"""
        desc_group = QGroupBox("📝 Describe Your Changes")
        desc_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        desc_layout = QVBoxLayout(desc_group)
        
        # Instructions
        instructions = QLabel("💡 Provide a clear description of what you changed and why:")
        instructions.setFont(QFont("Segoe UI", 9))
        instructions.setStyleSheet("color: #666; margin-bottom: 8px;")
        desc_layout.addWidget(instructions)
        
        # Text area with smart placeholder
        self.change_text = QTextEdit()
        if self.existing_description:
            self.change_text.setPlainText(self.existing_description)
        else:
            self.change_text.setPlaceholderText("Example: Added new wells TNO75_001025-001027, updated flags for TN075_001011 due to equipment malfunction, imported latest sensor data from field laptops...")
        
        self.change_text.setMinimumHeight(100)
        desc_layout.addWidget(self.change_text)
        
        return desc_group
        
    def _create_action_buttons(self, main_layout):
        """Create modern action buttons"""
        button_frame = QFrame()
        button_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        button_layout = QHBoxLayout(button_frame)
        
        # Help/info button
        help_btn = QPushButton("❓ Help")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        help_btn.clicked.connect(self._show_help)
        button_layout.addWidget(help_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Save button
        save_btn = QPushButton("💾 Save to SMOO")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        main_layout.addWidget(button_frame)
        
    def _show_help(self):
        """Show help information"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Help - Save to SMOO", 
            """💡 <b>Save to SMOO Help</b><br><br>
            <b>📊 Changes Analysis:</b><br>
            • <b>Summary:</b> Overview of all changes with statistics<br>
            • <b>Details:</b> Complete list of individual changes<br>
            • <b>Timeline:</b> Chronological view of when changes occurred<br><br>
            
            <b>📝 Description Tips:</b><br>
            • Describe WHAT you changed and WHY<br>
            • Mention specific wells, sensors, or data affected<br>
            • Note any issues or corrections made<br>
            • This helps team members understand your changes<br><br>
            
            <b>✨ Features:</b><br>
            • Auto-sync changes are tracked automatically<br>
            • Manual edits are detected and summarized<br>
            • All changes are timestamped for reference<br>
            • Resizable sections for better viewing
            """)
            
    def _format_detailed_changes(self):
        """Format detailed changes for display"""
        if not self.change_tracker or not self.change_tracker.changes:
            return "No changes to display."
            
        formatted = "📋 DETAILED CHANGES REPORT\n"
        formatted += "=" * 60 + "\n\n"
        
        for i, change in enumerate(self.change_tracker.changes, 1):
            change_type = change.get('change_type', 'UNKNOWN')
            action = change.get('action', 'UNKNOWN')
            table_name = change.get('table_name', 'unknown_table')
            description = change.get('description', 'No description')
            timestamp = change.get('timestamp', 'Unknown time')
            context = change.get('context', {})
            
            # Format timestamp
            try:
                if timestamp != 'Unknown time':
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted_time = timestamp
            except:
                formatted_time = str(timestamp)
            
            # Format change type icon
            type_icon = "🤖" if change_type == "AUTOMATIC" else "✏️"
            
            formatted += f"{type_icon} CHANGE #{i}\n"
            formatted += f"   Type: {change_type}\n"
            formatted += f"   Action: {action}\n"
            formatted += f"   Table: {table_name}\n"
            formatted += f"   Description: {description}\n"
            formatted += f"   Timestamp: {formatted_time}\n"
            
            if context:
                formatted += f"   Context: {context}\n"
                
            formatted += "\n" + "-" * 40 + "\n\n"
            
        return formatted
        
    def _format_timeline_changes(self):
        """Format changes in chronological order"""
        if not self.change_tracker or not self.change_tracker.changes:
            return "No timeline data available."
            
        # Sort changes by timestamp
        sorted_changes = sorted(
            self.change_tracker.changes,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        formatted = "⏱️ CHRONOLOGICAL TIMELINE\n"
        formatted += "=" * 60 + "\n\n"
        
        current_date = None
        for change in sorted_changes:
            timestamp = change.get('timestamp', 'Unknown time')
            
            try:
                if timestamp != 'Unknown time':
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                    time_str = dt.strftime('%H:%M:%S')
                    
                    # Add date header if new date
                    if current_date != date_str:
                        if current_date is not None:
                            formatted += "\n"
                        formatted += f"📅 {dt.strftime('%B %d, %Y')}\n"
                        formatted += "─" * 30 + "\n"
                        current_date = date_str
                else:
                    time_str = timestamp
            except:
                time_str = str(timestamp)
                
            change_type = change.get('change_type', 'UNKNOWN')
            description = change.get('description', 'No description')
            
            type_icon = "🤖" if change_type == "AUTOMATIC" else "✏️"
            formatted += f"{time_str} {type_icon} {description}\n"
            
        return formatted
        
    def accept(self):
        """Override accept to validate and save description"""
        description = self.change_text.toPlainText().strip()
        
        if not description:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Description Required",
                "Please provide a description of your changes before saving to SMOO."
            )
            self.change_text.setFocus()
            return
            
        self.changes_description = description
        super().accept()
        
    def get_changes_description(self):
        """Get the entered changes description"""
        return self.changes_description