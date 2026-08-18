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

  // Two APIs, tried in order. The versioned /rest/posts endpoint is the one
  // LinkedIn documents for editing; the old v2/ugcPosts PARTIAL_UPDATE is kept
  // as a fallback because some tokens only work against it.
  // LinkedIn retira las versiones mensuales al cabo de un tiempo y devuelve 426
  // si pides una inactiva, sin decir cual vale: se prueban varias.
  const VERSIONES = ['202506', '202504', '202502', '202412', '202410', '202408'];
  const intentos = [
    ...VERSIONES.map(v => ({
      nombre: `rest/posts (${v})`,
      url: `https://api.linkedin.com/rest/posts/${encodeURIComponent(urn)}`,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
        'X-RestLi-Method': 'PARTIAL_UPDATE',
        'LinkedIn-Version': v,
      },
      body: { patch: { $set: { commentary: text } } },
    })),
    {
      nombre: 'v2/ugcPosts',
      url: `https://api.linkedin.com/v2/ugcPosts/${encodeURIComponent(urn)}`,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
        'X-RestLi-Method': 'PARTIAL_UPDATE',
      },
      body: {
        patch: {
          specificContent: {
            'com.linkedin.ugc.ShareContent': { shareCommentary: { $set: { text } } },
          },
        },
      },
    },
  ];

  for (const intento of intentos) {
    const res = await fetch(intento.url, {
      method: 'POST',
      headers: intento.headers,
      body: JSON.stringify(intento.body),
    });
    if (res.ok || res.status === 204) {
      console.log(`✅ Post updated via ${intento.nombre}. Reload it on LinkedIn to confirm.`);
      return;
    }
    const cuerpo = (await res.text()).slice(0, 160);
    if (res.status !== 426) console.error(`  ✗ ${intento.nombre} -> ${res.status}: ${cuerpo}`);
  }
  console.error('❌ Could not edit the post through the API. Edit it by hand on LinkedIn:');
  console.error('   the corrected text is in the file passed as the second argument.');
  process.exit(1);
}

main().catch(e => { console.error('❌', e.message); process.exit(1); });
