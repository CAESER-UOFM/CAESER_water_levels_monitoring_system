import type { PlotCustomization } from '@/components/PlotCustomizationDialog';
import type { Well } from '@/lib/api/api';

// Utility function to format numbers with significant figures
function formatWithSignificantFigures(value: number, sigFigs: number): string {
  if (value === 0) return '0';
  
  const magnitude = Math.floor(Math.log10(Math.abs(value)));
  const precision = sigFigs - magnitude - 1;
  
  if (precision >= 0) {
    return value.toFixed(precision);
  } else {
    const factor = Math.pow(10, -precision);
    return (Math.round(value / factor) * factor).toString();
  }
}

// Smart margin calculation for export (full resolution)
function calculateSmartMargins(customization: PlotCustomization): {
  top: number;
  right: number;
  bottom: number;
  left: number;
} {
  const MINIMUM_BORDER_MARGIN = 30; // Minimum space from image border
  
  // Base margins for plot area
  let top = customization.title.show ? Math.max(60, customization.title.fontSize + 40) : 30;
  let right = 60;
  let bottom = 80;
  let left = 100;
  
  // Adjust based on axis label distances
  if (customization.xAxis.labelPosition === 'bottom') {
    bottom = Math.max(bottom, customization.xAxis.labelDistance + customization.xAxis.fontSize + MINIMUM_BORDER_MARGIN);
  } else {
    top = Math.max(top, customization.xAxis.labelDistance + customization.xAxis.fontSize + MINIMUM_BORDER_MARGIN);
  }
  
  if (customization.yAxis.labelPosition === 'left') {
    left = Math.max(left, customization.yAxis.labelDistance + customization.yAxis.fontSize + MINIMUM_BORDER_MARGIN);
  } else {
    right = Math.max(right, customization.yAxis.labelDistance + customization.yAxis.fontSize + MINIMUM_BORDER_MARGIN);
  }
  
  // Adjust for right axis if shown
  if (customization.showTemperatureData && customization.rightAxis.show) {
    right = Math.max(right, customization.rightAxis.labelDistance + customization.rightAxis.fontSize + MINIMUM_BORDER_MARGIN);
  }
  
  return { top, right, bottom, left };
}

interface WaterLevelData {
  timestamp: string;
  water_level: number;
  temperature?: number;
  reading_type: 'transducer' | 'manual';
}

export interface CustomPlotExportProgress {
  stage: string;
  percentage: number;
  message: string;
}

