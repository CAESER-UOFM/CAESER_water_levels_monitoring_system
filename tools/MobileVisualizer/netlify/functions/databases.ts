import { Handler, HandlerEvent } from '@netlify/functions';
import { GoogleDriveService } from '../../src/lib/api/services/googleDrive';
import { SQLiteService } from '../../src/lib/api/services/sqljs';
import { cacheService } from '../../src/lib/api/services/cache';
import { ApiResponse, DatabaseInfo } from '../../src/lib/api/api';

const googleDriveService = new GoogleDriveService();
const sqliteService = new SQLiteService();

export const handler: Handler = async (event: HandlerEvent) => {
  // Set CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
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
  const path = event.path.replace('/.netlify/functions/databases', '');
  const pathParts = path.split('/').filter(p => p);

  try {
    // GET /databases - List all databases
    if (event.httpMethod === 'GET' && pathParts.length === 0) {
      return await listDatabases();
    }

    // GET /databases/:id - Get database info
    if (event.httpMethod === 'GET' && pathParts.length === 1) {
      const databaseId = pathParts[0];
      return await getDatabaseInfo(databaseId);
    }

    // POST /databases/:id/refresh - Refresh database cache
    if (event.httpMethod === 'POST' && pathParts.length === 2 && pathParts[1] === 'refresh') {
      const databaseId = pathParts[0];
      return await refreshDatabaseCache(databaseId);
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
    console.error('Database function error:', error);
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

async function listDatabases() {
  // Check cache first
  const cachedDatabases = cacheService.getDatabaseList<DatabaseInfo[]>();
  if (cachedDatabases) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedDatabases
      } as ApiResponse<DatabaseInfo[]>),
    };
  }

  // Fetch from Google Drive
  const databases = await googleDriveService.listDatabases();
  
  // Enhance with additional metadata
  const enhancedDatabases = await Promise.all(
    databases.map(async (db) => {
      try {
        // Try to get well count from cache or calculate it
        const cachedStats = cacheService.getDatabaseStats(db.id);
        if (cachedStats?.wellsCount) {
          db.wellsCount = cachedStats.wellsCount;
        }
        return db;
      } catch (error) {
        console.warn(`Failed to get stats for database ${db.name}:`, error);
        return db;
      }
    })
  );

  // Cache the result
  cacheService.setDatabaseList(enhancedDatabases);

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: enhancedDatabases
    } as ApiResponse<DatabaseInfo[]>),
  };
}

async function getDatabaseInfo(id: string) {
  // Check cache first
  const cachedStats = cacheService.getDatabaseStats(id);
  if (cachedStats) {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        data: cachedStats
      } as ApiResponse),
    };
  }

  // Download and open database to get stats
  const databases = await googleDriveService.listDatabases();
  const database = databases.find(db => db.id === id);
  
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

  // Download and analyze database
  const filePath = await googleDriveService.downloadDatabase(id, database.name);
  await sqliteService.openDatabase(filePath);
  
  const stats = await sqliteService.getDatabaseStats();
  const wellFields = await sqliteService.getWellFields();
  
  const databaseInfo = {
    id: database.id,
    name: database.name,
    size: database.size,
    modified: database.modified,
    wellsCount: stats.wellsCount,
    readingsCount: stats.readingsCount,
    lastUpdate: stats.lastUpdate,
    wellFields
  };

  // Cache the stats
  cacheService.setDatabaseStats(id, databaseInfo);

  sqliteService.closeDatabase();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      data: databaseInfo
    } as ApiResponse),
  };
}

async function refreshDatabaseCache(id: string) {
  // Clear cache for this database
  cacheService.clearDatabaseCache(id);
  
  // Clear database list cache to force refresh
  cacheService.del('databases:list');

  // Clean up Google Drive cache for this file
  googleDriveService.cleanupCache();

  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: true,
      message: 'Database cache refreshed successfully'
    } as ApiResponse),
  };
}