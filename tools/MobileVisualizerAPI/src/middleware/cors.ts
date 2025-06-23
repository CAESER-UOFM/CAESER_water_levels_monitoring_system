import cors from 'cors';

// CORS configuration for the API
export const corsMiddleware = cors({
  origin: function (origin, callback) {
    // Allow requests with no origin (mobile apps, Postman, etc.)
    if (!origin) return callback(null, true);
    
    // Define allowed origins
    const allowedOrigins = [
      'http://localhost:3000', // Local development
      'http://localhost:3001', // Alternative local port
      'https://water-level-visualizer-mobile.netlify.app', // Production mobile app
      /https:\/\/.*\.netlify\.app$/, // Any Netlify preview URLs
      /http:\/\/localhost:\d+$/ // Any localhost port for development
    ];

    // Check if origin is allowed
    const isAllowed = allowedOrigins.some(allowedOrigin => {
      if (typeof allowedOrigin === 'string') {
        return origin === allowedOrigin;
      } else if (allowedOrigin instanceof RegExp) {
        return allowedOrigin.test(origin);
      }
      return false;
    });

    if (isAllowed) {
      callback(null, true);
    } else {
      console.warn(`CORS blocked origin: ${origin}`);
      callback(new Error('Not allowed by CORS'));
    }
  },
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  credentials: false, // No cookies needed for this API
  maxAge: 86400 // Cache preflight response for 24 hours
});