import logging
import uuid
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QSlider, QCheckBox, QButtonGroup, QRadioButton
)
from ..utils.button_styles import ButtonStyles
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console only
    ]
)

logger = logging.getLogger(__name__)

class EditToolHelperDialog(QDialog):
    """Base class for edit tool helper dialogs"""
    
    # Signal to notify main dialog of parameter changes
    parametersChanged = pyqtSignal(dict)
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        # Remove WindowStaysOnTopHint to allow other dialogs to appear in front
        self.setWindowFlags(Qt.Window)
        
        # Add blue background styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f6fafd;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        # Instance tracking
        self.instance_id = str(uuid.uuid4())
        self.parent_dialog = parent
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Preview controls group
        self.preview_group = QGroupBox("Preview Controls")
        preview_layout = QVBoxLayout()
        
        self.preview_checkbox = QCheckBox("Show Preview")
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.stateChanged.connect(self._on_preview_change)
        
        preview_layout.addWidget(self.preview_checkbox)
        self.preview_group.setLayout(preview_layout)
        
        # Buttons with styling
        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setStyleSheet(ButtonStyles.get_save_button_style())
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet(ButtonStyles.get_warning_button_style())
        
        # Add debugging to see which button is clicked
        self.apply_btn.clicked.connect(lambda: logger.info(f"Apply button clicked in {self.__class__.__name__}"))
        self.reset_btn.clicked.connect(lambda: logger.info(f"Reset button clicked in {self.__class__.__name__}"))
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.reset_btn)
        
        # Add to main layout
        self.layout.addWidget(self.preview_group)
        self.layout.addLayout(button_layout)
    
    def _on_preview_change(self, state):
        """Internal handler for preview checkbox changes"""
        self.on_parameter_change()
        
    def on_parameter_change(self):
        """Called when any parameter changes to emit the parametersChanged signal"""
        params = self.get_current_parameters()
        self.parametersChanged.emit(params)
        
    def get_current_parameters(self):
        """Override in subclass to return current parameter values"""
        return {"preview": self.preview_checkbox.isChecked()}

