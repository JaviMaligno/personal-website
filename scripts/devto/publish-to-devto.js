import { readFileSync } from 'fs';
import matter from 'gray-matter';

/**
 * Publishes a blog post to Dev.to
 * Requires: DEVTO_API_KEY, NEW_POST_PATH, SITE_URL environment variables
 */
async function publishToDevto() {
  try {
    console.log('📝 Publishing to Dev.to...');

    // Validate environment variables
    const apiKey = process.env.DEVTO_API_KEY;
    const postPath = process.env.NEW_POST_PATH;
    const siteUrl = process.env.SITE_URL || 'https://www.javieraguilar.ai';

    if (!apiKey) {
      throw new Error('DEVTO_API_KEY environment variable is required');
    }

    if (!postPath) {
      throw new Error('NEW_POST_PATH environment variable is required');
    }

    console.log(`📄 Reading post: ${postPath}`);

    // Read and parse the markdown file
    const fileContent = readFileSync(postPath, 'utf-8');
    const { data: frontmatter, content } = matter(fileContent);

    console.log(`\nPost details:`);
    console.log(`  Title: ${frontmatter.title}`);
    console.log(`  Description: ${frontmatter.description?.substring(0, 100)}...`);
    console.log(`  Tags: ${frontmatter.tags?.join(', ')}`);

    // Check if post should be published to Dev.to
    if (frontmatter.publishToDevto === false) {
      console.log('\n⏭️  Post has publishToDevto: false, skipping Dev.to publication');
      return;
    }

    // Prepare Dev.to article
    const slug = postPath.split('/').pop().replace('.md', '');
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

    // Determine publish status (default: true = auto-publish)
    const published = frontmatter.devtoPublished !== false;

    // Resolve cover image (support heroImage alias) and ensure absolute URL
    let coverImage = frontmatter.coverImage || frontmatter.heroImage;
    if (coverImage && coverImage.startsWith('/')) {
      coverImage = `${siteUrl}${coverImage}`;
    }

    const article = {
      title: frontmatter.title,
      body_markdown: contentWithCTA,
      published: published,
      tags: tags,
      canonical_url: canonicalUrl,
      description: frontmatter.description,
      main_image: coverImage || `${siteUrl}/og-image.png`,
    };

    console.log(`\nPublishing to Dev.to:`);
    console.log(`  Canonical URL: ${canonicalUrl}`);
    console.log(`  Tags: ${tags.join(', ')}`);
    console.log(`  Status: ${published ? 'PUBLISHED' : 'DRAFT'}`);

    // Check if article already exists by canonical URL
    console.log(`\n🔍 Checking for existing article...`);
    const articlesResponse = await fetch('https://dev.to/api/articles/me/all?per_page=1000', {
      headers: {
        'api-key': apiKey,
      },
    });

    if (!articlesResponse.ok) {
      throw new Error(`Failed to fetch articles (${articlesResponse.status})`);
    }

    const existingArticles = await articlesResponse.json();
    const existingArticle = existingArticles.find(a => a.canonical_url === canonicalUrl);

    let response;
    if (existingArticle) {
      console.log(`📝 Article exists (ID: ${existingArticle.id}), updating...`);
      response = await fetch(`https://dev.to/api/articles/${existingArticle.id}`, {
        method: 'PUT',
        headers: {
          'api-key': apiKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ article }),
      });
    } else {
      console.log(`📝 Creating new article...`);
      response = await fetch('https://dev.to/api/articles', {
        method: 'POST',
        headers: {
          'api-key': apiKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ article }),
      });
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Dev.to API error (${response.status}): ${errorText}`);
    }

    const result = await response.json();

    console.log(`\n✅ Successfully published to Dev.to!`);
    console.log(`📍 Dev.to URL: ${result.url}`);
    console.log(`🆔 Article ID: ${result.id}`);
    console.log(`📊 Status: ${result.published ? 'Published' : 'Draft'}`);

    if (!result.published) {
      console.log(`\n💡 Tip: Your article was created as a DRAFT.`);
      console.log(`   Visit ${result.url} to review and publish it manually.`);
    }

  } catch (error) {
    console.error('❌ Error publishing to Dev.to:', error.message);
    process.exit(1);
  }
}

publishToDevto();
