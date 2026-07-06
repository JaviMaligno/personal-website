import { readFileSync, existsSync } from 'fs';
import matter from 'gray-matter';
import { generateSummary } from './generate-summary.js';
import { uploadImageToLinkedIn, uploadVideoToLinkedIn, createLinkedInPost, buildPostText } from './utils.js';

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

    // Compose the post text (summary + optional "💻 Code" line + "Read more" + hashtags,
    // truncated under 3000 chars). Pure logic lives in buildPostText (unit-tested).
    const postText = buildPostText({
      summary,
      postUrl,
      hashtags,
      repoUrl: frontmatter.repoUrl,
    });

    console.log(`\n📄 Post preview (${postText.length} chars):`);
    console.log('─'.repeat(60));
    console.log(postText);
    console.log('─'.repeat(60));
    console.log('');

    // Media: prefer a video (linkedinVideo), else an image (linkedinImage, then heroImage).
    // LinkedIn does not animate uploaded GIFs via the API, so motion demos must be MP4 video.
    let videoUrn = null;
    let imageUrn = null;

    if (frontmatter.linkedinVideo) {
      const videoPath = `public${frontmatter.linkedinVideo}`;
      if (existsSync(videoPath)) {
        console.log(`🎬 Uploading video: ${videoPath}\n`);
        try {
          videoUrn = await uploadVideoToLinkedIn(videoPath);
          console.log(`✅ Video uploaded: ${videoUrn}\n`);
        } catch (error) {
          console.error(`❌ Video upload failed: ${error.message}`);
          console.log(`⚠️  Falling back to image...\n`);
          videoUrn = null;
        }
      } else {
        console.warn(`⚠️  Video not found: ${videoPath} — falling back to image\n`);
      }
    }

    if (!videoUrn) {
      const imageToUpload = frontmatter.linkedinImage || frontmatter.heroImage;
      if (imageToUpload) {
        const imagePath = `public${imageToUpload}`;
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
    }

    // Publish to LinkedIn
    console.log(`🚀 Publishing to LinkedIn...\n`);
    await createLinkedInPost({
      personUrn: process.env.LINKEDIN_PERSON_URN,
      text: postText,
      imageUrn,
      videoUrn,
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
