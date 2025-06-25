import type { 
  Well, 
  WaterLevelReading, 
  RechargeResult,
  WellsQueryParams,
  DataQueryParams,
  PaginatedResponse 
} from '../api';

interface TursoResponse {
  results: Array<{
    type: string;
    response: {
      type: string;
      result: {
        cols: Array<{ name: string; decltype: string | null }>;
        rows: Array<Array<{ type: string; value: string }>>;
      };
    };
  }>;
}

export class TursoService {
  private databaseUrl: string;
  private authToken: string;

  constructor() {
    // Get environment variables from Netlify
    const url = process.env.TURSO_DATABASE_URL;
    const authToken = process.env.TURSO_AUTH_TOKEN;

    // Remove debug logging

    if (!url || !authToken) {
      throw new Error('Missing Turso database credentials. Please set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables.');
    }

    this.databaseUrl = url;
    this.authToken = authToken;
  }

  private async execute(sql: string, args: any[] = []): Promise<{ columns: string[]; rows: any[] }> {
    // Convert Turso database URL to HTTP API URL  
    // From: libsql://caeser-water-monitoring-benjaled.aws-us-east-1.turso.io
    // To: https://caeser-water-monitoring-benjaled.aws-us-east-1.turso.io/v2/pipeline
    const apiUrl = this.databaseUrl.replace('libsql://', 'https://') + '/v2/pipeline';
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        requests: [{
          type: 'execute',
          stmt: {
            sql,
            args: args.length > 0 ? args.map(arg => {
              if (typeof arg === 'number') {
                return { type: 'integer', value: String(arg) };
              } else if (typeof arg === 'string') {
                return { type: 'text', value: arg };
              } else if (arg === null) {
                return { type: 'null' };
              } else {
                return { type: 'text', value: String(arg) };
              }
            }) : undefined
          }
        }]
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Turso API Error:', {
        status: response.status,
        statusText: response.statusText,
        errorText,
        apiUrl,
        sql
      });
      throw new Error(`Turso API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const data: TursoResponse = await response.json();
    
    if (!data.results || !data.results[0] || !data.results[0].response) {
      console.error('Unexpected Turso response:', data);
      throw new Error('Unexpected response from Turso API');
    }
    
    const result = data.results[0].response.result;
    
    // Convert Turso format to our expected format
    return {
      columns: result.cols.map(col => col.name),
      rows: result.rows.map(row => row.map(cell => cell.value))
    };
  }

  private rowToObject(columns: string[], row: any[]): Record<string, any> {
    const obj: Record<string, any> = {};
    columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  }

  async getWells(params: WellsQueryParams = {}): Promise<PaginatedResponse<Well>> {
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

      // Build WHERE conditions - simplified
      if (search) {
        whereConditions.push(`(well_number LIKE ? OR cae_number LIKE ? OR well_field LIKE ?)`);
        const searchPattern = `%${search}%`;
        queryParams.push(searchPattern, searchPattern, searchPattern);
      }

      if (field) {
        whereConditions.push(`well_field = ?`);
        queryParams.push(field);
      }

      // Skip hasData filter for now to simplify
      
      const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';
      const orderClause = `ORDER BY ${sortBy} ${sortOrder.toUpperCase()}`;

      // Get total count - simplified
      const countQuery = `SELECT COUNT(*) as total FROM wells ${whereClause}`;
      const countResult = await this.execute(countQuery, queryParams);
      const total = Number(countResult.rows[0][0]);

      // Simplified query first - just get basic well info
      const offset = (page - 1) * limit;
      const dataQuery = `
        SELECT 
          well_number, cae_number, well_field, cluster,
          latitude, longitude, top_of_casing, aquifer
        FROM wells
        ${whereClause.replace(/w\./g, '').replace(/wlr\./g, '')}
        ${orderClause.replace(/w\./g, '')}
        LIMIT ? OFFSET ?
      `;

      const result = await this.execute(dataQuery, [...queryParams, limit, offset]);

      const wells = await Promise.all(result.rows.map(async row => {
        const obj = this.rowToObject(result.columns, row);
        const wellBase = this.mapRowToWell(obj);
        
        // Get reading counts for this well from different tables
        try {
          const transducerCountQuery = `SELECT COUNT(*) as count FROM water_level_readings WHERE well_number = ?`;
          const transducerResult = await this.execute(transducerCountQuery, [wellBase.well_number]);
          const transducerCount = Number(transducerResult.rows[0][0]);

          const manualCountQuery = `SELECT COUNT(*) as count FROM manual_level_readings WHERE well_number = ?`;
          const manualResult = await this.execute(manualCountQuery, [wellBase.well_number]);
          const manualCount = Number(manualResult.rows[0][0]);

          const telemetryCountQuery = `SELECT COUNT(*) as count FROM telemetry_level_readings WHERE well_number = ?`;
          const telemetryResult = await this.execute(telemetryCountQuery, [wellBase.well_number]);
          const telemetryCount = Number(telemetryResult.rows[0][0]);
          
          return {
            ...wellBase,
            total_readings: transducerCount + manualCount + telemetryCount,
            has_manual_readings: manualCount > 0,
            has_transducer_data: transducerCount > 0,
            has_telemetry_data: telemetryCount > 0
          };
        } catch (err) {
          // If count fails, return well with 0 readings
          return {
            ...wellBase,
            total_readings: 0,
            has_manual_readings: false,
            has_transducer_data: false,
            has_telemetry_data: false
          };
        }
      }));

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
      console.error('Failed to get wells:', {
        error: error instanceof Error ? error.message : error,
        stack: error instanceof Error ? error.stack : undefined,
        params,
        databaseUrl: this.databaseUrl,
        hasAuthToken: !!this.authToken
      });
      throw new Error(`Failed to retrieve wells data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async getWell(wellNumber: string): Promise<Well | null> {
    try {
      const query = `
        SELECT 
          well_number, cae_number, well_field, cluster,
          latitude, longitude, top_of_casing, aquifer
        FROM wells
        WHERE well_number = ?
      `;

      const result = await this.execute(query, [wellNumber]);

      if (result.rows.length === 0) {
        return null;
      }

      const obj = this.rowToObject(result.columns, result.rows[0]);
      const wellBase = this.mapRowToWell(obj);
      
      // Get reading counts for this well from different tables
      try {
        const transducerCountQuery = `SELECT COUNT(*) as count FROM water_level_readings WHERE well_number = ?`;
        const transducerResult = await this.execute(transducerCountQuery, [wellBase.well_number]);
        const transducerCount = Number(transducerResult.rows[0][0]);

        const manualCountQuery = `SELECT COUNT(*) as count FROM manual_level_readings WHERE well_number = ?`;
        const manualResult = await this.execute(manualCountQuery, [wellBase.well_number]);
        const manualCount = Number(manualResult.rows[0][0]);

        const telemetryCountQuery = `SELECT COUNT(*) as count FROM telemetry_level_readings WHERE well_number = ?`;
        const telemetryResult = await this.execute(telemetryCountQuery, [wellBase.well_number]);
        const telemetryCount = Number(telemetryResult.rows[0][0]);
        
        return {
          ...wellBase,
          total_readings: transducerCount + manualCount + telemetryCount,
          has_manual_readings: manualCount > 0,
          has_transducer_data: transducerCount > 0,
          has_telemetry_data: telemetryCount > 0
        };
      } catch (err) {
        return {
          ...wellBase,
          total_readings: 0,
          has_manual_readings: false,
          has_transducer_data: false,
          has_telemetry_data: false
        };
      }
    } catch (error) {
      console.error(`Failed to get well ${wellNumber}:`, error);
      throw new Error('Failed to retrieve well data');
    }
  }

  async getWaterLevelData(params: DataQueryParams): Promise<WaterLevelReading[]> {
    const {
      wellNumber,
      startDate,
      endDate,
      dataType = 'all',
      downsample = false,
      maxPoints = 2000
    } = params;

    try {
      let allReadings: WaterLevelReading[] = [];

      // Query transducer data if needed
      if (dataType === 'all' || dataType === 'transducer') {
        const transducerReadings = await this.getTransducerData(wellNumber, startDate, endDate, downsample, maxPoints);
        allReadings = allReadings.concat(transducerReadings);
      }

      // Query manual data if needed  
      if (dataType === 'all' || dataType === 'manual') {
        const manualReadings = await this.getManualData(wellNumber, startDate, endDate);
        allReadings = allReadings.concat(manualReadings);
      }

      // Query telemetry data if needed
      if (dataType === 'all' || dataType === 'telemetry') {
        const telemetryReadings = await this.getTelemetryData(wellNumber, startDate, endDate);
        allReadings = allReadings.concat(telemetryReadings);
      }

      // Sort by timestamp
      allReadings.sort((a, b) => new Date(a.timestamp_utc).getTime() - new Date(b.timestamp_utc).getTime());

      return allReadings;
    } catch (error) {
      console.error(`Failed to get water level data for well ${wellNumber}:`, error);
      throw new Error('Failed to retrieve water level data');
    }
  }

  private async getTransducerData(wellNumber: string, startDate?: string, endDate?: string, downsample = false, maxPoints = 2000): Promise<WaterLevelReading[]> {
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

      const whereClause = whereConditions.join(' AND ');

      let query = `
        SELECT 
          id, well_number, timestamp_utc, julian_timestamp,
          water_level, temperature, baro_flag, level_flag
        FROM water_level_readings 
        WHERE ${whereClause}
        ORDER BY timestamp_utc ASC
      `;

      // Apply downsampling if requested and data is large
      if (downsample) {
        const countQuery = `SELECT COUNT(*) as total FROM water_level_readings WHERE ${whereClause}`;
        const countResult = await this.execute(countQuery, queryParams);
        
        const totalCount = Number(countResult.rows[0][0]);
        if (totalCount > maxPoints) {
          const skipFactor = Math.ceil(totalCount / maxPoints);
          query = `
            SELECT * FROM (
              SELECT 
                id, well_number, timestamp_utc, julian_timestamp,
                water_level, temperature, baro_flag, level_flag,
                ROW_NUMBER() OVER (ORDER BY timestamp_utc) as row_num
              FROM water_level_readings 
              WHERE ${whereClause}
            ) WHERE row_num % ${skipFactor} = 1
            ORDER BY timestamp_utc ASC
          `;
        }
      }

      const result = await this.execute(query, queryParams);

      return result.rows.map(row => {
        const obj = this.rowToObject(result.columns, row);
        return {
          ...this.mapRowToReading(obj),
          data_source: 'transducer' // Explicitly set for transducer data
        };
      });
    } catch (error) {
      console.error(`Failed to get transducer data for well ${wellNumber}:`, error);
      return [];
    }
  }

  private async getManualData(wellNumber: string, startDate?: string, endDate?: string): Promise<WaterLevelReading[]> {
    try {
      let whereConditions = ['well_number = ?'];
      let queryParams: any[] = [wellNumber];

      if (startDate) {
        whereConditions.push('measurement_date_utc >= ?');
        queryParams.push(startDate);
      }

      if (endDate) {
        whereConditions.push('measurement_date_utc <= ?');
        queryParams.push(endDate);
      }

      const whereClause = whereConditions.join(' AND ');

      const query = `
        SELECT 
          id, well_number, measurement_date_utc, dtw_avg, water_level,
          comments, data_source
        FROM manual_level_readings 
        WHERE ${whereClause}
        ORDER BY measurement_date_utc ASC
      `;

      const result = await this.execute(query, queryParams);

      return result.rows.map(row => {
        const obj = this.rowToObject(result.columns, row);
        return {
          id: Number(obj.id),
          well_number: String(obj.well_number),
          timestamp_utc: String(obj.measurement_date_utc), // Map measurement_date_utc to timestamp_utc
          julian_timestamp: undefined,
          water_level: obj.water_level ? Number(obj.water_level) : undefined,
          temperature: undefined, // Manual readings don't have temperature
          dtw: obj.dtw_avg ? Number(obj.dtw_avg) : undefined,
          data_source: 'manual', // Explicitly set for manual data
          baro_flag: undefined,
          level_flag: undefined,
          notes: obj.comments ? String(obj.comments) : undefined
        };
      });
    } catch (error) {
      console.error(`Failed to get manual data for well ${wellNumber}:`, error);
      return [];
    }
  }

  private async getTelemetryData(wellNumber: string, startDate?: string, endDate?: string): Promise<WaterLevelReading[]> {
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

      const whereClause = whereConditions.join(' AND ');

      const query = `
        SELECT 
          id, well_number, timestamp_utc, water_level, temperature
        FROM telemetry_level_readings 
        WHERE ${whereClause}
        ORDER BY timestamp_utc ASC
      `;

      const result = await this.execute(query, queryParams);

      return result.rows.map(row => {
        const obj = this.rowToObject(result.columns, row);
        return {
          id: Number(obj.id),
          well_number: String(obj.well_number),
          timestamp_utc: String(obj.timestamp_utc),
          julian_timestamp: undefined,
          water_level: obj.water_level ? Number(obj.water_level) : undefined,
          temperature: obj.temperature ? Number(obj.temperature) : undefined,
          dtw: undefined,
          data_source: 'telemetry', // Explicitly set for telemetry data
          baro_flag: undefined,
          level_flag: undefined,
          notes: undefined
        };
      });
    } catch (error) {
      console.error(`Failed to get telemetry data for well ${wellNumber}:`, error);
      return [];
    }
  }

  async getRechargeResults(wellNumber: string): Promise<RechargeResult[]> {
    try {
      const tables = ['rise_calculations', 'mrc_calculations', 'erc_calculations'];
      let allResults: RechargeResult[] = [];

      for (const table of tables) {
        try {
          // Check if table exists
          const tableExistsResult = await this.execute(
            `SELECT name FROM sqlite_master WHERE type='table' AND name=?`,
            [table]
          );

          if (tableExistsResult.rows.length > 0) {
            let method: 'RISE' | 'MRC' | 'ERC';
            if (table.includes('rise')) method = 'RISE';
            else if (table.includes('mrc')) method = 'MRC';
            else method = 'ERC';
            
            // Build query based on available columns
            const query = `
              SELECT *
              FROM ${table}
              WHERE well_number = ?
              ORDER BY created_at DESC
              LIMIT 50
            `;

            const result = await this.execute(query, [wellNumber]);

            const methodResults = result.rows.map(row => {
              const obj = this.rowToObject(result.columns, row);
              return {
                id: Number(obj.id || 0),
                well_number: String(obj.well_number),
                calculation_date: String(obj.created_at || obj.calculation_date || ''),
                start_date: String(obj.start_date || ''),
                end_date: String(obj.end_date || ''),
                recharge_mm: obj.recharge_mm ? Number(obj.recharge_mm) : undefined,
                recharge_inches: obj.recharge_inches ? Number(obj.recharge_inches) : undefined,
                specific_yield: obj.specific_yield ? Number(obj.specific_yield) : undefined,
                water_table_rise: obj.water_table_rise ? Number(obj.water_table_rise) : undefined,
                calculation_parameters: obj.calculation_parameters ? String(obj.calculation_parameters) : undefined,
                notes: obj.notes ? String(obj.notes) : undefined,
                method
              };
            });

            allResults = allResults.concat(methodResults);
          }
        } catch (tableError) {
          // Continue if table doesn't exist or query fails
          console.warn(`Table ${table} query failed:`, tableError);
        }
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
    try {
      const query = `
        SELECT DISTINCT well_field 
        FROM wells 
        WHERE well_field IS NOT NULL AND well_field != ''
        ORDER BY well_field
      `;

      const result = await this.execute(query);
      return result.rows.map(row => String(row[0]));
    } catch (error) {
      console.error('Failed to get well fields:', error);
      throw new Error('Failed to retrieve well fields');
    }
  }

  async getDatabaseStats(): Promise<{ wellsCount: number; readingsCount: number; lastUpdate: string | null }> {
    try {
      const wellsResult = await this.execute('SELECT COUNT(*) as count FROM wells');
      const readingsResult = await this.execute('SELECT COUNT(*) as count FROM water_level_readings');
      const lastUpdateResult = await this.execute(`
        SELECT MAX(timestamp_utc) as last_update 
        FROM water_level_readings
      `);

      return {
        wellsCount: Number(wellsResult.rows[0][0]),
        readingsCount: Number(readingsResult.rows[0][0]),
        lastUpdate: lastUpdateResult.rows[0][0] ? String(lastUpdateResult.rows[0][0]) : null
      };
    } catch (error) {
      console.error('Failed to get database stats:', error);
      throw new Error('Failed to retrieve database statistics');
    }
  }

  // Helper methods to map database rows to typed objects
  private mapRowToWell(row: any): Well {
    return {
      well_number: String(row.well_number),
      cae_number: row.cae_number ? String(row.cae_number) : undefined,
      well_field: row.well_field ? String(row.well_field) : undefined,
      cluster: row.cluster ? String(row.cluster) : undefined,
      latitude: row.latitude ? Number(row.latitude) : undefined,
      longitude: row.longitude ? Number(row.longitude) : undefined,
      top_of_casing: row.top_of_casing ? Number(row.top_of_casing) : undefined,
      ground_elevation: undefined, // Not in this schema
      well_depth: undefined, // Not in this schema
      screen_top: undefined, // Not in this schema
      screen_bottom: undefined, // Not in this schema
      aquifer_type: row.aquifer ? String(row.aquifer) as 'confined' | 'unconfined' | 'semiconfined' : undefined,
      static_water_level: undefined, // Not in this schema
      notes: undefined, // Not in this schema
      last_reading_date: row.last_reading_date ? String(row.last_reading_date) : undefined,
      total_readings: row.total_readings ? Number(row.total_readings) : 0,
      has_manual_readings: Boolean(row.has_manual_readings),
      has_transducer_data: Boolean(row.has_transducer_data),
      has_telemetry_data: Boolean(row.has_telemetry_data)
    };
  }

  private mapRowToReading(row: any): WaterLevelReading {
    return {
      id: Number(row.id),
      well_number: String(row.well_number),
      timestamp_utc: String(row.timestamp_utc),
      julian_timestamp: row.julian_timestamp ? Number(row.julian_timestamp) : undefined,
      water_level: row.water_level ? Number(row.water_level) : undefined,
      temperature: row.temperature ? Number(row.temperature) : undefined,
      dtw: undefined, // Not in this schema
      data_source: row.data_source ? String(row.data_source) : 'transducer', // Use database value
      baro_flag: row.baro_flag ? String(row.baro_flag) : undefined,
      level_flag: row.level_flag ? String(row.level_flag) : undefined,
      notes: undefined // Not in this schema
    };
  }

  private mapRowToRechargeResult(row: any): Omit<RechargeResult, 'method'> {
    return {
      id: Number(row.id),
      well_number: String(row.well_number),
      calculation_date: String(row.calculation_date),
      start_date: String(row.start_date),
      end_date: String(row.end_date),
      recharge_mm: row.recharge_mm ? Number(row.recharge_mm) : undefined,
      recharge_inches: row.recharge_inches ? Number(row.recharge_inches) : undefined,
      specific_yield: row.specific_yield ? Number(row.specific_yield) : undefined,
      water_table_rise: row.water_table_rise ? Number(row.water_table_rise) : undefined,
      calculation_parameters: row.calculation_parameters ? String(row.calculation_parameters) : undefined,
      notes: row.notes ? String(row.notes) : undefined
    };
  }
}