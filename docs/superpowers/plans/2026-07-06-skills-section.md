# Skills Section + Public Skills Repo v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Skills" section to javieraguilar.ai (above the MCP content) showcasing 14 authored skills grouped by capability, and publish a `agilabs-skills` public repo v1 with the 8 fully-generic skills.

**Architecture:** Mirror the existing `Projects` pattern exactly — a `src/data/skills.ts` data layer (TS array + interface, like `projects.ts`), i18n strings in `en.json`/`es.json`, and a `Skills.astro` section component grouped by category, inserted between `<Services />` and `<Projects />` on both locale home pages. Public cards deep-link to the new repo; internal cards are anonymized, non-linking capability cards.

**Tech Stack:** Astro 5, TypeScript, JSON i18n, `gh` CLI (repo), git.

## Global Constraints

- Verification model = `npm run build` (type-checks) + real-browser visual check on **both** `/en/` and `/es/` (project convention: always verify visual changes in browser before pushing). No src/ unit tests — the codebase does not unit-test `src/`.
- Bilingual: every user-facing string exists in both `en.json` and `es.json`.
- Internal skills: describe the *capability/pattern* only. Never write "SDS", "LOCO", "Simple KYC", "Verify" (product), "RFP", client names, internal URLs, or Confluence/Bitbucket IDs in site copy.
- Public repo publishing is outward-facing and hard to reverse — the mandatory safety scan (Task 5) gates the push.
- Do NOT merge to `main` directly (merge = production deploy). Finish with a PR.
- Work happens on branch `feat/skills-section` (already created).
- Repo: name `agilabs-skills`, owner `JaviMaligno`, public, MIT license.

---

### Task 1: Data layer — `src/data/skills.ts`

**Files:**
- Create: `src/data/skills.ts`

**Interfaces:**
- Produces: `interface Skill`, `const skills: Skill[]`, `type SkillCategory`, `const skillCategoryOrder`, `function getSkillsByCategory(): { category: SkillCategory; skills: Skill[] }[]`.

- [ ] **Step 1: Create the data file**

```ts
// src/data/skills.ts
export type SkillCategory = 'content' | 'devWorkflow' | 'qa' | 'governance';

export interface Skill {
  slug: string;            // stable id
  key: string;             // i18n key under `skills.<key>`
  category: SkillCategory;
  visibility: 'public' | 'internal';
  repoUrl: string | null;  // public → deep-link to repo subdir; internal → null
  tags: string[];
}

const REPO = 'https://github.com/JaviMaligno/agilabs-skills/tree/main';

export const skillCategoryOrder: SkillCategory[] = ['content', 'devWorkflow', 'qa', 'governance'];

export const skills: Skill[] = [
  // Content & media
  { slug: 'demo-video',    key: 'demoVideo',    category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/demo-video`,    tags: ['Chrome CDP', 'Google TTS', 'ffmpeg'] },
  { slug: 'blog-writer',   key: 'blogWriter',   category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/blog-writer`,   tags: ['Astro', 'i18n', 'Content'] },
  { slug: 'spotify-upload',key: 'spotifyUpload',category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/spotify-upload`,tags: ['Browser automation', 'Podcast'] },
  { slug: 'tailor-cv',     key: 'tailorCv',     category: 'content', visibility: 'public',   repoUrl: `${REPO}/content-media/tailor-cv`,     tags: ['DOCX', 'PDF', 'Job search'] },
  // Dev workflow
  { slug: 'feature-dev',   key: 'featureDev',   category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/feature-dev`, tags: ['Architecture', 'GitHub', 'PRs'] },
  { slug: 'code-review',   key: 'codeReview',   category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/code-review`, tags: ['Diffs', 'Security', 'Quality'] },
  { slug: 'commit-pr',     key: 'commitPr',     category: 'devWorkflow', visibility: 'public',   repoUrl: `${REPO}/dev-workflow/commit-pr`,   tags: ['Git', 'gh CLI'] },
  { slug: 'deploy',        key: 'deploy',       category: 'devWorkflow', visibility: 'internal', repoUrl: null, tags: ['Semver', 'CI/CD', 'Release'] },
  { slug: 'microservice-lifecycle', key: 'microserviceLifecycle', category: 'devWorkflow', visibility: 'internal', repoUrl: null, tags: ['Scaffolding', 'Kubernetes', 'Testing'] },
  // QA & testing
  { slug: 'verify-test',   key: 'verifyTest',   category: 'qa', visibility: 'internal', repoUrl: null, tags: ['E2E', 'Infra', 'UI'] },
  { slug: 'verify-env',    key: 'verifyEnv',    category: 'qa', visibility: 'internal', repoUrl: null, tags: ['API', 'Auth', 'Diagnostics'] },
  { slug: 'playwright-cli',key: 'playwrightCli',category: 'qa', visibility: 'public',   repoUrl: `${REPO}/qa-testing/playwright-cli`, tags: ['Playwright', 'Scraping', 'Testing'] },
  { slug: 'e2e-testing',   key: 'e2eTesting',   category: 'qa', visibility: 'internal', repoUrl: null, tags: ['Playwright', 'E2E', 'UI'] },
  // Governance
  { slug: 'responsible-ai-audit', key: 'responsibleAiAudit', category: 'governance', visibility: 'internal', repoUrl: null, tags: ['Compliance', 'Multi-agent', 'Governance'] },
];

