"""
EMR (Episodic Master Recession) method for recharge estimation.
This tab will implement the EMR method which links recharge events to specific rainfall episodes.
Based on USGS EMR methodology.
"""

import logging
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from .base_recharge_tab import BaseRechargeTab

logger = logging.getLogger(__name__)


class EmrTab(BaseRechargeTab):
    """
    EMR (Episodic Master Recession) tab for rainfall-linked recharge analysis.
    Currently under development.
    """
    
    def __init__(self, db_manager, parent=None):
        """Initialize the EMR tab."""
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add the canvas widget to layout
        main_layout.addWidget(self.canvas)
        
        # Update the plot with placeholder message
        self.update_plot()
        
    def get_method_name(self):
        """Return the method name for display."""
        return "EMR"
        
    def update_plot(self):
        """Update the plot with placeholder information."""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Set up the plot with professional styling
            ax.set_facecolor('#f8f9fa')
            self.figure.patch.set_facecolor('white')
            
            # Remove axes for cleaner look
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            
            # Add title
            ax.text(0.5, 0.85, 'EMR (Episodic Master Recession) Method', 
                   transform=ax.transAxes,
                   ha='center', va='center',
                   fontsize=20, fontweight='bold',
                   color='#2c3e50')
            
            # Add status
            ax.text(0.5, 0.75, 'Under Development', 
                   transform=ax.transAxes,
                   ha='center', va='center',
                   fontsize=16, fontweight='bold',
                   color='#e74c3c')
            
            # Add description
            description = (
                "The EMR method extends the Master Recession Curve approach by linking\n"
                "each recharge event to specific rainfall episodes. This allows calculation of:\n\n"
                "• Recharge amount per storm event\n"
                "• Lag time between rainfall and recharge response\n"
                "• Storm efficiency (recharge/rainfall ratio)\n"
                "• Seasonal patterns in recharge efficiency"
            )
            ax.text(0.5, 0.45, description, 
                   transform=ax.transAxes,
                   ha='center', va='center',
                   fontsize=12,
                   color='#495057',
                   linespacing=1.5)
            
            # Add coming soon message
            ax.text(0.5, 0.15, 
                   'This feature will be available once rainfall data\n'
                   'is integrated into the data management system.',
                   transform=ax.transAxes,
                   ha='center', va='center',
                   fontsize=11, style='italic',
                   color='#6c757d')
            
            # Add border
            rect = plt.Rectangle((0.1, 0.05), 0.8, 0.85, 
                               transform=ax.transAxes,
                               fill=False, 
                               edgecolor='#dee2e6',
                               linewidth=2,
                               linestyle='--')
            ax.add_patch(rect)
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error showing EMR placeholder: {e}")
            self._show_empty_plot("EMR analysis will be displayed here")
        
    def set_shared_data(self, raw_data, processed_data):
        """Receive shared data from parent tab."""
        # Store data for future use when rainfall integration is complete
        self.raw_data = raw_data
        self.processed_data = processed_data
        
        # Update plot with placeholder
        self.update_plot()
        
    def update_settings(self, settings):
        """Update EMR tab with unified settings."""
        # Store settings for future use
        self.settings = settings
        
    def update_well_selection(self, selected_wells):
        """Update well selection."""
        # Store selection for future use
        self.selected_wells = selected_wells