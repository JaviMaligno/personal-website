import { readFileSync, existsSync } from 'fs';
import matter from 'gray-matter';
import { generateSummary } from './generate-summary.js';
import { uploadImageToLinkedIn, createLinkedInPost } from './utils.js';

/**
 * Main orchestrator: Generate summary, upload image (if exists), publish to LinkedIn
 */
async function publishToLinkedIn() {
  try {
    const postPath = process.env.NEW_POST_PATH;
    const siteUrl = process.env.SITE_URL;

    if (!postPath || !siteUrl) {
      throw new Error('Missing required environment variables: NEW_POST_PATH or SITE_URL');
    }

    console.log(`\n📝 Processing post: ${postPath}\n`);

    // Read post content
    if (!existsSync(postPath)) {
      throw new Error(`Post file not found: ${postPath}`);
    }

    const fileContent = readFileSync(postPath, 'utf-8');
    const { data: frontmatter, content: markdown } = matter(fileContent);

    // Extract slug from path (e.g., src/content/blog/en/my-post.md → my-post)
    const slug = postPath.split('/').pop().replace('.md', '');
    const postUrl = `${siteUrl}/en/blog/${slug}`;

    console.log(`Post details:`);
    console.log(`  Title: ${frontmatter.title}`);
    console.log(`  Slug: ${slug}`);
    console.log(`  URL: ${postUrl}`);
    console.log(`  Tags: ${frontmatter.tags?.join(', ')}`);
    console.log(`  LinkedIn Image: ${frontmatter.linkedinImage || 'None'}\n`);

    // Generate LinkedIn summary using Gemini
    console.log('🤖 Generating LinkedIn summary with Gemini...\n');
    const summary = await generateSummary({
      title: frontmatter.title,
      description: frontmatter.description,
      content: markdown,
      tags: frontmatter.tags || [],
    });

    // Prepare post text with hashtags
    const hashtags = frontmatter.tags
      .map(tag => `#${tag.replace(/\s+/g, '')}`)
      .join(' ');

    let postText = `${summary}\n\n📖 Read more: ${postUrl}\n\n${hashtags}`;

    // Check character limit (LinkedIn max: 3000 chars)
    if (postText.length > 3000) {
      console.warn(`⚠️  Post text exceeds 3000 chars (${postText.length}). Truncating...`);
      const maxSummaryLength = 3000 - postUrl.length - hashtags.length - 50; // Buffer for formatting
      const truncatedSummary = summary.substring(0, maxSummaryLength) + '...';
      postText = `${truncatedSummary}\n\n📖 Read more: ${postUrl}\n\n${hashtags}`;
    }

    console.log(`\n📄 Post preview (${postText.length} chars):`);
    console.log('─'.repeat(60));
    console.log(postText);
    console.log('─'.repeat(60));
    console.log('');

    // Handle image upload if linkedinImage exists
    let imageUrn = null;
    if (frontmatter.linkedinImage) {
      // Convert /blog/image.png to public/blog/image.png
      const imagePath = `public${frontmatter.linkedinImage}`;

      if (existsSync(imagePath)) {
        console.log(`🖼️  Uploading image: ${imagePath}\n`);
        try {
          imageUrn = await uploadImageToLinkedIn(imagePath);
          console.log(`✅ Image uploaded: ${imageUrn}\n`);
        } catch (error) {
          console.error(`❌ Image upload failed: ${error.message}`);
          console.log(`⚠️  Continuing with text-only post...\n`);
          imageUrn = null;
        }
      } else {
        console.warn(`⚠️  Image not found: ${imagePath}`);
        console.log(`⚠️  Posting without image...\n`);
      }
    }

    // Publish to LinkedIn
    console.log(`🚀 Publishing to LinkedIn...\n`);
    await createLinkedInPost({
      personUrn: process.env.LINKEDIN_PERSON_URN,
      text: postText,
      imageUrn,
    });

    console.log('\n✅ LinkedIn post published successfully!');
    console.log(`\nVerify at: https://linkedin.com/in/javier-aguilar-ai\n`);

  } catch (error) {
    console.error('\n❌ Error publishing to LinkedIn:', error.message);
    console.error('\nFull error:', error);
    process.exit(1);
  }
}

publishToLinkedIn();
