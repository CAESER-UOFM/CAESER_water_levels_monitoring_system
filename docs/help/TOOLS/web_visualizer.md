# Web Visualizer and API Documentation

## Overview

The CAESER Water Levels Monitoring System includes comprehensive web-based tools for data visualization, analysis, and collaboration. This guide covers the Mobile Visualizer, API endpoints, and integration capabilities.

---

## 📱 Mobile Visualizer (Web Application)

### **Technology Stack**
- **Frontend**: Next.js 14, React, TypeScript
- **Styling**: Tailwind CSS for responsive design
- **Charts**: Recharts for interactive data visualization
- **Database**: SQLite with optional Turso cloud integration
- **Deployment**: Netlify with serverless functions

### **Key Features**

#### **Responsive Interface**
```typescript
// Mobile-optimized component structure
interface MobileVisualizerProps {
  data: WaterLevelData[];
  wellInfo: WellMetadata;
  viewMode: 'mobile' | 'tablet' | 'desktop';
}

const MobileVisualizer: React.FC<MobileVisualizerProps> = ({ 
  data, 
  wellInfo, 
  viewMode 
}) => {
  const [selectedWell, setSelectedWell] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>({
    start: subDays(new Date(), 30),
    end: new Date()
  });

  // Touch-optimized controls
  const handleTouchNavigation = useCallback((gesture: TouchGesture) => {
    switch (gesture.type) {
      case 'swipe-left':
        navigateToNextWell();
        break;
      case 'swipe-right':
        navigateToPreviousWell();
        break;
      case 'pinch-zoom':
        adjustDateRange(gesture.scale);
        break;
    }
  }, []);

  return (
    <div className="mobile-visualizer touch-responsive">
      <WellSelector 
        wells={wells}
        selectedWell={selectedWell}
        onWellChange={setSelectedWell}
        viewMode={viewMode}
      />
      <InteractiveChart
        data={filteredData}
        onTouchGesture={handleTouchNavigation}
        responsive={true}
      />
      <DataControls
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        compact={viewMode === 'mobile'}
      />
    </div>
  );
};
```

#### **Well Browser and Search**
```typescript
interface WellBrowserProps {
  wells: WellData[];
  searchFilters: SearchFilters;
}

const WellBrowser: React.FC<WellBrowserProps> = ({ wells, searchFilters }) => {
  const [filteredWells, setFilteredWells] = useState<WellData[]>(wells);
  const [searchTerm, setSearchTerm] = useState('');

  // Advanced search functionality
  const applyFilters = useCallback((filters: SearchFilters) => {
    let filtered = wells;

    // Text search
    if (searchTerm) {
      filtered = filtered.filter(well =>
        well.well_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
        well.location.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Geographic filter
    if (filters.boundingBox) {
      filtered = filtered.filter(well =>
        isWithinBounds(well.coordinates, filters.boundingBox)
      );
    }

    // Data availability filter
    if (filters.dataDateRange) {
      filtered = filtered.filter(well =>
        hasDataInRange(well, filters.dataDateRange)
      );
    }

    // Aquifer type filter
    if (filters.aquiferTypes?.length > 0) {
      filtered = filtered.filter(well =>
        filters.aquiferTypes.includes(well.aquifer)
      );
    }

    setFilteredWells(filtered);
  }, [wells, searchTerm]);

  return (
    <div className="well-browser">
      <SearchControls
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        filters={searchFilters}
        onFiltersChange={applyFilters}
      />
      <WellList
        wells={filteredWells}
        onWellSelect={handleWellSelection}
        viewMode="grid"
      />
    </div>
  );
};
```

