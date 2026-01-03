---
title: "Creating a Custom Skill for Claude Code: Automating Bilingual Blog Writing"
description: "How I built a Claude Code skill that standardizes and automates the creation of bilingual blog articles, ensuring consistency across EN/ES content."
pubDate: 2026-01-03
tags: ["Claude Code", "AI", "Automation", "Skills"]
lang: en
translationKey: claude-code-skills-blog-writer
---

One of the most powerful features of Claude Code is its ability to learn your specific workflows through **Agent Skills**. Today I want to share how I built a custom skill that automates the creation of bilingual blog articles for this website.

## What Are Agent Skills?

Agent Skills are a recent addition to Claude's ecosystem. According to Anthropic, skills are "folders that include instructions, scripts, and resources that Claude can load when needed."

Think of them as packaged expertise. Instead of explaining your workflow every time, you encode it once, and Claude loads it automatically when relevant.

Key characteristics of skills:

- **Selective Loading**: Claude only accesses a skill when it's relevant to the task
- **Composable**: Multiple skills can work together seamlessly
- **Portable**: They work across Claude apps, Claude Code, and the API

In Claude Code specifically, custom skills are filesystem-based—just a folder with a `SKILL.md` file that Claude discovers automatically.

## The Problem: Inconsistent Blog Content

My website supports both English and Spanish. Every article needs:

- Matching frontmatter in both files
- A shared `translationKey` to link translations
- Properly translated tags (AI → IA, Automation → Automatización)
- Consistent file naming and locations
- Same publication date for synchronized release

Before the skill, I had to remember all these requirements every time. Mistakes were common—mismatched translation keys, forgotten fields, inconsistent formatting.

## The Solution: blog-writer Skill

I created a skill at `.claude/skills/blog-writer/SKILL.md` that encodes all my blog writing conventions:

```yaml
---
name: blog-writer
description: Write bilingual blog articles for the personal website.
  Use when creating a new blog post, article, or writing content
  for the blog. Handles EN/ES translations, frontmatter, and
  content structure.
---
```

The skill defines:

### File Locations
```
src/content/blog/en/[slug].md  # English
src/content/blog/es/[slug].md  # Spanish
public/blog/[image-name].png   # Images
```

### Required Frontmatter
```yaml
---
title: "Article Title"
description: "SEO description"
pubDate: 2025-01-03
tags: ["Tag1", "Tag2"]
lang: en  # or es
translationKey: article-slug
---
```

### Tag Conventions

The skill includes a translation table for common tags:

| English | Spanish |
|---------|---------|
| AI | IA |
| Automation | Automatización |
| Development | Desarrollo |
| Architecture | Arquitectura |

## How It Works in Practice

When I invoke the skill, Claude automatically:

1. Creates both EN and ES files with matching `translationKey`
2. Uses the correct frontmatter format
3. Translates tags according to conventions
4. Follows the defined content structure
5. Places images in the correct directory

The invocation is simple:

```
/blog-writer Create an article about building MCP servers
```

Claude loads the skill, understands all the requirements, and produces consistent output every time.

## Repurposing LinkedIn Content

One feature I specifically built into the skill is the ability to convert LinkedIn posts into full blog articles. The skill includes instructions for:

1. Fetching the original post content
2. Downloading associated images
3. Expanding the condensed format into comprehensive sections
4. Maintaining the original publication date for authenticity
5. Keeping the core message while adding depth

This maximizes the value of content I've already created. A 200-word LinkedIn post becomes a 1500-word technical article with code examples, expanded explanations, and proper SEO optimization.

## Creating Your Own Skills

The structure is straightforward:

```
.claude/skills/
└── your-skill-name/
    └── SKILL.md
```

The `SKILL.md` file contains:

1. **Frontmatter**: Name and description (how Claude decides when to load it)
2. **Instructions**: Detailed workflow, conventions, and examples
3. **Checklists**: Verification steps before completion

The description in the frontmatter is crucial—it determines when Claude considers the skill relevant.

## Why This Matters

Skills represent a shift in how we work with AI assistants. Instead of:

- Repeating instructions every session
- Maintaining external documentation
- Catching inconsistencies in review

You encode your expertise once and benefit from it continuously.

For content creation specifically, this means:

- **Consistency**: Every article follows the same structure
- **Efficiency**: No time spent remembering conventions
- **Quality**: Built-in checklists catch common mistakes
- **Scale**: Produce more content without sacrificing standards

## What's Next

I'm exploring additional skills for other repetitive workflows—project documentation, code review checklists, deployment procedures. The pattern is the same: identify a workflow you repeat, encode it as a skill, and let Claude handle the details.

---

*Learn more about Agent Skills in the [official Anthropic documentation](https://claude.com/blog/skills) or explore the [skills repository](https://github.com/anthropics/skills).*
