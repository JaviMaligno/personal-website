# Project context

- Read `CLAUDE.md` for project guidance. For article work, also read
  `.claude/skills/blog-writer/SKILL.md` and `docs/blog-publishing.md`.
- When available locally, find this repository's Claude Code project memory under
  `~/.claude/projects/`. Read its `memory/MEMORY.md` index and the notes relevant to
  the task. Verify time-sensitive claims against current files and services.
- Before implementing or launching an experiment, inspect the actual clients and
  execution records of previous experiments, including their linked repositories.
  API-key examples are not evidence of the route actually used. Check existing
  gateway, cloud-login and agent-mediated routes before introducing a new one.
- Before a real experimental run, report estimated wall time and cost by provider.
  Keep private infrastructure, credentials and personal memory contents out of
  this public repository and out of command output.
- Validity gate before the pilot, written into the experiment's spec. Do not
  launch the pilot until all four hold:
  (a) for every evaluator, a valid trace that differs from the references is
  accepted (an evaluator that fails valid work measures the mould, not the model);
  (b) for every task, the statement is true and not trivial, so the model can fail
  in an interesting way;
  (c) a table of conditions per model (harness, tools, reasoning budget), so no
  comparison mixes conditions;
  (d) for every claim planned for the article, n = runs × models × cases, marking
  those with n < 3.
  In an orchestrated plan this gate is an adversarial review stage: a clean-context
  reviewer gets the spec, not the conclusion (or a different-model reviewer gets the
  harness diff).
- Any run longer than 10 minutes writes its progress after every episode to
  `~/.claude/corridas/<slug>.json` as `{"nombre", "hechos", "total", "estado",
  "eta", "actualizado"}` (ISO time), so progress is visible without asking. When it
  finishes or stops (including a stop for lack of memory, `"estado": "parado-RAM"`),
  it raises a desktop notification with `~/.claude/bin/avisar.ps1 "<text>"`.
- Use existing articles to understand Javier's voice and identify overlap, while
  preserving the new argument agreed in the conversation.
