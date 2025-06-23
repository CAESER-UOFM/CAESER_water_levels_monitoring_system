import { Request, Response } from 'express';
import { GoogleDriveService } from '@/services/googleDrive';
import { SQLiteService } from '@/services/sqlite';
import { cacheService, CacheService } from '@/services/cache';
import { ApiResponse, PaginatedResponse, Well, WellsQueryParams } from '@/types/api';

const googleDriveService = new GoogleDriveService();
const sqliteService = new SQLiteService();

export const getWells = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id } = req.params;
    const params = req.validatedQuery as WellsQueryParams;

    // Generate cache key based on parameters
    const cacheKey = CacheService.generateParamsKey(params);
    
    // Check cache first
    const cachedWells = cacheService.getWells(id, cacheKey);
    if (cachedWells) {
      return res.json(cachedWells);
    }

    // Get database list to find the database
    const databases = await googleDriveService.listDatabases();
    const database = databases.find(db => db.id === id);
    
    if (!database) {
      return res.status(404).json({
        success: false,
        error: 'Database not found'
      } as ApiResponse);
    }

    // Download and open database
    const filePath = await googleDriveService.downloadDatabase(id, database.name);
    await sqliteService.openDatabase(filePath);
    
    // Get wells with pagination
    const wells = await sqliteService.getWells(params);

    // Cache the result
    cacheService.setWells(id, cacheKey, wells);

    sqliteService.closeDatabase();

    res.json(wells);

  } catch (error) {
    console.error('Failed to get wells:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve wells data'
    } as PaginatedResponse<Well>);
  }
};

export const getWell = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id, wellNumber } = req.params;

    // Check cache first
    const cacheKey = `well:${wellNumber}`;
    const cachedWell = cacheService.get(cacheKey);
    if (cachedWell) {
      return res.json({
        success: true,
        data: cachedWell
      } as ApiResponse<Well>);
    }

    // Get database list to find the database
    const databases = await googleDriveService.listDatabases();
    const database = databases.find(db => db.id === id);
    
    if (!database) {
      return res.status(404).json({
        success: false,
        error: 'Database not found'
      } as ApiResponse);
    }

    // Download and open database
    const filePath = await googleDriveService.downloadDatabase(id, database.name);
    await sqliteService.openDatabase(filePath);
    
    // Get specific well
    const well = await sqliteService.getWell(wellNumber);

    if (!well) {
      sqliteService.closeDatabase();
      return res.status(404).json({
        success: false,
        error: 'Well not found'
      } as ApiResponse);
    }

    // Cache the result
    cacheService.set(cacheKey, well, 30 * 60); // 30 minutes TTL

    sqliteService.closeDatabase();

    res.json({
      success: true,
      data: well
    } as ApiResponse<Well>);

  } catch (error) {
    console.error('Failed to get well:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve well data'
    } as ApiResponse);
  }
};

export const getWellFields = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id } = req.params;

    // Check cache first
    const cacheKey = 'wellFields';
    const cachedFields = cacheService.get(`${id}:${cacheKey}`);
    if (cachedFields) {
      return res.json({
        success: true,
        data: cachedFields
      } as ApiResponse<string[]>);
    }

    // Get database list to find the database
    const databases = await googleDriveService.listDatabases();
    const database = databases.find(db => db.id === id);
    
    if (!database) {
      return res.status(404).json({
        success: false,
        error: 'Database not found'
      } as ApiResponse);
    }

    // Download and open database
    const filePath = await googleDriveService.downloadDatabase(id, database.name);
    await sqliteService.openDatabase(filePath);
    
    // Get well fields
    const wellFields = await sqliteService.getWellFields();

    // Cache the result
    cacheService.set(`${id}:${cacheKey}`, wellFields, 60 * 60); // 1 hour TTL

    sqliteService.closeDatabase();

    res.json({
      success: true,
      data: wellFields
    } as ApiResponse<string[]>);

  } catch (error) {
    console.error('Failed to get well fields:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve well fields'
    } as ApiResponse);
  }
};