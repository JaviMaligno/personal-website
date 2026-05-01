import { existsSync, readFileSync } from 'fs';
import matter from 'gray-matter';

/**
 * Update an existing Dev.to article
 * Usage: node scripts/devto/update-devto-post.js <article-id> <post-filename>
 * Example: node scripts/devto/update-devto-post.js 3158794 mcp-server-bitbucket.md
 */
function loadLocalEnv() {
  const envPath = new URL('../../.env', import.meta.url);
  if (!existsSync(envPath)) {
    return;
  }

  const envContent = readFileSync(envPath, 'utf-8');
  for (const line of envContent.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
    if (!match || line.trim().startsWith('#')) {
      continue;
    }

    const [, key, rawValue] = match;
    if (process.env[key] !== undefined) {
      continue;
    }

    let value = rawValue.trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    process.env[key] = value;
  }
}

function transformContentForDevto(content, siteUrl, canonicalUrl) {
  let devtoContent = content.replace(
    /<div[^>]*><iframe src="https:\/\/www\.loom\.com\/embed\/([^"]+)"[^>]*><\/iframe><\/div>/g,
    '**🎥 [Watch the video demo on Loom](https://www.loom.com/share/$1)**\n\n> _Note: Interactive video player available on the [original article]('+canonicalUrl+')_'
  );

  devtoContent = devtoContent.replace(
    /!\[([^\]]*)\]\(\/([^)]+)\)/g,
    `![$1](${siteUrl}/$2)`
  );

  devtoContent = devtoContent.replace(
    /(?<!!)\[([^\]]*)\]\(\/([^)]+)\)/g,
    `[$1](${siteUrl}/$2)`
  );

  return devtoContent;
}

async function updateDevtoPost() {
  try {
    loadLocalEnv();

    // Get article ID and post filename from command line
    const articleId = process.argv[2];
    const postFilename = process.argv[3];

    if (!articleId || !postFilename) {
      console.log(`
📝 Update Existing Dev.to Post

Usage: node scripts/devto/update-devto-post.js <article-id> <post-filename>

Example:
  node scripts/devto/update-devto-post.js 3158794 mcp-server-bitbucket.md

Note: Make sure DEVTO_API_KEY environment variable is set.
      `);
      process.exit(1);
    }

    console.log('📝 Updating Dev.to post...');

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

    // Prepare Dev.to article
    const slug = postFilename.replace('.md', '');
    const canonicalUrl = `${siteUrl}/en/blog/${slug}`;

    const devtoContent = transformContentForDevto(content, siteUrl, canonicalUrl);

    // Add CTA at the end of content
    const contentWithCTA = `${devtoContent}

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

    // Resolve cover image (support heroImage alias) and ensure absolute URL
    let coverImage = frontmatter.coverImage || frontmatter.heroImage;
    if (coverImage && coverImage.startsWith('/')) {
      coverImage = `${siteUrl}${coverImage}`;
    }

    const currentArticleResponse = await fetch(`https://dev.to/api/articles/${articleId}`, {
      headers: {
        'api-key': apiKey,
      },
    });

    if (!currentArticleResponse.ok) {
      const errorText = await currentArticleResponse.text();
      throw new Error(`Dev.to API error (${currentArticleResponse.status}): ${errorText}`);
    }

    const currentArticle = await currentArticleResponse.json();

    // Keep current publication status explicitly; DEV defaults omitted updates to draft.
    const article = {
      title: frontmatter.title,
      body_markdown: contentWithCTA,
      published: currentArticle.published,
      tags: tags,
      canonical_url: canonicalUrl,
      description: frontmatter.description,
      main_image: coverImage || `${siteUrl}/og-image.png`,
    };

    console.log(`\nUpdating Dev.to article ${articleId}:`);
    console.log(`  Canonical URL: ${canonicalUrl}`);
    console.log(`  Tags: ${tags.join(', ')}`);

    // Update on Dev.to
    const response = await fetch(`https://dev.to/api/articles/${articleId}`, {
      method: 'PUT',
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

    console.log(`\n✅ Successfully updated on Dev.to!`);
    console.log(`📍 Dev.to URL: ${result.url}`);
    console.log(`🆔 Article ID: ${result.id}`);
    console.log(`📊 Status: ${result.published ? 'Published' : 'Draft'}`);

  } catch (error) {
    console.error('\n❌ Error updating Dev.to post:', error.message);

    if (error.message.includes('ENOENT')) {
      console.error('\n💡 Make sure the post filename is correct and exists in src/content/blog/en/');
    }

    process.exit(1);
  }
}

updateDevtoPost();
