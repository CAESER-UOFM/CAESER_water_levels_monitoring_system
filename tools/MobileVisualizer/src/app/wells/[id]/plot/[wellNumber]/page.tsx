'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { SmartWaterLevelChart } from '@/components/SmartWaterLevelChart';
import { WellInfoPanel } from '@/components/WellInfoPanel';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ExportDialog, type ExportOptions } from '@/components/ExportDialog';
import { exportWaterLevelDataWithProgress } from '@/utils/dataExport';
import type { Well } from '@/lib/api/api';

export default function PlotViewerPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;
  const wellNumber = params.wellNumber as string;

  const [well, setWell] = useState<Well | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<{stage: string; percentage: number; message: string} | null>(null);
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





  const handleBackToWells = useCallback(() => {
    router.push(`/wells/${databaseId}`);
  }, [databaseId, router]);

  const handleExportData = useCallback(() => {
    setShowExportDialog(true);
  }, []);

  const handleExportDialogClose = useCallback(() => {
    if (!isExporting) {
      setShowExportDialog(false);
      setExportProgress(null);
    }
  }, [isExporting]);

  const handleExportStart = useCallback(async (options: ExportOptions) => {
    if (!well || !currentTimeRange) return;

    setIsExporting(true);
    setExportProgress({ stage: 'preparing', percentage: 0, message: 'Preparing export...' });

    const abortController = new AbortController();

    try {
      await exportWaterLevelDataWithProgress(
        databaseId,
        wellNumber,
        well,
        options,
        (progress) => {
          setExportProgress(progress);
        },
        abortController.signal
      );

      // Success - close dialog after a brief delay
      setTimeout(() => {
        setShowExportDialog(false);
        setExportProgress(null);
        setIsExporting(false);
      }, 1500);

    } catch (error) {
      console.error('Export failed:', error);
      
      if (error instanceof Error && error.message.includes('cancelled')) {
        setExportProgress({ stage: 'cancelled', percentage: 0, message: 'Export cancelled' });
      } else {
        setExportProgress({ 
          stage: 'error', 
          percentage: 0, 
          message: `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}` 
        });
      }

      // Reset after showing error
      setTimeout(() => {
        setShowExportDialog(false);
        setExportProgress(null);
        setIsExporting(false);
      }, 3000);
    }
  }, [databaseId, wellNumber, well, currentTimeRange]);

  const handleViewRecharge = useCallback(() => {
    router.push(`/wells/${databaseId}/recharge/${wellNumber}`);
  }, [databaseId, wellNumber, router]);

  const handleViewOnMap = useCallback(() => {
    router.push(`/wells/${databaseId}/map?highlight=${wellNumber}`);
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
                onClick={handleViewOnMap}
                className="btn-outline text-sm px-3 py-2"
                title="View well location on map"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="hidden sm:inline">Map</span>
              </button>
              
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
              
              {/* Export Button */}
              <button
                onClick={handleExportData}
                className="btn-primary text-sm px-3 py-2"
                title="Export data"
                disabled={isExporting}
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span className="hidden sm:inline">Export Data</span>
              </button>
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

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={handleExportDialogClose}
        onExport={handleExportStart}
        wellNumber={wellNumber}
        fullDataRange={currentTimeRange}
        isLoading={isExporting}
      />

      {/* Export Progress Overlay */}
      {isExporting && exportProgress && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Exporting Data</h3>
              
              <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                <div 
                  className={`h-2 rounded-full transition-all duration-300 ${
                    exportProgress.stage === 'error' ? 'bg-red-500' :
                    exportProgress.stage === 'cancelled' ? 'bg-gray-500' :
                    exportProgress.stage === 'complete' ? 'bg-green-500' :
                    'bg-blue-500'
                  }`}
                  style={{ width: `${exportProgress.percentage}%` }}
                />
              </div>
              
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">
                  {exportProgress.message}
                </p>
                <p className="text-xs text-gray-500">
                  {exportProgress.percentage}% complete
                </p>
              </div>

              {exportProgress.stage === 'complete' && (
                <div className="mt-4 flex items-center justify-center text-green-600">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium">Export completed successfully!</span>
                </div>
              )}

              {(exportProgress.stage === 'error' || exportProgress.stage === 'cancelled') && (
                <button
                  onClick={handleExportDialogClose}
                  className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}