export function getSkillsByCategory(): { category: SkillCategory; skills: Skill[] }[] {
  return skillCategoryOrder.map((category) => ({
    category,
    skills: skills.filter((s) => s.category === category),
  }));
}
```

- [ ] **Step 2: Type-check via build**

Run: `npm run build`
Expected: build completes with no TypeScript errors (section not yet rendered — that's fine).

- [ ] **Step 3: Commit**

```bash
git add src/data/skills.ts
git commit -m "feat(skills): add skills data layer"
```

---

### Task 2: i18n strings — `en.json` + `es.json`

**Files:**
- Modify: `src/i18n/en.json` (add top-level `skills` key)
- Modify: `src/i18n/es.json` (add top-level `skills` key)

**Interfaces:**
- Produces: `t('skills')` returning `{ section, categories, badges, <key>… }`. Every `Skill.key` from Task 1 has a `{ title, description }` entry in BOTH files.

- [ ] **Step 1: Add the `skills` block to `en.json`**

Insert as a new top-level key (sibling of `projects`):

```json
"skills": {
  "section": {
    "title": "Skills",
    "subtitle": "Reusable agent workflows I package as Claude skills — the layer I reach for before MCP.",
    "ctaLabel": "View all on GitHub →"
  },
  "categories": {
    "content": "Content & media",
    "devWorkflow": "Dev workflow",
    "qa": "QA & testing",
    "governance": "Governance"
  },
  "badges": { "public": "Public", "internal": "Internal" },
  "demoVideo": { "title": "Demo Video", "description": "Records narrated product-demo and verification videos of any web app by driving a real browser and assembling beat-narrated MP4s." },
  "blogWriter": { "title": "Blog Writer", "description": "Writes bilingual (EN/ES) blog articles end-to-end: structure, frontmatter and translations." },
  "spotifyUpload": { "title": "Podcast Publisher", "description": "Uploads and publishes podcast episodes to Spotify for Creators via browser automation." },
  "tailorCv": { "title": "CV Tailor", "description": "Adapts a CV and drafts a tailored cover letter for a specific role, exporting to Markdown, DOCX and PDF." },
  "featureDev": { "title": "Feature Dev", "description": "Guides new-feature development: architecture planning, implementation and PR creation." },
  "codeReview": { "title": "Code Review", "description": "Reviews diffs and PRs for correctness, security and performance, with actionable suggestions." },
  "commitPr": { "title": "Commit & PR", "description": "Creates well-structured commits and pull requests with clear messages and branch handling." },
  "deploy": { "title": "Service Deploy", "description": "Tags and deploys a service end-to-end: semver bump, release tag and config-repo update to trigger rollout." },
  "microserviceLifecycle": { "title": "Microservice Lifecycle", "description": "Full microservice lifecycle from a spec: scaffolding, implementation, testing and deployment, plus targeted bug-fix cycles against ground truth." },
  "verifyTest": { "title": "Service Verification", "description": "Validates a deployed microservice end-to-end, from infrastructure checks to UI testing and failure troubleshooting." },
  "verifyEnv": { "title": "Environment Probe", "description": "Connects to a running environment, authenticates via session and API token, and answers live queries about the deployed build." },
  "playwrightCli": { "title": "Playwright CLI", "description": "Automates browser interactions for testing, form filling, screenshots and data extraction." },
  "e2eTesting": { "title": "E2E UI Testing", "description": "Drives end-to-end UI test suites with Playwright, debugging visual issues across flows." },
  "responsibleAiAudit": { "title": "Responsible-AI Audit", "description": "Audits a repository against a Responsible-AI checklist, spawning parallel agents to close code-actionable gaps and tracking compliance." }
}
```

- [ ] **Step 2: Add the `skills` block to `es.json`** (same keys, Spanish copy)

```json
"skills": {
  "section": {
    "title": "Skills",
    "subtitle": "Workflows de agente reutilizables que empaqueto como skills de Claude — la capa a la que recurro antes que a los MCP.",
    "ctaLabel": "Ver todas en GitHub →"
  },
  "categories": {
    "content": "Contenido y media",
    "devWorkflow": "Flujo de desarrollo",
    "qa": "QA y testing",
    "governance": "Gobernanza"
  },
  "badges": { "public": "Pública", "internal": "Interna" },
  "demoVideo": { "title": "Demo Video", "description": "Graba vídeos demo y de verificación narrados de cualquier web, controlando un navegador real y montando MP4s narrados por escenas." },
  "blogWriter": { "title": "Blog Writer", "description": "Escribe artículos de blog bilingües (EN/ES) de principio a fin: estructura, frontmatter y traducciones." },
  "spotifyUpload": { "title": "Publicador de Podcast", "description": "Sube y publica episodios de podcast en Spotify for Creators mediante automatización de navegador." },
  "tailorCv": { "title": "Adaptador de CV", "description": "Adapta un CV y redacta una carta de presentación a medida para un puesto concreto, exportando a Markdown, DOCX y PDF." },
  "featureDev": { "title": "Desarrollo de Features", "description": "Guía el desarrollo de nuevas features: planificación de arquitectura, implementación y creación de PRs." },
  "codeReview": { "title": "Code Review", "description": "Revisa diffs y PRs en busca de correctitud, seguridad y rendimiento, con sugerencias accionables." },
  "commitPr": { "title": "Commit y PR", "description": "Crea commits y pull requests bien estructurados, con mensajes claros y gestión de ramas." },
  "deploy": { "title": "Despliegue de Servicios", "description": "Etiqueta y despliega un servicio de punta a punta: incremento semver, tag de release y actualización del repo de configuración para disparar el rollout." },
  "microserviceLifecycle": { "title": "Ciclo de Vida de Microservicios", "description": "Ciclo de vida completo de microservicios a partir de una especificación: scaffolding, implementación, testing y despliegue, más ciclos de corrección de bugs contra la verdad de referencia." },
  "verifyTest": { "title": "Verificación de Servicios", "description": "Valida un microservicio desplegado de punta a punta, desde chequeos de infraestructura hasta testing de UI y diagnóstico de fallos." },
  "verifyEnv": { "title": "Sonda de Entorno", "description": "Se conecta a un entorno en marcha, se autentica vía sesión y token de API, y responde consultas en vivo sobre el build desplegado." },
  "playwrightCli": { "title": "Playwright CLI", "description": "Automatiza interacciones de navegador para testing, rellenado de formularios, capturas y extracción de datos." },
  "e2eTesting": { "title": "Testing E2E de UI", "description": "Ejecuta suites de tests E2E de UI con Playwright, depurando problemas visuales a lo largo de los flujos." },
  "responsibleAiAudit": { "title": "Auditoría de IA Responsable", "description": "Audita un repositorio contra un checklist de IA Responsable, lanzando agentes en paralelo para cerrar brechas accionables en código y llevando el seguimiento de cumplimiento." }
}
```

- [ ] **Step 3: Verify JSON validity + key parity**

Run: `node -e "const en=require('./src/i18n/en.json'), es=require('./src/i18n/es.json'); const ke=Object.keys(en.skills).sort(), ks=Object.keys(es.skills).sort(); if(JSON.stringify(ke)!==JSON.stringify(ks)) throw new Error('key mismatch'); console.log('skills keys OK:', ke.length)"`
Expected: `skills keys OK: 17` (section, categories, badges + 14 skills).

- [ ] **Step 4: Commit**

```bash
git add src/i18n/en.json src/i18n/es.json
git commit -m "feat(skills): add EN/ES i18n strings for skills section"
```

---

### Task 3: `Skills.astro` component

**Files:**
- Create: `src/components/Skills.astro`

**Interfaces:**
- Consumes: `getSkillsByCategory`, `Skill` (Task 1); `t('skills')` (Task 2); `getLangFromUrl`, `useTranslations`, `type Language` (`src/i18n`).

- [ ] **Step 1: Create the component**

```astro
---
import { getLangFromUrl, useTranslations, type Language } from '../i18n';
import { getSkillsByCategory } from '../data/skills';

