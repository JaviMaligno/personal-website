// src/data/skills.ts
export type SkillCategory = 'content' | 'devWorkflow' | 'qa' | 'governance' | 'ops' | 'productivity';

export interface Skill {
  slug: string;            // stable id
  key: string;             // i18n key under `skills.<key>`
  category: SkillCategory;
  visibility: 'public' | 'internal';
  repoUrl: string | null;  // public → deep-link to repo subdir; internal → null
  tags: string[];
  featured?: boolean;      // shown in the home teaser
}

const REPO = 'https://github.com/JaviMaligno/agilabs-skills/tree/main';

export const skillCategoryOrder: SkillCategory[] = ['content', 'devWorkflow', 'qa', 'governance', 'ops', 'productivity'];

export const skills: Skill[] = [
  // Content & media
  { slug: 'demo-video',    key: 'demoVideo',    category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/demo-video`,    tags: ['Chrome CDP', 'Google TTS', 'ffmpeg'], featured: true },
  { slug: 'blog-writer',   key: 'blogWriter',   category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/blog-writer`,   tags: ['Astro', 'i18n', 'Content'] },
  { slug: 'spotify-upload',key: 'spotifyUpload',category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/spotify-upload`,tags: ['Browser automation', 'Podcast'] },
  { slug: 'tailor-cv',     key: 'tailorCv',     category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/tailor-cv`,     tags: ['DOCX', 'PDF', 'Job search'] },
  // Dev workflow
  { slug: 'feature-dev',   key: 'featureDev',   category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/feature-dev`, tags: ['Architecture', 'GitHub', 'PRs'], featured: true },
  { slug: 'code-review',   key: 'codeReview',   category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/code-review`, tags: ['Diffs', 'Security', 'Quality'] },
  { slug: 'commit-pr',     key: 'commitPr',     category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/commit-pr`,   tags: ['Git', 'gh CLI'] },
  { slug: 'deploy',        key: 'deploy',       category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/release-tag`, tags: ['Semver', 'CI/CD', 'Release'] },
  { slug: 'microservice-lifecycle', key: 'microserviceLifecycle', category: 'devWorkflow', visibility: 'public', repoUrl: `${REPO}/dev-workflow/microservice-scaffold`, tags: ['Scaffolding', 'Kubernetes', 'Testing'] },
  { slug: 'spec-driven-development', key: 'specDrivenDevelopment', category: 'devWorkflow', visibility: 'public', repoUrl: `${REPO}/dev-workflow/spec-driven-development`, tags: ['Specs', 'Traceability', 'Planning'] },
  { slug: 'codegen-validation-loop', key: 'codegenValidationLoop', category: 'devWorkflow', visibility: 'public', repoUrl: `${REPO}/dev-workflow/codegen-validation-loop`, tags: ['Codegen', 'Validation', 'Agents'] },
  // QA & testing
  { slug: 'verify-test',   key: 'verifyTest',   category: 'qa', visibility: 'public',   repoUrl: `${REPO}/qa-testing/deployment-verification`, tags: ['E2E', 'Infra', 'UI'] },
  { slug: 'verify-env',    key: 'verifyEnv',    category: 'qa', visibility: 'public',   repoUrl: `${REPO}/qa-testing/authenticated-api-probe`, tags: ['API', 'Auth', 'Diagnostics'] },
  { slug: 'playwright-cli',key: 'playwrightCli',category: 'qa', visibility: 'public',   repoUrl: `${REPO}/qa-testing/playwright-cli`, tags: ['Playwright', 'Scraping', 'Testing'] },
  { slug: 'e2e-testing',   key: 'e2eTesting',   category: 'qa', visibility: 'internal', repoUrl: null, tags: ['Playwright', 'E2E', 'UI'] },
  { slug: 'qa-design',     key: 'qaDesign',     category: 'qa', visibility: 'public',   repoUrl: `${REPO}/qa-testing/qa-design`, tags: ['QA', 'Test plan', 'Coverage'] },
  { slug: 'qa-execution',  key: 'qaExecution',  category: 'qa', visibility: 'public',   repoUrl: `${REPO}/qa-testing/qa-execution`, tags: ['QA', 'Evidence', 'Bug hunt'] },
  // Governance
  { slug: 'responsible-ai-audit', key: 'responsibleAiAudit', category: 'governance', visibility: 'public', repoUrl: `${REPO}/governance/responsible-ai-audit`, tags: ['Compliance', 'Multi-agent', 'Governance'], featured: true },
  // Ops
  { slug: 'render-development', key: 'renderDevelopment', category: 'ops', visibility: 'public', repoUrl: `${REPO}/ops/render-development`, tags: ['Render', 'Postgres', 'Deploy'] },
  // Productivity
  { slug: 'email-cleanup', key: 'emailCleanup', category: 'productivity', visibility: 'public', repoUrl: `${REPO}/productivity/email-cleanup`, tags: ['Gmail', 'Automation', 'Triage'] },
];

export function getSkillsByCategory(): { category: SkillCategory; skills: Skill[] }[] {
  return skillCategoryOrder.map((category) => ({
    category,
    skills: skills.filter((s) => s.category === category),
  }));
}

export function getFeaturedSkills(): Skill[] {
  return skills.filter((s) => s.featured);
}
