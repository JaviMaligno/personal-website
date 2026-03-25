import { uploadVideoToLinkedIn } from './utils.js';
import { existsSync } from 'fs';
import { resolve } from 'path';
import { readFileSync } from 'fs';

/**
 * Test video upload to LinkedIn WITHOUT publishing a post.
 * Validates: credentials, video registration, binary upload, processing.
 *
 * Usage:
 *   node scripts/linkedin/test-video-upload.js [path-to-video]
 */

// Load .env manually (no dotenv dependency)
const envPath = resolve(process.cwd(), '.env');
if (existsSync(envPath)) {
  readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) return;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim();
    if (!process.env[key]) process.env[key] = val;
  });
}

const videoPath = process.argv[2]
  || resolve(process.cwd(), 'video-linkedin-ai-cross-platform-demo.mov');

async function main() {
  console.log('🧪 LinkedIn Video Upload Test\n');

  // Check prerequisites
  if (!process.env.LINKEDIN_ACCESS_TOKEN) {
    console.error('❌ Missing LINKEDIN_ACCESS_TOKEN in .env');
    process.exit(1);
  }
  if (!process.env.LINKEDIN_PERSON_URN) {
    console.error('❌ Missing LINKEDIN_PERSON_URN in .env');
    process.exit(1);
  }
  if (!existsSync(videoPath)) {
    console.error(`❌ Video not found: ${videoPath}`);
    process.exit(1);
  }

  console.log(`✅ Credentials loaded`);
  console.log(`✅ Video found: ${videoPath}\n`);
  console.log('🚀 Starting upload test (this will upload but NOT create a post)...\n');

  try {
    const assetUrn = await uploadVideoToLinkedIn(videoPath);
    console.log(`\n🎉 TEST PASSED — Video uploaded and processed successfully!`);
    console.log(`   Asset URN: ${assetUrn}`);
    console.log(`\n   This asset is uploaded but NOT attached to any post.`);
    console.log(`   LinkedIn will auto-delete orphaned assets after some time.\n`);
  } catch (error) {
    console.error(`\n💥 TEST FAILED: ${error.message}\n`);
    if (error.message.includes('401')) {
      console.error('   → Token may be expired. Run: node scripts/linkedin-oauth-setup.js');
    } else if (error.message.includes('403')) {
      console.error('   → Token lacks required scopes (need w_member_social)');
    } else if (error.message.includes('timed out')) {
      console.error('   → Video processing took too long. Try a smaller/shorter file.');
    }
    process.exit(1);
  }
}

main();
