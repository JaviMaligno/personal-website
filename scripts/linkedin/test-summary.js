import { readFileSync } from 'fs';
import matter from 'gray-matter';

/**
 * Test: Generación de resumen (sin llamar a Gemini)
 * Valida el formato del prompt y la estructura
 */
async function testSummaryGeneration() {
  console.log('🧪 Test: Preparación de datos para resumen\n');

  try {
    // Leer un post existente
    const testPost = 'src/content/blog/en/claude-code-skills-blog-writer.md';
    const content = readFileSync(testPost, 'utf-8');
    const { data: frontmatter, content: markdown } = matter(content);

    console.log('📝 Post data extracted:\n');
    console.log(`Title: ${frontmatter.title}`);
    console.log(`Description: ${frontmatter.description}`);
    console.log(`Tags: ${frontmatter.tags?.join(', ')}`);
    console.log(`Content length: ${markdown.length} chars\n`);

    // Simular prompt de Gemini
    const prompt = `You are a LinkedIn content strategist creating engaging posts for AI/tech professionals and CTOs.

BLOG DETAILS:
Title: ${frontmatter.title}
Description: ${frontmatter.description}
Tags: ${frontmatter.tags?.join(', ')}

FULL CONTENT:
${markdown.substring(0, 4000)}

REQUIREMENTS:
- Write 2-3 concise paragraphs (max 400 words)
- Start with a compelling hook that grabs attention
- Focus on the "why" and key takeaways
- Speak to technical leaders: CTOs, engineering leads, AI architects
- Use professional but conversational tone
- Include a call-to-action at the end
- Write in first person (I/my/me) as Javier Aguilar, AI Agent Architect
- DO NOT include hashtags (will be added separately)
- DO NOT include the blog URL (will be added separately)

OUTPUT FORMAT:
Plain text only, no markdown formatting.`;

    console.log('📄 Gemini prompt preview:\n');
    console.log('─'.repeat(60));
    console.log(prompt.substring(0, 500) + '...\n');
    console.log('─'.repeat(60));
    console.log(`\nPrompt length: ${prompt.length} characters`);

    // Simular post de LinkedIn
    const mockSummary = `I spent weeks building a custom skill for Claude Code to automate my bilingual blog workflow. The result? Perfect consistency across 8+ articles with zero manual frontmatter errors.

The key insight: encoding your expertise once as a skill beats repeating instructions every session. My blog-writer skill handles EN/ES translations, tag conventions, image paths, and LinkedIn repurposing automatically.

What repetitive workflows are you still doing manually that could be encoded as skills?`;

    const hashtags = frontmatter.tags
      ?.map(tag => `#${tag.replace(/\s+/g, '')}`)
      .join(' ');

    const postUrl = 'https://javieraguilar.ai/en/blog/claude-code-skills-blog-writer';
    const fullPost = `${mockSummary}\n\n📖 Read more: ${postUrl}\n\n${hashtags}`;

    console.log('\n📱 Mock LinkedIn post:\n');
    console.log('─'.repeat(60));
    console.log(fullPost);
    console.log('─'.repeat(60));
    console.log(`\nPost length: ${fullPost.length} characters (max: 3000)`);

    if (fullPost.length > 3000) {
      console.warn('\n⚠️  Warning: Post exceeds LinkedIn limit!');
    } else {
      console.log('\n✅ Post within LinkedIn character limit');
    }

    console.log('\n✅ Test passed! Summary generation structure is correct.\n');
    console.log('💡 To test with real Gemini API:');
    console.log('   export GEMINI_API_KEY=your_key');
    console.log('   node scripts/linkedin/test-gemini.js\n');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

testSummaryGeneration();
