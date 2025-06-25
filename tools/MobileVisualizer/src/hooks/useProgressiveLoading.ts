'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import type { WaterLevelReading } from '@/lib/api/api';

export interface LoadedDataSegment {
  level: 1 | 2 | 3;
  data: WaterLevelReading[];
  startDate?: string;
  endDate?: string;
  loadedAt: Date;
  viewport?: {
    start: Date;
    end: Date;
  };
}

export interface ProgressiveLoadingState {
  segments: LoadedDataSegment[];
  currentLevel: 1 | 2 | 3;
  isLoading: boolean;
  error: string | null;
  totalDataPoints: number;
}

export interface UseProgressiveLoadingOptions {
  databaseId: string;
  wellNumber: string;
  onError?: (error: string) => void;
}

export function useProgressiveLoading({
  databaseId,
  wellNumber,
  onError
}: UseProgressiveLoadingOptions) {
  const [state, setState] = useState<ProgressiveLoadingState>({
    segments: [],
    currentLevel: 1,
    isLoading: false,
    error: null,
    totalDataPoints: 0
  });

  // Cache for loaded segments to avoid re-requests
  const [cache] = useState(new Map<string, LoadedDataSegment>());

  // Generate cache key for a data request
  const getCacheKey = useCallback((level: 1 | 2 | 3, startDate?: string, endDate?: string) => {
    return `${level}-${startDate || 'all'}-${endDate || 'all'}`;
  }, []);

  // Load data for a specific level
  const loadDataLevel = useCallback(async (
    level: 1 | 2 | 3,
    startDate?: string,
    endDate?: string,
    viewport?: { start: Date; end: Date }
  ) => {
    const cacheKey = getCacheKey(level, startDate, endDate);
    
    // Check cache first
    const cached = cache.get(cacheKey);
    if (cached) {
      console.log(`📋 Using cached data for level ${level}`);
      return cached.data;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const params = new URLSearchParams({
        level: level.toString(),
        ...(startDate && { startDate }),
        ...(endDate && { endDate }),
        // Add cache buster to force fresh API calls
        v: Date.now().toString()
      });

      const response = await fetch(`/.netlify/functions/data/${databaseId}/water/${wellNumber}?${params}`, {
        signal: AbortSignal.timeout(30000) // 30 second timeout
      });

      if (!response.ok) {
        if (response.status === 502 || response.status === 504) {
          throw new Error(`Server timeout for level ${level} - try a smaller date range`);
        }
        throw new Error(`Failed to load level ${level}: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      if (!result.success || !result.data) {
        throw new Error(result.error || `Failed to load level ${level} data`);
      }

      const data = result.data as WaterLevelReading[];
      console.log(`📊 Loaded level ${level}: ${data.length} points (expected: ${level === 1 ? '~5000' : level === 2 ? '~12000' : '~25000'})`);

      // Create segment
      const segment: LoadedDataSegment = {
        level,
        data,
        startDate,
        endDate,
        loadedAt: new Date(),
        viewport
      };

      // Cache the segment
      cache.set(cacheKey, segment);

      // Update state
      setState(prev => ({
        ...prev,
        segments: [...prev.segments.filter(s => s.level !== level || s.startDate !== startDate || s.endDate !== endDate), segment],
        currentLevel: level,
        totalDataPoints: prev.totalDataPoints + data.length,
        isLoading: false
      }));

      return data;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to load level ${level} data`;
      console.error('Progressive loading error:', errorMessage);
      
      setState(prev => ({ 
        ...prev, 
        isLoading: false, 
        error: errorMessage 
      }));
      
      if (onError) {
        onError(errorMessage);
      }
      
      throw err;
    }
  }, [databaseId, wellNumber, cache, getCacheKey, onError]);

  // Get current best data for display
  const getCurrentData = useCallback(() => {
    if (state.segments.length === 0) return [];

    // Return the highest level data available
    const sortedSegments = [...state.segments].sort((a, b) => b.level - a.level);
    return sortedSegments[0]?.data || [];
  }, [state.segments]);

  // Load initial overview data
  const loadOverview = useCallback(async () => {
    console.log('🚀 Loading overview (Level 1) - expecting ~5000 points');
    return loadDataLevel(1);
  }, [loadDataLevel]);

  // Load medium detail for specific time range
  const loadMediumDetail = useCallback(async (startDate: string, endDate: string) => {
    const viewport = { start: new Date(startDate), end: new Date(endDate) };
    return loadDataLevel(2, startDate, endDate, viewport);
  }, [loadDataLevel]);

  // Load full detail for specific time range
  const loadFullDetail = useCallback(async (startDate: string, endDate: string) => {
    const viewport = { start: new Date(startDate), end: new Date(endDate) };
    return loadDataLevel(3, startDate, endDate, viewport);
  }, [loadDataLevel]);

  // Determine the appropriate detail level based on time span
  const getDetailLevelForTimeSpan = useCallback((timeSpanDays: number): 1 | 2 | 3 => {
    if (timeSpanDays < 30) {
      return 3; // Full detail for < 30 days
    } else if (timeSpanDays < 365) {
      return 2; // Medium detail for < 1 year
    } else {
      return 1; // Overview for > 1 year
    }
  }, []);

  // Smart loading based on viewport
  const loadForViewport = useCallback(async (viewport: { start: Date; end: Date }) => {
    const timeSpanMs = viewport.end.getTime() - viewport.start.getTime();
    const timeSpanDays = timeSpanMs / (1000 * 60 * 60 * 24);
    
    // Determine the appropriate level based on time span
    let targetLevel: 1 | 2 | 3;
    if (timeSpanDays < 30) {
      targetLevel = 3; // Full detail for < 30 days
    } else if (timeSpanDays < 365) {
      targetLevel = 2; // Medium detail for < 1 year
    } else {
      targetLevel = 1; // Overview for > 1 year
    }
    
    console.log(`🔍 Viewport loading: ${timeSpanDays.toFixed(1)} days → Level ${targetLevel}`, viewport);
    
    const startDate = viewport.start.toISOString();
    const endDate = viewport.end.toISOString();

    // Always load the appropriate level for the viewport
    try {
      switch (targetLevel) {
        case 3:
          return await loadFullDetail(startDate, endDate);
        case 2:
          return await loadMediumDetail(startDate, endDate);
        case 1:
        default:
          return await loadDataLevel(1, startDate, endDate, viewport);
      }
    } catch (err) {
      console.error('Viewport loading failed, using current data:', err);
      return getCurrentData();
    }
  }, [loadDataLevel, loadMediumDetail, loadFullDetail, getCurrentData]);

  // Clear cache and reset
  const reset = useCallback(() => {
    console.log('🗑️ Clearing progressive loading cache and resetting state');
    cache.clear();
    setState({
      segments: [],
      currentLevel: 1,
      isLoading: false,
      error: null,
      totalDataPoints: 0
    });
  }, [cache]);

  // Get loading statistics
  const stats = useMemo(() => {
    const totalSegments = state.segments.length;
    const levelCounts = state.segments.reduce((acc, segment) => {
      acc[segment.level] = (acc[segment.level] || 0) + 1;
      return acc;
    }, {} as Record<1 | 2 | 3, number>);

    return {
      totalSegments,
      levelCounts,
      currentLevel: state.currentLevel,
      totalDataPoints: state.totalDataPoints,
      cacheSize: cache.size
    };
  }, [state.segments, state.currentLevel, state.totalDataPoints, cache.size]);

  return {
    // Data
    currentData: getCurrentData(),
    segments: state.segments,
    
    // State
    currentLevel: state.currentLevel,
    isLoading: state.isLoading,
    error: state.error,
    stats,
    
    // Actions
    loadOverview,
    loadMediumDetail,
    loadFullDetail,
    loadForViewport,
    reset,
    
    // Utilities
    getDetailLevelForTimeSpan
  };
}