export async function exportCustomPlot(
  databaseId: string,
  wellNumber: string,
  well: Well,
  customization: PlotCustomization,
  onProgress: (progress: CustomPlotExportProgress) => void,
  signal?: AbortSignal
): Promise<void> {
  try {
    onProgress({ stage: 'loading', percentage: 10, message: 'Loading water level data...' });

    // Fetch the data based on customization settings
    const dataUrl = `/.netlify/functions/data/${databaseId}/${wellNumber}`;
    const params = new URLSearchParams();
    
    if (customization.dateRange) {
      params.append('start', customization.dateRange.start);
      params.append('end', customization.dateRange.end);
    }
    
    const response = await fetch(`${dataUrl}?${params}`);
    if (!response.ok) throw new Error('Failed to fetch data');
    
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'Failed to load data');

    onProgress({ stage: 'processing', percentage: 30, message: 'Processing data...' });

    // Filter data based on customization
    let data: WaterLevelData[] = result.data;
    
    if (!customization.showTransducerData) {
      data = data.filter(d => d.reading_type !== 'transducer');
    }
    
    if (!customization.showManualData) {
      data = data.filter(d => d.reading_type !== 'manual');
    }

    if (signal?.aborted) throw new Error('Export cancelled');

    onProgress({ stage: 'generating', percentage: 50, message: 'Generating custom plot...' });

    // Create a canvas for the plot
    const canvas = document.createElement('canvas');
    canvas.width = customization.width;
    canvas.height = customization.height;
    const ctx = canvas.getContext('2d');
    
    if (!ctx) throw new Error('Could not create canvas context');

    // Set DPI scaling
    const dpiScale = customization.dpi / 96; // 96 DPI is the default
    canvas.style.width = `${customization.width}px`;
    canvas.style.height = `${customization.height}px`;
    canvas.width = customization.width * dpiScale;
    canvas.height = customization.height * dpiScale;
    ctx.scale(dpiScale, dpiScale);

    // Clear canvas with background color
    ctx.fillStyle = customization.backgroundColor;
    ctx.fillRect(0, 0, customization.width, customization.height);

    // Draw border if specified
    if (customization.borderWidth > 0) {
      ctx.strokeStyle = customization.borderColor;
      ctx.lineWidth = customization.borderWidth;
      ctx.strokeRect(0, 0, customization.width, customization.height);
    }

    onProgress({ stage: 'rendering', percentage: 70, message: 'Rendering plot elements...' });

    // Calculate plot area using smart margin calculation
    const margin = calculateSmartMargins(customization);

    const plotWidth = customization.width - margin.left - margin.right;
    const plotHeight = customization.height - margin.top - margin.bottom;
    const plotX = margin.left;
    const plotY = margin.top;

    // Draw plot area background
    ctx.fillStyle = customization.plotAreaColor;
    ctx.fillRect(plotX, plotY, plotWidth, plotHeight);

    // Draw title if enabled
    if (customization.title.show && customization.title.text) {
      ctx.fillStyle = customization.title.color;
      ctx.font = `${customization.title.fontSize}px Arial, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(customization.title.text, customization.width / 2, 40);
    }

    if (data.length > 0) {
      // Calculate data bounds
      const waterLevels = data.map(d => d.water_level);
      const timestamps = data.map(d => new Date(d.timestamp).getTime());
      
      const minLevel = Math.min(...waterLevels);
      const maxLevel = Math.max(...waterLevels);
      const minTime = Math.min(...timestamps);
      const maxTime = Math.max(...timestamps);

      // Add some padding to the data range
      const levelRange = maxLevel - minLevel;
      const levelPadding = levelRange * 0.1;
      const yMin = minLevel - levelPadding;
      const yMax = maxLevel + levelPadding;

      // Helper functions for coordinate conversion
      const xScale = (timestamp: number) => plotX + ((timestamp - minTime) / (maxTime - minTime)) * plotWidth;
      const yScale = (level: number) => plotY + plotHeight - ((level - yMin) / (yMax - yMin)) * plotHeight;

      // Draw grid if enabled
      if (customization.xAxis.showGrid) {
        ctx.strokeStyle = customization.xAxis.gridColor;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 10; i++) {
          const x = plotX + (plotWidth / 10) * i;
          ctx.beginPath();
          ctx.moveTo(x, plotY);
          ctx.lineTo(x, plotY + plotHeight);
          ctx.stroke();
        }
      }

      if (customization.yAxis.showGrid) {
        ctx.strokeStyle = customization.yAxis.gridColor;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 10; i++) {
          const y = plotY + (plotHeight / 10) * i;
          ctx.beginPath();
          ctx.moveTo(plotX, y);
          ctx.lineTo(plotX + plotWidth, y);
          ctx.stroke();
        }
      }

      // Draw data series
      const transducerData = data.filter(d => d.reading_type === 'transducer');
      const manualData = data.filter(d => d.reading_type === 'manual');

      // Draw transducer data as line
      if (customization.showTransducerData && transducerData.length > 0) {
        ctx.strokeStyle = customization.transducerData.color;
        ctx.lineWidth = customization.transducerData.lineWidth;
        ctx.beginPath();
        
        transducerData.forEach((point, index) => {
          const x = xScale(new Date(point.timestamp).getTime());
          const y = yScale(point.water_level);
          
          if (index === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });
        
        ctx.stroke();

        // Draw points if enabled
        if (customization.transducerData.showPoints) {
          ctx.fillStyle = customization.transducerData.color;
          transducerData.forEach(point => {
            const x = xScale(new Date(point.timestamp).getTime());
            const y = yScale(point.water_level);
            ctx.beginPath();
            ctx.arc(x, y, customization.transducerData.pointSize, 0, 2 * Math.PI);
            ctx.fill();
          });
        }
      }

      // Draw manual data as points
      if (customization.showManualData && manualData.length > 0) {
        ctx.fillStyle = customization.manualData.color;
        manualData.forEach(point => {
          const x = xScale(new Date(point.timestamp).getTime());
          const y = yScale(point.water_level);
          
          ctx.beginPath();
          if (customization.manualData.pointStyle === 'circle') {
            ctx.arc(x, y, customization.manualData.pointSize, 0, 2 * Math.PI);
          } else if (customization.manualData.pointStyle === 'square') {
            const size = customization.manualData.pointSize;
            ctx.rect(x - size, y - size, size * 2, size * 2);
          } else if (customization.manualData.pointStyle === 'triangle') {
            const size = customization.manualData.pointSize;
            ctx.moveTo(x, y - size);
            ctx.lineTo(x - size, y + size);
            ctx.lineTo(x + size, y + size);
            ctx.closePath();
          }
          ctx.fill();
        });
      }

      // Draw axes
      ctx.strokeStyle = customization.borderColor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(plotX, plotY);
      ctx.lineTo(plotX, plotY + plotHeight);
      ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
      ctx.stroke();

      // Draw axis labels
      ctx.fillStyle = customization.xAxis.color;
      ctx.font = `${customization.xAxis.fontSize}px Arial, sans-serif`;
      ctx.textAlign = 'center';
      const xLabelY = customization.xAxis.labelPosition === 'top' 
        ? plotY - customization.xAxis.labelDistance 
        : plotY + plotHeight + customization.xAxis.labelDistance;
      ctx.fillText(customization.xAxis.label, plotX + plotWidth / 2, xLabelY);

      ctx.fillStyle = customization.yAxis.color;
      ctx.font = `${customization.yAxis.fontSize}px Arial, sans-serif`;
      ctx.save();
      const yLabelX = customization.yAxis.labelPosition === 'right' 
        ? plotX + plotWidth + customization.yAxis.labelDistance 
        : plotX - customization.yAxis.labelDistance;
      ctx.translate(yLabelX, plotY + plotHeight / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.fillText(customization.yAxis.label, 0, 0);
      ctx.restore();

      // Draw axis tick labels
      ctx.fillStyle = customization.xAxis.color;
      ctx.font = `${customization.xAxis.fontSize - 2}px Arial, sans-serif`;
      ctx.textAlign = 'center';
      
      // X-axis ticks (dates)
      for (let i = 0; i <= 5; i++) {
        const timestamp = minTime + ((maxTime - minTime) / 5) * i;
        const x = xScale(timestamp);
        const date = new Date(timestamp);
        const label = date.toLocaleDateString();
        ctx.fillText(label, x, plotY + plotHeight + 20);
      }

      // Y-axis ticks (water levels)
      ctx.textAlign = 'right';
      for (let i = 0; i <= customization.yAxis.tickCount; i++) {
        const level = yMin + ((yMax - yMin) / customization.yAxis.tickCount) * i;
        const y = yScale(level);
        const label = formatWithSignificantFigures(level, customization.yAxis.significantFigures);
        ctx.fillText(label, plotX - 10, y + 4);
      }
      
      // Draw right axis for temperature if enabled
      if (customization.showTemperatureData && customization.rightAxis.show) {
        const temperatureData = data.filter(d => d.temperature !== undefined && d.temperature !== null);
        
        if (temperatureData.length > 0) {
          // Calculate temperature bounds
          const tempValues = temperatureData.map(d => d.temperature!);
          const minTemp = Math.min(...tempValues);
          const maxTemp = Math.max(...tempValues);
          const tempRange = maxTemp - minTemp;
          const tempPadding = tempRange * 0.1;
          const tempMin = minTemp - tempPadding;
          const tempMax = maxTemp + tempPadding;
          
          // Draw right axis line
          ctx.strokeStyle = customization.rightAxis.color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(plotX + plotWidth, plotY);
          ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
          ctx.stroke();
          
          // Draw right axis label
          ctx.fillStyle = customization.rightAxis.color;
          ctx.font = `${customization.rightAxis.fontSize}px Arial, sans-serif`;
          ctx.save();
          const rightLabelX = plotX + plotWidth + customization.rightAxis.labelDistance;
          ctx.translate(rightLabelX, plotY + plotHeight / 2);
          ctx.rotate(-Math.PI / 2);
          ctx.textAlign = 'center';
          ctx.fillText(customization.rightAxis.label, 0, 0);
          ctx.restore();
          
          // Draw right axis ticks
          ctx.fillStyle = customization.rightAxis.color;
          ctx.font = `${customization.rightAxis.tickFontSize}px Arial, sans-serif`;
          ctx.textAlign = 'left';
          
          for (let i = 0; i <= customization.rightAxis.tickCount; i++) {
            const tempValue = tempMin + ((tempMax - tempMin) / customization.rightAxis.tickCount) * i;
            const y = plotY + plotHeight - ((tempValue - tempMin) / (tempMax - tempMin)) * plotHeight;
            const tempLabel = formatWithSignificantFigures(tempValue, customization.rightAxis.significantFigures);
            ctx.fillText(tempLabel, plotX + plotWidth + 10, y + 4);
          }
        }
      }
    }

    // Draw legend if enabled
    if (customization.legend.show) {
      const legendItems = [];
      if (customization.showTransducerData) {
        legendItems.push({ label: 'Transducer Data', color: customization.transducerData.color });
      }
      if (customization.showManualData) {
        legendItems.push({ label: 'Manual Readings', color: customization.manualData.color });
      }

      if (legendItems.length > 0) {
        // Calculate legend position based on new positioning system
        let legendX = 20; // default
        let legendY = 20;
        const legendWidth = 200;
        const legendHeight = legendItems.length * 25 + 10;
        
        switch (customization.legend.position) {
          case 'top-left':
            legendX = 20;
            legendY = 20;
            break;
          case 'top-center':
            legendX = (customization.width - legendWidth) / 2;
            legendY = 20;
            break;
          case 'top-right':
            legendX = customization.width - legendWidth - 20;
            legendY = 20;
            break;
          case 'middle-left':
            legendX = 20;
            legendY = (customization.height - legendHeight) / 2;
            break;
          case 'middle-right':
            legendX = customization.width - legendWidth - 20;
            legendY = (customization.height - legendHeight) / 2;
            break;
          case 'bottom-left':
            legendX = 20;
            legendY = customization.height - legendHeight - 60;
            break;
          case 'bottom-center':
            legendX = (customization.width - legendWidth) / 2;
            legendY = customization.height - legendHeight - 60;
            break;
          case 'bottom-right':
            legendX = customization.width - legendWidth - 20;
            legendY = customization.height - legendHeight - 60;
            break;
          case 'below-x-axis':
            legendX = (customization.width - legendWidth) / 2;
            legendY = customization.height - 40;
            break;
        }

        // Draw legend background
        ctx.fillStyle = customization.legend.backgroundColor;
        ctx.fillRect(legendX, legendY, legendWidth, legendHeight);
        ctx.strokeStyle = customization.legend.borderColor;
        ctx.strokeRect(legendX, legendY, legendWidth, legendHeight);

        // Draw legend items
        ctx.fillStyle = customization.legend.textColor;
        ctx.font = `${customization.legend.fontSize}px Arial, sans-serif`;
        ctx.textAlign = 'left';
        
        legendItems.forEach((item, index) => {
          const itemY = legendY + 20 + index * 25;
          
          // Draw color indicator
          ctx.fillStyle = item.color;
          ctx.fillRect(legendX + 10, itemY - 8, 20, 3);
          
          // Draw label
          ctx.fillStyle = customization.legend.textColor;
          ctx.fillText(item.label, legendX + 40, itemY);
        });
      }
    }

    onProgress({ stage: 'saving', percentage: 90, message: 'Saving image...' });

    // Convert canvas to blob and download
    canvas.toBlob((blob) => {
      if (!blob) throw new Error('Failed to generate image');
      
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `well_${wellNumber}_custom_plot_${customization.width}x${customization.height}_${customization.dpi}dpi.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      onProgress({ stage: 'complete', percentage: 100, message: 'Custom plot exported successfully!' });
    }, 'image/png', 1.0);

  } catch (error) {
    throw new Error(`Custom plot export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}