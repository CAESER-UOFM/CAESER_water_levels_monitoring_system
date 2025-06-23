import { Handler } from '@netlify/functions';
import { google } from 'googleapis';

export const handler: Handler = async () => {
  try {
    console.log('Testing Google Drive API...');
    
    // Use service account credentials from environment
    const credentials = {
      type: 'service_account',
      project_id: process.env.GOOGLE_PROJECT_ID,
      private_key_id: process.env.GOOGLE_PRIVATE_KEY_ID,
      private_key: process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
      client_email: process.env.GOOGLE_CLIENT_EMAIL,
      client_id: process.env.GOOGLE_CLIENT_ID,
      auth_uri: 'https://accounts.google.com/o/oauth2/auth',
      token_uri: 'https://oauth2.googleapis.com/token',
      auth_provider_x509_cert_url: 'https://www.googleapis.com/oauth2/v1/certs',
      client_x509_cert_url: process.env.GOOGLE_CLIENT_CERT_URL,
      universe_domain: 'googleapis.com'
    };

    console.log('Project ID:', process.env.GOOGLE_PROJECT_ID);
    console.log('Client Email:', process.env.GOOGLE_CLIENT_EMAIL);

    const auth = new google.auth.GoogleAuth({
      credentials,
      scopes: ['https://www.googleapis.com/auth/drive.readonly']
    });

    const drive = google.drive({ version: 'v3', auth });
    
    console.log('Authentication successful, testing folder access...');
    
    // Test 1: List files in the projects folder
    const projectsFolderId = '1JjiXRblLAf6rdhiOzrAaYik8bjNpBc9s';
    
    const response = await drive.files.list({
      q: `'${projectsFolderId}' in parents`,
      fields: 'files(id, name, size, modifiedTime, mimeType)',
      pageSize: 10
    });

    const files = response.data.files || [];
    
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: true,
        message: 'Google Drive API test successful',
        projectsFolderId,
        filesFound: files.length,
        files: files.map(f => ({
          id: f.id,
          name: f.name,
          size: f.size,
          mimeType: f.mimeType
        }))
      }),
    };

  } catch (error) {
    console.error('Google Drive API test failed:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      }),
    };
  }
};