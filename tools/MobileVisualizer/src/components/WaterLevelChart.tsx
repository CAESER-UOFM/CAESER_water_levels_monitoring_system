'use client';

import React, { useMemo, useState, useCallback } from 'react';
import { SamplingControls, downsampleData } from './SamplingControls';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ScatterChart,
  Scatter,
  ComposedChart,
  ReferenceLine
} from 'recharts';
import type { WaterLevelReading, PlotConfig, ChartDataPoint } from '@/types/database';

interface ChartMetadata {
  totalPoints: number;
  displayedPoints: number;
  manualReadings: number;
  dataRange: {
    start: string;
    end: string;
  } | null;
  viewStatus: string | null;
}

interface WaterLevelChartProps {
  data: WaterLevelReading[];
  config: PlotConfig;
  loading?: boolean;
  onMetadataChange?: (metadata: ChartMetadata) => void;
  currentSampling?: string;
  onSamplingChange?: (sampling: string) => void;
  onViewportChange?: (startDate: Date, endDate: Date) => Promise<void>;
}

interface SamplingState {
  selectedSampling: string;
  isLoadingSampling: boolean;
}

export function WaterLevelChart({ data, config, loading = false, onMetadataChange, currentSampling = '15min', onSamplingChange, onViewportChange }: WaterLevelChartProps) {
  const [zoomedData, setZoomedData] = useState<ChartDataPoint[] | null>(null);
  const [viewWindow, setViewWindow] = useState<{ start: number; end: number } | null>(null);
  const [samplingState, setSamplingState] = useState<SamplingState>({
    selectedSampling: currentSampling,
    isLoadingSampling: false
  });

  // Update internal state when external sampling changes
  React.useEffect(() => {
    setSamplingState(prev => ({
      ...prev,
      selectedSampling: currentSampling
    }));
  }, [currentSampling]);

  // Handle sampling change
  const handleSamplingChange = useCallback((newSampling: string) => {
    setSamplingState(prev => ({
      ...prev,
      selectedSampling: newSampling,
      isLoadingSampling: true
    }));
    
    // Call external handler if provided
    if (onSamplingChange) {
      onSamplingChange(newSampling);
    }
    
    // Simulate processing time for large datasets
    setTimeout(() => {
      setSamplingState(prev => ({
        ...prev,
        isLoadingSampling: false
      }));
    }, newSampling === 'all' ? 1000 : 300);
  }, [onSamplingChange]);

  // Process data for chart (downsampling now handled at API level)
  const chartData = useMemo(() => {
    // Filter by date range if needed (though this might also be handled at API level)
    const filteredData = data.filter(reading => {
      if (!config.dateRange.start || !config.dateRange.end) return true;
      const readingDate = new Date(reading.timestamp_utc);
      return readingDate >= config.dateRange.start && readingDate <= config.dateRange.end;
    });

    const processedData: ChartDataPoint[] = filteredData
      .map(reading => ({
        timestamp: reading.timestamp_utc,
        date: new Date(reading.timestamp_utc),
        water_level: reading.water_level,
        temperature: reading.temperature,
        dtw: reading.dtw,
        source: reading.data_source,
        original_timestamp: reading.timestamp_utc
      }))
      .sort((a, b) => a.date.getTime() - b.date.getTime());

    return processedData;
  }, [data, config.dateRange]);

  // Process data for display - no client-side windowing when using progressive loading
  const displayData = useMemo(() => {
    // When using progressive loading (onViewportChange exists), don't do client-side filtering
    // The API handles the windowing with appropriate detail levels
    const finalData = onViewportChange ? chartData : (zoomedData || chartData);
    
    // Add manual indicator for styling
    const processedData = finalData.map(point => ({
      ...point,
      isManual: point.source === 'manual',
      // For manual readings, we'll use scatter plot
      manualWaterLevel: point.source === 'manual' ? point.water_level : null,
      // For continuous readings, we'll use line plot
      continuousWaterLevel: point.source !== 'manual' ? point.water_level : null
    }));
    
    console.log(`🎯 Chart data processing:`, {
      totalPoints: finalData.length,
      manualCount: finalData.filter(p => p.source === 'manual').length,
      continuousCount: finalData.filter(p => p.source !== 'manual').length,
      usingProgressiveLoading: !!onViewportChange,
      windowActive: !!viewWindow,
      zoomActive: !!zoomedData
    });
    
    return processedData;
  }, [chartData, zoomedData, viewWindow, onViewportChange]);

  const manualReadings = useMemo(() => {
    return displayData.filter(point => point.source === 'manual');
  }, [displayData]);

  const continuousData = useMemo(() => {
    return displayData.filter(point => point.source !== 'manual');
  }, [displayData]);

  // Calculate Y-axis domain
  const yAxisDomain = useMemo(() => {
    if (config.yAxisRange?.min !== undefined && config.yAxisRange?.max !== undefined) {
      return [config.yAxisRange.min, config.yAxisRange.max];
    }

    const waterLevels = chartData
      .map(d => d.water_level)
      .filter(val => val !== undefined && val !== null) as number[];
    
    if (waterLevels.length === 0) return ['auto', 'auto'];

    const min = Math.min(...waterLevels);
    const max = Math.max(...waterLevels);
    const padding = (max - min) * 0.1;
    
    return [min - padding, max + padding];
  }, [chartData, config.yAxisRange]);

  // Custom tooltip
  const CustomTooltip = useCallback(({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    const date = new Date(label);
    const isManual = payload[0]?.payload?.source === 'manual';

    return (
      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 mb-2">
          {date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between space-x-4">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-sm text-gray-700 capitalize">
                {entry.dataKey === 'water_level' 
                  ? isManual ? 'Manual Reading' : 'Water Level'
                  : entry.dataKey === 'temperature' 
                  ? 'Temperature' 
                  : entry.dataKey}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900">
              {entry.value?.toFixed(3)} {entry.dataKey === 'temperature' ? '°C' : 'ft'}
            </span>
          </div>
        ))}
        {isManual && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            <span className="text-xs text-gray-500">Manual measurement</span>
          </div>
        )}
      </div>
    );
  }, []);

  // Format X-axis labels
  const formatXAxis = useCallback((tickItem: string) => {
    const date = new Date(tickItem);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: chartData.length > 100 ? '2-digit' : undefined
    });
  }, [chartData.length]);

  // Format Y-axis labels - use whole numbers for better readability
  const formatYAxis = useCallback((value: number) => {
    return Math.round(value).toString();
  }, []);


  // Modern navigation handlers
  const handleNavigateLeft = useCallback(() => {
    if (!viewWindow) {
      setViewWindow({ start: 0, end: 25 });
    } else {
      const windowSize = viewWindow.end - viewWindow.start;
      const newStart = Math.max(0, viewWindow.start - windowSize / 2);
      const newEnd = Math.min(100, newStart + windowSize);
      setViewWindow({ start: newStart, end: newEnd });
    }
  }, [viewWindow]);

  const handleNavigateRight = useCallback(() => {
    if (!viewWindow) {
      setViewWindow({ start: 75, end: 100 });
    } else {
      const windowSize = viewWindow.end - viewWindow.start;
      const newEnd = Math.min(100, viewWindow.end + windowSize / 2);
      const newStart = Math.max(0, newEnd - windowSize);
      setViewWindow({ start: newStart, end: newEnd });
    }
  }, [viewWindow]);

  const handleResetView = useCallback(() => {
    setViewWindow(null);
    setZoomedData(null);
  }, []);

  const handleZoomIn = useCallback(async () => {
    if (onViewportChange && chartData.length > 0) {
      // Progressive loading mode - calculate time-based zoom
      const currentTimeSpan = chartData.length > 1 ? 
        new Date(chartData[chartData.length - 1].timestamp).getTime() - new Date(chartData[0].timestamp).getTime() :
        30 * 24 * 60 * 60 * 1000; // Default to 30 days if single point
        
      // Zoom in to middle 50% of current time range
      const startTime = new Date(chartData[0].timestamp).getTime();
      const zoomStartTime = startTime + currentTimeSpan * 0.25;
      const zoomEndTime = startTime + currentTimeSpan * 0.75;
      
      const startDate = new Date(zoomStartTime);
      const endDate = new Date(zoomEndTime);
      
      console.log(`🔍 Zoom in triggered viewport loading:`, {
        timeSpanDays: currentTimeSpan / (1000 * 60 * 60 * 24),
        dateRange: { start: startDate.toISOString(), end: endDate.toISOString() }
      });
      
      try {
        await onViewportChange(startDate, endDate);
      } catch (err) {
        console.error('Failed to load viewport data on zoom:', err);
      }
    } else {
      // Fallback to client-side windowing for non-progressive mode
      let newWindow;
      if (!viewWindow) {
        newWindow = { start: 25, end: 75 };
      } else {
        const center = (viewWindow.start + viewWindow.end) / 2;
        const newSize = (viewWindow.end - viewWindow.start) / 2;
        const newStart = Math.max(0, center - newSize / 2);
        const newEnd = Math.min(100, center + newSize / 2);
        newWindow = { start: newStart, end: newEnd };
      }
      setViewWindow(newWindow);
    }
  }, [viewWindow, chartData, onViewportChange]);

  const handleZoomOut = useCallback(async () => {
    if (onViewportChange && chartData.length > 0) {
      // Progressive loading mode - calculate time-based zoom out
      const currentTimeSpan = chartData.length > 1 ? 
        new Date(chartData[chartData.length - 1].timestamp).getTime() - new Date(chartData[0].timestamp).getTime() :
        30 * 24 * 60 * 60 * 1000; // Default to 30 days if single point
        
      // Zoom out to 2x current time range, centered
      const startTime = new Date(chartData[0].timestamp).getTime();
      const endTime = new Date(chartData[chartData.length - 1].timestamp).getTime();
      const center = (startTime + endTime) / 2;
      const newTimeSpan = currentTimeSpan * 2;
      
      const zoomStartTime = center - newTimeSpan / 2;
      const zoomEndTime = center + newTimeSpan / 2;
      
      const startDate = new Date(zoomStartTime);
      const endDate = new Date(zoomEndTime);
      
      console.log(`🔍 Zoom out triggered viewport loading:`, {
        timeSpanDays: newTimeSpan / (1000 * 60 * 60 * 24),
        dateRange: { start: startDate.toISOString(), end: endDate.toISOString() }
      });
      
      try {
        await onViewportChange(startDate, endDate);
      } catch (err) {
        console.error('Failed to load viewport data on zoom out:', err);
      }
    } else {
      // Fallback to client-side windowing for non-progressive mode
      let newWindow = null;
      
      if (!viewWindow) {
        newWindow = { start: 0, end: 100 };
      } else {
        const center = (viewWindow.start + viewWindow.end) / 2;
        const newSize = Math.min(100, (viewWindow.end - viewWindow.start) * 2);
        const newStart = Math.max(0, center - newSize / 2);
        const newEnd = Math.min(100, center + newSize / 2);
        
        if (newStart === 0 && newEnd === 100) {
          newWindow = null;
        } else {
          newWindow = { start: newStart, end: newEnd };
        }
      }
      setViewWindow(newWindow);
    }
  }, [viewWindow, chartData, onViewportChange]);

  // This line is now handled in the useMemo above

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 loading-spinner mx-auto mb-2"></div>
          <p className="text-sm text-gray-600">Loading chart...</p>
        </div>
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Data to Display</h3>
          <p className="text-gray-600">Adjust your filters or date range to view data.</p>
        </div>
      </div>
    );
  }

  // Send metadata to parent component
  const metadata: ChartMetadata = {
    totalPoints: chartData.length,
    displayedPoints: displayData.length,
    manualReadings: manualReadings.length,
    dataRange: displayData.length > 0 ? {
      start: displayData[0].date.toLocaleDateString(),
      end: displayData[displayData.length - 1].date.toLocaleDateString()
    } : null,
    viewStatus: (viewWindow || zoomedData) ? 
      `${viewWindow ? 'Navigated' : ''}${zoomedData ? ' Zoomed' : ''}`.trim() : null
  };

  // Call metadata callback when metadata changes
  React.useEffect(() => {
    if (onMetadataChange) {
      onMetadataChange(metadata);
    }
  }, [onMetadataChange, chartData.length, displayData.length, manualReadings.length, viewWindow, zoomedData]);

  return (
    <div className="space-y-3">
      {/* Modern Chart Navigation */}
      <div className="space-y-2">
        {/* Sampling Controls */}
        <SamplingControls
          selectedSampling={samplingState.selectedSampling}
          onSamplingChange={handleSamplingChange}
          totalPoints={data.length}
          displayedPoints={chartData.length}
          isLoading={samplingState.isLoadingSampling}
        />

        {/* Consolidated Navigation and View Info */}
        <div className="bg-gray-50 rounded-lg p-3">
          {/* Single line with all navigation info */}
          <div className="flex items-center justify-between gap-2 mb-3">
            {/* Navigation Controls */}
            <div className="flex items-center space-x-1">
              <button
                onClick={handleNavigateLeft}
                className="flex items-center justify-center w-8 h-8 bg-white border border-gray-300 rounded-md hover:bg-gray-100 active:bg-gray-200 transition-colors mobile-touch-target"
                title="Navigate left"
                disabled={viewWindow?.start === 0}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              <button
                onClick={handleZoomOut}
                className="flex items-center justify-center w-8 h-8 bg-white border border-gray-300 rounded-md hover:bg-gray-100 active:bg-gray-200 transition-colors mobile-touch-target"
                title="Zoom out"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
                </svg>
              </button>

              <button
                onClick={handleResetView}
                className="flex items-center justify-center px-2 h-8 bg-primary-600 text-white rounded-md hover:bg-primary-700 active:bg-primary-800 transition-colors mobile-touch-target font-medium text-xs"
                title="Reset view"
              >
                Reset
              </button>

              <button
                onClick={handleZoomIn}
                className="flex items-center justify-center w-8 h-8 bg-white border border-gray-300 rounded-md hover:bg-gray-100 active:bg-gray-200 transition-colors mobile-touch-target"
                title="Zoom in"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
                </svg>
              </button>

              <button
                onClick={handleNavigateRight}
                className="flex items-center justify-center w-8 h-8 bg-white border border-gray-300 rounded-md hover:bg-gray-100 active:bg-gray-200 transition-colors mobile-touch-target"
                title="Navigate right"
                disabled={viewWindow?.end === 100}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* View Info and Points Count */}
            <div className="text-xs text-gray-600 text-right flex-1">
              <div className="flex items-center justify-end space-x-2">
                <span>Showing {displayData.length.toLocaleString()}</span>
                {config.showManualReadings && manualReadings.length > 0 && (
                  <span className="text-green-600">+{manualReadings.length} manual</span>
                )}
                {viewWindow && (
                  <span className="text-primary-600">
                    {Math.round(viewWindow.start)}-{Math.round(viewWindow.end)}%
                  </span>
                )}
              </div>
              {viewWindow && chartData.length > 0 && (
                <div className="text-gray-500 font-mono mt-1">
                  {(() => {
                    const startIdx = Math.floor((viewWindow.start / 100) * chartData.length);
                    const endIdx = Math.floor((viewWindow.end / 100) * chartData.length);
                    const startDate = new Date(chartData[Math.max(0, startIdx)]?.timestamp);
                    const endDate = new Date(chartData[Math.min(chartData.length - 1, endIdx)]?.timestamp);
                    return `${startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
                  })()}
                </div>
              )}
            </div>
          </div>

          {/* Progress bar for view window */}
          {viewWindow && (
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div 
                className="bg-primary-600 h-1.5 rounded-full transition-all duration-200"
                style={{
                  marginLeft: `${viewWindow.start}%`,
                  width: `${viewWindow.end - viewWindow.start}%`
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Main Chart */}
      <div className="h-96 w-full relative overflow-hidden" style={{ touchAction: 'pan-x pan-y' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={displayData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              stroke="#6b7280"
              fontSize={12}
              angle={-45}
              textAnchor="end"
              height={60}
              interval="preserveStartEnd"
            />
            <YAxis 
              domain={yAxisDomain}
              stroke="#6b7280"
              fontSize={12}
              tickFormatter={formatYAxis}
              label={{ 
                value: 'Water Level (ft)', 
                angle: -90, 
                position: 'insideLeft',
                style: { textAnchor: 'middle' }
              }}
            />
            {/* Secondary Y-axis for temperature */}
            {config.showTemperature && (
              <YAxis 
                yAxisId="temp"
                orientation="right"
                stroke="#6b7280"
                fontSize={12}
                label={{ 
                  value: 'Temperature (°C)', 
                  angle: 90, 
                  position: 'insideRight',
                  style: { textAnchor: 'middle' }
                }}
              />
            )}
            <Tooltip content={<CustomTooltip />} />
            
            {/* Water Level Line for continuous data */}
            {config.showWaterLevel && (
              <Line
                type="monotone"
                dataKey="continuousWaterLevel"
                stroke={config.colors.waterLevel}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: config.colors.waterLevel, strokeWidth: 2 }}
                name="Water Level"
                connectNulls={false}
              />
            )}
            
            {/* Temperature Line (secondary axis) */}
            {config.showTemperature && (
              <Line
                type="monotone"
                dataKey="temperature"
                stroke={config.colors.temperature}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: config.colors.temperature, strokeWidth: 2 }}
                name="Temperature"
                yAxisId="temp"
                connectNulls={false}
              />
            )}

            {/* Manual Readings as Scatter on the same chart */}
            {config.showManualReadings && (
              <Scatter
                dataKey="manualWaterLevel"
                fill={config.colors.manual}
                stroke={config.colors.manual}
                strokeWidth={2}
                name="Manual Readings"
              />
            )}

          </ComposedChart>
        </ResponsiveContainer>
      </div>


    </div>
  );
}