'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { WaterLevelChart } from '@/components/WaterLevelChart';
import { ChartControls } from '@/components/ChartControls';
import { ChartControlsPanel } from '@/components/ChartControlsPanel';
import { WellInfoPanel } from '@/components/WellInfoPanel';
import { DataStatisticsPanel } from '@/components/DataStatisticsPanel';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useProgressiveLoading } from '@/hooks/useProgressiveLoading';
import { exportWaterLevelDataToCSV, exportWaterLevelDataToJSON, filterDataForExport } from '@/utils/dataExport';
import type { Well, WaterLevelReading } from '@/lib/api/api';
import type { PlotConfig } from '@/types/database';

export default function PlotViewerPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;
  const wellNumber = params.wellNumber as string;

  const [well, setWell] = useState<Well | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isChartControlsCollapsed, setIsChartControlsCollapsed] = useState(false);
  const [currentTimeRange, setCurrentTimeRange] = useState<{ start: string; end: string } | null>(null);
  const [samplingRate, setSamplingRate] = useState('Overview');
  
  // Track if initial data has been loaded to prevent infinite loops
  const initialLoadedRef = useRef(false);

  // Progressive loading hook with stable error handler
  const handleProgressiveError = useCallback((errorMessage: string) => {
    setError(errorMessage);
  }, []);

  const progressiveLoading = useProgressiveLoading({
    databaseId,
    wellNumber,
    onError: handleProgressiveError
  });
  const [plotConfig, setPlotConfig] = useState<PlotConfig>({
    showWaterLevel: true,
    showTemperature: false,
    showManualReadings: true,
    dateRange: {},
    colors: {
      waterLevel: '#3b82f6',
      temperature: '#ef4444',
      manual: '#10b981'
    }
  });

  // Handle sampling rate changes with progressive loading
  const handleSamplingRateChange = useCallback(async (newSampling: string) => {
    setSamplingRate(newSampling);
    
    try {
      setLoading(true);
      
      // Map sampling rate to time ranges (always ~5000 points)
      switch (newSampling) {
        case 'Overview':
          // Load full dataset
          await progressiveLoading.loadOverview();
          break;
        case 'Medium Detail':
          if (plotConfig.dateRange?.start && plotConfig.dateRange?.end) {
            // Use current date range
            await progressiveLoading.loadForTimeRange(
              plotConfig.dateRange.start.toISOString(),
              plotConfig.dateRange.end.toISOString()
            );
          } else {
            // Load last year
            const endDate = new Date();
            const startDate = new Date(endDate.getTime() - 365 * 24 * 60 * 60 * 1000);
            await progressiveLoading.loadForTimeRange(
              startDate.toISOString(),
              endDate.toISOString()
            );
          }
          break;
        case 'Full Detail':
          if (plotConfig.dateRange?.start && plotConfig.dateRange?.end) {
            // Use current date range
            await progressiveLoading.loadForTimeRange(
              plotConfig.dateRange.start.toISOString(),
              plotConfig.dateRange.end.toISOString()
            );
          } else {
            // Load last month
            const endDate = new Date();
            const startDate = new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000);
            await progressiveLoading.loadForTimeRange(
              startDate.toISOString(),
              endDate.toISOString()
            );
          }
          break;
      }
    } catch (err) {
      console.error('Error loading progressive data:', err);
    } finally {
      setLoading(false);
    }
  }, [progressiveLoading, plotConfig.dateRange]);

  // Load well data and initial overview
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Reset initial loading flag for new well
        initialLoadedRef.current = false;

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

  // Load initial overview data after well is loaded
  useEffect(() => {
    if (well && !initialLoadedRef.current && progressiveLoading.segments.length === 0 && !progressiveLoading.isLoading) {
      initialLoadedRef.current = true;
      progressiveLoading.loadOverview().catch(err => {
        console.error('Failed to load initial overview:', err);
        initialLoadedRef.current = false; // Reset on error to allow retry
      });
    }
  }, [well, progressiveLoading.segments.length, progressiveLoading.isLoading, progressiveLoading.loadOverview]);

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

  const handlePlotConfigChange = useCallback((newConfig: Partial<PlotConfig>) => {
    setPlotConfig(prev => ({ ...prev, ...newConfig }));
  }, []);

  const handleDateRangeChange = useCallback(async (startDate?: Date, endDate?: Date) => {
    // Update plot config first
    setPlotConfig(prev => ({
      ...prev,
      dateRange: {
        start: startDate,
        end: endDate
      }
    }));
    
    // Load appropriate detail level for new viewport
    if (startDate && endDate) {
      try {
        setLoading(true);
        await progressiveLoading.loadForViewport({ start: startDate, end: endDate });
      } catch (err) {
        console.error('Error loading data for date range:', err);
      } finally {
        setLoading(false);
      }
    }
  }, [progressiveLoading.loadForViewport]);

  const handleBackToWells = useCallback(() => {
    router.push(`/wells/${databaseId}`);
  }, [databaseId, router]);

  const handleExportData = useCallback(() => {
    setShowExportMenu(prev => !prev);
  }, []);

  const handleExportCSV = useCallback(async () => {
    if (!well || progressiveLoading.currentData.length === 0) return;
    
    try {
      const filteredData = filterDataForExport(
        progressiveLoading.currentData as any,
        plotConfig.dateRange?.start?.toISOString(),
        plotConfig.dateRange?.end?.toISOString()
      );
      exportWaterLevelDataToCSV(filteredData, well as any);
      setShowExportMenu(false);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Failed to export CSV file. Please try again.');
    }
  }, [well, progressiveLoading.currentData, plotConfig.dateRange]);

  const handleExportJSON = useCallback(async () => {
    if (!well || progressiveLoading.currentData.length === 0) return;
    
    try {
      const filteredData = filterDataForExport(
        progressiveLoading.currentData as any,
        plotConfig.dateRange?.start?.toISOString(),
        plotConfig.dateRange?.end?.toISOString()
      );
      exportWaterLevelDataToJSON(filteredData, well as any);
      setShowExportMenu(false);
    } catch (error) {
      console.error('Error exporting JSON:', error);
      alert('Failed to export JSON file. Please try again.');
    }
  }, [well, progressiveLoading.currentData, plotConfig.dateRange]);

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
                  disabled={progressiveLoading.currentData.length === 0}
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
                        Exports current data: {progressiveLoading.currentData.length} readings (Level {progressiveLoading.currentLevel})
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
          totalPoints={progressiveLoading.stats.totalDataPoints}
          displayedPoints={progressiveLoading.currentData.length}
          samplingRate={`${samplingRate} (Level ${progressiveLoading.currentLevel})`}
        />

        {/* Chart Controls - Collapsible */}
        <ChartControlsPanel
          config={plotConfig}
          onConfigChange={setPlotConfig}
          isCollapsed={isChartControlsCollapsed}
          onToggleCollapse={() => setIsChartControlsCollapsed(!isChartControlsCollapsed)}
        />

        {/* Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Water Level Data
            </h2>
            {loading && (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <LoadingSpinner size="small" />
                <span>Updating...</span>
              </div>
            )}
          </div>
          
          {progressiveLoading.currentData.length === 0 ? (
            <div className="text-center py-12">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {progressiveLoading.isLoading ? 'Loading Data...' : 'No Data Available'}
              </h3>
              <p className="text-gray-600">
                {progressiveLoading.isLoading 
                  ? 'Please wait while we load your water level data.'
                  : 'No water level readings found for the selected date range.'}
              </p>
            </div>
          ) : (
            <WaterLevelChart
              data={progressiveLoading.currentData as any}
              config={plotConfig}
              loading={loading || progressiveLoading.isLoading}
              currentSampling={samplingRate}
              onSamplingChange={handleSamplingRateChange}
              onViewportChange={progressiveLoading.loadForViewport}
            />
          )}
        </div>

        {/* Data Statistics Panel - Bottom */}
        <DataStatisticsPanel 
          data={progressiveLoading.currentData as any}
          wellNumber={well.well_number}
        />
      </div>
    </div>
  );
}