const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
const s = t('skills');
const groups = getSkillsByCategory();
const repoRoot = 'https://github.com/JaviMaligno/agilabs-skills';
---

<section id="skills" class="skills">
  <div class="container">
    <div class="section-header">
      <h2>{s.section.title}</h2>
      <p>{s.section.subtitle}</p>
    </div>

    {groups.map((group) => (
      <div class="skill-group">
        <h3 class="group-title">{s.categories[group.category]}</h3>
        <div class="grid grid-3">
          {group.skills.map((skill) => {
            const badge = skill.visibility === 'public' ? s.badges.public : s.badges.internal;
            const body = (
              <>
                <div class="skill-header">
                  <span class="visibility-badge" data-visibility={skill.visibility}>{badge}</span>
                </div>
                <h4>{s[skill.key].title}</h4>
                <p>{s[skill.key].description}</p>
                <div class="tags">
                  {skill.tags.map((tag) => <span class="tag">{tag}</span>)}
                </div>
              </>
            );
            return skill.visibility === 'public' && skill.repoUrl ? (
              <a class="card skill-card is-link" href={skill.repoUrl} target="_blank" rel="noopener">{body}</a>
            ) : (
              <div class="card skill-card">{body}</div>
            );
          })}
        </div>
      </div>
    ))}

    <div class="view-all">
      <a href={repoRoot} target="_blank" rel="noopener" class="view-all-link">{s.section.ctaLabel}</a>
    </div>
  </div>
