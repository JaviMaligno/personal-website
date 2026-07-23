# Egress-blocked hosts (Claude Code on the web session)

> **Purpose.** During the session that drafted the *routing / prompt-engineering*
> articles, several primary sources could not be fetched. This file lists every
> host that was blocked so the egress policy can be widened where it makes sense.
>
> **This doc is infra scratch, not site content.** It lives under `docs/` (not
> `src/content/`), so it is never published as a page. It's kept on the working
> branch only — **delete it or drop it before merging to `main`.** Nothing here
> is required by the site build.

## Two different kinds of "403" — only one is yours to fix

1. **Egress-policy denial (fixable by you).** The session's outbound proxy
   rejects the `CONNECT` before it ever reaches the site. The proxy records
   these as `kind: "connect_rejected"`, detail *"gateway answered 403 to
   CONNECT (policy denial or upstream failure)"*. These hosts are simply not on
   the environment's egress allowlist — widening the network policy for the
   environment lets a future session reach them.

2. **Site-side bot-blocking (NOT fixable by allowlisting).** The request does
   reach the site, but the site itself returns 403 to automated fetchers
   (Cloudflare / anti-bot). Allowlisting does nothing here — the content is only
   reachable by a real browser (i.e. you), or via search-snippet aggregators.

The proxy is the source of truth for which is which. Check any time with:

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status"   # see recentRelayFailures[]
```

(Per `/root/.ccr/README.md`: never disable TLS, never unset `HTTPS_PROXY`, and
policy denials must be reported, not routed around.)

## Confirmed egress-policy denials (proxy rejected the CONNECT)

These are the ones worth allowlisting — they blocked primary sources we needed.

| Host | Why we needed it | Specific URLs that failed |
|------|------------------|---------------------------|
| `arxiv.org` | Primary sources for the routing article (RouteLLM, FrugalGPT, Hybrid LLM papers) | `arxiv.org/abs/2406.18665`, `arxiv.org/abs/2305.05176`, `arxiv.org/abs/2404.14618`, `arxiv.org/html/2510.00202v1` |
| `cursor.com` | The Cursor "agent swarm / model economics" study — central source for Art. 2 (routing) | `cursor.com/es/blog/agent-swarm-model-economics`, `cursor.com/blog/composer`, `cursor.com/blog/router` |

## Blocked on fetch, cause ambiguous (egress policy *or* site bot-blocking)

Fetches to these returned 403; the proxy log didn't clearly attribute them, so
some may be site-side anti-bot rather than your egress policy. Try allowlisting
the ones you care about, but if they still 403 from a real fetch, it's the site.

| Host | Why we needed it |
|------|------------------|
| `x.com` / `t.co` | Source tweets: Karpathy ramble, Matt Shumer conjecture post, the DGG shared chat (`x.com/i/status/2080011280526594119`), Cursor link (`t.co/GktfUOjNgL`) |
| `openai.com`, `help.openai.com` | GPT-5.6 (Sol/Terra/Luna) announcement, reasoning-effort docs, model release notes |
| `en.wikipedia.org` | GPT-5.x version history cross-check |
| `cnbc.com` | GPT-5.6 public-release reporting |
| `lmsys.org` | RouteLLM blog (per-benchmark cost figures) |
| `openrouter.ai` | Auto Router docs + routing blog |
| `platform.claude.com` | Claude 4.6 effort-level (`standard/high/xhigh/max`) docs |
| `marktechpost.com`, `datacamp.com`, `thedecoder.com`, `artificialanalysis.ai` | Secondary write-ups used to triangulate the above |

## What still needs a real-browser check before publishing

Because the primaries above were unreachable, these specific claims in the draft
articles rest on search snippets and should be verified by opening the source
yourself:

- **Cursor study (Art. 2):** the exact planner/executor combinations, the
  cost/quality numbers, and which models — open `cursor.com/es/blog/agent-swarm-model-economics`.
- **Cursor Router:** the "30–50% lower cost" figure — `cursor.com/blog/router`.
- **RouteLLM per-benchmark numbers** (GSM8K ~35%, MMLU ~45%): the 85%/95% headline
  is verified from the GitHub README, but these two splits came from the LMSYS blog.
- **OpenAI effort levels:** the `max` level on GPT-5.6, and **Claude 4.6's** exact
  effort enum — verify on `help.openai.com` and `platform.claude.com`.
- **GPT-5.6 Sol/Terra/Luna** naming — confirmed across CNBC/Axios/Nextgov snippets,
  but worth one primary read.

## Already verified from a primary source (no re-check needed)

- **RouteLLM headline:** up to **85% cost reduction at 95% of GPT-4 quality**
  (MT-Bench, GPT-4 strong + Mixtral 8x7B weak) — read directly from
  `github.com/lm-sys/RouteLLM` (GitHub was reachable).
