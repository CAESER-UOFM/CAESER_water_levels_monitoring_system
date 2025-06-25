'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { DatabaseSelector } from '@/components/DatabaseSelector';
import type { DatabaseInfo } from '@/types/database';

export default function HomePage() {
  const router = useRouter();
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch databases from API
  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        setLoading(true);
        const response = await fetch('/.netlify/functions/databases');
        const data = await response.json();
        
        if (data.success) {
          setDatabases(data.data);
        } else {
          setError(data.error || 'Failed to fetch databases');
        }
      } catch (err) {
        setError('Failed to connect to database');
        console.error('Error fetching databases:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDatabases();
  }, []);

  const handleDatabaseSelected = useCallback((database: DatabaseInfo) => {
    // Navigate to wells page
    router.push(`/wells/${database.id}`);
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            CAESER Water Levels Visualizer
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Mobile-optimized visualization of groundwater monitoring data from the CAESER research database.
          </p>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          {/* Database Connection Status */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                Database Connection
              </h2>
              <span className={`text-sm px-2 py-1 rounded ${
                loading ? 'bg-yellow-100 text-yellow-800' :
                error ? 'bg-red-100 text-red-800' :
                'bg-green-100 text-green-800'
              }`}>
                {loading ? 'Connecting...' : error ? 'Error' : 'Connected'}
              </span>
            </div>
            
            {loading && (
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <span className="text-gray-600">Connecting to database...</span>
              </div>
            )}
            
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800">Error: {error}</p>
              </div>
            )}
            
            {!loading && !error && (
              <DatabaseSelector
                databases={databases}
                onDatabaseSelected={handleDatabaseSelected}
              />
            )}
          </div>


          {/* Quick Access Features */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg mb-3">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Interactive Charts</h3>
              <p className="text-xs text-gray-600">Touch-optimized visualization with zoom and filtering</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4 hover:border-green-300 transition-colors">
              <div className="flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg mb-3">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Data Export</h3>
              <p className="text-xs text-gray-600">Download data in CSV or JSON formats</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4 hover:border-purple-300 transition-colors">
              <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg mb-3">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Well Browser</h3>
              <p className="text-xs text-gray-600">Search and filter 44+ monitoring wells</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4 hover:border-orange-300 transition-colors">
              <div className="flex items-center justify-center w-10 h-10 bg-orange-100 rounded-lg mb-3">
                <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Recharge Analysis</h3>
              <p className="text-xs text-gray-600">Access RISE, MRC, and ERC calculations</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}