#### **Interactive Charts**
```typescript
interface ChartComponentProps {
  data: TimeSeriesData[];
  chartType: 'line' | 'scatter' | 'bar';
  interactive: boolean;
}

const InteractiveChart: React.FC<ChartComponentProps> = ({ 
  data, 
  chartType, 
  interactive 
}) => {
  const [zoomDomain, setZoomDomain] = useState<Domain | null>(null);
  const [selectedPoints, setSelectedPoints] = useState<DataPoint[]>([]);

  // Chart configuration for different types
  const chartConfig = useMemo(() => {
    switch (chartType) {
      case 'line':
        return {
          component: LineChart,
          dataKey: 'water_level',
          stroke: '#2563eb',
          strokeWidth: 2
        };
      case 'scatter':
        return {
          component: ScatterChart,
          dataKey: ['timestamp', 'water_level'],
          fill: '#3b82f6'
        };
      default:
        return {
          component: LineChart,
          dataKey: 'water_level',
          stroke: '#2563eb'
        };
    }
  }, [chartType]);

  // Handle zoom and pan
  const handleZoom = useCallback((domain: Domain) => {
    setZoomDomain(domain);
    // Filter data based on zoom domain
    const filteredData = data.filter(point =>
      point.timestamp >= domain.start && point.timestamp <= domain.end
    );
    onDataFilter?.(filteredData);
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        onMouseDown={interactive ? handleZoom : undefined}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="timestamp"
          type="number"
          domain={zoomDomain ? [zoomDomain.start, zoomDomain.end] : ['dataMin', 'dataMax']}
          tickFormatter={(value) => format(new Date(value), 'MMM dd')}
        />
        <YAxis
          label={{ value: 'Water Level (ft)', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip
          labelFormatter={(value) => format(new Date(value), 'PPP p')}
          formatter={(value: number) => [value.toFixed(2), 'Water Level (ft)']}
        />
        <Line
          type="monotone"
          dataKey="water_level"
          stroke="#2563eb"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};
```

### **Progressive Web App (PWA) Features**
```typescript
// Service Worker for offline functionality
const CACHE_NAME = 'water-levels-visualizer-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event: FetchEvent) => {
  // Cache-first strategy for static assets
  if (event.request.url.includes('/static/')) {
    event.respondWith(
      caches.match(event.request)
        .then((response) => response || fetch(event.request))
    );
  }
  
  // Network-first strategy for API calls
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful responses
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME)
              .then((cache) => cache.put(event.request, responseClone));
          }
          return response;
        })
        .catch(() => caches.match(event.request)) // Fallback to cache
    );
  }
});

// Background sync for data updates
self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'data-sync') {
    event.waitUntil(syncDataWithServer());
  }
});

async function syncDataWithServer() {
  try {
    // Sync pending uploads
    const pendingUploads = await getPendingUploads();
    for (const upload of pendingUploads) {
      await fetch('/api/sync', {
        method: 'POST',
        body: JSON.stringify(upload)
      });
    }
    
    // Download latest data
    const latestData = await fetch('/api/data/latest');
    const data = await latestData.json();
    await cacheLatestData(data);
    
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}
```

---

## 🔌 API Endpoints and Integration

### **RESTful API Architecture**
```typescript
// API route structure
const apiRoutes = {
  // Well management
  wells: {
    list: 'GET /api/v1/wells',
    get: 'GET /api/v1/wells/:id',
    create: 'POST /api/v1/wells',
    update: 'PUT /api/v1/wells/:id',
    delete: 'DELETE /api/v1/wells/:id'
  },
  
  // Data retrieval
  data: {
    waterLevels: 'GET /api/v1/wells/:id/water-levels',
    barometric: 'GET /api/v1/wells/:id/barometric',
    manual: 'GET /api/v1/wells/:id/manual-readings',
    telemetry: 'GET /api/v1/wells/:id/telemetry'
  },
  
  // Analysis and calculations
  analysis: {
    recharge: 'GET /api/v1/wells/:id/recharge',
    statistics: 'GET /api/v1/wells/:id/statistics',
    trends: 'GET /api/v1/wells/:id/trends'
  },
  
  // Export functionality
  export: {
    csv: 'GET /api/v1/export/csv',
    json: 'GET /api/v1/export/json',
    database: 'GET /api/v1/export/database'
  }
};
```

### **API Implementation Examples**

