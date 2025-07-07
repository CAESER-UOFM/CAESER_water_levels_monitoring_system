from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox
)
import logging

logger = logging.getLogger(__name__)

class TransducerLocationDialog(QDialog):
    def __init__(self, current_location: dict, new_location: dict, parent=None):
        super().__init__(parent)
        self.current_location = current_location
        self.new_location = new_location
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add warning message
        msg = QLabel(
            f"Transducer {self.new_location['serial_number']} is currently "
            f"installed in well {self.current_location['well_number']}.\n"
            f"Do you want to move it to well {self.new_location['well_number']}?"
        )
        layout.addWidget(msg)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons) 