import { uploadImageToLinkedIn, uploadVideoToLinkedIn, createLinkedInPost, parseMentions, buildMentionAttributes } from './utils.js';
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { resolve, extname, basename } from 'path';

/**
 * Standalone LinkedIn post publisher — supports text, image(s), video, and @-mentions
 *
 * Usage:
 *   export LINKEDIN_ACCESS_TOKEN=your_token
 *   export LINKEDIN_PERSON_URN=your_urn
 *
 *   # From a text file:
 *   node scripts/linkedin/post-standalone.js scripts/linkedin/posts/my-post.txt [--dry-run]
 *
 * Media discovery (in priority order):
 *   1. Video at repo root: video-linkedin.mov/.mp4/... (single video, excludes images)
 *   2. Folder with the same name as the post: scripts/linkedin/posts/my-post/ → all images inside (natural sort)
 *   3. Numbered images at repo root: image-1.png, image-2.jpg, ... (numeric order)
 *   4. Single image at repo root: image.png/.jpg/... (legacy behavior)
 *
 * Mentions syntax inside the .txt:
 *   @[LangChain](urn:li:organization:25507109)     → company mention
 *   @[Jane Doe](urn:li:person:abc123)              → person mention
 * The visible text will be "LangChain" / "Jane Doe" and LinkedIn renders it
 * as a real mention (visible text must match the entity's real name).
 */

const VIDEO_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv', '.webm'];
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif'];
const MAX_IMAGES = 20; // LinkedIn multi-image feed post limit

function findImages(basePath, postPath) {
  // Priority 1: folder with the same name as the post .txt
  // e.g. scripts/linkedin/posts/my-post.txt → scripts/linkedin/posts/my-post/
  const postDir = postPath.replace(/\.txt$/, '');
  if (existsSync(postDir) && statSync(postDir).isDirectory()) {
    const images = readdirSync(postDir)
      .filter(f => IMAGE_EXTENSIONS.includes(extname(f).toLowerCase()))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
      .map(f => resolve(postDir, f));
    if (images.length > 0) return { images, source: `posts/${basename(postDir)}/` };
  }

  // Priority 2: numbered images at repo root (image-1.png, image-2.jpg, ...)
  const numbered = [];
  for (let i = 1; i <= MAX_IMAGES; i++) {
    for (const ext of IMAGE_EXTENSIONS) {
      const fullPath = resolve(basePath, `image-${i}${ext}`);
      if (existsSync(fullPath)) {
        numbered.push(fullPath);
        break; // only one extension per index
      }
    }
  }
  if (numbered.length > 0) return { images: numbered, source: 'repo root (image-N.*)' };

  // Priority 3: single image.png fallback (legacy)
  for (const ext of IMAGE_EXTENSIONS) {
    const fullPath = resolve(basePath, `image${ext}`);
    if (existsSync(fullPath)) return { images: [fullPath], source: 'repo root (image.*)' };
  }

  return { images: [], source: null };
}

