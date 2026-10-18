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
  repoUrl: string;
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
];
