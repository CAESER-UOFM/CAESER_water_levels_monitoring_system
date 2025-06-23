import express from 'express';
import helmet from 'helmet';
import compression from 'compression';
import dotenv from 'dotenv';
import { corsMiddleware } from '@/middleware/cors';
import { rateLimiter, dataRateLimiter } from '@/middleware/auth';
import { 
  validateDatabaseId, 
  validateWellNumber, 
  validateWellsQuery, 
  validateDataQuery 
} from '@/middleware/validation';

// Import controllers
import { listDatabases, getDatabaseInfo, refreshDatabaseCache } from '@/controllers/databases';
import { getWells, getWell, getWellFields } from '@/controllers/wells';
import { getWaterLevelData, getRechargeResults, getDataSummary } from '@/controllers/data';

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Security middleware
app.use(helmet({
  crossOriginEmbedderPolicy: false // Allow embedding for mobile apps
}));

// Compression middleware
app.use(compression());

// CORS middleware
app.use(corsMiddleware);

// Rate limiting
app.use('/api/', rateLimiter);
app.use('/api/databases/:id/data', dataRateLimiter);

// Parse JSON bodies
app.use(express.json({ limit: '10mb' }));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    message: 'Water Level Visualizer API is running',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Database routes
app.get('/api/databases', listDatabases);
app.get('/api/databases/:id', validateDatabaseId, getDatabaseInfo);
app.post('/api/databases/:id/refresh', validateDatabaseId, refreshDatabaseCache);

// Wells routes
app.get('/api/databases/:id/wells', 
  validateDatabaseId, 
  validateWellsQuery, 
  getWells
);

app.get('/api/databases/:id/wells/:wellNumber', 
  validateDatabaseId, 
  validateWellNumber, 
  getWell
);

app.get('/api/databases/:id/well-fields', 
  validateDatabaseId, 
  getWellFields
);

// Data routes
app.get('/api/databases/:id/data/:wellNumber', 
  validateDatabaseId, 
  validateWellNumber, 
  validateDataQuery, 
  getWaterLevelData
);

app.get('/api/databases/:id/recharge/:wellNumber', 
  validateDatabaseId, 
  validateWellNumber, 
  getRechargeResults
);

app.get('/api/databases/:id/summary/:wellNumber', 
  validateDatabaseId, 
  validateWellNumber, 
  getDataSummary
);

// Error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('API Error:', err);
  
  res.status(err.status || 500).json({
    success: false,
    error: err.message || 'Internal server error'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found'
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Water Level Visualizer API running on port ${PORT}`);
  console.log(`📋 Health check: http://localhost:${PORT}/api/health`);
  console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
});

export default app;