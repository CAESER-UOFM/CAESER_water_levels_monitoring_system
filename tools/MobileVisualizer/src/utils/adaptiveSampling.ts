/**
 * Adaptive Sampling Utility
 * 
 * Calculates optimal sampling rates for time ranges to achieve 4000-4500 data points
 * Uses natural time boundaries instead of arbitrary downsampling
 */

export interface SamplingRate {
  name: string;
  minutes: number;
  description: string;
}

export const SAMPLING_RATES: SamplingRate[] = [
  { name: '15min', minutes: 15, description: '15 minutes (raw data)' },
  { name: '30min', minutes: 30, description: '30 minutes' },
  { name: '1hour', minutes: 60, description: '1 hour' },
  { name: '3hour', minutes: 180, description: '3 hours' },
  { name: '6hour', minutes: 360, description: '6 hours' },
  { name: '12hour', minutes: 720, description: '12 hours' },
  { name: '1day', minutes: 1440, description: '1 day' },
  { name: '3day', minutes: 4320, description: '3 days' },
  { name: '1week', minutes: 10080, description: '1 week' },
  { name: '1month', minutes: 43200, description: '1 month (~30 days)' }
];

export interface AdaptiveSamplingResult {
  samplingRate: SamplingRate;
  estimatedPoints: number;
  timeSpanDays: number;
  recommendation: string;
}

/**
 * Calculate optimal sampling rate for a given time range
 * Target: 4000-4500 points for optimal performance and detail
 */
export function calculateOptimalSampling(
  startDate: Date, 
  endDate: Date,
  targetMinPoints: number = 4000,
  targetMaxPoints: number = 4500
): AdaptiveSamplingResult {
  const timeSpanMs = endDate.getTime() - startDate.getTime();
  const timeSpanDays = timeSpanMs / (1000 * 60 * 60 * 24);
  const timeSpanMinutes = timeSpanMs / (1000 * 60);
  
  // Find the best sampling rate
  let bestRate = SAMPLING_RATES[0]; // Default to 15min
  let bestPoints = Math.floor(timeSpanMinutes / bestRate.minutes);
  
  for (const rate of SAMPLING_RATES) {
    const estimatedPoints = Math.floor(timeSpanMinutes / rate.minutes);
    
    // If this rate gives us points in our target range, use it
    if (estimatedPoints >= targetMinPoints && estimatedPoints <= targetMaxPoints) {
      bestRate = rate;
      bestPoints = estimatedPoints;
      break;
    }
    
    // If we're below target, this is our best option (finest resolution possible)
    if (estimatedPoints < targetMinPoints) {
      bestRate = rate;
      bestPoints = estimatedPoints;
      break;
    }
    
    // Keep this as a candidate (it's above target but might be our best option)
    bestRate = rate;
    bestPoints = estimatedPoints;
  }
  
  // Generate recommendation message
  let recommendation: string;
  if (bestPoints >= targetMinPoints && bestPoints <= targetMaxPoints) {
    recommendation = `Perfect: ${bestPoints} points with ${bestRate.description}`;
  } else if (bestPoints < targetMinPoints) {
    recommendation = `Maximum detail: ${bestPoints} points (limited by ${bestRate.description} resolution)`;
  } else {
    recommendation = `Efficient view: ${bestPoints} points with ${bestRate.description}`;
  }
  
  return {
    samplingRate: bestRate,
    estimatedPoints: bestPoints,
    timeSpanDays,
    recommendation
  };
}

/**
 * Get sampling rate for overview loading (full dataset)
 * Uses longer time periods for very large datasets
 */
export function calculateOverviewSampling(
  totalDataSpanDays: number,
  targetPoints: number = 4500
): AdaptiveSamplingResult {
  // Create a synthetic time range for calculation
  const endDate = new Date();
  const startDate = new Date(endDate.getTime() - (totalDataSpanDays * 24 * 60 * 60 * 1000));
  
  return calculateOptimalSampling(startDate, endDate, 4000, targetPoints);
}

/**
 * Format sampling info for user display
 */
export function formatSamplingInfo(result: AdaptiveSamplingResult): string {
  const { timeSpanDays, samplingRate, estimatedPoints } = result;
  
  if (timeSpanDays < 1) {
    return `${(timeSpanDays * 24).toFixed(1)} hours at ${samplingRate.description} (${estimatedPoints.toLocaleString()} points)`;
  } else if (timeSpanDays < 30) {
    return `${timeSpanDays.toFixed(1)} days at ${samplingRate.description} (${estimatedPoints.toLocaleString()} points)`;
  } else if (timeSpanDays < 365) {
    return `${(timeSpanDays / 30).toFixed(1)} months at ${samplingRate.description} (${estimatedPoints.toLocaleString()} points)`;
  } else {
    return `${(timeSpanDays / 365).toFixed(1)} years at ${samplingRate.description} (${estimatedPoints.toLocaleString()} points)`;
  }
}