</section>

<style>
  .skill-group { margin-top: var(--space-xl); }
  .group-title {
    font-size: 1.125rem;
    color: var(--text-secondary, var(--text-muted));
    margin-bottom: var(--space-md);
    padding-bottom: var(--space-sm);
    border-bottom: 1px solid var(--glass-border);
  }
  .skill-card { display: flex; flex-direction: column; text-decoration: none; color: inherit; }
  .skill-card.is-link { transition: transform 0.2s ease, border-color 0.2s ease; }
  .skill-card.is-link:hover { transform: translateY(-2px); border-color: var(--primary); }
  .skill-header { margin-bottom: var(--space-sm); }
  .visibility-badge {
    display: inline-block;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.25rem 0.625rem;
    border-radius: var(--radius-full);
    background: var(--glass);
    border: 1px solid var(--glass-border);
    color: var(--text-muted);
  }
  .visibility-badge[data-visibility="public"] {
    background: rgba(34, 197, 94, 0.15);
    border-color: rgba(34, 197, 94, 0.3);
    color: #4ade80;
  }
  .visibility-badge[data-visibility="internal"] {
    background: rgba(148, 163, 184, 0.15);
    border-color: rgba(148, 163, 184, 0.3);
    color: #94a3b8;
  }
  .skill-card h4 { margin-bottom: var(--space-sm); color: var(--text-primary); }
  .skill-card p { flex-grow: 1; font-size: 0.9375rem; }
  .view-all { text-align: center; margin-top: var(--space-xl); }
  .view-all-link { color: var(--text-muted); font-size: 0.9375rem; text-decoration: none; transition: color 0.2s ease; }
  .view-all-link:hover { color: var(--primary); }
</style>
```

> Note: if `npm run build` complains about indexing `s[skill.key]` types, add `const sk = s as any;` in the frontmatter and use `sk[skill.key]`. Match whatever `Projects.astro` gets away with first; only fall back to `as any` if the build fails.

- [ ] **Step 2: Type-check via build**

Run: `npm run build`
Expected: build completes, no errors. (Component compiles even though not yet mounted.)

- [ ] **Step 3: Commit**

```bash
git add src/components/Skills.astro
git commit -m "feat(skills): add Skills section component"
```

---

### Task 4: Mount the section on both home pages

**Files:**
- Modify: `src/pages/en/index.astro`
- Modify: `src/pages/es/index.astro`

- [ ] **Step 1: Import + mount in `en/index.astro`**

Add the import next to the others:
```astro
import Skills from '../../components/Skills.astro';
```
Insert between `<Services />` and `<Projects />`:
```astro
  <Services />
  <Skills />
  <Projects />
