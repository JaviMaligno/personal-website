// src/data/plugins.ts
// Claude Code plugins: several skills shipped together, shown above the
// single-skill collection on /skills.

export interface PluginVideo {
  slug: string;            // file stem under /videos/plugins/ (.mp4 + .jpg poster)
  translationKey: string;  // blog translationKey; the article link only shows once it is published
  title: string;           // article title, kept in English like the video itself
  duration: string;
}

export interface Plugin {
  slug: string;
  key: string;             // i18n key under `skills.plugins.<key>`
  repoUrl: string | null;  // null for private repos
  projectSlug?: string;    // case study under /projects/ to link instead
  pipeline?: string[];     // phase skills, drawn as a stepper when there are no videos
  skills: string[];        // skill folder names inside the plugin
  tags: string[];
  videos: PluginVideo[];   // first one plays by default
}

export const plugins: Plugin[] = [
  {
    slug: 'agilabs-video-studio',
    key: 'videoStudio',
    repoUrl: 'https://github.com/JaviMaligno/agilabs-video-studio',
    skills: ['article-video', 'explainer-script', 'explainer-animation', 'narration'],
    tags: ['Remotion', 'Cartesia TTS', 'Claude Code plugin'],
    videos: [
      { slug: 'wheres-the-ball', translationKey: 'wheres-the-ball', title: "Where's the Ball?", duration: '52 s' },
      { slug: 'sport-from-motion', translationKey: 'sport-from-motion', title: 'Sport from motion', duration: '60 s' },
      { slug: 'nobody-tells-the-implementer-why', translationKey: 'nobody-tells-the-implementer-why', title: 'Nobody tells the implementer why', duration: '60 s' },
      { slug: 'that-was-for-another-chat', translationKey: 'that-was-for-another-chat', title: 'That was for another chat', duration: '59 s' },
    ],
  },
  {
    slug: 'data-source-automator',
    key: 'dataSourceAutomator',
    repoUrl: null,
    projectSlug: 'data-source-automator',
    pipeline: ['research', 'requirements', 'contract', 'implement', 'verify', 'publish'],
    skills: ['new-source', 'intake', 'benchmark', 'retro'],
    tags: ['Claude Code plugin', 'Multi-agent', 'Playwright', 'HITL'],
    videos: [],
  },
  {
    slug: 'delivery-loop',
    key: 'deliveryLoop',
    repoUrl: 'https://github.com/JaviMaligno/delivery-loop',
    pipeline: ['0 · start', '1–3 · spec, gaps, plan', '4–6 · implement, review, integrate', '7 · live verification', '8–9 · promote, close'],
    skills: ['deliver', 'census', 'spec', 'qa-design', 'qa-execution'],
    tags: ['Claude Code plugin', 'Spec-driven', 'QA', 'MIT'],
    videos: [],
  },
];
