---
name: tailor-cv
description: Use when adapting a CV or writing a cover letter for a specific job posting, role description, or recruiter message. Handles job analysis, project matching, and document generation in markdown, DOCX, and PDF.
---

# Tailor CV and Cover Letter

Adapt Javier Aguilar's CV and generate a cover letter tailored to a specific role.

## Inputs

One of:
- **Job URL** - fetched and analyzed via WebFetch
- **Job description text** - pasted directly by user
- **Recruiter message** - extracted requirements from informal message

Plus optional user instructions (e.g., "emphasize Langfuse experience", "focus on Python").

## Workflow

0. **Read the master CV first.** It is the source of truth for dates, job titles, contract status and confidentiality rules, and lives in the **private** repo `JaviMaligno/cv-and-interviews` at `master/Javier_Aguilar_CV_Master.md` (locally: `~/Documents/repos/cv-and-interviews`). Do **not** take dates or titles from the old PDFs in `Downloads/` — they have incorrect overlapping "Present" ranges. Never invent a job title, a contract type, or the reason behind a technical decision: a fabricated date fails the reference check and a fabricated rationale fails the technical interview. Ask instead.

1. **Read portfolio context**
   - Read `src/data/projects.ts` for project list
   - Read `src/i18n/en.json` for project descriptions and outcomes
   - If user provides additional context about unlisted experience, incorporate it

2. **Analyze job requirements**
   - If URL: fetch with WebFetch and extract requirements
   - If text/message: parse directly
   - Extract: role title, company, must-have skills, nice-to-have skills, domain, language requirements, location constraints

3. **Match and strategize**
   - Rank top 3-4 projects by relevance to the role
   - Identify which skills to highlight (e.g., Python vs TypeScript, AWS vs GCP)
   - Determine the CV "angle" (e.g., "Agentic AI Engineer", "MLOps Engineer", "Full-Stack AI")
   - Note any user-specific instructions for emphasis

4. **Generate CV** as `docs/cvs/sources/Javier_Aguilar_[Role]_[Company].md`
5. **Generate Cover Letter** as `docs/cvs/sources/Cover_Letter_[Role]_[Company].md`
6. **Convert to DOCX and PDF** using pandoc — see *Where files go* and *Document Conversion*
7. **Sweep the root before finishing.** List the CVs currently sitting at the root of `docs/cvs/` with their dates and ask Javier which are dead, so they drop to `archive/`. This is the only moment the folder gets attention, so it replaces any periodic review. Rules:
   - **Ask, never infer.** File dates say when a CV was generated, not whether the process is open — and they cannot tell a lost application from a won one (`Profesor_UnivHesperides` was archived as "old" when it had actually landed the job).
   - Offer a starting guess to make answering cheap: anything older than ~2 months with no follow-up is *probably* dead. Javier confirms or corrects; a one-word "todas menos X" is a valid answer.
   - Do not sweep on a run where Javier is just regenerating or tweaking an existing CV — only when a genuinely new application is created.
   - Archiving is reversible: moving a file back up from `archive/` is fine if a recruiter resurfaces.

## Where files go

`docs/cvs/` is laid out so that the frequent action (grab the CV to upload it) shows nothing else. Respect it — do not write deliverables back to the root:

```
docs/cvs/
├── Javier_Aguilar_<slug>.docx / .pdf   ← ONLY CV deliverables, current applications
├── cover-letters/  Cover_Letter_<slug>.docx / .pdf
├── sources/        every .md (CV and cover letter alike — they are sources, not deliverables)
└── archive/        everything belonging to past applications, flat
```

- **Every `.md` goes in `sources/`**, whether it is a CV or a letter. That is the whole rule; there is no `.md` at the root.
- The `Cover_Letter_` prefix stays even inside `cover-letters/`: it is the filename a recruiter sees when Javier attaches it.
- Javier rarely sends cover letters. Still generate one, but the CV is the deliverable that matters.
- `archive/` is a flat dumping ground, not a mirror of this structure. It holds every finished application — lost, won or gone quiet alike. Never archive without asking (step 7).
- **`docs/cvs/` is in `.gitignore`** (the repo is public). Never force-add it, and do not count on `git checkout` to recover anything here.

## CV Template

```markdown
# JAVIER AGUILAR MARTIN

**London, UK (EU/Schengen)** | javiecija96@gmail.com | [javieraguilar.ai](https://javieraguilar.ai) | [github.com/JaviMaligno](https://github.com/JaviMaligno)

---

## SUMMARY

**[Tailored Role Title]** with [2-3 lines matching key requirements]. [Unique differentiator].

---

## EXPERIENCE

### ML Engineer (contractor) — Sapira AI
**Aug 2025 – Present**

- [4-5 bullets tailored to job requirements, using STAR-lite format]
- Each bullet: **Bold keyword:** Action + measurable result

### AI Engineer — Simple KYC
**Jan 2024 – Present**

- [3-4 bullets relevant to role]

### Lecturer in Algebra & Geometry — Universidad de las Hespérides
**From Oct 2026**

- [only for academic, research or teaching-adjacent roles; omit from engineering CVs]

### Graduate Data Scientist — Hastings Direct
**Sep 2023 – Aug 2025**

- [1-2 bullets relevant to role]

---

## INDEPENDENT PRACTICE — AGILabs

**2025 – Present**

- [1-2 lines: direct-to-client AI delivery, public library of packaged agent skills, bilingual engineering blog]
- [optional: fold the "Selected public work" table in here — AGILabs is the umbrella it all ships under]

---

## TECHNICAL SKILLS

**[Category matching role]:**
- [Grouped by relevance, most important first]
- **Bold** the exact technologies mentioned in the job posting

**[Second category]:**
- [...]

---

## EDUCATION

- **PhD in Mathematics** — University of Kent (2020–2023)
- **Master's Degree in Mathematics** — University of Seville (2018–2019)
- **Bachelor's Degree in Mathematics** — University of Seville (2014–2018)

---

## LANGUAGES

- Spanish (Native)
- English (Advanced)
- German (B2)
- French (B1)
```

