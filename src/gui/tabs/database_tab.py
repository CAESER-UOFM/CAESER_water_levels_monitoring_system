from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QGroupBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer  # Add QTimer
from folium import Map, Marker, Icon  # Add Icon import
from io import BytesIO
import base64
import sqlite3
import os
import time  # Add time module
import tempfile
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebChannel import QWebChannel
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd
from pathlib import Path
import logging
import subprocess
import json
import sys

logger = logging.getLogger(__name__)

class DatabaseTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.db_manager.database_changed.connect(self.sync_database_selection)
        self.current_dir = Path(__file__).parent.parent.parent.parent
        self.current_map_file = None  # Track current map file
        self.init_ui()

    def init_ui(self):
        """Setup the UI with map."""
        layout = QVBoxLayout(self)

        # --- Map Section ---
        self.map_view = QWebEngineView()
        self.map_view.setMinimumSize(800, 500)
        
        # Set up web channel BEFORE loading the map
        self.setup_web_channel()
        
        layout.addWidget(self.map_view, stretch=1)
        self.setLayout(layout)
        
        # Load wells when the tab is initialized
        self.load_wells()
        
        if self.db_manager and self.db_manager.current_db:
            self.load_wells()

    def setup_ui(self):
        """Setup the UI with a database selection panel, a 'New Database' button, and a map."""
    
        main_layout = QVBoxLayout(self)  # Main vertical layout
    
        # --- Database Selection Panel ---
        db_group = QGroupBox("Database Management")  # Add a titled section
        db_layout = QHBoxLayout()
    
        # Label
        self.db_label = QLabel("Select Database:")
        self.db_label.setStyleSheet("font-weight: bold;")
    
        # Dropdown for database selection
        self.db_combo = QComboBox()
        self.db_combo.setFixedWidth(250)  # Make it compact
        self.db_combo.currentTextChanged.connect(self.on_database_changed)
    
        # Create "New Database" button
        self.create_db_button = QPushButton("New Database")
        self.create_db_button.setFixedWidth(140)
        self.create_db_button.clicked.connect(self.create_new_database)
    
        # Create "Refresh" button
        self.refresh_db_button = QPushButton("Refresh")
        self.refresh_db_button.setFixedWidth(100)
        self.refresh_db_button.clicked.connect(self.load_existing_databases)
    
        # Add widgets to the database selection layout
        db_layout.addWidget(self.db_label)
        db_layout.addWidget(self.db_combo, stretch=1)  # Allow dropdown to expand
        db_layout.addWidget(self.create_db_button)  # Ensure button is here
        db_layout.addWidget(self.refresh_db_button)
        
        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)
    
        # --- Map Section ---
        self.map_view = QWebEngineView()
        self.map_view.setMinimumSize(800, 500)  # Ensure good default size
        main_layout.addWidget(self.map_view, stretch=1)  # Expand map section
    
        self.setLayout(main_layout)
    
        self.load_existing_databases()

    def setup_web_channel(self):
        """Setup communication between folium map and PyQt to send well data."""
        from PyQt5.QtWebChannel import QWebChannel
        from PyQt5.QtCore import QObject, pyqtSlot
    
        class WebBridge(QObject):
            """Bridge class to handle messages from JavaScript."""
            def __init__(self, parent):
                super().__init__(parent)
                self.parent = parent
    
            @pyqtSlot(str)
            def sendData(self, well_number):
                """Handle well selection and update the graph."""
                # Update the graph in the tab
                self.parent.update_graph(well_number)
                
                # Also open the data visualizer dialog with this well pre-selected
                self.parent.open_data_visualizer(well_number)
    
        self.bridge = WebBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("pywebchannel", self.bridge)
        self.map_view.page().setWebChannel(self.channel)
        
        # Connect to the loadFinished signal to inject JavaScript after page load
        self.map_view.loadFinished.connect(self._inject_web_channel_js)

    def _inject_web_channel_js(self, ok):
        """Inject the QWebChannel JavaScript code after the page is loaded."""
        if ok:
            try:
                # First inject the QWebChannel JavaScript library
                from PyQt5.QtCore import QFile, QIODevice
                from PyQt5.QtWebChannel import QWebChannel
                
                # Find the qwebchannel.js file from PyQt resources
                qwebchannel_js = QFile(':/qtwebchannel/qwebchannel.js')
                if qwebchannel_js.open(QIODevice.ReadOnly):
                    # Read the JavaScript content
                    js_bytes = qwebchannel_js.readAll()
                    js_string = str(js_bytes, 'utf-8')
                    qwebchannel_js.close()
                    
                    # First inject the QWebChannel library JavaScript
                    self.map_view.page().runJavaScript(js_string)
                    logger.debug("Injected QWebChannel JavaScript library")
                    
                    # Then inject our connection code with a slight delay to ensure the library is loaded
                    QTimer.singleShot(200, lambda: self._inject_connection_code())
                else:
                    logger.error("Could not open qwebchannel.js resource file")
                    # Try to inject connection code directly anyway
                    self._inject_connection_code()
            except Exception as e:
                logger.error(f"Error injecting web channel JS: {e}")
    
    def _inject_connection_code(self):
        """Inject the code to connect to our Python object after library is loaded."""
        try:
            # Inject JavaScript to connect the bridge
            js_code = """
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.pywebchannel = channel.objects.pywebchannel;
                });
            """
            self.map_view.page().runJavaScript(js_code)
            logger.debug("Injected QWebChannel connection code")
        except Exception as e:
            logger.error(f"Error injecting connection code: {e}")

    def load_existing_databases(self):
        """This method is no longer needed"""
        pass

    def load_wells(self):
        """Load wells from the selected database and display them on a map."""
        import time
        start_time = time.time()
        logger.debug("PERF: Starting well loading process")
        
        if not self.db_manager or not self.db_manager.current_db:
            logger.debug("PERF: No database manager or database, skipping well loading")
            return

        # Get well locations
        fetch_start = time.time()
        well_data = self.get_well_locations()
        fetch_end = time.time()
        logger.debug(f"PERF: Fetching well locations took {(fetch_end - fetch_start)*1000:.2f}ms, found {len(well_data)} wells")
        
        # Display on map
        display_start = time.time()
        self.display_map(well_data)  # Always call display_map
        display_end = time.time()
        logger.debug(f"PERF: Displaying wells on map took {(display_end - display_start)*1000:.2f}ms")
        
        total_time = time.time() - start_time
        logger.debug(f"PERF: Total well loading process took {total_time*1000:.2f}ms")

    def get_well_locations(self):
        """Fetch well locations from the selected database."""
        import time
        start_time = time.time()
        logger.debug("PERF: Fetching well location data from database")
        
        try:
            query_start = time.time()
            with sqlite3.connect(self.db_manager.current_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT well_number, latitude, longitude FROM wells WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
                wells = cursor.fetchall()
                
                if wells:
                    first_well = wells[0] if wells else None
                    sample = f"First well: {first_well}" if first_well else "No wells found"
                    logger.debug(f"PERF: Found {len(wells)} wells with coordinates. {sample}")
                else:
                    logger.debug("PERF: No wells with coordinates found in the database")
                    
            query_end = time.time()
            logger.debug(f"PERF: Database query for well locations took {(query_end - query_start)*1000:.2f}ms")
            
            total_time = time.time() - start_time
            logger.debug(f"PERF: Total well location fetch time: {total_time*1000:.2f}ms")
            return wells
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"PERF: Error fetching well data after {error_time*1000:.2f}ms: {e}")
            return []

    def display_map(self, well_data):
        """Display map with better error handling and file cleanup"""
        import time
        start_time = time.time()
        logger.debug(f"PERF: Starting map display with {len(well_data)} wells")
        
        try:
            # Clean up previous map file if it exists
            cleanup_start = time.time()
            self._cleanup_previous_map()
            cleanup_end = time.time()
            logger.debug(f"PERF: Previous map cleanup took {(cleanup_end - cleanup_start)*1000:.2f}ms")

            # Create a folium map (initial center/zoom will be adjusted to fit wells)
            map_create_start = time.time()
            m = Map(
                location=[35.1495, -90.0490],
                zoom_start=10,
                prefer_canvas=True  # Add this for better performance
            )
            map_create_end = time.time()
            logger.debug(f"PERF: Folium map creation took {(map_create_end - map_create_start)*1000:.2f}ms")

            # Fetch well stats using the well_statistics table instead of slow JOIN
            stats_query_start = time.time()
            try:
                # Use the WellModel to get statistics - much faster query
                from src.database.models.well import WellModel
                well_model = WellModel(self.db_manager.current_db)
                
                # Get well data including the flag status stored in the wells table
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    # Include the baro_status and level_status columns from the wells table
                    cursor.execute("""
                        SELECT w.well_number, w.cae_number, w.latitude, w.longitude,
                               w.baro_status, w.level_status, 
                               ws.num_points, ws.min_timestamp, ws.max_timestamp
                        FROM wells w
                        LEFT JOIN well_statistics ws ON w.well_number = ws.well_number
                        WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
                    """)
                    well_stats = cursor.fetchall()
                
                stats_query_end = time.time()
                logger.debug(f"PERF: Retrieved well stats for map in {(stats_query_end - stats_query_start)*1000:.2f}ms")
                
                # No well data available
                if not well_stats:
                    logger.debug("No well data available for map")
                    self._show_empty_map()
                    return
            except Exception as e:
                logger.warning(f"PERF: Could not fetch well stats from statistics table: {e}")
                logger.warning("PERF: Falling back to the slower query method")
                
                # Fallback to the older, slower method
                with sqlite3.connect(self.db_manager.current_db) as conn:
                    cursor = conn.cursor()
                    try:
                        # Check if we have water_level_readings table, if not, use basic well info
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='water_level_readings'")
                        if not cursor.fetchone():
                            logger.warning("PERF: water_level_readings table does not exist, using basic well data")
                            cursor.execute("""
                                SELECT w.well_number, w.cae_number, w.latitude, w.longitude,
                                       0 AS num_points, NULL AS min_ts, NULL AS max_ts
                                FROM wells w
                                WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
                            """)
                        else:
                            cursor.execute("""
                                SELECT w.well_number, w.cae_number, w.latitude, w.longitude,
                                       COUNT(l.timestamp_utc) AS num_points,
                                       MIN(l.timestamp_utc) AS min_ts,
                                       MAX(l.timestamp_utc) AS max_ts
                                FROM wells w
                                LEFT JOIN water_level_readings l ON w.well_number = l.well_number
                                WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
                                GROUP BY w.well_number, w.cae_number, w.latitude, w.longitude
                            """)
                        well_stats = cursor.fetchall()
                        logger.debug(f"PERF: Found detailed stats for {len(well_stats)} wells using slow query")
                    except sqlite3.OperationalError as e:
                        logger.warning(f"PERF: Could not fetch well stats (missing table?): {e}")
                        
                        # Last resort: just get basic well data without statistics
                        try:
                            cursor.execute("""
                                SELECT well_number, cae_number, latitude, longitude,
                                       0 AS num_points, NULL AS min_ts, NULL AS max_ts
                                FROM wells
                                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                            """)
                            well_stats = cursor.fetchall()
                            logger.debug(f"PERF: Falling back to basic well data for {len(well_stats)} wells")
                        except Exception as inner_e:
                            logger.error(f"PERF: Could not fetch even basic well data: {inner_e}")
                            well_stats = []
            stats_query_end = time.time()
            logger.debug(f"PERF: Well stats query took {(stats_query_end - stats_query_start)*1000:.2f}ms")

            # Add markers and format map
            markers_start = time.time()
            if well_stats:
                # Determine map bounds
                lats = [row[2] for row in well_stats]
                lons = [row[3] for row in well_stats]
                # Add markers with enriched popup
                for well in well_stats:
                    well_number, cae_number, lat, lon, baro_status, level_status, num_points, min_ts, max_ts = well
                    data_status = 'Has Data' if num_points else 'No Data'
                    date_range = f"{min_ts} to {max_ts}" if num_points else 'N/A'
                    
                    # Determine marker color based on flags from wells table
                    if baro_status == 'all_master' and level_status == 'no_default':
                        marker_color = 'green'  # All good
                    elif baro_status == 'has_non_master' and level_status == 'default_level':
                        marker_color = 'red'    # Both flags have issues
                    elif baro_status == 'has_non_master':
                        marker_color = 'orange' # Baro issue
                    elif level_status == 'default_level':
                        marker_color = 'purple' # Level issue
                    else:
                        marker_color = 'blue'   # Default or no data
                    
                    popup_content = f"""
                    <b>Well:</b> {well_number}<br>
                    <b>CAE:</b> {cae_number or 'N/A'}<br>
                    <b>Data Status:</b> {data_status}<br>
                    <b>Date Range:</b> {date_range}<br>
                    <b>Baro Status:</b> {baro_status}<br>
                    <b>Level Status:</b> {level_status}<br>
                    """
                    popup_html = f"""
                        <div style='font-family: Arial, sans-serif;'>
                            {popup_content}
                            <a href='#' onclick="
                                window.selectedWellNumber = '{well_number}';
                                console.log('Well selected:', window.selectedWellNumber);
                                return false;
                            ">
                                View Data
                            </a>
                        </div>
                    """
                    Marker([lat, lon], popup=popup_html, icon=Icon(color=marker_color)).add_to(m)
                # Adjust map view: if only one well, center and set closer zoom, else fit bounds
                if len(well_stats) == 1:
                    # Single well, center and zoom in
                    m.location = [lats[0], lons[0]]
                    m.zoom_start = 13
                else:
                    # Multiple wells, fit bounds to show all markers
                    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
            else:
                Marker(
                    location=[35.1495, -90.0490],
                    popup="No wells loaded yet",
                    icon=Icon(color='red')
                ).add_to(m)
            markers_end = time.time()
            logger.debug(f"PERF: Adding {len(well_stats) if well_stats else 0} markers took {(markers_end - markers_start)*1000:.2f}ms")

            # Save to temp file with unique name to avoid caching
            save_start = time.time()
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            temp_map_path = os.path.join(temp_dir, f"map_{timestamp}.html")
            m.save(temp_map_path)
            save_end = time.time()
            logger.debug(f"PERF: Saving map to {temp_map_path} took {(save_end - save_start)*1000:.2f}ms")
            
            # Modify the HTML file to add our simple API
            script_start = time.time()
            with open(temp_map_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # Inject a simple JavaScript API that doesn't rely on QWebChannel
            injection_script = """
            <script>
            // Global variable to store selected well
            window.selectedWellNumber = null;
            
            // Function called by Qt to check if a well was selected
            function checkSelectedWell() {
                var selected = window.selectedWellNumber;
                // Reset after reading
                if (selected) {
                    console.log("Returning selected well:", selected);
                    window.selectedWellNumber = null;
                    return selected;
                }
                return "";
            }
            </script>
            </body>
            """
            
            # Replace the closing body tag with our script
            html_content = html_content.replace("</body>", injection_script)
            
            # Write the modified HTML back to the file
            with open(temp_map_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            script_end = time.time()
            logger.debug(f"PERF: Modifying HTML and adding scripts took {(script_end - script_start)*1000:.2f}ms")

            # Store current map file path
            self.current_map_file = temp_map_path

            # Safely disconnect any existing loadFinished connections
            disconnect_start = time.time()
            try:
                self.map_view.loadFinished.disconnect()
            except TypeError:
                # Ignore if no connections exist
                pass
            disconnect_end = time.time()
            logger.debug(f"PERF: Disconnecting signals took {(disconnect_end - disconnect_start)*1000:.2f}ms")
            
            # Connect to loadFinished for both QWebChannel and polling setup
            load_start = time.time()
            self.map_view.loadFinished.connect(self._on_map_loaded)
            self.map_view.setUrl(QUrl.fromLocalFile(temp_map_path))
            load_end = time.time()
            logger.debug(f"PERF: Setting up map URL took {(load_end - load_start)*1000:.2f}ms")

            total_time = time.time() - start_time
            logger.debug(f"PERF: Total map display preparation took {total_time*1000:.2f}ms")

        except Exception as e:
            error_time = time.time() - start_time
            # Log full stack trace
            logger.error(f"PERF: Error displaying map after {error_time*1000:.2f}ms: {e}", exc_info=True)
            # Show error message in the map view for debugging
            self.map_view.setHtml(
                f"<h3 style='color: red; text-align: center;'>"  \
                f"Error loading map: {e}"  \
                "</h3>"
            )

    def _on_map_loaded(self, ok):
        """Handle map load completion by setting up both QWebChannel and polling."""
        import time
        start_time = time.time()
        logger.debug(f"PERF: Map load finished with result: {ok}")
        
        if ok:
            try:
                # First inject the QWebChannel JavaScript
                webchannel_start = time.time()
                self._inject_web_channel_js(ok)
                webchannel_end = time.time()
                logger.debug(f"PERF: Web channel JavaScript injection took {(webchannel_end - webchannel_start)*1000:.2f}ms")
                
                # Then set up polling
                polling_start = time.time()
                self._setup_map_polling()
                polling_end = time.time()
                logger.debug(f"PERF: Setting up map polling took {(polling_end - polling_start)*1000:.2f}ms")
                
                # Safely disconnect the signal
                disconnect_start = time.time()
                try:
                    self.map_view.loadFinished.disconnect(self._on_map_loaded)
                except TypeError:
                    # Ignore if signal is not connected
                    pass
                disconnect_end = time.time()
                logger.debug(f"PERF: Disconnecting load signal took {(disconnect_end - disconnect_start)*1000:.2f}ms")
                
                total_time = time.time() - start_time
                logger.debug(f"PERF: Total map load handling took {total_time*1000:.2f}ms")
                
            except Exception as e:
                logger.error(f"PERF: Error in _on_map_loaded: {e}")
        else:
            logger.warning("PERF: Map failed to load properly")

    def _cleanup_previous_map(self):
        """Clean up previous map file with error handling"""
        if self.current_map_file and os.path.exists(self.current_map_file):
            try:
                os.unlink(self.current_map_file)
            except (PermissionError, OSError) as e:
                logger.debug(f"Could not remove old map file: {e}")
                # Not critical, file will be cleaned up later

    def _schedule_cleanup(self):
        """Schedule cleanup of current map file after it's loaded"""
        if self.current_map_file:
            # Disconnect the signal
            self.map_view.loadFinished.disconnect()
            # Schedule cleanup with longer delay
            QTimer.singleShot(5000, self._delayed_cleanup)

    def _delayed_cleanup(self):
        """Attempt to clean up map file after delay"""
        if self.current_map_file and os.path.exists(self.current_map_file):
            try:
                os.unlink(self.current_map_file)
                self.current_map_file = None
            except (PermissionError, OSError) as e:
                logger.debug(f"Delayed cleanup failed: {e}")
                # Not critical if it fails

    def _setup_map_polling(self):
        """Set up polling for well selection."""
        import time
        start_time = time.time()
        logger.debug("PERF: Setting up map polling")
        
        try:
            # First check if our JavaScript function is available
            js_check_start = time.time()
            self.map_view.page().runJavaScript(
                "typeof checkSelectedWell === 'function'",
                self._check_well_selection_function
            )
            js_check_end = time.time()
            logger.debug(f"PERF: JavaScript function check initiated in {(js_check_end - js_check_start)*1000:.2f}ms")
            
            # Create the polling timer
            timer_start = time.time()
            if not hasattr(self, 'polling_timer'):
                self.polling_timer = QTimer(self)
                self.polling_timer.setInterval(500)  # Check every 500ms
                self.polling_timer.timeout.connect(self._poll_for_well_selection)
            
            # Start the timer
            self.polling_timer.start()
            timer_end = time.time()
            logger.debug(f"PERF: Polling timer setup took {(timer_end - timer_start)*1000:.2f}ms")
            
            total_time = time.time() - start_time
            logger.debug(f"PERF: Total map polling setup took {total_time*1000:.2f}ms")
        except Exception as e:
            logger.error(f"PERF: Error setting up map polling: {e}")

    def _poll_for_well_selection(self):
        """Poll the map for well selection."""
        import time
        start_time = time.time()
        
        try:
            # Run the JavaScript to check for selected well
            self.map_view.page().runJavaScript(
                "checkSelectedWell()",
                self._handle_well_selection
            )
            
            end_time = time.time()
            # Only log if it takes more than 20ms to avoid excessive logging
            if (end_time - start_time) * 1000 > 20:
                logger.debug(f"PERF: Map polling took {(end_time - start_time)*1000:.2f}ms")
        except Exception as e:
            logger.error(f"PERF: Error polling for well selection: {e}")

    def _check_well_selection_function(self, function_exists):
        """Check if the well selection function exists in the map."""
        import time
        start_time = time.time()
        
        if function_exists:
            logger.debug("PERF: checkSelectedWell function exists in map")
        else:
            logger.warning("PERF: checkSelectedWell function does not exist in map")
            # Try to inject it again or handle the error
            try:
                # Simplified version of the function for injection
                self.map_view.page().runJavaScript("""
                    window.selectedWellNumber = null;
                    function checkSelectedWell() {
                        var selected = window.selectedWellNumber;
                        if (selected) {
                            window.selectedWellNumber = null;
                            return selected;
                        }
                        return "";
                    }
                """)
                logger.debug("PERF: Attempted to inject checkSelectedWell function")
            except Exception as e:
                logger.error(f"PERF: Error injecting JavaScript function: {e}")
        
        total_time = time.time() - start_time
        if total_time * 1000 > 10:  # Only log if slow
            logger.debug(f"PERF: Well selection function check took {total_time*1000:.2f}ms")

    def _handle_well_selection(self, well_number):
        """Handle well selection from JavaScript"""
        if well_number and well_number.strip():
            logger.debug(f"Well selected from map: {well_number}")
            # Skip updating the graph - just open the visualizer
            self.open_data_visualizer(well_number)

    def cleanup(self):
        """Clean up resources before closing"""
        self._cleanup_previous_map()
        
        # Stop polling timer if it exists
        if hasattr(self, 'polling_timer') and self.polling_timer.isActive():
            self.polling_timer.stop()

    def update_graph(self, well_number):
        """Fetch water level data for the selected well and update the graph."""
        if not self.db_manager or not self.db_manager.current_db:
            return

        try:
            with sqlite3.connect(self.db_manager.current_db) as conn:
                try:
                    query = """
                        SELECT timestamp_utc, water_level 
                        FROM water_level_readings 
                        WHERE well_number = ?
                        ORDER BY timestamp_utc
                    """
                    df = pd.read_sql_query(query, conn, params=(well_number,))
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not fetch graph data (missing table?): {e}")
                    df = pd.DataFrame()

                if df.empty:
                    self.graph_label.setText(f"No water level data for Well {well_number}")
                    return

                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

                # Update graph
                self.ax.clear()
                self.ax.plot(df['timestamp_utc'], df['water_level'], label=f"Well {well_number}", color="blue")
                self.ax.set_xlabel("Date")
                self.ax.set_ylabel("Water Level (ft)")
                self.ax.legend()
                self.canvas.draw()
                self.graph_label.setText(f"Water Level Data for Well {well_number}")

        except Exception as e:
            self.graph_label.setText(f"Error loading data: {e}")
            
    def create_new_database(self):
        """Create a new database and refresh the map."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        from ..handlers.progress_dialog_handler import progress_dialog
        
        logger.debug("Opening file dialog for new database creation")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Database",
            str(self.current_dir),
            "Database files (*.db)"
        )
    
        if file_path:
            try:
                # Show progress dialog
                progress_dialog.show("Creating new database...", "Database Creation", min_duration=0)
                progress_dialog.update(10, "Initializing database...")
                
                # Create database with slight delay to show progress dialog
                QTimer.singleShot(100, lambda: self._perform_database_creation(file_path))
                
            except Exception as e:
                progress_dialog.close()
                logger.error(f"Failed to create database: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")
    
    def _perform_database_creation(self, file_path):
        """Perform the actual database creation with progress updates."""
        try:
            # Step 1: Create database file
            progress_dialog.update(20, "Creating database file...")
            logger.debug(f"Attempting to create database at: {file_path}")
            self.db_manager.create_database(file_path)
            
            # Step 2: Setting up tables
            progress_dialog.update(50, "Setting up database structure...")
            
            # Step 3: Finalizing
            progress_dialog.update(80, "Finalizing database setup...")
            
            # Step 4: Updating UI
            progress_dialog.update(90, "Refreshing map display...")
            logger.info(f"Successfully created database: {Path(file_path).name}")
            
            # Refresh the map with the empty database
            logger.debug("Refreshing map with empty database")
            self.load_wells()
            
            progress_dialog.update(100, "Database created successfully!")
            
            # Close progress dialog with a small delay to show completion
            QTimer.singleShot(500, progress_dialog.close)
            
            # Show success message
            QMessageBox.information(self, "Success", f"Database created: {Path(file_path).name}")
            
        except Exception as e:
            progress_dialog.close()
            logger.error(f"Failed to create database: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")
    
    def sync_database_selection(self, db_name: str):
        """Handle database selection changes."""
        import time
        start_time = time.time()
        logger.debug(f"PERF: Database tab received database change to {db_name}")
        
        if not db_name or db_name == "No databases found":
            logger.debug(f"PERF: Empty database name, clearing map")
            # Clear map when no database is selected
            clear_start = time.time()
            self.display_map([])
            clear_end = time.time()
            logger.debug(f"PERF: Map clearing took {(clear_end - clear_start)*1000:.2f}ms")
            return

        try:
            # Database is already open by MainWindow, no need to reopen it
            # Just refresh the UI with the current database
            load_start = time.time()
            self.load_wells()
            load_end = time.time()
            logger.debug(f"PERF: Loading wells and updating map took {(load_end - load_start)*1000:.2f}ms")
            
            total_time = time.time() - start_time
            logger.debug(f"PERF: Total database tab update time: {total_time*1000:.2f}ms")
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"PERF: Error updating UI after {error_time*1000:.2f}ms: {e}")
            # Clear map on error
            self.display_map([])

    def refresh_data(self):
        """Refresh the wells data and map display."""
        logger.debug("Refreshing wells data")
        if self.db_manager and self.db_manager.current_db:
            try:
                self.load_wells()
                return True
            except Exception as e:
                logger.error(f"Error refreshing wells data: {e}")
                return False
        return False

    def on_database_changed(self, db_name):
        """Handle database changes with proper cleanup"""
        logger.debug(f"Database changed to {db_name}")
        if not db_name or db_name == "No databases found":
            # Clear map when no database is selected
            self.display_map([])
            return

        try:
            self.db_manager.open_database(str(self.current_dir / db_name))
            # Clear and refresh map after database change
            self.load_wells()
        except Exception as e:
            logger.error(f"Error changing database: {e}")
            # Clear map on error
            self.display_map([])

    def update_for_screen(self, screen):
        """Update layout for the current screen"""
        try:
            logger.debug(f"Updating DatabaseTab layout for screen: {screen.name()}")
            
            # Calculate appropriate map size based on screen size
            available_size = screen.availableGeometry().size()
            map_min_width = int(available_size.width() * 0.6)
            map_min_height = int(available_size.height() * 0.4)
            
            # Update map view size
            if hasattr(self, 'map_view'):
                self.map_view.setMinimumSize(map_min_width, map_min_height)
                
            # Force layout update
            if self.layout():
                self.layout().update()
                self.layout().activate()
                
            # Refresh the map if it's already loaded
            if hasattr(self, 'current_map_file') and self.current_map_file:
                self.load_wells()
                
        except Exception as e:
            logger.error(f"Error updating DatabaseTab for screen change: {e}")

    def open_data_visualizer(self, well_number):
        """Open the standalone data visualizer app with the selected well pre-selected."""
        try:
            import subprocess
            import json
            import os
            
            # Get the path to the database - make sure it's a string
            db_path = str(self.db_manager.current_db)
            
            # Path to the new visualizer app
            visualizer_path = str(Path(__file__).parent.parent.parent.parent / "tools" / "Visualizer" / "main.py")
            
            # Create a temporary settings file to pass the database path and selected well
            settings_path = str(Path(__file__).parent.parent.parent.parent / "tools" / "Visualizer" / "settings.json")
            
            # Prepare settings with current database path and selected well
            settings = {
                'database_path': db_path,
                'selected_well': well_number if well_number else None
            }
            
            # Save settings
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
            
            logger.debug(f"Launching standalone visualizer with database: {db_path}, well: {well_number}")
            
            # Launch the visualizer as a subprocess
            subprocess.Popen([sys.executable, visualizer_path])
            
        except Exception as e:
            logger.error(f"Error opening standalone visualizer for well {well_number}: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Could not open visualizer: {str(e)}")

    def _select_well_in_visualizer(self, dialog, well_number):
        """Helper to select a specific well in the visualizer's table."""
        try:
            # Find the well in the table
            for row in range(dialog.well_table.rowCount()):
                item = dialog.well_table.item(row, 0)
                if item and item.text() == well_number:
                    # Select this row
                    dialog.well_table.selectRow(row)
                    # Ensure it's visible
                    dialog.well_table.scrollToItem(item)
                    logger.debug(f"Selected well {well_number} in data visualizer")
                    
                    # Set the auto date range to show all data for this well
                    dialog.set_auto_date_range()
                    return True
            
            logger.warning(f"Well {well_number} not found in data visualizer table")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting well in visualizer: {e}")
            return False
