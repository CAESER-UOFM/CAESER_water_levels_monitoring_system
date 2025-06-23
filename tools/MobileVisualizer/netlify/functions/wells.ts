import { Handler, HandlerEvent } from '@netlify/functions';
import { GoogleDriveService } from '../../src/lib/api/services/googleDrive';
import { SQLiteService } from '../../src/lib/api/services/sqljs';
import { cacheService, CacheService } from '../../src/lib/api/services/cache';
import { ApiResponse, PaginatedResponse, Well, WellsQueryParams } from '../../src/lib/api/api';

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
  const path = event.path.replace('/.netlify/functions/wells', '');
  const pathParts = path.split('/').filter(p => p);

  try {
    // GET /wells/:databaseId - Get wells for database
    if (event.httpMethod === 'GET' && pathParts.length === 1) {
      const databaseId = pathParts[0];
      return await getWells(databaseId, event.queryStringParameters || {});
    }

    // GET /wells/:databaseId/:wellNumber - Get specific well
    if (event.httpMethod === 'GET' && pathParts.length === 2) {
      const [databaseId, wellNumber] = pathParts;
      return await getWell(databaseId, wellNumber);
    }

    // GET /wells/:databaseId/fields - Get well fields
    if (event.httpMethod === 'GET' && pathParts.length === 2 && pathParts[1] === 'fields') {
      const databaseId = pathParts[0];
      return await getWellFields(databaseId);
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
    console.error('Wells function error:', error);
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

async function getWells(databaseId: string, queryParams: Record<string, string | undefined>) {
  // Validate and sanitize parameters
  const params: WellsQueryParams = {};

  // Search parameter
  if (queryParams.search && typeof queryParams.search === 'string') {
    params.search = queryParams.search.trim().substring(0, 100);
  }

  // Field parameter
  if (queryParams.field && typeof queryParams.field === 'string') {
    params.field = queryParams.field.trim().substring(0, 100);
  }

  // HasData parameter
  if (queryParams.hasData !== undefined) {
    params.hasData = queryParams.hasData === 'true';
  }

  // Page parameter
  if (queryParams.page && typeof queryParams.page === 'string') {
    const page = parseInt(queryParams.page);
    if (!isNaN(page) && page >= 1) {
      params.page = Math.min(page, 1000);
    }
  }

  // Limit parameter
  if (queryParams.limit && typeof queryParams.limit === 'string') {
    const limit = parseInt(queryParams.limit);
    if (!isNaN(limit) && limit >= 1) {
      params.limit = Math.min(limit, 100);
    }
  }

  // SortBy parameter
  if (queryParams.sortBy && typeof queryParams.sortBy === 'string') {
    const allowedSortFields = ['well_number', 'cae_number', 'last_reading_date'];
    if (allowedSortFields.includes(queryParams.sortBy)) {
      params.sortBy = queryParams.sortBy as any;
    }
  }

  // SortOrder parameter
  if (queryParams.sortOrder && typeof queryParams.sortOrder === 'string') {
    if (['asc', 'desc'].includes(queryParams.sortOrder.toLowerCase())) {
      params.sortOrder = queryParams.sortOrder.toLowerCase() as 'asc' | 'desc';
    }
  }

  // Generate cache key based on parameters
  const cacheKey = CacheService.generateParamsKey(params);
  
  // Check cache first
  const cachedWells = cacheService.getWells(databaseId, cacheKey);
  if (cachedWells) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(cachedWells),
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
  
  // Get wells with pagination
  const wells = await sqliteService.getWells(params);

  // Cache the result
  cacheService.setWells(databaseId, cacheKey, wells);

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(wells),
  };
}

async function getWell(databaseId: string, wellNumber: string) {
  // Check cache first
  const cacheKey = `well:${wellNumber}`;
  const cachedWell = cacheService.get(cacheKey);
  if (cachedWell) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedWell
      } as ApiResponse<Well>),
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
  
  // Get specific well
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

  // Cache the result
  cacheService.set(cacheKey, well, 30 * 60); // 30 minutes TTL

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: well
    } as ApiResponse<Well>),
  };
}

async function getWellFields(databaseId: string) {
  // Check cache first
  const cacheKey = 'wellFields';
  const cachedFields = cacheService.get(`${databaseId}:${cacheKey}`);
  if (cachedFields) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedFields
      } as ApiResponse<string[]>),
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
  
  // Get well fields
  const wellFields = await sqliteService.getWellFields();

  // Cache the result
  cacheService.set(`${databaseId}:${cacheKey}`, wellFields, 60 * 60); // 1 hour TTL

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: wellFields
    } as ApiResponse<string[]>),
  };
}