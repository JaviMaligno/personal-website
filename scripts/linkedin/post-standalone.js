import { uploadImageToLinkedIn, createLinkedInPost } from './utils.js';
import { existsSync } from 'fs';
import { resolve } from 'path';

/**
 * Standalone LinkedIn post publisher
 * 
 * Usage:
 *   export LINKEDIN_ACCESS_TOKEN=your_token
 *   export LINKEDIN_PERSON_URN=your_urn
 *   node scripts/linkedin/post-standalone.js [--dry-run]
 */

const POST_TEXT = `A tiny habit that's been a game-changer when working with AI:

Name your terminals. 🏷️

When you have 3+ Claude sessions running in parallel — each on a different project, each mid-way through a complex task — it's incredibly easy to lose track.

Which one was handling the deploy? Which one was running tests? Which one was refactoring?

The fix is ridiculously simple: name each terminal after what it's doing.

In the image you can see how I do it:
• "mlflow-azure-migration" → infrastructure migration
• "renew-certificate" → certificate management
• "name-vectorizer-nexus" → Nexus integration

When you come back after a meeting (or making coffee ☕), a single glance at the tabs tells you exactly what's happening in each session.

It's one of those micro-habits that seems insignificant but makes all the difference when you scale how you work with AI agents.

How do you organize your sessions when running multiple agents in parallel?

#AI #Productivity #ClaudeAI #DevTools #AIAgents #DeveloperExperience`;

const IMAGE_PATH = resolve(process.cwd(), 'image.png');

async function main() {
  const dryRun = process.argv.includes('--dry-run');

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

  if (dryRun) {
    console.log('🏃 DRY RUN — Post will NOT be published.');
    console.log(`📎 Image: ${IMAGE_PATH} (exists: ${existsSync(IMAGE_PATH)})`);
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

  // Upload image
  let imageUrn = null;
  if (existsSync(IMAGE_PATH)) {
    console.log(`🖼️  Uploading image: ${IMAGE_PATH}\n`);
    try {
      imageUrn = await uploadImageToLinkedIn(IMAGE_PATH);
      console.log(`✅ Image uploaded: ${imageUrn}\n`);
    } catch (error) {
      console.error(`❌ Image upload failed: ${error.message}`);
      console.log('⚠️  Continuing with text-only post...\n');
    }
  } else {
    console.warn(`⚠️  Image not found at: ${IMAGE_PATH}`);
    console.log('⚠️  Posting without image...\n');
  }

  // Publish
  console.log('🚀 Publishing to LinkedIn...\n');
  await createLinkedInPost({
    personUrn: process.env.LINKEDIN_PERSON_URN,
    text: POST_TEXT,
    imageUrn,
  });

  console.log('\n✅ LinkedIn post published successfully!');
  console.log('🔗 Check at: https://linkedin.com/in/javier-aguilar-ai\n');
}

main().catch(error => {
  console.error('\n❌ Fatal error:', error.message);
  process.exit(1);
});
