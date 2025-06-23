import os
import logging
import tempfile
import time
import sqlite3
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
from folium import Map, Marker, Icon

logger = logging.getLogger(__name__)

class MapHandler(QObject):
    """Handles map visualization for the water level visualizer using folium."""
    
    # Signals
    map_updated = pyqtSignal()  # Emitted when the map is updated
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    well_selected = pyqtSignal(str)  # Emitted when a well is clicked on the map
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = None
        self.current_map_file = None
        self.parent = parent  # Store reference to parent for data access
        self.polling_timer = None
        
    def get_widget(self):
        """Get the map widget for adding to the layout."""
        if not self.web_view:
            self.web_view = QWebEngineView()
            self.web_view.setMinimumSize(800, 500)
        return self.web_view
    
    def update_map(self, selected_wells=None):
        """Update the map with current database data and selected wells."""
        try:
            start_time = time.time()
            logger.debug(f"Starting map update with selected wells: {selected_wells}")
            
            # Get database connection from parent's data manager
            if not hasattr(self.parent, 'data_manager'):
                logger.error("Parent does not have data_manager")
                return
                
            db_path = self.parent.data_manager.db_path
            
            # Get well locations from database
            well_locations = self._get_well_locations(db_path)
            
            if not well_locations:
                logger.warning("No well locations found in database")
                self._show_empty_map()
                return
            
            # Display the map
            self._display_map(well_locations, selected_wells)
            
            total_time = time.time() - start_time
            logger.debug(f"Map update completed in {total_time*1000:.2f}ms")
            
        except Exception as e:
            error_msg = f"Error updating map: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
    
    def _get_well_locations(self, db_path):
        """Fetch well locations and statistics from the database."""
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Try to get well statistics including baro and level status
                cursor.execute("""
                    SELECT w.well_number, w.cae_number, w.latitude, w.longitude,
                           w.aquifer, w.baro_status, w.level_status,
                           ws.num_points, ws.min_timestamp, ws.max_timestamp
                    FROM wells w
                    LEFT JOIN well_statistics ws ON w.well_number = ws.well_number
                    WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
                """)
                
                well_stats = cursor.fetchall()
                return [dict(row) for row in well_stats]
                
        except Exception as e:
            logger.error(f"Error fetching well locations: {e}")
            # Try fallback query without statistics
            try:
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT well_number, cae_number, latitude, longitude, aquifer
                        FROM wells
                        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                    """)
                    wells = cursor.fetchall()
                    return [dict(row) for row in wells]
            except Exception as inner_e:
                logger.error(f"Fallback query also failed: {inner_e}")
                return []
    
    def _display_map(self, well_locations, selected_wells=None):
        """Display the folium map with well markers."""
        try:
            # Clean up previous map file
            self._cleanup_previous_map()
            
            # Create folium map
            m = Map(
                location=[35.1495, -90.0490],  # Default center
                zoom_start=10,
                prefer_canvas=True
            )
            
            if well_locations:
                # Get bounds for all wells
                lats = [w['latitude'] for w in well_locations]
                lons = [w['longitude'] for w in well_locations]
                
                # Add markers for each well
                for well in well_locations:
                    well_number = well['well_number']
                    lat = well['latitude']
                    lon = well['longitude']
                    
                    # Determine if this well is selected
                    is_selected = selected_wells and well_number in selected_wells
                    
                    # Determine marker color based on data status
                    baro_status = well.get('baro_status', 'no_data')
                    level_status = well.get('level_status', 'no_data')
                    num_points = well.get('num_points', 0) or 0  # Handle None values
                    
                    if is_selected:
                        marker_color = 'red'  # Selected wells are always red
                    elif baro_status == 'all_master' and level_status == 'no_default':
                        marker_color = 'green'  # All good
                    elif baro_status == 'has_non_master' and level_status == 'default_level':
                        marker_color = 'darkred'  # Both flags have issues
                    elif baro_status == 'has_non_master':
                        marker_color = 'orange'  # Baro issue
                    elif level_status == 'default_level':
                        marker_color = 'purple'  # Level issue
                    elif num_points > 0:
                        marker_color = 'blue'  # Has data
                    else:
                        marker_color = 'gray'  # No data
                    
                    # Create popup content
                    cae_number = well.get('cae_number', 'N/A')
                    aquifer = well.get('aquifer', 'Unknown')
                    min_ts = well.get('min_timestamp', 'N/A')
                    max_ts = well.get('max_timestamp', 'N/A')
                    data_status = 'Has Data' if num_points and num_points > 0 else 'No Data'
                    date_range = f"{min_ts} to {max_ts}" if num_points and num_points > 0 else 'N/A'
                    
                    popup_content = f"""
                    <b>Well:</b> {well_number}<br>
                    <b>CAE:</b> {cae_number}<br>
                    <b>Aquifer:</b> {aquifer}<br>
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
                                Select Well
                            </a>
                        </div>
                    """
                    
                    Marker(
                        [lat, lon], 
                        popup=popup_html, 
                        icon=Icon(color=marker_color),
                        tooltip=f"Well: {well_number}"
                    ).add_to(m)
                
                # Fit bounds to show all markers
                if len(well_locations) == 1:
                    m.location = [lats[0], lons[0]]
                    m.zoom_start = 13
                else:
                    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
            
            # Save to temp file
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            temp_map_path = os.path.join(temp_dir, f"visualizer_map_{timestamp}.html")
            m.save(temp_map_path)
            
            # Inject JavaScript for well selection handling
            with open(temp_map_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            injection_script = """
            <script>
            // Global variable to store selected well
            window.selectedWellNumber = null;
            
            // Function called by Qt to check if a well was selected
            function checkSelectedWell() {
                var selected = window.selectedWellNumber;
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
            
            html_content = html_content.replace("</body>", injection_script)
            
            with open(temp_map_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Store current map file path
            self.current_map_file = temp_map_path
            
            # Load the map in the web view
            if not self.web_view:
                self.web_view = QWebEngineView()
                self.web_view.setMinimumSize(800, 500)
            
            # Connect to loadFinished signal
            try:
                self.web_view.loadFinished.disconnect()
            except TypeError:
                pass
            
            self.web_view.loadFinished.connect(self._on_map_loaded)
            self.web_view.setUrl(QUrl.fromLocalFile(temp_map_path))
            
            # Emit signal that map was updated
            self.map_updated.emit()
            
        except Exception as e:
            logger.error(f"Error displaying map: {e}", exc_info=True)
            self._show_error_map(str(e))
    
    def _on_map_loaded(self, ok):
        """Handle map load completion."""
        if ok:
            logger.debug("Map loaded successfully")
            self._setup_map_polling()
            try:
                self.web_view.loadFinished.disconnect(self._on_map_loaded)
            except TypeError:
                pass
        else:
            logger.warning("Map failed to load")
    
    def _setup_map_polling(self):
        """Set up polling for well selection."""
        try:
            # Check if JavaScript function is available
            self.web_view.page().runJavaScript(
                "typeof checkSelectedWell === 'function'",
                self._check_well_selection_function
            )
            
            # Create or restart polling timer
            if not self.polling_timer:
                self.polling_timer = QTimer(self)
                self.polling_timer.setInterval(500)  # Check every 500ms
                self.polling_timer.timeout.connect(self._poll_for_well_selection)
            
            self.polling_timer.start()
            logger.debug("Map polling started")
            
        except Exception as e:
            logger.error(f"Error setting up map polling: {e}")
    
    def _poll_for_well_selection(self):
        """Poll the map for well selection."""
        try:
            self.web_view.page().runJavaScript(
                "checkSelectedWell()",
                self._handle_well_selection
            )
        except Exception as e:
            logger.error(f"Error polling for well selection: {e}")
    
    def _check_well_selection_function(self, function_exists):
        """Check if the well selection function exists."""
        if not function_exists:
            logger.warning("checkSelectedWell function not found, injecting it")
            try:
                self.web_view.page().runJavaScript("""
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
            except Exception as e:
                logger.error(f"Error injecting JavaScript: {e}")
    
    def _handle_well_selection(self, well_number):
        """Handle well selection from JavaScript."""
        if well_number and well_number.strip():
            logger.debug(f"Well selected from map: {well_number}")
            # Emit signal that a well was selected
            self.well_selected.emit(well_number)
    
    def _cleanup_previous_map(self):
        """Clean up previous map file."""
        if self.current_map_file and os.path.exists(self.current_map_file):
            try:
                os.unlink(self.current_map_file)
            except (PermissionError, OSError) as e:
                logger.debug(f"Could not remove old map file: {e}")
    
    def _show_empty_map(self):
        """Show a map with no wells message."""
        try:
            m = Map(location=[35.1495, -90.0490], zoom_start=10)
            Marker(
                location=[35.1495, -90.0490],
                popup="No wells with coordinates found in database",
                icon=Icon(color='red')
            ).add_to(m)
            
            temp_dir = tempfile.gettempdir()
            temp_map_path = os.path.join(temp_dir, f"empty_map_{int(time.time())}.html")
            m.save(temp_map_path)
            
            self.current_map_file = temp_map_path
            
            if not self.web_view:
                self.web_view = QWebEngineView()
            
            self.web_view.setUrl(QUrl.fromLocalFile(temp_map_path))
            
        except Exception as e:
            logger.error(f"Error showing empty map: {e}")
    
    def _show_error_map(self, error_message):
        """Show error message in the map view."""
        if not self.web_view:
            self.web_view = QWebEngineView()
        
        self.web_view.setHtml(
            f"<h3 style='color: red; text-align: center;'>"
            f"Error loading map: {error_message}"
            "</h3>"
        )
    
    def cleanup(self):
        """Clean up resources."""
        self._cleanup_previous_map()
        
        # Stop polling timer
        if self.polling_timer and self.polling_timer.isActive():
            self.polling_timer.stop()
    
    # Compatibility methods for existing interface
    def create_arcgis_map_widget(self, well_locations, selected_wells=None):
        """Compatibility method - redirects to update_map."""
        # Convert well_locations list to match expected format
        formatted_locations = []
        for well in well_locations:
            if isinstance(well, dict):
                formatted_locations.append(well)
            else:
                # Assume it's a tuple or list with basic info
                formatted_locations.append({
                    'well_number': well.get('well_number', 'Unknown'),
                    'latitude': well.get('latitude'),
                    'longitude': well.get('longitude'),
                    'aquifer': well.get('aquifer', 'Unknown'),
                    'cae_number': well.get('cae_number', '')
                })
        
        self._display_map(formatted_locations, selected_wells)
        return self.web_view
    
    def create_map(self, well_locations, selected_wells=None):
        """Compatibility method - creates map and returns file path."""
        self.create_arcgis_map_widget(well_locations, selected_wells)
        return self.current_map_file