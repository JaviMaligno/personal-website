---
title: "Bootstrap the Environment, Not the Agent"
description: "Why cloud workspaces and AI coding sessions need repository-owned bootstrap scripts for system packages, tests, and builds."
pubDate: 2026-07-08
tags: ["AI Agents", "Cloud Development", "Automation", "DevEx", "Claude Code"]
lang: en
translationKey: bootstrap-the-environment-not-the-agent
heroImage: "/blog/bootstrap-cloud-environments.png"
repoUrl: "https://github.com/JaviMaligno/code-world-models"
---

I recently found myself repeating the same loop with Claude Code in a remote session:

1. Ask it to make a change.
2. Watch it try to run the build or tests.
3. Watch the environment fail because a system dependency was missing.
4. Tell it: "use `apt-get` and install this."
5. Repeat in the next clean session.

The problem was not Claude. It was not LaTeX, Python, or the build itself either. The problem was that part of the project's operational knowledge lived in a conversation, not in the repository.

The concrete case was [Code World Models](https://github.com/JaviMaligno/code-world-models). The project has Python tests, but it also builds a LaTeX paper. On my laptop, everything was installed. In CI, everything was installed too, because GitHub Actions installed TeX Live before compiling the paper. But a remote Claude Code session starts from a fresh environment and has no reason to know that `pdflatex` is part of the real repository contract.

The fix was small: a session-start hook that prepares the environment before the agent needs it.

The broader principle is more useful: **bootstrap the environment, not the agent**.

## The Antipattern: Dependencies in the Prompt

When we work locally, we accumulate state without noticing. We have system packages, CLIs, credentials, caches, extensions, fonts, browsers, native binaries, and toolchains that do not appear in `package.json`, `pyproject.toml`, or `requirements.txt`.

That state becomes invisible because the project "works on my machine."

Cloud environments break that assumption. AI agents break it faster, because the agent tries to close the full loop:

- change the code;
- run tests;
- compile docs;
- open browsers;
- generate screenshots;
- publish artifacts;
- verify the final result.

If a binary is missing, the agent often does the reasonable thing: diagnose the failure, find an install command, try again. But that burns time, tokens, and attention. Worse, if the fix only lives in chat, the next environment does not improve.

Telling an agent "install TeX Live before compiling" is manual operational memory. Putting it in the repo is infrastructure.

## The Real Case: LaTeX and Python in a Remote Environment

In Code World Models, the paper lives in `docs/paper/main.tex` and is checked with:

```bash
bash scripts/check_latex.sh
```

In CI, the dependency was declared in `.github/workflows/ci.yml`:

```yaml
- name: Install TeX Live
  run: |
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra \
      texlive-fonts-recommended texlive-science texlive-bibtex-extra biber
```

That protected GitHub Actions, but not necessarily a remote work session.

So I added a Claude Code `SessionStart` hook:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

The script does three important things:

```bash
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

if ! command -v pdflatex >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended
fi

python -m pip install -e ".[dev]"
```

First, it is a no-op locally. My laptop already has what it needs, and I do not want an agent hook mutating my machine unnecessarily.

Second, it runs asynchronously. The first version of this hook was synchronous, but in this repo the paper build usually happens at the end, after the code and text edits are done. I do not need to block session startup while TeX Live installs; I need it ready by the time compilation happens.

Third, it is idempotent. If `pdflatex` already exists, it does not reinstall the toolchain.

Fourth, it uses `python -m pip`, not plain `pip`, so the install targets the same interpreter that later runs `python -m pytest`. That small detail avoids a tedious class of bugs where `pip` and `python` point at different environments.

The result is not dramatic. That is why it is good. The next time the agent opens the repo remotely, the environment prepares itself and the agent can spend its reasoning on the actual change.

## This Is Not Just About Agents

The same principle applies to any ephemeral environment:

- GitHub Codespaces;
- Dev Containers;
- Gitpod;
- CI runners;
- Vercel-like sandboxes;
- temporary demo machines;
- internal onboarding environments;
- remote agent sessions.

The difference with AI is that the cost of not doing it becomes more visible. A human might remember, "this repo always needs `libpq-dev`." An agent can infer it, but it should not have to rediscover it in every session.

Cloud workspaces make environments disposable. Agents make the build-test-fix loop much more frequent. Together, they make reproducible setup part of the repository contract rather than a nice-to-have.

## What Belongs in the Bootstrap

Not everything belongs in a startup script. If you put too much there, the environment becomes slow, opaque, and fragile. But there is a clear category of things that do fit:

- system packages required to compile or test;
- CLIs used by repository scripts;
- browsers or native dependencies for end-to-end tests;
- documentation toolchains such as LaTeX, Pandoc, or Graphviz;
- editable install of the local package;
- quick version checks;
- cache or temporary-directory setup.

The practical rule I use:

**If the agent, CI, or a new developer has to ask for it manually to run the basic workflow, it should be declared in the repo.**

It does not have to be a Claude hook. It could be a `devcontainer.json`, a Dockerfile, `scripts/bootstrap.sh`, a Makefile, a Nix definition, a reusable workflow, or a combination. The tool matters less than the ownership: the repository should know how to prepare its own environment.

## A Good Bootstrap Has Six Properties

### 1. It Is Idempotent

It should be safe to run many times. Check before installing:

```bash
if ! command -v pdflatex >/dev/null 2>&1; then
  apt-get install ...
fi
```

Agents retry. Humans retry. Design for that.

### 2. It Separates Local from Remote

Not every environment needs the same treatment. My hook exits immediately unless it is in a remote session:

```bash
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi
```

That condition keeps the bootstrap from becoming a source of local surprises.

### 3. It Reuses the CI Contract

If CI installs TeX Live, the remote environment should install TeX Live. If CI runs `pip install -e ".[dev]"`, the agent should prepare the same package. Consistency matters more than elegance.

In the best case, you factor the shared setup into one script. In some repos, the CI workflow and the remote hook duplicate a few lines. That is acceptable as long as they do not drift semantically.

### 4. It Chooses Sync vs Async Deliberately

Some setup can run in the background, but not all of it. In my case, the hook can start asynchronously because the PDF is built at the end of the workflow, long after the session starts. That would not be acceptable for a dependency needed by tests in the first few seconds.

The rule is simple: if the likely next command depends on the setup, keep it synchronous and fail fast. If the setup prepares a tool that will be used later, it can run asynchronously and save startup latency.

The bootstrap should not hide errors that make the environment invalid.

### 5. It Fails Visibly When It Blocks the Workflow

Async does not mean silent. If a dependency is mandatory, the workflow that uses it still needs a clear failure when setup did not finish or could not complete. In this case, `scripts/check_latex.sh` remains the real guard: when compilation time comes, it validates that the toolchain exists.

### 6. It Is Conservative with Privilege and Network Access

A startup hook is not a good place for arbitrary downloads. Avoid `curl | bash` unless you have a strong, controlled reason. Use system packages where they are enough. Pin versions when reproducibility matters. Separate privileged OS setup from user-level project setup.

## The Mental Shift

Many repositories still treat setup as documentation:

```markdown
Install these things before running the project.
```

That was reasonable when the main reader was a human sitting at their primary machine.

Now the reader might be an agent, an ephemeral runner, a temporary workspace, or a collaborator joining from another machine. For those readers, documentation is not enough. They need an executable contract.

The question is not "can the agent figure out how to install this?"

It probably can.

The better question is: **why should it figure it out every time?**

Every dependency that lives only in a conversation is friction that will repeat. Every setup step the repo can execute by itself is one less piece of context you have to load into your head, or into the agent's.

For teams working with AI, this becomes a form of DevEx: not just human developer experience, but agent experience. The best environment for an agent is not the one with the longest prompt instructions. It is the one that needs the fewest explanations before it can reach an honest build.

Bootstrap the environment. Let the agent work on the problem.
