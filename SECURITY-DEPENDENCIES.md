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

The 23 October follow-up uses stable KaTeX 0.18.10 for the existing Markdown and
Mermaid consumers. The corrected release is outside their old 0.16 ranges, so
the scoped overrides are guarded by actual article and existing-diagram compatibility
checks. The deprecated 0.18.11 accidental breaking release is deliberately avoided.
See the [KaTeX changelog](https://github.com/KaTeX/KaTeX/blob/main/CHANGELOG.md).
The blog now imports that same package's local CSS and font assets, replacing the
old 0.16.21 CDN stylesheet. Existing `.katex-mathml` and `.katex-display` custom
selectors remain valid and unchanged; internal KaTeX class prefixes come from
the matching new stylesheet. Root-coordinated Preview QA of both language articles
and a Mermaid route is required before merge; no new local browser/build proof
is claimed by this follow-up.

The scoped routing-utils override uses path-to-regexp 6.3.0, the corrected release
within major 6 ([security advisory](https://github.com/pillarjs/path-to-regexp/security/advisories/GHSA-9wv6-86v2-598j)).
The existing Vercel parent still returns its old compiler despite shipping a second
fixed alias. Before/after checks of all 12 actual public patterns, 10 routes from
the prior adapter output and 17 ordinary URL samples preserve route order,
redirects, headers, destinations and captures. The security fix changes capture
allocation for ambiguous synthetic templates such as `:name.:ext` or `:first-:second`
containing repeated separators; this site uses neither template. That behavior
change is documented, not normalized away.

Run `node security/math-routing.contract.mjs` after a frozen scripts-disabled
install for real article SSR, matching local CSS/font references and actual site
routing. It makes no assessment API request, browser/provider call, exploit or
stress probe. Mermaid Preview rendering and final-lock public OSV/hosted CI are
separate gates; a selected passing contract is not a universal clean bill.

PRs retain normal isolated Preview CI. Production remains push/main-only; this
task performs no merge, manual deployment, article publication or credential
change. Rendered checks run explicitly after a build; they are outside the
ordinary pre-build `npm test` glob.
