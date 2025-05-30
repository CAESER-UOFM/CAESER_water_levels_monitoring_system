"""
Test script for the Recharge Estimates tab.
This allows testing the recharge estimation functionality in isolation.
"""

import sys
import os
import sqlite3
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QAbstractItemView
)
from PyQt5.QtCore import Qt
from recharge_tab import RechargeTab

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from simple_db_manager import SimpleDatabaseManager
from gui.managers.data_manager import DataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockDataManager:
    """Mock data manager for testing."""
    
    def __init__(self):
        """Initialize with sample data."""
        self.wells = [
            {'well_id': '1', 'name': 'Test Well 1', 'aquifer': 'Memphis', 'depth': 150, 'well_type': 'Monitoring'},
            {'well_id': '2', 'name': 'Test Well 2', 'aquifer': 'Memphis', 'depth': 200, 'well_type': 'Monitoring'},
            {'well_id': '3', 'name': 'Test Well 3', 'aquifer': 'Sparta', 'depth': 300, 'well_type': 'Monitoring'},
            {'well_id': '4', 'name': 'Test Well 4', 'aquifer': 'Alluvial', 'depth': 50, 'well_type': 'Monitoring'},
        ]
    
    def get_wells(self):
        """Return mock wells data."""
        return self.wells

class TestWindow(QMainWindow):
    """Test window for the recharge tab."""
    
    def __init__(self):
        """Initialize the test window."""
        super().__init__()
        self.setWindowTitle("Recharge Estimates Test")
        self.resize(1200, 800)
        
        # Try to use real data manager if possible
        try:
            db_path = r"S:\Water_Projects\CAESER\Water_Data_Series\water_levels_monitoring\CAESER_GENERAL.db"
            if os.path.exists(db_path):
                db_manager = SimpleDatabaseManager(db_path)
                self.data_manager = DataManager(db_path)
                logger.info(f"Using real database at: {db_path}")
            else:
                logger.warning(f"Database not found at: {db_path}")
                logger.info("Using mock data manager")
                self.data_manager = MockDataManager()
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            logger.info("Using mock data manager")
            self.data_manager = MockDataManager()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create a layout that simulates the main window layout
        test_layout = QHBoxLayout()
        
        # Create a well selection area (to simulate the main window's well selection)
        wells_widget = QWidget()
        wells_layout = QVBoxLayout(wells_widget)
        wells_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add a well table
        self.well_table = QTableWidget()
        self.well_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.well_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.well_table.setColumnCount(3)
        self.well_table.setHorizontalHeaderLabels(["Well ID", "Name", "Aquifer"])
        self.well_table.selectionModel().selectionChanged.connect(self.on_well_selection_changed)
        
        wells_layout.addWidget(self.well_table)
        test_layout.addWidget(wells_widget)
        
        # Create recharge tab
        self.recharge_tab = RechargeTab(self.data_manager)
        test_layout.addWidget(self.recharge_tab)
        
        # Set layout weights
        test_layout.setStretch(0, 1)  # Well selection takes 1/3
        test_layout.setStretch(1, 2)  # Recharge tab takes 2/3
        
        main_layout.addLayout(test_layout)
        
        # Add buttons at the bottom
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All Wells")
        select_all_btn.clicked.connect(self.select_all_wells)
        button_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(clear_btn)
        
        main_layout.addLayout(button_layout)
        
        # Load test data
        self.load_wells()
    
    def load_wells(self):
        """Load wells into the table for testing."""
        wells = self.data_manager.get_wells()
        
        self.well_table.setRowCount(len(wells))
        for row, well in enumerate(wells):
            # Well ID
            self.well_table.setItem(row, 0, QTableWidgetItem(str(well.get('well_id', ''))))
            # Name
            self.well_table.setItem(row, 1, QTableWidgetItem(str(well.get('name', ''))))
            # Aquifer
            self.well_table.setItem(row, 2, QTableWidgetItem(str(well.get('aquifer', ''))))
        
        self.well_table.resizeColumnsToContents()
    
    def on_well_selection_changed(self):
        """Handle well selection changes."""
        selected_rows = self.well_table.selectionModel().selectedRows()
        
        # Format selected wells as (well_id, well_name) tuples
        selected_wells = []
        for row_idx in selected_rows:
            row = row_idx.row()
            well_id = self.well_table.item(row, 0).text()
            well_name = self.well_table.item(row, 1).text()
            selected_wells.append((well_id, well_name))
        
        # Update the recharge tab with selected wells
        self.recharge_tab.update_well_selection(selected_wells)
    
    def select_all_wells(self):
        """Select all wells in the table."""
        self.well_table.selectAll()
    
    def clear_selection(self):
        """Clear well selection."""
        self.well_table.clearSelection()

def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 