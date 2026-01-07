import { readFileSync, existsSync } from 'fs';
import matter from 'gray-matter';

/**
 * Test: Detección de posts sin necesitar git diff
 * Valida que podemos leer y parsear posts del blog
 */
async function testDetectPosts() {
  console.log('🧪 Test: Detección y parseo de posts\n');

  try {
    // Test con un post existente
    const testPost = 'src/content/blog/en/claude-code-skills-blog-writer.md';

    console.log(`📝 Testing with: ${testPost}\n`);

    if (!existsSync(testPost)) {
      throw new Error(`Test post not found: ${testPost}`);
    }

    // Leer y parsear
    const content = readFileSync(testPost, 'utf-8');
    const { data: frontmatter, content: markdown } = matter(content);

    console.log('✅ Post parsed successfully\n');
    console.log('Frontmatter:');
    console.log(`  Title: ${frontmatter.title}`);
    console.log(`  Description: ${frontmatter.description?.substring(0, 80)}...`);
    console.log(`  Tags: ${frontmatter.tags?.join(', ')}`);
    console.log(`  Lang: ${frontmatter.lang}`);
    console.log(`  Translation Key: ${frontmatter.translationKey}`);
    console.log(`  LinkedIn Image: ${frontmatter.linkedinImage || 'None'}`);
    console.log(`\nMarkdown content length: ${markdown.length} characters`);

    // Extraer slug
    const slug = testPost.split('/').pop().replace('.md', '');
    const postUrl = `https://javieraguilar.ai/en/blog/${slug}`;
    console.log(`\nGenerated URL: ${postUrl}`);

    // Generar hashtags
    const hashtags = frontmatter.tags
      ?.map(tag => `#${tag.replace(/\s+/g, '')}`)
      .join(' ');
    console.log(`Hashtags: ${hashtags}`);

    console.log('\n✅ Test passed! Post detection and parsing works correctly.\n');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

testDetectPosts();
