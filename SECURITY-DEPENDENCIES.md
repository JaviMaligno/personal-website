# Dependency security update (23 October 2026)

Use Node24.22.1 with the committed npm lock and `npm ci --ignore-scripts`.
Astro7.4.2 and its official Vercel11.0.16/Markdown integrations replace the
uncorrected Astro5 cohort. Sharp0.35.5, Vite8 and compatible transitive packages
resolve within that supported parent set.

The security upgrade requires the modern Content Layer API: the schema moves
to `src/content.config.ts`, uses the built-in glob loader, and consumers use
entry IDs and `render(entry)`. Existing article IDs/URLs, content, translations,
publication data and layouts remain unchanged. The unified remark/rehype math
and table plugins remain active, with HTML whitespace behavior preserved.
See the official [v6](https://docs.astro.build/en/guides/upgrade-to/v6/) and
[v7](https://docs.astro.build/en/guides/upgrade-to/v7/) migration guides.

Frozen install and Astro build passed, producing215 pages. A focused typecheck
of the eight changed content surfaces reports no errors, warnings or hints.
Eighteen selected offline checks pass, covering existing publication links and
rendered metadata, every existing article URL/body, KaTeX and Markdown table
wrappers. The first full local typecheck timed out; it is not reported as passed.
No browser, deployed-service, mail or provider verification is claimed.

Fresh public OSV package/version queries retain KaTeX0.16.47 (corrected0.18.2,
outside rehype-katex7's range) and path-to-regexp6.1.0 (corrected6.3.0, outside
the Vercel routing-utils exact pin; that parent also ships a separate corrected
alias). These remain unresolved package findings; no incompatible override is
used to hide them. Advisory coverage is bounded, not a universal clean bill.

PRs retain normal isolated Preview CI. Production remains push/main-only; this
task performs no merge, manual deployment, article publication or credential
change. Rendered checks run explicitly after a build; they are outside the
ordinary pre-build `npm test` glob.
