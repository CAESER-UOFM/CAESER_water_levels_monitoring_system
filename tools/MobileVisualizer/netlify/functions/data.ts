import { Handler, HandlerEvent } from '@netlify/functions';
import { GoogleDriveService } from '../../src/lib/api/services/googleDrive';
import { SQLiteService } from '../../src/lib/api/services/sqljs';
import { cacheService, CacheService } from '../../src/lib/api/services/cache';
import { ApiResponse, WaterLevelReading, RechargeResult, DataQueryParams } from '../../src/lib/api/api';

const googleDriveService = new GoogleDriveService();
const sqliteService = new SQLiteService();

export const handler: Handler = async (event: HandlerEvent) => {
  // Set CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json',
  };

  // Handle OPTIONS preflight request
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: '',
    };
  }

  // Parse the path to determine action
  const path = event.path.replace('/.netlify/functions/data', '');
  const pathParts = path.split('/').filter(p => p);

  try {
    // GET /data/:databaseId/water/:wellNumber - Get water level data
    if (event.httpMethod === 'GET' && pathParts.length === 3 && pathParts[1] === 'water') {
      const [databaseId, , wellNumber] = pathParts;
      return await getWaterLevelData(databaseId, wellNumber, event.queryStringParameters || {});
    }

    // GET /data/:databaseId/recharge/:wellNumber - Get recharge results
    if (event.httpMethod === 'GET' && pathParts.length === 3 && pathParts[1] === 'recharge') {
      const [databaseId, , wellNumber] = pathParts;
      return await getRechargeResults(databaseId, wellNumber);
    }

    // GET /data/:databaseId/summary/:wellNumber - Get data summary
    if (event.httpMethod === 'GET' && pathParts.length === 3 && pathParts[1] === 'summary') {
      const [databaseId, , wellNumber] = pathParts;
      return await getDataSummary(databaseId, wellNumber);
    }

    return {
      statusCode: 404,
      headers,
      body: JSON.stringify({
        success: false,
        error: 'Not found'
      } as ApiResponse),
    };

  } catch (error) {
    console.error('Data function error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : 'Internal server error'
      } as ApiResponse),
    };
  }
};

async function getWaterLevelData(databaseId: string, wellNumber: string, queryParams: Record<string, string | undefined>) {
  // Validate and sanitize parameters
  const params: DataQueryParams = {
    wellNumber
  };

  // StartDate parameter
  if (queryParams.startDate && typeof queryParams.startDate === 'string') {
    const startDate = new Date(queryParams.startDate);
    if (!isNaN(startDate.getTime())) {
      params.startDate = queryParams.startDate;
    }
  }

  // EndDate parameter
  if (queryParams.endDate && typeof queryParams.endDate === 'string') {
    const endDate = new Date(queryParams.endDate);
    if (!isNaN(endDate.getTime())) {
      params.endDate = queryParams.endDate;
    }
  }

  // DataType parameter
  if (queryParams.dataType && typeof queryParams.dataType === 'string') {
    const allowedTypes = ['all', 'transducer', 'telemetry', 'manual'];
    if (allowedTypes.includes(queryParams.dataType)) {
      params.dataType = queryParams.dataType as any;
    }
  }

  // Downsample parameter
  if (queryParams.downsample !== undefined) {
    params.downsample = queryParams.downsample === 'true';
  }

  // MaxPoints parameter
  if (queryParams.maxPoints) {
    const maxPoints = parseInt(queryParams.maxPoints);
    if (!isNaN(maxPoints) && maxPoints >= 1) {
      params.maxPoints = Math.min(maxPoints, 10000);
    }
  }

  // Generate cache key based on parameters
  const cacheKey = CacheService.generateParamsKey(params);
  
  // Check cache first
  const cachedData = cacheService.getWaterLevelData(databaseId, cacheKey);
  if (cachedData) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedData
      } as ApiResponse<WaterLevelReading[]>),
    };
  }

  // Get database list to find the database
  const databases = await googleDriveService.listDatabases();
  const database = databases.find(db => db.id === databaseId);
  
  if (!database) {
    return {
      statusCode: 404,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: false,
        error: 'Database not found'
      } as ApiResponse),
    };
  }

  // Download and open database
  const filePath = await googleDriveService.downloadDatabase(databaseId, database.name);
  await sqliteService.openDatabase(filePath);
  
  // Get water level data
  const waterLevelData = await sqliteService.getWaterLevelData(params);

  // Cache the result (shorter TTL for data queries)
  cacheService.setWaterLevelData(databaseId, cacheKey, waterLevelData);

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: waterLevelData,
      metadata: {
        wellNumber: params.wellNumber,
        dataType: params.dataType || 'all',
        totalPoints: waterLevelData.length,
        downsample: params.downsample || false,
        dateRange: {
          start: params.startDate,
          end: params.endDate
        }
      }
    } as ApiResponse<WaterLevelReading[]>),
  };
}

