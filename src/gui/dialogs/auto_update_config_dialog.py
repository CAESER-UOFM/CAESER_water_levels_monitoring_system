# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 12:16:28 2025

@author: bledesma
"""

# src/gui/dialogs/auto_update_config_dialog.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                           QPushButton, QLabel, QSpinBox)
from PyQt5.QtCore import Qt
from pathlib import Path
import json

class AutoUpdateConfigDialog(QDialog):
    def __init__(self, baro_model, parent=None):
        super().__init__(parent)
        self.baro_model = baro_model
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Configure Automatic Updates")
        layout = QVBoxLayout(self)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_path = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(QLabel("Watch Folder:"))
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)
        
        # Update frequency
        self.update_freq = QSpinBox()
        self.update_freq.setMinimum(1)
        self.update_freq.setValue(24)
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Check Every:"))
        freq_layout.addWidget(self.update_freq)
        freq_layout.addWidget(QLabel("hours"))
        layout.addLayout(freq_layout)
        
        # Save button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)

