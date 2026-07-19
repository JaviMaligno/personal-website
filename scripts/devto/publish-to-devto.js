import { existsSync, readFileSync } from 'fs';
import matter from 'gray-matter';

/**
 * Publishes a blog post to Dev.to
 * Requires: DEVTO_API_KEY, NEW_POST_PATH, SITE_URL environment variables
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

async function publishToDevto() {
  try {
    loadLocalEnv();

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

    let devtoContent = content;

    // --- Dev.to compatibility: it renders neither inline SVG nor $$…$$ KaTeX ---
    // 1) Strip scoped <style> blocks (would show as raw CSS text on Dev.to).
    devtoContent = devtoContent.replace(/<style>[\s\S]*?<\/style>\s*/g, '');

    // 2) Replace each inline SVG <figure class="cwm-fig"> with a hosted image
    //    (pre-rendered to public/blog/<slug>-fig-<n>.{gif,png}, in document order).
    //    alt = the SVG aria-label; caption = the <figcaption> text.
    let figIdx = 0;
    devtoContent = devtoContent.replace(/<figure class="cwm-fig">([\s\S]*?)<\/figure>/g, (_m, inner) => {
      figIdx++;
      const alt = (inner.match(/aria-label="([^"]*)"/) || [, `Figure ${figIdx}`])[1];
      let cap = (inner.match(/<figcaption>([\s\S]*?)<\/figcaption>/) || [, ''])[1];
      cap = cap.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
      const base = `${slug}-fig-${figIdx}`;
      const ext = existsSync(`public/blog/${base}.gif`) ? 'gif' : 'png';
      const url = `${siteUrl}/blog/${base}.${ext}`;
      return `![${alt}](${url})\n\n*${cap}*`;
    });

    // 3) KaTeX: block $$…$$ → Dev.to's {% katex %} liquid tag.
    devtoContent = devtoContent.replace(/\$\$\s*([\s\S]*?)\s*\$\$/g, (_m, eq) => `{% katex %}\n${eq.trim()}\n{% endkatex %}`);
    // 4) Inline $…$ → readable unicode (Dev.to has no reliable inline-math tag).
    devtoContent = devtoContent.replace(/\$([^$\n]+)\$/g, (_m, eq) =>
      eq.replace(/\\text\{([^}]*)\}/g, '$1').replace(/\\,/g, ' ').replace(/\^N\b/g, 'ᴺ').replace(/[{}]/g, '').trim()
    );

    // Transform content for Dev.to compatibility
    // Replace Loom iframe embeds with links (Dev.to doesn't support Loom iframes)
    devtoContent = devtoContent.replace(
      /<div[^>]*><iframe src="https:\/\/www\.loom\.com\/embed\/([^"]+)"[^>]*><\/iframe><\/div>/g,
      '**🎥 [Watch the video demo on Loom](https://www.loom.com/share/$1)**\n\n> _Note: Interactive video player available on the [original article]('+canonicalUrl+')_'
    );

    // Convert relative image paths to absolute URLs for Dev.to
    devtoContent = devtoContent.replace(
      /!\[([^\]]*)\]\(\/([^)]+)\)/g,
      `![$1](${siteUrl}/$2)`
    );

    // Convert relative link paths to absolute URLs for Dev.to
    devtoContent = devtoContent.replace(
      /(?<!!)\[([^\]]*)\]\(\/([^)]+)\)/g,
      `[$1](${siteUrl}/$2)`
    );

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

    if (process.env.DEVTO_DRY_RUN) {
      console.log('\n===== DRY RUN: transformed body_markdown =====\n');
      console.log(contentWithCTA);
      console.log('\n===== END DRY RUN =====');
      return;
    }

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
