import logging
import pandas as pd
import matplotlib
from matplotlib.widgets import Cursor
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QGroupBox, QCheckBox, QDateTimeEdit,
    QLabel, QPushButton, QMessageBox, QProgressBar, QSpinBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QAbstractSpinBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
from matplotlib import cm
import matplotlib.dates as mdates
import sqlite3
import json
from PyQt5.QtWidgets import QApplication
from ..handlers.progress_dialog_handler import progress_dialog

logger = logging.getLogger(__name__)

class MasterBaroDialog(QDialog):
    # Signal emitted when master baro is created to inform parent
    master_baro_created = pyqtSignal()
    
    def __init__(self, baro_model, parent=None):
        super().__init__(parent)
        self.baro_model = baro_model
        self.baro_checkboxes = {}
        self.barologger_data = {}  # Cache for barologger data
        self.filtered_data = {}    # Cache for filtered data based on time range
        self.baro_colors = {}
        self.has_master_data = False
        self.master_data = None
                
        # Initialize plot components
        self.figure = Figure(figsize=(10, 6), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        self.check_master_data()
        self.has_overlap = False
        self.setup_ui()
        self.load_barologger_data()
        
        # Add screen adaptation after dialog is shown
        QTimer.singleShot(10, self.adjust_for_screen)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Create Master Baro")
        
        # Calculate appropriate size for the current screen
        main_screen = QApplication.primaryScreen()
        screen_size = main_screen.availableGeometry().size()
        
        # Calculate size as percentage of screen size
        width = min(int(screen_size.width() * 0.65), 1200)
        height = min(int(screen_size.height() * 0.65), 800)
        
        # Set size and minimum size
        self.resize(width, height)
        self.setMinimumSize(800, 550)
        
        # Main container
        main_container = QVBoxLayout(self)
        
        # Top section with controls (horizontally arranged)
        top_controls = QHBoxLayout()
        
        # 1. Left panel - Barologger selection
        baro_group = QGroupBox("Select Barologgers")
        baro_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.baro_layout = QVBoxLayout(baro_group)
        
        # Top control row with All and Master Baro checkboxes
        control_row = QHBoxLayout()
        
        # "All" checkbox
        self.select_all_cb = QCheckBox("All")
        self.select_all_cb.setChecked(True)
        self.select_all_cb.stateChanged.connect(self.toggle_all_barologgers)
        control_row.addWidget(self.select_all_cb)
        
        # "Master Baro" checkbox
        self.master_baro_cb = QCheckBox("Master Baro")
        self.master_baro_cb.setChecked(True)
        self.master_baro_cb.stateChanged.connect(self.update_preview)
        control_row.addWidget(self.master_baro_cb)
        
        # Add stretch to push checkboxes to the left
        control_row.addStretch()
        
        # Add control row to baro layout
        self.baro_layout.addLayout(control_row)
        
        # Separator
        self.baro_layout.addWidget(QLabel("───────────────"))
        
        # The barologger checkboxes will be added here in load_barologger_data()
        
        # 2. Middle panel - Time Range
        time_group = QGroupBox("Time Range")
        time_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        time_layout = QVBoxLayout(time_group)
        
        # Start date/time
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("Start UTC:"))
        self.start_date = QDateTimeEdit()
        self.start_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_date.setCalendarPopup(True)
        self.start_date.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.start_date.setAccelerated(True)
        start_layout.addWidget(self.start_date)
        time_layout.addLayout(start_layout)
        
        # End date/time
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("End UTC:"))
        self.end_date = QDateTimeEdit()
        self.end_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_date.setCalendarPopup(True)
        self.end_date.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.end_date.setAccelerated(True)
        end_layout.addWidget(self.end_date)
        time_layout.addLayout(end_layout)
        
        # Buttons for time range
        button_layout = QVBoxLayout()
        
        self.full_range_btn = QPushButton("Set Full Range")
        self.full_range_btn.clicked.connect(self.set_full_range)
        button_layout.addWidget(self.full_range_btn)
        
        self.zoom_to_selection_btn = QPushButton("Zoom to Selection")
        self.zoom_to_selection_btn.clicked.connect(self.zoom_to_selected_data)
        button_layout.addWidget(self.zoom_to_selection_btn)
        
        time_layout.addLayout(button_layout)
        
        # 3. Right panel - Legend
        legend_group = QGroupBox("Legend")
        legend_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        legend_layout = QVBoxLayout(legend_group)
        
        self.legend_widget = QLabel("No data loaded")
        self.legend_widget.setWordWrap(True)
        self.legend_widget.setTextFormat(Qt.RichText)
        legend_layout.addWidget(self.legend_widget)
        
        # Add the three panels to the top controls layout with appropriate weights
        top_controls.addWidget(baro_group, 5)       # Barologger selection (wider)
        top_controls.addWidget(time_group, 3)       # Time range 
        top_controls.addWidget(legend_group, 3)     # Legend
        
        # Plot section - Give it maximum vertical space
        plot_group = QGroupBox("Data Preview")
        plot_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout = QVBoxLayout(plot_group)
        
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        # Bottom section - Processing options and buttons
        bottom_layout = QVBoxLayout()
        
        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QHBoxLayout(options_group)
        
        min_readings_layout = QHBoxLayout()
        min_readings_layout.addWidget(QLabel("Minimum readings required:"))
        self.min_readings = QSpinBox()
        self.min_readings.setRange(1, 10)
        self.min_readings.setValue(1)
        min_readings_layout.addWidget(self.min_readings)
        options_layout.addLayout(min_readings_layout)
        
        self.overwrite_cb = QCheckBox("Overwrite overlapping data")
        self.overwrite_cb.setEnabled(False)
        self.overwrite_cb.setChecked(False)
        self.overwrite_cb.stateChanged.connect(self.on_overwrite_changed)
        options_layout.addWidget(self.overwrite_cb)
        options_layout.addStretch()
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        preview_btn = QPushButton("Preview Master Baro")
        preview_btn.clicked.connect(self.preview_master_baro)
        btn_layout.addWidget(preview_btn)
        
        create_btn_text = "Edit Master Baro" if self.has_master_data else "Create Master Baro"
        self.create_btn = QPushButton(create_btn_text)
        self.create_btn.clicked.connect(self.create_master_baro)
        btn_layout.addWidget(self.create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        bottom_layout.addWidget(options_group)
        bottom_layout.addLayout(btn_layout)
        
        # Add all sections to main container with appropriate vertical sizing
        main_container.addLayout(top_controls)
        main_container.addWidget(plot_group)
        main_container.addLayout(bottom_layout)
        
        # Create the span selector
        self.span_selector = SpanSelector(
            self.ax, self.on_span_select, 'horizontal',
            useblit=True, props=dict(alpha=0.2, facecolor='red'),
            interactive=True
        )
    
    def adjust_for_screen(self):
        """Adjust dialog layout for the current screen"""
        try:
            # Get current screen
            screen = self.screen()
            if not screen:
                screen = QApplication.primaryScreen()
                
            # Get screen metrics
            available_size = screen.availableGeometry().size()
            dpi_factor = screen.devicePixelRatio()
            
            # Resize the dialog appropriately for the screen
            width = min(int(available_size.width() * 0.65), 1200)
            height = min(int(available_size.height() * 0.65), 800)
            
            # Set size
            self.resize(width, height)
            
            # Update figure size if exists
            if hasattr(self, 'figure'):
                # Calculate new figure size in inches (divide pixel size by DPI)
                # Use a more conservative sizing to ensure proper centering
                width_inches = (width * 0.65) / (self.figure.dpi * dpi_factor)
                height_inches = (height * 0.45) / (self.figure.dpi * dpi_factor)
                self.figure.set_size_inches(width_inches, height_inches)
                
                # Force tight layout to ensure proper spacing
                self.figure.tight_layout(pad=1.5)
                
                # Redraw canvas
                if hasattr(self, 'canvas'):
                    self.canvas.draw()
            
            # Center the dialog on screen
            self.center_on_screen()
            
        except Exception as e:
            logger.error(f"Error adjusting for screen: {e}")

    def center_on_screen(self):
        """Center the dialog on the current screen"""
        # Get screen geometry
        screen = self.screen()
        if not screen:
            screen = QApplication.primaryScreen()
        
        screen_geometry = screen.availableGeometry()
        
        # Calculate center position
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        
        # Move the dialog
        self.move(screen_geometry.left() + x, screen_geometry.top() + y)

    def moveEvent(self, event):
        """Handle move events to adapt to screen changes"""
        super().moveEvent(event)
        # Detect if moved to a different screen
        new_screen = self.screen()
        if hasattr(self, 'current_screen') and self.current_screen != new_screen:
            self.current_screen = new_screen
            # Adjust layout for the new screen
            QTimer.singleShot(100, self.adjust_for_screen)
        elif not hasattr(self, 'current_screen'):
            self.current_screen = new_screen
    
    def update_preview(self, maintain_limits=False):
        """Plot barologger data including master baro"""
        try:
            if maintain_limits:
                old_xlim = self.ax.get_xlim()
                old_ylim = self.ax.get_ylim()
                
            self.ax.clear()
            start_dt = self.start_date.dateTime().toPyDateTime()
            end_dt = self.end_date.dateTime().toPyDateTime()
            has_data = False
            all_pressures = []
            all_timestamps = []  # Track actual data timestamps
            
            # Plot master baro first in black if exists and the checkbox is checked
            if self.has_master_data and self.master_baro_cb.isChecked():
                mask = (self.master_data['timestamp_utc'] >= start_dt) & \
                       (self.master_data['timestamp_utc'] <= end_dt)
                master_filtered = self.master_data[mask]
                if not master_filtered.empty:
                    self.ax.plot(master_filtered['timestamp_utc'],
                               master_filtered['pressure'],
                               'k-', label='Master Baro',
                               linewidth=2, zorder=10)
                    all_pressures.extend(master_filtered['pressure'].values)
                    all_timestamps.extend(master_filtered['timestamp_utc'].values)
                    has_data = True
                    
            # Plot individual barologgers
            for serial, cb in self.baro_checkboxes.items():
                if cb.isChecked() and serial in self.barologger_data:
                    df = self.barologger_data[serial]
                    mask = (df['timestamp_utc'] >= start_dt) & (df['timestamp_utc'] <= end_dt)
                    filtered = df[mask]
                    if not filtered.empty:
                        color_rgba = self.baro_colors[serial]
                        
                        # Modified: Remove date range from label - get just the serial and location
                        label_parts = cb.text().split('-', 1)
                        location = label_parts[1].strip() if len(label_parts) > 1 else ""
                        if "(" in location:  # Remove date range in parentheses
                            location = location.split("(")[0].strip()
                        label_txt = f"{serial} - {location}"
                        
                        self.ax.plot(filtered['timestamp_utc'], filtered['pressure'],
                                   label=label_txt, color=color_rgba, alpha=0.6)
                        all_pressures.extend(filtered['pressure'].values)
                        all_timestamps.extend(filtered['timestamp_utc'].values)
                        has_data = True
                        
            if has_data:
                self.ax.set_ylabel('Pressure (PSI)')
                self.ax.grid(True, linestyle='--', alpha=0.6)
                
                # Don't show legend directly on the plot
                self.ax.legend_ = None
                
                self.ax.tick_params(axis='x', rotation=45)
                
                # Format date axis for UTC
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                
                if maintain_limits and old_xlim[0] != old_xlim[1] and old_ylim[0] != old_ylim[1]:
                    # Only maintain limits if they're valid
                    self.ax.set_xlim(old_xlim)
                    self.ax.set_ylim(old_ylim)
                else:
                    if all_pressures:
                        ymin, ymax = min(all_pressures), max(all_pressures)
                        # Increase padding for better visualization
                        pad = max(0.5, (ymax - ymin) * 0.2)
                        self.ax.set_ylim(ymin - pad, ymax + pad)
                    
                    # Set x-axis limits based on actual data range, not input range
                    if all_timestamps:
                        # Convert to pandas datetime for easier manipulation
                        ts_series = pd.Series(all_timestamps)
                        xmin, xmax = ts_series.min(), ts_series.max()
                        # Add small padding (2% of range)
                        x_range = (xmax - xmin).total_seconds()
                        x_pad = pd.Timedelta(seconds=x_range * 0.02)
                        self.ax.set_xlim(xmin - x_pad, xmax + x_pad)
                    else:
                        # Fallback to input range if no data
                        self.ax.set_xlim(start_dt, end_dt)
                    
                # Update the legend in the dedicated legend widget
                handles, labels = self.ax.get_legend_handles_labels()
                if handles:
                    legend_text = ""
                    # Create an HTML-based legend
                    for i, (handle, label) in enumerate(zip(handles, labels)):
                        # Check the type of handle to get the appropriate color
                        if hasattr(handle, 'get_color'):
                            color = handle.get_color()
                        elif hasattr(handle, 'get_facecolor'):
                            # For Rectangle or other patch objects
                            color = handle.get_facecolor()
                        else:
                            # Default color if we can't determine
                            color = "#999999"
                            
                        if isinstance(color, tuple):
                            # RGB tuple to hex
                            hex_color = "#{:02x}{:02x}{:02x}".format(
                                int(color[0]*255), int(color[1]*255), int(color[2]*255))
                        elif isinstance(color, str) and color == 'k':
                            hex_color = "#000000"  # Black for Master Baro
                        else:
                            hex_color = color
                            
                        legend_text += f"<span style='color:{hex_color};'>■</span> {label}<br>"
                        
                        # Add a line break after every 2 items
                        if (i + 1) % 2 == 0 and i < len(handles) - 1:
                            legend_text += "<br>"
                    
                    # Set legend text
                    self.legend_widget.setText(legend_text)
                    self.legend_widget.setTextFormat(Qt.RichText)
                else:
                    self.legend_widget.setText("No data to display")
            else:
                self.ax.text(0.5, 0.5, 'No data available',
                            ha='center', va='center', transform=self.ax.transAxes)
                self.legend_widget.setText("No data to display")
                    
            # Recreate span selector
            self.span_selector = SpanSelector(
                self.ax, self.on_span_select, 'horizontal',
                useblit=True, props=dict(alpha=0.2, facecolor='red'),
                interactive=True
            )
            
            # Apply tight layout for better spacing
            self.figure.tight_layout(pad=1.5)
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            QMessageBox.warning(self, "Warning", f"Error updating preview: {str(e)}")
    
    def on_span_select(self, xmin, xmax):
        """Handle span selection"""
        try:
            start = pd.Timestamp(matplotlib.dates.num2date(xmin))
            end = pd.Timestamp(matplotlib.dates.num2date(xmax))
            self.start_date.setDateTime(start)
            self.end_date.setDateTime(end)
            self.canvas.draw()
        except Exception as e:
            logger.error(f"Error in span selection: {e}")
            
    def get_cached_data_for(self, serial: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
        """Helper method to get filtered data from cache for a specific barologger"""
        try:
            if serial not in self.barologger_data:
                return pd.DataFrame()
            
            df = self.barologger_data[serial]
            mask = (df['timestamp_utc'] >= start_dt) & (df['timestamp_utc'] <= end_dt)
            return df[mask].copy()
        except Exception as e:
            logger.error(f"Error filtering cached data for {serial}: {e}")
            return pd.DataFrame()
            
    def load_barologger_data(self):
        """Load and cache all barologger data"""
        try:
            barologgers = self.baro_model.get_all_barologgers()
            color_map = cm.get_cmap('tab10', len(barologgers))
            overall_min_date = None
            overall_max_date = None
    
            logger.debug(f"Loading data for {len(barologgers)} barologgers")
            
            # Use progress_dialog instead of embedded progress bar
            progress_dialog.show("Loading barologger data...", "Loading Data", min_duration=0)
            progress_dialog.update(0, f"Loading {len(barologgers)} barologgers...")
    
            # Now load and add the individual barologgers
            for i, baro in enumerate(barologgers):
                serial = baro['serial_number']
                loc_desc = baro['location_description']
                self.baro_colors[serial] = color_map(i)
                
                # Update progress dialog with specific barologger info
                progress_dialog.update(
                    int(100 * (i + 0.5) / len(barologgers)), 
                    f"Loading data for {serial} - {loc_desc}..."
                )
    
                # Load and cache all data for this barologger
                data = self.baro_model.get_readings(serial)
                
                # Create checkbox with appropriate label (with date range if data exists)
                if not data.empty:
                    # Ensure timestamp_utc is datetime
                    data['timestamp_utc'] = pd.to_datetime(data['timestamp_utc'])
                    min_t = data['timestamp_utc'].min()
                    max_t = data['timestamp_utc'].max()
                    
                    # Format date range for checkbox
                    date_range = f"({min_t.strftime('%Y-%m-%d')} to {max_t.strftime('%Y-%m-%d')})"
                    
                    # Create checkbox with date range
                    cb = QCheckBox(f"{serial} - {loc_desc} {date_range}")
                    
                    if overall_min_date is None or min_t < overall_min_date:
                        overall_min_date = min_t
                    if overall_max_date is None or max_t > overall_max_date:
                        overall_max_date = max_t
                        
                    self.barologger_data[serial] = data
                    logger.debug(f"Cached {len(data)} readings for {serial}")
                else:
                    # If no data, add checkbox without date range
                    cb = QCheckBox(f"{serial} - {loc_desc} (no data)")
                
                # Set checkbox properties and add to layout
                cb.setChecked(True)
                cb.stateChanged.connect(self.baro_checkbox_changed)
                self.baro_checkboxes[serial] = cb
                self.baro_layout.addWidget(cb)
                
                # Update progress dialog
                progress_dialog.update(int(100 * (i + 1) / len(barologgers)))
                QApplication.processEvents()
    
            # Update progress before preparing plot
            progress_dialog.update(90, "Preparing plot...")
    
            if overall_min_date and overall_max_date:
                self.start_date.setDateTime(overall_min_date)
                self.end_date.setDateTime(overall_max_date)
    
            self.update_preview(False)
            self.canvas.draw()
            self.toolbar.push_current()
            
            # Close progress dialog
            progress_dialog.close()
            
            logger.debug("Completed loading and caching barologger data")
    
        except Exception as e:
            progress_dialog.close()  # Make sure to close the dialog on error
            logger.error(f"Error loading barologger data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
    
    def baro_checkbox_changed(self, state):
        """Handle checkbox changes"""
        try:
            selected_dfs = []
            for serial, cb in self.baro_checkboxes.items():
                if cb.isChecked() and serial in self.barologger_data:
                    selected_dfs.append(self.barologger_data[serial])
    
            if not selected_dfs:
                self.ax.clear()
                self.canvas.draw()
                return
    
            combined = pd.concat(selected_dfs)
            min_t = combined['timestamp_utc'].min()
            max_t = combined['timestamp_utc'].max()
    
            self.start_date.blockSignals(True)
            self.end_date.blockSignals(True)
            self.start_date.setDateTime(min_t)
            self.end_date.setDateTime(max_t)
            self.start_date.blockSignals(False)
            self.end_date.blockSignals(False)
    
            self.update_preview(False)
            self.canvas.draw()
            self.toolbar.push_current()
    
        except Exception as e:
            logger.error(f"Error adjusting baro checkboxes: {e}")
    
    def zoom_to_selected_data(self):
        try:
            start_dt = self.start_date.dateTime().toPyDateTime()
            end_dt = self.end_date.dateTime().toPyDateTime()
            start_num = matplotlib.dates.date2num(start_dt)
            end_num = matplotlib.dates.date2num(end_dt)
            self.ax.set_xlim(start_num, end_num)
            self.canvas.draw()
        except Exception as e:
            logger.error(f"Error zooming to selected data: {e}")
    
    def toggle_all_barologgers(self, state):
        for cb in self.baro_checkboxes.values():
            cb.setChecked(state == Qt.Checked)
        # Don't toggle the master baro checkbox here
    
    def preview_master_baro(self):
        """Preview master baro calculation using cached data"""
        try:
            logger.debug("Starting master baro preview calculation")
            selected_baros = [serial for serial, cb in self.baro_checkboxes.items() 
                            if cb.isChecked()]
            
            if not selected_baros:
                logger.warning("No barologgers selected")
                QMessageBox.warning(self, "Warning", "Select at least one barologger")
                return
                
            start_dt = self.start_date.dateTime().toPyDateTime()
            end_dt = self.end_date.dateTime().toPyDateTime()
            logger.debug(f"Time range: {start_dt} to {end_dt}")
            
            # Use cached data filtered by time range
            readings_data = []
            for serial in selected_baros:
                filtered_df = self.get_cached_data_for(serial, start_dt, end_dt)
                if not filtered_df.empty:
                    readings_data.append(filtered_df)
                    logger.debug(f"Using {len(filtered_df)} cached readings for {serial}")
            
            if not readings_data:
                logger.warning("No data found in selected range")
                QMessageBox.warning(self, "Warning", "No data found in selected range")
                return
                
            logger.debug(f"Processing data from {len(readings_data)} barologgers")
            preview_data = self.baro_model._process_master_baro_data(readings_data, 
                                                                  self.min_readings.value())
            logger.debug(f"Processed data size: {len(preview_data) if not preview_data.empty else 0} rows")
            
            # Cache the preview data for potential creation
            self.preview_result = preview_data
            
            self.plot_preview(preview_data)
            
        except Exception as e:
            logger.error(f"Error in preview_master_baro: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to generate preview: {str(e)}")
    
    def check_master_data(self):
        """Check if master baro data exists"""
        try:
            with sqlite3.connect(self.baro_model.db_path) as conn:
                # First check if table exists
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='master_baro_readings'
                """)
                
                if not cursor.fetchone():
                    self.has_master_data = False
                    return
                
                # Query existing data
                query = """
                    SELECT timestamp_utc, pressure, temperature,
                           source_barologgers, processing_date, notes
                    FROM master_baro_readings
                    ORDER BY timestamp_utc
                """
                
                df = pd.read_sql_query(query, conn)
                
                if not df.empty:
                    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                    self.master_data = df
                    self.has_master_data = True
                else:
                    self.has_master_data = False
                    
        except Exception as e:
            logger.error(f"Error checking master data: {e}")
            self.has_master_data = False
    
    def create_master_baro(self):
        """Create master baro using cached data"""
        try:
            selected_baros = [serial for serial, cb in self.baro_checkboxes.items() 
                             if cb.isChecked()]
            
            if not selected_baros:
                QMessageBox.warning(self, "Warning", "Select at least one barologger")
                return
                
            start_dt = self.start_date.dateTime().toPyDateTime()
            end_dt = self.end_date.dateTime().toPyDateTime()
            
            if start_dt >= end_dt:
                QMessageBox.warning(self, "Warning", "Invalid date range")
                return
            
            # Show progress dialog
            progress_dialog.show(message="Preparing master barometric data...", 
                                 title="Creating Master Baro", 
                                 min_duration=0)
            progress_dialog.update(10, "Validating inputs...")
            
            # Use cached preview result if available, otherwise recompute
            if not hasattr(self, 'preview_result') or self.preview_result is None:
                progress_dialog.update(20, "Processing barologger data...")
                readings_data = []
                for serial in selected_baros:
                    filtered_df = self.get_cached_data_for(serial, start_dt, end_dt)
                    if not filtered_df.empty:
                        readings_data.append(filtered_df)
                
                if not readings_data:
                    progress_dialog.close()
                    QMessageBox.warning(self, "Warning", "No data found in selected range")
                    return
                
                progress_dialog.update(40, "Calculating master baro values...")
                master_data = self.baro_model._process_master_baro_data(
                    readings_data,
                    self.min_readings.value()
                )
            else:
                progress_dialog.update(40, "Using preview results...")
                master_data = self.preview_result
            
            progress_dialog.update(50, "Validating results...")
            
            if master_data is None or master_data.empty:
                progress_dialog.close()
                QMessageBox.warning(self, "Warning", "No valid data to save")
                return
            
            # Prepare data for batch insert
            try:
                progress_dialog.update(60, "Saving to database...")
                with sqlite3.connect(self.baro_model.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # If overwrite is enabled, delete overlapping timestamps
                    if self.overwrite_cb.isChecked():
                        progress_dialog.update(70, "Removing overlapping data...")
                        cursor.execute("""
                            DELETE FROM master_baro_readings
                            WHERE timestamp_utc BETWEEN ? AND ?
                        """, (start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                              end_dt.strftime('%Y-%m-%d %H:%M:%S')))
                    
                    # Prepare batch insert data
                    progress_dialog.update(80, "Preparing batch insert...")
                    sources_json = json.dumps(selected_baros)
                    insert_data = []
                    
                    for _, row in master_data.iterrows():
                        insert_data.append((
                            row['timestamp_utc'].strftime('%Y-%m-%d %H:%M:%S'),
                            row['pressure_mean'],
                            row['temp_mean'] if 'temp_mean' in row else None,
                            sources_json,
                            ''  # notes
                        ))
                    
                    # Batch insert
                    progress_dialog.update(90, f"Inserting {len(insert_data)} data points...")
                    cursor.executemany("""
                        INSERT INTO master_baro_readings 
                        (timestamp_utc, pressure, temperature, source_barologgers, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """, insert_data)
                    
                    conn.commit()
                
                # Instead of closing the dialog immediately, show a message that data will be reloaded
                progress_dialog.update(95, "Master baro created. Reloading data in main window...")
                
                # Emit signal that master baro was created (parent will handle reloading)
                self.master_baro_created.emit()
                
                # Keep progress dialog open a bit longer to show user data is being reloaded
                QTimer.singleShot(1000, lambda: self.complete_creation(progress_dialog))
                
            except Exception as e:
                progress_dialog.close()
                logger.error(f"Error saving master baro data: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save master baro: {str(e)}")
                
        except Exception as e:
            if progress_dialog:
                progress_dialog.close()
            logger.error(f"Error creating master baro: {e}")
            QMessageBox.critical(self, "Error", str(e))
    
    def complete_creation(self, progress_dialog_instance):
        """Complete the creation process by closing the progress dialog and the form"""
        progress_dialog_instance.close()
        QMessageBox.information(self, "Success", "Master baro created successfully.")
        self.accept()
            
    def on_overwrite_changed(self, state):
        """Handle overwrite checkbox state change"""
        if self.has_master_data:
            self.preview_master_baro()   
        
    def plot_preview(self, preview_data: pd.DataFrame):
        """Plot preview of master baro data"""
        try:
            logger.debug("Starting plot_preview")
            logger.debug(f"Preview data empty: {preview_data.empty if preview_data is not None else 'None'}")
            if preview_data is not None:
                logger.debug(f"Preview data columns: {preview_data.columns.tolist()}")
            
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            
            if preview_data is None or preview_data.empty:
                self.ax.text(0.5, 0.5, 'No data available',
                            ha='center', va='center',
                            transform=self.ax.transAxes)
                self.canvas.draw()
                return

            has_data = False
            y_min, y_max = float('inf'), float('-inf')

            # Plot Existing Master Data if available and master baro checkbox is checked
            if self.has_master_data and not self.master_data.empty and self.master_baro_cb.isChecked():
                logger.debug(f"Plotting existing master data: {len(self.master_data)} points")
                has_data = True
                self.ax.plot(self.master_data['timestamp_utc'], self.master_data['pressure'],
                            'k-', label='Existing Master', alpha=0.3)
                y_min = min(y_min, self.master_data['pressure'].min())
                y_max = max(y_max, self.master_data['pressure'].max())

                # If not overwriting, mark overlapping regions
                if not self.overwrite_cb.isChecked():
                    overlap_mask = preview_data['timestamp_utc'].isin(self.master_data['timestamp_utc'])
                    if overlap_mask.any():
                        # Highlight overlapping regions
                        overlap_times = preview_data['timestamp_utc'][overlap_mask]
                        self.ax.axvspan(overlap_times.min(), overlap_times.max(),
                                      color='yellow', alpha=0.2, label='Overlap')
                        
                        # If overwrite is disabled, remove overlapping timestamps from preview
                        preview_data = preview_data[~overlap_mask]

            # Plot Individual Barologger Data
            selected_baros = [serial for serial, cb in self.baro_checkboxes.items() if cb.isChecked()]
            for serial in selected_baros:
                if serial in self.barologger_data:
                    data = self.barologger_data[serial]
                    if not data.empty:
                        logger.debug(f"Plotting barologger {serial} data: {len(data)} points")
                        has_data = True
                        color = self.baro_colors[serial]
                        
                        # Modified: Create cleaner label without date range
                        cb_text = self.baro_checkboxes[serial].text()
                        location = cb_text.split('-', 1)[1].strip() if '-' in cb_text else ""
                        if "(" in location:  # Remove date range in parentheses
                            location = location.split("(")[0].strip()
                        label = f"{serial} - {location}"
                        
                        self.ax.plot(data['timestamp_utc'], data['pressure'],
                                   color=color, alpha=0.5, label=label)
                        y_min = min(y_min, data['pressure'].min())
                        y_max = max(y_max, data['pressure'].max())

            # Plot Preview Master Baro Data
            if not preview_data.empty:
                logger.debug("Plotting preview master baro data")
                has_data = True
                
                # Find gaps in the data (where pressure_count is less than minimum readings)
                # Using 1 as the default minimum if min_readings is not set explicitly
                min_readings_value = self.min_readings.value() if hasattr(self, 'min_readings') else 1
                gap_mask = preview_data['pressure_count'] < min_readings_value
                
                # Plot regular data
                valid_data = preview_data[~gap_mask]
                if not valid_data.empty:
                    self.ax.plot(valid_data['timestamp_utc'], valid_data['pressure_mean'],
                                'b-', label='Preview Master', linewidth=2)
                
                # Highlight gaps with different color and style
                gap_data = preview_data[gap_mask]
                if not gap_data.empty:
                    self.ax.plot(gap_data['timestamp_utc'], gap_data['pressure_mean'],
                                'r--', label='Insufficient Readings', linewidth=1, alpha=0.5)
                    
                    # Add light red background for gap periods
                    for _, group in gap_data.groupby((gap_data['timestamp_utc'].diff() > pd.Timedelta('15min')).cumsum()):
                        if len(group) > 0:
                            self.ax.axvspan(group['timestamp_utc'].iloc[0], 
                                          group['timestamp_utc'].iloc[-1],
                                          color='red', alpha=0.1)
                
                y_min = min(y_min, preview_data['pressure_mean'].min())
                y_max = max(y_max, preview_data['pressure_mean'].max())

            # Final Plot Adjustments
            if has_data:
                logger.debug("Applying final plot adjustments")
                self.ax.set_ylabel('Pressure (PSI)')
                self.ax.grid(True, linestyle='--', alpha=0.6)
                
                # Format x-axis with dates
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                self.ax.tick_params(axis='x', rotation=45)
                
                # Set y-axis limits with better padding
                y_range = y_max - y_min
                # Use at least 0.5 PSI padding or 20% of range, whichever is larger
                padding = max(0.5, y_range * 0.2)
                self.ax.set_ylim(y_min - padding, y_max + padding)

                # Update the legend widget instead of showing it on the plot
                handles, labels = self.ax.get_legend_handles_labels()
                if handles:
                    legend_text = ""
                    # Create an HTML-based legend
                    for i, (handle, label) in enumerate(zip(handles, labels)):
                        # Check the type of handle to get the appropriate color
                        if hasattr(handle, 'get_color'):
                            color = handle.get_color()
                        elif hasattr(handle, 'get_facecolor'):
                            # For Rectangle or other patch objects
                            color = handle.get_facecolor()
                        else:
                            # Default color if we can't determine
                            color = "#999999"
                            
                        if isinstance(color, tuple):
                            # RGB tuple to hex
                            hex_color = "#{:02x}{:02x}{:02x}".format(
                                int(color[0]*255), int(color[1]*255), int(color[2]*255))
                        elif isinstance(color, str) and color == 'k':
                            hex_color = "#000000"  # Black for Master Baro
                        elif isinstance(color, str) and color == 'b':
                            hex_color = "#0000FF"  # Blue for Preview Master
                        elif isinstance(color, str) and color == 'r':
                            hex_color = "#FF0000"  # Red for Insufficient Readings
                        else:
                            hex_color = color
                            
                        legend_text += f"<span style='color:{hex_color};'>■</span> {label}<br>"
                        
                        # Add a line break after every 2 items
                        if (i + 1) % 2 == 0 and i < len(handles) - 1:
                            legend_text += "<br>"
                    
                    # Set legend text
                    self.legend_widget.setText(legend_text)
                    self.legend_widget.setTextFormat(Qt.RichText)
                else:
                    self.legend_widget.setText("No data to display")
            else:
                logger.warning("No data to plot")
                self.ax.text(0.5, 0.5, 'No data available',
                            ha='center', va='center',
                            transform=self.ax.transAxes)
                self.legend_widget.setText("No data to display")

            # Apply tight layout for better spacing
            self.figure.tight_layout(pad=1.5)
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error in plot_preview: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to plot preview: {str(e)}")
    
    def set_full_range(self):
        """Set the time range to the full range of all selected barologgers and highlight the selection"""
        try:
            selected_dfs = []
            # Include master baro data if checked
            if self.master_baro_cb.isChecked() and self.has_master_data and self.master_data is not None:
                selected_dfs.append(self.master_data)
                
            # Add selected barologgers
            for serial, cb in self.baro_checkboxes.items():
                if cb.isChecked() and serial in self.barologger_data:
                    selected_dfs.append(self.barologger_data[serial])
            
            if not selected_dfs:
                QMessageBox.warning(self, "Warning", "No barologgers selected")
                return
                
            # Find min and max timestamp across all selected data
            combined = pd.concat(selected_dfs)
            min_t = combined['timestamp_utc'].min()
            max_t = combined['timestamp_utc'].max()
            
            # Set the range
            self.start_date.setDateTime(min_t)
            self.end_date.setDateTime(max_t)
            
            # Update the plot
            self.update_preview()
            
            # Highlight the full range in the plot with the span selector
            # Convert datetime to matplotlib date numbers
            min_num = mdates.date2num(min_t)
            max_num = mdates.date2num(max_t)
            
            # Simulate a span selection to highlight the area
            # First remove existing span
            if hasattr(self, 'span_selector'):
                self.span_selector.clear()
                
            # Then add new span that covers the full range
            if hasattr(self.ax, 'axvspan'):
                # Remove any existing spans
                for artist in self.ax.patches:
                    if isinstance(artist, matplotlib.patches.Rectangle) and artist.get_alpha() == 0.2:
                        artist.remove()
                
                # Add the new span
                self.ax.axvspan(min_num, max_num, alpha=0.2, facecolor='red')
                self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error setting full range: {e}")
            QMessageBox.warning(self, "Error", f"Could not set full range: {str(e)}")