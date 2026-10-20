#!/usr/bin/env bash
# Shared install step for every condition (A, AL, AP, APL), run from the root of
# a variant tree by the Dockerfile and by `aa variant install` for local trees.
# The eslint devDependencies are installed with the same pinned versions in all
# four environments (configured only in AL/APL), so the environments differ only
# by the patches. They are not part of any patch: the patched tree is installed
# with --immutable first, then these are added on top.
set -euo pipefail
yarn install --immutable
cd packages/loot-core
yarn add -D eslint@9.39.5 @typescript-eslint/parser@8.71.0 typescript-eslint@8.71.0 --mode=skip-build
yarn eslint --version
