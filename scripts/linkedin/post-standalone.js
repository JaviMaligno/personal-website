import { uploadImageToLinkedIn, uploadVideoToLinkedIn, createLinkedInPost } from './utils.js';
import { existsSync, readFileSync, statSync } from 'fs';
import { resolve, extname } from 'path';

/**
 * Standalone LinkedIn post publisher — supports text, image, and video posts
 *
 * Usage:
 *   export LINKEDIN_ACCESS_TOKEN=your_token
 *   export LINKEDIN_PERSON_URN=your_urn
 *
 *   # From a text file:
 *   node scripts/linkedin/post-standalone.js scripts/linkedin/posts/my-post.txt [--dry-run]
 *
 *   # With media (place image.png or video-linkedin-*.mov/.mp4 in repo root):
 *   node scripts/linkedin/post-standalone.js scripts/linkedin/posts/my-post.txt [--dry-run]
 *
 * The post text is read from the file passed as the first argument.
 */

const VIDEO_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv', '.webm'];
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif'];

function findMedia(basePath) {
  // Priority 1: video files matching video-linkedin-* pattern
  for (const ext of VIDEO_EXTENSIONS) {
    const candidates = [`video-linkedin${ext}`];
    for (const name of candidates) {
      const fullPath = resolve(basePath, name);
      if (existsSync(fullPath)) return { path: fullPath, type: 'video' };
    }
  }

  // Priority 2: image.png fallback
  for (const ext of IMAGE_EXTENSIONS) {
    const fullPath = resolve(basePath, `image${ext}`);
    if (existsSync(fullPath)) return { path: fullPath, type: 'image' };
  }

  return null;
}

async function main() {
  const args = process.argv.slice(2).filter(a => !a.startsWith('--'));
  const dryRun = process.argv.includes('--dry-run');
  const basePath = process.cwd();

  // Read post text from file argument
  const postFile = args[0];
  if (!postFile) {
    console.error(`Usage: node scripts/linkedin/post-standalone.js <post-file.txt> [--dry-run]

Example:
  node scripts/linkedin/post-standalone.js scripts/linkedin/posts/software-dissolving-1-skills.txt
  node scripts/linkedin/post-standalone.js scripts/linkedin/posts/software-dissolving-1-skills.txt --dry-run

Available posts:`);
    // List available posts
    const postsDir = resolve(basePath, 'scripts/linkedin/posts');
    if (existsSync(postsDir)) {
      const { readdirSync } = await import('fs');
      const files = readdirSync(postsDir).filter(f => f.endsWith('.txt'));
      files.forEach(f => console.error(`  scripts/linkedin/posts/${f}`));
    }
    process.exit(1);
  }

  const postPath = resolve(basePath, postFile);
  if (!existsSync(postPath)) {
    console.error(`\u274c File not found: ${postFile}`);
    process.exit(1);
  }

  const POST_TEXT = readFileSync(postPath, 'utf-8').trim();

  console.log('\ud83d\udcdd LinkedIn Standalone Post Publisher\n');
  console.log('\u2500'.repeat(60));
  console.log(POST_TEXT);
  console.log('\u2500'.repeat(60));
  console.log(`\n\ud83d\udcca Character count: ${POST_TEXT.length}/3000`);

  if (POST_TEXT.length > 3000) {
    console.error('\u274c Post exceeds LinkedIn 3000 character limit!');
    process.exit(1);
  }

  console.log(`\u2705 Within character limit\n`);

  // Find media
  const media = findMedia(basePath);
  if (media) {
    const sizeMB = (statSync(media.path).size / 1024 / 1024).toFixed(1);
    console.log(`\ud83d\udcce Media found: ${media.type.toUpperCase()} \u2014 ${media.path} (${sizeMB} MB)`);
    if (media.type === 'video' && statSync(media.path).size > 200 * 1024 * 1024) {
      console.error('\u274c Video exceeds LinkedIn 200 MB limit!');
      process.exit(1);
    }
  } else {
    console.log('\u26a0\ufe0f  No media found \u2014 will post text-only');
  }

  if (dryRun) {
    console.log('\n\ud83c\udfc3 DRY RUN \u2014 Post will NOT be published.');
    console.log('   Everything looks good. Run without --dry-run to publish.');
    process.exit(0);
  }

  // Validate env vars
  if (!process.env.LINKEDIN_ACCESS_TOKEN) {
    console.error('\u274c Missing LINKEDIN_ACCESS_TOKEN. Set it with:');
    console.error('   export LINKEDIN_ACCESS_TOKEN=your_token');
    process.exit(1);
  }
  if (!process.env.LINKEDIN_PERSON_URN) {
    console.error('\u274c Missing LINKEDIN_PERSON_URN. Set it with:');
    console.error('   export LINKEDIN_PERSON_URN=your_urn');
    process.exit(1);
  }

  // Upload media
  let imageUrn = null;
  let videoUrn = null;

  if (media) {
    try {
      if (media.type === 'video') {
        console.log(`\n\ud83c\udfac Uploading video: ${media.path}\n`);
        videoUrn = await uploadVideoToLinkedIn(media.path);
        console.log(`\u2705 Video ready: ${videoUrn}\n`);
      } else {
        console.log(`\n\ud83d\uddbc\ufe0f  Uploading image: ${media.path}\n`);
        imageUrn = await uploadImageToLinkedIn(media.path);
        console.log(`\u2705 Image uploaded: ${imageUrn}\n`);
      }
    } catch (error) {
      console.error(`\u274c Media upload failed: ${error.message}`);
      console.log('\u26a0\ufe0f  Continuing with text-only post...\n');
    }
  }

  // Publish
  console.log('\ud83d\ude80 Publishing to LinkedIn...\n');
  await createLinkedInPost({
    personUrn: process.env.LINKEDIN_PERSON_URN,
    text: POST_TEXT,
    imageUrn,
    videoUrn,
  });

  console.log('\n\u2705 LinkedIn post published successfully!');
  console.log('\ud83d\udd17 Check at: https://linkedin.com/in/javier-aguilar-ai\n');
}

main().catch(error => {
  console.error('\n\u274c Fatal error:', error.message);
  process.exit(1);
});