#### **Wells API**
```typescript
// GET /api/v1/wells
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const filters = {
      county: searchParams.get('county'),
      aquifer: searchParams.get('aquifer'),
      dataSource: searchParams.get('data_source'),
      bounds: searchParams.get('bounds') // "lat1,lng1,lat2,lng2"
    };

    const wells = await database.getWells(filters);
    
    return NextResponse.json({
      success: true,
      data: wells,
      count: wells.length,
      filters: filters
    });
    
  } catch (error) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// GET /api/v1/wells/:id/water-levels
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { searchParams } = new URL(request.url);
    const startDate = searchParams.get('start_date');
    const endDate = searchParams.get('end_date');
    const aggregation = searchParams.get('aggregation') || 'raw'; // raw, hourly, daily
    
    const query = {
      wellNumber: params.id,
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
      aggregation: aggregation as 'raw' | 'hourly' | 'daily'
    };

    const data = await database.getWaterLevelData(query);
    
    // Apply aggregation if requested
    const processedData = aggregation !== 'raw' 
      ? await aggregateData(data, aggregation)
      : data;

    return NextResponse.json({
      success: true,
      data: processedData,
      metadata: {
        wellNumber: params.id,
        recordCount: processedData.length,
        dateRange: {
          start: processedData[0]?.timestamp,
          end: processedData[processedData.length - 1]?.timestamp
        },
        aggregation: aggregation
      }
    });
    
  } catch (error) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
```

#### **Recharge Calculations API**
```typescript
// GET /api/v1/wells/:id/recharge
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { searchParams } = new URL(request.url);
    const method = searchParams.get('method') || 'rise'; // rise, mrc, erc
    const parameters = searchParams.get('parameters');
    
    // Parse custom parameters if provided
    const calculationParams = parameters 
      ? JSON.parse(parameters)
      : getDefaultParameters(method);

    // Get water level data for calculations
    const waterLevelData = await database.getWaterLevelData({
      wellNumber: params.id,
      qualityFlags: ['good', 'fair'] // Exclude poor quality data
    });

    // Perform recharge calculation based on method
    let rechargeResults;
    switch (method) {
      case 'rise':
        rechargeResults = await calculateRiseRecharge(waterLevelData, calculationParams);
        break;
      case 'mrc':
        rechargeResults = await calculateMrcRecharge(waterLevelData, calculationParams);
        break;
      case 'erc':
        rechargeResults = await calculateErcRecharge(waterLevelData, calculationParams);
        break;
      default:
        throw new Error(`Unsupported recharge method: ${method}`);
    }

    // Store results in database for future reference
    await database.storeRechargeResults(params.id, method, rechargeResults);

    return NextResponse.json({
      success: true,
      data: rechargeResults,
      metadata: {
        wellNumber: params.id,
        method: method,
        parameters: calculationParams,
        calculationDate: new Date().toISOString(),
        dataQuality: assessDataQuality(waterLevelData)
      }
    });
    
  } catch (error) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
```

### **Data Export API**
```typescript
// GET /api/v1/export/csv
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const wells = searchParams.get('wells')?.split(',') || [];
    const dataTypes = searchParams.get('types')?.split(',') || ['water_levels'];
    const startDate = searchParams.get('start_date');
    const endDate = searchParams.get('end_date');
    const format = searchParams.get('format') || 'standard';

    // Collect data from specified wells
    const exportData = await Promise.all(
      wells.map(async (wellNumber) => {
        const wellData = { wellNumber, datasets: {} };
        
        for (const dataType of dataTypes) {
          switch (dataType) {
            case 'water_levels':
              wellData.datasets.waterLevels = await database.getWaterLevelData({
                wellNumber,
                startDate: startDate ? new Date(startDate) : undefined,
                endDate: endDate ? new Date(endDate) : undefined
              });
              break;
            case 'manual_readings':
              wellData.datasets.manualReadings = await database.getManualReadings({
                wellNumber,
                startDate: startDate ? new Date(startDate) : undefined,
                endDate: endDate ? new Date(endDate) : undefined
              });
              break;
            case 'recharge_results':
              wellData.datasets.rechargeResults = await database.getRechargeResults({
                wellNumber
              });
              break;
          }
        }
        
        return wellData;
      })
    );

    // Convert to CSV format
    const csvData = await convertToCSV(exportData, format);
    
    // Set appropriate headers for file download
    const headers = new Headers({
      'Content-Type': 'text/csv',
      'Content-Disposition': `attachment; filename="water_levels_export_${new Date().toISOString().split('T')[0]}.csv"`
    });

    return new NextResponse(csvData, { headers });
    
  } catch (error) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
```

