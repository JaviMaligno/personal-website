import { setOutput } from './utils.js';

/**
 * Check how many days are left before the LinkedIn access token expires.
 *
 * LinkedIn access tokens last 60 days and (for apps without programmatic
 * refresh tokens) cannot be auto-renewed — they must be regenerated via the
 * OAuth flow. This script uses the official Token Introspection endpoint to
 * read the real expiry date and warns when renewal is due.
 *
 * Ref: https://learn.microsoft.com/en-us/linkedin/shared/authentication/token-introspection
 *
 * Env: LINKEDIN_ACCESS_TOKEN, LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET
 *
 * Outputs (for GitHub Actions):
 *   needs_renewal: 'true' | 'false'
 *   days_left:     integer (or -1 if expired/unknown)
 *   status:        'active' | 'expired' | 'revoked' | 'error'
 *
 * Usage:
 *   node scripts/linkedin/check-token-expiry.js [--threshold 7]
 */

const DAY_MS = 24 * 60 * 60 * 1000;

function getThreshold() {
  const idx = process.argv.indexOf('--threshold');
  if (idx !== -1 && process.argv[idx + 1]) {
    const n = parseInt(process.argv[idx + 1], 10);
    if (!Number.isNaN(n)) return n;
  }
  return 7; // warn when 7 or fewer days remain
}

async function main() {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;
  const clientId = process.env.LINKEDIN_CLIENT_ID;
  const clientSecret = process.env.LINKEDIN_CLIENT_SECRET;
  const threshold = getThreshold();

  if (!accessToken || !clientId || !clientSecret) {
    console.error('❌ Missing LINKEDIN_ACCESS_TOKEN, LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET');
    setOutput('needs_renewal', 'true');
    setOutput('days_left', '-1');
    setOutput('status', 'error');
    process.exit(1);
  }

  try {
    const response = await fetch('https://www.linkedin.com/oauth/v2/introspectToken', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        token: accessToken,
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Introspection failed (${response.status}): ${text}`);
    }

    const data = await response.json();
    const status = data.status || (data.active ? 'active' : 'unknown');

    // expires_at is epoch seconds
    if (status !== 'active' || !data.expires_at) {
      console.log(`⚠️  Token status: ${status}. Renewal required now.`);
      setOutput('needs_renewal', 'true');
      setOutput('days_left', '-1');
      setOutput('status', status);
      return;
    }

    const expiresAtMs = Number(data.expires_at) * 1000;
    const daysLeft = Math.floor((expiresAtMs - Date.now()) / DAY_MS);
    const expiresOn = new Date(expiresAtMs).toISOString().slice(0, 10);

    console.log(`🔑 LinkedIn access token`);
    console.log(`   Status:     ${status}`);
    console.log(`   Expires on: ${expiresOn}`);
    console.log(`   Days left:  ${daysLeft}`);
    console.log(`   Threshold:  ${threshold} days`);

    const needsRenewal = daysLeft <= threshold;
    if (needsRenewal) {
      console.log(`\n⚠️  Token expires in ${daysLeft} day(s) — renewal is due.`);
    } else {
      console.log(`\n✅ Token healthy (${daysLeft} days left).`);
    }

    setOutput('needs_renewal', needsRenewal ? 'true' : 'false');
    setOutput('days_left', String(daysLeft));
    setOutput('status', status);
    setOutput('expires_on', expiresOn);
  } catch (error) {
    console.error('❌ Error checking token:', error.message);
    setOutput('needs_renewal', 'true');
    setOutput('days_left', '-1');
    setOutput('status', 'error');
    process.exit(1);
  }
}

main();
