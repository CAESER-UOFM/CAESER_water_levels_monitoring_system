'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { WellBrowser } from '@/components/WellBrowser';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { databaseManager } from '@/lib/database';
import type { DatabaseInfo, Well } from '@/types/database';

export default function WellsPage() {
  const params = useParams();
  const router = useRouter();
  const databaseId = params.id as string;

  const [database, setDatabase] = useState<DatabaseInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load database on mount
  useEffect(() => {
    const loadDatabase = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get database metadata
        const stored = localStorage.getItem('uploaded_databases');
        if (!stored) {
          throw new Error('No databases found');
        }

        const databases = JSON.parse(stored) as DatabaseInfo[];
        const dbInfo = databases.find(db => db.id === databaseId);
        
        if (!dbInfo) {
          throw new Error('Database not found');
        }

        setDatabase(dbInfo);

        // Load database data
        const dbData = localStorage.getItem(`db_${databaseId}`);
        if (!dbData) {
          throw new Error('Database data not found');
        }

        const dataArray = JSON.parse(dbData) as number[];
        const arrayBuffer = new Uint8Array(dataArray).buffer;
        
        await databaseManager.loadDatabase(databaseId, arrayBuffer);
        
      } catch (err) {
        console.error('Error loading database:', err);
        setError(err instanceof Error ? err.message : 'Failed to load database');
      } finally {
        setLoading(false);
      }
    };

    loadDatabase();

    // Cleanup on unmount
    return () => {
      databaseManager.closeDatabase(databaseId);
    };
  }, [databaseId]);

  const handleWellSelected = useCallback((well: Well) => {
    router.push(`/wells/${databaseId}/plot/${well.well_number}`);
  }, [databaseId, router]);

  const handleBackToDatabases = useCallback(() => {
    router.push('/');
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Loading database...</p>
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
            Database Error
          </h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={handleBackToDatabases}
            className="btn-primary"
          >
            ← Back to Databases
          </button>
        </div>
      </div>
    );
  }

  if (!database) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleBackToDatabases}
                className="p-2 text-gray-600 hover:text-gray-900 transition-colors mobile-touch-target"
                title="Back to databases"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {database.name}
                </h1>
                <p className="text-sm text-gray-600">
                  {database.wellsCount} wells available
                </p>
              </div>
            </div>
            
            {/* Database Info Badge */}
            <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-500">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              <span>Database</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <WellBrowser
          databaseId={databaseId}
          onWellSelected={handleWellSelected}
        />
      </div>
    </div>
  );
}