---

## 🗄️ Turso Database Integration

### **Cloud Database Configuration**
```typescript
interface TursoConfig {
  url: string;
  authToken: string;
  regions: string[];
  syncInterval: number;
  encryptionKey?: string;
}

class TursoDatabase {
  private client: LibsqlClient;
  private config: TursoConfig;

  constructor(config: TursoConfig) {
    this.config = config;
    this.client = createClient({
      url: config.url,
      authToken: config.authToken
    });
  }

  async syncFromLocal(localDbPath: string): Promise<SyncResult> {
    try {
      // Read local SQLite database
      const localDb = new Database(localDbPath);
      
      // Get list of tables to sync
      const tables = await this.getTablesToSync();
      
      const syncResults: TableSyncResult[] = [];
      
      for (const table of tables) {
        const result = await this.syncTable(localDb, table);
        syncResults.push(result);
      }
      
      // Update last sync timestamp
      await this.updateSyncTimestamp();
      
      return {
        success: true,
        syncedTables: syncResults,
        timestamp: new Date().toISOString()
      };
      
    } catch (error) {
      return {
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  private async syncTable(localDb: Database, tableName: string): Promise<TableSyncResult> {
    // Get last sync timestamp for this table
    const lastSync = await this.getLastSyncTimestamp(tableName);
    
    // Query for new/updated records since last sync
    const newRecords = localDb.prepare(`
      SELECT * FROM ${tableName} 
      WHERE updated_at > ? OR created_at > ?
    `).all(lastSync, lastSync);

    if (newRecords.length === 0) {
      return { table: tableName, recordsSynced: 0, status: 'up-to-date' };
    }

    // Batch insert/update to Turso
    const batch = newRecords.map(record => ({
      sql: `INSERT OR REPLACE INTO ${tableName} (${Object.keys(record).join(', ')}) 
            VALUES (${Object.keys(record).map(() => '?').join(', ')})`,
      args: Object.values(record)
    }));

    await this.client.batch(batch);

    return {
      table: tableName,
      recordsSynced: newRecords.length,
      status: 'synced'
    };
  }
}
```

### **Real-time Synchronization**
```typescript
class RealtimeSync {
  private tursoDb: TursoDatabase;
  private localDb: Database;
  private syncInterval: number;
  private isRunning: boolean = false;

  constructor(tursoDb: TursoDatabase, localDb: Database, syncInterval: number = 300000) {
    this.tursoDb = tursoDb;
    this.localDb = localDb;
    this.syncInterval = syncInterval; // 5 minutes default
  }

  start(): void {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.scheduleNextSync();
  }

  stop(): void {
    this.isRunning = false;
  }

  private scheduleNextSync(): void {
    if (!this.isRunning) return;

    setTimeout(async () => {
      try {
        await this.performSync();
      } catch (error) {
        console.error('Sync failed:', error);
      } finally {
        this.scheduleNextSync();
      }
    }, this.syncInterval);
  }

  private async performSync(): Promise<void> {
    // Two-way sync: local → cloud and cloud → local
    
    // 1. Push local changes to cloud
    await this.tursoDb.syncFromLocal(this.localDb.path);
    
    // 2. Pull cloud changes to local
    await this.syncFromCloud();
    
    // 3. Resolve any conflicts
    await this.resolveConflicts();
  }

  private async syncFromCloud(): Promise<void> {
    const lastSync = await this.getLastCloudSync();
    
    // Get updated records from Turso
    const updatedRecords = await this.tursoDb.client.execute({
      sql: "SELECT * FROM sync_log WHERE updated_at > ?",
      args: [lastSync]
    });

    // Apply changes to local database
    for (const record of updatedRecords.rows) {
      await this.applyChange(record);
    }
  }
}
```

