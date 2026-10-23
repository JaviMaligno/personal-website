# Delivery profile

## vcs
- host: GitHub JaviMaligno/personal-website
- integration-branch: main
- production-branch: main
Source: fetched main and deploy workflow · checked 2026-10-22

## ci
- kind: GitHub Actions
- on-push-branch: main deploys production; article-specific paths also cross-post
Source: .github/workflows and CLAUDE.md · checked 2026-10-22

## environments
- test-env: local-static-build-or-pr-preview
- production-env: public-website
Source: deploy.yml and CLAUDE.md · checked 2026-10-22

## deploy
- kind: Vercel
- via: GitHub Actions
Rules:
- [invariant no-live-publishing] This maintenance task prepares the PR only. Do not merge to main, dispatch social/publishing workflows, publish content or launch experiments without explicit approval.
Source: deployment/publishing behavior verified in current workflows; user requested dependency security maintenance · checked 2026-10-22

## tracker
- kind: none
Source: user-requested security follow-up · checked 2026-10-22
