'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { LoadingSpinner } from '@/components/LoadingSpinner';

// Dynamic import to avoid SSR issues with Leaflet
const WellsMap = dynamic(() => import('@/components/WellsMap'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center">
      <LoadingSpinner size="large" />
    </div>
  )
});

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

export default function MapPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;
  const highlightWell = params.highlight as string || null;

  const [wells, setWells] = useState<WellLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAquifer, setSelectedAquifer] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const loadWellLocations = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/.netlify/functions/wells-locations?databaseId=${databaseId}`);
        const result = await response.json();

        if (!result.success) {
          throw new Error(result.error || 'Failed to load well locations');
        }

        setWells(result.data || []);
      } catch (err) {
        console.error('Error loading well locations:', err);
        setError(err instanceof Error ? err.message : 'Failed to load well locations');
      } finally {
        setLoading(false);
      }
    };

    loadWellLocations();
  }, [databaseId]);

  const handleBackToWells = () => {
    router.push(`/wells/${databaseId}`);
  };

  const handleWellClick = (wellNumber: string) => {
    router.push(`/wells/${databaseId}/plot/${wellNumber}`);
  };

  // Filter wells based on search and aquifer
  const filteredWells = wells.filter(well => {
    const matchesSearch = searchTerm === '' || 
      well.well_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      well.cae_number.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesAquifer = selectedAquifer === 'all' || well.aquifer === selectedAquifer;
    
    return matchesSearch && matchesAquifer;
  });

  // Get unique aquifers for filter
  const uniqueAquifers = Array.from(new Set(wells.map(w => w.aquifer))).filter(Boolean).sort();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Loading well locations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <svg className="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Map</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-3">
            <button onClick={handleBackToWells} className="btn-secondary">
              ← Back to Wells
            </button>
            <button onClick={() => window.location.reload()} className="btn-primary">
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleBackToWells}
                className="p-2 text-gray-600 hover:text-gray-900 transition-colors mobile-touch-target"
                title="Back to wells"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Wells Map</h1>
                <p className="text-sm text-gray-600">{filteredWells.length} of {wells.length} wells</p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center space-x-3">
              <button
                onClick={handleBackToWells}
                className="btn-outline text-sm px-3 py-2"
              >
                View List
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="mt-4 flex flex-col md:flex-row gap-3">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search wells..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div className="md:w-48">
              <select
                value={selectedAquifer}
                onChange={(e) => setSelectedAquifer(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All Aquifers</option>
                {uniqueAquifers.map(aquifer => (
                  <option key={aquifer} value={aquifer}>{aquifer}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        {wells.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Well Locations</h3>
              <p className="text-gray-600">No wells with coordinate data found in this database.</p>
            </div>
          </div>
        ) : (
          <WellsMap
            wells={filteredWells}
            highlightWell={highlightWell}
            onWellClick={handleWellClick}
            databaseId={databaseId}
          />
        )}
      </div>

      {/* Legend */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="container mx-auto">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Legend</h3>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span>Has Data</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span>Limited Data</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-gray-400"></div>
              <span>No Data</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span>Highlighted</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}