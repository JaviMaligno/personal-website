import { GoogleGenerativeAI } from '@google/generative-ai';
import { buildSummaryPrompt } from './prompt.js';
import { generateWithFallback } from './summary-fallback.js';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Ultimo recurso, de otra familia: si Gemini entero esta saturado, otro modelo
// de Gemini no ayuda. Sin OPENROUTER_API_KEY simplemente no se intenta.
const OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || 'anthropic/claude-sonnet-5.5';

async function callOpenRouter(prompt) {
  const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
      'Content-Type': 'application/json',
      'X-Title': 'personal-website LinkedIn summary',
    },
    body: JSON.stringify({
      model: OPENROUTER_MODEL,
      messages: [{ role: 'user', content: prompt }],
    }),
  });
  if (!res.ok) {
    throw new Error(`[${res.status}] ${(await res.text()).slice(0, 300)}`);
  }
  const data = await res.json();
  return data.choices?.[0]?.message?.content ?? '';
}

/**
 * Generate LinkedIn-optimized summary: Gemini with retries, then OpenRouter.
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

  return generateWithFallback({
    models,
    callModel: async (modelName) => {
      const model = genAI.getGenerativeModel({ model: modelName });
      const result = await model.generateContent(prompt);
      return result.response.text();
    },
    lastResort: process.env.OPENROUTER_API_KEY?.trim()
      ? { name: `openrouter:${OPENROUTER_MODEL}`, call: () => callOpenRouter(prompt) }
      : undefined,
  });
}
