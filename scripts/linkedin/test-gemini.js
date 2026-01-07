import { readFileSync } from 'fs';
import matter from 'gray-matter';
import { generateSummary } from './generate-summary.js';

/**
 * Test: Generación real con Gemini API
 * Requiere: export GEMINI_API_KEY=your_key
 *
 * Usa Gemini 3.0 Flash (fallback a 2.5 Flash)
 */
async function testGeminiAPI() {
  console.log('🧪 Test: Generación de resumen con Gemini API\n');

  if (!process.env.GEMINI_API_KEY) {
    console.error('❌ Error: GEMINI_API_KEY not set');
    console.error('\nUsage:');
    console.error('  export GEMINI_API_KEY=your_api_key');
    console.error('  node scripts/linkedin/test-gemini.js');
    process.exit(1);
  }

  try {
    // Leer un post existente
    const testPost = 'src/content/blog/en/claude-code-skills-blog-writer.md';
    console.log(`📝 Testing with: ${testPost}\n`);

    const content = readFileSync(testPost, 'utf-8');
    const { data: frontmatter, content: markdown } = matter(content);

    console.log('🤖 Calling Gemini API...\n');

    const summary = await generateSummary({
      title: frontmatter.title,
      description: frontmatter.description,
      content: markdown,
      tags: frontmatter.tags || [],
    });

    console.log('\n✅ Summary generated successfully!\n');
    console.log('─'.repeat(60));
    console.log(summary);
    console.log('─'.repeat(60));
    console.log(`\nSummary stats:`);
    console.log(`  Characters: ${summary.length}`);
    console.log(`  Words: ~${summary.split(/\s+/).length}`);

    // Construir post completo
    const hashtags = frontmatter.tags
      .map(tag => `#${tag.replace(/\s+/g, '')}`)
      .join(' ');
    const postUrl = 'https://javieraguilar.ai/en/blog/claude-code-skills-blog-writer';
    const fullPost = `${summary}\n\n📖 Read more: ${postUrl}\n\n${hashtags}`;

    console.log(`\n📱 Full LinkedIn post:\n`);
    console.log('─'.repeat(60));
    console.log(fullPost);
    console.log('─'.repeat(60));
    console.log(`\nTotal length: ${fullPost.length} characters (max: 3000)`);

    if (fullPost.length > 3000) {
      console.warn('\n⚠️  Post exceeds 3000 chars, would be truncated');
    } else {
      console.log('\n✅ Post within LinkedIn character limit');
    }

    console.log('\n✅ Gemini API test passed!\n');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('\nFull error:', error);
    process.exit(1);
  }
}

testGeminiAPI();
