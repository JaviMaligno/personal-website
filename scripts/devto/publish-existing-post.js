import { readFileSync } from 'fs';
import matter from 'gray-matter';

/**
 * Test script to publish an existing blog post to Dev.to
 * Usage: node scripts/devto/publish-existing-post.js <post-filename>
 * Example: node scripts/devto/publish-existing-post.js mcp-server-bitbucket.md
 */
async function publishExistingPost() {
  try {
    // Get post filename from command line
    const postFilename = process.argv[2];

    if (!postFilename) {
      console.log(`
📝 Publish Existing Post to Dev.to

Usage: node scripts/devto/publish-existing-post.js <post-filename>

Example:
  node scripts/devto/publish-existing-post.js mcp-server-bitbucket.md

Available posts:
  - azure-content-filter-workarounds.md
  - claude-code-skills-blog-writer.md
  - mcp-server-bitbucket.md
  - parallel-ai-agent-development.md
  - typescript-ai-agent-guardrails.md

Note: Make sure DEVTO_API_KEY environment variable is set.
      `);
      process.exit(1);
    }

    console.log('📝 Publishing existing post to Dev.to...');

    // Validate environment variables
    const apiKey = process.env.DEVTO_API_KEY;
    const siteUrl = process.env.SITE_URL || 'https://www.javieraguilar.ai';

    if (!apiKey) {
      throw new Error('DEVTO_API_KEY environment variable is required');
    }

    // Construct path to post
    const postPath = `src/content/blog/en/${postFilename}`;

    console.log(`📄 Reading post: ${postPath}`);

    // Read and parse the markdown file
    const fileContent = readFileSync(postPath, 'utf-8');
    const { data: frontmatter, content } = matter(fileContent);

    console.log(`\nPost details:`);
    console.log(`  Title: ${frontmatter.title}`);
    console.log(`  Description: ${frontmatter.description?.substring(0, 100)}...`);
    console.log(`  Tags: ${frontmatter.tags?.join(', ')}`);
    console.log(`  Publish Date: ${frontmatter.pubDate}`);

    // Prepare Dev.to article
    const slug = postFilename.replace('.md', '');
    const canonicalUrl = `${siteUrl}/en/blog/${slug}`;

    // Add CTA at the end of content
    const contentWithCTA = `${content}

---

*Originally published on [javieraguilar.ai](${canonicalUrl})*

Want to see more AI agent projects? Check out my [portfolio](${siteUrl}) where I showcase multi-agent systems, MCP development, and compliance automation.
`;

    // Prepare tags (Dev.to max 4 tags)
    // Sanitize: lowercase, replace spaces with empty string, only alphanumeric
    const tags = (frontmatter.tags || [])
      .slice(0, 4)
      .map(tag => tag.toLowerCase().replace(/\s+/g, '').replace(/[^a-z0-9]/g, ''))
      .filter(tag => tag.length > 0);

    // Always publish as DRAFT for testing
    const article = {
      title: frontmatter.title,
      body_markdown: contentWithCTA,
      published: false, // Always draft for testing
      tags: tags,
      canonical_url: canonicalUrl,
      description: frontmatter.description,
      main_image: frontmatter.coverImage || `${siteUrl}/og-image.png`,
    };

    console.log(`\nPublishing to Dev.to:`);
    console.log(`  Canonical URL: ${canonicalUrl}`);
    console.log(`  Tags: ${tags.join(', ')}`);
    console.log(`  Status: DRAFT (for testing)`);

    // Ask for confirmation
    console.log(`\n⚠️  This will create a DRAFT article on Dev.to.`);
    console.log(`   Press Ctrl+C to cancel, or wait 3 seconds to continue...`);

    await new Promise(resolve => setTimeout(resolve, 3000));

    // Publish to Dev.to
    console.log(`\n🚀 Publishing...`);

    const response = await fetch('https://dev.to/api/articles', {
      method: 'POST',
      headers: {
        'api-key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ article }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Dev.to API error (${response.status}): ${errorText}`);
    }

    const result = await response.json();

    console.log(`\n✅ Successfully published to Dev.to!`);
    console.log(`\n📍 Dev.to Draft URL: ${result.url}`);
    console.log(`🆔 Article ID: ${result.id}`);
    console.log(`\n💡 Next steps:`);
    console.log(`   1. Visit ${result.url}`);
    console.log(`   2. Review the article formatting`);
    console.log(`   3. Add a cover image if needed`);
    console.log(`   4. Click "Publish" when ready`);

  } catch (error) {
    console.error('\n❌ Error publishing to Dev.to:', error.message);

    if (error.message.includes('ENOENT')) {
      console.error('\n💡 Make sure the post filename is correct and exists in src/content/blog/en/');
    }

    process.exit(1);
  }
}

publishExistingPost();