## Cover Letter Template

```markdown
Dear [Hiring Manager/Recruiter name if known],

[Opening: Why this specific role excites you - reference company/project]

[Body 1: Most relevant experience mapped to their top requirement]

[Body 2: Second key match, with concrete outcomes/metrics]

[Body 3: Cultural/team fit - language skills, remote experience, collaboration style]

[Closing: Call to action, availability]

Best regards,
Javier Aguilar Martin
javieraguilar.ai
```

## Tailoring Rules

- **Mirror job language**: Use their exact terminology (e.g., "observability" not "monitoring" if that's what they say)
- **Lead with matches**: First bullet under Sapira AI should directly address the #1 job requirement
- **Quantify outcomes**: Use metrics from project outcomes (">95% accuracy", "40% cost reduction", "processing under 2 min/doc")
- **Bold matching tech**: If job says "Langfuse", bold **Langfuse** in skills and bullets
- **Adapt title**: Match role title to job (AI Engineer, MLOps, GenAI Consultant, etc.)
- **Never put AGILabs under EXPERIENCE**: it is Javier's own brand, not an employer. Listed alongside two live contracts it produces three consecutive "Present" entries and readers conclude he is working three jobs at once — this has already cost him in real applications. It goes in its own section after EXPERIENCE (see template), where placement alone signals "independent practice" without needing a disclaimer.
- **Location**: Show "London, UK (EU/Schengen)" when EU location is relevant
- **Languages section**: Move up if multilingual requirement mentioned

## Document Conversion

Run from the repo root with absolute-ish paths; do **not** `cd docs/cvs`, it leaves the shell's working directory moved for later commands.

### Pandoc header (required)

Helvetica has no `→` glyph, so arrows silently vanish from the PDF. Always pass a header file:

```bash
cat > /tmp/cvfix.tex <<'EOF'
\usepackage{newunicodechar}
\newunicodechar{→}{\ensuremath{\rightarrow}}
\usepackage{titlesec}
\titlespacing*{\section}{0pt}{6pt}{3pt}
\titlespacing*{\subsection}{0pt}{5pt}{2pt}
\setlength{\parskip}{2pt}
EOF
```

### DOCX

```bash
pandoc docs/cvs/sources/Javier_Aguilar_[Role]_[Company].md -o docs/cvs/Javier_Aguilar_[Role]_[Company].docx
pandoc docs/cvs/sources/Cover_Letter_[Role]_[Company].md  -o docs/cvs/cover-letters/Cover_Letter_[Role]_[Company].docx
```

### PDF

CV uses tighter margins and 10pt to hold two pages; the cover letter gets wider margins.

```bash
pandoc docs/cvs/sources/Javier_Aguilar_[Role]_[Company].md -o docs/cvs/Javier_Aguilar_[Role]_[Company].pdf \
  --pdf-engine=xelatex -H /tmp/cvfix.tex -V geometry:margin=1.4cm -V fontsize=10pt \
  -V mainfont="Helvetica" -V colorlinks=true -V linkcolor=blue -V urlcolor=blue
pandoc docs/cvs/sources/Cover_Letter_[Role]_[Company].md -o docs/cvs/cover-letters/Cover_Letter_[Role]_[Company].pdf \
  --pdf-engine=xelatex -H /tmp/cvfix.tex -V geometry:margin=2cm -V fontsize=11pt \
  -V mainfont="Helvetica" -V colorlinks=true -V linkcolor=blue -V urlcolor=blue
```

Note: `fontsize` only accepts 10/11/12pt — LaTeX silently ignores anything else.

### Verifying the result

- **Page count: use `pdfinfo`, never `mdls`.** `mdls` serves stale Spotlight metadata and will report the pre-edit count for minutes after a rebuild.
- Target 2 pages for the CV. If it spills by a few lines, cut content before shrinking the font.
- Confirm arrows survived: `pdftotext <pdf> - | grep -c '→'`.

## Checklist

- [ ] Master CV read (source of truth for dates, titles, contract status)
- [ ] Portfolio context read (projects.ts + en.json)
- [ ] Job requirements extracted and listed
- [ ] Top 3-4 projects matched with justification
- [ ] AGILabs kept OUT of EXPERIENCE, in its own section
- [ ] CV written to `docs/cvs/sources/`, cover letter to `docs/cvs/sources/`
- [ ] DOCX + PDF built with the `cvfix.tex` header, landing in `docs/cvs/` and `docs/cvs/cover-letters/`
- [ ] Page count checked with `pdfinfo` (CV ≈ 2 pages), arrows verified with `pdftotext`
- [ ] No `.md` and no cover-letter deliverable left at the root of `docs/cvs/`
- [ ] User-specific emphasis incorporated
