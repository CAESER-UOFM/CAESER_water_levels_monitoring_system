from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QScrollArea, QWidget, QPushButton, QFrame)
from PyQt5.QtCore import Qt

class MonetUpdateDialog(QDialog):
    def __init__(self, records_added, well_updates, unmatched, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monet Data Update Results")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create summary section
        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        summary_layout = QVBoxLayout(summary_frame)
        
        # Add total records count
        total_label = QLabel(f"Total new measurements: {records_added}")
        total_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(total_label)
        
        # Add summary to main layout
        layout.addWidget(summary_frame)
        
        # Create scrollable area for updated wells
        if well_updates:
            updated_frame = QFrame()
            updated_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            updated_layout = QVBoxLayout(updated_frame)
            
            # Add header
            header = QLabel("Updated Wells")
            header.setStyleSheet("font-weight: bold;")
            updated_layout.addWidget(header)
            
            # Create scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Create content widget
            content = QWidget()
            content_layout = QVBoxLayout(content)
            
            # Add well entries
            for well, count in well_updates.items():
                if count > 0:
                    well_label = QLabel(f"- {well}: {count} new readings")
                    content_layout.addWidget(well_label)
            
            scroll.setWidget(content)
            updated_layout.addWidget(scroll)
            
            # Add to main layout
            layout.addWidget(updated_frame)
        
        # Create scrollable area for unmatched wells
        if unmatched:
            unmatched_frame = QFrame()
            unmatched_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            unmatched_layout = QVBoxLayout(unmatched_frame)
            
            # Add header
            header = QLabel("Unmatched Wells")
            header.setStyleSheet("font-weight: bold; color: red;")
            unmatched_layout.addWidget(header)
            
            # Create scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Create content widget
            content = QWidget()
            content_layout = QVBoxLayout(content)
            
            # Add unmatched wells
            for well in unmatched:
                well_label = QLabel(f"- {well}")
                content_layout.addWidget(well_label)
            
            scroll.setWidget(content)
            unmatched_layout.addWidget(scroll)
            
            # Add to main layout
            layout.addWidget(unmatched_frame)
        
        # Add OK button
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout) 