```

- [ ] **Step 2: Repeat for `es/index.astro`** (identical import + placement).

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: success.

- [ ] **Step 4: Browser verification (both locales)**

Run: `npm run dev`, then open `http://localhost:4321/en/` and `http://localhost:4321/es/`.
Verify:
- Skills section appears between Services and Projects.
- Four groups render in order: Content & media / Contenido y media → Dev workflow → QA & testing → Governance.
- Public cards (green badge) are clickable and open the repo deep-link in a new tab; internal cards (grey badge) are not links.
- Spanish page shows Spanish copy; layout is responsive (no horizontal scroll on narrow width).

- [ ] **Step 5: Commit**

```bash
git add src/pages/en/index.astro src/pages/es/index.astro
git commit -m "feat(skills): mount Skills section above Projects on both locales"
```

---

### Task 5: Public repo `agilabs-skills` v1

**Files (outside this repo):**
- Create: `~/Documents/repos/agilabs-skills/` (working copy) with the 8 generic skills, `README.md`, `LICENSE`.

**Skill sources (copy `SKILL.md` + any `scripts/`/assets):**
- `~/.claude/skills/demo-video` → `content-media/demo-video`
- `~/.claude/skills/spotify-upload` → `content-media/spotify-upload`
- `~/Documents/repos/personal-website/.claude/skills/blog-writer` → `content-media/blog-writer`
- `~/Documents/repos/personal-website/.claude/skills/tailor-cv` → `content-media/tailor-cv`
- `~/Documents/repos/oss-agent/.claude/skills/feature-dev` → `dev-workflow/feature-dev`
- `~/Documents/repos/oss-agent/.claude/skills/code-review` → `dev-workflow/code-review`
- `~/Documents/repos/oss-agent/.claude/skills/commit-pr` → `dev-workflow/commit-pr`
- `~/Documents/repos/sds_analysis/.claude/skills/playwright-cli` → `qa-testing/playwright-cli`

- [ ] **Step 1: Scaffold the working copy**

```bash
mkdir -p ~/Documents/repos/agilabs-skills/{content-media,dev-workflow,qa-testing}
cp -R ~/.claude/skills/demo-video ~/Documents/repos/agilabs-skills/content-media/demo-video
cp -R ~/.claude/skills/spotify-upload ~/Documents/repos/agilabs-skills/content-media/spotify-upload
cp -R ~/Documents/repos/personal-website/.claude/skills/blog-writer ~/Documents/repos/agilabs-skills/content-media/blog-writer
cp -R ~/Documents/repos/personal-website/.claude/skills/tailor-cv ~/Documents/repos/agilabs-skills/content-media/tailor-cv
cp -R ~/Documents/repos/oss-agent/.claude/skills/feature-dev ~/Documents/repos/agilabs-skills/dev-workflow/feature-dev
cp -R ~/Documents/repos/oss-agent/.claude/skills/code-review ~/Documents/repos/agilabs-skills/dev-workflow/code-review
cp -R ~/Documents/repos/oss-agent/.claude/skills/commit-pr ~/Documents/repos/agilabs-skills/dev-workflow/commit-pr
cp -R ~/Documents/repos/sds_analysis/.claude/skills/playwright-cli ~/Documents/repos/agilabs-skills/qa-testing/playwright-cli
```

- [ ] **Step 2: MANDATORY safety scan** (blocks the push)

