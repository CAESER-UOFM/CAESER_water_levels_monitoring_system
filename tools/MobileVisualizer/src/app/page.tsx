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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-blue-900">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-8">
            {/* CAESER Mascot with breathing animation */}
            <div className="w-32 h-32 rounded-full flex items-center justify-center shadow-2xl mr-8 overflow-hidden bg-white animate-pulse-gentle">
              <img 
                src="/caeser-mascot.png" 
                alt="CAESER Mascot"
                className="w-full h-full object-cover"
              />
            </div>
            
            <div className="text-left">
              <h1 className="text-5xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent mb-4">
                CAESER
              </h1>
              <h2 className="text-3xl font-bold text-white mb-2">
                Water Levels Visualizer
              </h2>
              <p className="text-xl text-gray-300 max-w-2xl">
                Mobile-optimized groundwater monitoring platform from the CAESER research database
              </p>
            </div>
          </div>
          
          <div className="flex items-center justify-center space-x-2 text-gray-400 mb-8">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium">Advanced Hydrological Analysis Platform</span>
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          {/* Database Connection Status */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white flex items-center">
                <svg className="w-6 h-6 mr-3 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
                Database Connection
              </h2>
              <span className={`text-sm px-3 py-1 rounded-full font-medium ${
                loading ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-600' :
                error ? 'bg-red-900/50 text-red-300 border border-red-600' :
                'bg-green-900/50 text-green-300 border border-green-600'
              }`}>
                {loading ? 'Connecting...' : error ? 'Error' : 'Connected'}
              </span>
            </div>
            
            {loading && (
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-400"></div>
                <span className="text-gray-300">Establishing secure connection...</span>
              </div>
            )}
            
            {error && (
              <div className="bg-red-900/30 border border-red-600 rounded-lg p-4">
                <p className="text-red-300">Connection Error: {error}</p>
              </div>
            )}
            
            {!loading && !error && (
              <DatabaseSelector
                databases={databases}
                onDatabaseSelected={handleDatabaseSelected}
              />
            )}
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gray-800/30 backdrop-blur-sm border border-gray-600 rounded-xl p-6 text-center">
              <div className="text-3xl font-bold text-cyan-400 mb-2">44+</div>
              <div className="text-gray-300">Monitoring Wells</div>
            </div>
            <div className="bg-gray-800/30 backdrop-blur-sm border border-gray-600 rounded-xl p-6 text-center">
              <div className="text-3xl font-bold text-blue-400 mb-2">4.9M+</div>
              <div className="text-gray-300">Water Level Readings</div>
            </div>
            <div className="bg-gray-800/30 backdrop-blur-sm border border-gray-600 rounded-xl p-6 text-center">
              <div className="text-3xl font-bold text-indigo-400 mb-2">3</div>
              <div className="text-gray-300">Aquifer Types</div>
            </div>
          </div>

          {/* Features Grid - 60% smaller */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-gradient-to-br from-blue-900/50 to-blue-800/30 backdrop-blur-sm border border-blue-700 rounded-lg p-3 hover:border-blue-500 transition-all duration-300 transform hover:scale-105">
              <div className="flex items-center justify-center w-8 h-8 bg-blue-500/20 rounded-lg mb-2">
                <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="font-semibold text-white mb-1 text-sm">Interactive Charts</h3>
              <p className="text-xs text-gray-300">Touch-optimized visualization</p>
            </div>

            <div className="bg-gradient-to-br from-green-900/50 to-green-800/30 backdrop-blur-sm border border-green-700 rounded-lg p-3 hover:border-green-500 transition-all duration-300 transform hover:scale-105">
              <div className="flex items-center justify-center w-8 h-8 bg-green-500/20 rounded-lg mb-2">
                <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </div>
              <h3 className="font-semibold text-white mb-1 text-sm">Data Export</h3>
              <p className="text-xs text-gray-300">CSV & JSON formats</p>
            </div>

            <div className="bg-gradient-to-br from-purple-900/50 to-purple-800/30 backdrop-blur-sm border border-purple-700 rounded-lg p-3 hover:border-purple-500 transition-all duration-300 transform hover:scale-105">
              <div className="flex items-center justify-center w-8 h-8 bg-purple-500/20 rounded-lg mb-2">
                <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-white mb-1 text-sm">Well Browser</h3>
              <p className="text-xs text-gray-300">Search & filter wells</p>
            </div>

            <div className="bg-gradient-to-br from-orange-900/50 to-orange-800/30 backdrop-blur-sm border border-orange-700 rounded-lg p-3 hover:border-orange-500 transition-all duration-300 transform hover:scale-105">
              <div className="flex items-center justify-center w-8 h-8 bg-orange-500/20 rounded-lg mb-2">
                <svg className="w-4 h-4 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="font-semibold text-white mb-1 text-sm">Recharge Analysis</h3>
              <p className="text-xs text-gray-300">RISE & MRC calculations</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-12 pt-8 border-t border-gray-700">
          <p className="text-gray-400 text-sm">
            University of Memphis • CAESER Research Group • Advanced Hydrological Monitoring
          </p>
        </div>
      </div>
    </div>
  );
}