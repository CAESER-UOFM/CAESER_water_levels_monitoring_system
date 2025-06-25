'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { Well, WellsQueryParams, PaginatedResponse } from '@/lib/api/api';

interface WellBrowserProps {
  databaseId: string;
  onWellSelected: (well: Well) => void;
}

export function WellBrowser({ databaseId, onWellSelected }: WellBrowserProps) {
  const [wells, setWells] = useState<Well[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedField, setSelectedField] = useState('');
  const [hasDataFilter, setHasDataFilter] = useState<boolean | undefined>(undefined);
  const [sortBy, setSortBy] = useState<'well_number' | 'cae_number' | 'last_reading_date'>('well_number');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalWells, setTotalWells] = useState(0);
  const [wellFields, setWellFields] = useState<string[]>([]);

  const pageSize = 20;

  // Load well fields for filter
  useEffect(() => {
    const loadWellFields = async () => {
      try {
        const response = await fetch(`/.netlify/functions/wells/${databaseId}/fields`);
        const result = await response.json();
        
        if (result.success && result.data) {
          setWellFields(result.data);
        }
      } catch (err) {
        console.error('Error loading well fields:', err);
      }
    };

    loadWellFields();
  }, [databaseId]);

  const loadWells = useCallback(async (params: WellsQueryParams = {}) => {
    try {
      setLoading(true);
      setError(null);

      // Build query parameters
      const queryParams = new URLSearchParams({
        page: currentPage.toString(),
        limit: pageSize.toString(),
        ...(params.search && { search: params.search }),
        ...(params.field && { field: params.field }),
        ...(params.hasData !== undefined && { hasData: params.hasData.toString() }),
        ...(params.sortBy && { sortBy: params.sortBy }),
        ...(params.sortOrder && { sortOrder: params.sortOrder })
      });

      const response = await fetch(`/.netlify/functions/wells/${databaseId}?${queryParams}`);
      const result: PaginatedResponse<Well> = await response.json();

      if (result.success && result.data) {
        setWells(result.data);
        setTotalPages(result.pagination.totalPages);
        setTotalWells(result.pagination.total);
      } else {
        throw new Error(result.error || 'Failed to load wells');
      }
    } catch (err) {
      console.error('Error loading wells:', err);
      setError(err instanceof Error ? err.message : 'Failed to load wells');
      setWells([]);
    } finally {
      setLoading(false);
    }
  }, [databaseId, currentPage, pageSize]);

  // Load wells when filters change
  useEffect(() => {
    const params: WellsQueryParams = {
      search: searchTerm || undefined,
      field: selectedField || undefined,
      hasData: hasDataFilter,
      sortBy,
      sortOrder
    };

    loadWells(params);
  }, [loadWells, searchTerm, selectedField, hasDataFilter, sortBy, sortOrder]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedField, hasDataFilter]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchTerm(value);
  }, []);

  const handleFieldChange = useCallback((value: string) => {
    setSelectedField(value);
  }, []);

  const handleDataFilterChange = useCallback((value: string) => {
    setHasDataFilter(value === '' ? undefined : value === 'true');
  }, []);

  const handleSortChange = useCallback((field: 'well_number' | 'cae_number' | 'last_reading_date') => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  }, [sortBy]);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'No data';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
        </svg>
      );
    }
    
    return sortOrder === 'asc' ? (
      <svg className="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 15l4-4 4 4" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 9l-4 4-4-4" />
      </svg>
    );
  };

  if (error) {
    return (
      <div className="text-center py-12">
        <svg className="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Error Loading Wells
        </h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={() => loadWells()}
          className="btn-primary"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Well Browser</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Search Wells
            </label>
            <div className="relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Well number, CAE, field..."
                className="input-field pl-10"
              />
              <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          {/* Field Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Well Field
            </label>
            <select
              value={selectedField}
              onChange={(e) => handleFieldChange(e.target.value)}
              className="input-field"
            >
              <option value="">All Fields</option>
              {wellFields.map(field => (
                <option key={field} value={field}>{field}</option>
              ))}
            </select>
          </div>

          {/* Data Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Availability
            </label>
            <select
              value={hasDataFilter === undefined ? '' : hasDataFilter.toString()}
              onChange={(e) => handleDataFilterChange(e.target.value)}
              className="input-field"
            >
              <option value="">All Wells</option>
              <option value="true">With Data</option>
              <option value="false">No Data</option>
            </select>
          </div>

          {/* Results Count */}
          <div className="flex items-end">
            <div className="text-sm text-gray-600">
              <span className="font-medium">{totalWells}</span> wells found
              {totalPages > 1 && (
                <span className="block text-xs">
                  Page {currentPage} of {totalPages}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Wells Table */}
      <div className="card">
        {loading ? (
          <div className="text-center py-12">
            <LoadingSpinner size="large" />
            <p className="mt-4 text-gray-600">Loading wells...</p>
          </div>
        ) : wells.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Wells Found
            </h3>
            <p className="text-gray-600">
              Try adjusting your search criteria or filters
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th 
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 mobile-touch-target"
                    onClick={() => handleSortChange('well_number')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Well Number</span>
                      {getSortIcon('well_number')}
                    </div>
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 mobile-touch-target"
                    onClick={() => handleSortChange('cae_number')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>CAE Number</span>
                      {getSortIcon('cae_number')}
                    </div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Field
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Readings
                  </th>
                  <th 
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 mobile-touch-target"
                    onClick={() => handleSortChange('last_reading_date')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Last Reading</span>
                      {getSortIcon('last_reading_date')}
                    </div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {wells.map((well) => (
                  <tr 
                    key={well.well_number}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => onWellSelected(well)}
                  >
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {well.well_number}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                      {well.cae_number || '—'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                      {well.well_field || '—'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                      <div className="flex items-center space-x-4">
                        <span className="font-medium">{well.total_readings || 0}</span>
                        <div className="flex space-x-1">
                          {well.has_transducer_data && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800" title="Has transducer data">
                              T
                            </span>
                          )}
                          {well.has_manual_readings && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800" title="Has manual readings">
                              M
                            </span>
                          )}
                          {well.has_telemetry_data && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800" title="Has telemetry data">
                              Tel
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                      {formatDate(well.last_reading_date)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onWellSelected(well);
                        }}
                        className="text-primary-600 hover:text-primary-800 font-medium mobile-touch-target"
                      >
                        View Data →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-3 sm:px-6">
            <div className="flex justify-between sm:hidden">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span>
                  {' '}to{' '}
                  <span className="font-medium">
                    {Math.min(currentPage * pageSize, totalWells)}
                  </span>
                  {' '}of{' '}
                  <span className="font-medium">{totalWells}</span>
                  {' '}results
                </p>
              </div>
              <div>
                <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clipRule="evenodd" />
                    </svg>
                  </button>
                  
                  {/* Page numbers */}
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const page = i + 1;
                    return (
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                          currentPage === page
                            ? 'z-10 bg-primary-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600'
                            : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                        }`}
                      >
                        {page}
                      </button>
                    );
                  })}

                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                    </svg>
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}