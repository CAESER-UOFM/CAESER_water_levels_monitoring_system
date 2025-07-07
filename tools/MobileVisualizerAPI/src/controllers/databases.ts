import { Request, Response } from 'express';
import { GoogleDriveService } from '@/services/googleDrive';
import { SQLiteService } from '@/services/sqlite';
import { cacheService, CacheService } from '@/services/cache';
import { ApiResponse, DatabaseInfo } from '@/types/api';

const googleDriveService = new GoogleDriveService();
const sqliteService = new SQLiteService();

export const listDatabases = async (req: Request, res: Response): Promise<any> => {
  try {
    // Check cache first
    const cachedDatabases = cacheService.getDatabaseList<DatabaseInfo[]>();
    if (cachedDatabases) {
      return res.json({
        success: true,
        data: cachedDatabases
      } as ApiResponse<DatabaseInfo[]>);
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

    res.json({
      success: true,
      data: enhancedDatabases
    } as ApiResponse<DatabaseInfo[]>);

  } catch (error) {
    console.error('Failed to list databases:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve database list'
    } as ApiResponse);
  }
};

export const getDatabaseInfo = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id } = req.params;

    // Check cache first
    const cachedStats = cacheService.getDatabaseStats(id);
    if (cachedStats) {
      return res.json({
        success: true,
        data: cachedStats
      } as ApiResponse);
    }

    // Download and open database to get stats
    const databases = await googleDriveService.listDatabases();
    const database = databases.find(db => db.id === id);
    
    if (!database) {
      return res.status(404).json({
        success: false,
        error: 'Database not found'
      } as ApiResponse);
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

    res.json({
      success: true,
      data: databaseInfo
    } as ApiResponse);

  } catch (error) {
    console.error('Failed to get database info:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve database information'
    } as ApiResponse);
  }
};

export const refreshDatabaseCache = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id } = req.params;

    // Clear cache for this database
    cacheService.clearDatabaseCache(id);
    
    // Clear database list cache to force refresh
    cacheService.del('databases:list');

    // Clean up Google Drive cache for this file
    googleDriveService.cleanupCache();

    res.json({
      success: true,
      message: 'Database cache refreshed successfully'
    } as ApiResponse);

  } catch (error) {
    console.error('Failed to refresh database cache:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to refresh database cache'
    } as ApiResponse);
  }
};