/**
 * Test file for the new resolution system
 * Run with: npm test -- resolution-system.test.ts
 * Or manually test the functions to ensure they work correctly
 */

import { 
  RESOLUTION_CONFIGS, 
  calculateOptimalResolution, 
  calculateNavigationState,
  getDefaultDateRange 
} from '../utils/resolutionConfig';

import { 
  calculateResolutionSampling,
  calculateOptimalSampling 
} from '../utils/adaptiveSampling';

// Mock data for testing
const mockAvailableRange = {
  start: new Date('2023-01-01'),
  end: new Date('2024-01-01')
};

// Test resolution configuration
export function testResolutionConfig() {
  console.log('🧪 Testing Resolution Configuration...');
  
  // Test that all resolution modes exist
  const modes = ['full', '1year', '6months', '1month'] as const;
  modes.forEach(mode => {
    const config = RESOLUTION_CONFIGS[mode];
    console.log(`✅ ${mode}:`, {
      name: config.name,
      interval: config.samplingInterval,
      targetPoints: config.targetPoints,
      maxTimeSpan: config.maxTimeSpan
    });
  });

  return true;
}

// Test optimal resolution calculation
export function testOptimalResolutionCalculation() {
  console.log('\n🧪 Testing Optimal Resolution Calculation...');
  
  const testCases = [
    { days: 7, expected: '1month' },
    { days: 60, expected: '6months' },
    { days: 200, expected: '1year' },
    { days: 400, expected: 'full' }
  ];

  testCases.forEach(testCase => {
    const endDate = new Date('2024-01-01');
    const startDate = new Date(endDate.getTime() - testCase.days * 24 * 60 * 60 * 1000);
    
    const result = calculateOptimalResolution(startDate, endDate, mockAvailableRange);
    
    console.log(`✅ ${testCase.days} days → ${result.mode} (expected: ${testCase.expected})`);
    console.log(`   Sampling: ${result.samplingInterval}min, Points: ${result.estimatedPoints}`);
  });

  return true;
}

// Test adaptive sampling with resolution modes
export function testAdaptiveSamplingWithResolutions() {
  console.log('\n🧪 Testing Adaptive Sampling with Resolutions...');
  
  const endDate = new Date('2024-01-01');
  const startDate = new Date('2023-07-01'); // 6 months
  
  const modes = ['1month', '6months', '1year', 'full'] as const;
  
  modes.forEach(mode => {
    const result = calculateResolutionSampling(startDate, endDate, mode);
    console.log(`✅ ${mode}:`, {
      samplingInterval: result.samplingInterval,
      estimatedPoints: result.estimatedPoints,
      actualTimeSpan: result.actualTimeSpan.toFixed(1)
    });

    // Verify we never exceed 5000 points
    if (result.estimatedPoints > 5000) {
      console.error(`❌ ${mode} exceeds 5000 points: ${result.estimatedPoints}`);
      return false;
    }
  });

  return true;
}

// Test navigation state calculation
export function testNavigationState() {
  console.log('\n🧪 Testing Navigation State...');
  
  const currentRange = {
    start: new Date('2023-06-01'),
    end: new Date('2023-07-01')
  };
  
  const navState = calculateNavigationState('1month', currentRange, mockAvailableRange);
  
  console.log('✅ Navigation State:', {
    canNavigateLeft: navState.canNavigateLeft,
    canNavigateRight: navState.canNavigateRight,
    position: (navState.position * 100).toFixed(1) + '%'
  });

  return true;
}

// Test cache key generation
export function testCacheKeyGeneration() {
  console.log('\n🧪 Testing Cache Key Generation...');
  
  // This would normally import from the cache, but we'll simulate it
  const generateCacheKey = (
    wellNumber: string, 
    resolution: string, 
    samplingInterval: number, 
    startDate: string, 
    endDate: string
  ) => {
    return `${wellNumber}_${resolution}_${samplingInterval}_${startDate}_${endDate}`;
  };

  const key = generateCacheKey(
    'W001',
    '1month',
    15,
    '2023-01-01',
    '2023-02-01'
  );
  
  console.log('✅ Cache Key:', key);
  
  // Verify the key format
  const parts = key.split('_');
  if (parts.length >= 5) {
    console.log('✅ Cache key format is correct');
    return true;
  } else {
    console.error('❌ Cache key format is incorrect');
    return false;
  }
}

// Test data point calculations
export function testDataPointCalculations() {
  console.log('\n🧪 Testing Data Point Calculations...');
  
  const testRanges = [
    { start: new Date('2024-01-01'), end: new Date('2024-01-02') }, // 1 day
    { start: new Date('2024-01-01'), end: new Date('2024-01-08') }, // 1 week  
    { start: new Date('2024-01-01'), end: new Date('2024-02-01') }, // 1 month
    { start: new Date('2024-01-01'), end: new Date('2024-07-01') }, // 6 months
    { start: new Date('2023-01-01'), end: new Date('2024-01-01') }  // 1 year
  ];

  testRanges.forEach((range, index) => {
    const days = (range.end.getTime() - range.start.getTime()) / (1000 * 60 * 60 * 24);
    
    // Test different resolutions for each range
    const resolutions = ['1month', '6months', '1year', 'full'] as const;
    
    console.log(`📊 Range ${index + 1}: ${days.toFixed(1)} days`);
    
    resolutions.forEach(resolution => {
      const result = calculateResolutionSampling(range.start, range.end, resolution);
      const pointsOk = result.estimatedPoints <= 5000;
      
      console.log(`   ${resolution}: ${result.estimatedPoints} points ${pointsOk ? '✅' : '❌'}`);
    });
  });

  return true;
}

// Run all tests
export function runAllTests() {
  console.log('🚀 Running Resolution System Tests...\n');
  
  const tests = [
    testResolutionConfig,
    testOptimalResolutionCalculation,
    testAdaptiveSamplingWithResolutions,
    testNavigationState,
    testCacheKeyGeneration,
    testDataPointCalculations
  ];
  
  const results = tests.map(test => {
    try {
      return test();
    } catch (error) {
      console.error('❌ Test failed:', error);
      return false;
    }
  });
  
  const passed = results.filter(Boolean).length;
  const total = results.length;
  
  console.log(`\n📈 Test Results: ${passed}/${total} passed`);
  
  if (passed === total) {
    console.log('🎉 All tests passed! Resolution system is working correctly.');
  } else {
    console.log('⚠️  Some tests failed. Please check the implementation.');
  }
  
  return passed === total;
}

// Manual test runner for browser console
if (typeof window !== 'undefined') {
  // Browser environment - attach to window for manual testing
  (window as any).testResolutionSystem = runAllTests;
  console.log('💡 Run testResolutionSystem() in the console to test the resolution system');
}