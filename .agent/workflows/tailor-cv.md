---
description: Adapt CV and write Cover Letter based on a Job Posting URL and my Projects portfolio.
---

# Tailor CV and Cover Letter

1. **Read Project Context**
   I will read your project portfolio to understand your experience.
   <!-- id: read_projects -->
   ```bash
   cat src/data/projects.ts
   ```

2. **Analyze Job Posting**
   I need the Job URL to proceed. Please provide the `Job URL`.
   I will then read the content of the URL to extract requirements.
   <!-- id: read_job -->
   <!-- param: job_url -->

3. **Generate Tailored Strategy**
   Based on the `job_url` content and your `projects.ts`, I will:
   - Identify the top 3 matching projects.
   - Determine the key skills to highlight (e.g., Python vs Node, AWS vs GCP).
   - Draft a strategy for the CV and Cover Letter.

4. **Create Documents**
   I will generate two markdown files in `docs/cvs/`:
   - `Javier_Aguilar_[Role]_[Company].md` (CV)
   - `Cover_Letter_[Role]_[Company].md` (Cover Letter)
   
   *The CV will include your website link `javieraguilar.ai` and prioritize the matched projects.*

5. **Convert to DOCX**
   I will convert the generated markdown files to DOCX using pandoc.
   // turbo
   ```bash
   cd docs/cvs
   # Find the most recently created .md files to convert (or I will ask you for specific names)
   # For automation, I will try to convert the files I just created.
   ```