```bash
cd ~/Documents/repos/agilabs-skills && grep -rniE 'simple ?kyc|\bSDS\b|\bLOCO\b|confluence|bitbucket|api[_-]?key|secret|password|bearer |authorization:|AZURE_|OPENAI_|sk-[a-z0-9]|xox[baprs]-|ghp_|-----BEGIN' . || echo "SCAN CLEAN"
```
Expected: `SCAN CLEAN`. If ANY hit: open the file, sanitize (or drop that skill to v2 and remove its card's public status in Task 1/2), and re-run until clean.
Note: `javieraguilar.ai` / `getvitamind.app` in `blog-writer`, and Google-TTS references in `demo-video`, are already-public and OK — the scan pattern above does not flag them; if you add broader patterns, whitelist those.

- [ ] **Step 3: Write `LICENSE` (MIT)**

```bash
cd ~/Documents/repos/agilabs-skills && curl -s https://raw.githubusercontent.com/licenses/license-templates/master/templates/mit.txt -o /dev/null 2>&1; true
```
Then write `LICENSE` with the standard MIT text, `Copyright (c) 2026 Javier Aguilar`. (Write the file directly — do not rely on network.)

- [ ] **Step 4: Write `README.md`**

Content: what these skills are (portable Claude Code / agent skills), how to install (`cp -R <skill> ~/.claude/skills/`), and an index table of the 8 skills grouped by the 3 folders with a one-line description each (reuse the EN descriptions from Task 2). Link back to https://javieraguilar.ai.

- [ ] **Step 5: Init, create GitHub repo, push**

```bash
cd ~/Documents/repos/agilabs-skills && git init -q && git add -A && git commit -q -m "feat: agilabs-skills v1 — 8 reusable agent skills"
gh repo create JaviMaligno/agilabs-skills --public --source=. --remote=origin --push
```
Expected: repo created and pushed; `gh repo view JaviMaligno/agilabs-skills --web` opens it.

- [ ] **Step 6: Verify deep-links resolve**

Run: `for p in content-media/demo-video content-media/blog-writer content-media/spotify-upload content-media/tailor-cv dev-workflow/feature-dev dev-workflow/code-review dev-workflow/commit-pr qa-testing/playwright-cli; do curl -s -o /dev/null -w "%{http_code} $p\n" "https://github.com/JaviMaligno/agilabs-skills/tree/main/$p"; done`
Expected: all `200`. (These are the exact `repoUrl`s from Task 1 — fix any 404 by aligning folder name ↔ `repoUrl`.)

---

### Task 6: Final verification & PR

**Files:** none (integration + delivery)

- [ ] **Step 1: Full build**

Run: `npm run build`
Expected: success.

- [ ] **Step 2: Final browser pass**

`npm run dev`; on `/en/` and `/es/` click at least two public cards and confirm they land on live repo pages (200, not 404). Confirm internal cards remain non-links. Capture one screenshot per locale for the PR.

- [ ] **Step 3: Push branch and open PR (do NOT merge — merge = production deploy)**

```bash
git push -u origin feat/skills-section
gh pr create --base main --head feat/skills-section \
  --title "feat(skills): add Skills section + link to public agilabs-skills repo" \
  --body "Adds a Skills section (grouped by capability, above the MCP/Projects content) on both locales. Public skills deep-link to the new public repo github.com/JaviMaligno/agilabs-skills (v1, 8 generic skills). Internal skills shown as anonymized capability cards. Spec: docs/superpowers/specs/2026-07-06-skills-section-design.md."
```

- [ ] **Step 4: Report** the PR URL and repo URL to the user for review before merge.

---

## Self-Review

**Spec coverage:**
- Web section placement (Services→Skills→Projects) → Task 4. ✅
- Grouped-by-capability cards + badges → Task 3. ✅
- Data layer `skills.ts` + interface → Task 1. ✅
- i18n EN/ES for all 14 + section/categories/badges → Task 2. ✅
- Internal anonymization → enforced in Task 2 copy + Global Constraints. ✅
- Public repo v1 with 8 generic skills, MIT, README → Task 5. ✅
- Mandatory pre-publish safety scan → Task 5 Step 2. ✅
- Deep-link `repoUrl`s + root CTA → Task 1 (`REPO` const) + Task 3 (`repoRoot`) + Task 5 Step 6 verify. ✅
- No merge to main (PR instead) → Task 6. ✅
- Out of scope (detail pages, filters, v2 core extraction) → not present in any task. ✅

**Placeholder scan:** No TBD/TODO/"handle edge cases". LICENSE/README steps specify exact content requirements. ✅

**Type consistency:** `SkillCategory`, `skills`, `getSkillsByCategory`, `skillCategoryOrder` defined in Task 1 and consumed with the same names/shape in Task 3. `t('skills')` shape (`section`, `categories`, `badges`, `<key>.title/description`) defined in Task 2 and consumed identically in Task 3. `repoUrl` folder paths in Task 1 match the copy destinations in Task 5 and the 200-check in Task 5 Step 6. ✅
