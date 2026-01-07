import { setOutput } from './utils.js';

/**
 * Refreshes LinkedIn access token using refresh token
 * LinkedIn tokens expire after 60 days, but refresh tokens are valid for 1 year
 */
async function refreshAccessToken() {
  try {
    console.log('🔄 Refreshing LinkedIn access token...');

    const refreshToken = process.env.LINKEDIN_REFRESH_TOKEN;
    const clientId = process.env.LINKEDIN_CLIENT_ID;
    const clientSecret = process.env.LINKEDIN_CLIENT_SECRET;

    if (!refreshToken || !clientId || !clientSecret) {
      throw new Error('Missing required environment variables: LINKEDIN_REFRESH_TOKEN, LINKEDIN_CLIENT_ID, or LINKEDIN_CLIENT_SECRET');
    }

    const response = await fetch('https://www.linkedin.com/oauth/v2/accessToken', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: clientId,
        client_secret: clientSecret,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Token refresh failed (${response.status}): ${errorText}`);
    }

    const data = await response.json();

    console.log('✅ LinkedIn token refreshed successfully');
    console.log(`Token expires in: ${data.expires_in} seconds (${Math.floor(data.expires_in / 3600)} hours)`);

    // Output new access token for next step
    setOutput('access_token', data.access_token);

  } catch (error) {
    console.error('❌ Error refreshing LinkedIn token:', error.message);
    console.error('\nTroubleshooting:');
    console.error('1. Check that LINKEDIN_REFRESH_TOKEN is valid (expires after 1 year)');
    console.error('2. Verify LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET match your LinkedIn app');
    console.error('3. Ensure your LinkedIn app has "Share on LinkedIn" product enabled');
    process.exit(1);
  }
}

refreshAccessToken();
