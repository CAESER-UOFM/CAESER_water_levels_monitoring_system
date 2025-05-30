"""
Recharge Estimates Tab for the Water Level Visualizer.
This tab provides tools for estimating aquifer recharge using various methods.
"""

import logging
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QMessageBox,
    QSplitter, QHBoxLayout, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal

# Import the individual recharge method tabs
from .rise_tab import RiseTab
from .mrc_tab import MrcTab
from .erc_tab import ErcTab

logger = logging.getLogger(__name__)

class RechargeTab(QWidget):
    """
    Tab for recharge estimation using water table fluctuation methods.
    Contains sub-tabs for different methods: RISE, MRC, and ERC.
    """
    
    def __init__(self, data_manager, parent=None):
        """
        Initialize the recharge tab.
        
        Args:
            data_manager: Data manager providing access to well data
            parent: Parent widget
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.selected_wells = []
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI for the recharge tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Info label at the top
        info_label = QLabel(
            "Select wells from the main 'Available Wells' table to analyze for recharge estimation. "
            "Unconfined aquifer wells are recommended for water table fluctuation methods."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Create recharge methods tabs
        recharge_methods = self.create_recharge_methods()
        layout.addWidget(recharge_methods)
    
    def create_recharge_methods(self):
        """Create the tab widget for different recharge methods."""
        group_box = QGroupBox("Recharge Estimation Methods")
        layout = QVBoxLayout(group_box)
        
        # Create tab widget
        self.methods_tab = QTabWidget()
        
        # Create tabs for each method
        self.rise_tab = RiseTab(self.data_manager)
        self.mrc_tab = MrcTab(self.data_manager)
        self.erc_tab = ErcTab(self.data_manager)
        
        # Add tabs
        self.methods_tab.addTab(self.rise_tab, "RISE Method")
        self.methods_tab.addTab(self.mrc_tab, "MRC Method")
        self.methods_tab.addTab(self.erc_tab, "ERC Method")
        
        layout.addWidget(self.methods_tab)
        
        return group_box
    
    def update_well_selection(self, selected_wells):
        """
        Update selected wells based on the main window's well table selection.
        
        Args:
            selected_wells: List of tuples (well_id, well_name) selected in the main window
        """
        self.selected_wells = selected_wells
        
        # Update all method tabs with the new selection
        self.rise_tab.update_well_selection(self.selected_wells)
        self.mrc_tab.update_well_selection(self.selected_wells)
        self.erc_tab.update_well_selection(self.selected_wells)
        
        logger.debug(f"Recharge tab updated with wells: {self.selected_wells}") 