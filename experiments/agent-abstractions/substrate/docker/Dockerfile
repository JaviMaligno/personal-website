# Agent sandbox image: one per condition (aa-actual:<cond>).
# Build context (made by aa.runner.build_image): a temp dir holding the variant
# tree as `variant/`. Runs as the non-root `node` user so Claude Code accepts
# `--permission-mode bypassPermissions` (Review Focus #3).
#
# Stage `cli` (Node + agent CLIs, no repository) is also built alone as `aa-cli`
# (aa.runner.build_cli_image) for the memorisation probe, which must not see
# any Actual tree.
FROM node:24.22.1-bookworm AS cli
RUN corepack enable && apt-get update \
 && apt-get install -y --no-install-recommends git python3 build-essential ripgrep ca-certificates \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN npm i -g @anthropic-ai/claude-code@2.1.289 @openai/codex@0.159.3
USER node
RUN git config --global user.email agent@local && git config --global user.name agent
WORKDIR /home/node

FROM cli AS actual
ARG COND
LABEL aa.cond=$COND
USER root
COPY --chown=node:node variant/ /work/actual/
USER node
WORKDIR /work/actual
# Shared install step (substrate/docker/install-lint-deps.sh, also used by
# `aa variant install` for local trees): `yarn install --immutable`, then the
# eslint devDependencies with the same pinned versions in all four images
# (configured only in AL/APL), so the environments differ only by the patches.
# A failure here must fail the build; the version check proves the binary is
# resolvable from loot-core.
COPY --chown=node:node install-lint-deps.sh /home/node/install-lint-deps.sh
RUN bash /home/node/install-lint-deps.sh

# Study 2 (conditions R/F only): the `actual` image plus jscpd, pinned, for the
# per-chain duplication measure. A separate final stage so the study-1 images are
# unchanged: aa.runner.build_image builds study-1 conditions with `--target actual`
# (same instructions as before this stage existed) and R/F with `--target study2`.
FROM actual AS study2
USER root
RUN npm i -g jscpd@5.4.0 && jscpd --version
USER node
WORKDIR /work/actual
