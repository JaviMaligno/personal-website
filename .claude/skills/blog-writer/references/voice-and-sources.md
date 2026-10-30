# Voice and sources

## Whose Article This Is — First Person, Always

**Javier is the author.** The articles are written in his first person: *"hice
tres tandas"*, *"las leí todas a mano"*, *"estuve a punto de dar el eje por
cerrado"*. You put the words down; the voice, the work and the byline are his.

**Never write "Javier did X" or "Javier pointed out Y" inside an article.** That
turns the piece into yours and him into a character in it. His words, 2026-09-17:
*"quien es Javier? quien escribe el articulo? ESTOS ARTICULOS SON MIOS SOY EL
AUTOR Y ES MI VOZ, TU SOLO PONES LAS PALABRAS"*.

**And what he contributes is his credit, not an anecdote.** When he hand-labels a
sample and catches what the automated judge got wrong, that IS the interesting
part of the article — the human oversight finding the machine's errors. Write it
as his work: *"etiqueto a ciegas una muestra de cada tanda"*, *"el juez se
equivocaba en una dirección concreta"*. Not *"a reviewer objected"*.

This is the complement of the rule that **your** mistakes are never narrated in
his first person: yours get omitted or told as the experiment's, his findings are
his.

## Where the facts come from

1. **His account first.** When Javier tells the story of a project (why it failed, what the users
   did, what he decided), that is the version the article tells. He talked to the people
   involved; the repo did not. Example: the Data Source Automator pivot failed on adoption (too
   much friction against the users' own workflow), which he had told in the brief; the draft that
   took its causes from `design.md` instead had to be rewritten.
2. **The data and the scripts.** Every number comes from a script run over the raw data, so it can
   be recomputed. Numbers relayed by another session are recomputed too.
3. **The repo's docs** fill in facts he has not told you. Use them for what they are (design notes,
   reports) and keep them out of his first-person story.

Anything that cannot be traced to one of the three is a question for him, asked in the decisions
block. A plausible detail with no source behind it is the most expensive kind of correction.

Your own work in the session (the bugs you fixed, the false lead you followed, a parameter you set
wrong) belongs in the experiment's internal docs, where whoever picks it up next benefits from it.
The article reports what the experiment found. It enters the article only when the agent's
behaviour is itself the subject of the study.

## The reader

The reader knows only what is published: the article in front of them and the earlier articles it
links. Write for that reader.

- **Open by placing them.** Before the first number or anecdote, a sentence or two on the situation
  and why it matters, so the article starts at a walk rather than mid-stride.
- **Introduce each entity before using it.** A dataset, a model, a corpus or a tool gets one clause
  of who or what it is the first time it appears ("Steam, the PC game store, with 100,000+ game
  descriptions").
- **Readable on the diagonal.** Each block opens with a bold sentence that carries its point, so a
  reader skimming the bold lines gets the argument; the strongest result is the most visible one.
- **Answer the reader's obvious objection** in the text, at the point where they would raise it.
- **The finished argument only.** Unpublished studies, earlier drafts and the corrections made
  while writing stay out; when a revision teaches something the reader needs, state it as fact.

## Javier's voice

- **Nuance, as he thinks.** Claims as strong as the evidence and no stronger; scope them ("on these
  runs", "in this setup"). He writes from the centre of gravity of a practice, not as someone who
  just discovered it: good testing, reading the agent's trace and checking results were always
  part of his work.
- **Tight prose where the point is simple.** Spend the words on the hard parts.
- **His paragraphs are his.** When he writes or rewrites a passage, it goes in as he wrote it; you
  edit around it.
- **One language per file.** The EN article carries his remarks translated into English; the
  Spanish originals live in the ES article.
- **Work material is anonymised, never trimmed.** The site repo is public. When the best part of an
  article comes from a work session, keep it and replace the identifiers: tickets renumbered
  (`TICKET-41`), packages, workspace, SHAs and teammates made generic. The technical content stays
  intact. Grep for leftovers before committing.

## Writing Style

- **Tone**: Professional but conversational
- **Focus**: Practical value, real examples
- **Length**: 800-2000 words typically
- **Structure**: Clear headings, scannable sections
- **Code**: Include relevant code snippets with language identifiers
- **Images**: Always use **absolute URLs** for inline images: `https://www.javieraguilar.ai/blog/image-name.png`. Dev.to cannot resolve relative paths (`/blog/...`), and the publish script auto-converts relative paths but using absolute URLs from the start avoids issues. The `heroImage` frontmatter field can remain a relative path (it's converted by the publish script).

## Content Structure

```markdown
Opening paragraph placing the reader in the situation and the problem.

## Section Heading

**The point of the section in one bold sentence.** Content with clear explanations.
Focus on "why" not just "how".

## Another Section

Include practical examples:

```language
code block with syntax highlighting
```

## Conclusion/Next Steps

Wrap up with actionable takeaways or links.

---

*Footer with links to resources, repos, etc.*
```

## Link Javier's Own Work — Every Mention Is a Link

**Whenever the draft refers to something Javier has made, that mention must be a link.** Not a
"nice to have": a naked reference to his own work is a bug in the draft. Sweep for it before
handing the article over, because it is the single most common thing missing from first drafts.

What counts, and where it points:

| The draft says… | Link to |
|---|---|
| a previous article, "as I wrote before", "the previous article", any of its findings | `/en/blog/<slug>` · `/es/blog/<slug>` |
| "I've written some skills", any named skill of his | `/en/skills` · `/es/skills` |
| a project or case study | `/en/projects/<slug>` · `/es/projects/<slug>` |
| mentoring, teaching, the starter session | `/en/mentoring` · `/es/mentoring` |
| an experiment's code or data | the public repo, plus `repoUrl:` in the frontmatter |

Rules:

- **Use language-matched paths.** `/en/...` in the English file, `/es/...` in the Spanish one.
  Copy-pasting the English link into the Spanish article sends Spanish readers to English pages.
- **Link the first substantive mention**, not every one. Two links to the same article in one
  post is noise; zero is a lost reader.
- **Link the claim, not the boilerplate.** `[the previous article](/en/blog/slug), where
  declaring provenance only moved the strongest model` beats a bare "see my previous post".
- **Verify the slug exists** (`ls src/content/blog/en/`) before linking. A 404 in your own
  article is worse than no link.
- Series articles should link **backwards to their predecessor**; when a new one supersedes or
  qualifies an older finding, say so at the point where it does. A follow-up that adds models or
  conditions weaves them into the same comparison as the original ones, rather than appending an
  "Update" section.
- Something public that Javier made and that appears on his site (a product like the industry
  classifier, its models) is named and linked; anonymisation covers work identifiers, not his
  own published work.

**External things are links too.** The tweet the article answers, a paper, a named game or tool:
link each one at its first mention. The URL is usually in his first message of the session
(`session_brief.py` prints it).
