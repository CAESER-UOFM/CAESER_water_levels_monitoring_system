'use client';

import React from 'react';
import type { Well } from '@/lib/api/api';

interface WellInfoPanelProps {
  well: Well;
  currentTimeRange?: {
    start: string;
    end: string;
  } | null;
  totalPoints: number;
  displayedPoints: number;
  samplingRate: string;
}

export function WellInfoPanel({ 
  well, 
  currentTimeRange, 
  totalPoints, 
  displayedPoints,
  samplingRate 
}: WellInfoPanelProps) {
  const InfoItem = ({ label, value, color }: { label: string; value: string | number; color?: string }) => (
    <div>
      <div className="text-xs font-medium text-gray-500">{label}</div>
      <div className={`text-sm font-semibold ${color || 'text-gray-900'}`}>{value}</div>
    </div>
  );

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Well Information</h3>
      
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {/* Basic Well Info */}
        <InfoItem label="Well Number" value={well.well_number} color="text-primary-600" />
        <InfoItem label="CAE Number" value={well.cae_number || '—'} />
        <InfoItem label="Aquifer Type" value={well.aquifer_type ? well.aquifer_type.charAt(0).toUpperCase() + well.aquifer_type.slice(1) : '—'} />
        
        {/* Data Overview */}
        <InfoItem 
          label="Total Points" 
          value={totalPoints.toLocaleString()} 
          color="text-blue-600" 
        />
        
        {/* Current View Info */}
        <InfoItem 
          label="Displayed Points" 
          value={displayedPoints.toLocaleString()} 
          color="text-green-600" 
        />
        
        <InfoItem 
          label="Sampling Rate" 
          value={samplingRate} 
          color="text-purple-600" 
        />

        {/* Technical Details */}
        {well.top_of_casing && (
          <InfoItem 
            label="Top of Casing" 
            value={`${well.top_of_casing.toFixed(2)} ft`} 
          />
        )}

        {well.well_field && (
          <InfoItem 
            label="Field" 
            value={well.well_field} 
          />
        )}
      </div>

      {/* Current Time Range */}
      {currentTimeRange && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-xs font-medium text-gray-500 mb-2">Current Time Range</div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-mono text-gray-700">{currentTimeRange.start}</span>
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
              <span className="font-mono text-gray-700">{currentTimeRange.end}</span>
            </div>
          </div>
        </div>
      )}

      {/* Data Availability Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="text-xs font-medium text-gray-500 mb-3">Data Availability</div>
        <div className="flex items-center space-x-4">
          {well.has_transducer_data && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-xs text-gray-600">Transducer</span>
            </div>
          )}
          {well.has_telemetry_data && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span className="text-xs text-gray-600">Telemetry</span>
            </div>
          )}
          {well.has_manual_readings && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-xs text-gray-600">Manual</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}