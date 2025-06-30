"""
Modern data management dialog for MRC curves and segments.
Features a cool, professional interface for managing saved data.
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, 
    QCheckBox, QMessageBox, QHeaderView, QFrame, QLineEdit,
    QComboBox, QTextEdit, QSplitter, QProgressDialog, QGroupBox,
    QGridLayout, QScrollArea, QSpacerItem, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QFont, QPalette, QLinearGradient, QBrush, QColor, QPixmap, QPainter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class ManageDataDialog(QDialog):
    """Modern, cool data management dialog for MRC curves and segments."""
    
    def __init__(self, well_id, mrc_db, parent=None):
        super().__init__(parent)
        self.well_id = well_id
        self.mrc_db = mrc_db
        self.selected_curve_ids = set()
        
        self.setup_modern_ui()
        self.load_data()
        
        # Apply cool styling
        self.apply_modern_style()
        
    def setup_modern_ui(self):
        """Setup the modern, tabbed interface."""
        self.setWindowTitle("🗂️ Data Manager - Curves & Segments")
        self.setModal(True)
        self.resize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header section
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Tab 1: Curve Management
        self.curves_tab = self.create_curves_tab()
        self.tab_widget.addTab(self.curves_tab, "📈 Curves")
        
        # Tab 2: Statistics & Visualization
        self.stats_tab = self.create_stats_tab()
        self.tab_widget.addTab(self.stats_tab, "📊 Statistics")
        
        main_layout.addWidget(self.tab_widget)
        
        # Footer with action buttons
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
    def create_header(self):
        """Create the modern header section."""
        header = QFrame()
        header.setFixedHeight(80)
        header.setObjectName("header")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Title and info
        title_layout = QVBoxLayout()
        
        title = QLabel("Data Manager")
        title.setObjectName("title")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title_layout.addWidget(title)
        
        subtitle = QLabel(f"Managing data for well: {self.well_id}")
        subtitle.setObjectName("subtitle")
        subtitle.setFont(QFont("Arial", 10))
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Search box
        search_layout = QVBoxLayout()
        search_label = QLabel("Search:")
        search_label.setFont(QFont("Arial", 9))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter curves...")
        self.search_box.textChanged.connect(self.filter_curves)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        
        layout.addLayout(search_layout)
        
        return header
        
    def create_curves_tab(self):
        """Create the curves management tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Left panel - Curve list
        left_panel = QFrame()
        left_panel.setFixedWidth(400)
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_curves)
        toolbar.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Clear Selection")
        self.select_none_btn.clicked.connect(self.clear_selection)
        toolbar.addWidget(self.select_none_btn)
        
        toolbar.addStretch()
        
        # Filter combo
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Curves", "Exponential", "Power", "Linear", "High Quality (R² > 0.9)"])
        self.filter_combo.currentTextChanged.connect(self.filter_curves)
        toolbar.addWidget(self.filter_combo)
        
        left_layout.addLayout(toolbar)
        
        # Curves table
        self.curves_table = QTableWidget()
        self.curves_table.setColumnCount(6)
        self.curves_table.setHorizontalHeaderLabels([
            "✓", "Date", "Type", "R²", "Segments", "Description"
        ])
        
        # Make table look modern
        self.curves_table.setAlternatingRowColors(True)
        self.curves_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.curves_table.horizontalHeader().setStretchLastSection(True)
        self.curves_table.setObjectName("dataTable")
        
        left_layout.addWidget(self.curves_table)
        
        # Action buttons
        action_layout = QGridLayout()
        
        self.clone_btn = QPushButton("🔄 Clone Selected")
        self.clone_btn.clicked.connect(self.clone_selected_curves)
        self.clone_btn.setObjectName("actionButton")
        action_layout.addWidget(self.clone_btn, 0, 0)
        
        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected_curves)
        self.delete_btn.setObjectName("dangerButton")
        action_layout.addWidget(self.delete_btn, 0, 1)
        
        self.export_btn = QPushButton("💾 Export Data")
        self.export_btn.clicked.connect(self.export_curves)
        self.export_btn.setObjectName("actionButton")
        action_layout.addWidget(self.export_btn, 1, 0)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.refresh_btn.setObjectName("actionButton")
        action_layout.addWidget(self.refresh_btn, 1, 1)
        
        left_layout.addLayout(action_layout)
        
        layout.addWidget(left_panel)
        
        # Right panel - Preview and details
        right_panel = self.create_preview_panel()
        layout.addWidget(right_panel)
        
        return tab
        
    def create_preview_panel(self):
        """Create the preview panel for selected curves."""
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        
        # Preview header
        preview_header = QLabel("Curve Preview")
        preview_header.setFont(QFont("Arial", 12, QFont.Bold))
        preview_header.setAlignment(Qt.AlignCenter)
        layout.addWidget(preview_header)
        
        # Curve details
        details_group = QGroupBox("Curve Details")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(details_group)
        
        # Mini plot for curve visualization
        plot_group = QGroupBox("Curve Visualization")
        plot_layout = QVBoxLayout(plot_group)
        
        self.preview_figure = Figure(figsize=(6, 4))
        self.preview_canvas = FigureCanvas(self.preview_figure)
        plot_layout.addWidget(self.preview_canvas)
        
        layout.addWidget(plot_group)
        
        # Connect table selection to preview update
        self.curves_table.itemSelectionChanged.connect(self.update_preview)
        
        return panel
        
    def create_stats_tab(self):
        """Create the statistics and visualization tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Statistics cards
        stats_layout = QHBoxLayout()
        
        # Summary cards
        cards = [
            ("Total Curves", "curves_count", "📈"),
            ("Avg R²", "avg_r_squared", "📊"),
            ("Best Fit", "best_r_squared", "🏆"),
            ("Total Segments", "total_segments", "📋")
        ]
        
        self.stat_cards = {}
        for title, key, icon in cards:
            card = self.create_stat_card(title, "—", icon)
            self.stat_cards[key] = card
            stats_layout.addWidget(card)
        
        layout.addLayout(stats_layout)
        
        # Comparison chart
        chart_group = QGroupBox("Curve Quality Comparison")
        chart_layout = QVBoxLayout(chart_group)
        
        self.stats_figure = Figure(figsize=(10, 6))
        self.stats_canvas = FigureCanvas(self.stats_figure)
        chart_layout.addWidget(self.stats_canvas)
        
        layout.addWidget(chart_group)
        
        return tab
        
    def create_stat_card(self, title, value, icon):
        """Create a modern statistics card."""
        card = QFrame()
        card.setObjectName("statCard")
        card.setFixedSize(180, 100)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Header with icon
        header_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 20))
        header_layout.addWidget(icon_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setObjectName("statValue")
        layout.addWidget(value_label)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("statTitle")
        layout.addWidget(title_label)
        
        # Store value label for updates
        card.value_label = value_label
        
        return card
        
    def create_footer(self):
        """Create the footer with action buttons."""
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setObjectName("footer")
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Dialog buttons
        self.ok_btn = QPushButton("✓ Done")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setObjectName("primaryButton")
        layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("✗ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setObjectName("secondaryButton")
        layout.addWidget(self.cancel_btn)
        
        return footer
        
    def apply_modern_style(self):
        """Apply modern, cool styling to the dialog."""
        style = """
        QDialog {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #f8f9fa, stop: 1 #e9ecef);
        }
        
        #header {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #4a90e2, stop: 1 #357abd);
            border: none;
            border-radius: 0px;
        }
        
        #header #title {
            color: white;
            font-weight: bold;
        }
        
        #header #subtitle {
            color: #e6f3ff;
        }
        
        #panel {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin: 2px;
        }
        
        #dataTable {
            gridline-color: #e9ecef;
            background-color: white;
            alternate-background-color: #f8f9fa;
            selection-background-color: #4a90e2;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        
        #dataTable::item {
            padding: 8px;
        }
        
        #dataTable::item:selected {
            background-color: #4a90e2;
            color: white;
        }
        
        #statCard {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin: 5px;
        }
        
        #statCard:hover {
            border-color: #4a90e2;
            box-shadow: 0 4px 8px rgba(74, 144, 226, 0.1);
        }
        
        #statValue {
            color: #4a90e2;
            font-weight: bold;
        }
        
        #statTitle {
            color: #6c757d;
        }
        
        #footer {
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
        }
        
        #statusLabel {
            color: #6c757d;
            font-style: italic;
        }
        
        #primaryButton {
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        #primaryButton:hover {
            background: #218838;
        }
        
        #secondaryButton {
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 4px;
        }
        
        #secondaryButton:hover {
            background: #5a6268;
        }
        
        #actionButton {
            background: #007bff;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 500;
        }
        
        #actionButton:hover {
            background: #0056b3;
        }
        
        #dangerButton {
            background: #dc3545;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 500;
        }
        
        #dangerButton:hover {
            background: #c82333;
        }
        
        QTabWidget::pane {
            border: 1px solid #dee2e6;
            background: white;
            border-radius: 4px;
        }
        
        QTabBar::tab {
            background: #e9ecef;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background: white;
            color: #4a90e2;
            font-weight: bold;
        }
        
        QTabBar::tab:hover {
            background: #f8f9fa;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #495057;
        }
        
        QLineEdit {
            padding: 6px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            background: white;
        }
        
        QLineEdit:focus {
            border-color: #4a90e2;
            outline: none;
        }
        
        QComboBox {
            padding: 4px 8px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            background: white;
        }
        
        QTextEdit {
            border: 1px solid #ced4da;
            border-radius: 4px;
            background: white;
            padding: 4px;
        }
        """
        
        self.setStyleSheet(style)
        
    def load_data(self):
        """Load curves data from database."""
        try:
            if not self.mrc_db:
                return
                
            curves = self.mrc_db.get_curves_for_well(self.well_id)
            self.populate_curves_table(curves)
            self.update_statistics(curves)
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.status_label.setText(f"Error loading data: {str(e)}")
            
    def populate_curves_table(self, curves):
        """Populate the curves table with data."""
        self.curves_table.setRowCount(len(curves))
        
        for row, curve in enumerate(curves):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.on_selection_changed)
            self.curves_table.setCellWidget(row, 0, checkbox)
            
            # Date
            date_str = curve['creation_date'][:10] if curve['creation_date'] else "Unknown"
            self.curves_table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # Type
            curve_type = curve['curve_type'].title()
            self.curves_table.setItem(row, 2, QTableWidgetItem(curve_type))
            
            # R²
            r_squared = curve.get('r_squared', 0)
            r_squared_item = QTableWidgetItem(f"{r_squared:.3f}")
            
            # Color code based on R² value
            if r_squared >= 0.9:
                r_squared_item.setBackground(QBrush(QColor("#d4edda")))  # Green
            elif r_squared >= 0.7:
                r_squared_item.setBackground(QBrush(QColor("#fff3cd")))  # Yellow
            else:
                r_squared_item.setBackground(QBrush(QColor("#f8d7da")))  # Red
                
            self.curves_table.setItem(row, 3, r_squared_item)
            
            # Segments
            segments = curve.get('recession_segments', 0)
            self.curves_table.setItem(row, 4, QTableWidgetItem(str(segments)))
            
            # Description
            description = curve.get('description', 'No description')
            self.curves_table.setItem(row, 5, QTableWidgetItem(description))
            
            # Store curve ID as user data
            self.curves_table.item(row, 1).setData(Qt.UserRole, curve['id'])
            
        # Auto-resize columns
        self.curves_table.resizeColumnsToContents()
        
    def update_statistics(self, curves):
        """Update the statistics cards and charts."""
        if not curves:
            return
            
        # Calculate statistics
        total_curves = len(curves)
        r_squared_values = [c.get('r_squared', 0) for c in curves]
        avg_r_squared = np.mean(r_squared_values) if r_squared_values else 0
        best_r_squared = max(r_squared_values) if r_squared_values else 0
        total_segments = sum(c.get('recession_segments', 0) for c in curves)
        
        # Update cards
        self.stat_cards['curves_count'].value_label.setText(str(total_curves))
        self.stat_cards['avg_r_squared'].value_label.setText(f"{avg_r_squared:.3f}")
        self.stat_cards['best_r_squared'].value_label.setText(f"{best_r_squared:.3f}")
        self.stat_cards['total_segments'].value_label.setText(str(total_segments))
        
        # Update comparison chart
        self.update_comparison_chart(curves)
        
    def update_comparison_chart(self, curves):
        """Update the comparison chart."""
        try:
            self.stats_figure.clear()
            
            if not curves:
                return
                
            # Create subplots
            ax1 = self.stats_figure.add_subplot(221)
            ax2 = self.stats_figure.add_subplot(222)
            ax3 = self.stats_figure.add_subplot(223)
            ax4 = self.stats_figure.add_subplot(224)
            
            # R² distribution
            r_squared_values = [c.get('r_squared', 0) for c in curves]
            ax1.hist(r_squared_values, bins=10, alpha=0.7, color='#4a90e2')
            ax1.set_title('R² Distribution')
            ax1.set_xlabel('R² Value')
            ax1.set_ylabel('Frequency')
            
            # Curve types
            curve_types = [c['curve_type'] for c in curves]
            type_counts = {}
            for ct in curve_types:
                type_counts[ct] = type_counts.get(ct, 0) + 1
            
            ax2.pie(type_counts.values(), labels=type_counts.keys(), autopct='%1.1f%%')
            ax2.set_title('Curve Types')
            
            # R² by curve type
            type_r_squared = {}
            for curve in curves:
                ct = curve['curve_type']
                if ct not in type_r_squared:
                    type_r_squared[ct] = []
                type_r_squared[ct].append(curve.get('r_squared', 0))
            
            for i, (ct, values) in enumerate(type_r_squared.items()):
                ax3.boxplot(values, positions=[i], labels=[ct])
            ax3.set_title('R² by Curve Type')
            ax3.set_ylabel('R² Value')
            
            # Timeline
            dates = []
            r_values = []
            for curve in curves:
                if curve['creation_date']:
                    try:
                        date = datetime.fromisoformat(curve['creation_date'][:19])
                        dates.append(date)
                        r_values.append(curve.get('r_squared', 0))
                    except:
                        continue
            
            if dates:
                ax4.scatter(dates, r_values, alpha=0.7, color='#28a745')
                ax4.set_title('R² Over Time')
                ax4.set_xlabel('Date')
                ax4.set_ylabel('R² Value')
                ax4.tick_params(axis='x', rotation=45)
            
            self.stats_figure.tight_layout()
            self.stats_canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating comparison chart: {e}")
            
    def filter_curves(self):
        """Filter curves based on search and filter criteria."""
        search_text = self.search_box.text().lower()
        filter_type = self.filter_combo.currentText()
        
        for row in range(self.curves_table.rowCount()):
            show_row = True
            
            # Search filter
            if search_text:
                description = self.curves_table.item(row, 5).text().lower()
                curve_type = self.curves_table.item(row, 2).text().lower()
                if search_text not in description and search_text not in curve_type:
                    show_row = False
            
            # Type filter
            if show_row and filter_type != "All Curves":
                if filter_type == "High Quality (R² > 0.9)":
                    r_squared_text = self.curves_table.item(row, 3).text()
                    try:
                        r_squared = float(r_squared_text)
                        if r_squared <= 0.9:
                            show_row = False
                    except:
                        show_row = False
                else:
                    curve_type = self.curves_table.item(row, 2).text()
                    if filter_type.lower() not in curve_type.lower():
                        show_row = False
            
            self.curves_table.setRowHidden(row, not show_row)
            
    def update_preview(self):
        """Update the preview panel based on selected curve."""
        try:
            current_row = self.curves_table.currentRow()
            if current_row < 0:
                self.details_text.clear()
                self.preview_figure.clear()
                self.preview_canvas.draw()
                return
                
            # Get curve ID
            curve_id = self.curves_table.item(current_row, 1).data(Qt.UserRole)
            if not curve_id:
                return
                
            # Get curve details
            curve_data = self.mrc_db.get_curve_details(curve_id)
            if not curve_data:
                return
                
            # Update details text
            details = f"""
