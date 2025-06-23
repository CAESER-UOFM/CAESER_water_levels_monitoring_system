'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { databaseManager } from '@/lib/database';
import { exportRechargeResultsToCSV, exportRechargeResultsToJSON, exportRechargeResultsToPDF } from '@/utils/dataExport';
import type { Well, RechargeResult } from '@/types/database';

export default function RechargeResultsPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;
  const wellNumber = params.wellNumber as string;

  const [well, setWell] = useState<Well | null>(null);
  const [rechargeResults, setRechargeResults] = useState<RechargeResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRechargeData = async () => {
      try {
        setLoading(true);
        setError(null);

        const db = databaseManager.getDatabase(databaseId);
        if (!db) {
          throw new Error('Database not available');
        }

        // Load well metadata
        const wellData = await db.getWell(wellNumber);
        if (!wellData) {
          throw new Error('Well not found');
        }
        setWell(wellData);

        // Load recharge results
        const results = await db.getRechargeResults(wellNumber);
        setRechargeResults(results);

      } catch (err) {
        console.error('Error loading recharge data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load recharge data');
      } finally {
        setLoading(false);
      }
    };

    loadRechargeData();
  }, [databaseId, wellNumber]);

  const handleBackToPlot = useCallback(() => {
    router.push(`/wells/${databaseId}/plot/${wellNumber}`);
  }, [databaseId, wellNumber, router]);

  const handleBackToWells = useCallback(() => {
    router.push(`/wells/${databaseId}`);
  }, [databaseId, router]);

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatRechargeValue = (value?: number, unit: string = 'mm'): string => {
    if (value === undefined || value === null) return '—';
    return `${value.toFixed(2)} ${unit}`;
  };

  const handleExportCSV = useCallback(async () => {
    if (!well || rechargeResults.length === 0) return;
    
    try {
      exportRechargeResultsToCSV(rechargeResults, well);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Failed to export CSV file. Please try again.');
    }
  }, [well, rechargeResults]);

  const handleExportJSON = useCallback(async () => {
    if (!well || rechargeResults.length === 0) return;
    
    try {
      exportRechargeResultsToJSON(rechargeResults, well);
    } catch (error) {
      console.error('Error exporting JSON:', error);
      alert('Failed to export JSON file. Please try again.');
    }
  }, [well, rechargeResults]);

  const handleExportPDF = useCallback(async () => {
    if (!well || rechargeResults.length === 0) return;
    
    try {
      exportRechargeResultsToPDF(rechargeResults, well);
    } catch (error) {
      console.error('Error exporting PDF:', error);
      alert('Failed to export PDF report. Please try again.');
    }
  }, [well, rechargeResults]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Loading recharge results...</p>
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
            Error Loading Results
          </h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-3">
            <button onClick={handleBackToWells} className="btn-secondary">
              ← Back to Wells
            </button>
            <button onClick={() => window.location.reload()} className="btn-primary">
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleBackToPlot}
                className="p-2 text-gray-600 hover:text-gray-900 transition-colors mobile-touch-target"
                title="Back to plot"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Recharge Results - Well {well?.well_number}
                </h1>
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  {well?.cae_number && <span>CAE: {well.cae_number}</span>}
                  {well?.well_field && <span>Field: {well.well_field}</span>}
                  <span>{rechargeResults.length} calculation{rechargeResults.length !== 1 ? 's' : ''}</span>
                </div>
              </div>
            </div>
            
            <button
              onClick={handleBackToPlot}
              className="btn-outline text-sm px-3 py-2"
            >
              View Plot
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {rechargeResults.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Recharge Results Available
            </h3>
            <p className="text-gray-600 mb-4">
              No recharge calculations have been performed for this well.
            </p>
            <button
              onClick={handleBackToPlot}
              className="btn-primary"
            >
              View Water Level Data
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Results Overview */}
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Recharge Calculation Summary
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {['RISE', 'MRC', 'EMR'].map(method => {
                  const methodResults = rechargeResults.filter(r => r.method === method);
                  const latestResult = methodResults.sort((a, b) => 
                    new Date(b.calculation_date).getTime() - new Date(a.calculation_date).getTime()
                  )[0];
                  
                  return (
                    <div key={method} className="bg-gray-50 rounded-lg p-4">
                      <h3 className="font-medium text-gray-900 mb-2">{method} Method</h3>
                      {latestResult ? (
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Latest:</span>
                            <span className="font-medium">{formatDate(latestResult.calculation_date)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Recharge:</span>
                            <span className="font-medium text-primary-600">
                              {formatRechargeValue(latestResult.recharge_mm)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Calculations:</span>
                            <span className="font-medium">{methodResults.length}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No calculations</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Detailed Results */}
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                All Recharge Calculations
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Method
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Calculation Date
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Period
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Recharge (mm)
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Recharge (in)
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Specific Yield
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {rechargeResults
                      .sort((a, b) => new Date(b.calculation_date).getTime() - new Date(a.calculation_date).getTime())
                      .map((result, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            result.method === 'RISE' ? 'bg-blue-100 text-blue-800' :
                            result.method === 'MRC' ? 'bg-green-100 text-green-800' :
                            'bg-purple-100 text-purple-800'
                          }`}>
                            {result.method}
                          </span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatDate(result.calculation_date)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                          {formatDate(result.start_date)} - {formatDate(result.end_date)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {formatRechargeValue(result.recharge_mm)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                          {formatRechargeValue(result.recharge_inches, 'in')}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                          {result.specific_yield ? result.specific_yield.toFixed(3) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Method Information */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="card">
                <h3 className="font-semibold text-gray-900 mb-3">RISE Method</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Recharge Investigation and Simulation Tool - automated water table fluctuation method.
                </p>
                <div className="text-xs text-gray-500">
                  <p>• Automated calculation</p>
                  <p>• Statistical analysis</p>
                  <p>• Quality control filters</p>
                </div>
              </div>

              <div className="card">
                <h3 className="font-semibold text-gray-900 mb-3">MRC Method</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Manual Recharge Calculation - user-defined parameters and periods.
                </p>
                <div className="text-xs text-gray-500">
                  <p>• Manual parameter selection</p>
                  <p>• Custom time periods</p>
                  <p>• User-defined specific yield</p>
                </div>
              </div>

              <div className="card">
                <h3 className="font-semibold text-gray-900 mb-3">EMR Method</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Enhanced Manual Recharge - advanced manual calculation with additional parameters.
                </p>
                <div className="text-xs text-gray-500">
                  <p>• Enhanced parameter control</p>
                  <p>• Advanced filtering options</p>
                  <p>• Detailed quality assessment</p>
                </div>
              </div>
            </div>

            {/* Export Options */}
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-3">Export Results</h3>
              <p className="text-sm text-gray-600 mb-4">
                Download recharge calculation results for further analysis.
              </p>
              <div className="flex flex-wrap gap-3">
                <button 
                  className="btn-outline"
                  onClick={handleExportCSV}
                  disabled={rechargeResults.length === 0}
                >
                  📊 Export CSV
                </button>
                <button 
                  className="btn-outline"
                  onClick={handleExportJSON}
                  disabled={rechargeResults.length === 0}
                >
                  📋 Export JSON
                </button>
                <button 
                  className="btn-outline"
                  onClick={handleExportPDF}
                  disabled={rechargeResults.length === 0}
                >
                  📄 Export Report
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}