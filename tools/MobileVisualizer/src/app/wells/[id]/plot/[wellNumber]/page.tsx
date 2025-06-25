'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { WaterLevelChart } from '@/components/WaterLevelChart';
import { ChartControls } from '@/components/ChartControls';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { exportWaterLevelDataToCSV, exportWaterLevelDataToJSON, filterDataForExport } from '@/utils/dataExport';
import type { Well, WaterLevelReading } from '@/lib/api/api';
import type { PlotConfig } from '@/types/database';

export default function PlotViewerPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;
  const wellNumber = params.wellNumber as string;

  const [well, setWell] = useState<Well | null>(null);
  const [data, setData] = useState<WaterLevelReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
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

  // Load well data and readings
  useEffect(() => {
    const loadWellData = async () => {
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

        // Load water level data
        const dataParams = new URLSearchParams({
          downsample: 'true',
          maxPoints: '2000'
        });
        
        const dataResponse = await fetch(`/.netlify/functions/data/${databaseId}/water/${wellNumber}?${dataParams}`);
        const dataResult = await dataResponse.json();
        
        if (!dataResult.success) {
          throw new Error(dataResult.error || 'Failed to load water level data');
        }
        
        setData(dataResult.data || []);

        // Set initial date range based on data
        if (dataResult.data && dataResult.data.length > 0) {
          const dates = dataResult.data.map((r: WaterLevelReading) => new Date(r.timestamp_utc));
          const minDate = new Date(Math.min(...dates.map((d: Date) => d.getTime())));
          const maxDate = new Date(Math.max(...dates.map((d: Date) => d.getTime())));
          
          setPlotConfig(prev => ({
            ...prev,
            dateRange: {
              start: minDate,
              end: maxDate
            }
          }));
        }

      } catch (err) {
        console.error('Error loading well data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load well data');
      } finally {
        setLoading(false);
      }
    };

    loadWellData();
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

  const handlePlotConfigChange = useCallback((newConfig: Partial<PlotConfig>) => {
    setPlotConfig(prev => ({ ...prev, ...newConfig }));
  }, []);

  const handleDateRangeChange = useCallback(async (startDate?: Date, endDate?: Date) => {
    try {
      setLoading(true);
      
      const dataParams = new URLSearchParams({
        downsample: 'true',
        maxPoints: '2000',
        ...(startDate && { startDate: startDate.toISOString() }),
        ...(endDate && { endDate: endDate.toISOString() })
      });
      
      const dataResponse = await fetch(`/.netlify/functions/data/${databaseId}/water/${wellNumber}?${dataParams}`);
      const dataResult = await dataResponse.json();
      
      if (dataResult.success && dataResult.data) {
        setData(dataResult.data);
      }
      
      setData(dataResult.data || []);
      setPlotConfig(prev => ({
        ...prev,
        dateRange: {
          start: startDate,
          end: endDate
        }
      }));
    } catch (err) {
      console.error('Error loading filtered data:', err);
    } finally {
      setLoading(false);
    }
  }, [databaseId, wellNumber]);

  const handleBackToWells = useCallback(() => {
    router.push(`/wells/${databaseId}`);
  }, [databaseId, router]);

  const handleExportData = useCallback(() => {
    setShowExportMenu(prev => !prev);
  }, []);

  const handleExportCSV = useCallback(async () => {
    if (!well || data.length === 0) return;
    
    try {
      const filteredData = filterDataForExport(
        data as any,
        plotConfig.dateRange?.start?.toISOString(),
        plotConfig.dateRange?.end?.toISOString()
      );
      exportWaterLevelDataToCSV(filteredData, well as any);
      setShowExportMenu(false);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Failed to export CSV file. Please try again.');
    }
  }, [well, data, plotConfig.dateRange]);

  const handleExportJSON = useCallback(async () => {
    if (!well || data.length === 0) return;
    
    try {
      const filteredData = filterDataForExport(
        data as any,
        plotConfig.dateRange?.start?.toISOString(),
        plotConfig.dateRange?.end?.toISOString()
      );
      exportWaterLevelDataToJSON(filteredData, well as any);
      setShowExportMenu(false);
    } catch (error) {
      console.error('Error exporting JSON:', error);
      alert('Failed to export JSON file. Please try again.');
    }
  }, [well, data, plotConfig.dateRange]);

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
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  {well.cae_number && (
                    <span>CAE: {well.cae_number}</span>
                  )}
                  {well.well_field && (
                    <span>Field: {well.well_field}</span>
                  )}
                  <span>{data.length} readings</span>
                </div>
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
                  disabled={data.length === 0}
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
                        Exports current date range: {data.length} readings
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
        {/* Chart Controls */}
        <ChartControls
          config={plotConfig}
          onConfigChange={handlePlotConfigChange}
          onDateRangeChange={handleDateRangeChange}
          well={well}
          dataCount={data.length}
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
          
          {data.length === 0 ? (
            <div className="text-center py-12">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No Data Available
              </h3>
              <p className="text-gray-600">
                No water level readings found for the selected date range.
              </p>
            </div>
          ) : (
            <WaterLevelChart
              data={data as any}
              config={plotConfig}
              loading={loading}
            />
          )}
        </div>

        {/* Well Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Well Details */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Well Information</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Well Number:</span>
                  <p className="text-gray-900">{well.well_number}</p>
                </div>
                {well.cae_number && (
                  <div>
                    <span className="font-medium text-gray-700">CAE Number:</span>
                    <p className="text-gray-900">{well.cae_number}</p>
                  </div>
                )}
                {well.well_field && (
                  <div>
                    <span className="font-medium text-gray-700">Well Field:</span>
                    <p className="text-gray-900">{well.well_field}</p>
                  </div>
                )}
                {well.aquifer_type && (
                  <div>
                    <span className="font-medium text-gray-700">Aquifer Type:</span>
                    <p className="text-gray-900 capitalize">{well.aquifer_type}</p>
                  </div>
                )}
                {well.top_of_casing && (
                  <div>
                    <span className="font-medium text-gray-700">Top of Casing:</span>
                    <p className="text-gray-900">{well.top_of_casing.toFixed(2)} ft</p>
                  </div>
                )}
                {well.well_depth && (
                  <div>
                    <span className="font-medium text-gray-700">Well Depth:</span>
                    <p className="text-gray-900">{well.well_depth.toFixed(2)} ft</p>
                  </div>
                )}
              </div>
              {well.notes && (
                <div>
                  <span className="font-medium text-gray-700">Notes:</span>
                  <p className="text-gray-900 text-sm mt-1">{well.notes}</p>
                </div>
              )}
            </div>
          </div>

          {/* Data Summary */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Summary</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Transducer Data */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="w-3 h-3 bg-blue-600 rounded-full"></div>
                    <span className="font-medium text-blue-900">Transducer Data</span>
                  </div>
                  <div className="text-2xl font-bold text-blue-900">
                    {well.has_transducer_data ? (well.total_readings || 0) - (well.manual_readings_count || 0) : 0}
                  </div>
                  <div className="text-xs text-blue-700">15-minute intervals</div>
                </div>

                {/* Manual Readings */}
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="w-3 h-3 bg-green-600 rounded-full"></div>
                    <span className="font-medium text-green-900">Manual Readings</span>
                  </div>
                  <div className="text-2xl font-bold text-green-900">
                    {well.manual_readings_count || 0}
                  </div>
                  <div className="text-xs text-green-700">Periodic measurements</div>
                </div>
              </div>

              {/* Total */}
              <div className="pt-2 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">Total Readings:</span>
                  <span className="text-lg font-semibold text-gray-900">{well.total_readings || 0}</span>
                </div>
              </div>

              {well.last_reading_date && (
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">Last Reading:</span>
                  <span className="text-gray-900">
                    {new Date(well.last_reading_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}