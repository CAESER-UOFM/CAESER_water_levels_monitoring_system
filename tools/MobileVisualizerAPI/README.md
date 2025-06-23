# Water Level Visualizer API

Backend API service for the mobile water level visualizer that provides read-only access to SQLite databases stored in Google Drive.

## 🎯 Overview

This API serves as a bridge between the mobile web app and Google Drive databases, eliminating the need for users to upload large (2GB+) database files. It provides secure, cached access to water level monitoring data.

## 🏗️ Architecture

```
Mobile App → API Server → Google Drive → SQLite Database
                ↓
          Cached JSON Data
```

## 🚀 Features

- **Google Drive Integration**: Direct access to databases stored in Google Drive
- **Intelligent Caching**: Multi-layer caching for optimal performance
- **Data Pagination**: Efficient handling of large datasets
- **Rate Limiting**: Protection against abuse
- **CORS Support**: Secure cross-origin requests
- **Type Safety**: Full TypeScript implementation

## 📋 API Endpoints

### Health Check
```
GET /api/health
```

### Databases
```
GET /api/databases                    # List all available databases
GET /api/databases/:id                # Get database information
POST /api/databases/:id/refresh       # Refresh database cache
```

### Wells
```
GET /api/databases/:id/wells          # Get wells with pagination/filtering
GET /api/databases/:id/wells/:wellNumber  # Get specific well details
GET /api/databases/:id/well-fields    # Get unique well field values
```

### Data
```
GET /api/databases/:id/data/:wellNumber      # Get water level readings
GET /api/databases/:id/recharge/:wellNumber  # Get recharge calculation results
GET /api/databases/:id/summary/:wellNumber   # Get data summary
```

## 🛠️ Setup

### Prerequisites
- Node.js 18+
- Google Drive service account credentials
- SQLite databases in Google Drive

### Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Google service account credentials
   ```

3. **Development**
   ```bash
   npm run dev
   ```

4. **Production build**
   ```bash
   npm run build
   npm start
   ```

## 🔧 Environment Variables

```env
# Google Drive Service Account
GOOGLE_PROJECT_ID=water-levels-monitoring-451921
GOOGLE_PRIVATE_KEY_ID=your_private_key_id
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
GOOGLE_CLIENT_EMAIL=service-account@project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

# Server Configuration
PORT=3001
NODE_ENV=production
```

## 🚀 Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Environment Variables in Vercel
Add these in your Vercel dashboard:
- `GOOGLE_PROJECT_ID`
- `GOOGLE_PRIVATE_KEY_ID`
- `GOOGLE_PRIVATE_KEY`
- `GOOGLE_CLIENT_EMAIL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_CERT_URL`

## 📊 Caching Strategy

- **Database List**: 1 hour TTL
- **Well Data**: 10 minutes TTL
- **Water Level Data**: 5 minutes TTL
- **Recharge Results**: 30 minutes TTL
- **File Downloads**: Cache with modification time check

## 🔒 Security

- **Rate Limiting**: 100 requests/15min per IP
- **CORS Whitelist**: Only allowed origins
- **Input Validation**: All parameters validated
- **SQL Injection Prevention**: Parameterized queries
- **HTTPS Only**: All communication encrypted

## 📈 Performance

- **Intelligent Caching**: Reduces database access
- **Data Pagination**: Handles large datasets efficiently
- **Compression**: Gzip compression enabled
- **Connection Pooling**: Optimized database connections

## 🐛 Troubleshooting

### Common Issues

1. **Google Drive Authentication Failed**
   - Verify service account credentials
   - Check Google Drive API is enabled
   - Ensure service account has access to files

2. **Database Not Found**
   - Check file ID is correct
   - Verify file is accessible by service account
   - Ensure file is a valid SQLite database

3. **Rate Limit Exceeded**
   - Implement request caching in client
   - Reduce request frequency
   - Use pagination for large datasets

### Debug Mode
```bash
NODE_ENV=development npm run dev
```

## 🔄 API Response Format

### Success Response
```json
{
  "success": true,
  "data": [...],
  "metadata": {
    "totalPoints": 1500,
    "dateRange": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Database not found"
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 156,
    "totalPages": 4
  }
}
```

## 📞 Support

For technical support:
1. Check server logs for error messages
2. Verify Google Drive credentials
3. Test with smaller databases first
4. Monitor rate limits and cache performance

---

**Note**: This API provides read-only access to water level monitoring data. No data modification or uploading capabilities are included for security.