class SpikeFixHelperDialog(EditToolHelperDialog):
    def __init__(self, parent=None):
        super().__init__("Fix Spikes Helper", parent)
        
        # Remove the preview controls since we're not doing live preview
        self.preview_group.hide()
        
        # Add spike-specific controls
        params_group = QGroupBox("Linear Interpolation Parameters")
        params_layout = QVBoxLayout()
        
        # Instructions label with detailed explanation
        instructions = QLabel(
            "<b>Instructions:</b><br>"
            "1. Click 'Start Selection' to begin selecting pairs.<br>"
            "2. Click on the first point in the plot (start of spike).<br>"
            "3. Click on the second point in the plot (end of spike).<br>"
            "4. The pair will be added to the list below.<br>"
            "5. Repeat to select as many pairs as needed.<br>"
            "6. Click 'Apply' to interpolate all pairs at once.<br>"
            "<br>ESC or 'Cancel Selection' will exit selection mode but keep the dialog open."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        
        # Selection mode button
        self.selection_mode_btn = QPushButton("Start Selection")
        self.selection_mode_btn.setStyleSheet("background-color: #e0f0e0;")
        self.selection_mode_btn.clicked.connect(self._toggle_selection_mode)
        
        # Remove pause button, add remove last pair button
        self.remove_last_pair_btn = QPushButton("Remove Last Pair")
        self.remove_last_pair_btn.setStyleSheet("background-color: #ffe0e0;")
        self.remove_last_pair_btn.clicked.connect(self._remove_last_pair)
        self.remove_last_pair_btn.setEnabled(False)
        
        # Status label to show selected points
        self.status_label = QLabel("No points selected")
        self.status_label.setStyleSheet("font-style: italic; color: #666;")
        
        # List of selected pairs
        self.pairs_label = QLabel("")
        self.pairs_label.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc; padding: 5px;")
        self.pairs_label.setWordWrap(True)
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.selection_mode_btn)
        button_layout.addWidget(self.remove_last_pair_btn)
        
        # Add to layout
        params_layout.addWidget(instructions)
        params_layout.addLayout(button_layout)
        params_layout.addWidget(self.status_label)
        params_layout.addWidget(QLabel("<b>Selected Pairs:</b>"))
        params_layout.addWidget(self.pairs_label)
        
        params_group.setLayout(params_layout)
        
        # Add to main layout before buttons
        self.layout.insertWidget(self.layout.count() - 1, params_group)
        
        # Track selected points and pairs
        self.current_point = None  # None, or (timestamp, level)
        self.pairs = []  # List of ((t1, l1), (t2, l2))
        self.selection_mode_active = False
        
    def _toggle_selection_mode(self):
        """Toggle point selection mode on/off"""
        self.selection_mode_active = not self.selection_mode_active
        
        if self.selection_mode_active:
            self.selection_mode_btn.setText("Cancel Selection")
            self.selection_mode_btn.setStyleSheet("background-color: #f0e0e0;")
            self.status_label.setText("Click on first point (start of spike)")
            # Tell parent to start point selection mode
            if self.parent():
                self.parent().start_spike_point_selection(self)
        else:
            self.selection_mode_btn.setText("Start Selection")
            self.selection_mode_btn.setStyleSheet("background-color: #e0f0e0;")
            self.status_label.setText("Selection canceled")
            self.current_point = None
            # Tell parent to cancel point selection mode
            if self.parent():
                self.parent().cancel_spike_point_selection()
        
    def set_selected_point(self, timestamp, level):
        """Set a selected point from the main dialog. Handles first/second point logic."""
        if self.current_point is None:
            self.current_point = (timestamp, level)
            self.status_label.setText(f"First point set: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}, Level: {level:.2f} ft\nClick on second point (end of spike)")
        else:
            pair = (self.current_point, (timestamp, level))
            self.pairs.append(pair)
            self.current_point = None
            self.status_label.setText("Pair added. Click on first point for next pair, or finish selection.")
            self._update_pairs_label()
            self.remove_last_pair_btn.setEnabled(True if self.pairs else False)
        
    def _remove_last_pair(self):
        if self.pairs:
            self.pairs.pop()
            self._update_pairs_label()
            self.remove_last_pair_btn.setEnabled(True if self.pairs else False)
            self.status_label.setText("Last pair removed. Continue selecting or finish.")
        else:
            self.status_label.setText("No pairs to remove.")
        
    def _update_pairs_label(self):
        if not self.pairs:
            self.pairs_label.setText("<i>No pairs selected.</i>")
        else:
            text = ""
            for i, ((t1, l1), (t2, l2)) in enumerate(self.pairs, 1):
                text += f"Pair {i}:<br>"
                text += f"&nbsp;&nbsp;Start: {t1.strftime('%Y-%m-%d %H:%M:%S')}, Level: {l1:.2f} ft<br>"
                text += f"&nbsp;&nbsp;End: {t2.strftime('%Y-%m-%d %H:%M:%S')}, Level: {l2:.2f} ft<br>"
            self.pairs_label.setText(text)
        
    def get_current_parameters(self):
        """Return the selected pairs for linear interpolation"""
        return {
            "pairs": self.pairs,
            "interval_minutes": 15  # Fixed 15-minute sampling interval
        }
    
    def reset_selection(self):
        self.current_point = None
        self.status_label.setText("Selection reset. Click on first point.")
    
    def clear_all(self):
        self.pairs = []
        self.current_point = None
        self._update_pairs_label()
        self.remove_last_pair_btn.setEnabled(False)
        self.status_label.setText("All pairs cleared.")

