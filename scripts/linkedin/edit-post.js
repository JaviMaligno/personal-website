/**
 * Edit the commentary of an already-published LinkedIn post.
 *
 * Exists because the auto-generated post can land with wrong facts, and once it
 * has a comment you cannot delete and repost without losing the thread. LinkedIn
 * allows a PARTIAL_UPDATE on the ugcPost's shareCommentary; media and links stay
 * as they are.
 *
 * Usage:
 *   export LINKEDIN_ACCESS_TOKEN=...            (or have it in .env)
 *   node scripts/linkedin/edit-post.js <urn> <text-file> [--dry-run]
 *
 * Example:
 *   node scripts/linkedin/edit-post.js urn:li:share:7495402758574043136 \
 *     scripts/linkedin/posts/scaffolding-corrected-en.txt --dry-run
 */
import fs from 'fs';
import path from 'path';

function loadEnv() {
  for (const f of ['.env', '.env.local']) {
    const p = path.join(process.cwd(), f);
    if (!fs.existsSync(p)) continue;
    for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
  }
}

async function main() {
  loadEnv();
  const [urn, file] = process.argv.slice(2).filter(a => !a.startsWith('--'));
  const dryRun = process.argv.includes('--dry-run');

  if (!urn || !file) {
    console.error('Usage: node scripts/linkedin/edit-post.js <urn> <text-file> [--dry-run]');
    process.exit(1);
  }
  const token = process.env.LINKEDIN_ACCESS_TOKEN;
  if (!token) {
    console.error('❌ LINKEDIN_ACCESS_TOKEN not set (and not found in .env)');
    process.exit(1);
  }
  const text = fs.readFileSync(file, 'utf8').trimEnd();

  console.log(`\n📝 Editing ${urn}`);
  console.log('─'.repeat(60));
  console.log(text);
  console.log('─'.repeat(60));
  console.log(`${text.length} characters\n`);

  if (dryRun) {
    console.log('🔍 --dry-run: nothing sent.');
    return;
  }

  const res = await fetch(`https://api.linkedin.com/v2/ugcPosts/${encodeURIComponent(urn)}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-Restli-Protocol-Version': '2.0.0',
      'X-RestLi-Method': 'PARTIAL_UPDATE',
    },
    body: JSON.stringify({
      patch: {
        'specificContent': {
          'com.linkedin.ugc.ShareContent': {
            'shareCommentary': { $set: { text } },
          },
        },
      },
    }),
  });

  if (res.ok || res.status === 204) {
    console.log('✅ Post updated. Reload the post on LinkedIn to confirm.');
    return;
  }
  console.error(`❌ LinkedIn API error (${res.status}): ${await res.text()}`);
  process.exit(1);
}

main().catch(e => { console.error('❌', e.message); process.exit(1); });
