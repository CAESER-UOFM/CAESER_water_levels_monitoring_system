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
      <div className="text-xs font-medium text-gray-400">{label}</div>
      <div className={`text-sm font-semibold ${color || 'text-white'}`}>{value}</div>
    </div>
  );

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6 shadow-xl">
      <h3 className="text-lg font-semibold text-white mb-4">Well Information</h3>
      
      {/* Well Static Info */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <InfoItem label="Well Number" value={well.well_number} color="text-cyan-400" />
        <InfoItem label="CAE Number" value={well.cae_number || '—'} />
        <InfoItem label="Aquifer Type" value={well.aquifer_type ? well.aquifer_type.charAt(0).toUpperCase() + well.aquifer_type.slice(1) : '—'} />
        <InfoItem label="Top of Casing" value={well.top_of_casing ? `${well.top_of_casing.toFixed(2)} ft` : '—'} />
      </div>

      {/* Dataset Info */}
      <div className="bg-cyan-900/20 border border-cyan-700/30 rounded-lg p-4">
        <div className="text-sm font-medium text-cyan-300 mb-3">Full Dataset</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <InfoItem 
            label="Total Points Available" 
            value={`${well.total_readings?.toLocaleString() || totalPoints.toLocaleString()} (Manual: ${well.manual_readings_count?.toLocaleString() || 'N/A'})`} 
            color="text-cyan-400" 
          />
          <InfoItem 
            label="Full Data Range" 
            value={currentTimeRange ? 
              `${new Date(currentTimeRange.start).toLocaleDateString()} - ${new Date(currentTimeRange.end).toLocaleDateString()}`
              : 'Loading...'
            } 
          />
          <InfoItem 
            label="Total Span" 
            value={currentTimeRange ? 
              (() => {
                // Use the same calculation method as WellStatisticsPanel for consistency
                const totalDays = Math.round((new Date(currentTimeRange.end).getTime() - new Date(currentTimeRange.start).getTime()) / (1000 * 60 * 60 * 24));
                const years = (totalDays / 365.25).toFixed(1);
                return `${totalDays} days (${years} years)`;
              })()
              : 'Loading...'
            } 
            color="text-gray-600" 
          />
        </div>
      </div>

    </div>
  );
}