class CompensationHelperDialog(EditToolHelperDialog):
    def __init__(self, parent=None):
        super().__init__("Compensation Helper", parent)
        self.setMinimumWidth(400)
        
        # Hide the preview checkbox since preview is not needed
        self.preview_group.hide()
        
        # Add two mutually exclusive check buttons (using a QButtonGroup)
        options_group_box = QGroupBox("Compensation Options")
        options_layout = QHBoxLayout()
        self.apply_to_missing = QRadioButton("Apply to Missing Ranges")
        self.apply_to_selection = QRadioButton("Apply to Selection")
        options_layout.addWidget(self.apply_to_missing)
        options_layout.addWidget(self.apply_to_selection)
        options_group_box.setLayout(options_layout)
        
        # Set a default selection and disable the "Apply to Selection" option
        self.apply_to_missing.setChecked(True)
        self.apply_to_selection.setEnabled(False)  # Disable this option for now
        
        # Insert the new options group at the top of the dialog
        self.layout.insertWidget(0, options_group_box)
        
    def get_current_parameters(self):
        # Always set preview to false since we don't want automatic preview
        params = {"preview": False}
        
        # Since apply_to_selection is disabled, mode will always be "missing"
        params["mode"] = "missing"
        
        return params

class BaselineHelperDialog(EditToolHelperDialog):
    def __init__(self, parent=None):
        super().__init__("Baseline Adjustment Helper", parent)
        self.setMinimumWidth(400)
        
        # Remove preview controls as they're not needed
        self.preview_group.hide()
        
        # Add baseline-specific controls
        params_group = QGroupBox("Baseline Parameters")
        params_layout = QVBoxLayout()
        
        # Method selection group
        options_group = QGroupBox("Adjustment Method")
        options_layout = QHBoxLayout()
        
        # Create simple radio buttons
        self.manual_mode = QRadioButton("Manual Measurements")
        self.free_mode = QRadioButton("Free Leveling")
        
        # Set free leveling as default (per user request)
        self.free_mode.setChecked(True)
        
        # Add to layout
        options_layout.addWidget(self.manual_mode)
        options_layout.addWidget(self.free_mode)
        options_group.setLayout(options_layout)
        
        # Remove value adjustment control from here - will be moved to bottom
        
        # Difference calculation option
        diff_group = QGroupBox("Difference Calculation (Optional)")
        diff_layout = QVBoxLayout()
        
        # Checkbox to enable difference calculation
        self.use_difference = QCheckBox("Calculate adjustment from two elevation points")
        diff_layout.addWidget(self.use_difference)
        
        # Two input fields for elevation values
        points_layout = QHBoxLayout()
        points_layout.addWidget(QLabel("Point 1 Elevation (ft):"))
        self.point1_spin = QDoubleSpinBox()
        self.point1_spin.setRange(-1000, 10000)
        self.point1_spin.setDecimals(3)
        self.point1_spin.setSingleStep(0.1)
        self.point1_spin.setEnabled(False)
        points_layout.addWidget(self.point1_spin)
        
        points_layout.addWidget(QLabel("Point 2 Elevation (ft):"))
        self.point2_spin = QDoubleSpinBox()
        self.point2_spin.setRange(-1000, 10000)
        self.point2_spin.setDecimals(3)
        self.point2_spin.setSingleStep(0.1)
        self.point2_spin.setEnabled(False)
        points_layout.addWidget(self.point2_spin)
        
        # Calculate button with styling
        self.calc_diff_btn = QPushButton("Calculate Difference")
        self.calc_diff_btn.setStyleSheet(ButtonStyles.get_primary_button_style())
        self.calc_diff_btn.setEnabled(False)
        self.calc_diff_btn.clicked.connect(self._calculate_difference)
        
        diff_layout.addLayout(points_layout)
        diff_layout.addWidget(self.calc_diff_btn)
        diff_group.setLayout(diff_layout)
        
        # Connect difference calculation signals
        self.use_difference.toggled.connect(self._on_difference_toggled)
        
        # Add all to params layout
        params_layout.addWidget(options_group)
        params_layout.addWidget(diff_group)
        params_group.setLayout(params_layout)
        
        # Add to main layout before buttons
        self.layout.insertWidget(self.layout.count() - 1, params_group)
        
        # Value adjustment control group - moved to bottom
        value_group = QGroupBox("Adjustment Value")
        value_group_layout = QVBoxLayout()
        
        # Create horizontal layout with sign toggle button
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Adjustment Value (ft):"))
        
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1000, 1000)
        self.value_spin.setValue(0)
        self.value_spin.setDecimals(3)
        self.value_spin.setSingleStep(0.1)
        self.value_spin.setEnabled(True)  # Now enabled by default since free leveling is default
        value_layout.addWidget(self.value_spin)
        
        # Add sign toggle button with ± symbol
        self.sign_toggle_btn = QPushButton("±")
        self.sign_toggle_btn.setMaximumWidth(40)
        self.sign_toggle_btn.setToolTip("Click to change sign of the value")
        self.sign_toggle_btn.clicked.connect(self._toggle_sign)
        value_layout.addWidget(self.sign_toggle_btn)
        
        value_group_layout.addLayout(value_layout)
        value_group.setLayout(value_group_layout)
        
        # Add value group before buttons
        self.layout.insertWidget(self.layout.count() - 1, value_group)
        
        # Connect signals but don't trigger parameter changes
        self.manual_mode.toggled.connect(self._on_mode_changed)
        self.free_mode.toggled.connect(self._on_mode_changed)
        # Don't connect spinbox value changes - we only want to apply when the button is clicked
    
    def _on_mode_changed(self):
        """Handle mode changes - only enable/disable spinbox, no preview"""
        try:
            # Enable/disable value spinbox based on free mode
            self.value_spin.setEnabled(self.free_mode.isChecked())
            # Don't emit parameter changes for preview
        except Exception as e:
            logger.error(f"Error in mode change: {e}", exc_info=True)
    
    def _on_difference_toggled(self, checked):
        """Handle difference calculation checkbox toggle"""
        try:
            # Enable/disable difference calculation controls
            self.point1_spin.setEnabled(checked)
            self.point2_spin.setEnabled(checked)
            self.calc_diff_btn.setEnabled(checked)
            
            # If unchecked, clear the calculated value
            if not checked:
                # Don't reset the main value - user might want to keep it
                pass
        except Exception as e:
            logger.error(f"Error in difference toggle: {e}", exc_info=True)
    
    def _calculate_difference(self):
        """Calculate difference between two elevation points and set as adjustment value"""
        try:
            point1 = self.point1_spin.value()
            point2 = self.point2_spin.value()
            difference = point2 - point1
            
            # Set the calculated difference as the adjustment value
            self.value_spin.setValue(difference)
            
            logger.info(f"Calculated difference: {point2} - {point1} = {difference} ft")
        except Exception as e:
            logger.error(f"Error calculating difference: {e}", exc_info=True)
    
    def _toggle_sign(self):
        """Toggle the sign of the adjustment value by multiplying by -1"""
        try:
            current_value = self.value_spin.value()
            new_value = current_value * -1
            self.value_spin.setValue(new_value)
            logger.info(f"Toggled sign: {current_value} -> {new_value}")
        except Exception as e:
            logger.error(f"Error toggling sign: {e}", exc_info=True)
    
    def get_current_parameters(self):
        """Get current parameters"""
        try:
            method = "free" if self.free_mode.isChecked() else "manual"
            
            # If manual mode and parent has data, calculate adjustment automatically
            if method == "manual" and hasattr(self.parent(), 'calculate_baseline_adjustment'):
                calculated_adjustment = self.parent().calculate_baseline_adjustment()
                if calculated_adjustment is not None:
                    # Update the spinbox with calculated value
                    self.value_spin.setValue(calculated_adjustment)
                    logger.info(f"Auto-calculated baseline adjustment: {calculated_adjustment} ft")
            
            return {
                "method": method,
                "adjustment_value": self.value_spin.value()
            }
        except Exception as e:
            logger.error(f"Error getting parameters: {e}", exc_info=True)
            return {"method": "manual", "adjustment_value": 0}