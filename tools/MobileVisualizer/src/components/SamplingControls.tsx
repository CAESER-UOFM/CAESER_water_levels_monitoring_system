'use client';

import React from 'react';

export interface SamplingOption {
  label: string;
  value: string;
  intervalMinutes: number | null; // null means no downsampling
}

const SAMPLING_OPTIONS: SamplingOption[] = [
  { label: 'Overview', value: 'Overview', intervalMinutes: null }, // Full dataset - ~5000 points
  { label: 'Last Year', value: 'Medium Detail', intervalMinutes: null }, // 1 year - ~5000 points
  { label: 'Last Month', value: 'Full Detail', intervalMinutes: null }, // 1 month - ~5000 points
];

interface SamplingControlsProps {
  selectedSampling: string;
  onSamplingChange: (sampling: string) => void;
  totalPoints: number;
  displayedPoints: number;
  isLoading?: boolean;
}

export function SamplingControls({ 
  selectedSampling, 
  onSamplingChange, 
  totalPoints, 
  displayedPoints,
  isLoading = false 
}: SamplingControlsProps) {
  const selectedOption = SAMPLING_OPTIONS.find(opt => opt.value === selectedSampling) || SAMPLING_OPTIONS[0];

  return (
    <div className="bg-gray-50 rounded-lg p-3 space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">
          Data Sampling
        </label>
        <div className="text-xs text-gray-500">
          {displayedPoints.toLocaleString()} points loaded
        </div>
      </div>
      
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
        {SAMPLING_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => onSamplingChange(option.value)}
            disabled={isLoading}
            className={`px-3 py-2 text-xs rounded-md border transition-all mobile-touch-target ${
              selectedSampling === option.value
                ? 'bg-primary-600 text-white border-primary-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 active:bg-gray-100'
            } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {option.label}
          </button>
        ))}
      </div>
      
      {selectedOption && (
        <div className="text-xs text-gray-600 text-center">
          {selectedOption.value === 'Overview' && 'Full dataset with ~5,000 points (auto time resolution)'}
          {selectedOption.value === 'Medium Detail' && 'Last year with ~5,000 points (higher resolution)'}
          {selectedOption.value === 'Full Detail' && 'Last month with ~5,000 points (highest resolution)'}
          {isLoading && (
            <span className="ml-2 text-primary-600">
              <svg className="inline w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Loading...
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// Utility function to downsample data based on time intervals
export function downsampleData<T extends { timestamp_utc: string; water_level?: number }>(
  data: T[],
  intervalMinutes: number | null
): T[] {
  if (!intervalMinutes || data.length === 0) {
    return data; // Return original data if no downsampling needed
  }

  const intervalMs = intervalMinutes * 60 * 1000;
  const result: T[] = [];
  const groups = new Map<number, T[]>();

  // Group data points by time intervals
  data.forEach(point => {
    const timestamp = new Date(point.timestamp_utc).getTime();
    const intervalKey = Math.floor(timestamp / intervalMs) * intervalMs;
    
    if (!groups.has(intervalKey)) {
      groups.set(intervalKey, []);
    }
    groups.get(intervalKey)!.push(point);
  });

  // For each interval, calculate average or select representative point
  Array.from(groups.entries())
    .sort(([a], [b]) => a - b)
    .forEach(([intervalKey, points]) => {
      if (points.length === 1) {
        result.push(points[0]);
      } else {
        // Calculate average water level for the interval
        const validWaterLevels = points
          .map(p => p.water_level)
          .filter(level => level !== undefined && level !== null) as number[];
        
        if (validWaterLevels.length > 0) {
          const avgWaterLevel = validWaterLevels.reduce((sum, level) => sum + level, 0) / validWaterLevels.length;
          
          // Use the first point as template and update water level
          const representative = { ...points[0] };
          if (representative.water_level !== undefined) {
            representative.water_level = avgWaterLevel;
          }
          
          // Use timestamp at the middle of the interval
          representative.timestamp_utc = new Date(intervalKey + intervalMs / 2).toISOString();
          
          result.push(representative);
        }
      }
    });

  return result;
}