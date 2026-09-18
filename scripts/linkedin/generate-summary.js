import { GoogleGenerativeAI } from '@google/generative-ai';
import { buildSummaryPrompt } from './prompt.js';

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

  // El texto del prompt vive en prompt.js, que es tambien lo que mide el banco
  // de pruebas. Un prompt copiado en dos sitios deja de ser el mismo a la
  // segunda edicion, y entonces el experimento mide algo que no se despliega.
  const prompt = buildSummaryPrompt({ title, description, content, tags });

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
