'use client';

import { useState, useEffect } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface WellStatistics {
  wellNumber: string;
  totalReadings: number;
  dataRange: {
    startDate: string;
    endDate: string;
    totalDays: number;
  };
  levels: {
    min: number;
    max: number;
    average: number;
    range: number;
    minDate: string;
    maxDate: string;
  };
  trend: {
    direction: 'rising' | 'falling' | 'stable';
    slope: number;
    changePerYear: number;
    confidence: number;
  };
  seasonal: {
    highestMonth: string;
    lowestMonth: string;
    seasonalVariation: number;
    monthlyAverages: Array<{
      month: string;
      average: number;
      readings: number;
    }>;
  };
  recent: {
    last30Days: number;
    last90Days: number;
    lastReading: string;
    recentTrend: 'rising' | 'falling' | 'stable';
  };
}

interface WellStatisticsPanelProps {
  databaseId: string;
  wellNumber: string;
}

export function WellStatisticsPanel({ databaseId, wellNumber }: WellStatisticsPanelProps) {
  const [statistics, setStatistics] = useState<WellStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const loadStatistics = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get well statistics from our new endpoint
        const statsResponse = await fetch(`/.netlify/functions/well-statistics?wellNumber=${encodeURIComponent(wellNumber)}`);
        const statsResult = await statsResponse.json();
        
        if (!statsResult.success) {
          throw new Error(statsResult.error || 'Failed to load well statistics');
        }

        setStatistics(statsResult.data);
      } catch (err) {
        console.error('Error loading well statistics:', err);
        setError(err instanceof Error ? err.message : 'Failed to load statistics');
      } finally {
        setLoading(false);
      }
    };

    loadStatistics();
  }, [databaseId, wellNumber]);

  const formatDate = (dateString: string): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'N/A';
    }
  };

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'rising':
        return <span className="text-green-600">📈</span>;
      case 'falling':
        return <span className="text-red-600">📉</span>; 
      default:
        return <span className="text-gray-500">➡️</span>;
    }
  };

  const getTrendColor = (direction: string) => {
    switch (direction) {
      case 'rising':
        return 'text-green-600';
      case 'falling':
        return 'text-red-600';
      default:
        return 'text-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="small" />
          <span className="ml-2 text-gray-600">Loading statistics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="text-center py-4">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!statistics) {
    return null;
  }

  return (
    <div className="card">
      {/* Header - Always visible */}
      <div 
        className="flex items-center justify-between cursor-pointer hover:bg-gray-50 -m-6 p-6 rounded-lg"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="text-lg font-semibold text-gray-900">Well Statistics & Insights</h3>
        <svg 
          className={`w-5 h-5 text-gray-600 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Quick Summary - Always visible */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <div className="text-center">
          <div className="text-xl font-bold text-blue-600">{statistics.levels.min.toFixed(2)} ft</div>
          <div className="text-xs text-gray-600">Minimum Level</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-red-600">{statistics.levels.max.toFixed(2)} ft</div>
          <div className="text-xs text-gray-600">Maximum Level</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-green-600">{statistics.levels.average.toFixed(2)} ft</div>
          <div className="text-xs text-gray-600">Average Level</div>
        </div>
        <div className="text-center">
          <div className={`text-xl font-bold flex items-center justify-center ${getTrendColor(statistics.trend.direction)}`}>
            {getTrendIcon(statistics.trend.direction)}
            <span className="ml-1">{statistics.trend.direction}</span>
            <span className="ml-1 text-sm">({statistics.trend.changePerYear.toFixed(2)} ft/yr)</span>
          </div>
          <div className="text-xs text-gray-600">Trend</div>
        </div>
      </div>

      {/* Detailed Statistics - Collapsible */}
      {isExpanded && (
        <div className="mt-6 space-y-6">
          {/* Water Level Statistics */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Detailed Water Level Statistics</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Minimum Level:</span>
                  <span className="ml-2">{statistics.levels.min.toFixed(2)} ft</span>
                  <div className="text-xs text-gray-500 ml-2">on {formatDate(statistics.levels.minDate)}</div>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Maximum Level:</span>
                  <span className="ml-2">{statistics.levels.max.toFixed(2)} ft</span>
                  <div className="text-xs text-gray-500 ml-2">on {formatDate(statistics.levels.maxDate)}</div>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Average Level:</span>
                  <span className="ml-2">{statistics.levels.average.toFixed(2)} ft</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Total Range:</span>
                  <span className="ml-2">{statistics.levels.range.toFixed(2)} ft</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Total Readings:</span>
                  <span className="ml-2">{statistics.totalReadings.toLocaleString()}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Data Duration:</span>
                  <span className="ml-2">{statistics.dataRange.totalDays > 0 ? (statistics.dataRange.totalDays / 365.25).toFixed(1) : '0'} years</span>
                </div>
              </div>
            </div>
          </div>

          {/* Data Range */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Data Period</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Start:</span>
                  <span className="ml-2">{formatDate(statistics.dataRange.startDate)}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">End:</span>
                  <span className="ml-2">{formatDate(statistics.dataRange.endDate)}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Duration:</span>
                  <span className="ml-2">{statistics.dataRange.totalDays > 0 ? (statistics.dataRange.totalDays / 365.25).toFixed(1) : '0'} years</span>
                </div>
              </div>
            </div>
          </div>

          {/* Trend Analysis */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Trend Analysis</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Trend Direction:</span>
                  <span className={`ml-2 ${getTrendColor(statistics.trend.direction)}`}>
                    {getTrendIcon(statistics.trend.direction)} {statistics.trend.direction}
                  </span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Change per Year:</span>
                  <span className="ml-2">{statistics.trend.changePerYear.toFixed(3)} ft/year</span>
                </div>
              </div>
            </div>
          </div>

          {/* Seasonal Patterns */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Seasonal Patterns</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Highest Month:</span>
                  <span className="ml-2">{statistics.seasonal.highestMonth || 'N/A'}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Lowest Month:</span>
                  <span className="ml-2">{statistics.seasonal.lowestMonth || 'N/A'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Recent Activity</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Readings (Last 30 Days):</span>
                  <span className="ml-2">{statistics.recent.last30Days.toLocaleString()}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Last Reading:</span>
                  <span className="ml-2">{formatDate(statistics.recent.lastReading)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}