Curve ID: {curve_data['id']}
Type: {curve_data['curve_type'].title()}
Created: {curve_data['creation_date'][:19]}
R²: {curve_data['r_squared']:.4f}
Segments: {curve_data['recession_segments']}
Description: {curve_data.get('description', 'No description')}

Parameters:
{self.format_parameters(curve_data)}
            """.strip()
            
            self.details_text.setText(details)
            
            # Update mini plot
            self.update_mini_plot(curve_data)
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            
    def format_parameters(self, curve_data):
        """Format curve parameters for display."""
        try:
            params = curve_data.get('curve_coefficients', {})
            curve_type = curve_data['curve_type']
            
            if curve_type == 'exponential':
                return f"a = {params.get('a', 0):.4f}\nQ₀ = {params.get('Q0', 0):.4f}"
            elif curve_type == 'power':
                return f"a = {params.get('a', 0):.4f}\nb = {params.get('b', 0):.4f}"
            else:  # linear
                return f"slope = {params.get('slope', 0):.4f}\nintercept = {params.get('intercept', 0):.4f}"
        except:
            return "Parameters not available"
            
    def update_mini_plot(self, curve_data):
        """Update the mini plot with curve visualization."""
        try:
            self.preview_figure.clear()
            ax = self.preview_figure.add_subplot(111)
            
            # Create sample data for visualization
            t = np.linspace(0, 30, 100)
            curve_type = curve_data['curve_type']
            params = curve_data.get('curve_coefficients', {})
            
            if curve_type == 'exponential':
                a = params.get('a', 1)
                Q0 = params.get('Q0', 10)
                y = Q0 * np.exp(-a * t)
                equation = f"Q = {Q0:.2f} × e^(-{a:.3f}t)"
            elif curve_type == 'power':
                a = params.get('a', 1)
                b = params.get('b', 0.5)
                y = a * np.power(np.maximum(t, 0.001), b)
                equation = f"Q = {a:.2f} × t^{b:.3f}"
            else:  # linear
                slope = params.get('slope', -0.1)
                intercept = params.get('intercept', 2)
                y = intercept + slope * t
                equation = f"ln(Q) = {intercept:.2f} + {slope:.3f}t"
            
            ax.plot(t, y, 'b-', linewidth=2, label=equation)
            ax.set_xlabel('Time (days)')
            ax.set_ylabel('Flow/Level')
            ax.set_title(f'{curve_type.title()} Curve (R² = {curve_data["r_squared"]:.3f})')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            self.preview_figure.tight_layout()
            self.preview_canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating mini plot: {e}")
            
    def select_all_curves(self):
        """Select all visible curves."""
        for row in range(self.curves_table.rowCount()):
            if not self.curves_table.isRowHidden(row):
                checkbox = self.curves_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
                    
    def clear_selection(self):
        """Clear all curve selections."""
        for row in range(self.curves_table.rowCount()):
            checkbox = self.curves_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
                
    def on_selection_changed(self):
        """Handle selection changes."""
        self.selected_curve_ids.clear()
        selected_count = 0
        
        for row in range(self.curves_table.rowCount()):
            checkbox = self.curves_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                curve_id = self.curves_table.item(row, 1).data(Qt.UserRole)
                if curve_id:
                    self.selected_curve_ids.add(curve_id)
                    selected_count += 1
        
        # Update status
        if selected_count == 0:
            self.status_label.setText("Ready")
        elif selected_count == 1:
            self.status_label.setText("1 curve selected")
        else:
            self.status_label.setText(f"{selected_count} curves selected")
            
        # Enable/disable buttons
        has_selection = selected_count > 0
        self.clone_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
        
    def clone_selected_curves(self):
        """Clone the selected curves."""
        if not self.selected_curve_ids:
            QMessageBox.warning(self, "No Selection", "Please select curves to clone.")
            return
            
        try:
            cloned_count = 0
            
            for curve_id in self.selected_curve_ids:
                # Get curve details
                curve_data = self.mrc_db.get_curve_details(curve_id)
                if not curve_data:
                    continue
                    
                # Create clone with new description
                original_desc = curve_data.get('description', '')
                clone_desc = f"Clone of {original_desc}" if original_desc else f"Clone of curve {curve_id}"
                
                # Remove ID and update description
                clone_data = curve_data.copy()
                if 'id' in clone_data:
                    del clone_data['id']
                clone_data['description'] = clone_desc
                
                # Save clone
                new_curve_id = self.mrc_db.save_curve(
                    well_number=self.well_id,
                    well_name=clone_data.get('well_name', 'Unknown'),
                    curve_type=clone_data['curve_type'],
                    curve_parameters=clone_data.get('curve_parameters', {}),
                    curve_coefficients=clone_data.get('curve_coefficients', {}),
                    r_squared=clone_data.get('r_squared', 0),
                    recession_segments=clone_data.get('recession_segments', 0),
                    min_recession_length=clone_data.get('min_recession_length', 7),
                    description=clone_desc,
                    recession_segments_data=clone_data.get('recession_segments_data', [])
                )
                
                if new_curve_id:
                    cloned_count += 1
            
            if cloned_count > 0:
                QMessageBox.information(self, "Clone Complete", 
                    f"Successfully cloned {cloned_count} curve(s).")
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Clone Failed", "No curves were cloned.")
                
        except Exception as e:
            logger.error(f"Error cloning curves: {e}")
            QMessageBox.critical(self, "Error", f"Failed to clone curves: {str(e)}")
            
    def delete_selected_curves(self):
        """Delete the selected curves with confirmation."""
        if not self.selected_curve_ids:
            QMessageBox.warning(self, "No Selection", "Please select curves to delete.")
            return
            
        # Confirmation dialog
        reply = QMessageBox.question(self, "Confirm Deletion", 
            f"Are you sure you want to delete {len(self.selected_curve_ids)} curve(s)?\n\n"
            f"This will also delete all associated segments.\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Show progress dialog
            progress = QProgressDialog("Deleting curves...", "Cancel", 0, len(self.selected_curve_ids), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            deleted_count = 0
            
            for i, curve_id in enumerate(self.selected_curve_ids):
                if progress.wasCanceled():
                    break
                    
                progress.setValue(i)
                QApplication.processEvents()
                
                # Delete curve and segments
                if self.mrc_db.delete_curves_and_segments([curve_id]):
                    deleted_count += 1
            
            progress.setValue(len(self.selected_curve_ids))
            
            if deleted_count > 0:
                QMessageBox.information(self, "Deletion Complete", 
                    f"Successfully deleted {deleted_count} curve(s) and their segments.")
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Deletion Failed", "No curves were deleted.")
                
        except Exception as e:
            logger.error(f"Error deleting curves: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete curves: {str(e)}")
            
    def export_curves(self):
        """Export selected curves to a file."""
        if not self.selected_curve_ids:
            QMessageBox.warning(self, "No Selection", "Please select curves to export.")
            return
            
        QMessageBox.information(self, "Export", 
            "Export functionality will be implemented in a future version.")
            
    def refresh_data(self):
        """Refresh the data from database."""
        try:
            self.status_label.setText("Refreshing data...")
            self.load_data()
            self.clear_selection()
            self.status_label.setText("Data refreshed")
            
            # Brief animation
            QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
            
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            self.status_label.setText(f"Refresh failed: {str(e)}")