async function getRechargeResults(databaseId: string, wellNumber: string) {
  // Check cache first
  const cachedResults = cacheService.getRechargeResults(databaseId, wellNumber);
  if (cachedResults) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedResults
      } as ApiResponse<RechargeResult[]>),
    };
  }

  // Get database list to find the database
  const databases = await googleDriveService.listDatabases();
  const database = databases.find(db => db.id === databaseId);
  
  if (!database) {
    return {
      statusCode: 404,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: false,
        error: 'Database not found'
      } as ApiResponse),
    };
  }

  // Download and open database
  const filePath = await googleDriveService.downloadDatabase(databaseId, database.name);
  await sqliteService.openDatabase(filePath);
  
  // Get recharge results
  const rechargeResults = await sqliteService.getRechargeResults(wellNumber);

  // Cache the result
  cacheService.setRechargeResults(databaseId, wellNumber, rechargeResults);

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: rechargeResults,
      metadata: {
        wellNumber,
        totalCalculations: rechargeResults.length,
        methods: [...new Set(rechargeResults.map(r => r.method))]
      }
    } as ApiResponse<RechargeResult[]>),
  };
}

async function getDataSummary(databaseId: string, wellNumber: string) {
  // Check cache first
  const cacheKey = `summary:${wellNumber}`;
  const cachedSummary = cacheService.get(cacheKey);
  if (cachedSummary) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedSummary
      } as ApiResponse),
    };
  }

  // Get database list to find the database
  const databases = await googleDriveService.listDatabases();
  const database = databases.find(db => db.id === databaseId);
  
  if (!database) {
    return {
      statusCode: 404,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: false,
        error: 'Database not found'
      } as ApiResponse),
    };
  }

  // Download and open database
  const filePath = await googleDriveService.downloadDatabase(databaseId, database.name);
  await sqliteService.openDatabase(filePath);
  
  // Get well info
  const well = await sqliteService.getWell(wellNumber);
  if (!well) {
    sqliteService.closeDatabase();
    return {
      statusCode: 404,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: false,
        error: 'Well not found'
      } as ApiResponse),
    };
  }

  // Get data counts by type
  const allData = await sqliteService.getWaterLevelData({ wellNumber });
  const rechargeResults = await sqliteService.getRechargeResults(wellNumber);

  const dataTypeCounts = allData.reduce((counts, reading) => {
    counts[reading.data_source] = (counts[reading.data_source] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const summary = {
    well,
    totalReadings: allData.length,
    dataTypeCounts,
    dateRange: allData.length > 0 ? {
      start: allData[0].timestamp_utc,
      end: allData[allData.length - 1].timestamp_utc
    } : null,
    rechargeCalculations: rechargeResults.length,
    rechargeMethodCounts: rechargeResults.reduce((counts, result) => {
      counts[result.method] = (counts[result.method] || 0) + 1;
      return counts;
    }, {} as Record<string, number>)
  };

  // Cache the result
  cacheService.set(cacheKey, summary, 30 * 60); // 30 minutes TTL

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: summary
    } as ApiResponse),
  };
}