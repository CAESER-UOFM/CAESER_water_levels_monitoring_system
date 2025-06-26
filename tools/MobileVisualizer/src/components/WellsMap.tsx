'use client';

import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css';
import 'leaflet-defaulticon-compatibility';

interface WellLocation {
  well_number: string;
  cae_number: string;
  latitude: number;
  longitude: number;
  aquifer: string;
  well_field: string;
  cluster: string;
  ground_elevation?: number;
  well_depth?: number;
  static_water_level?: number;
  last_reading_date?: string;
  total_readings: number;
  data_status: 'transducer' | 'telemetry' | 'manual' | 'no_data';
  status: 'has_data' | 'limited_data' | 'no_data';
  has_manual_readings: boolean;
  has_transducer_data: boolean;
  has_telemetry_data: boolean;
  notes: string;
}

interface WellsMapProps {
  wells: WellLocation[];
  highlightWell?: string | null;
  onWellClick: (wellNumber: string) => void;
  databaseId: string;
}

// Create custom icons for different statuses
const createWellIcon = (status: string, isHighlighted: boolean = false) => {
  let color = '#6b7280'; // gray-500 default
  
  if (isHighlighted) {
    color = '#ef4444'; // red-500
  } else {
    switch (status) {
      case 'has_data':
        color = '#22c55e'; // green-500
        break;
      case 'limited_data':
        color = '#3b82f6'; // blue-500
        break;
      case 'no_data':
        color = '#6b7280'; // gray-500
        break;
      default:
        color = '#6b7280';
    }
  }

  return new L.Icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(`
      <svg width="25" height="41" viewBox="0 0 25 41" xmlns="http://www.w3.org/2000/svg">
        <path fill="${color}" stroke="#ffffff" stroke-width="2" d="M12.5 0C5.596 0 0 5.596 0 12.5c0 12.5 12.5 28.5 12.5 28.5S25 25 25 12.5C25 5.596 19.404 0 12.5 0z"/>
        <circle cx="12.5" cy="12.5" r="6" fill="#ffffff"/>
      </svg>
    `)}`,
    iconSize: [25, 41],
    iconAnchor: [12.5, 41],
    popupAnchor: [0, -41],
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    shadowSize: [41, 41],
    shadowAnchor: [13, 41]
  });
};

// Component to handle map bounds fitting
function MapBounds({ wells, highlightWell }: { wells: WellLocation[]; highlightWell?: string | null }) {
  const map = useMap();

  useEffect(() => {
    if (wells.length === 0) return;

    if (wells.length === 1) {
      // Single well: center on it
      const well = wells[0];
      map.setView([well.latitude, well.longitude], 13);
    } else {
      // Multiple wells: fit bounds
      const bounds = L.latLngBounds(wells.map(well => [well.latitude, well.longitude]));
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [map, wells]);

  // Highlight specific well if provided
  useEffect(() => {
    if (highlightWell && wells.length > 0) {
      const well = wells.find(w => w.well_number === highlightWell);
      if (well) {
        map.setView([well.latitude, well.longitude], 13);
      }
    }
  }, [map, wells, highlightWell]);

  return null;
}

export default function WellsMap({ wells, highlightWell, onWellClick, databaseId }: WellsMapProps) {
  const mapRef = useRef<L.Map | null>(null);

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'No data';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Invalid date';
    }
  };

  const getDataStatusText = (well: WellLocation): string => {
    const sources = [];
    if (well.has_transducer_data) sources.push('Transducer');
    if (well.has_telemetry_data) sources.push('Telemetry');
    if (well.has_manual_readings) sources.push('Manual');
    
    return sources.length > 0 ? sources.join(', ') : 'No data';
  };

  // Memphis area center (matching desktop implementation)
  const center: [number, number] = [35.1495, -90.0490];

  return (
    <div className="h-full w-full">
      <MapContainer
        center={center}
        zoom={10}
        style={{ height: '100%', width: '100%' }}
        ref={mapRef}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <MapBounds wells={wells} highlightWell={highlightWell} />

        {wells.map((well) => {
          const isHighlighted = highlightWell === well.well_number;
          
          return (
            <Marker
              key={well.well_number}
              position={[well.latitude, well.longitude]}
              icon={createWellIcon(well.status, isHighlighted)}
              eventHandlers={{
                click: () => onWellClick(well.well_number)
              }}
            >
              <Popup>
                <div className="p-2 min-w-[250px]">
                  <div className="mb-3">
                    <h3 className="font-semibold text-lg text-gray-900">
                      Well {well.well_number}
                    </h3>
                    {well.cae_number && (
                      <p className="text-sm text-gray-600">CAE: {well.cae_number}</p>
                    )}
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="font-medium text-gray-700">Aquifer:</span>
                        <p className="text-gray-600">{well.aquifer || 'Unknown'}</p>
                      </div>
                      {well.well_field && (
                        <div>
                          <span className="font-medium text-gray-700">Field:</span>
                          <p className="text-gray-600">{well.well_field}</p>
                        </div>
                      )}
                    </div>

                    <div>
                      <span className="font-medium text-gray-700">Data Sources:</span>
                      <p className="text-gray-600">{getDataStatusText(well)}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="font-medium text-gray-700">Total Readings:</span>
                        <p className="text-gray-600">{well.total_readings.toLocaleString()}</p>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Last Reading:</span>
                        <p className="text-gray-600">{formatDate(well.last_reading_date)}</p>
                      </div>
                    </div>

                    {well.ground_elevation && (
                      <div>
                        <span className="font-medium text-gray-700">Ground Elevation:</span>
                        <p className="text-gray-600">{well.ground_elevation.toFixed(2)} ft</p>
                      </div>
                    )}

                    {well.well_depth && (
                      <div>
                        <span className="font-medium text-gray-700">Well Depth:</span>
                        <p className="text-gray-600">{well.well_depth.toFixed(2)} ft</p>
                      </div>
                    )}

                    {well.static_water_level && (
                      <div>
                        <span className="font-medium text-gray-700">Static Water Level:</span>
                        <p className="text-gray-600">{well.static_water_level.toFixed(2)} ft</p>
                      </div>
                    )}

                    {well.notes && (
                      <div>
                        <span className="font-medium text-gray-700">Notes:</span>
                        <p className="text-gray-600 text-xs">{well.notes}</p>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-200">
                    <button
                      onClick={() => onWellClick(well.well_number)}
                      className="w-full bg-primary-600 text-white px-3 py-2 rounded-md text-sm font-medium hover:bg-primary-700 transition-colors"
                    >
                      View Plot Data
                    </button>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}