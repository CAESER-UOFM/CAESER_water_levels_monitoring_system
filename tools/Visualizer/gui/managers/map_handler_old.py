import os
import logging
import tempfile
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
import json

logger = logging.getLogger(__name__)

class MapHandler(QObject):
    """Handles map visualization for the water level visualizer."""
    
    # Signals
    map_updated = pyqtSignal()  # Emitted when the map is updated
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = None
        self.arcgis_layer_url = "https://services1.arcgis.com/EX9Lx0EdFAxE7zvX/arcgis/rest/services/MONET/FeatureServer/0"
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def get_widget(self):
        """Get the map widget for adding to the layout."""
        if not self.web_view:
            self.web_view = QWebEngineView()
        return self.web_view
    
    def create_arcgis_map_widget(self, well_locations, selected_wells=None):
        """
        Create an ArcGIS map widget showing well locations with the MONET layer.
        
        Args:
            well_locations (list): List of dictionaries with well information including coordinates
            selected_wells (list): List of selected well numbers to highlight
            
        Returns:
            QWebEngineView: The web view widget containing the map
        """
        try:
            # Create a new web view if one doesn't exist
            if not self.web_view:
                self.web_view = QWebEngineView()
                self.web_view.setMinimumSize(800, 500)
            
            # Create HTML with ArcGIS JavaScript API
            html_content = self._generate_arcgis_html(well_locations, selected_wells)
            
            # Write HTML to a temporary file
            map_file = os.path.join(self.temp_dir.name, "arcgis_map.html")
            with open(map_file, "w") as f:
                f.write(html_content)
            
            # Load the file in the web view
            self.web_view.load(QUrl.fromLocalFile(map_file))
            
            # Signal that the map was updated
            self.map_updated.emit()
            
            return self.web_view
            
        except Exception as e:
            error_msg = f"Error creating ArcGIS map: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def _generate_arcgis_html(self, well_locations, selected_wells=None):
        """
        Generate HTML with ArcGIS JavaScript API to display wells and the MONET layer.
        
        Args:
            well_locations (list): List of dictionaries with well information
            selected_wells (list): List of selected well numbers to highlight
            
        Returns:
            str: HTML content for the map
        """
        # Create GeoJSON for well points
        features = []
        
        for well in well_locations:
            # Skip wells without coordinates
            if 'latitude' not in well or 'longitude' not in well:
                continue
                
            # Skip wells with invalid coordinates
            if not well['latitude'] or not well['longitude']:
                continue
                
            well_number = well.get('well_number', 'Unknown')
            is_selected = selected_wells and well_number in selected_wells
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(well['longitude']), float(well['latitude'])]
                },
                "properties": {
                    "well_number": well_number,
                    "aquifer": well.get('aquifer', 'Unknown'),
                    "cae_number": well.get('cae_number', ''),
                    "is_selected": is_selected
                }
            }
            features.append(feature)
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Create HTML with ArcGIS JavaScript API
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="initial-scale=1, maximum-scale=1, user-scalable=no" />
            <title>ArcGIS Well Map</title>
            <style>
                html, body, #viewDiv {{
                    padding: 0;
                    margin: 0;
                    height: 100%;
                    width: 100%;
                }}
                #info-div {{
                    background-color: white;
                    padding: 10px;
                    border-radius: 5px;
                    position: absolute;
                    bottom: 20px;
                    right: 20px;
                    max-width: 300px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.2);
                    font-size: 12px;
                }}
                .esri-popup__main-container {{
                    max-width: 300px !important;
                }}
            </style>
            <link rel="stylesheet" href="https://js.arcgis.com/4.27/esri/themes/light/main.css">
            <script src="https://js.arcgis.com/4.27/"></script>
            <script>
                // Store the well data in a variable
                const wellData = {json.dumps(geojson_data)};
                
                // Initialize the map
                require([
                    "esri/Map",
                    "esri/views/MapView",
                    "esri/layers/GeoJSONLayer",
                    "esri/layers/FeatureLayer",
                    "esri/widgets/Legend",
                    "esri/widgets/LayerList",
                    "esri/widgets/Home",
                    "esri/widgets/BasemapGallery",
                    "esri/widgets/Expand"
                ], function(Map, MapView, GeoJSONLayer, FeatureLayer, Legend, LayerList, Home, BasemapGallery, Expand) {{
                    
                    // Define the MONET Feature Layer with the provided URL
                    const monetLayer = new FeatureLayer({{
                        url: "{self.arcgis_layer_url}",
                        outFields: ["*"],
                        title: "MONET Layer",
                        opacity: 0.7,
                        popupTemplate: {{
                            title: "MONET Data",
                            content: [
                                {{
                                    type: "fields",
                                    fieldInfos: [
                                        // Add relevant field info from the MONET layer
                                        {{ fieldName: "Name", label: "Name" }},
                                        {{ fieldName: "Description", label: "Description" }}
                                        // Add more fields as needed
                                    ]
                                }}
                            ]
                        }}
                    }});
                    
                    // Render the well points
                    const wellRenderer = {{
                        type: "unique-value",
                        field: "is_selected",
                        defaultSymbol: {{
                            type: "simple-marker",
                            color: [120, 120, 120, 0.8],
                            size: 8,
                            outline: {{
                                color: [50, 50, 50],
                                width: 1
                            }}
                        }},
                        uniqueValueInfos: [
                            {{
                                value: true,
                                symbol: {{
                                    type: "simple-marker",
                                    color: [255, 0, 0, 0.8],
                                    size: 12,
                                    outline: {{
                                        color: [255, 255, 255],
                                        width: 2
                                    }}
                                }}
                            }}
                        ]
                    }};
                    
                    // Create a blob URL for the GeoJSON data
                    const blob = new Blob([JSON.stringify(wellData)], {{ type: "application/json" }});
                    const wellsUrl = URL.createObjectURL(blob);
                    
                    // Create GeoJSON layer for wells
                    const wellsLayer = new GeoJSONLayer({{
                        url: wellsUrl,
                        title: "Wells",
                        renderer: wellRenderer,
                        popupTemplate: {{
                            title: "Well: {well_number}",
                            content: [
                                {{
                                    type: "text",
                                    text: "<b>Well Number:</b> {well_number}<br><b>Aquifer:</b> {aquifer}<br><b>CAE Number:</b> {cae_number}"
                                }}
                            ]
                        }}
                    }});
                    
                    // Create the map
                    const map = new Map({{
                        basemap: "streets-navigation-vector",
                        layers: [monetLayer, wellsLayer]
                    }});
                    
                    // Create the view
                    const view = new MapView({{
                        container: "viewDiv",
                        map: map,
                        zoom: 10
                    }});
                    
                    // Add home button
                    const homeBtn = new Home({{
                        view: view
                    }});
                    view.ui.add(homeBtn, "top-left");
                    
                    // Add basemap gallery in expandable widget
                    const basemapGallery = new BasemapGallery({{
                        view: view
                    }});
                    const bmExpand = new Expand({{
                        view: view,
                        content: basemapGallery,
                        expandIconClass: "esri-icon-basemap"
                    }});
                    view.ui.add(bmExpand, "top-right");
                    
                    // Add layer list in expandable widget
                    const layerList = new LayerList({{
                        view: view
                    }});
                    const layerListExpand = new Expand({{
                        view: view,
                        content: layerList,
                        expandIconClass: "esri-icon-layer-list"
                    }});
                    view.ui.add(layerListExpand, {{
                        position: "top-right"
                    }});
                    
                    // Add legend
                    const legend = new Legend({{
                        view: view
                    }});
                    const legendExpand = new Expand({{
                        view: view,
                        content: legend,
                        expandIconClass: "esri-icon-legend"
                    }});
                    view.ui.add(legendExpand, "bottom-left");
                    
                    // Add info div
                    const infoDiv = document.createElement("div");
                    infoDiv.id = "info-div";
                    infoDiv.innerHTML = "<h3>Map Information</h3>" +
                        "<p>Red markers: Selected wells<br>Gray markers: Available wells</p>" +
                        "<p>Click on layers icon to toggle visibility</p>";
                    view.ui.add(infoDiv, "bottom-right");
                    
                    // Zoom to wells extent when all layers are loaded
                    Promise.all([wellsLayer.load(), monetLayer.load()]).then(function() {{
                        // Zoom to wells layer if there are wells
                        if (wellsLayer.graphics.length > 0) {{
                            view.goTo(wellsLayer.fullExtent);
                        }} else {{
                            // Otherwise zoom to MONET layer
                            view.goTo(monetLayer.fullExtent);
                        }}
                    }});
                }});
            </script>
        </head>
        <body>
            <div id="viewDiv"></div>
        </body>
        </html>
        '''
        
        return html
    
    def create_map(self, well_locations, selected_wells=None):
        """
        Fallback method to create a map file using alternative mapping library.
        This can serve as a backup implementation using folium or other libraries.
        
        Args:
            well_locations (list): List of dictionaries with well information
            selected_wells (list): List of selected well numbers
            
        Returns:
            str: Path to the generated map HTML file
        """
        try:
            # Try using the ArcGIS implementation first
            if self.create_arcgis_map_widget(well_locations, selected_wells):
                map_file = os.path.join(self.temp_dir.name, "arcgis_map.html")
                return map_file
                
            # Import folium for fallback map creation
            import folium
            from folium.plugins import MarkerCluster
            
            # Create a map centered on the first well with coordinates
            center_lat, center_lon = 35.1495, -90.0490  # Default to Memphis
            
            # Find a well with valid coordinates to center the map
            for well in well_locations:
                if 'latitude' in well and 'longitude' in well and well['latitude'] and well['longitude']:
                    center_lat = float(well['latitude'])
                    center_lon = float(well['longitude'])
                    break
            
            # Create map
            m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
            
            # Add marker cluster
            marker_cluster = MarkerCluster().add_to(m)
            
            # Add wells to map
            for well in well_locations:
                if 'latitude' not in well or 'longitude' not in well:
                    continue
                    
                if not well['latitude'] or not well['longitude']:
                    continue
                    
                well_number = well.get('well_number', 'Unknown')
                aquifer = well.get('aquifer', 'Unknown')
                cae_number = well.get('cae_number', '')
                
                # Determine marker color based on selection
                color = 'red' if selected_wells and well_number in selected_wells else 'gray'
                
                # Create popup content
                popup_html = f"""
                <div style="min-width: 200px;">
                    <h4>Well: {well_number}</h4>
                    <b>Aquifer:</b> {aquifer}<br>
                    <b>CAE Number:</b> {cae_number}<br>
                </div>
                """
                
                # Add marker
                folium.Marker(
                    location=[float(well['latitude']), float(well['longitude'])],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=well_number,
                    icon=folium.Icon(color=color, icon='info-sign')
                ).add_to(marker_cluster)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Save to file
            map_file = os.path.join(self.temp_dir.name, "well_map.html")
            m.save(map_file)
            
            return map_file
            
        except Exception as e:
            error_msg = f"Error creating map: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def cleanup(self):
        """Clean up temporary files and resources."""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir:
                self.temp_dir.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up map resources: {e}") 