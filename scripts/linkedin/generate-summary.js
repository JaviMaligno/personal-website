import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

/**
 * Generate LinkedIn-optimized summary using Gemini API
 * Strategy: Try Flash 2.0 first, fallback to 2.5 Flash
 *
 * @param {Object} params - Post parameters
 * @param {string} params.title - Blog post title
 * @param {string} params.description - Blog post description
 * @param {string} params.content - Full blog post content (markdown)
 * @param {string[]} params.tags - Blog post tags
 * @returns {Promise<string>} - LinkedIn-optimized summary
 */
export async function generateSummary({ title, description, content, tags }) {
  const models = [
    'gemini-3-flash-preview',  // Primary: Gemini 3.0 Flash (latest, Jan 2026)
    'gemini-2.5-flash',        // Fallback: Gemini 2.5 Flash
  ];

  const prompt = `You are a LinkedIn content strategist creating engaging posts for AI/tech professionals and CTOs.

BLOG DETAILS:
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

REQUIREMENTS:
- Write 2-3 concise paragraphs (max 400 words)
- Start with a compelling hook that grabs attention (problem, insight, or question)
- Focus on the "why" and key takeaways, not just implementation details
- Speak to technical leaders: CTOs, engineering leads, AI architects
- Use professional but conversational tone
- Include a subtle call-to-action at the end (e.g., "What's your experience with...", "How are you handling...")
- Write in first person (I/my/me) as Javier Aguilar, AI Agent Architect
- DO NOT include hashtags (will be added separately)
- DO NOT include the blog URL (will be added separately)
- DO NOT use emojis (except sparingly if they enhance meaning)

OUTPUT FORMAT:
Plain text only, no markdown formatting.

Example opening hooks:
- "I spent 3 weeks debugging LinkedIn's API before realizing..."
- "Most teams waste hours on manual deployments. Here's why..."
- "The hardest part of AI automation isn't the code—it's..."`;

  for (const modelName of models) {
    try {
      console.log(`🤖 Attempting summary generation with ${modelName}...`);

      const model = genAI.getGenerativeModel({ model: modelName });
      const result = await model.generateContent(prompt);
      const summary = result.response.text().trim();

      if (!summary || summary.length < 50) {
        throw new Error('Generated summary too short');
      }

      console.log(`✅ Summary generated with ${modelName}`);
      console.log(`   Length: ${summary.length} characters`);
      console.log(`   Words: ~${summary.split(/\s+/).length} words`);

      return summary;

    } catch (error) {
      console.warn(`⚠️  ${modelName} failed: ${error.message}`);

      // If last model, throw error
      if (modelName === models[models.length - 1]) {
        throw new Error(`All Gemini models failed to generate summary. Last error: ${error.message}`);
      }

      // Otherwise, continue to next model
      console.log(`Trying fallback model...`);
    }
  }
}
