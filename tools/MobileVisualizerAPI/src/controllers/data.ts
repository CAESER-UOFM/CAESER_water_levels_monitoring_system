import { Request, Response } from 'express';
import { GoogleDriveService } from '@/services/googleDrive';
import { SQLiteService } from '@/services/sqlite';
import { cacheService, CacheService } from '@/services/cache';
import { ApiResponse, WaterLevelReading, RechargeResult, DataQueryParams } from '@/types/api';

const googleDriveService = new GoogleDriveService();
const sqliteService = new SQLiteService();

export const getWaterLevelData = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id } = req.params;
    const params = req.validatedQuery as DataQueryParams;

    // Generate cache key based on parameters
    const cacheKey = CacheService.generateParamsKey(params);
    
    // Check cache first
    const cachedData = cacheService.getWaterLevelData(id, cacheKey);
    if (cachedData) {
      return res.json({
        success: true,
        data: cachedData
      } as ApiResponse<WaterLevelReading[]>);
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
    
    // Get water level data
    const waterLevelData = await sqliteService.getWaterLevelData(params);

    // Cache the result (shorter TTL for data queries)
    cacheService.setWaterLevelData(id, cacheKey, waterLevelData);

    sqliteService.closeDatabase();

    res.json({
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
    } as ApiResponse<WaterLevelReading[]>);

  } catch (error) {
    console.error('Failed to get water level data:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve water level data'
    } as ApiResponse);
  }
};

export const getRechargeResults = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id, wellNumber } = req.params;

    // Check cache first
    const cachedResults = cacheService.getRechargeResults(id, wellNumber);
    if (cachedResults) {
      return res.json({
        success: true,
        data: cachedResults
      } as ApiResponse<RechargeResult[]>);
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
    
    // Get recharge results
    const rechargeResults = await sqliteService.getRechargeResults(wellNumber);

    // Cache the result
    cacheService.setRechargeResults(id, wellNumber, rechargeResults);

    sqliteService.closeDatabase();

    res.json({
      success: true,
      data: rechargeResults,
      metadata: {
        wellNumber,
        totalCalculations: rechargeResults.length,
        methods: [...new Set(rechargeResults.map(r => r.method))]
      }
    } as ApiResponse<RechargeResult[]>);

  } catch (error) {
    console.error('Failed to get recharge results:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve recharge results'
    } as ApiResponse);
  }
};

export const getDataSummary = async (req: Request, res: Response): Promise<any> => {
  try {
    const { id, wellNumber } = req.params;

    // Check cache first
    const cacheKey = `summary:${wellNumber}`;
    const cachedSummary = cacheService.get(cacheKey);
    if (cachedSummary) {
      return res.json({
        success: true,
        data: cachedSummary
      } as ApiResponse);
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
    
    // Get well info
    const well = await sqliteService.getWell(wellNumber);
    if (!well) {
      sqliteService.closeDatabase();
      return res.status(404).json({
        success: false,
        error: 'Well not found'
      } as ApiResponse);
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

    res.json({
      success: true,
      data: summary
    } as ApiResponse);

  } catch (error) {
    console.error('Failed to get data summary:', error);
    sqliteService.closeDatabase();
    
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve data summary'
    } as ApiResponse);
  }
};