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
    viewport?: { start: Date; end: Date },
    backgroundMode = false // If true, don't update current state
  ) => {
    const cacheKey = getCacheKey(level, startDate, endDate);
    
    // Check cache first
    const cached = cache.get(cacheKey);
    if (cached) {
      console.log(`📋 Using cached data for level ${level}`);
      return cached.data;
    }

    // Check if already loading this specific request
    const loadingKey = `loading-${cacheKey}`;
    if (cache.has(loadingKey)) {
      console.log(`⏳ Already loading ${cacheKey}, skipping duplicate request`);
      return [];
    }
    
    // Mark as loading
    cache.set(loadingKey, { data: [], loadedAt: new Date(), level } as any);

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

      // Cache the segment and clear loading flag
      cache.set(cacheKey, segment);
      cache.delete(`loading-${cacheKey}`);

      // Update state only if not in background mode
      if (!backgroundMode) {
        setState(prev => {
          const existingSegments = prev.segments.filter(s => !(s.level === level && s.startDate === startDate && s.endDate === endDate));
          return {
            ...prev,
            segments: [...existingSegments, segment],
            currentLevel: level,
            totalDataPoints: existingSegments.reduce((sum, s) => sum + s.data.length, 0) + data.length,
            isLoading: false
          };
        });
      } else {
        // In background mode, just clear loading state but don't update segments
        setState(prev => ({ ...prev, isLoading: false }));
      }

      return data;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to load level ${level} data`;
      console.error('Progressive loading error:', errorMessage);
      
      // Clear loading flag on error
      cache.delete(`loading-${cacheKey}`);
      
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

  // Load initial overview data (full dataset)
  const loadOverview = useCallback(async () => {
    console.log('🚀 Loading overview - expecting ~5000 points for full dataset');
    return loadDataLevel(1);
  }, [loadDataLevel]);

  // Load data for specific time range (always ~5000 points)
  const loadForTimeRange = useCallback(async (startDate: string, endDate: string) => {
    const viewport = { start: new Date(startDate), end: new Date(endDate) };
    const timeSpanDays = (viewport.end.getTime() - viewport.start.getTime()) / (1000 * 60 * 60 * 24);
    console.log(`🚀 Loading ${timeSpanDays.toFixed(1)} days - expecting ~5000 points for time range`);
    return loadDataLevel(1, startDate, endDate, viewport);
  }, [loadDataLevel]);


  // Background viewport loading with caching - loads but doesn't auto-apply to prevent loops
  const loadForViewport = useCallback(async (viewport: { start: Date; end: Date }) => {
    const timeSpanMs = viewport.end.getTime() - viewport.start.getTime();
    const timeSpanDays = timeSpanMs / (1000 * 60 * 60 * 24);
    
    const startDate = viewport.start.toISOString();
    const endDate = viewport.end.toISOString();
    
    // Check if we already have this exact time range cached
    const cacheKey = getCacheKey(1, startDate, endDate);
    const cached = cache.get(cacheKey);
    
    if (cached) {
      console.log(`📋 Smart cache hit for ${timeSpanDays.toFixed(1)} days - data ready`);
      // DON'T update current state to avoid infinite loops
      // Just return the cached data for potential future use
      return cached.data;
    }
    
    console.log(`🔍 Background viewport loading: ${timeSpanDays.toFixed(1)} days → ~5000 points`);
    console.log(`🚀 Loading fresh data for ${timeSpanDays.toFixed(1)} days - expecting ~5000 points`);

    // Load fresh data in background mode - caches but doesn't update current view
    try {
      const viewportData = { start: viewport.start, end: viewport.end };
      const data = await loadDataLevel(1, startDate, endDate, viewportData, true); // background mode = true
      console.log(`💾 Background data loaded and cached for ${timeSpanDays.toFixed(1)} days`);
      return data;
    } catch (err) {
      console.error('Background loading failed:', err);
      return [];
    }
  }, [loadDataLevel, cache, getCacheKey]);

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
    loadForTimeRange,
    loadForViewport,
    reset
  };
}