---

## 📊 Performance Optimization

### **Data Caching Strategy**
```typescript
class DataCache {
  private cache: Map<string, CacheEntry> = new Map();
  private maxAge: number = 300000; // 5 minutes
  private maxSize: number = 100; // Maximum number of cached entries

  async get<T>(key: string, fetchFunction: () => Promise<T>): Promise<T> {
    const cached = this.cache.get(key);
    
    if (cached && !this.isExpired(cached)) {
      return cached.data as T;
    }

    // Fetch fresh data
    const freshData = await fetchFunction();
    
    // Store in cache
    this.set(key, freshData);
    
    return freshData;
  }

  private set(key: string, data: any): void {
    // Implement LRU eviction if cache is full
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  private isExpired(entry: CacheEntry): boolean {
    return Date.now() - entry.timestamp > this.maxAge;
  }
}

// Usage in API routes
const dataCache = new DataCache();

export async function GET(request: NextRequest) {
  const cacheKey = `water-levels-${wellId}-${startDate}-${endDate}`;
  
  const data = await dataCache.get(cacheKey, async () => {
    return await database.getWaterLevelData({ wellId, startDate, endDate });
  });

  return NextResponse.json({ data });
}
```

### **Database Query Optimization**
```sql
-- Optimized queries for large datasets

-- Efficient time-series queries using indexed julian timestamps
CREATE INDEX IF NOT EXISTS idx_water_readings_well_julian 
ON water_level_readings(well_number, julian_timestamp);

-- Aggregated data queries for visualization
SELECT 
  DATE(timestamp_utc) as date,
  AVG(water_level) as avg_level,
  MIN(water_level) as min_level,
  MAX(water_level) as max_level,
  COUNT(*) as reading_count
FROM water_level_readings 
WHERE well_number = ? 
  AND julian_timestamp BETWEEN ? AND ?
  AND level_flag != 'error'
GROUP BY DATE(timestamp_utc)
ORDER BY date;

-- Efficient geographic queries
CREATE INDEX IF NOT EXISTS idx_wells_coordinates 
ON wells(latitude, longitude);

SELECT * FROM wells 
WHERE latitude BETWEEN ? AND ? 
  AND longitude BETWEEN ? AND ?
  AND user_flag = 'approved';
```

---

## 🔐 Security and Access Control

### **API Authentication**
```typescript
// JWT-based authentication middleware
export async function authenticate(request: NextRequest): Promise<User | null> {
  const token = request.headers.get('Authorization')?.replace('Bearer ', '');
  
  if (!token) {
    return null;
  }

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!) as JWTPayload;
    const user = await database.getUser(payload.userId);
    
    if (!user || !user.isActive) {
      return null;
    }

    return user;
  } catch (error) {
    return null;
  }
}

// Role-based access control
export function requireRole(requiredRole: UserRole) {
  return async (request: NextRequest, user: User) => {
    const roleHierarchy = {
      'guest': 0,
      'user': 1,
      'admin': 2
    };

    if (roleHierarchy[user.role] < roleHierarchy[requiredRole]) {
      throw new Error('Insufficient permissions');
    }
  };
}
```

### **Data Validation**
```typescript
// Input validation schemas
const waterLevelQuerySchema = z.object({
  wellNumber: z.string().min(1).max(50),
  startDate: z.string().datetime().optional(),
  endDate: z.string().datetime().optional(),
  aggregation: z.enum(['raw', 'hourly', 'daily']).default('raw'),
  qualityFlags: z.array(z.enum(['good', 'fair', 'poor', 'error'])).optional()
});

// Validation middleware
export function validateQuery<T>(schema: z.ZodSchema<T>) {
  return (request: NextRequest): T => {
    const { searchParams } = new URL(request.url);
    const query = Object.fromEntries(searchParams.entries());
    
    try {
      return schema.parse(query);
    } catch (error) {
      throw new ValidationError('Invalid query parameters', error.errors);
    }
  };
}
```

---

**Next Steps**: Continue to [API Reference](api_reference.md) for complete API documentation and [Utilities](utilities.md) for information about helper tools and scripts.