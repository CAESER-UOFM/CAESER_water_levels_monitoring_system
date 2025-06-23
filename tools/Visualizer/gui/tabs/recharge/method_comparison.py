"""
Method Comparison Window for Recharge Calculations.
Provides side-by-side comparison of multiple recharge calculation methods
with synchronized settings and comparative analysis.
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QSpacerItem, QMessageBox, QComboBox, QCheckBox, QWidget,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QPalette
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MethodComparisonWindow(QMainWindow):
    """
    Window for comparing multiple recharge calculation methods side-by-side.
    """
    
    def __init__(self, methods, data_manager, options, parent=None):
        super().__init__(parent)
        self.methods = methods  # List of method names to compare
        self.data_manager = data_manager
        self.options = options
        self.parent_widget = parent
        
        # Method instances and results
        self.method_instances = {}
        self.method_results = {}
        
        # UI components
        self.method_widgets = {}
        self.comparison_plots = {}
        
        self.setWindowTitle(f"Method Comparison: {', '.join(methods)} - {options.get('well_name', 'Unknown Well')}")
        self.resize(1400, 900)
        
        self.setup_ui()
        self.initialize_methods()
        
    def setup_ui(self):
        """Setup the comparison window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header with comparison info
        self.create_header(layout)
        
        # Main comparison area
        self.create_comparison_area(layout)
        
        # Results summary
        self.create_results_summary(layout)
        
        # Control buttons
        self.create_control_buttons(layout)
        
    def create_header(self, layout):
        """Create header section."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title = QLabel(f"Comparing {len(self.methods)} Methods: {', '.join(self.methods)}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        # Well info
        well_info = QLabel(f"Well: {self.options.get('well_name', 'Unknown')} | Unified Settings: {'✅' if self.options.get('use_unified_settings') else '❌'}")
        well_info.setAlignment(Qt.AlignCenter)
        well_info.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(well_info)
        layout.addWidget(header_frame)
        
    def create_comparison_area(self, layout):
        """Create the main comparison area."""
        # Use a splitter for resizable comparison panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Create a panel for each method
        for method in self.methods:
            method_panel = self.create_method_panel(method)
            self.main_splitter.addWidget(method_panel)
            
        # Equal sizes for all panels
        self.main_splitter.setSizes([400] * len(self.methods))
        
        layout.addWidget(self.main_splitter)
        
    def create_method_panel(self, method_name):
        """Create a panel for a single method."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        panel.setLineWidth(1)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Method header
        header = QLabel(f"{method_name} Method")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(12)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignCenter)
        
        # Color coding for methods
        colors = {'RISE': '#2E86AB', 'MRC': '#A23B72', 'ERC': '#F18F01'}
        header.setStyleSheet(f"""
            QLabel {{
                background-color: {colors.get(method_name, '#6c757d')};
                color: white;
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 10px;
            }}
        """)
        
        # Method-specific widget area (will contain the actual method tab)
        method_widget_area = QFrame()
        method_widget_layout = QVBoxLayout(method_widget_area)
        
        # Placeholder for now - will be replaced with actual method instance
        placeholder = QLabel(f"Loading {method_name} method...")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #6c757d; font-style: italic;")
        method_widget_layout.addWidget(placeholder)
        
        # Quick stats area
        stats_area = self.create_method_stats_area(method_name)
        
        layout.addWidget(header)
        layout.addWidget(method_widget_area, 1)  # Give most space to the method widget
        layout.addWidget(stats_area)
        
        # Store references
        self.method_widgets[method_name] = {
            'panel': panel,
            'widget_area': method_widget_area,
            'layout': method_widget_layout,
            'placeholder': placeholder,
            'stats': stats_area
        }
        
        return panel
        
    def create_method_stats_area(self, method_name):
        """Create quick stats area for a method."""
        stats_group = QGroupBox("Quick Results")
        stats_layout = QVBoxLayout(stats_group)
        
        # Create labels for key metrics
        stats_labels = {
            'events': QLabel("Events: --"),
            'total_recharge': QLabel("Total: -- inches"),
            'annual_rate': QLabel("Annual: -- in/year"),
            'status': QLabel("Status: Not calculated")
        }
        
        for label in stats_labels.values():
            label.setStyleSheet("font-size: 10px; margin: 2px;")
            stats_layout.addWidget(label)
            
        # Store reference to update later
        self.method_widgets[method_name]['stats_labels'] = stats_labels
        
        return stats_group
        
    def create_results_summary(self, layout):
        """Create results summary section."""
        summary_group = QGroupBox("Comparison Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        # Summary table
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(len(self.methods) + 1)  # +1 for metric names
        
        headers = ['Metric'] + self.methods
        self.summary_table.setHorizontalHeaderLabels(headers)
        
        # Set up metrics to compare
        metrics = [
            'Total Events',
            'Total Recharge (inches)',
            'Annual Rate (in/year)',
            'Average Event Size (inches)',
            'Max Event Size (inches)',
            'Calculation Time (sec)',
            'Data Quality Score'
        ]
        
        self.summary_table.setRowCount(len(metrics))
        
        # Add metric names
        for i, metric in enumerate(metrics):
            self.summary_table.setItem(i, 0, QTableWidgetItem(metric))
            
        # Style the table
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setMaximumHeight(200)
        
        summary_layout.addWidget(self.summary_table)
        
        # Recommendation area
        self.recommendation_label = QLabel("Run calculations to see method comparison and recommendations.")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("""
            QLabel {
                background-color: #e7f3ff;
                border: 1px solid #bee5eb;
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        summary_layout.addWidget(self.recommendation_label)
        
        layout.addWidget(summary_group)
        
    def create_control_buttons(self, layout):
        """Create control buttons."""
        button_layout = QHBoxLayout()
        
        # Run all calculations
        self.run_all_button = QPushButton("🚀 Run All Calculations")
        self.run_all_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.run_all_button.clicked.connect(self.run_all_calculations)
        
        # Export comparison
        self.export_button = QPushButton("📊 Export Comparison")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_comparison)
        
        # Sync settings
        self.sync_button = QPushButton("⚙️ Sync Settings")
        self.sync_button.clicked.connect(self.sync_all_settings)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.run_all_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.sync_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
    def initialize_methods(self):
        """Initialize method instances."""
        try:
            # Import method classes
            from .rise_tab import RiseTab
            from .mrc_tab import MrcTab
            from .erc_tab import ErcTab
            
            method_classes = {
                'RISE': RiseTab,
                'MRC': MrcTab,
                'ERC': ErcTab
            }
            
            # Create instances for each method
            for method_name in self.methods:
                if method_name in method_classes:
                    method_class = method_classes[method_name]
                    
                    # Create method instance
                    method_instance = method_class(self.data_manager, self)
                    
                    # Replace placeholder with actual method widget
                    widget_info = self.method_widgets[method_name]
                    widget_info['layout'].removeWidget(widget_info['placeholder'])
                    widget_info['placeholder'].deleteLater()
                    
                    # Add the method widget
                    widget_info['layout'].addWidget(method_instance)
                    
                    # Store reference
                    self.method_instances[method_name] = method_instance
                    
                    # Load well data
                    if hasattr(method_instance, 'load_well_data'):
                        method_instance.load_well_data(self.options['well_id'])
                        
                    logger.info(f"Initialized {method_name} method for comparison")
                    
        except Exception as e:
            logger.error(f"Error initializing methods: {e}")
            QMessageBox.critical(self, "Error", f"Failed to initialize methods: {str(e)}")
            
    def run_all_calculations(self):
        """Run calculations for all methods."""
        self.run_all_button.setEnabled(False)
        self.run_all_button.setText("🔄 Running Calculations...")
        
        try:
            successful_runs = 0
            
            for method_name, method_instance in self.method_instances.items():
                try:
                    # Run the calculation for this method
                    if hasattr(method_instance, 'calculate_recharge'):
                        method_instance.calculate_recharge()
                        successful_runs += 1
                        
                        # Update quick stats
                        self.update_method_stats(method_name, method_instance)
                        
                    logger.info(f"Completed calculation for {method_name}")
                    
                except Exception as e:
                    logger.error(f"Error running {method_name} calculation: {e}")
                    self.update_method_stats(method_name, None, error=str(e))
                    
            # Update comparison summary
            self.update_comparison_summary()
            
            # Enable export if we have results
            if successful_runs > 0:
                self.export_button.setEnabled(True)
                
            # Generate recommendations
            self.generate_recommendations()
            
        except Exception as e:
            logger.error(f"Error in run_all_calculations: {e}")
            QMessageBox.critical(self, "Error", f"Failed to run calculations: {str(e)}")
            
        finally:
            self.run_all_button.setEnabled(True)
            self.run_all_button.setText("🚀 Run All Calculations")
            
    def update_method_stats(self, method_name, method_instance, error=None):
        """Update quick stats for a method."""
        stats_labels = self.method_widgets[method_name]['stats_labels']
        
        if error:
            stats_labels['status'].setText(f"Status: Error - {error[:30]}...")
            stats_labels['status'].setStyleSheet("color: red; font-size: 10px;")
            return
            
        try:
            if hasattr(method_instance, 'recharge_events'):
                events = method_instance.recharge_events
                if events:
                    total_events = len(events)
                    total_recharge = sum(event.get('recharge_value', 0) for event in events)
                    avg_event = total_recharge / total_events if total_events > 0 else 0
                    
                    stats_labels['events'].setText(f"Events: {total_events}")
                    stats_labels['total_recharge'].setText(f"Total: {total_recharge:.2f} inches")
                    stats_labels['annual_rate'].setText(f"Annual: {total_recharge * 365/365:.2f} in/year")  # Simplified
                    stats_labels['status'].setText("Status: ✅ Complete")
                    stats_labels['status'].setStyleSheet("color: green; font-size: 10px;")
                    
                    # Store results for comparison
                    self.method_results[method_name] = {
                        'events': total_events,
                        'total_recharge': total_recharge,
                        'annual_rate': total_recharge * 365/365,
                        'avg_event': avg_event,
                        'max_event': max(event.get('recharge_value', 0) for event in events) if events else 0
                    }
                else:
                    stats_labels['status'].setText("Status: No events found")
                    stats_labels['status'].setStyleSheet("color: orange; font-size: 10px;")
                    
        except Exception as e:
            logger.error(f"Error updating stats for {method_name}: {e}")
            stats_labels['status'].setText("Status: ⚠️ Error")
            stats_labels['status'].setStyleSheet("color: red; font-size: 10px;")
            
    def update_comparison_summary(self):
        """Update the comparison summary table."""
        try:
            metrics = [
                'Total Events',
                'Total Recharge (inches)',
                'Annual Rate (in/year)',
                'Average Event Size (inches)',
                'Max Event Size (inches)',
                'Calculation Time (sec)',
                'Data Quality Score'
            ]
            
            for i, metric in enumerate(metrics):
                for j, method_name in enumerate(self.methods):
                    col = j + 1  # +1 because first column is metric names
                    
                    if method_name in self.method_results:
                        results = self.method_results[method_name]
                        
                        if metric == 'Total Events':
                            value = str(results.get('events', 'N/A'))
                        elif metric == 'Total Recharge (inches)':
                            value = f"{results.get('total_recharge', 0):.2f}"
                        elif metric == 'Annual Rate (in/year)':
                            value = f"{results.get('annual_rate', 0):.2f}"
                        elif metric == 'Average Event Size (inches)':
                            value = f"{results.get('avg_event', 0):.3f}"
                        elif metric == 'Max Event Size (inches)':
                            value = f"{results.get('max_event', 0):.3f}"
                        else:
                            value = "N/A"  # Placeholder for future metrics
                    else:
                        value = "No data"
                        
                    item = QTableWidgetItem(value)
                    self.summary_table.setItem(i, col, item)
                    
        except Exception as e:
            logger.error(f"Error updating comparison summary: {e}")
            
    def generate_recommendations(self):
        """Generate method recommendations based on results."""
        try:
            if not self.method_results:
                self.recommendation_label.setText("No results available for comparison.")
                return
                
            # Simple recommendation logic
            recommendations = []
            
            # Find method with most events
            max_events = max(r.get('events', 0) for r in self.method_results.values())
            methods_with_max_events = [m for m, r in self.method_results.items() if r.get('events', 0) == max_events]
            
            if len(methods_with_max_events) == 1:
                recommendations.append(f"📊 {methods_with_max_events[0]} identified the most recharge events ({max_events})")
            
            # Find method with highest total recharge
            max_recharge = max(r.get('total_recharge', 0) for r in self.method_results.values())
            methods_with_max_recharge = [m for m, r in self.method_results.items() if r.get('total_recharge', 0) == max_recharge]
            
            if len(methods_with_max_recharge) == 1:
                recommendations.append(f"💧 {methods_with_max_recharge[0]} calculated the highest total recharge ({max_recharge:.2f}\")")
                
            # Check for consistency
            recharge_values = [r.get('total_recharge', 0) for r in self.method_results.values()]
            cv = np.std(recharge_values) / np.mean(recharge_values) if np.mean(recharge_values) > 0 else 0
            
            if cv < 0.2:
                recommendations.append("✅ Methods show good agreement (low variability)")
            elif cv > 0.5:
                recommendations.append("⚠️ Methods show significant disagreement - consider data quality")
                
            # General recommendations
            if 'RISE' in self.method_results and 'MRC' in self.method_results:
                recommendations.append("💡 For publication, consider using MRC results with RISE validation")
                
            recommendation_text = "Method Comparison Recommendations:\n• " + "\n• ".join(recommendations)
            self.recommendation_label.setText(recommendation_text)
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            self.recommendation_label.setText("Error generating recommendations.")
            
    def sync_all_settings(self):
        """Sync settings across all methods."""
        try:
            if self.options.get('use_unified_settings') and hasattr(self.parent_widget, 'get_current_settings'):
                settings = self.parent_widget.get_current_settings()
                
                for method_instance in self.method_instances.values():
                    if hasattr(method_instance, 'update_settings'):
                        method_instance.update_settings(settings)
                        
                QMessageBox.information(self, "Settings Synced", "Unified settings have been applied to all methods.")
            else:
                QMessageBox.information(self, "Manual Sync", "Please manually adjust settings in each method panel as needed.")
                
        except Exception as e:
            logger.error(f"Error syncing settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to sync settings: {str(e)}")
            
    def export_comparison(self):
        """Export comparison results."""
        try:
            # For now, just show a placeholder message
            QMessageBox.information(self, "Export", "Export functionality will be implemented in a future update.")
            
        except Exception as e:
            logger.error(f"Error exporting comparison: {e}")
            QMessageBox.warning(self, "Error", f"Failed to export: {str(e)}")