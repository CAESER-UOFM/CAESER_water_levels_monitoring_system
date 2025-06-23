'use client';

import { useMemo, useState, useCallback } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
  ScatterChart,
  Scatter,
  ReferenceLine
} from 'recharts';
import type { WaterLevelReading, PlotConfig, ChartDataPoint } from '@/types/database';

interface WaterLevelChartProps {
  data: WaterLevelReading[];
  config: PlotConfig;
  loading?: boolean;
}

export function WaterLevelChart({ data, config, loading = false }: WaterLevelChartProps) {
  const [zoomedData, setZoomedData] = useState<ChartDataPoint[] | null>(null);
  const [showBrush, setShowBrush] = useState(true);

  // Process data for chart
  const chartData = useMemo(() => {
    const processedData: ChartDataPoint[] = data
      .filter(reading => {
        if (!config.dateRange.start || !config.dateRange.end) return true;
        const readingDate = new Date(reading.timestamp_utc);
        return readingDate >= config.dateRange.start && readingDate <= config.dateRange.end;
      })
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

  // Separate manual readings for scatter plot
  const manualReadings = useMemo(() => {
    return chartData.filter(point => point.source === 'manual');
  }, [chartData]);

  const continuousData = useMemo(() => {
    return chartData.filter(point => point.source !== 'manual');
  }, [chartData]);

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

  // Handle brush change
  const handleBrushChange = useCallback((brushData: any) => {
    if (brushData && brushData.startIndex !== undefined && brushData.endIndex !== undefined) {
      const start = brushData.startIndex;
      const end = brushData.endIndex;
      setZoomedData(chartData.slice(start, end + 1));
    } else {
      setZoomedData(null);
    }
  }, [chartData]);

  const displayData = zoomedData || chartData;

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

  return (
    <div className="space-y-4">
      {/* Chart Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-600">
            {displayData.length} points displayed
          </span>
          {zoomedData && (
            <button
              onClick={() => setZoomedData(null)}
              className="text-sm text-primary-600 hover:text-primary-800"
            >
              Reset Zoom
            </button>
          )}
        </div>
        <button
          onClick={() => setShowBrush(!showBrush)}
          className="text-sm text-gray-600 hover:text-gray-800"
        >
          {showBrush ? 'Hide' : 'Show'} Navigation
        </button>
      </div>

      {/* Main Chart */}
      <div className="h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={displayData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
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
              label={{ 
                value: 'Water Level (ft)', 
                angle: -90, 
                position: 'insideLeft',
                style: { textAnchor: 'middle' }
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            
            {/* Water Level Line */}
            {config.showWaterLevel && (
              <Line
                type="monotone"
                dataKey="water_level"
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

            {/* Brush for navigation */}
            {showBrush && chartData.length > 50 && (
              <Brush
                dataKey="timestamp"
                height={30}
                stroke={config.colors.waterLevel}
                onChange={handleBrushChange}
                tickFormatter={formatXAxis}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Manual Readings Overlay */}
      {config.showManualReadings && manualReadings.length > 0 && (
        <div className="h-96 w-full -mt-96 relative pointer-events-none">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart data={manualReadings} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <XAxis 
                dataKey="timestamp"
                type="category"
                scale="time"
                domain={['dataMin', 'dataMax']}
                hide
              />
              <YAxis domain={yAxisDomain} hide />
              <Scatter
                dataKey="water_level"
                fill={config.colors.manual}
                stroke={config.colors.manual}
                strokeWidth={2}
                r={5}
                shape="circle"
                name="Manual Readings"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Chart Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
        {config.showWaterLevel && (
          <div className="flex items-center space-x-2">
            <div 
              className="w-4 h-0.5"
              style={{ backgroundColor: config.colors.waterLevel }}
            />
            <span className="text-gray-700">Water Level</span>
          </div>
        )}
        {config.showTemperature && (
          <div className="flex items-center space-x-2">
            <div 
              className="w-4 h-0.5"
              style={{ backgroundColor: config.colors.temperature }}
            />
            <span className="text-gray-700">Temperature</span>
          </div>
        )}
        {config.showManualReadings && manualReadings.length > 0 && (
          <div className="flex items-center space-x-2">
            <div 
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: config.colors.manual }}
            />
            <span className="text-gray-700">Manual Readings ({manualReadings.length})</span>
          </div>
        )}
      </div>

      {/* Data Range Info */}
      {chartData.length > 0 && (
        <div className="text-xs text-gray-500 text-center">
          Data range: {chartData[0].date.toLocaleDateString()} to{' '}
          {chartData[chartData.length - 1].date.toLocaleDateString()}
          {zoomedData && (
            <span className="ml-2 text-primary-600">
              (Zoomed view)
            </span>
          )}
        </div>
      )}
    </div>
  );
}