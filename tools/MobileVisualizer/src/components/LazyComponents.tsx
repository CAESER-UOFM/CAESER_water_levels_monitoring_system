'use client';

import dynamic from 'next/dynamic';
import { LoadingSpinner } from './LoadingSpinner';

// Loading fallback component
const ComponentLoadingFallback = ({ name }: { name: string }) => (
  <div className="flex items-center justify-center p-8">
    <div className="text-center">
      <LoadingSpinner size="large" className="mx-auto mb-4" />
      <p className="text-gray-400 text-sm">Loading {name}...</p>
    </div>
  </div>
);

// Lazy load heavy components with loading fallbacks
export const LazyDatabaseSelector = dynamic(
  () => import('./DatabaseSelector').then(mod => ({ default: mod.DatabaseSelector })),
  {
    loading: () => <ComponentLoadingFallback name="Database Selector" />,
    ssr: false
  }
);

export const LazyWaterLevelChart = dynamic(
  () => import('./WaterLevelChart').then(mod => ({ default: mod.WaterLevelChart })),
  {
    loading: () => <ComponentLoadingFallback name="Chart Component" />,
    ssr: false
  }
);

export const LazyWellsMap = dynamic(
  () => import('./WellsMap'),
  {
    loading: () => <ComponentLoadingFallback name="Map Component" />,
    ssr: false
  }
);

export const LazyChartJSTimeSeriesChart = dynamic(
  () => import('./ChartJSTimeSeriesChart').then(mod => ({ default: mod.ChartJSTimeSeriesChart })),
  {
    loading: () => <ComponentLoadingFallback name="Advanced Chart" />,
    ssr: false
  }
);

export const LazySmartWaterLevelChart = dynamic(
  () => import('./SmartWaterLevelChart').then(mod => ({ default: mod.SmartWaterLevelChart })),
  {
    loading: () => <ComponentLoadingFallback name="Smart Chart" />,
    ssr: false
  }
);

export const LazyWellBrowser = dynamic(
  () => import('./WellBrowser').then(mod => ({ default: mod.WellBrowser })),
  {
    loading: () => <ComponentLoadingFallback name="Well Browser" />,
    ssr: false
  }
);

export const LazyDatabaseUpload = dynamic(
  () => import('./DatabaseUpload').then(mod => ({ default: mod.DatabaseUpload })),
  {
    loading: () => <ComponentLoadingFallback name="Database Upload" />,
    ssr: false
  }
);

export const LazyExportDialog = dynamic(
  () => import('./ExportDialog').then(mod => ({ default: mod.ExportDialog })),
  {
    loading: () => <ComponentLoadingFallback name="Export Tools" />,
    ssr: false
  }
);

export const LazyPlotCustomizationDialog = dynamic(
  () => import('./PlotCustomizationDialog').then(mod => ({ default: mod.PlotCustomizationDialog })),
  {
    loading: () => <ComponentLoadingFallback name="Plot Customization" />,
    ssr: false
  }
);

// Preload functions for eager loading when needed
export const preloadChartComponents = () => {
  import('./WaterLevelChart');
  import('./ChartJSTimeSeriesChart');
  import('./SmartWaterLevelChart');
};

export const preloadMapComponents = () => {
  import('./WellsMap');
};

export const preloadDatabaseComponents = () => {
  import('./DatabaseSelector');
  import('./DatabaseUpload');
};