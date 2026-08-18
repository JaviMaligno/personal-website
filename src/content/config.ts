import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    heroImage: z.string().optional(),
    tags: z.array(z.string()).default([]),
    lang: z.enum(['en', 'es']),
    // For linking translations
    translationKey: z.string(),
    // For LinkedIn automation (optional)
    linkedinImage: z.string().optional(),
    // Optional link to a code repo; appended to the LinkedIn post when present
    repoUrl: z.string().optional(),
    // Optional extra links (product page, preprint, …); each rendered as a
    // "🔗 <label>: <url>" line in the auto-generated LinkedIn post
    linkedinLinks: z
      .array(z.object({ label: z.string().optional(), url: z.string() }))
      .optional(),
    // Hand-written LinkedIn body. When present it is used verbatim and Gemini is
    // not called, so the post reads exactly as written instead of as a summary of
    // the article. The links, "💻 Code" line and hashtags are still appended by
    // buildPostText, so write only the body here.
    linkedinSummary: z.string().optional(),
  }),
});

export const collections = { blog };
