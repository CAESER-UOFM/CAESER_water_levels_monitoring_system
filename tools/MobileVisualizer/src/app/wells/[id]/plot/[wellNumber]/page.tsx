'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { SmartWaterLevelChart } from '@/components/SmartWaterLevelChart';
import { WellInfoPanel } from '@/components/WellInfoPanel';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { Well } from '@/lib/api/api';

export default function PlotViewerPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;
  const wellNumber = params.wellNumber as string;

  const [well, setWell] = useState<Well | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [currentTimeRange, setCurrentTimeRange] = useState<{ start: string; end: string } | null>(null);
  const chartRef = useRef<{ switchToDailyOverview: () => void; resetZoom: () => void; isZoomed: boolean } | null>(null);
  const [chartInfo, setChartInfo] = useState<{ 
    totalPoints: number; 
    displayedPoints: number; 
    samplingRate: string;
    dataRange: { start: string; end: string } | null;
    isHighRes: boolean;
  }>({ 
    totalPoints: 0, 
    displayedPoints: 0, 
    samplingRate: 'Loading...',
    dataRange: null,
    isHighRes: false
  });

  // Handle chart info updates - stable callback
  const updateChartInfo = useCallback((info: typeof chartInfo) => {
    setChartInfo(info);
    if (info.dataRange) {
      setCurrentTimeRange(info.dataRange);
    }
  }, []);

  // Load well data and initial overview
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        setError(null);
        

        // Load well metadata
        const wellResponse = await fetch(`/.netlify/functions/wells/${databaseId}/${wellNumber}`);
        const wellResult = await wellResponse.json();
        
        if (!wellResult.success) {
          throw new Error(wellResult.error || 'Well not found');
        }
        setWell(wellResult.data);

      } catch (err) {
        console.error('Error loading initial data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load well data');
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, [databaseId, wellNumber]);


  // Close export menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showExportMenu) {
        const target = event.target as Element;
        if (!target.closest('.relative')) {
          setShowExportMenu(false);
        }
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showExportMenu]);



  const handleBackToWells = useCallback(() => {
    router.push(`/wells/${databaseId}`);
  }, [databaseId, router]);

  const handleExportData = useCallback(() => {
    setShowExportMenu(prev => !prev);
  }, []);

  const handleExportCSV = useCallback(async () => {
    alert('Export functionality will be implemented with the new chart system.');
    setShowExportMenu(false);
  }, []);

  const handleExportJSON = useCallback(async () => {
    alert('Export functionality will be implemented with the new chart system.');
    setShowExportMenu(false);
  }, []);

  const handleViewRecharge = useCallback(() => {
    router.push(`/wells/${databaseId}/recharge/${wellNumber}`);
  }, [databaseId, wellNumber, router]);

  if (loading && !well) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Loading well data...</p>
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
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            Error Loading Data
          </h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-3">
            <button
              onClick={handleBackToWells}
              className="btn-secondary"
            >
              ← Back to Wells
            </button>
            <button
              onClick={() => window.location.reload()}
              className="btn-primary"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!well) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
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
                <h1 className="text-xl font-semibold text-gray-900">
                  Well {well.well_number}
                </h1>
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleViewRecharge}
                className="btn-outline text-sm px-3 py-2"
                title="View recharge calculations"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <span className="hidden sm:inline">Recharge</span>
              </button>
              
              {/* Export Dropdown */}
              <div className="relative">
                <button
                  onClick={handleExportData}
                  className="btn-primary text-sm px-3 py-2"
                  title="Export data"
                  disabled={false}
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span className="hidden sm:inline">Export</span>
                  <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {showExportMenu && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-20">
                    <div className="py-1">
                      <button
                        onClick={handleExportCSV}
                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <span className="mr-2">📊</span>
                        Export as CSV
                      </button>
                      <button
                        onClick={handleExportJSON}
                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <span className="mr-2">📋</span>
                        Export as JSON
                      </button>
                      <div className="border-t border-gray-100 my-1"></div>
                      <div className="px-4 py-2 text-xs text-gray-500">
                        Smart chart export coming soon
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Well Information Panel - Top */}
        <WellInfoPanel
          well={well}
          currentTimeRange={currentTimeRange}
          totalPoints={chartInfo.totalPoints}
          displayedPoints={chartInfo.displayedPoints}
          samplingRate={chartInfo.samplingRate}
        />


        {/* Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex-1"></div>
            <h2 className="text-lg font-semibold text-gray-900">
              Water Level Data
            </h2>
            <div className="flex-1 flex justify-end">
              <div className="flex items-center space-x-2">
              {/* Back to Overview button - always visible, goes to full daily view */}
              <button
                onClick={() => {
                  if (chartRef.current) {
                    chartRef.current.switchToDailyOverview();
                  }
                  // Also reset zoom
                  if ((window as any).chartResetZoom) {
                    (window as any).chartResetZoom();
                  }
                }}
                disabled={loading}
                className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded hover:bg-blue-200 disabled:opacity-50 transition-colors"
              >
                Back to Overview
              </button>
              {/* Reset Zoom button - only when high-res data loaded */}
              {chartInfo.isHighRes && (
                <button
                  onClick={() => {
                    if ((window as any).chartResetZoom) {
                      (window as any).chartResetZoom();
                    }
                  }}
                  disabled={loading}
                  className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200 disabled:opacity-50 transition-colors"
                >
                  Reset Zoom
                </button>
              )}
              {/* Loading indicator */}
              {loading && (
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <LoadingSpinner size="small" />
                  <span>Updating...</span>
                </div>
              )}
              </div>
            </div>
          </div>
          
          <SmartWaterLevelChart
            ref={chartRef}
            databaseId={databaseId}
            wellNumber={wellNumber}
            title=""
            height={400}
            onError={(error) => setError(error)}
            onInfoUpdate={updateChartInfo}
          />
        </div>

      </div>
    </div>
  );
}