function findMedia(basePath, postPath) {
  // Priority 0: video files matching video-linkedin.* pattern (video excludes images)
  for (const ext of VIDEO_EXTENSIONS) {
    const fullPath = resolve(basePath, `video-linkedin${ext}`);
    if (existsSync(fullPath)) return { type: 'video', paths: [fullPath], source: 'repo root' };
  }

  const { images, source } = findImages(basePath, postPath);
  if (images.length > 0) return { type: 'image', paths: images, source };

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
      const files = readdirSync(postsDir).filter(f => f.endsWith('.txt'));
      files.forEach(f => console.error(`  scripts/linkedin/posts/${f}`));
    }
    process.exit(1);
  }

  const postPath = resolve(basePath, postFile);
  if (!existsSync(postPath)) {
    console.error(`❌ File not found: ${postFile}`);
    process.exit(1);
  }

  const RAW_TEXT = readFileSync(postPath, 'utf-8').trim();

  // Parse @[Name](urn:li:...) mentions — offsets computed over the cleaned text
  const { text: POST_TEXT, mentions } = parseMentions(RAW_TEXT);

  console.log('📝 LinkedIn Standalone Post Publisher\n');
  console.log('─'.repeat(60));
  console.log(POST_TEXT);
  console.log('─'.repeat(60));
  console.log(`\n📊 Character count: ${POST_TEXT.length}/3000`);

  if (POST_TEXT.length > 3000) {
    console.error('❌ Post exceeds LinkedIn 3000 character limit!');
    process.exit(1);
  }

  console.log(`✅ Within character limit\n`);

  // Show detected mentions
  if (mentions.length > 0) {
    console.log(`🏷️  Mentions detected: ${mentions.length}`);
    mentions.forEach(m => {
      const type = m.urn.startsWith('urn:li:organization:') ? 'company' : 'person';
      console.log(`   • "${m.name}" (${type}) → ${m.urn} [start=${m.start}, length=${m.length}]`);
    });
    console.log('');
  } else {
    console.log('🏷️  No mentions detected\n');
  }

  // Find media
  const media = findMedia(basePath, postPath);
  if (media) {
    if (media.type === 'video') {
      const sizeMB = (statSync(media.paths[0]).size / 1024 / 1024).toFixed(1);
      console.log(`📎 Media found: VIDEO — ${media.paths[0]} (${sizeMB} MB)`);
      if (statSync(media.paths[0]).size > 200 * 1024 * 1024) {
        console.error('❌ Video exceeds LinkedIn 200 MB limit!');
        process.exit(1);
      }
    } else {
      console.log(`📎 Media found: ${media.paths.length} image(s) from ${media.source}`);
      media.paths.forEach((p, i) => {
        const sizeMB = (statSync(p).size / 1024 / 1024).toFixed(1);
        console.log(`   ${i + 1}. ${p} (${sizeMB} MB)`);
      });
      if (media.paths.length > MAX_IMAGES) {
        console.error(`❌ Too many images (${media.paths.length}). LinkedIn allows up to ${MAX_IMAGES}.`);
        process.exit(1);
      }
    }
  } else {
    console.log('⚠️  No media found — will post text-only');
  }

  if (dryRun) {
    console.log('\n🏃 DRY RUN — Post will NOT be published.');
    if (mentions.length > 0) {
      console.log('\n🔍 shareCommentary.attributes that would be sent:');
      console.log(JSON.stringify(buildMentionAttributes(mentions), null, 2));
    }
    console.log(`\n📷 Images that would be uploaded: ${media?.type === 'image' ? media.paths.length : 0}`);
    console.log('   Everything looks good. Run without --dry-run to publish.');
    process.exit(0);
  }

  // Validate env vars
  if (!process.env.LINKEDIN_ACCESS_TOKEN) {
    console.error('❌ Missing LINKEDIN_ACCESS_TOKEN. Set it with:');
    console.error('   export LINKEDIN_ACCESS_TOKEN=your_token');
    process.exit(1);
  }
  if (!process.env.LINKEDIN_PERSON_URN) {
    console.error('❌ Missing LINKEDIN_PERSON_URN. Set it with:');
    console.error('   export LINKEDIN_PERSON_URN=your_urn');
    process.exit(1);
  }

  // Upload media
  let imageUrns = [];
  let videoUrn = null;

  if (media) {
    try {
      if (media.type === 'video') {
        console.log(`\n🎬 Uploading video: ${media.paths[0]}\n`);
        videoUrn = await uploadVideoToLinkedIn(media.paths[0]);
        console.log(`✅ Video ready: ${videoUrn}\n`);
      } else {
        for (const [i, imagePath] of media.paths.entries()) {
          console.log(`\n🖼️  Uploading image ${i + 1}/${media.paths.length}: ${imagePath}\n`);
          const urn = await uploadImageToLinkedIn(imagePath);
          imageUrns.push(urn);
          console.log(`✅ Image ${i + 1} uploaded: ${urn}\n`);
        }
      }
    } catch (error) {
      console.error(`❌ Media upload failed: ${error.message}`);
      console.log('⚠️  Continuing with text-only post...\n');
      imageUrns = [];
      videoUrn = null;
    }
  }

  // Publish
  console.log('🚀 Publishing to LinkedIn...\n');
  await createLinkedInPost({
    personUrn: process.env.LINKEDIN_PERSON_URN,
    text: POST_TEXT,
    imageUrns,
    videoUrn,
    mentions,
  });

  console.log('\n✅ LinkedIn post published successfully!');
  console.log('🔗 Check at: https://linkedin.com/in/javier-aguilar-ai\n');
}

main().catch(error => {
  console.error('\n❌ Fatal error:', error.message);
  process.exit(1);
});
