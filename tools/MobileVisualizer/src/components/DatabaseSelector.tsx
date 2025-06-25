'use client';

import { useState, useEffect } from 'react';
import type { DatabaseInfo } from '@/types/database';

interface DatabaseSelectorProps {
  databases: DatabaseInfo[];
  onDatabaseSelected: (database: DatabaseInfo) => void;
}

export function DatabaseSelector({ databases, onDatabaseSelected }: DatabaseSelectorProps) {
  const [allDatabases, setAllDatabases] = useState<DatabaseInfo[]>(databases);
  const [selectedId, setSelectedId] = useState<string>('');

  // Load databases from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('uploaded_databases');
      if (stored) {
        const storedDatabases = JSON.parse(stored) as DatabaseInfo[];
        setAllDatabases(prev => {
          // Merge with prop databases, avoiding duplicates
          const combined = [...prev];
          storedDatabases.forEach(db => {
            if (!combined.find(existing => existing.id === db.id)) {
              combined.push(db);
            }
          });
          return combined.sort((a, b) => new Date(b.uploadDate).getTime() - new Date(a.uploadDate).getTime());
        });
      }
    } catch (error) {
      console.error('Error loading stored databases:', error);
    }
  }, []);

  // Update when prop databases change
  useEffect(() => {
    setAllDatabases(prev => {
      const combined = [...prev];
      databases.forEach(db => {
        if (!combined.find(existing => existing.id === db.id)) {
          combined.push(db);
        }
      });
      return combined.sort((a, b) => new Date(b.uploadDate).getTime() - new Date(a.uploadDate).getTime());
    });
  }, [databases]);

  const handleDatabaseSelect = (database: DatabaseInfo) => {
    setSelectedId(database.id);
    // Don't immediately navigate - wait for button click
  };

  const handleNavigate = () => {
    const selected = allDatabases.find(db => db.id === selectedId);
    if (selected) {
      onDatabaseSelected(selected);
    }
  };

  const handleDelete = (databaseId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    
    if (confirm('Are you sure you want to delete this database? This action cannot be undone.')) {
      try {
        // Remove from localStorage
        localStorage.removeItem(`db_${databaseId}`);
        
        // Update stored databases list
        const stored = localStorage.getItem('uploaded_databases');
        if (stored) {
          const storedDatabases = JSON.parse(stored) as DatabaseInfo[];
          const filtered = storedDatabases.filter(db => db.id !== databaseId);
          localStorage.setItem('uploaded_databases', JSON.stringify(filtered));
        }
        
        // Update local state
        setAllDatabases(prev => prev.filter(db => db.id !== databaseId));
        
        if (selectedId === databaseId) {
          setSelectedId('');
        }
      } catch (error) {
        console.error('Error deleting database:', error);
        alert('Failed to delete database. Please try again.');
      }
    }
  };

  const formatFileSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (allDatabases.length === 0) {
    return (
      <div className="text-center py-8">
        <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-1">
          No databases available
        </h3>
        <p className="text-gray-600 mb-4">
          Upload a database file to get started with visualization
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {allDatabases.map((database) => (
        <div
          key={database.id}
          className={`
            relative border rounded-lg p-4 cursor-pointer transition-all duration-200
            ${selectedId === database.id 
              ? 'border-primary-500 bg-primary-50 shadow-md' 
              : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
            }
          `}
          onClick={() => handleDatabaseSelect(database)}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg 
                    className={`w-8 h-8 ${selectedId === database.id ? 'text-primary-600' : 'text-gray-400'}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-medium text-gray-900 truncate">
                    {database.name}
                  </h3>
                  <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                    <span className="flex items-center space-x-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                      <span>{database.wellsCount} wells</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span>{formatFileSize(database.size)}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>{formatDate(database.uploadDate)}</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Delete Button - only show for uploaded databases, not main production database */}
            {database.id !== 'caeser-water-monitoring' && (
              <button
                onClick={(e) => handleDelete(database.id, e)}
                className="flex-shrink-0 ml-3 p-2 text-gray-400 hover:text-red-600 transition-colors duration-200 mobile-touch-target"
                title="Delete database"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>

          {/* Filename */}
          <div className="mt-2 pt-2 border-t border-gray-100">
            <p className="text-xs text-gray-500 truncate">
              <span className="font-medium">File:</span> {database.filename}
            </p>
          </div>

          {/* Selection Indicator */}
          {selectedId === database.id && (
            <div className="absolute top-2 right-2">
              <svg className="w-5 h-5 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
          )}
        </div>
      ))}

      {/* Selection Action */}
      {selectedId && (
        <div className="flex justify-center pt-4">
          <button
            onClick={handleNavigate}
            className="btn-primary mobile-touch-target px-8"
          >
            Continue to Wells →
          </button>
        </div>
      )}
    </div>
  );
}