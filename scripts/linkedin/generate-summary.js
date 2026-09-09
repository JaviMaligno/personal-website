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
  // MEDIDO 2026-09-09 (scripts/linkedin/experiments/): con el articulo entero
  // en el prompt, gemini-3.8-flash devuelve 503 UNAVAILABLE y 429
  // RESOURCE_EXHAUSTED en las tres pruebas, aunque responde 200 a una peticion
  // minima: la clave lo alcanza, el cupo no da para un articulo. 2.5-flash
  // fallo 3 de 6 veces. 3.5 y 3.6 respondieron 3/3, mas lentos (12-36 s) que
  // el preview (7-9 s). Revisar 3.8 cuando cambie el cupo.
  const models = [
    'gemini-3-flash-preview',  // Primary: el mas rapido que responde de forma fiable
    'gemini-3.5-flash',        // Fallback 1: estable, tambien en v1
    'gemini-3.6-flash',        // Fallback 2
  ];

  // El prompt anterior traia tres ganchos de EJEMPLO y el modelo los copiaba:
  // en la matriz del 2026-09-09, 12 de 12 aperturas eran una de las tres
  // familias ("X isn't Y, it's Z", "I spent N days...", "Most teams..."), con
  // cuatro modelos distintos. Tambien exigia una llamada a la accion, asi que
  // 7 de cada 12 posts acababan en pregunta, y llego a inventar historia
  // personal que el articulo no dice. Sin ejemplos y sin CTA: 0 de 10.
  const prompt = `You are writing a LinkedIn post for Javier Aguilar about an article he wrote. Write as him, first person.

ARTICLE
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

WHAT THE POST MUST DO
- Lead with the article's own subject and its most concrete finding. If the article is about mathematics, the post is about mathematics; if it is about a measurement, lead with the number.
- Carry at least two specifics from the article: a number, a name, a mechanism. Never a claim so general it would fit a different article.
- Keep the author's judgment exactly as the article states it. Do NOT invent personal history, effort, conversions or opinions — no "I used to think", no "this proved me wrong", no "I spent three weeks". If the article does not say it, he did not say it.
- Assume a reader who knows the field. Do not address CTOs, leaders or "those of us building X" as a group.

WHAT THE POST MUST NOT DO
- No opening formula. Never start with "The hardest part of X isn't Y, it's Z", "Most teams...", "I spent N days..." or any variant of them.
- No closing question, no call to action, no "what's your experience", no "how are you thinking about".
- No hashtags and no URL (both are appended afterwards). No markdown, no emojis.

LENGTH
Two or three short paragraphs, under 300 words. End on a statement.`;

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
