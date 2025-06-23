'use client';

import { useState, useCallback } from 'react';
import { DatabaseSelector } from '@/components/DatabaseSelector';
import { DatabaseUpload } from '@/components/DatabaseUpload';
import type { DatabaseInfo } from '@/types/database';

export default function HomePage() {
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseInfo | null>(null);
  const [uploadedDatabases, setUploadedDatabases] = useState<DatabaseInfo[]>([]);

  const handleDatabaseUploaded = useCallback((database: DatabaseInfo) => {
    setUploadedDatabases(prev => [...prev, database]);
  }, []);

  const handleDatabaseSelected = useCallback((database: DatabaseInfo) => {
    setSelectedDatabase(database);
    // Redirect to wells page
    window.location.href = `/wells/${database.id}`;
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Water Level Visualizer
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Mobile-optimized visualization of groundwater monitoring data. 
            Upload your database or select from previously uploaded files.
          </p>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          {/* Database Upload Section */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                Upload Database
              </h2>
              <span className="text-sm text-gray-500">
                SQLite files (.db, .sqlite)
              </span>
            </div>
            <DatabaseUpload onDatabaseUploaded={handleDatabaseUploaded} />
          </div>

          {/* Database Selection Section */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                Select Database
              </h2>
              <span className="text-sm text-gray-500">
                {uploadedDatabases.length} available
              </span>
            </div>
            <DatabaseSelector
              databases={uploadedDatabases}
              onDatabaseSelected={handleDatabaseSelected}
            />
          </div>

          {/* Quick Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-blue-900 mb-1">
                  Getting Started
                </h3>
                <div className="text-sm text-blue-700 space-y-1">
                  <p>• Upload a SQLite database file containing water level monitoring data</p>
                  <p>• Browse wells and view time-series plots</p>
                  <p>• Export data in CSV or JSON format</p>
                  <p>• View recharge calculation results (if available)</p>
                </div>
              </div>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Interactive Plots</h3>
              </div>
              <p className="text-gray-600 text-sm">
                Touch-optimized charts with zoom, pan, and detailed data tooltips. 
                View water levels, temperature, and manual readings.
              </p>
            </div>

            <div className="card">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <h3 className="font-semibold text-gray-900">Data Export</h3>
              </div>
              <p className="text-gray-600 text-sm">
                Download filtered data in CSV or JSON format. 
                Customize date ranges and data types for your analysis.
              </p>
            </div>

            <div className="card">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Well Browser</h3>
              </div>
              <p className="text-gray-600 text-sm">
                Search and filter wells by number, field, or data availability. 
                Quick access to well metadata and recent readings.
              </p>
            </div>

            <div className="card">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Recharge Results</h3>
              </div>
              <p className="text-gray-600 text-sm">
                View existing recharge calculations from RISE, MRC, and EMR methods. 
                Display results with detailed calculation metadata.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}