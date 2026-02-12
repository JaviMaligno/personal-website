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

4. **Generate CV** as `docs/cvs/Javier_Aguilar_[Role]_[Company].md`
5. **Generate Cover Letter** as `docs/cvs/Cover_Letter_[Role]_[Company].md`
6. **Convert to DOCX and PDF** using pandoc

## CV Template

```markdown
# JAVIER AGUILAR MARTIN

**London, UK (EU/Schengen)** | javiecija96@gmail.com | [javieraguilar.ai](https://javieraguilar.ai) | [github.com/JaviMaligno](https://github.com/JaviMaligno)

---

## SUMMARY

**[Tailored Role Title]** with [2-3 lines matching key requirements]. [Unique differentiator].

---

## EXPERIENCE

### [Tailored Title] — Sapira AI
**Aug 2025 – Present**

- [4-5 bullets tailored to job requirements, using STAR-lite format]
- Each bullet: **Bold keyword:** Action + measurable result

### [Tailored Title] — Simple KYC
**Jan 2024 – Jul 2025**

- [3-4 bullets relevant to role]

### Graduate Data Scientist — Hastings Direct
**Sep 2023 – Aug 2024**

- [1-2 bullets relevant to role]

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
- **Location**: Show "London, UK (EU/Schengen)" when EU location is relevant
- **Languages section**: Move up if multilingual requirement mentioned

## Document Conversion

### DOCX

```bash
cd docs/cvs && pandoc "Javier_Aguilar_[Role]_[Company].md" -o "Javier_Aguilar_[Role]_[Company].docx" && pandoc "Cover_Letter_[Role]_[Company].md" -o "Cover_Letter_[Role]_[Company].docx"
```

### PDF

Uses xelatex for proper font rendering and link styling. CV uses tighter margins (1.5cm), cover letter uses wider margins (2cm).

```bash
cd docs/cvs && pandoc "Javier_Aguilar_[Role]_[Company].md" -o "Javier_Aguilar_[Role]_[Company].pdf" --pdf-engine=xelatex -V geometry:margin=1.5cm -V fontsize=11pt -V mainfont="Helvetica" -V colorlinks=true -V linkcolor=blue -V urlcolor=blue && pandoc "Cover_Letter_[Role]_[Company].md" -o "Cover_Letter_[Role]_[Company].pdf" --pdf-engine=xelatex -V geometry:margin=2cm -V fontsize=11pt -V mainfont="Helvetica" -V colorlinks=true -V linkcolor=blue -V urlcolor=blue
```

## Checklist

- [ ] Portfolio context read (projects.ts + en.json)
- [ ] Job requirements extracted and listed
- [ ] Top 3-4 projects matched with justification
- [ ] CV generated with tailored summary, experience bullets, and skills
- [ ] Cover letter generated
- [ ] Both converted to DOCX
- [ ] Both converted to PDF
- [ ] User-specific emphasis incorporated
