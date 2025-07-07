import { Request, Response, NextFunction } from 'express';
import { WellsQueryParams, DataQueryParams } from '@/types/api';

// Validation middleware for query parameters
export const validateWellsQuery = (req: Request, res: Response, next: NextFunction): any => {
  const query = req.query;
  
  // Validate and sanitize parameters
  const params: WellsQueryParams = {};

  // Search parameter
  if (query.search && typeof query.search === 'string') {
    params.search = query.search.trim().substring(0, 100); // Limit length
  }

  // Field parameter
  if (query.field && typeof query.field === 'string') {
    params.field = query.field.trim().substring(0, 100);
  }

  // HasData parameter
  if (query.hasData !== undefined) {
    params.hasData = query.hasData === 'true';
  }

  // Page parameter
  if (query.page) {
    const page = parseInt(query.page as string);
    if (isNaN(page) || page < 1) {
      return res.status(400).json({
        success: false,
        error: 'Page must be a positive integer'
      });
    }
    params.page = Math.min(page, 1000); // Maximum page limit
  }

  // Limit parameter
  if (query.limit) {
    const limit = parseInt(query.limit as string);
    if (isNaN(limit) || limit < 1) {
      return res.status(400).json({
        success: false,
        error: 'Limit must be a positive integer'
      });
    }
    params.limit = Math.min(limit, 100); // Maximum limit of 100
  }

  // SortBy parameter
  if (query.sortBy && typeof query.sortBy === 'string') {
    const allowedSortFields = ['well_number', 'cae_number', 'last_reading_date'];
    if (allowedSortFields.includes(query.sortBy)) {
      params.sortBy = query.sortBy as any;
    }
  }

  // SortOrder parameter
  if (query.sortOrder && typeof query.sortOrder === 'string') {
    if (['asc', 'desc'].includes(query.sortOrder.toLowerCase())) {
      params.sortOrder = query.sortOrder.toLowerCase() as 'asc' | 'desc';
    }
  }

  req.validatedQuery = params;
  next();
};

export const validateDataQuery = (req: Request, res: Response, next: NextFunction): any => {
  const query = req.query;
  const params: DataQueryParams = {
    wellNumber: req.params.wellNumber
  };

  // Validate well number
  if (!params.wellNumber || typeof params.wellNumber !== 'string') {
    return res.status(400).json({
      success: false,
      error: 'Well number is required'
    });
  }

  // StartDate parameter
  if (query.startDate && typeof query.startDate === 'string') {
    const startDate = new Date(query.startDate);
    if (isNaN(startDate.getTime())) {
      return res.status(400).json({
        success: false,
        error: 'Invalid start date format'
      });
    }
    params.startDate = query.startDate;
  }

  // EndDate parameter
  if (query.endDate && typeof query.endDate === 'string') {
    const endDate = new Date(query.endDate);
    if (isNaN(endDate.getTime())) {
      return res.status(400).json({
        success: false,
        error: 'Invalid end date format'
      });
    }
    params.endDate = query.endDate;
  }

  // DataType parameter
  if (query.dataType && typeof query.dataType === 'string') {
    const allowedTypes = ['all', 'transducer', 'telemetry', 'manual'];
    if (allowedTypes.includes(query.dataType)) {
      params.dataType = query.dataType as any;
    }
  }

  // Downsample parameter
  if (query.downsample !== undefined) {
    params.downsample = query.downsample === 'true';
  }

  // MaxPoints parameter
  if (query.maxPoints) {
    const maxPoints = parseInt(query.maxPoints as string);
    if (isNaN(maxPoints) || maxPoints < 1) {
      return res.status(400).json({
        success: false,
        error: 'MaxPoints must be a positive integer'
      });
    }
    params.maxPoints = Math.min(maxPoints, 10000); // Maximum of 10,000 points
  }

  req.validatedQuery = params;
  next();
};

export const validateDatabaseId = (req: Request, res: Response, next: NextFunction): any => {
  const { id } = req.params;
  
  if (!id || typeof id !== 'string' || id.trim().length === 0) {
    return res.status(400).json({
      success: false,
      error: 'Database ID is required'
    });
  }

  // Basic validation for Google Drive file ID format
  if (!/^[a-zA-Z0-9_-]+$/.test(id)) {
    return res.status(400).json({
      success: false,
      error: 'Invalid database ID format'
    });
  }

  next();
};

export const validateWellNumber = (req: Request, res: Response, next: NextFunction): any => {
  const { wellNumber } = req.params;
  
  if (!wellNumber || typeof wellNumber !== 'string' || wellNumber.trim().length === 0) {
    return res.status(400).json({
      success: false,
      error: 'Well number is required'
    });
  }

  // Sanitize well number
  req.params.wellNumber = wellNumber.trim().substring(0, 50);
  next();
};

// Extend Express Request interface to include validated query
declare global {
  namespace Express {
    interface Request {
      validatedQuery?: any;
    }
  }
}