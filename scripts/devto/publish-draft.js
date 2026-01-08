import { readFileSync } from 'fs';

/**
 * Publish an existing Dev.to draft article
 * Usage: node scripts/devto/publish-draft.js <article-id>
 * Example: node scripts/devto/publish-draft.js 3158782
 */
async function publishDraft() {
  try {
    // Get article ID from command line
    const articleId = process.argv[2];

    if (!articleId) {
      console.log(`
📝 Publish Dev.to Draft

Usage: node scripts/devto/publish-draft.js <article-id>

Example:
  node scripts/devto/publish-draft.js 3158782

Note: Make sure DEVTO_API_KEY environment variable is set.
      `);
      process.exit(1);
    }

    console.log(`📝 Publishing Dev.to draft ${articleId}...`);

    // Validate environment variables
    const apiKey = process.env.DEVTO_API_KEY;

    if (!apiKey) {
      throw new Error('DEVTO_API_KEY environment variable is required');
    }

    // Update article to published
    const article = {
      published: true
    };

    console.log(`\n🚀 Publishing article ${articleId}...`);

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

    console.log(`\n✅ Successfully published!`);
    console.log(`📍 Dev.to URL: ${result.url}`);
    console.log(`🆔 Article ID: ${result.id}`);
    console.log(`📊 Status: ${result.published ? 'PUBLISHED ✨' : 'Draft'}`);
    console.log(`📅 Published at: ${result.published_timestamp}`);

  } catch (error) {
    console.error('\n❌ Error publishing draft:', error.message);
    process.exit(1);
  }
}

publishDraft();
