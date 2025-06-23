import initSqlJs, { Database, SqlJsStatic } from 'sql.js';
import fs from 'fs';
import { Well, WaterLevelReading, RechargeResult, WellsQueryParams, DataQueryParams, PaginatedResponse } from '../api';

let SQL: SqlJsStatic | null = null;

// Initialize sql.js
async function initSqlJsNode(): Promise<void> {
  if (SQL) return;
  
  try {
    SQL = await initSqlJs();
  } catch (error) {
    console.error('Failed to initialize sql.js:', error);
    throw new Error('Database initialization failed');
  }
}

export class SQLiteService {
  private db: Database | null = null;
  private currentFilePath: string | null = null;

  async openDatabase(filePath: string): Promise<void> {
    try {
      // Close existing connection if any
      this.closeDatabase();

      // Initialize sql.js if needed
      await initSqlJsNode();
      if (!SQL) throw new Error('SQL.js not initialized');

      // Read the database file
      const buffer = fs.readFileSync(filePath);
      
      // Open database
      this.db = new SQL.Database(buffer);
      this.currentFilePath = filePath;
      
      // Verify database structure
      await this.verifyDatabaseStructure();
      console.log(`Database opened successfully: ${filePath}`);
    } catch (error) {
      console.error('Failed to open database:', error);
      throw new Error(`Failed to open database: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  closeDatabase(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
      this.currentFilePath = null;
    }
  }

  async getWells(params: WellsQueryParams = {}): Promise<PaginatedResponse<Well>> {
    if (!this.db) throw new Error('Database not connected');

    const {
      search = '',
      field = '',
      hasData,
      page = 1,
      limit = 50,
      sortBy = 'well_number',
      sortOrder = 'asc'
    } = params;

    try {
      let whereConditions: string[] = [];
      let queryParams: any[] = [];

      // Build WHERE conditions
      if (search) {
        whereConditions.push(`(well_number LIKE ? OR cae_number LIKE ? OR well_field LIKE ?)`);
        const searchPattern = `%${search}%`;
        queryParams.push(searchPattern, searchPattern, searchPattern);
      }

      if (field) {
        whereConditions.push(`well_field = ?`);
        queryParams.push(field);
      }

      if (hasData !== undefined) {
        if (hasData) {
          whereConditions.push(`(has_transducer_data = 1 OR has_telemetry_data = 1 OR has_manual_readings = 1)`);
        } else {
          whereConditions.push(`(has_transducer_data = 0 AND has_telemetry_data = 0 AND has_manual_readings = 0)`);
        }
      }

      const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';
      const orderClause = `ORDER BY ${sortBy} ${sortOrder.toUpperCase()}`;

      // Get total count
      const countQuery = `SELECT COUNT(*) as total FROM wells ${whereClause}`;
      const countStmt = this.db.prepare(countQuery);
      countStmt.bind(queryParams);
      countStmt.step();
      const countResult = countStmt.getAsObject() as { total: number };
      const total = countResult.total;
      countStmt.free();

      // Get paginated results
      const offset = (page - 1) * limit;
      const dataQuery = `
        SELECT 
          well_number, cae_number, well_field, cluster,
          latitude, longitude, top_of_casing, ground_elevation,
          well_depth, screen_top, screen_bottom, aquifer_type,
          static_water_level, notes, last_reading_date, total_readings,
          has_manual_readings, has_transducer_data, has_telemetry_data
        FROM wells 
        ${whereClause} 
        ${orderClause} 
        LIMIT ? OFFSET ?
      `;

      const stmt = this.db.prepare(dataQuery);
      stmt.bind([...queryParams, limit, offset]);

      const wells: Well[] = [];
      while (stmt.step()) {
        const row = stmt.getAsObject();
        wells.push(row as unknown as Well);
      }
      stmt.free();

      return {
        success: true,
        data: wells,
        pagination: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit)
        }
      };
    } catch (error) {
      console.error('Failed to get wells:', error);
      throw new Error('Failed to retrieve wells data');
    }
  }

  async getWell(wellNumber: string): Promise<Well | null> {
    if (!this.db) throw new Error('Database not connected');

    try {
      const query = `
        SELECT 
          well_number, cae_number, well_field, cluster,
          latitude, longitude, top_of_casing, ground_elevation,
          well_depth, screen_top, screen_bottom, aquifer_type,
          static_water_level, notes, last_reading_date, total_readings,
          has_manual_readings, has_transducer_data, has_telemetry_data
        FROM wells 
        WHERE well_number = ?
      `;

      const stmt = this.db.prepare(query);
      stmt.bind([wellNumber]);
      
      if (stmt.step()) {
        const row = stmt.getAsObject();
        stmt.free();
        return row as unknown as Well;
      }
      
      stmt.free();
      return null;
    } catch (error) {
      console.error(`Failed to get well ${wellNumber}:`, error);
      throw new Error('Failed to retrieve well data');
    }
  }

  async getWaterLevelData(params: DataQueryParams): Promise<WaterLevelReading[]> {
    if (!this.db) throw new Error('Database not connected');

    const {
      wellNumber,
      startDate,
      endDate,
      dataType = 'all',
      downsample = false,
      maxPoints = 2000
    } = params;

    try {
      let whereConditions = ['well_number = ?'];
      let queryParams: any[] = [wellNumber];

      if (startDate) {
        whereConditions.push('timestamp_utc >= ?');
        queryParams.push(startDate);
      }

      if (endDate) {
        whereConditions.push('timestamp_utc <= ?');
        queryParams.push(endDate);
      }

      if (dataType !== 'all') {
        whereConditions.push('data_source = ?');
        queryParams.push(dataType);
      }

      const whereClause = whereConditions.join(' AND ');

      let query = `
        SELECT 
          id, well_number, timestamp_utc, julian_timestamp,
          water_level, temperature, dtw, data_source,
          baro_flag, level_flag, notes
        FROM water_level_readings 
        WHERE ${whereClause}
        ORDER BY timestamp_utc ASC
      `;

      // Apply downsampling if requested and data is large
      if (downsample) {
        const countQuery = `SELECT COUNT(*) as total FROM water_level_readings WHERE ${whereClause}`;
        const countStmt = this.db.prepare(countQuery);
        countStmt.bind(queryParams);
        countStmt.step();
        const countResult = countStmt.getAsObject() as { total: number };
        countStmt.free();
        
        if (countResult.total > maxPoints) {
          const skipFactor = Math.ceil(countResult.total / maxPoints);
          query = `
            SELECT * FROM (
              SELECT 
                id, well_number, timestamp_utc, julian_timestamp,
                water_level, temperature, dtw, data_source,
                baro_flag, level_flag, notes,
                ROW_NUMBER() OVER (ORDER BY timestamp_utc) as row_num
              FROM water_level_readings 
              WHERE ${whereClause}
            ) WHERE row_num % ${skipFactor} = 1
            ORDER BY timestamp_utc ASC
          `;
        }
      }

      const stmt = this.db.prepare(query);
      stmt.bind(queryParams);

      const readings: WaterLevelReading[] = [];
      while (stmt.step()) {
        const row = stmt.getAsObject();
        readings.push(row as unknown as WaterLevelReading);
      }
      stmt.free();

      return readings;
    } catch (error) {
      console.error(`Failed to get water level data for well ${wellNumber}:`, error);
      throw new Error('Failed to retrieve water level data');
    }
  }

  async getRechargeResults(wellNumber: string): Promise<RechargeResult[]> {
    if (!this.db) throw new Error('Database not connected');

    try {
      const tables = ['rise_results', 'mrc_results', 'emr_results'];
      let allResults: RechargeResult[] = [];

      for (const table of tables) {
        // Check if table exists
        const tableExistsStmt = this.db.prepare(`
          SELECT name FROM sqlite_master 
          WHERE type='table' AND name=?
        `);
        tableExistsStmt.bind([table]);
        
        if (tableExistsStmt.step()) {
          const method = table.split('_')[0].toUpperCase() as 'RISE' | 'MRC' | 'EMR';
          
          const query = `
            SELECT 
              id, well_number, calculation_date, start_date, end_date,
              recharge_mm, recharge_inches, specific_yield, water_table_rise,
              calculation_parameters, notes
            FROM ${table}
            WHERE well_number = ?
            ORDER BY calculation_date DESC
          `;

          const stmt = this.db.prepare(query);
          stmt.bind([wellNumber]);

          while (stmt.step()) {
            const row = stmt.getAsObject();
            allResults.push({
              ...row,
              method
            } as unknown as RechargeResult);
          }
          stmt.free();
        }
        tableExistsStmt.free();
      }

      return allResults.sort((a, b) => 
        new Date(b.calculation_date).getTime() - new Date(a.calculation_date).getTime()
      );
    } catch (error) {
      console.error(`Failed to get recharge results for well ${wellNumber}:`, error);
      throw new Error('Failed to retrieve recharge results');
    }
  }

  async getWellFields(): Promise<string[]> {
    if (!this.db) throw new Error('Database not connected');

    try {
      const query = `
        SELECT DISTINCT well_field 
        FROM wells 
        WHERE well_field IS NOT NULL AND well_field != ''
        ORDER BY well_field
      `;

      const stmt = this.db.prepare(query);
      const results: string[] = [];
      
      while (stmt.step()) {
        const row = stmt.getAsObject() as { well_field: string };
        results.push(row.well_field);
      }
      stmt.free();

      return results;
    } catch (error) {
      console.error('Failed to get well fields:', error);
      throw new Error('Failed to retrieve well fields');
    }
  }

  async getDatabaseStats(): Promise<{ wellsCount: number; readingsCount: number; lastUpdate: string | null }> {
    if (!this.db) throw new Error('Database not connected');

    try {
      const wellsStmt = this.db.prepare('SELECT COUNT(*) as count FROM wells');
      wellsStmt.step();
      const wellsCount = (wellsStmt.getAsObject() as { count: number }).count;
      wellsStmt.free();
      
      const readingsStmt = this.db.prepare('SELECT COUNT(*) as count FROM water_level_readings');
      readingsStmt.step();
      const readingsCount = (readingsStmt.getAsObject() as { count: number }).count;
      readingsStmt.free();
      
      const lastUpdateStmt = this.db.prepare(`
        SELECT MAX(timestamp_utc) as last_update 
        FROM water_level_readings
      `);
      lastUpdateStmt.step();
      const lastUpdate = (lastUpdateStmt.getAsObject() as { last_update: string | null }).last_update;
      lastUpdateStmt.free();

      return {
        wellsCount,
        readingsCount,
        lastUpdate
      };
    } catch (error) {
      console.error('Failed to get database stats:', error);
      throw new Error('Failed to retrieve database statistics');
    }
  }

  private async verifyDatabaseStructure(): Promise<void> {
    if (!this.db) throw new Error('Database not connected');

    const requiredTables = ['wells', 'water_level_readings'];
    
    for (const table of requiredTables) {
      const stmt = this.db.prepare(`
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
      `);
      stmt.bind([table]);

      if (!stmt.step()) {
        stmt.free();
        throw new Error(`Required table '${table}' not found in database`);
      }
      stmt.free();
    }
  }
}