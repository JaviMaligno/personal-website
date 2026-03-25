import { uploadImageToLinkedIn, uploadVideoToLinkedIn, createLinkedInPost } from './utils.js';
import { existsSync, statSync } from 'fs';
import { resolve, extname } from 'path';

/**
 * Standalone LinkedIn post publisher — supports text, image, and video posts
 *
 * Usage:
 *   export LINKEDIN_ACCESS_TOKEN=your_token
 *   export LINKEDIN_PERSON_URN=your_urn
 *   node scripts/linkedin/post-standalone.js [--dry-run]
 *
 * Media: place a file named "image.png" or "video-linkedin-*.mov/.mp4" in the repo root.
 *   Video takes priority over image if both exist.
 */

const POST_TEXT = `Remember that meme where someone asks a simple question and instead of answering, you send them a "Let Me Google That For You" video?

I just did something similar — but upgraded to the AI era.

A colleague needed repo links and README URLs for two microservices to fill in DevOps deployment tickets. She didn't have Bitbucket access, the tickets were cloned from a template with wrong placeholders, and she was manually chasing info across Slack, Jira, Confluence, and Bitbucket.

Instead of copying links one by one, I asked Claude Code to handle it. In under 3 minutes, it:

→ Read our Slack conversation to understand what was needed
→ Pulled the Confluence page to identify which services were involved
→ Read both Jira tickets to see the template structure
→ Fetched repos, READMEs, tags, .env files, and billing codes from Bitbucket
→ Updated both Jira tickets with the correct information
→ Sent her a Slack summary with all the links

Six different platforms. Zero copy-paste. Three minutes.

The video attached is the actual recording of the interaction — in Spanish, but you can see the tools firing in real time.

The real power isn't in any single AI capability. It's in connecting them: Slack + Jira + Confluence + Bitbucket + Claude, all in one conversation. The MCP connectors turn what would be 30 minutes of tab-switching into a single natural language request.

Instead of sending her a LMGTFY link, I sent the screen recording of an AI doing all the work. Same energy, 2026 edition.

What repetitive cross-platform tasks are eating your time?

#AI #Automation #Productivity #GenerativeAI #DevOps #AIAgents #ClaudeAI #SoftwareEngineering #FutureOfWork #LLM`;

const VIDEO_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv', '.webm'];
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif'];

function findMedia(basePath) {
  // Priority 1: video files matching video-linkedin-* pattern
  for (const ext of VIDEO_EXTENSIONS) {
    const candidates = [`video-linkedin-ai-cross-platform-demo${ext}`];
    for (const name of candidates) {
      const fullPath = resolve(basePath, name);
      if (existsSync(fullPath)) return { path: fullPath, type: 'video' };
    }
  }

  // Priority 2: any video-linkedin-* file
  // (we can't glob easily without extra deps, so check common names)

  // Priority 3: image.png fallback
  for (const ext of IMAGE_EXTENSIONS) {
    const fullPath = resolve(basePath, `image${ext}`);
    if (existsSync(fullPath)) return { path: fullPath, type: 'image' };
  }

  return null;
}

async function main() {
  const dryRun = process.argv.includes('--dry-run');
  const basePath = process.cwd();

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

  // Find media
  const media = findMedia(basePath);
  if (media) {
    const sizeMB = (statSync(media.path).size / 1024 / 1024).toFixed(1);
    console.log(`📎 Media found: ${media.type.toUpperCase()} — ${media.path} (${sizeMB} MB)`);
    if (media.type === 'video' && statSync(media.path).size > 200 * 1024 * 1024) {
      console.error('❌ Video exceeds LinkedIn 200 MB limit!');
      process.exit(1);
    }
  } else {
    console.log('⚠️  No media found — will post text-only');
  }

  if (dryRun) {
    console.log('\n🏃 DRY RUN — Post will NOT be published.');
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
  let imageUrn = null;
  let videoUrn = null;

  if (media) {
    try {
      if (media.type === 'video') {
        console.log(`\n🎬 Uploading video: ${media.path}\n`);
        videoUrn = await uploadVideoToLinkedIn(media.path);
        console.log(`✅ Video ready: ${videoUrn}\n`);
      } else {
        console.log(`\n🖼️  Uploading image: ${media.path}\n`);
        imageUrn = await uploadImageToLinkedIn(media.path);
        console.log(`✅ Image uploaded: ${imageUrn}\n`);
      }
    } catch (error) {
      console.error(`❌ Media upload failed: ${error.message}`);
      console.log('⚠️  Continuing with text-only post...\n');
    }
  }

  // Publish
  console.log('🚀 Publishing to LinkedIn...\n');
  await createLinkedInPost({
    personUrn: process.env.LINKEDIN_PERSON_URN,
    text: POST_TEXT,
    imageUrn,
    videoUrn,
  });

  console.log('\n✅ LinkedIn post published successfully!');
  console.log('🔗 Check at: https://linkedin.com/in/javier-aguilar-ai\n');
}

main().catch(error => {
  console.error('\n❌ Fatal error:', error.message);
  process.exit(1);
});
